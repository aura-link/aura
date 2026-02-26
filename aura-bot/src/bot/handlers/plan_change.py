"""Handler /cambiarplan: solicitud de cambio de plan por cliente + aprobacion admin."""

from datetime import datetime
from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.roles import is_admin
from src.utils.logger import log
from src import config

TZ = ZoneInfo("America/Mexico_City")

# Display-friendly names for PPP profiles
PLAN_DISPLAY = {
    "$300 basico 3m/8m": "Básico $300 (3M/8M)",
    "$500 residencial 4m/12m": "Residencial $500 (4M/12M)",
    "$800 profesional 5m/15m": "Profesional $800 (5M/15M)",
    "$1000 empresarial 8m/20m": "Empresarial $1,000 (8M/20M)",
}

# Profiles excluded from the selection (internal/special)
EXCLUDED_PROFILES = {"default", "default_matriz", "morosos", "casas nodos", "20mb", "cruz"}

MONTH_NAMES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}


def _display_name(profile: str) -> str:
    """Get friendly display name for a profile."""
    return PLAN_DISPLAY.get(profile.lower(), profile)


def _next_month_first() -> tuple[str, str]:
    """Return (YYYY-MM-DD, display) for the 1st of next month."""
    now = datetime.now(TZ)
    month = now.month % 12 + 1
    year = now.year + (1 if month == 1 else 0)
    date_str = f"{year}-{month:02d}-01"
    display = f"1 de {MONTH_NAMES.get(month, str(month))} {year}"
    return date_str, display


async def cambiarplan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /cambiarplan command for clients."""
    user = update.effective_user
    if not user:
        return

    msg = update.message or (update.callback_query.message if update.callback_query else None)
    if update.callback_query:
        await update.callback_query.answer()
    if not msg:
        return

    db = context.bot_data["db"]
    mk = context.bot_data.get("mikrotik")

    # Must be linked
    link = await db.get_customer_link(user.id)
    if not link:
        await msg.reply_text(
            "Primero vincula tu cuenta con /vincular para poder solicitar un cambio de plan."
        )
        return

    # Check for existing pending request
    existing = await db.has_pending_plan_change(user.id)
    if existing:
        plan_display = _display_name(existing["requested_plan"])
        status_txt = "pendiente de aprobación" if existing["status"] == "pending" else "aprobada"
        await msg.reply_text(
            f"Ya tienes una solicitud {status_txt} para cambiar a *{plan_display}*.\n"
            f"Aplica el: {existing['effective_date']}\n\n"
            "Espera a que se procese antes de solicitar otro cambio.",
            parse_mode="Markdown",
        )
        return

    if not mk:
        await msg.reply_text("Servicio no disponible temporalmente. Intenta más tarde.")
        return

    # Find current plan
    client_name = link["crm_client_name"]
    secret = await mk.find_secret_by_name(client_name)
    if not secret:
        await msg.reply_text(
            "No encontré tu cuenta PPPoE. Contacta a soporte para asistencia."
        )
        return

    current_profile = secret.get("profile", "default")
    current_display = _display_name(current_profile)

    # Build plan selection buttons (exclude current + internal profiles)
    buttons = []
    for profile_key, display in PLAN_DISPLAY.items():
        if profile_key == current_profile.lower():
            continue
        buttons.append([InlineKeyboardButton(
            display,
            callback_data=f"planchange_select_{profile_key}",
        )])
    buttons.append([InlineKeyboardButton("Cancelar", callback_data="planchange_cancel")])

    await msg.reply_text(
        f"*Cambio de plan*\n\n"
        f"Tu plan actual: *{current_display}*\n\n"
        "Selecciona el plan al que deseas cambiar:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def handle_planchange_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all planchange_* callbacks."""
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data
    user = update.effective_user

    if data == "planchange_cancel":
        await query.answer("Cancelado")
        await query.edit_message_text("Solicitud de cambio cancelada.")
        return

    # Client selects a plan
    if data.startswith("planchange_select_"):
        await _handle_select(update, context)
        return

    # Admin approves
    if data.startswith("planchange_approve_"):
        await _handle_approve(update, context)
        return

    # Admin rejects
    if data.startswith("planchange_reject_"):
        await _handle_reject(update, context)
        return


async def _handle_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Client selected a new plan."""
    query = update.callback_query
    user = update.effective_user
    await query.answer()

    requested_plan = query.data[len("planchange_select_"):]
    requested_display = _display_name(requested_plan)

    db = context.bot_data["db"]
    mk = context.bot_data.get("mikrotik")

    link = await db.get_customer_link(user.id)
    if not link:
        await query.edit_message_text("Error: cuenta no vinculada.")
        return

    # Re-verify current plan
    client_name = link["crm_client_name"]
    secret = await mk.find_secret_by_name(client_name) if mk else None
    current_profile = secret.get("profile", "default") if secret else "desconocido"
    current_display = _display_name(current_profile)

    effective_date, effective_display = _next_month_first()

    # Create request in DB
    change_id = await db.create_plan_change_request(
        crm_client_id=link["crm_client_id"],
        client_name=client_name,
        telegram_user_id=user.id,
        current_plan=current_profile,
        requested_plan=requested_plan,
        effective_date=effective_date,
    )

    await query.edit_message_text(
        f"*Solicitud de cambio de plan enviada*\n\n"
        f"Plan actual: *{current_display}*\n"
        f"Plan solicitado: *{requested_display}*\n"
        f"Aplica a partir del: *{effective_display}*\n\n"
        "Un administrador revisará tu solicitud y te notificaremos cuando sea aprobada.",
        parse_mode="Markdown",
    )

    # Notify admin
    for admin_id in config.TELEGRAM_ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=(
                    f"📋 *Solicitud de cambio de plan*\n\n"
                    f"Cliente: *{client_name}*\n"
                    f"Plan actual: {current_display}\n"
                    f"Plan solicitado: *{requested_display}*\n"
                    f"Aplica: {effective_display}\n"
                    f"ID solicitud: #{change_id}"
                ),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Aprobar", callback_data=f"planchange_approve_{change_id}"),
                     InlineKeyboardButton("Rechazar", callback_data=f"planchange_reject_{change_id}")],
                ]),
            )
        except Exception as e:
            log.warning("Failed to notify admin %d about plan change: %s", admin_id, e)

    log.info("Plan change request #%d: %s wants %s -> %s (effective %s)",
             change_id, client_name, current_profile, requested_plan, effective_date)


async def _handle_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin approves plan change."""
    query = update.callback_query
    user = update.effective_user

    if not user or not is_admin(user.id):
        await query.answer("Solo administradores.")
        return

    change_id = int(query.data[len("planchange_approve_"):])
    db = context.bot_data["db"]

    change = await db.get_plan_change(change_id)
    if not change:
        await query.answer("Solicitud no encontrada.")
        return

    if change["status"] != "pending":
        await query.answer(f"Ya fue procesada: {change['status']}")
        return

    await db.update_plan_change(
        change_id,
        status="approved",
        approved_at=datetime.now(TZ).isoformat(),
    )

    await query.answer("Aprobado")
    effective_display = change["effective_date"]
    requested_display = _display_name(change["requested_plan"])

    await query.edit_message_text(
        f"✅ *Cambio aprobado*\n\n"
        f"Cliente: {change['client_name']}\n"
        f"Plan: {requested_display}\n"
        f"Aplica: {effective_display}",
        parse_mode="Markdown",
    )

    # Notify client
    try:
        await context.bot.send_message(
            chat_id=change["telegram_user_id"],
            text=(
                f"✅ *Tu cambio de plan fue aprobado*\n\n"
                f"Nuevo plan: *{requested_display}*\n"
                f"Aplica a partir del: *{effective_display}*\n\n"
                "El cambio se aplicará automáticamente en esa fecha."
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        log.warning("Failed to notify client %d: %s", change["telegram_user_id"], e)

    log.info("Plan change #%d approved by admin %d", change_id, user.id)


async def _handle_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin rejects plan change."""
    query = update.callback_query
    user = update.effective_user

    if not user or not is_admin(user.id):
        await query.answer("Solo administradores.")
        return

    change_id = int(query.data[len("planchange_reject_"):])
    db = context.bot_data["db"]

    change = await db.get_plan_change(change_id)
    if not change:
        await query.answer("Solicitud no encontrada.")
        return

    if change["status"] != "pending":
        await query.answer(f"Ya fue procesada: {change['status']}")
        return

    await db.update_plan_change(change_id, status="rejected")

    await query.answer("Rechazado")
    await query.edit_message_text(
        f"❌ *Cambio rechazado*\n\n"
        f"Cliente: {change['client_name']}\n"
        f"Plan solicitado: {_display_name(change['requested_plan'])}",
        parse_mode="Markdown",
    )

    # Notify client
    try:
        await context.bot.send_message(
            chat_id=change["telegram_user_id"],
            text=(
                f"❌ *Tu solicitud de cambio de plan fue rechazada*\n\n"
                f"Plan solicitado: {_display_name(change['requested_plan'])}\n\n"
                "Si tienes dudas, contacta a soporte."
            ),
            parse_mode="Markdown",
        )
    except Exception as e:
        log.warning("Failed to notify client %d: %s", change["telegram_user_id"], e)

    log.info("Plan change #%d rejected by admin %d", change_id, user.id)


async def apply_approved_changes(mk, db, notifier=None, bot=None):
    """Apply all approved plan changes for today's effective date.

    Called by the billing scheduler on day 1 of each month.
    After updating the secret profile, disconnects the active session
    so the client reconnects with the new profile.
    """
    now = datetime.now(TZ)
    effective_date = now.strftime("%Y-%m-%d")

    changes = await db.get_approved_plan_changes(effective_date)
    if not changes:
        return 0

    applied = 0
    for change in changes:
        client_name = change["client_name"]
        requested_plan = change["requested_plan"]

        try:
            # Find and update secret
            secret = await mk.find_secret_by_name(client_name)
            if not secret:
                log.warning("Plan change #%d: secret not found for '%s'", change["id"], client_name)
                continue

            secret_id = secret.get(".id")
            if not secret_id:
                continue

            # Find the actual profile name (case-sensitive) from MikroTik
            profiles = await mk.get_ppp_profiles()
            actual_profile = requested_plan  # fallback
            for p in profiles:
                if (p.get("name") or "").lower() == requested_plan.lower():
                    actual_profile = p["name"]
                    break

            result = await mk.update_ppp_secret(secret_id, profile=actual_profile)
            if not result.get("success"):
                log.error("Plan change #%d: failed to update secret", change["id"])
                continue

            # Disconnect active session to force reconnect with new profile
            secret_name = secret.get("name", client_name)
            await mk.disconnect_session(secret_name)

            # Mark as applied
            await db.update_plan_change(
                change["id"],
                status="applied",
                applied_at=now.isoformat(),
            )
            applied += 1

            # Notify client
            if bot:
                try:
                    await bot.send_message(
                        chat_id=change["telegram_user_id"],
                        text=(
                            f"✅ *Tu cambio de plan se ha aplicado*\n\n"
                            f"Nuevo plan: *{_display_name(requested_plan)}*\n\n"
                            "Tu conexión se reiniciará brevemente para aplicar el cambio."
                        ),
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    log.warning("Failed to notify client %d: %s", change["telegram_user_id"], e)

            log.info("Plan change #%d applied: %s -> %s", change["id"], client_name, actual_profile)

        except Exception as e:
            log.error("Plan change #%d error: %s", change["id"], e)

    log.info("Applied %d/%d plan changes for %s", applied, len(changes), effective_date)
    return applied
