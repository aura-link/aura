"""Handler de fotos de comprobantes de pago enviados por clientes."""

import json
from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import ContextTypes
from src.bot.roles import get_role, Role
from src import config
from src.utils.logger import log

TZ = ZoneInfo("America/Mexico_City")

MONTH_NAMES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa foto enviada como comprobante de pago."""
    user = update.effective_user
    msg = update.message
    if not user or not msg or not msg.photo:
        return

    db = context.bot_data["db"]
    link = await db.get_customer_link(user.id)
    role = get_role(user.id, is_linked=link is not None)

    # Admin photos are ignored (they use callbacks)
    if role == Role.ADMIN:
        return

    if not link:
        await msg.reply_text(
            "Para enviar un comprobante de pago, primero vincula tu cuenta "
            "con /vincular."
        )
        return

    client_id = link["crm_client_id"]
    client_name = link.get("crm_client_name", "")

    payment_processor = context.bot_data.get("payment_processor")
    notifier = context.bot_data.get("notifier")

    if not payment_processor:
        await msg.reply_text(
            "El sistema de pagos no esta disponible en este momento. "
            "Contacta al administrador."
        )
        return

    await msg.reply_text("📷 Analizando tu comprobante...")

    # Download photo (largest size)
    photo = msg.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()
    image_bytes = bytes(image_bytes)

    # Save receipt to disk
    receipt_path = payment_processor.receipt_storage.save(client_id, image_bytes)

    # Analyze with Claude Vision
    analysis = await payment_processor.analyze_receipt(image_bytes)
    log.info("Receipt analysis for client %s: %s", client_id, analysis)

    if not analysis.get("valid"):
        # Invalid receipt - check fraud
        reason = analysis.get("reason", "No es un comprobante valido")
        report_id = await db.create_payment_report(
            client_id=client_id, telegram_user_id=user.id,
            amount=None, method=None, receipt_path=receipt_path,
            ai_analysis=json.dumps(analysis), matched_invoice_ids=None,
            status="rejected",
        )

        fraud_result = await payment_processor.check_fraud(
            client_id, user.id, report_id, reason,
        )

        action = fraud_result.get("action")
        if action == "suspended":
            template = "fraud_suspended"
        elif action == "warning_2":
            template = "fraud_warning_2"
        else:
            template = "fraud_warning_1"

        if notifier:
            await notifier.notify_client(
                user.id, template, f"fraud_{report_id}",
            )
        else:
            await msg.reply_text(
                "❌ La imagen enviada no parece ser un comprobante de pago valido.\n"
                "Por favor envia una foto clara del comprobante."
            )
        return

    # Valid receipt - extract data
    amount = float(analysis.get("amount", 0))
    method = analysis.get("method", "transferencia")
    reference = analysis.get("reference", "")
    confidence = analysis.get("confidence", "low")

    if amount <= 0:
        await msg.reply_text(
            "No pude identificar el monto del comprobante. "
            "Por favor envia una foto mas clara."
        )
        return

    # Check for duplicate receipt
    duplicate = await payment_processor.check_duplicate_receipt(
        client_id, reference, amount
    )
    if duplicate:
        dup_id = duplicate.get("id")
        dup_date = (duplicate.get("created_at") or "")[:16]
        await msg.reply_text(
            f"⚠️ Este comprobante ya fue reportado anteriormente "
            f"(reporte #{dup_id}, {dup_date}).\n\n"
            f"Si tienes un pago diferente, envia el nuevo comprobante."
        )
        return

    # Match invoices
    matched = await payment_processor.match_invoices(client_id, amount)
    invoice_ids = [inv.get("id") for inv in matched if inv.get("id")]
    invoice_ids_json = json.dumps(invoice_ids) if invoice_ids else None

    # Check if client is suspended (needs reconnection fee)
    suspension = await db.get_suspension_for_client(client_id)
    if suspension:
        invoices = await payment_processor.crm.get_unpaid_invoices(client_id)
        total_unpaid = sum(inv.get("total", 0) for inv in invoices)
        total_needed = payment_processor.calculate_reactivation_amount(total_unpaid)

        if amount < total_needed - 5:  # tolerance
            await msg.reply_text(
                f"⚠️ Tu servicio esta suspendido.\n"
                f"Deuda pendiente: *${total_unpaid:.0f} MXN*\n"
                f"Cargo de reconexion: *${config.RECONNECTION_FEE:.0f} MXN*\n"
                f"Total necesario: *${total_needed:.0f} MXN*\n\n"
                f"Tu comprobante es por ${amount:.0f} MXN. "
                f"Necesitas cubrir al menos ${total_needed:.0f} MXN para reactivar.",
                parse_mode="Markdown",
            )
            return

    if method == "efectivo":
        # Cash payments need admin approval
        report_id = await db.create_payment_report(
            client_id=client_id, telegram_user_id=user.id,
            amount=amount, method=method, receipt_path=receipt_path,
            ai_analysis=json.dumps(analysis), matched_invoice_ids=invoice_ids_json,
            status="pending",
        )

        if notifier:
            await notifier.notify_client(
                user.id, "payment_pending_client",
                f"pending_{report_id}", amount=f"{amount:.0f}",
            )
            await notifier.notify_admins(
                "payment_pending_admin", f"pending_{report_id}",
                client_name=client_name or client_id,
                amount=f"{amount:.0f}", report_id=report_id,
            )
        else:
            await msg.reply_text(
                f"📋 Tu reporte de pago en efectivo por ${amount:.0f} MXN "
                "ha sido enviado al administrador."
            )
        return

    # Transfer/OXXO - auto-register if confidence is high/medium
    if confidence in ("high", "medium") and invoice_ids:
        note = f"Auto-registrado via Telegram. Ref: {reference}. Confianza: {confidence}"
        # Register only the invoice amount (not reconnection fee) in CRM
        invoice_total = sum(inv.get("total", 0) for inv in matched)
        payment = await payment_processor.register_payment(
            client_id, invoice_total, method, invoice_ids, note,
        )

        crm_payment_id = payment.get("id") if payment else None
        report_id = await db.create_payment_report(
            client_id=client_id, telegram_user_id=user.id,
            amount=amount, method=method, receipt_path=receipt_path,
            ai_analysis=json.dumps(analysis), matched_invoice_ids=invoice_ids_json,
            crm_payment_id=crm_payment_id, status="approved",
        )

        # Reactivate if suspended
        if suspension:
            await payment_processor.reactivate_client(client_id, 0)

        # Notify client
        now = datetime.now(TZ)
        next_month_num = now.month % 12 + 1
        next_month = MONTH_NAMES.get(next_month_num, "proximo mes")

        if notifier:
            await notifier.notify_client(
                user.id, "payment_approved",
                f"approved_{report_id}",
                amount=f"{amount:.0f}", next_month=next_month,
            )
        else:
            await msg.reply_text(f"✅ Pago de ${amount:.0f} MXN registrado exitosamente!")

        # Notify admin about auto-approval
        if notifier:
            await notifier.notify_admins(
                "payment_approved_admin", f"auto_{report_id}",
                client_name=client_name or client_id,
                amount=f"{amount:.0f}", method=method,
                report_id=report_id,
                invoice_ids=", ".join(str(i) for i in invoice_ids),
            )
    else:
        # Low confidence or no matching invoices - send to admin
        report_id = await db.create_payment_report(
            client_id=client_id, telegram_user_id=user.id,
            amount=amount, method=method, receipt_path=receipt_path,
            ai_analysis=json.dumps(analysis), matched_invoice_ids=invoice_ids_json,
            status="pending",
        )

        if notifier:
            await notifier.notify_client(
                user.id, "payment_pending_client",
                f"pending_{report_id}", amount=f"{amount:.0f}",
            )
            await notifier.notify_admins(
                "payment_pending_admin", f"pending_{report_id}",
                client_name=client_name or client_id,
                amount=f"{amount:.0f}", report_id=report_id,
            )
        else:
            await msg.reply_text(
                f"📋 Tu comprobante por ${amount:.0f} MXN fue recibido. "
                "El administrador verificara y registrara tu pago."
            )
