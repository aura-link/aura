"""Handler /aviso: crear, previsualizar y publicar avisos en el portal captive.

Supports phased rollout with 3 modes:
- soft: aviso shows, verifies, but always gives internet (Feb 25 - Mar 14)
- medium: verify strict + temp dismiss available (Mar 15 - Mar 27)
- strict: must register to browse (Mar 28 - Mar 31)
"""

import asyncio
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.bot.roles import is_admin
from src.utils.logger import log
from src import config

TZ = ZoneInfo("America/Mexico_City")

# Aviso schedule: mode transitions by date (month, day)
AVISO_MODE_SCHEDULE = [
    ((3, 28), "strict"),   # Mar 28+ → strict
    ((3, 15), "medium"),   # Mar 15-27 → medium
    ((2, 25), "soft"),     # Feb 25 - Mar 14 → soft
]
AVISO_REPUBLISH_DAYS = 3  # Re-publish every 3 days in soft/medium modes

AVISOS_URL = None  # lazy-loaded from config
ADMIN_TOKEN = None

STRUCTURING_PROMPT = """\
Eres asistente de AURALINK, un ISP rural en Tomatlan, Jalisco. \
Estructura el siguiente texto como un aviso profesional para los clientes.

Retorna SOLO un JSON valido (sin markdown, sin backticks) con estos campos:
- "title": string, titulo corto (max 50 chars)
- "icon": string, un emoji relevante como icono (ej: "🔧", "📢", "⚠️", "🎉")
- "color_theme": "blue"|"orange"|"green"|"red" segun tono del aviso
- "body": string, texto principal del aviso, claro y profesional (max 200 chars)
- "details": lista de strings con datos clave (zona, horario, etc), puede estar vacia
- "show_bank_info": boolean, true solo si el aviso menciona pagos
- "show_telegram_bot": boolean, true si conviene recordar el bot de Telegram
- "dismiss_text": string, texto del boton (ej: "Entendido", "De acuerdo")

Texto del admin: """

NAT_COMMENT = "Avisos: redirect HTTP a portal de anuncios"
SCHEDULER_NAME = "populate-avisos-schedule"
SCRIPT_NAME = "populate-avisos"


def _get_config():
    global AVISOS_URL, ADMIN_TOKEN
    if AVISOS_URL is None:
        AVISOS_URL = getattr(config, "AVISOS_PORTAL_URL", "http://217.216.85.65:8090")
        ADMIN_TOKEN = getattr(config, "AVISOS_ADMIN_TOKEN", "auralink-avisos-2026")


async def _portal_request(method: str, path: str, json_data: dict | None = None) -> dict | None:
    """Make HTTP request to avisos portal API."""
    _get_config()
    url = f"{AVISOS_URL}{path}"
    headers = {"X-Admin-Token": ADMIN_TOKEN}
    try:
        async with aiohttp.ClientSession() as session:
            if method == "POST":
                async with session.post(url, json=json_data, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    return await resp.json()
            else:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    return await resp.json()
    except Exception as e:
        log.error("Portal API error (%s %s): %s", method, path, e)
        return None


async def _structure_with_claude(text: str) -> dict | None:
    """Use Claude to structure free text into announcement JSON."""
    if not config.ANTHROPIC_API_KEY:
        return None
    try:
        client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        response = await client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": STRUCTURING_PROMPT + text}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            if raw.endswith("```"):
                raw = raw[:-3]
            raw = raw.strip()
        return json.loads(raw)
    except (json.JSONDecodeError, Exception) as e:
        log.error("Claude structuring error: %s", e)
        return None


def _preview_text(data: dict) -> str:
    """Format announcement data as Telegram preview text."""
    theme_labels = {"blue": "Informativo", "orange": "Mantenimiento", "green": "Buena noticia", "red": "Urgente"}
    theme = theme_labels.get(data.get("color_theme", "blue"), "Info")
    icon = data.get("icon", "")
    title = data.get("title", "Sin titulo")
    body = data.get("body", "")
    details = data.get("details", [])
    features = data.get("features", [])
    steps = data.get("steps", [])
    bank = "Si" if data.get("show_bank_info") else "No"
    tg = "Si" if data.get("show_telegram_bot") else "No"

    lines = [
        f"{icon} {title}",
        f"Tema: {theme}",
        "",
        body,
    ]
    if details:
        lines.append("")
        for d in details:
            lines.append(f"  - {d}")
    if features:
        lines.append("")
        lines.append("Beneficios:")
        for f in features:
            lines.append(f"  {f.get('icon', '✓')} {f.get('text', '')}")
    if steps:
        lines.append("")
        lines.append("Pasos:")
        for i, s in enumerate(steps, 1):
            lines.append(f"  {i}. {s}")
    mode = data.get("mode", "normal")
    mode_labels = {"soft": "Suave (internet siempre)", "medium": "Medio (verifica estricto)", "strict": "Estricto (debe registrarse)"}
    mode_label = mode_labels.get(mode, "Normal")
    lines.extend(["", f"Datos bancarios: {bank} | Bot Telegram: {tg}", f"Modo: {mode_label}"])
    return "\n".join(lines)


async def _reply(update: Update, text: str, **kwargs):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, **kwargs)
    elif update.message:
        await update.message.reply_text(text, **kwargs)


async def aviso_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /aviso command."""
    user = update.effective_user
    if not user or not is_admin(user.id):
        await _reply(update, "Solo administradores.")
        return

    args = " ".join(context.args) if context.args else ""

    # /aviso (no args) → show status
    if not args:
        await _show_status(update, context)
        return

    # /aviso off → deactivate
    if args.strip().lower() == "off":
        await _deactivate(update, context)
        return

    # /aviso registro → hardcoded registration announcement
    if args.strip().lower() == "registro":
        structured = {
            "title": "Nuevo Sistema de Atención AURALINK",
            "icon": "📱",
            "color_theme": "blue",
            "body": "A partir de abril 2026, AURALINK gestionará tu cuenta a través de Telegram: consultas de saldo, reportes de pago, soporte técnico y avisos de servicio.\n\nEl registro está disponible durante el mes de marzo. Los clientes que no se registren antes del 31 de marzo no tendrán acceso a estos beneficios cuando el sistema entre en operación.",
            "details": [
                "Registro disponible: 1 al 31 de marzo 2026",
                "Inicio de operación: abril 2026",
            ],
            "features": [
                {"icon": "💰", "text": "Consultar tu saldo y facturas"},
                {"icon": "📡", "text": "Ver el estado de tu servicio"},
                {"icon": "🔧", "text": "Reportar problemas de conexión"},
                {"icon": "📸", "text": "Enviar comprobantes de pago"},
                {"icon": "🆘", "text": "Soporte técnico directo"},
            ],
            "steps": [
                "Abre Telegram en tu celular",
                "Busca @auralinkmonitor_bot",
                "Presiona Iniciar",
                "Vincula tu cuenta con tu nombre",
            ],
            "show_bank_info": False,
            "show_telegram_bot": True,
            "dismiss_text": "Ya me registré",
            "verify_registro": True,
            "mode": "soft",
        }
        context.user_data["pending_aviso"] = structured
        preview = _preview_text(structured)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Publicar", callback_data="aviso_publish"),
             InlineKeyboardButton("Cancelar", callback_data="aviso_cancel")],
        ])
        await _reply(update, f"Preview del aviso de registro:\n\n{preview}", reply_markup=keyboard)
        return

    # /aviso <text> → structure with Claude and preview
    await _reply(update, "Estructurando aviso con IA...")

    structured = await _structure_with_claude(args)
    if not structured:
        await _reply(update, "Error al estructurar el aviso. Intenta de nuevo.")
        return

    # Store pending aviso in user_data
    context.user_data["pending_aviso"] = structured

    preview = _preview_text(structured)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Publicar", callback_data="aviso_publish"),
         InlineKeyboardButton("Cancelar", callback_data="aviso_cancel")],
    ])

    await _reply(update, f"Preview del aviso:\n\n{preview}", reply_markup=keyboard)


async def _show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current portal status."""
    mk = context.bot_data.get("mikrotik")

    result = await _portal_request("GET", "/api/admin/status")

    if result and result.get("active"):
        title = result.get("title", "?")
        pending = 0
        if mk:
            try:
                pending = await mk.get_address_list_count("avisos")
            except Exception:
                pass
        await _reply(update,
            f"*Estado del portal de avisos*\n\n"
            f"Estado: ACTIVO\n"
            f"Titulo: {title}\n"
            f"Clientes pendientes: {pending}",
            parse_mode="Markdown",
        )
    else:
        await _reply(update,
            "*Estado del portal de avisos*\n\n"
            "Estado: INACTIVO\n\n"
            "Usa `/aviso <texto>` para crear un aviso.",
            parse_mode="Markdown",
        )


async def registrados_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /registrados: muestra clientes registrados vs no registrados."""
    user = update.effective_user
    if not user or not is_admin(user.id):
        await _reply(update, "Solo administradores.")
        return

    db = context.bot_data.get("db")
    mk = context.bot_data.get("mikrotik")
    if not db:
        await _reply(update, "DB no disponible.")
        return

    # Get registered clients (linked to Telegram)
    links = await db.get_all_customer_links()
    linked_names = {}
    for link in links:
        name = link.get("crm_client_name") or "?"
        linked_names[name.lower().replace(" ", "")] = {
            "name": name,
            "service_id": link.get("service_id", ""),
            "telegram_user_id": link.get("telegram_user_id"),
            "telegram_username": link.get("telegram_username", ""),
        }

    # Get active PPPoE sessions (total connected clients)
    sessions = []
    if mk:
        try:
            sessions = await mk.get_active_sessions()
        except Exception:
            pass

    # Cross-reference: which active sessions are registered?
    registered = []
    not_registered = []
    for s in sessions:
        ppp_name = s.get("name", "")
        if not ppp_name:
            continue
        ppp_lower = ppp_name.lower().replace(" ", "")
        found = False
        for linked_key, linked_info in linked_names.items():
            if linked_key == ppp_lower or linked_key in ppp_lower or ppp_lower in linked_key:
                registered.append({
                    "ppp_name": ppp_name,
                    "ip": s.get("address", "?"),
                    "service_id": linked_info["service_id"],
                    "tg_username": linked_info["telegram_username"],
                })
                found = True
                break
        if not found:
            not_registered.append({
                "ppp_name": ppp_name,
                "ip": s.get("address", "?"),
            })

    total = len(registered) + len(not_registered)
    pct = (len(registered) / total * 100) if total > 0 else 0

    # Progress bar
    filled = round(pct / 10)
    bar = "\u2588" * filled + "\u2591" * (10 - filled)

    text = (
        f"*Registro de Clientes*\n\n"
        f"Sesiones PPPoE activas: *{total}*\n"
        f"Registrados: *{len(registered)}*\n"
        f"Sin registrar: *{len(not_registered)}*\n\n"
        f"Progreso: {bar} *{pct:.0f}%*\n"
    )

    # List registered
    if registered:
        text += f"\n*Registrados ({len(registered)}):*\n"
        for r in sorted(registered, key=lambda x: x["ppp_name"]):
            tg = f" @{r['tg_username']}" if r["tg_username"] else ""
            sid = f" [{r['service_id']}]" if r["service_id"] else ""
            text += f"  {r['ppp_name']}{sid}{tg}\n"

    # List not registered (max 50 to avoid message too long)
    if not_registered:
        text += f"\n*Sin registrar ({len(not_registered)}):*\n"
        for nr in sorted(not_registered, key=lambda x: x["ppp_name"])[:50]:
            text += f"  {nr['ppp_name']} ({nr['ip']})\n"
        if len(not_registered) > 50:
            text += f"  _...y {len(not_registered) - 50} mas_\n"

    await _reply(update, text, parse_mode="Markdown")


async def _deactivate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Deactivate current announcement and disable MikroTik NAT."""
    mk = context.bot_data.get("mikrotik")

    result = await _portal_request("POST", "/api/admin/deactivate")
    if not result or not result.get("ok"):
        await _reply(update, "Error al desactivar el portal.")
        return

    # Disable MikroTik NAT redirect + scheduler
    if mk:
        try:
            await mk.set_nat_rule_disabled(NAT_COMMENT, disabled=True)
            await mk.set_scheduler_disabled(SCHEDULER_NAME, disabled=True)
        except Exception as e:
            log.warning("MikroTik deactivate error: %s", e)

    await _reply(update, "Aviso desactivado. El portal ya no redirige clientes.")


async def handle_aviso_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle publish/cancel callbacks for avisos."""
    query = update.callback_query
    if not query:
        return

    user = update.effective_user
    if not user or not is_admin(user.id):
        await query.answer("Solo administradores.")
        return

    data = query.data

    if data == "aviso_publish":
        await _publish(update, context)
    elif data == "aviso_cancel":
        context.user_data.pop("pending_aviso", None)
        await query.answer("Cancelado")
        await query.edit_message_text("Aviso cancelado.")


async def _publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Publish the pending announcement."""
    query = update.callback_query
    await query.answer("Publicando...")

    aviso = context.user_data.pop("pending_aviso", None)
    if not aviso:
        await query.edit_message_text("No hay aviso pendiente.")
        return

    # 1. Send to portal API
    result = await _portal_request("POST", "/api/admin/update", aviso)
    if not result or not result.get("ok"):
        await query.edit_message_text("Error al publicar en el portal.")
        return

    mk = context.bot_data.get("mikrotik")
    clients_count = 0

    if mk:
        try:
            # 2. Clear avisos-visto (so everyone sees the new announcement)
            await mk.clear_address_list("avisos-visto")
            # 3. Clear existing avisos list
            await mk.clear_address_list("avisos")
            # 4. Run populate-avisos script (fills address-list from active PPPoE)
            await mk.run_script(SCRIPT_NAME)
            # 5. Enable NAT redirect rule
            await mk.set_nat_rule_disabled(NAT_COMMENT, disabled=False)
            # 6. Enable scheduler for periodic repopulation
            await mk.set_scheduler_disabled(SCHEDULER_NAME, disabled=False)
            # 7. Count clients that will see it
            clients_count = await mk.get_address_list_count("avisos")
        except Exception as e:
            log.error("MikroTik publish error: %s", e)

    # 8. Auto-dismiss registered clients (so they don't see aviso)
    dismissed = 0
    db = context.bot_data.get("db")
    if mk and db:
        try:
            dismissed = await _auto_dismiss_registered(mk, db)
        except Exception as e:
            log.warning("Auto-dismiss error: %s", e)

    title = aviso.get("title", "?")
    mode = aviso.get("mode", "normal")
    msg = f"Aviso publicado: *{title}*"
    if clients_count > 0:
        msg += f"\n\n{clients_count} clientes lo veran al navegar."
        if dismissed > 0:
            msg += f"\n{dismissed} clientes registrados auto-excluidos."
    else:
        msg += "\n\nMikroTik no disponible o lista vacia — verifica manualmente."
    if mode in ("soft", "medium", "strict"):
        mode_labels = {"soft": "Suave", "medium": "Medio", "strict": "Estricto"}
        msg += f"\nModo: {mode_labels.get(mode, mode)}"

    await query.edit_message_text(msg, parse_mode="Markdown")


async def _auto_dismiss_registered(mk, db) -> int:
    """Add registered clients to avisos-visto so they skip the aviso."""
    links = await db.get_all_customer_links()
    if not links:
        return 0

    sessions = await mk.get_active_sessions()
    linked_names = set()
    for link in links:
        name = (link.get("crm_client_name") or "").lower().replace(" ", "")
        if name:
            linked_names.add(name)

    dismissed = 0
    for session in sessions:
        ppp_name = (session.get("name") or "").lower().replace(" ", "")
        if not ppp_name:
            continue
        for linked in linked_names:
            if linked == ppp_name or linked in ppp_name or ppp_name in linked:
                ip = session.get("address")
                if ip:
                    ok = await mk.add_address_list_entry("avisos-visto", ip, session.get("name", ""))
                    if ok:
                        dismissed += 1
                break

    log.info("Auto-dismissed %d registered clients from avisos", dismissed)
    return dismissed


def _get_current_mode() -> str:
    """Determine the correct mode based on today's date."""
    now = datetime.now(TZ)
    for (month, day), mode in AVISO_MODE_SCHEDULE:
        if (now.month, now.day) >= (month, day):
            return mode
    return "soft"


# --- Registration Aviso Template (reusable for scheduler) ---

def _get_registro_aviso(mode: str) -> dict:
    """Get the registration aviso template with the specified mode."""
    return {
        "title": "Nuevo Sistema de Atención AURALINK",
        "icon": "\U0001f4f1",
        "color_theme": "blue",
        "body": "A partir de abril 2026, AURALINK gestionará tu cuenta a través de Telegram: consultas de saldo, reportes de pago, soporte técnico y avisos de servicio.\n\nEl registro está disponible durante el mes de marzo. Los clientes que no se registren antes del 31 de marzo no tendrán acceso a estos beneficios cuando el sistema entre en operación.",
        "details": [
            "Registro disponible: 1 al 31 de marzo 2026",
            "Inicio de operación: abril 2026",
        ],
        "features": [
            {"icon": "\U0001f4b0", "text": "Consultar tu saldo y facturas"},
            {"icon": "\U0001f4e1", "text": "Ver el estado de tu servicio"},
            {"icon": "\U0001f527", "text": "Reportar problemas de conexión"},
            {"icon": "\U0001f4f8", "text": "Enviar comprobantes de pago"},
            {"icon": "\U0001f198", "text": "Soporte técnico directo"},
        ],
        "steps": [
            "Abre Telegram en tu celular",
            "Busca @auralinkmonitor_bot",
            "Presiona Iniciar",
            "Vincula tu cuenta con tu nombre",
        ],
        "show_bank_info": False,
        "show_telegram_bot": True,
        "dismiss_text": "Ya me registré",
        "verify_registro": True,
        "mode": mode,
    }


async def _republish_aviso(mk, db, mode: str) -> dict:
    """Re-publish registration aviso with updated mode. Returns summary dict."""
    aviso = _get_registro_aviso(mode)

    # 1. Send to portal API
    result = await _portal_request("POST", "/api/admin/update", aviso)
    if not result or not result.get("ok"):
        return {"ok": False, "error": "Portal API failed"}

    clients_count = 0
    dismissed = 0

    if mk:
        # 2. Clear avisos-visto (so unregistered see it again)
        await mk.clear_address_list("avisos-visto")
        # 3. Clear avisos
        await mk.clear_address_list("avisos")
        # 4. Run populate-avisos script
        await mk.run_script(SCRIPT_NAME)
        # 5. Enable NAT + scheduler
        await mk.set_nat_rule_disabled(NAT_COMMENT, disabled=False)
        await mk.set_scheduler_disabled(SCHEDULER_NAME, disabled=False)
        # 6. Auto-dismiss registered clients
        if db:
            dismissed = await _auto_dismiss_registered(mk, db)
        # 7. Count remaining
        clients_count = await mk.get_address_list_count("avisos")

    return {
        "ok": True,
        "mode": mode,
        "clients": clients_count,
        "dismissed": dismissed,
        "title": aviso["title"],
    }


async def aviso_scheduler_loop(bot_data: dict):
    """Background task: re-publishes registration aviso every 3 days and transitions modes.

    Schedule:
    - Feb 25 - Mar 14: soft mode, re-publish every 3 days
    - Mar 15 - Mar 27: medium mode, re-publish every 3 days
    - Mar 28 - Mar 31: strict mode (no re-publish needed, stays strict)
    - Apr 1+: auto-deactivate
    """
    await asyncio.sleep(30)  # let bot finish init
    log.info("Aviso scheduler started")

    while True:
        try:
            now = datetime.now(TZ)
            mk = bot_data.get("mikrotik")
            db = bot_data.get("db")

            # After March → deactivate
            if now.month >= 4:
                log.info("Aviso scheduler: April reached, deactivating")
                await _portal_request("POST", "/api/admin/deactivate")
                if mk:
                    try:
                        await mk.set_nat_rule_disabled(NAT_COMMENT, disabled=True)
                        await mk.set_scheduler_disabled(SCHEDULER_NAME, disabled=True)
                    except Exception:
                        pass
                break

            # Before Feb 25 → do nothing
            if now.month < 2 or (now.month == 2 and now.day < 25):
                await asyncio.sleep(3600)
                continue

            # Check if aviso is active
            aviso_state = bot_data.get("aviso_scheduler_state", {})
            last_publish = aviso_state.get("last_publish_date", "")
            last_mode = aviso_state.get("last_mode", "")
            today_str = now.strftime("%Y-%m-%d")
            current_mode = _get_current_mode()

            should_republish = False

            # Mode changed → re-publish immediately
            if current_mode != last_mode and last_mode:
                log.info("Aviso mode transition: %s → %s", last_mode, current_mode)
                should_republish = True

            # 3 days since last publish → re-publish (soft/medium only)
            elif current_mode in ("soft", "medium"):
                if not last_publish:
                    should_republish = True
                else:
                    try:
                        last_dt = datetime.strptime(last_publish, "%Y-%m-%d").replace(tzinfo=TZ)
                        days_since = (now - last_dt).days
                        if days_since >= AVISO_REPUBLISH_DAYS:
                            should_republish = True
                    except ValueError:
                        should_republish = True

            if should_republish and mk:
                log.info("Aviso scheduler: re-publishing in %s mode", current_mode)
                try:
                    result = await _republish_aviso(mk, db, current_mode)
                    if result.get("ok"):
                        bot_data["aviso_scheduler_state"] = {
                            "last_publish_date": today_str,
                            "last_mode": current_mode,
                        }
                        log.info("Aviso re-published: mode=%s, clients=%d, dismissed=%d",
                                 current_mode, result.get("clients", 0), result.get("dismissed", 0))

                        # Notify admin
                        for admin_id in config.TELEGRAM_ADMIN_IDS:
                            try:
                                bot = bot_data.get("_bot")
                                if bot:
                                    mode_labels = {"soft": "Suave", "medium": "Medio", "strict": "Estricto"}
                                    await bot.send_message(
                                        chat_id=admin_id,
                                        text=(
                                            f"Aviso re-publicado automaticamente\n\n"
                                            f"Modo: {mode_labels.get(current_mode, current_mode)}\n"
                                            f"Clientes pendientes: {result.get('clients', 0)}\n"
                                            f"Registrados excluidos: {result.get('dismissed', 0)}"
                                        ),
                                    )
                            except Exception:
                                pass
                    else:
                        log.error("Aviso re-publish failed: %s", result.get("error"))
                except Exception as e:
                    log.error("Aviso scheduler re-publish error: %s", e)

        except Exception as e:
            log.error("Aviso scheduler error: %s", e)

        # Check every 6 hours
        await asyncio.sleep(6 * 3600)
