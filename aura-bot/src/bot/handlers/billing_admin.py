"""Comandos admin de cobranza: /pagos, /morosos, /reactivar."""

import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.roles import is_admin
from src.utils.logger import log


async def pagos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista reportes de pago pendientes de aprobacion."""
    user = update.effective_user
    msg = update.message or (update.callback_query and update.callback_query.message)
    if not user or not msg:
        return
    if update.callback_query:
        await update.callback_query.answer()

    if not is_admin(user.id):
        await msg.reply_text("Solo administradores pueden usar este comando.")
        return

    db = context.bot_data["db"]
    pending = await db.get_pending_payment_reports()

    if not pending:
        await msg.reply_text("✅ No hay reportes de pago pendientes.")
        return

    for report in pending[:10]:
        rid = report["id"]
        client_id = report["client_id"]
        amount = report.get("amount", 0)
        method = report.get("method", "?")
        created = report.get("created_at", "")

        # Get client name
        crm = context.bot_data.get("uisp_crm")
        client_name = client_id
        if crm:
            c = await crm.get_client(client_id)
            if c:
                client_name = crm.get_client_name(c)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Aprobar", callback_data=f"pay_approve_{rid}"),
             InlineKeyboardButton("❌ Rechazar", callback_data=f"pay_reject_{rid}")],
        ])

        await msg.reply_text(
            f"📋 *Reporte #{rid}*\n\n"
            f"👤 {client_name}\n"
            f"💰 ${amount:.0f} MXN ({method})\n"
            f"📅 {created[:16] if created else 'N/A'}",
            parse_mode="Markdown",
            reply_markup=keyboard,
        )


async def morosos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista clientes suspendidos por falta de pago."""
    user = update.effective_user
    msg = update.message or (update.callback_query and update.callback_query.message)
    if not user or not msg:
        return
    if update.callback_query:
        await update.callback_query.answer()

    if not is_admin(user.id):
        await msg.reply_text("Solo administradores pueden usar este comando.")
        return

    db = context.bot_data["db"]
    suspensions = await db.get_active_suspensions()

    if not suspensions:
        await msg.reply_text("✅ No hay clientes suspendidos actualmente.")
        return

    lines = ["🔴 *Clientes suspendidos:*\n"]
    for s in suspensions[:20]:
        client_id = s["client_id"]
        secret = s.get("secret_name", "?")
        reason = s.get("reason", "nonpayment")
        since = s.get("suspended_at", "")[:10]
        reason_emoji = "💰" if reason == "nonpayment" else "🚨"
        lines.append(f"{reason_emoji} *{secret}* (ID: {client_id})")
        lines.append(f"   Desde: {since} | Razon: {reason}")

    lines.append(f"\nTotal: {len(suspensions)}")
    lines.append("\nUsa `/reactivar <nombre>` para reactivar.")

    await msg.reply_text("\n".join(lines), parse_mode="Markdown")


async def reactivar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reactivar un cliente suspendido."""
    user = update.effective_user
    msg = update.message
    if not user or not msg:
        return

    if not is_admin(user.id):
        await msg.reply_text("Solo administradores pueden usar este comando.")
        return

    args = msg.text.split(maxsplit=1)
    if len(args) < 2:
        await msg.reply_text("Uso: `/reactivar <nombre o ID de cliente>`", parse_mode="Markdown")
        return

    query = args[1].strip()
    db = context.bot_data["db"]
    payment_processor = context.bot_data.get("payment_processor")
    crm = context.bot_data.get("uisp_crm")

    if not payment_processor or not crm:
        await msg.reply_text("Sistema de cobranza no disponible.")
        return

    # Try to find by client ID first, then by name
    client_id = None
    suspensions = await db.get_active_suspensions()

    for s in suspensions:
        if s["client_id"] == query:
            client_id = s["client_id"]
            break
        if query.lower() in (s.get("secret_name") or "").lower():
            client_id = s["client_id"]
            break

    if not client_id:
        # Try searching CRM
        clients = await crm.search_clients(query)
        for c in clients:
            cid = str(c.get("id", ""))
            suspension = await db.get_suspension_for_client(cid)
            if suspension:
                client_id = cid
                break

    if not client_id:
        await msg.reply_text(f"No encontre un cliente suspendido que coincida con '{query}'.")
        return

    await msg.reply_text("⏳ Reactivando cliente...")
    result = await payment_processor.reactivate_client(client_id, user.id)

    if result.get("success"):
        name = result.get("client_name", client_id)
        mk_status = "✅" if result.get("mikrotik") else "⚠️ (manual)"
        crm_status = "✅" if result.get("crm") else "⚠️ (manual)"
        await msg.reply_text(
            f"✅ *Cliente reactivado*\n\n"
            f"👤 {name}\n"
            f"📡 MikroTik: {mk_status}\n"
            f"📋 CRM: {crm_status}",
            parse_mode="Markdown",
        )
    else:
        await msg.reply_text(
            f"❌ Error: {result.get('error', 'No se pudo reactivar')}"
        )


async def handle_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja callbacks de aprobar/rechazar pago."""
    query = update.callback_query
    if not query or not query.data:
        return

    user = update.effective_user
    if not user or not is_admin(user.id):
        await query.answer("Solo administradores pueden hacer esto.")
        return

    data = query.data
    await query.answer()

    db = context.bot_data["db"]
    payment_processor = context.bot_data.get("payment_processor")
    crm = context.bot_data.get("uisp_crm")
    notifier = context.bot_data.get("notifier")

    if data.startswith("pay_approve_"):
        report_id = int(data.replace("pay_approve_", ""))
        report = await db.get_payment_report(report_id)
        if not report:
            await query.message.reply_text("Reporte no encontrado.")
            return
        if report["status"] != "pending":
            await query.message.reply_text(f"Reporte ya fue procesado ({report['status']}).")
            return

        client_id = report["client_id"]
        amount = report.get("amount", 0)
        method = report.get("method", "efectivo")
        invoice_ids_raw = report.get("matched_invoice_ids")
        invoice_ids = json.loads(invoice_ids_raw) if invoice_ids_raw else None

        # Register payment in CRM
        payment = None
        if payment_processor:
            note = f"Aprobado por admin via Telegram. Reporte #{report_id}"
            payment = await payment_processor.register_payment(
                client_id, amount, method, invoice_ids, note
            )

        crm_payment_id = payment.get("id") if payment else None
        await db.update_payment_report(
            report_id, status="approved", reviewed_at="CURRENT_TIMESTAMP",
            admin_notes=f"Aprobado por {user.id}",
            crm_payment_id=crm_payment_id,
        )

        # Check if client should be reactivated
        suspension = await db.get_suspension_for_client(client_id)
        if suspension and payment_processor:
            await payment_processor.reactivate_client(client_id, user.id)

        # Notify client
        telegram_user_id = report.get("telegram_user_id")
        if telegram_user_id and notifier:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo("America/Mexico_City"))
            months = {1: "febrero", 2: "marzo", 3: "abril", 4: "mayo",
                      5: "junio", 6: "julio", 7: "agosto", 8: "septiembre",
                      9: "octubre", 10: "noviembre", 11: "diciembre", 12: "enero"}
            next_month = months.get(now.month, "proximo mes")
            await notifier.notify_client(
                telegram_user_id, "payment_approved",
                f"approved_{report_id}",
                amount=f"{amount:.0f}", next_month=next_month,
            )

        # Get client name for confirmation
        client_name = client_id
        if crm:
            c = await crm.get_client(client_id)
            if c:
                client_name = crm.get_client_name(c)

        reactivated = " + reactivado" if suspension else ""
        await query.message.edit_text(
            f"✅ *Pago aprobado{reactivated}*\n\n"
            f"👤 {client_name}\n"
            f"💰 ${amount:.0f} MXN\n"
            f"📋 Reporte #{report_id}\n"
            f"Aprobado por: {user.first_name}",
            parse_mode="Markdown",
        )

    elif data.startswith("pay_reject_"):
        report_id = int(data.replace("pay_reject_", ""))
        report = await db.get_payment_report(report_id)
        if not report:
            await query.message.reply_text("Reporte no encontrado.")
            return
        if report["status"] != "pending":
            await query.message.reply_text(f"Reporte ya fue procesado ({report['status']}).")
            return

        client_id = report["client_id"]
        await db.update_payment_report(
            report_id, status="rejected", reviewed_at="CURRENT_TIMESTAMP",
            admin_notes=f"Rechazado por {user.id}",
        )

        # Check fraud
        if payment_processor:
            fraud_result = await payment_processor.check_fraud(
                client_id, report.get("telegram_user_id", 0),
                report_id, "Rechazado por admin",
            )

        # Notify client
        telegram_user_id = report.get("telegram_user_id")
        if telegram_user_id and notifier:
            await notifier.notify_client(
                telegram_user_id, "payment_rejected",
                f"rejected_{report_id}",
            )

        await query.message.edit_text(
            f"❌ *Pago rechazado*\n\n"
            f"📋 Reporte #{report_id}\n"
            f"Rechazado por: {user.first_name}",
            parse_mode="Markdown",
        )
