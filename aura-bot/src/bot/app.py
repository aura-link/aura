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
from src.bot.handlers import monitoring_admin
from src.bot.handlers import signup
from src.monitoring.zones import ZoneMapper
from src.monitoring.notifications import NotificationSender
from src.monitoring.monitor import NetworkMonitor
from src.monitoring.maintenance import MaintenanceManager
from src.billing.payments import PaymentProcessor
from src.billing.receipt_storage import ReceiptStorage
from src.billing.scheduler import BillingScheduler
from src.bot.handlers import billing_admin, receipts
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

    # Monitoring
    zone_mapper = ZoneMapper(nms, crm, db)
    notifier = NotificationSender(application.bot, db)
    monitor = NetworkMonitor(nms, db, zone_mapper, notifier)
    maintenance_mgr = MaintenanceManager(db)

    application.bot_data["zone_mapper"] = zone_mapper
    application.bot_data["notifier"] = notifier
    application.bot_data["monitor"] = monitor
    application.bot_data["maintenance"] = maintenance_mgr

    if config.MONITOR_ENABLED:
        await monitor.start()

    # Billing
    receipt_storage = ReceiptStorage(config.RECEIPT_STORAGE_PATH)
    payment_processor = PaymentProcessor(crm, mk, db, notifier, receipt_storage)
    billing_scheduler = BillingScheduler(crm, mk, db, notifier)

    application.bot_data["receipt_storage"] = receipt_storage
    application.bot_data["payment_processor"] = payment_processor
    application.bot_data["billing_scheduler"] = billing_scheduler

    if config.BILLING_ENABLED:
        await billing_scheduler.start()

    log.info("Aura Bot inicializado correctamente")


async def post_shutdown(application: Application):
    """Limpieza al apagar."""
    billing_scheduler = application.bot_data.get("billing_scheduler")
    if billing_scheduler:
        await billing_scheduler.stop()

    monitor = application.bot_data.get("monitor")
    if monitor:
        await monitor.stop()

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

    # TP-Link
    app.add_handler(CommandHandler("tplink", admin.tplink_command))

    # Signup & plan commands
    app.add_handler(CommandHandler("alta", signup.alta_command))
    app.add_handler(CommandHandler("plan", signup.plan_command))

    # Admin panel
    app.add_handler(CommandHandler("admin", admin.admin_command))

    # Billing admin commands
    app.add_handler(CommandHandler("pagos", billing_admin.pagos_command))
    app.add_handler(CommandHandler("morosos", billing_admin.morosos_command))
    app.add_handler(CommandHandler("reactivar", billing_admin.reactivar_command))
    app.add_handler(CommandHandler("cobranza", billing_admin.cobranza_command))

    # Monitoring admin commands
    app.add_handler(CommandHandler("zonas", monitoring_admin.zonas_command))
    app.add_handler(CommandHandler("incidentes", monitoring_admin.incidentes_command))
    app.add_handler(CommandHandler("monitor", monitoring_admin.monitor_command))
    app.add_handler(CommandHandler("mantenimiento", monitoring_admin.mantenimiento_command))

    # Callback queries from inline keyboards
    app.add_handler(CallbackQueryHandler(_handle_callback))

    # Photo handler for payment receipts (before catch-all text)
    app.add_handler(MessageHandler(filters.PHOTO, receipts.handle_photo))

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
        "cmd_zonas": monitoring_admin.zonas_command,
        "cmd_incidentes": monitoring_admin.incidentes_command,
        "cmd_monitor": monitoring_admin.monitor_command,
        "cmd_mantenimiento": monitoring_admin.mantenimiento_command,
        "cmd_tplink": admin.tplink_command,
        "cmd_admin": admin.admin_command,
        "cmd_pagos": billing_admin.pagos_command,
        "cmd_morosos": billing_admin.morosos_command,
    }

    # No-op for section dividers
    if data == "noop":
        await query.answer()
        return

    handler = handlers.get(data)
    if handler:
        await handler(update, context)
        return

    # Help callbacks → show usage instructions
    help_texts = {
        "cmd_alta_help": (
            "*Uso:* `/alta nombre-zona,perfil`\n\n"
            "*Ejemplo:*\n"
            "`/alta jesus arreola-cumbre,basico`\n\n"
            "Crea secret PPPoE en MikroTik y cliente en CRM."
        ),
        "cmd_plan_help": (
            "*Uso:* `/plan nombre,perfil`\n\n"
            "*Ejemplo:*\n"
            "`/plan jesus valencia,residencial`\n\n"
            "Cambia el perfil PPPoE del cliente."
        ),
        "cmd_buscar_help": (
            "*Uso:* `/buscar nombre`\n\n"
            "*Ejemplo:*\n"
            "`/buscar jesus`\n\n"
            "Busca clientes en el CRM por nombre."
        ),
        "cmd_diag_help": (
            "*Uso:* `/diagnostico ip`\n\n"
            "*Ejemplo:*\n"
            "`/diagnostico 10.10.1.50`\n\n"
            "Hace ping desde el MikroTik a la IP."
        ),
        "cmd_cobranza_help": (
            "*Uso:* `/cobranza <accion>`\n\n"
            "`/cobranza aviso` — Enviar avisos de factura\n"
            "`/cobranza recordatorio` — Enviar recordatorios\n"
            "`/cobranza advertencia` — Enviar advertencias\n"
            "`/cobranza suspender` — Ejecutar suspensiones\n"
        ),
    }

    if data in help_texts:
        await query.answer()
        await query.message.reply_text(
            help_texts[data], parse_mode="Markdown"
        )
        return

    # Payment approve/reject callbacks
    if data and data.startswith("pay_"):
        await billing_admin.handle_payment_callback(update, context)
        return

    # "Reportar Pago" button for customers
    if data == "cmd_reportar_pago":
        await query.answer()
        await query.message.reply_text(
            "💳 *Reportar pago*\n\n"
            "Envia una foto de tu comprobante de pago "
            "(transferencia, OXXO o deposito) y lo analizo automaticamente.\n\n"
            "Solo envia la foto como mensaje.",
            parse_mode="Markdown",
        )
        return

    # Maintenance cancel callbacks
    if data and data.startswith("cancel_maint_"):
        await monitoring_admin.handle_cancel_maintenance(update, context)
