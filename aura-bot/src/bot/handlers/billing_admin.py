"""Comandos admin de cobranza: /pagos, /morosos, /reactivar, /cobranza."""

import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.roles import is_admin
from src import config
from src.utils.logger import log

TZ = ZoneInfo("America/Mexico_City")


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
        receipt_path = report.get("receipt_path")

        # Get client name
        crm = context.bot_data.get("uisp_crm")
        client_name = client_id
        if crm:
            c = await crm.get_client(client_id)
            if c:
                client_name = crm.get_client_name(c)

        buttons = [
            [InlineKeyboardButton("✅ Aprobar", callback_data=f"pay_approve_{rid}"),
             InlineKeyboardButton("❌ Rechazar", callback_data=f"pay_reject_{rid}")],
        ]
        if receipt_path:
            buttons.append(
                [InlineKeyboardButton("📷 Ver comprobante", callback_data=f"pay_receipt_{rid}")]
            )
        keyboard = InlineKeyboardMarkup(buttons)

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


async def cobranza_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trigger manual de acciones de cobranza: /cobranza <accion>."""
    user = update.effective_user
    msg = update.message
    if not user or not msg:
        return

    if not is_admin(user.id):
        await msg.reply_text("Solo administradores pueden usar este comando.")
        return

    args = msg.text.split(maxsplit=1)
    if len(args) < 2:
        await msg.reply_text(
            "📋 *Trigger manual de cobranza*\n\n"
            "`/cobranza aviso` — Enviar avisos de factura (dia 1)\n"
            "`/cobranza recordatorio` — Enviar recordatorios (dia 3)\n"
            "`/cobranza advertencia` — Enviar advertencias (dia 7)\n"
            "`/cobranza suspender` — Ejecutar suspensiones (dia 8)\n",
            parse_mode="Markdown",
        )
        return

    action_map = {
        "aviso": "invoice",
        "recordatorio": "reminder",
        "advertencia": "warning",
        "suspender": "suspend",
    }
    action = action_map.get(args[1].strip().lower())
    if not action:
        await msg.reply_text("Accion no reconocida. Usa: aviso, recordatorio, advertencia, suspender")
        return

    scheduler = context.bot_data.get("billing_scheduler")
    if not scheduler:
        await msg.reply_text("Scheduler de cobranza no disponible.")
        return

    await msg.reply_text(f"⏳ Ejecutando '{args[1].strip()}'...")
    result = await scheduler.run_manual(action)
    await msg.reply_text(f"✅ {result}")


async def handle_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja callbacks de aprobar/rechazar/ver comprobante."""
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

    # View receipt image
    if data.startswith("pay_receipt_"):
        report_id = int(data.replace("pay_receipt_", ""))
        report = await db.get_payment_report(report_id)
        if not report or not report.get("receipt_path"):
            await query.message.reply_text("Comprobante no disponible.")
            return
        receipt_path = report["receipt_path"]
        try:
            with open(receipt_path, "rb") as f:
                await query.message.reply_photo(
                    photo=f,
                    caption=f"📷 Comprobante del reporte #{report_id}",
                )
        except FileNotFoundError:
            await query.message.reply_text("Archivo de comprobante no encontrado.")
        return

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
            report_id, status="approved",
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
            now = datetime.now(TZ)
            next_month_num = now.month % 12 + 1
            months = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
                      5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
                      9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}
            next_month = months.get(next_month_num, "proximo mes")
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
            report_id, status="rejected",
            admin_notes=f"Rechazado por {user.id}",
        )

        # Check fraud
        if payment_processor:
            await payment_processor.check_fraud(
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
