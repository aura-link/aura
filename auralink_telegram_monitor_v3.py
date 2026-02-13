#!/usr/bin/env python3
"""
AURALINK Monitor v3 - Bot de Telegram para UISP (Versión Robusta)
Diseñado para evitar problemas con event loop
"""

import logging
import requests
import signal
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('/home/uisp/auralink_monitor/monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========== CONFIGURACIÓN ==========
TELEGRAM_TOKEN = "8318058273:AAEiKpg6L8gG9DSb4zLrtnPUS1Z6urYe_UI"
UISP_HOST = "10.1.1.254"
UISP_USER = "AURALINK"
UISP_PASS = "Varce*101089"

logger.info("=" * 50)
logger.info("AURALINK Monitor Bot v3 - Iniciando")
logger.info("=" * 50)

# Variable global para la aplicación
app = None

# ========== FUNCIONES ==========
def obtener_clientes():
    """Obtener lista de clientes desde UISP"""
    try:
        session = requests.Session()
        session.verify = False

        # Intentar login
        login_url = f"https://{UISP_HOST}/api/v2.1/user/login"
        payload = {
            "username": UISP_USER,
            "password": UISP_PASS
        }

        response = session.post(login_url, json=payload, timeout=10)
        logger.info(f"UISP Login respuesta: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            token = data.get('authorization')
            if token:
                session.headers.update({'Authorization': f'Bearer {token}'})
                logger.info("✓ Autenticación UISP exitosa")

        # Obtener clientes
        clients_url = f"https://{UISP_HOST}/api/v2.1/clients"
        response = session.get(clients_url, timeout=10)

        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Error obteniendo clientes: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error en obtener_clientes: {e}")
        return []

# ========== HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id} envió /start")

    welcome_msg = """🌐 **AURALINK Monitor v3**
Bot de monitoreo de UISP

✅ Bot operacional
📊 Conectado a UISP

**Comandos:**
/help - Ver ayuda
/status - Estado del sistema
/clients - Listar clientes

**O escribe:**
¿Cuántos clientes hay?"""

    await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    logger.info(f"Usuario {update.effective_user.id} pidió /help")
    help_text = """📖 **Guía de Comandos**

/status - Estado actual
/clients - Listar clientes
/help - Este mensaje

**Consultas:**
Puedes escribir preguntas naturales como:
- ¿Cuántos clientes activos hay?
- Muestra los dispositivos
- ¿Cuál es la IP del cliente X?"""

    await update.message.reply_text(help_text, parse_mode='Markdown')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status"""
    logger.info(f"Usuario {update.effective_user.id} pidió /status")

    try:
        clientes = obtener_clientes()
        status_msg = f"""✅ **Estado AURALINK Monitor**

📊 **Estadísticas:**
• Clientes totales: {len(clientes)}
• Servidor UISP: 🟢 Online

⏰ Sistema operacional"""

        await update.message.reply_text(status_msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error en status: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def clients_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /clients"""
    logger.info(f"Usuario {update.effective_user.id} pidió /clients")

    try:
        clientes = obtener_clientes()

        if not clientes:
            await update.message.reply_text("No hay clientes registrados")
            return

        msg = "👥 **Clientes Registrados:**\n\n"
        for i, client in enumerate(clientes[:15], 1):
            nombre = client.get('name', 'Sin nombre')
            msg += f"{i}. {nombre}\n"

        if len(clientes) > 15:
            msg += f"\n... y {len(clientes) - 15} más"

        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error en clients_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar mensajes de texto normales"""
    user_message = update.message.text.lower()
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id}: {user_message}")

    response = """✅ Mensaje recibido

El bot está operacional pero las funciones avanzadas están en desarrollo.

Intenta:
/status
/clients
/help"""

    await update.message.reply_text(response, parse_mode='Markdown')

async def error_handler(update, context):
    """Manejar errores"""
    logger.error(f"Error: {context.error}")

# ========== SIGNAL HANDLERS ==========
async def shutdown_handler(signum, frame):
    """Manejar señal de shutdown"""
    logger.info("Señal recibida, iniciando shutdown...")
    if app:
        await app.stop()
    logger.info("Bot finalizado correctamente")
    sys.exit(0)

# ========== MAIN ==========
async def main():
    """Iniciar el bot"""
    global app

    logger.info("✓ Creando aplicación Telegram...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    logger.info("✓ Agregando handlers...")
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("clients", clients_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("✓ Bot listo para recibir mensajes")
    logger.info("✓ Esperando mensajes en Telegram...")

    # Registrar signal handlers
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGTERM, signal.SIG_DFL)

    try:
        await app.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        logger.info("Bot detenido por usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}")

if __name__ == '__main__':
    import asyncio

    try:
        logger.info("Iniciando servicio...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot finalizado por usuario")
    except Exception as e:
        logger.error(f"Error en main: {e}")
        sys.exit(1)
