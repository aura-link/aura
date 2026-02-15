"""Handlers admin para monitoreo: /zonas, /incidentes, /monitor, /mantenimiento."""

import time
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.bot.roles import is_admin
from src.utils.logger import log


def _admin_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user or not is_admin(user.id):
            msg = update.message or (update.callback_query and update.callback_query.message)
            if msg:
                await msg.reply_text("⛔ Solo administradores pueden usar este comando.")
            return
        return await func(update, context)
    return wrapper


async def _reply(update: Update, text: str, **kwargs):
    """Responde a mensaje o callback query."""
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, **kwargs)
    elif update.message:
        await update.message.reply_text(text, **kwargs)


@_admin_required
async def zonas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista zonas de infraestructura con clientes asociados."""
    zone_mapper = context.bot_data.get("zone_mapper")
    if not zone_mapper:
        await _reply(update, "❌ Monitor no disponible.")
        return

    zones = await zone_mapper.get_zone_summary()
    if not zones:
        await _reply(update, "📍 No hay mapeo de zonas. El monitor lo construira automaticamente.")
        return

    lines = ["📍 *Zonas de infraestructura:*\n"]
    for z in zones:
        name = z.get("infra_site_name", "Sin nombre")
        endpoints = z.get("total_endpoints", 0)
        clients = z.get("total_clients", 0)
        lines.append(f"• *{name}*: {endpoints} endpoints, {clients} clientes CRM")

    lines.append(f"\n_Total: {len(zones)} zonas_")
    await _reply(update, "\n".join(lines), parse_mode="Markdown")


@_admin_required
async def incidentes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra incidentes activos y recientes."""
    db = context.bot_data["db"]

    active = await db.get_active_incidents()
    recent = await db.get_recent_incidents(limit=5)

    lines = ["🚨 *Incidentes:*\n"]

    if active:
        lines.append("*Activos:*")
        for inc in active:
            name = inc.get("device_name", "?")
            zone = inc.get("site_name", "?")
            affected = inc.get("affected_clients", 0)
            started = inc.get("started_at", "")
            try:
                st = datetime.fromisoformat(started)
                started_fmt = st.strftime("%d/%m %H:%M")
            except (ValueError, TypeError):
                started_fmt = started
            lines.append(f"🔴 *{name}* — zona {zone}")
            lines.append(f"   👥 {affected} clientes | 🕐 desde {started_fmt}")
    else:
        lines.append("✅ No hay incidentes activos.\n")

    # Recientes resueltos
    resolved = [i for i in recent if i.get("status") == "resolved"]
    if resolved:
        lines.append("\n*Resueltos recientemente:*")
        for inc in resolved[:3]:
            name = inc.get("device_name", "?")
            zone = inc.get("site_name", "?")
            resolved_at = inc.get("resolved_at", "")
            try:
                rt = datetime.fromisoformat(resolved_at)
                resolved_fmt = rt.strftime("%d/%m %H:%M")
            except (ValueError, TypeError):
                resolved_fmt = resolved_at
            lines.append(f"🟢 {name} — zona {zone} (resuelto {resolved_fmt})")

    await _reply(update, "\n".join(lines), parse_mode="Markdown")


@_admin_required
async def monitor_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Estado del monitor de red."""
    monitor = context.bot_data.get("monitor")
    if not monitor:
        await _reply(update, "❌ Monitor no inicializado.")
        return

    status = "🟢 Corriendo" if monitor.is_running else "🔴 Detenido"
    tracked = monitor.tracked_devices
    last_poll = "Nunca"
    if monitor.last_poll_time:
        ago = int(time.time() - monitor.last_poll_time)
        last_poll = f"hace {ago}s"

    db = context.bot_data["db"]
    active_incidents = await db.get_active_incidents()
    pending_maint = await db.get_active_maintenance()

    from src import config
    lines = [
        "📊 *Estado del Monitor:*\n",
        f"Estado: {status}",
        f"Intervalo: {config.MONITOR_INTERVAL}s",
        f"Ultimo poll: {last_poll}",
        f"Dispositivos tracked: {tracked}",
        f"Incidentes activos: {len(active_incidents)}",
        f"Mantenimientos: {len(pending_maint)}",
        f"Cooldown notif: {config.NOTIFICATION_COOLDOWN}s",
    ]

    await _reply(update, "\n".join(lines), parse_mode="Markdown")


@_admin_required
async def mantenimiento_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lista mantenimientos o crea uno nuevo con /mantenimiento <zona> <horas>."""
    db = context.bot_data["db"]
    msg = update.message
    args = msg.text.split() if msg and msg.text else []

    if len(args) >= 3:
        # Crear mantenimiento: /mantenimiento <zona_nombre> <duracion_horas> [descripcion...]
        zone_search = args[1]
        try:
            duration_hours = float(args[2])
        except ValueError:
            await _reply(update, "❌ Duracion invalida. Uso: /mantenimiento <zona> <horas> [descripcion]")
            return

        description = " ".join(args[3:]) if len(args) > 3 else "Mantenimiento de red programado"

        # Buscar zona
        zone_mapper = context.bot_data.get("zone_mapper")
        if not zone_mapper:
            await _reply(update, "❌ Monitor no disponible.")
            return

        zones = await zone_mapper.get_zone_summary()
        matched_zone = None
        for z in zones:
            zname = (z.get("infra_site_name") or "").lower()
            if zone_search.lower() in zname:
                matched_zone = z
                break

        if not matched_zone:
            zone_names = [z.get("infra_site_name", "?") for z in zones[:10]]
            await _reply(
                update,
                f"❌ Zona '{zone_search}' no encontrada.\n\n"
                f"Zonas disponibles:\n" + "\n".join(f"• {n}" for n in zone_names),
            )
            return

        now = datetime.now()
        starts_at = now.isoformat()
        ends_at = (now + timedelta(hours=duration_hours)).isoformat()

        maintenance = context.bot_data.get("maintenance")
        mw_id = await maintenance.create(
            site_id=matched_zone["infra_site_id"],
            site_name=matched_zone.get("infra_site_name"),
            description=description,
            starts_at=starts_at,
            ends_at=ends_at,
            created_by=update.effective_user.id,
        )

        end_fmt = (now + timedelta(hours=duration_hours)).strftime("%d/%m/%Y %H:%M")
        clients = matched_zone.get("total_clients", 0)

        await _reply(
            update,
            f"🔧 *Mantenimiento #{mw_id} creado*\n\n"
            f"📍 Zona: *{matched_zone.get('infra_site_name')}*\n"
            f"⏱ Duracion: {duration_hours}h (hasta {end_fmt})\n"
            f"👥 Clientes en zona: {clients}\n"
            f"📝 {description}\n\n"
            f"Los clientes vinculados seran notificados automaticamente.",
            parse_mode="Markdown",
        )
        return

    # Sin argumentos: listar mantenimientos activos
    active = await db.get_active_maintenance()
    if not active:
        await _reply(
            update,
            "🔧 *Mantenimientos:*\n\n"
            "No hay mantenimientos activos.\n\n"
            "Para crear: /mantenimiento <zona> <horas> [descripcion]\n"
            "Ejemplo: `/mantenimiento gloria 2 Cambio de equipo`",
            parse_mode="Markdown",
        )
        return

    lines = ["🔧 *Mantenimientos activos:*\n"]
    buttons = []
    for mw in active:
        mw_id = mw["id"]
        site_name = mw.get("site_name", "General")
        desc = mw.get("description", "")
        ends = mw.get("ends_at", "")
        try:
            et = datetime.fromisoformat(ends)
            end_fmt = et.strftime("%d/%m %H:%M")
        except (ValueError, TypeError):
            end_fmt = ends
        lines.append(f"#{mw_id} *{site_name}* — hasta {end_fmt}")
        if desc:
            lines.append(f"   📝 {desc}")
        buttons.append([InlineKeyboardButton(
            f"❌ Cancelar #{mw_id}", callback_data=f"cancel_maint_{mw_id}"
        )])

    kb = InlineKeyboardMarkup(buttons) if buttons else None
    await _reply(update, "\n".join(lines), parse_mode="Markdown", reply_markup=kb)


@_admin_required
async def handle_cancel_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela un mantenimiento desde callback query."""
    query = update.callback_query
    if not query or not query.data:
        return

    try:
        mw_id = int(query.data.replace("cancel_maint_", ""))
    except ValueError:
        return

    await query.answer()
    maintenance = context.bot_data.get("maintenance")
    if maintenance:
        await maintenance.cancel(mw_id)
        await query.message.reply_text(f"✅ Mantenimiento #{mw_id} cancelado.")
