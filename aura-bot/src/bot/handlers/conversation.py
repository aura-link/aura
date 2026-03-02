"""Handler para mensajes libres → Claude AI con pre-filtro y rate limiting."""

from telegram import Update
from telegram.ext import ContextTypes
from src.bot.roles import get_role, Role
from src.utils.filter import is_relevant, REJECTION_MESSAGE
from src.diagnostics.auto_responder import auto_respond, format_diagnostic_context
from src.utils.logger import log

# Limite de consultas AI por dia para clientes/guests
DAILY_AI_LIMIT = 15

# Keywords que indican problema de conexion
_CONN_KW = {
    "lento", "lenta", "no carga", "no abre", "no jala", "no sirve",
    "sin internet", "sin señal", "sin conexion", "no conecta", "se cae",
    "se desconecta", "intermitente", "inestable", "caida", "caido",
    "falla", "fallo", "no funciona", "lag", "latencia", "ping",
    "velocidad", "megas", "mbps", "señal", "antena", "reiniciar", "reboot",
    "no tengo internet", "no hay internet", "me cae", "se me cae",
    "no tengo señal", "no tengo conexion",
}


def _is_connection_problem(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in _CONN_KW)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa mensajes de texto libre con 3 capas de proteccion."""
    user = update.effective_user
    message = update.message
    if not user or not message or not message.text:
        return

    text = message.text.strip()
    if not text:
        return

    db = context.bot_data["db"]
    claude = context.bot_data.get("claude")

    if not claude or not claude.enabled:
        await message.reply_text(
            "💬 Por ahora solo puedo atender comandos.\n"
            "Usa /help para ver que puedo hacer."
        )
        return

    # Determine role
    link = await db.get_customer_link(user.id)
    role = get_role(user.id, is_linked=link is not None)

    # === CAPA 1: Pre-filtro local (solo para clientes/guests, admins pasan libre) ===
    if role != Role.ADMIN and not is_relevant(text):
        log.info("Mensaje filtrado (no relevante) de user %d: %s", user.id, text[:50])
        await message.reply_text(REJECTION_MESSAGE, parse_mode="Markdown")
        return

    # === CAPA 2: Rate limiting (solo para clientes/guests, admins sin limite) ===
    if role != Role.ADMIN:
        usage = await db.get_ai_usage_today(user.id)
        if usage >= DAILY_AI_LIMIT:
            log.info("Rate limit alcanzado para user %d: %d/%d", user.id, usage, DAILY_AI_LIMIT)
            await message.reply_text(
                f"⚠️ Has alcanzado el limite de {DAILY_AI_LIMIT} consultas por hoy.\n\n"
                "Puedes seguir usando los comandos directos:\n"
                "💰 /misaldo — Tu saldo\n"
                "📡 /miservicio — Tu servicio\n"
                "📶 /miconexion — Diagnostico\n"
                "🆘 /soporte — Hablar con un tecnico\n\n"
                "El limite se renueva mañana."
            )
            return

    # === CAPA 2.5: Check incidente/mantenimiento activo (respuesta automatica, $0) ===
    if link:
        client_id_check = link["crm_client_id"]

        # Check incidente activo
        incident = await db.get_active_incident_for_client(client_id_check)
        if incident:
            zone = incident.get("site_name", "tu zona")
            await message.reply_text(
                f"⚠️ *Interrupcion detectada en zona {zone}*\n\n"
                "Ya estamos trabajando para restablecer el servicio. "
                "Te notificaremos cuando se resuelva.\n\n"
                "Si necesitas mas ayuda, usa /soporte.",
                parse_mode="Markdown",
            )
            log.info("Respuesta automatica por incidente activo para user %d", user.id)
            return

        # Check mantenimiento activo
        maint = await db.get_maintenance_for_client(client_id_check)
        if maint:
            zone = maint.get("site_name", "tu zona")
            ends = maint.get("ends_at", "")
            try:
                from datetime import datetime
                et = datetime.fromisoformat(ends)
                end_fmt = et.strftime("%H:%M")
            except (ValueError, TypeError):
                end_fmt = ends
            await message.reply_text(
                f"🔧 *Mantenimiento en curso en zona {zone}*\n\n"
                f"Fin estimado: {end_fmt}\n"
                "Tu servicio se restablecera al terminar.\n\n"
                "Si el problema persiste despues, usa /miconexion.",
                parse_mode="Markdown",
            )
            log.info("Respuesta automatica por mantenimiento activo para user %d", user.id)
            return

    # === CAPA 2.7: Diagnostico automatico Tier 1 (solo clientes vinculados, $0) ===
    diagnostic_context = None
    if link and role != Role.ADMIN and _is_connection_problem(text):
        engine = context.bot_data.get("diagnostic_engine")
        if engine:
            await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")
            diag = await engine.diagnose(link["crm_client_id"], link["crm_client_name"])

            response = auto_respond(diag)
            if response:
                log.info("Auto-diagnostic response for user %d (severity=%s)", user.id, diag.severity)
                await message.reply_text(response, parse_mode="Markdown")
                await db.add_message(user.id, "user", text)
                await db.add_message(user.id, "assistant", response)
                return

            # No auto-response → pass diagnostic context to Claude
            diagnostic_context = format_diagnostic_context(diag)
            log.info("Diagnostic pre-loaded for user %d (severity=%s), passing to Claude", user.id, diag.severity)

    # === CAPA 3: Claude AI (con system prompt que refuerza el enfoque) ===
    role_str = role.value
    client_name = link["crm_client_name"] if link else None
    client_id = link["crm_client_id"] if link else None

    user_context = {
        "telegram_user_id": user.id,
        "telegram_username": user.username,
        "client_id": client_id,
    }

    # Get conversation history
    history = await db.get_history(user.id)

    # Send typing indicator
    await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")

    # Get active incidents for context (admin sees them in system prompt)
    active_incidents = None
    if role == Role.ADMIN:
        active_incidents = await db.get_active_incidents()

    # Call Claude
    response = await claude.chat(
        user_message=text,
        history=history,
        role=role_str,
        client_name=client_name,
        client_id=client_id,
        user_context=user_context,
        active_incidents=active_incidents if active_incidents else None,
        diagnostic_context=diagnostic_context,
    )

    # Save to history
    await db.add_message(user.id, "user", text)
    await db.add_message(user.id, "assistant", response)

    # Send response (split if too long)
    if len(response) <= 4096:
        await message.reply_text(response)
    else:
        for i in range(0, len(response), 4096):
            chunk = response[i : i + 4096]
            await message.reply_text(chunk)
