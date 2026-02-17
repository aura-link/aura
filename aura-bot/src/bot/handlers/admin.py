"""Handlers de administrador: /red, /clientes, /buscar, /dispositivos, /pppoe, /diagnostico, /caidas, /admin."""

from telegram import Update
from telegram.ext import ContextTypes
from src.bot.roles import is_admin
from src.bot import keyboards
from src.utils.formatting import status_emoji, format_signal, format_uptime, format_mxn, truncate
from src.utils.logger import log


async def _reply(update: Update, text: str, **kwargs):
    """Reply that works for both commands and callback queries."""
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, **kwargs)
    elif update.message:
        await update.message.reply_text(text, **kwargs)


def _admin_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_admin(user.id):
            await _reply(update, "⛔ Acceso denegado. Solo administradores.")
            return
        return await func(update, context)
    return wrapper


@_admin_required
async def red_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Overview general de la red."""
    nms = context.bot_data["uisp_nms"]
    crm = context.bot_data["uisp_crm"]
    mk = context.bot_data.get("mikrotik")

    devices_ov = await nms.get_devices_overview()
    clients_ov = await crm.get_clients_overview()

    text = (
        "🌐 *Estado de la Red AURALINK*\n\n"
        f"📡 *Dispositivos:*\n"
        f"  🟢 Online: {devices_ov['online']}\n"
        f"  🔴 Offline: {devices_ov['offline']}\n"
        f"  ⚪ Unknown: {devices_ov['unknown']}\n"
        f"  Total: {devices_ov['total']}\n\n"
        f"👥 *Clientes CRM:*\n"
        f"  Activos: {clients_ov['active']}\n"
        f"  Inactivos: {clients_ov['inactive']}\n"
        f"  Con saldo: {clients_ov['with_balance']}\n"
        f"  Total: {clients_ov['total']}\n"
    )

    if mk:
        try:
            pppoe = await mk.get_active_sessions()
            text += f"\n📊 *PPPoE activos:* {len(pppoe)}\n"
        except Exception as e:
            log.warning("MikroTik error en /red: %s", e)

    await _reply(update, text, parse_mode="Markdown")


@_admin_required
async def clientes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resumen de clientes CRM."""
    crm = context.bot_data["uisp_crm"]
    clients = await crm.get_clients()

    if not clients:
        await _reply(update, "No se pudieron obtener clientes.")
        return

    active = [c for c in clients if c.get("isActive")]
    with_balance = sorted(
        [c for c in active if (c.get("accountBalance") or 0) > 0],
        key=lambda c: c.get("accountBalance", 0),
        reverse=True,
    )

    text = f"👥 *Clientes AURALINK* ({len(active)} activos / {len(clients)} total)\n\n"

    if with_balance:
        text += "💰 *Top clientes con saldo pendiente:*\n"
        for c in with_balance[:10]:
            name = crm.get_client_name(c)
            bal = format_mxn(c.get("accountBalance", 0))
            text += f"  • {name}: {bal}\n"

    await _reply(update, truncate(text), parse_mode="Markdown")


@_admin_required
async def buscar_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buscar cliente por nombre."""
    if not context.args:
        await _reply(update, "Uso: /buscar <nombre>")
        return

    query = " ".join(context.args)
    crm = context.bot_data["uisp_crm"]
    results = await crm.search_clients(query)

    if not results:
        await _reply(update, f"No se encontraron clientes con '{query}'.")
        return

    text = f"🔍 *Resultados para '{query}':*\n\n"
    for c in results[:10]:
        name = crm.get_client_name(c)
        status = "✅" if c.get("isActive") else "❌"
        bal = format_mxn(c.get("accountBalance", 0))
        text += f"  {status} {name} — Saldo: {bal}\n"

    await _reply(update, truncate(text), parse_mode="Markdown")


@_admin_required
async def dispositivos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista dispositivos offline."""
    nms = context.bot_data["uisp_nms"]
    offline = await nms.get_offline_devices()

    if not offline:
        await _reply(update, "✅ Todos los dispositivos estan online.")
        return

    text = f"🔴 *Dispositivos offline ({len(offline)}):*\n\n"
    for d in offline[:20]:
        name = d.get("identification", {}).get("name") or d.get("name", "Sin nombre")
        ip = (d.get("ipAddress") or "sin IP").split("/")[0]
        model = d.get("identification", {}).get("model") or ""
        text += f"  • {name} ({model}) — {ip}\n"

    if len(offline) > 20:
        text += f"\n... y {len(offline) - 20} mas"

    await _reply(update, truncate(text), parse_mode="Markdown")


@_admin_required
async def pppoe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sesiones PPPoE activas."""
    mk = context.bot_data.get("mikrotik")
    if not mk:
        await _reply(update, "⚠️ MikroTik no esta configurado.")
        return

    try:
        sessions = await mk.get_active_sessions()
    except Exception as e:
        await _reply(update, f"❌ Error conectando a MikroTik: {e}")
        return

    text = f"📊 *Sesiones PPPoE activas: {len(sessions)}*\n\n"
    for s in sessions[:20]:
        name = s.get("name", "")
        address = s.get("address", "")
        uptime = s.get("uptime", "")
        text += f"  • {name} — {address} ({uptime})\n"

    if len(sessions) > 20:
        text += f"\n... y {len(sessions) - 20} mas"

    await _reply(update, truncate(text), parse_mode="Markdown")


@_admin_required
async def diagnostico_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ping desde MikroTik a una IP."""
    if not context.args:
        await _reply(update, "Uso: /diagnostico <ip>")
        return

    ip = context.args[0]
    mk = context.bot_data.get("mikrotik")
    if not mk:
        await _reply(update, "⚠️ MikroTik no esta configurado.")
        return

    await _reply(update, f"🏓 Haciendo ping a {ip}...")

    try:
        result = await mk.ping(ip)
        if result.get("success"):
            text = (
                f"🏓 *Ping a {ip}:*\n\n"
                f"  Enviados: {result.get('sent', 0)}\n"
                f"  Recibidos: {result.get('received', 0)}\n"
                f"  Perdidos: {result.get('lost', 0)}\n"
                f"  Promedio: {result.get('avg_rtt', 'N/A')} ms"
            )
        else:
            text = f"❌ Sin respuesta de {ip}"
    except Exception as e:
        text = f"❌ Error: {e}"

    await _reply(update, text, parse_mode="Markdown")


@_admin_required
async def caidas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Outages activos en UISP."""
    nms = context.bot_data["uisp_nms"]
    outages = await nms.get_active_outages()

    if not outages:
        await _reply(update, "✅ No hay caidas activas en este momento.")
        return

    text = f"⚠️ *Caidas activas ({len(outages)}):*\n\n"
    for o in outages[:10]:
        device = o.get("device", {}) or {}
        name = device.get("name") or "Desconocido"
        site = (o.get("site", {}) or {}).get("name", "")
        start = o.get("startTimestamp", "")
        text += f"  • {name}"
        if site:
            text += f" ({site})"
        if start:
            text += f" — desde {start[:16]}"
        text += "\n"

    await _reply(update, truncate(text), parse_mode="Markdown")


@_admin_required
async def tplink_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista dispositivos TP-Link detectados via CDP en MikroTik."""
    mk = context.bot_data.get("mikrotik")
    if not mk:
        await _reply(update, "⚠️ MikroTik no esta configurado.")
        return

    try:
        neighbors = await mk.get_neighbors()
    except Exception as e:
        await _reply(update, f"❌ Error conectando a MikroTik: {e}")
        return

    tplinks = [n for n in neighbors if "tp-link" in (n.get("platform") or "").lower()]

    if not tplinks:
        await _reply(update, "No se detectaron dispositivos TP-Link en el neighbor list.")
        return

    # Agrupar por modelo
    by_model: dict[str, list[dict]] = {}
    for n in tplinks:
        platform = n.get("platform") or "TP-LINK"
        by_model.setdefault(platform, []).append(n)

    text = f"📡 *TP-Link detectados: {len(tplinks)}*\n"

    for model, devices in sorted(by_model.items()):
        text += f"\n*{model}* ({len(devices)}):\n"
        for d in sorted(devices, key=lambda x: x.get("identity") or ""):
            identity = d.get("identity") or "sin nombre"
            addr = d.get("address") or ""
            iface = d.get("interface-name") or d.get("interface") or ""
            version = d.get("version") or ""
            icon = "🟢" if addr else "⚪"
            line = f"  {icon} {identity}"
            if addr:
                line += f" — {addr}"
            if version:
                line += f" (v{version})"
            if iface:
                line += f" [{iface}]"
            text += line + "\n"

    await _reply(update, truncate(text), parse_mode="Markdown")


@_admin_required
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Panel completo de administracion con todas las herramientas."""
    text = (
        "🛠 *Panel de Administracion AURALINK*\n\n"
        "Selecciona una opcion:"
    )
    kb = keyboards.admin_panel()
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            text, parse_mode="Markdown", reply_markup=kb
        )
    elif update.message:
        await update.message.reply_text(
            text, parse_mode="Markdown", reply_markup=kb
        )
