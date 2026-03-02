"""Handlers de cliente: /misaldo, /miservicio, /miconexion, /reportar, /soporte."""

from telegram import Update
from telegram.ext import ContextTypes
from src.utils.formatting import format_mxn, format_signal, format_speed, format_datetime, status_emoji
from src.diagnostics.engine import DiagnosticResult
from src.utils.logger import log


async def _get_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> dict | None:
    """Verifica que el usuario este vinculado. Retorna link o None."""
    user = update.effective_user
    if not user:
        return None
    db = context.bot_data["db"]
    link = await db.get_customer_link(user.id)
    if not link:
        msg = update.message or (update.callback_query and update.callback_query.message)
        if msg:
            await msg.reply_text(
                "⚠️ No tienes cuenta vinculada.\n"
                "Usa /vincular para registrarte primero."
            )
        return None
    return link


async def misaldo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra saldo del cliente."""
    msg = update.message or (update.callback_query and update.callback_query.message)
    if update.callback_query:
        await update.callback_query.answer()

    link = await _get_link(update, context)
    if not link:
        return

    crm = context.bot_data["uisp_crm"]
    balance = await crm.get_client_balance(link["crm_client_id"])

    if "error" in balance:
        await msg.reply_text(f"❌ {balance['error']}")
        return

    text = (
        f"💰 *Saldo de {balance['client_name']}*\n\n"
        f"  Saldo: {format_mxn(balance['balance'])}\n"
        f"  Facturas pendientes: {balance['unpaid_count']}\n"
        f"  Total pendiente: {format_mxn(balance['total_unpaid'])}\n"
    )

    if balance["balance"] <= 0 and balance["unpaid_count"] == 0:
        text += "\n✅ Tu cuenta esta al corriente!"
    elif balance["total_unpaid"] > 0:
        text += "\n⚠️ Tienes pagos pendientes."

    await msg.reply_text(text, parse_mode="Markdown")


async def miservicio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra detalles del servicio del cliente."""
    msg = update.message or (update.callback_query and update.callback_query.message)
    if update.callback_query:
        await update.callback_query.answer()

    link = await _get_link(update, context)
    if not link:
        return

    crm = context.bot_data["uisp_crm"]
    services = await crm.get_client_service_details(link["crm_client_id"])

    if not services:
        await msg.reply_text("No se encontraron servicios activos.")
        return

    text = f"📡 *Servicios de {link['crm_client_name']}*\n\n"
    for svc in services:
        emoji = status_emoji(svc["status"])
        text += (
            f"{emoji} *{svc['name']}*\n"
            f"  Plan: {svc['plan']}\n"
            f"  Estado: {svc['status']}\n"
        )
        if svc["download"]:
            text += f"  Descarga: {format_speed(svc['download'])}\n"
        if svc["upload"]:
            text += f"  Subida: {format_speed(svc['upload'])}\n"
        if svc["address"]:
            text += f"  Direccion: {svc['address']}\n"
        text += "\n"

    await msg.reply_text(text, parse_mode="Markdown")


async def miconexion_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Diagnostica la conexion del cliente: señal + PPPoE + ping."""
    msg = update.message or (update.callback_query and update.callback_query.message)
    if update.callback_query:
        await update.callback_query.answer()

    link = await _get_link(update, context)
    if not link:
        return

    await msg.reply_text("🔍 Analizando tu conexion...")

    engine = context.bot_data.get("diagnostic_engine")
    if not engine:
        await msg.reply_text("⚠️ Diagnostico no disponible. Usa /soporte.")
        return

    diag = await engine.diagnose(link["crm_client_id"], link["crm_client_name"])
    text = _format_miconexion(diag)
    await msg.reply_text(text, parse_mode="Markdown")


def _format_miconexion(d: DiagnosticResult) -> str:
    """Formatea DiagnosticResult para /miconexion (vista detallada)."""
    text = f"📶 *Conexion de {d.client_name}*\n\n"

    if not d.device_found:
        text += "⚠️ No se encontro dispositivo asociado a tu servicio.\nContacta a soporte si tienes problemas."
        return text

    text += f"📡 *Antena: {d.device_name or 'N/A'}*\n"
    text += f"  Modelo: {d.device_model or 'N/A'}\n"
    text += f"  Estado: {status_emoji(d.device_status)} {d.device_status}\n"

    if d.signal_dbm is not None:
        text += f"  Señal: {format_signal(d.signal_dbm)}\n"

    if d.device_ip:
        text += f"  IP: {d.device_ip}\n"

    if d.pppoe_active:
        text += f"\n📊 *PPPoE:*\n"
        text += f"  Usuario: {d.pppoe_username or 'N/A'}\n"
        text += f"  Uptime: {d.pppoe_uptime or 'N/A'}\n"
        text += f"  MAC: {d.pppoe_mac or 'N/A'}\n"
    elif d.device_ip:
        text += "\n⚠️ Sin sesion PPPoE activa\n"

    if d.ping_sent > 0:
        if d.ping_success:
            text += f"\n🏓 *Ping:* {d.ping_avg_ms or 'N/A'} ms ({d.ping_received}/{d.ping_sent})\n"
        else:
            text += "\n🏓 *Ping:* Sin respuesta\n"

    return text


async def reportar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Diagnostico automatico + reporte."""
    msg = update.message or (update.callback_query and update.callback_query.message)
    if update.callback_query:
        await update.callback_query.answer()

    link = await _get_link(update, context)
    if not link:
        return

    await msg.reply_text("🔧 Ejecutando diagnostico completo...")

    engine = context.bot_data.get("diagnostic_engine")
    if not engine:
        await msg.reply_text("⚠️ Diagnostico no disponible. Usa /soporte.")
        return

    diag = await engine.diagnose(link["crm_client_id"], link["crm_client_name"])

    if not diag.issues:
        await msg.reply_text(
            "✅ *Diagnostico completado*\n\n"
            "No se detectaron problemas con tu conexion.\n\n"
            "Si aun tienes problemas, usa /soporte para hablar con un tecnico.",
            parse_mode="Markdown",
        )
    else:
        text = "⚠️ *Diagnostico completado*\n\nProblemas detectados:\n"
        for issue in diag.issues:
            text += f"  • {issue}\n"
        text += "\nUsa /soporte para escalar a un tecnico."
        await msg.reply_text(text, parse_mode="Markdown")


async def soporte_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Escala a soporte humano."""
    msg = update.message or (update.callback_query and update.callback_query.message)
    if update.callback_query:
        await update.callback_query.answer()

    user = update.effective_user
    if not user:
        return

    db = context.bot_data["db"]
    link = await db.get_customer_link(user.id)

    issue = "Solicitud de soporte via Telegram"
    if context.args:
        issue = " ".join(context.args)

    ticket_id = await db.create_escalation(
        telegram_user_id=user.id,
        telegram_username=user.username,
        crm_client_id=link["crm_client_id"] if link else None,
        issue=issue,
    )

    name = link["crm_client_name"] if link else (user.full_name or "Desconocido")

    await msg.reply_text(
        f"🆘 *Ticket de soporte #{ticket_id}*\n\n"
        f"Nombre: {name}\n"
        f"Motivo: {issue}\n\n"
        "Un tecnico se pondra en contacto contigo pronto.\n"
        "Mientras tanto, puedes describir tu problema aqui.",
        parse_mode="Markdown",
    )

    # Notify admins
    from src import config
    for admin_id in config.TELEGRAM_ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"🆘 *Nuevo ticket de soporte #{ticket_id}*\n\n"
                    f"Cliente: {name}\n"
                    f"Telegram: @{user.username or 'N/A'}\n"
                    f"Motivo: {issue}"
                ),
                parse_mode="Markdown",
            )
        except Exception as e:
            log.warning("No se pudo notificar admin %d: %s", admin_id, e)
