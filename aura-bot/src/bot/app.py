"""Telegram Application setup: registra handlers y configura dependencias."""

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from src import config
from src.database.db import Database
from src.integrations.uisp_nms import UispNmsClient
from src.integrations.uisp_crm import UispCrmClient
from src.integrations.mikrotik import MikroTikClient
from src.ai.claude_client import ClaudeClient
from src.ai.tool_executor import ToolExecutor
from src.bot.handlers import start, admin, customer, conversation
from src.bot.handlers.registration import get_registration_handler
from src.utils.logger import log


async def post_init(application: Application):
    """Se ejecuta despues de que la Application se inicializa."""
    # Database
    db = Database(config.DB_PATH)
    await db.connect()
    application.bot_data["db"] = db

    # UISP clients
    nms = UispNmsClient()
    crm = UispCrmClient()
    application.bot_data["uisp_nms"] = nms
    application.bot_data["uisp_crm"] = crm

    # MikroTik client
    mk = None
    if config.MIKROTIK_PASSWORD:
        mk = MikroTikClient()
        try:
            ok = await mk.test_connection()
            if ok:
                log.info("MikroTik conectado: %s:%d", config.MIKROTIK_HOST, config.MIKROTIK_PORT)
            else:
                log.warning("MikroTik no accesible, continuando sin MikroTik")
                mk = None
        except Exception as e:
            log.warning("MikroTik error: %s, continuando sin MikroTik", e)
            mk = None
    application.bot_data["mikrotik"] = mk

    # Claude AI
    tool_executor = ToolExecutor(nms, crm, mk, db)
    claude = ClaudeClient(tool_executor)
    application.bot_data["claude"] = claude
    if claude.enabled:
        log.info("Claude AI habilitado (modelo: %s)", config.CLAUDE_MODEL)
    else:
        log.warning("Claude AI deshabilitado (sin ANTHROPIC_API_KEY)")

    log.info("Aura Bot inicializado correctamente")


async def post_shutdown(application: Application):
    """Limpieza al apagar."""
    db = application.bot_data.get("db")
    if db:
        await db.close()

    nms = application.bot_data.get("uisp_nms")
    if nms:
        await nms.close()

    crm = application.bot_data.get("uisp_crm")
    if crm:
        await crm.close()

    log.info("Aura Bot apagado")


def create_application() -> Application:
    """Crea y configura la Application de Telegram."""
    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # -- Handlers (orden importa) --

    # Registration ConversationHandler (must be before general message handler)
    app.add_handler(get_registration_handler())

    # /start, /help, /menu
    app.add_handler(CommandHandler("start", start.start_command))
    app.add_handler(CommandHandler("help", start.help_command))
    app.add_handler(CommandHandler("menu", start.menu_command))

    # Customer commands
    app.add_handler(CommandHandler("misaldo", customer.misaldo_command))
    app.add_handler(CommandHandler("miservicio", customer.miservicio_command))
    app.add_handler(CommandHandler("miconexion", customer.miconexion_command))
    app.add_handler(CommandHandler("reportar", customer.reportar_command))
    app.add_handler(CommandHandler("soporte", customer.soporte_command))

    # Admin commands
    app.add_handler(CommandHandler("red", admin.red_command))
    app.add_handler(CommandHandler("clientes", admin.clientes_command))
    app.add_handler(CommandHandler("buscar", admin.buscar_command))
    app.add_handler(CommandHandler("dispositivos", admin.dispositivos_command))
    app.add_handler(CommandHandler("pppoe", admin.pppoe_command))
    app.add_handler(CommandHandler("diagnostico", admin.diagnostico_command))
    app.add_handler(CommandHandler("caidas", admin.caidas_command))

    # Callback queries from inline keyboards
    app.add_handler(CallbackQueryHandler(_handle_callback))

    # Free text messages → Claude AI (catch-all, must be last)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, conversation.handle_message))

    return app


async def _handle_callback(update, context):
    """Despacha callback queries de teclados inline a los handlers correctos."""
    query = update.callback_query
    if not query or not query.data:
        return

    data = query.data

    # Map callback_data to command handlers
    handlers = {
        "cmd_misaldo": customer.misaldo_command,
        "cmd_miservicio": customer.miservicio_command,
        "cmd_miconexion": customer.miconexion_command,
        "cmd_reportar": customer.reportar_command,
        "cmd_soporte": customer.soporte_command,
        "cmd_red": admin.red_command,
        "cmd_clientes": admin.clientes_command,
        "cmd_dispositivos": admin.dispositivos_command,
        "cmd_pppoe": admin.pppoe_command,
        "cmd_caidas": admin.caidas_command,
    }

    handler = handlers.get(data)
    if handler:
        await handler(update, context)
