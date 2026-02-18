"""Handlers para onboarding de clientes: /sinvincular, /progreso, /mensaje."""

import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.roles import is_admin
from src.utils.logger import log

# Zone abbreviation → display name
ZONE_NAMES = {
    "TML": "Tomatlan", "CBR": "La Cumbre", "PNS": "Pino Suarez",
    "GLR": "La Gloria", "COC": "El Coco", "TUL": "El Tule",
    "NAH": "Nahuapa", "BJZ": "Benito Juarez", "CTR": "Centro",
    "SGR": "SAGAR", "CRL": "Cruz de Loreto", "JAL": "Jalisco",
    "OTR": "Otra zona",
}

# Keywords in CRM city/street → zone abbreviation
ZONE_KEYWORDS = {
    "tomatlan": "TML", "tomatlán": "TML",
    "cumbre": "CBR",
    "pino suarez": "PNS", "pino suárez": "PNS",
    "gloria": "GLR",
    "coco": "COC",
    "tule": "TUL",
    "nahuapa": "NAH",
    "juarez": "BJZ", "juárez": "BJZ", "benito": "BJZ",
    "centro": "CTR",
    "sagar": "SGR", "campamento": "SGR",
    "cruz": "CRL", "loreto": "CRL",
    "jalisco": "JAL",
}

WHATSAPP_MESSAGE = """Hola! Soy Carlos de AURALINK.

Te escribo para avisarte que ya tenemos un *asistente virtual por Telegram* llamado *AURA* que te permite:

- Consultar tu saldo y pagos pendientes
- Ver el estado de tu servicio e internet
- Reportar problemas automaticamente
- Enviar comprobantes de pago por foto (y se registran al instante)
- Recibir avisos importantes de la red

*Como activarlo (2 minutos):*

1. Abre Telegram (si no lo tienes, descargalo gratis)
2. Busca: *@auralinkmonitor_bot*
3. Presiona *Iniciar*
4. Presiona *Vincular mi cuenta*
5. Escribe tu nombre completo
6. Selecciona tu zona
7. Confirma tus datos

Y listo! Ya puedes consultar tu saldo, enviar comprobantes de pago y mas.

Es importante que lo actives antes del 1 de abril, porque a partir de esa fecha los avisos de cobro y comprobantes se manejan por ahi.

Cualquier duda me escribes!"""


async def _reply(update: Update, text: str, reply_markup=None):
    """Helper: reply to message or callback query."""
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            text, parse_mode="Markdown", reply_markup=reply_markup,
        )
    elif update.message:
        await update.message.reply_text(
            text, parse_mode="Markdown", reply_markup=reply_markup,
        )


def _detect_zone(services: list[dict]) -> str:
    """Detect zone from CRM service city/street fields."""
    for svc in services:
        for field in ("city", "street", "street2"):
            val = (svc.get(field) or "").lower()
            if not val:
                continue
            for keyword, abbr in ZONE_KEYWORDS.items():
                if keyword in val:
                    return abbr
    return "OTR"


async def _sync_onboarding(db, crm) -> dict:
    """Sync CRM clients with onboarding tracking table. Returns stats."""
    all_clients = await crm.get_clients()
    all_links = await db.get_all_customer_links()
    linked_ids = {link["crm_client_id"] for link in all_links}

    synced = 0
    newly_linked = 0

    for client in all_clients:
        client_id = str(client.get("id", ""))
        if not client_id or not client.get("isActive"):
            continue

        client_name = crm.get_client_name(client)

        if client_id in linked_ids:
            # Already linked — mark in onboarding
            await db.upsert_onboarding(client_id, client_name, "---")
            await db.mark_onboarding_linked(client_id)
            newly_linked += 1
            continue

        # Detect zone from services
        services = await crm.get_client_services(client_id)
        zone = _detect_zone(services)

        await db.upsert_onboarding(client_id, client_name, zone)
        synced += 1

        # Rate limit
        await asyncio.sleep(0.05)

    await db.onboarding_sync_committed()
    return {"synced": synced, "linked": newly_linked, "total": len(all_clients)}


async def sinvincular_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: muestra clientes sin vincular agrupados por zona."""
    user = update.effective_user
    if not user or not is_admin(user.id):
        return

    db = context.bot_data["db"]
    crm = context.bot_data["uisp_crm"]

    await _reply(update, "Sincronizando clientes CRM con onboarding...")

    # Sync first
    result = await _sync_onboarding(db, crm)

    # Get zone summary
    zones = await db.get_onboarding_by_zone()
    stats = await db.get_onboarding_stats()

    total = stats["pending"] + stats["contacted"] + stats["linked"] + stats["skipped"]
    pct_linked = (stats["linked"] / total * 100) if total > 0 else 0

    text = (
        f"*Onboarding de Clientes*\n\n"
        f"Total CRM activos: *{total}*\n"
        f"Vinculados: *{stats['linked']}* ({pct_linked:.0f}%)\n"
        f"Contactados (sin vincular): *{stats['contacted']}*\n"
        f"Pendientes de contactar: *{stats['pending']}*\n"
        f"Omitidos: *{stats['skipped']}*\n\n"
        f"Selecciona una zona para ver clientes pendientes:"
    )

    # Zone buttons (only zones with pending clients)
    buttons = []
    for z in zones:
        if z["pending"] <= 0 and z["contacted"] <= 0:
            continue
        zone_name = ZONE_NAMES.get(z["zone"], z["zone"])
        label = f"{zone_name} ({z['pending']} pend"
        if z["contacted"] > 0:
            label += f", {z['contacted']} cont"
        label += ")"
        buttons.append([InlineKeyboardButton(label, callback_data=f"onb_zone_{z['zone']}")])

    buttons.append([InlineKeyboardButton("Mensaje WhatsApp", callback_data="onb_whatsapp")])
    buttons.append([InlineKeyboardButton("Progreso por zona", callback_data="cmd_progreso")])

    msg = update.callback_query.message if update.callback_query else update.message
    await msg.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))


async def progreso_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: dashboard de progreso de vinculacion."""
    user = update.effective_user
    if not user or not is_admin(user.id):
        return

    db = context.bot_data["db"]
    zones = await db.get_onboarding_by_zone()
    stats = await db.get_onboarding_stats()

    total = stats["pending"] + stats["contacted"] + stats["linked"] + stats["skipped"]

    text = "*Progreso de Vinculacion*\n\n"

    for z in zones:
        zone_name = ZONE_NAMES.get(z["zone"], z["zone"])
        zt = z["total"]
        linked = z["linked"]
        pct = (linked / zt * 100) if zt > 0 else 0

        # Progress bar (10 chars)
        filled = round(pct / 10)
        bar = "█" * filled + "░" * (10 - filled)

        text += f"*{zone_name}*: {bar} {pct:.0f}%\n"
        text += f"  {linked}/{zt} vinculados"
        if z["contacted"] > 0:
            text += f", {z['contacted']} contactados"
        if z["pending"] > 0:
            text += f", {z['pending']} pendientes"
        text += "\n\n"

    pct_total = (stats["linked"] / total * 100) if total > 0 else 0
    bar_total = "█" * round(pct_total / 10) + "░" * (10 - round(pct_total / 10))
    text += f"*TOTAL*: {bar_total} *{pct_total:.0f}%* ({stats['linked']}/{total})\n"

    buttons = [[InlineKeyboardButton("Actualizar", callback_data="cmd_progreso")],
               [InlineKeyboardButton("Ver pendientes", callback_data="cmd_sinvincular")]]

    await _reply(update, text, InlineKeyboardMarkup(buttons))


async def handle_onboarding_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle onboarding-related callbacks."""
    query = update.callback_query
    if not query or not query.data:
        return
    user = update.effective_user
    if not user or not is_admin(user.id):
        await query.answer("Solo admins")
        return

    data = query.data
    db = context.bot_data["db"]

    # Show clients in a zone (with optional page: onb_zone_TML or onb_zone_TML_p2)
    if data.startswith("onb_zone_"):
        rest = data[9:]  # after "onb_zone_"
        page = 0
        if "_p" in rest:
            parts = rest.rsplit("_p", 1)
            zone = parts[0]
            try:
                page = int(parts[1])
            except ValueError:
                page = 0
        else:
            zone = rest
        await query.answer()
        await _show_zone_clients(query.message, db, zone, page)
        return

    # Mark client as contacted
    if data.startswith("onb_contacted_"):
        client_id = data.replace("onb_contacted_", "")
        await db.mark_contacted(client_id, via="whatsapp")
        await query.answer("Marcado como contactado")
        # Refresh the zone view
        # Get zone from DB
        cursor = await db.db.execute(
            "SELECT zone FROM onboarding_tracking WHERE crm_client_id = ?",
            (client_id,),
        )
        row = await cursor.fetchone()
        if row:
            await _show_zone_clients(query.message, db, row[0])
        return

    # Skip client
    if data.startswith("onb_skip_"):
        client_id = data.replace("onb_skip_", "")
        await db.mark_onboarding_skipped(client_id, "Omitido por admin")
        await query.answer("Cliente omitido")
        cursor = await db.db.execute(
            "SELECT zone FROM onboarding_tracking WHERE crm_client_id = ?",
            (client_id,),
        )
        row = await cursor.fetchone()
        if row:
            await _show_zone_clients(query.message, db, row[0])
        return

    # Show WhatsApp message
    if data == "onb_whatsapp":
        await query.answer()
        await query.message.reply_text(
            "*Mensaje para enviar por WhatsApp:*\n\n"
            "_(Copia y pega el siguiente mensaje a tus clientes)_\n\n"
            "---\n\n" + WHATSAPP_MESSAGE,
            parse_mode="Markdown",
        )
        return

    # Mark all in zone as contacted
    if data.startswith("onb_allzone_"):
        zone = data.replace("onb_allzone_", "")
        clients = await db.get_uncontacted_by_zone(zone)
        for c in clients:
            await db.mark_contacted(c["crm_client_id"], via="whatsapp")
        await query.answer(f"{len(clients)} clientes marcados")
        await _show_zone_clients(query.message, db, zone)
        return

    # Show contacted clients in zone
    if data.startswith("onb_showcontacted_"):
        zone = data.replace("onb_showcontacted_", "")
        await query.answer()
        contacted = await db.get_contacted_unlinked_by_zone(zone)
        if not contacted:
            await query.message.reply_text("No hay clientes contactados pendientes en esta zona.")
            return
        text = f"*Contactados sin vincular — {ZONE_NAMES.get(zone, zone)}:*\n\n"
        for c in contacted:
            text += f"- {c['crm_client_name']} (ID {c['crm_client_id']})\n"
        text += f"\n_Total: {len(contacted)} clientes contactados esperando vincularse_"
        await query.message.reply_text(text, parse_mode="Markdown")
        return


async def _show_zone_clients(message, db, zone: str, page: int = 0):
    """Show uncontacted clients in a zone with action buttons."""
    zone_name = ZONE_NAMES.get(zone, zone)
    pending = await db.get_uncontacted_by_zone(zone)
    contacted = await db.get_contacted_unlinked_by_zone(zone)

    PAGE_SIZE = 8
    start = page * PAGE_SIZE
    page_clients = pending[start:start + PAGE_SIZE]

    text = f"*{zone_name}* — {len(pending)} pendientes, {len(contacted)} contactados\n\n"

    if not page_clients and not contacted:
        text += "Todos los clientes de esta zona ya fueron contactados o vinculados."
        await message.reply_text(text, parse_mode="Markdown")
        return

    buttons = []

    if page_clients:
        text += "*Pendientes de contactar:*\n"
        for i, c in enumerate(page_clients, start + 1):
            text += f"{i}. {c['crm_client_name']} _(ID {c['crm_client_id']})_\n"
            buttons.append([
                InlineKeyboardButton(
                    f"Contactado: {c['crm_client_name']}",
                    callback_data=f"onb_contacted_{c['crm_client_id']}"
                ),
                InlineKeyboardButton(
                    "Omitir",
                    callback_data=f"onb_skip_{c['crm_client_id']}"
                ),
            ])

    # Pagination
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("< Anterior", callback_data=f"onb_zone_{zone}_p{page-1}"))
    if start + PAGE_SIZE < len(pending):
        nav_row.append(InlineKeyboardButton("Siguiente >", callback_data=f"onb_zone_{zone}_p{page+1}"))
    if nav_row:
        buttons.append(nav_row)

    # Batch actions
    action_row = []
    if pending:
        action_row.append(InlineKeyboardButton(
            f"Marcar todos ({len(pending)})",
            callback_data=f"onb_allzone_{zone}"
        ))
    if contacted:
        action_row.append(InlineKeyboardButton(
            f"Ver contactados ({len(contacted)})",
            callback_data=f"onb_showcontacted_{zone}"
        ))
    if action_row:
        buttons.append(action_row)

    buttons.append([InlineKeyboardButton("Volver", callback_data="cmd_sinvincular")])

    await message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def mensaje_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: muestra el mensaje de WhatsApp para copiar."""
    user = update.effective_user
    if not user or not is_admin(user.id):
        return

    await _reply(
        update,
        "*Mensaje para enviar por WhatsApp:*\n\n"
        "_(Copia y pega el siguiente mensaje a tus clientes)_\n\n"
        "---\n\n" + WHATSAPP_MESSAGE,
    )
