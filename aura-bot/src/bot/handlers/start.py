"""Handlers para /start, /help, /menu."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.roles import get_role, Role
from src.bot import keyboards
from src.utils.logger import log


WELCOME_MSG = (
    "*Hola! Soy AURA*, tu asistente virtual de AURALINK.\n\n"
    "Puedo ayudarte con:\n"
    "- Consultar tu saldo y pagos\n"
    "- Ver el estado de tu servicio\n"
    "- Diagnosticar tu conexion\n"
    "- Reportar problemas\n\n"
    "Tambien puedes escribirme cualquier pregunta en español.\n\n"
    "Usa /help para ver todos los comandos."
)

WELCOME_GUEST = (
    "*Hola! Soy AURA*, asistente virtual de AURALINK.\n\n"
    "Para atenderte necesito saber quien eres.\n"
    "Presiona el boton para vincular tu cuenta."
)

HELP_CUSTOMER = (
    "📋 *Comandos disponibles:*\n\n"
    "💰 /misaldo — Saldo y estado de pago\n"
    "📡 /miservicio — Plan, velocidad, estado\n"
    "📶 /miconexion — Señal, PPPoE, diagnostico\n"
    "🔧 /reportar — Diagnostico automatico\n"
    "🆘 /soporte — Escalar a tecnico\n"
    "📋 /menu — Menu principal\n\n"
    "💳 *Pagos:*\n"
    "Envia una foto de tu comprobante de pago "
    "(transferencia u OXXO) y lo registro automaticamente.\n\n"
    "💬 O escribe cualquier pregunta!"
)

HELP_ADMIN = (
    "🛠 *Comandos de administrador:*\n\n"
    "🌐 /red — Overview de la red\n"
    "👥 /clientes — Resumen de clientes\n"
    "🔍 /buscar <nombre> — Buscar cliente\n"
    "📡 /dispositivos — Dispositivos offline\n"
    "📊 /pppoe — Sesiones PPPoE activas\n"
    "🏓 /diagnostico <ip> — Ping desde MikroTik\n"
    "⚠️ /caidas — Outages activos\n\n"
    "📍 *Monitoreo:*\n"
    "📍 /zonas — Zonas y clientes asociados\n"
    "🚨 /incidentes — Incidentes activos\n"
    "📊 /monitor — Estado del monitor\n"
    "🔧 /mantenimiento — Mantenimientos programados\n\n"
    "⚡ *Gestion rapida:*\n"
    "➕ /alta nombre-zona,perfil — Alta cliente nuevo\n"
    "📋 /plan nombre,perfil — Cambiar plan PPPoE\n"
    "🛠 /admin — Panel completo de administracion\n\n"
    "💳 *Cobranza:*\n"
    "💳 /pagos — Reportes de pago pendientes\n"
    "🔴 /morosos — Clientes suspendidos\n"
    "✅ /reactivar nombre — Reactivar cliente\n"
    "⚡ /cobranza — Trigger manual de cobranza\n\n"
    "📲 *Onboarding:*\n"
    "📲 /sinvincular — Clientes sin vincular (por zona)\n"
    "📊 /progreso — Dashboard de vinculacion\n"
    "💬 /mensaje — Mensaje WhatsApp para clientes\n"
)

HELP_GUEST = (
    "Para acceder a tus datos, primero necesitas vincular tu cuenta.\n\n"
    "Usa /vincular para comenzar."
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message:
        return

    db = context.bot_data["db"]
    link = await db.get_customer_link(user.id)

    # Deep link: /start link_PPPUSERNAME — auto-register from captive portal
    args = context.args
    if args and args[0].startswith("link_") and not link:
        await _handle_deep_link(update, context, args[0][5:])
        return

    role = get_role(user.id, is_linked=link is not None)

    if role == Role.ADMIN:
        await update.message.reply_text(
            WELCOME_MSG, parse_mode="Markdown", reply_markup=keyboards.main_menu_admin()
        )
    elif role == Role.CUSTOMER:
        await update.message.reply_text(
            WELCOME_MSG, parse_mode="Markdown", reply_markup=keyboards.main_menu_customer()
        )
    else:
        await update.message.reply_text(
            WELCOME_GUEST, parse_mode="Markdown", reply_markup=keyboards.main_menu_guest()
        )


async def _handle_deep_link(update: Update, context: ContextTypes.DEFAULT_TYPE, ppp_name: str):
    """Auto-link client from captive portal deep link. PPP name identifies the client."""
    user = update.effective_user
    db = context.bot_data["db"]
    crm = context.bot_data["uisp_crm"]
    mk = context.bot_data.get("mikrotik")

    log.info("Deep link registration: telegram=%d, ppp_name=%s", user.id, ppp_name)

    # Find the PPPoE secret to get the IP
    secret = None
    device_ip = ""
    if mk:
        secret = await mk.find_secret_by_name(ppp_name)
        if secret:
            device_ip = secret.get("remote-address", "") or ""

    # Search CRM clients matching this PPPoE name
    clients = await crm.get_clients()
    all_links = await db.get_all_customer_links()
    linked_ids = {str(l["crm_client_id"]) for l in all_links}

    # Match PPP name against CRM client names
    from rapidfuzz import fuzz
    best_match = None
    best_score = 0
    for c in clients:
        if str(c.get("id", "")) in linked_ids:
            continue
        client_name = crm.get_client_name(c)
        # Compare ppp_name (e.g. "juanlopezc") against normalized client name
        normalized = client_name.lower().replace(" ", "")
        score = fuzz.ratio(ppp_name.lower(), normalized)
        if score > best_score:
            best_score = score
            best_match = (c, client_name)

    if not best_match or best_score < 50:
        log.warning("Deep link: no CRM match for ppp=%s (best_score=%d)", ppp_name, best_score)
        await update.message.reply_text(
            "No pude encontrar tu cuenta automaticamente.\n"
            "Usa /vincular para vincular manualmente.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Vincular cuenta", callback_data="cmd_vincular")],
            ]),
        )
        return

    client, client_name = best_match
    client_id = str(client.get("id", ""))

    # Get service info for display
    services = await crm.get_client_services(client_id)
    plan = "Sin plan"
    svc_zone = ""
    for svc in services:
        if svc.get("status") in (0, 1):
            plan = svc.get("servicePlanName") or "Sin plan"
            svc_zone = svc.get("city") or svc.get("street") or ""
            break

    from src.bot.handlers.registration import _get_zone_abbr, _generate_service_id
    zone_abbr = _get_zone_abbr(svc_zone) if svc_zone else "AUR"
    service_id = _generate_service_id(zone_abbr, client_id)

    # Store match for confirmation
    context.user_data["deeplink_match"] = {
        "client_id": client_id,
        "client_name": client_name,
        "plan": plan,
        "zone": svc_zone,
        "zone_abbr": zone_abbr,
        "service_id": service_id,
        "device_ip": device_ip,
        "ppp_name": ppp_name,
    }

    ip_line = f"Antena IP: `{device_ip}`\n" if device_ip else ""
    await update.message.reply_text(
        f"*Vinculacion rapida*\n\n"
        f"Nombre: *{client_name}*\n"
        f"Zona: *{svc_zone}*\n"
        f"Plan: *{plan}*\n"
        f"{ip_line}"
        f"ID de servicio: `{service_id}`\n\n"
        f"Es esta tu cuenta?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Si, vincular mi cuenta", callback_data="deeplink_confirm")],
            [InlineKeyboardButton("No es mi cuenta", callback_data="cmd_vincular")],
        ]),
    )


async def handle_deeplink_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm deep link registration."""
    query = update.callback_query
    if not query:
        return
    await query.answer()

    user = update.effective_user
    db = context.bot_data["db"]
    crm = context.bot_data["uisp_crm"]

    match = context.user_data.pop("deeplink_match", None)
    if not match:
        await query.message.reply_text("Sesion expirada. Usa /vincular para intentar de nuevo.")
        return

    client_id = match["client_id"]
    client_name = match["client_name"]
    service_id = match["service_id"]
    device_ip = match.get("device_ip", "")

    # Write userIdent to CRM
    ident_ok = await crm.update_client_ident(client_id, service_id)
    if ident_ok:
        log.info("Deep link CRM userIdent: %s -> %s", client_id, service_id)

    # Save link
    await db.link_customer(
        telegram_user_id=user.id,
        telegram_username=user.username,
        crm_client_id=client_id,
        crm_client_name=client_name,
        service_id=service_id,
    )
    await db.mark_onboarding_linked(client_id)

    # Dismiss from captive portal
    mk = context.bot_data.get("mikrotik")
    if mk:
        try:
            from src.bot.handlers.registration import _dismiss_from_avisos
            await _dismiss_from_avisos(mk, client_name, device_ip=device_ip)
        except Exception as e:
            log.warning("Deep link dismiss error: %s", e)

    log.info("Deep link vinculado: Telegram %d -> CRM %s (%s) sid=%s",
             user.id, client_id, client_name, service_id)

    await query.message.reply_text(
        f"*Cuenta vinculada!*\n\n"
        f"Bienvenido/a, *{client_name}*!\n"
        f"Tu ID de servicio: `{service_id}`\n\n"
        "Ahora puedes usar:\n"
        "/misaldo — Ver tu saldo\n"
        "/miservicio — Ver tu servicio\n"
        "/miconexion — Diagnosticar tu conexion\n\n"
        "O escribeme cualquier pregunta.",
        parse_mode="Markdown",
        reply_markup=keyboards.main_menu_customer(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message:
        return

    db = context.bot_data["db"]
    link = await db.get_customer_link(user.id)
    role = get_role(user.id, is_linked=link is not None)

    text = HELP_CUSTOMER
    if role == Role.ADMIN:
        text = HELP_CUSTOMER + "\n" + HELP_ADMIN
    elif role == Role.GUEST:
        text = HELP_GUEST

    await update.message.reply_text(text, parse_mode="Markdown")


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message:
        return

    db = context.bot_data["db"]
    link = await db.get_customer_link(user.id)
    role = get_role(user.id, is_linked=link is not None)

    if role == Role.ADMIN:
        kb = keyboards.main_menu_admin()
    elif role == Role.CUSTOMER:
        kb = keyboards.main_menu_customer()
    else:
        kb = keyboards.main_menu_guest()

    await update.message.reply_text(
        "📋 *Menu principal:*", parse_mode="Markdown", reply_markup=kb
    )
