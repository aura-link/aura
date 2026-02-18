"""Flujo de vinculacion Telegram → CRM con seleccion de zona e ID de servicio."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from rapidfuzz import fuzz
from src.bot import keyboards
from src.utils.logger import log

# States
WAITING_NAME, WAITING_ZONE, WAITING_CONFIRM = range(3)

# Zone abbreviations for service ID generation
ZONE_ABBREVIATIONS = {
    "Tomatlan": "TML",
    "Tomatlán": "TML",
    "La Cumbre": "CBR",
    "Jose Maria Pino Suarez": "PNS",
    "José María Pino Suárez": "PNS",
    "Jalisco": "JAL",
    "La Gloria": "GLR",
    "El Coco": "COC",
    "El Tule": "TUL",
    "Nahuapa": "NAH",
    "Benito Juarez": "BJZ",
    "Benito Juárez": "BJZ",
    "Centro": "CTR",
    "Campamento SAGAR Colonia las Palmas": "SGR",
    "Campamento SAGAR": "SGR",
    "La Cruz de Loreto": "CRL",
}

# Reverse map: abbreviation → display name
ABBR_TO_ZONE = {
    "TML": "Tomatlan",
    "CBR": "La Cumbre",
    "PNS": "Jose Maria Pino Suarez",
    "GLR": "La Gloria",
    "COC": "El Coco",
    "TUL": "El Tule",
    "NAH": "Nahuapa",
    "BJZ": "Benito Juarez",
    "CTR": "Centro",
    "SGR": "Campamento SAGAR",
    "CRL": "La Cruz de Loreto",
    "JAL": "Jalisco",
}


def _get_zone_abbr(zone_name: str) -> str:
    """Obtiene la abreviatura de zona. Intenta match exacto, luego parcial."""
    if zone_name in ZONE_ABBREVIATIONS:
        return ZONE_ABBREVIATIONS[zone_name]
    # Partial match (case-insensitive)
    zone_lower = zone_name.lower()
    for name, abbr in ZONE_ABBREVIATIONS.items():
        if name.lower() in zone_lower or zone_lower in name.lower():
            return abbr
    return "AUR"  # Fallback


def _generate_service_id(zone_abbr: str, client_id: str | int) -> str:
    """Genera ID de servicio legible: ABBR-ID (ej: CBR-213)."""
    return f"{zone_abbr}-{client_id}"


async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo de vinculacion."""
    user = update.effective_user
    if not user:
        return ConversationHandler.END

    # Check if already linked
    db = context.bot_data["db"]
    link = await db.get_customer_link(user.id)
    if link:
        msg = update.message or update.callback_query.message
        if update.callback_query:
            await update.callback_query.answer()
        sid = link.get("service_id") or "sin asignar"
        await msg.reply_text(
            f"Ya estas vinculado como *{link['crm_client_name']}*\n"
            f"Tu ID de servicio: `{sid}`\n\n"
            "Si necesitas cambiar tu cuenta, contacta a soporte.",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    msg = update.message or update.callback_query.message
    if update.callback_query:
        await update.callback_query.answer()

    await msg.reply_text(
        "*Vinculacion de cuenta*\n\n"
        "Escribe tu *nombre completo* tal como esta registrado en AURALINK.\n\n"
        "Ejemplo: Juan Perez Garcia\n\n"
        "Escribe /cancelar para cancelar.",
        parse_mode="Markdown",
    )
    return WAITING_NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el nombre y muestra teclado de zonas."""
    if not update.message:
        return ConversationHandler.END

    query = update.message.text.strip()
    if len(query) < 3:
        await update.message.reply_text("Por favor escribe al menos 3 caracteres.")
        return WAITING_NAME

    context.user_data["reg_name"] = query

    await update.message.reply_text(
        f"Nombre: *{query}*\n\n"
        "Ahora selecciona tu *zona* o colonia:",
        parse_mode="Markdown",
        reply_markup=keyboards.zone_selection(),
    )
    return WAITING_ZONE


async def receive_zone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe zona seleccionada, busca match en CRM filtrado por zona."""
    query = update.callback_query
    if not query:
        return ConversationHandler.END

    await query.answer()
    data = query.data

    if not data or not data.startswith("zone_"):
        return WAITING_ZONE

    zone_abbr = data[5:]  # Remove "zone_" prefix
    name_query = context.user_data.get("reg_name", "")

    if zone_abbr == "OTHER":
        await query.message.reply_text(
            "Escribe el nombre de tu zona o colonia:"
        )
        context.user_data["reg_waiting_custom_zone"] = True
        return WAITING_ZONE

    zone_name = ABBR_TO_ZONE.get(zone_abbr, zone_abbr)
    context.user_data["reg_zone_abbr"] = zone_abbr
    context.user_data["reg_zone_name"] = zone_name

    await _search_and_show_matches(query.message, context, name_query, zone_name, zone_abbr)
    return WAITING_CONFIRM


async def receive_custom_zone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe zona escrita manualmente."""
    if not update.message:
        return ConversationHandler.END

    if not context.user_data.get("reg_waiting_custom_zone"):
        # Not waiting for custom zone, re-enter name flow
        return await receive_name(update, context)

    context.user_data.pop("reg_waiting_custom_zone", None)
    zone_text = update.message.text.strip()
    zone_abbr = _get_zone_abbr(zone_text)
    zone_name = zone_text

    context.user_data["reg_zone_abbr"] = zone_abbr
    context.user_data["reg_zone_name"] = zone_name

    name_query = context.user_data.get("reg_name", "")
    await _search_and_show_matches(update.message, context, name_query, zone_name, zone_abbr)
    return WAITING_CONFIRM


async def _search_and_show_matches(message, context, name_query: str, zone_name: str, zone_abbr: str):
    """Busca clientes CRM, filtra por zona, y muestra matches."""
    crm = context.bot_data["uisp_crm"]
    nms = context.bot_data["uisp_nms"]
    db = context.bot_data["db"]
    clients = await crm.get_clients()

    # Get already-linked client IDs to exclude them
    all_links = await db.get_all_customer_links()
    linked_ids = {str(link["crm_client_id"]) for link in all_links}

    # Score all clients by name match, excluding already-linked
    scored = []
    for c in clients:
        if str(c.get("id", "")) in linked_ids:
            continue
        client_name = crm.get_client_name(c)
        score = fuzz.token_sort_ratio(name_query.lower(), client_name.lower())
        if score >= 55:
            scored.append((score, c, client_name))

    scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        await message.reply_text(
            f"No encontre cuentas similares a '*{name_query}*' en ninguna zona.\n\n"
            "Verifica que tu nombre sea el mismo que usaste al contratar.\n"
            "Intenta de nuevo con /vincular o contacta a soporte.",
            parse_mode="Markdown",
        )
        return

    # Get top matches (up to 5) and enrich with service info
    top = scored[:5]
    match_details = []

    for score, client, client_name in top:
        client_id = str(client.get("id", ""))
        # Get service details
        services = await crm.get_client_services(client_id)
        plan = "Sin plan"
        svc_zone = ""
        for svc in services:
            if svc.get("status") in (0, 1):  # prepared/active
                plan = svc.get("servicePlanName") or "Sin plan"
                svc_zone = svc.get("city") or svc.get("street") or ""
                break

        # Get device IP from NMS endpoint linked to service
        device_ip = ""
        for svc in services:
            site_id = svc.get("unmsClientSiteId")
            if site_id:
                sites = await nms.get_sites()
                for site in sites:
                    if str(site.get("id")) == str(site_id):
                        # Find device at this site
                        devices = await nms.get_devices()
                        for d in devices:
                            d_site = (d.get("identification", {}).get("site", {}) or {}).get("id", "")
                            if str(d_site) == str(site_id):
                                device_ip = (d.get("ipAddress") or "").split("/")[0]
                                break
                        break
                break

        match_details.append({
            "client_id": client_id,
            "name": client_name,
            "score": score,
            "plan": plan,
            "zone": svc_zone or zone_name,
            "ip": device_ip,
        })

    # Store for confirmation step
    context.user_data["reg_matches"] = match_details

    if len(match_details) == 1 and match_details[0]["score"] >= 80:
        # High confidence single match — show directly for confirmation
        m = match_details[0]
        sid = _generate_service_id(zone_abbr, m["client_id"])
        ip_line = f"Antena IP: `{m['ip']}`\n" if m["ip"] else ""

        await message.reply_text(
            f"*Encontre tu cuenta:*\n\n"
            f"Nombre: *{m['name']}*\n"
            f"Zona: *{m['zone']}*\n"
            f"Plan: *{m['plan']}*\n"
            f"{ip_line}"
            f"ID de servicio: `{sid}`\n\n"
            f"Es esta tu cuenta?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Si, es mi cuenta", callback_data=f"reg_confirm_{m['client_id']}"),
                 InlineKeyboardButton("No", callback_data="reg_retry")],
            ]),
        )
    else:
        # Multiple matches — show top as buttons
        buttons = []
        for m in match_details[:3]:
            label = f"{m['name']}"
            if m["zone"]:
                label += f" ({m['zone']})"
            buttons.append([InlineKeyboardButton(label, callback_data=f"reg_pick_{m['client_id']}")])
        buttons.append([InlineKeyboardButton("Ninguno de estos", callback_data="reg_retry")])

        await message.reply_text(
            "Encontre varias cuentas similares.\n"
            "Selecciona la tuya:",
            reply_markup=InlineKeyboardMarkup(buttons),
        )


async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja confirmacion o seleccion de cliente."""
    query = update.callback_query
    if not query:
        return ConversationHandler.END

    await query.answer()
    data = query.data

    if data == "reg_retry":
        await query.message.reply_text(
            "No hay problema. Intenta de nuevo con /vincular o contacta a soporte."
        )
        return ConversationHandler.END

    # Extract client_id from reg_confirm_XXX or reg_pick_XXX
    client_id = None
    if data.startswith("reg_confirm_"):
        client_id = data[12:]
    elif data.startswith("reg_pick_"):
        client_id = data[9:]

    if not client_id:
        return WAITING_CONFIRM

    # If picked from list, show details for confirmation first
    if data.startswith("reg_pick_"):
        matches = context.user_data.get("reg_matches", [])
        zone_abbr = context.user_data.get("reg_zone_abbr", "AUR")
        m = next((m for m in matches if m["client_id"] == client_id), None)
        if m:
            sid = _generate_service_id(zone_abbr, client_id)
            ip_line = f"Antena IP: `{m['ip']}`\n" if m.get("ip") else ""

            await query.message.reply_text(
                f"*Confirma tu cuenta:*\n\n"
                f"Nombre: *{m['name']}*\n"
                f"Zona: *{m.get('zone', '')}*\n"
                f"Plan: *{m.get('plan', 'Sin plan')}*\n"
                f"{ip_line}"
                f"ID de servicio: `{sid}`\n\n"
                f"Es esta tu cuenta?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Si, es mi cuenta", callback_data=f"reg_confirm_{client_id}"),
                     InlineKeyboardButton("No", callback_data="reg_retry")],
                ]),
            )
            return WAITING_CONFIRM

    # --- Confirmed: link account ---
    user = update.effective_user
    crm = context.bot_data["uisp_crm"]
    db = context.bot_data["db"]

    client = await crm.get_client(client_id)
    if not client:
        await query.message.reply_text("Error al obtener datos del cliente. Intenta de nuevo con /vincular.")
        return ConversationHandler.END

    client_name = crm.get_client_name(client)
    zone_abbr = context.user_data.get("reg_zone_abbr", "AUR")
    service_id = _generate_service_id(zone_abbr, client_id)

    # Write userIdent to CRM
    ident_ok = await crm.update_client_ident(client_id, service_id)
    if ident_ok:
        log.info("CRM userIdent actualizado: cliente %s -> %s", client_id, service_id)
    else:
        log.warning("No se pudo actualizar userIdent para cliente %s", client_id)

    # Save link in local DB
    await db.link_customer(
        telegram_user_id=user.id,
        telegram_username=user.username,
        crm_client_id=client_id,
        crm_client_name=client_name,
        service_id=service_id,
    )

    # Update onboarding tracking
    await db.mark_onboarding_linked(client_id)

    log.info("Cliente vinculado: Telegram %d -> CRM %s (%s) service_id=%s",
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

    # Cleanup user_data
    for key in ["reg_name", "reg_zone_abbr", "reg_zone_name", "reg_matches", "reg_waiting_custom_zone"]:
        context.user_data.pop(key, None)

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela el flujo de registro."""
    if update.message:
        await update.message.reply_text("Registro cancelado. Usa /vincular cuando quieras intentar de nuevo.")
    # Cleanup
    for key in ["reg_name", "reg_zone_abbr", "reg_zone_name", "reg_matches", "reg_waiting_custom_zone"]:
        context.user_data.pop(key, None)
    return ConversationHandler.END


def get_registration_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("vincular", start_registration),
            CallbackQueryHandler(start_registration, pattern="^cmd_vincular$"),
        ],
        states={
            WAITING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name),
            ],
            WAITING_ZONE: [
                CallbackQueryHandler(receive_zone, pattern="^zone_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_custom_zone),
            ],
            WAITING_CONFIRM: [
                CallbackQueryHandler(handle_confirm, pattern="^reg_"),
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, _timeout_handler),
            ],
        },
        fallbacks=[
            CommandHandler("cancelar", cancel),
        ],
        conversation_timeout=300,
    )


async def _timeout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Notifica al usuario que la conversacion expiro."""
    msg = update.message or (update.callback_query.message if update.callback_query else None)
    if msg:
        await msg.reply_text(
            "La vinculacion se cancelo por inactividad (5 minutos).\n"
            "Usa /vincular para intentar de nuevo."
        )
    for key in ["reg_name", "reg_zone_abbr", "reg_zone_name", "reg_matches", "reg_waiting_custom_zone"]:
        context.user_data.pop(key, None)
    return ConversationHandler.END
