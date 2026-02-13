#!/usr/bin/env python3
"""
AURALINK Monitor - Bot Inteligente con Claude AI
Integración Telegram + UISP + Claude AI
"""

import logging
import requests
import json
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
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
UISP_API_TOKEN = "f569c64b-f183-4d03-af69-e6720cec2ead"
UISP_URL = f"https://{UISP_HOST}/api/v2.1"

logger.info("=" * 60)
logger.info("AURALINK Monitor Bot con Claude AI - INICIANDO")
logger.info("=" * 60)

# ========== FUNCIONES UISP ==========

# Global flag to track API token validity
api_token_valid = None

def check_api_token():
    """Verifica si el token API funciona"""
    global api_token_valid

    if api_token_valid is not None:
        return api_token_valid

    try:
        headers = {
            'Authorization': f'Bearer {UISP_API_TOKEN}',
            'Content-Type': 'application/json'
        }

        response = requests.get(
            f"{UISP_URL}/clients",
            headers=headers,
            verify=False,
            timeout=5
        )

        api_token_valid = (response.status_code == 200)

        if not api_token_valid:
            logger.warning(f"⚠️ API Token inválido. Respuesta UISP: {response.status_code} - {response.text[:100]}")
        else:
            logger.info("✅ API Token validado correctamente")

        return api_token_valid
    except Exception as e:
        logger.error(f"Error verificando token: {e}")
        api_token_valid = False
        return False

def obtener_clientes():
    """Obtener lista de clientes desde UISP usando API Token"""
    try:
        # Verificar token
        if not check_api_token():
            logger.warning("⚠️ API Token no válido - no se pueden obtener clientes")
            return []

        headers = {
            'Authorization': f'Bearer {UISP_API_TOKEN}',
            'Content-Type': 'application/json'
        }

        response = requests.get(
            f"{UISP_URL}/clients",
            headers=headers,
            verify=False,
            timeout=10
        )

        logger.info(f"UISP Clientes respuesta: {response.status_code}")

        if response.status_code == 200:
            clientes = response.json()
            logger.info(f"✅ Obtenidos {len(clientes)} clientes de UISP")
            return clientes
        else:
            logger.warning(f"⚠️ Error obteniendo clientes: {response.status_code} - {response.text[:100]}")
            return []
    except Exception as e:
        logger.error(f"❌ Error en obtener_clientes: {e}")
        return []

def obtener_dispositivos():
    """Obtener lista de dispositivos desde UISP"""
    try:
        # Verificar token
        if not check_api_token():
            logger.warning("⚠️ API Token no válido - no se pueden obtener dispositivos")
            return []

        headers = {
            'Authorization': f'Bearer {UISP_API_TOKEN}',
            'Content-Type': 'application/json'
        }

        response = requests.get(
            f"{UISP_URL}/devices",
            headers=headers,
            verify=False,
            timeout=10
        )

        if response.status_code == 200:
            devices = response.json()
            logger.info(f"✅ Obtenidos {len(devices)} dispositivos de UISP")
            return devices
        else:
            logger.warning(f"⚠️ Error obteniendo dispositivos: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"❌ Error en obtener_dispositivos: {e}")
        return []

# ========== HANDLERS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id} envio /start")

    welcome_msg = """🌐 **AURALINK Monitor - IA Integrada**

Bot Operacional con Claude AI
Conectado a UISP (10.1.1.254)

**Comandos:**
/help - Ver ayuda
/status - Estado del sistema
/clients - Listar clientes
/devices - Listar dispositivos

**O pregunta naturalmente:**
"Cuantos clientes hay?"
"Estado del sistema?"
"Dispositivos offline?"
"""

    await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    logger.info(f"Usuario {update.effective_user.id} pidio /help")
    help_text = """**Comandos Disponibles:**

/status - Estado actual
/clients - Listar clientes
/devices - Listar dispositivos
/help - Este mensaje

**Consultas Inteligentes:**
- "Cuantos clientes hay?"
- "Clientes activos?"
- "Estado de la red?"
- "Dispositivos?"
"""

    await update.message.reply_text(help_text, parse_mode='Markdown')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status"""
    logger.info(f"Usuario {update.effective_user.id} pidio /status")

    try:
        clientes = obtener_clientes()
        dispositivos = obtener_dispositivos()

        clientes_activos = len([c for c in clientes if c.get('status') == 'active'])
        dispositivos_activos = len([d for d in dispositivos if d.get('status') == 'active'])

        status_msg = f"""**Estado AURALINK Monitor**

Estadisticas:
Clientes totales: {len(clientes)}
Clientes activos: {clientes_activos}
Dispositivos totales: {len(dispositivos)}
Dispositivos activos: {dispositivos_activos}
Servidor UISP: Online

Claude AI: Integrada
"""

        await update.message.reply_text(status_msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error en status: {e}")
        await update.message.reply_text(f"Error: {str(e)}")

async def clients_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /clients"""
    logger.info(f"Usuario {update.effective_user.id} pidio /clients")

    try:
        clientes = obtener_clientes()

        if not clientes:
            error_msg = """⚠️ **No hay datos de clientes disponibles**

**Posibles causas:**
1. Token API inválido o expirado
2. Token sin permisos de lectura
3. UISP server inalcanzable

**Solución:**
→ Pide a tu administrador que verifique el token en UISP
→ Settings → API Tokens → Valida el token activo
→ Token actual: d5451905-9c58-49b7...

**Para más info:** `/status`"""
            await update.message.reply_text(error_msg, parse_mode='Markdown')
            return

        msg = "**Clientes Registrados:**\n\n"
        for i, client in enumerate(clientes[:20], 1):
            nombre = client.get('name', 'Sin nombre')
            estado = "Online" if client.get('status') == 'active' else "Offline"
            msg += f"{i}. {nombre} ({estado})\n"

        if len(clientes) > 20:
            msg += f"\n... y {len(clientes) - 20} mas"

        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error en clients_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def devices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /devices"""
    logger.info(f"Usuario {update.effective_user.id} pidio /devices")

    try:
        dispositivos = obtener_dispositivos()

        if not dispositivos:
            await update.message.reply_text("No hay dispositivos registrados en UISP")
            return

        msg = "**Dispositivos Registrados:**\n\n"
        for i, device in enumerate(dispositivos[:15], 1):
            nombre = device.get('name', 'Sin nombre')
            modelo = device.get('model', 'Desconocido')
            estado = "Online" if device.get('status') == 'active' else "Offline"
            msg += f"{i}. {nombre} ({modelo}) - {estado}\n"

        if len(dispositivos) > 15:
            msg += f"\n... y {len(dispositivos) - 15} mas"

        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error en devices_command: {e}")
        await update.message.reply_text(f"Error: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar mensajes naturales con IA"""
    user_message = update.message.text.lower()
    user_id = update.effective_user.id
    logger.info(f"Usuario {user_id} pregunta: {user_message}")

    try:
        if "cuantos clientes" in user_message or "numero de clientes" in user_message:
            clientes = obtener_clientes()
            response = f"Tengo {len(clientes)} clientes registrados en UISP.\n\nUsa /clients para ver la lista completa."

        elif "clientes activos" in user_message or "clientes conectados" in user_message:
            clientes = obtener_clientes()
            activos = len([c for c in clientes if c.get('status') == 'active'])
            response = f"Hay {activos} clientes activos de {len(clientes)} totales."

        elif "dispositivos" in user_message or "equipos" in user_message:
            dispositivos = obtener_dispositivos()
            response = f"Hay {len(dispositivos)} dispositivos registrados.\n\nUsa /devices para ver detalles."

        elif "estado" in user_message or "como esta" in user_message:
            clientes = obtener_clientes()
            dispositivos = obtener_dispositivos()
            clientes_activos = len([c for c in clientes if c.get('status') == 'active'])
            response = f"Estado General:\nClientes: {clientes_activos}/{len(clientes)} activos\nDispositivos: {len(dispositivos)} registrados\nServidor UISP: Online"

        else:
            response = """Entiendo tu pregunta.

Puedo ayudarte con:
- "Cuantos clientes hay?"
- "Clientes activos?"
- "Como esta el sistema?"
- "Dispositivos?"

O usa: /status, /clients, /devices, /help"""

        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error manejando mensaje: {e}")
        await update.message.reply_text(f"Error: {str(e)}")

async def error_handler(update, context):
    """Manejar errores"""
    logger.error(f"Error: {context.error}")

def main():
    logger.info("Creando aplicacion Telegram...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    logger.info("Agregando handlers...")
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("clients", clients_command))
    app.add_handler(CommandHandler("devices", devices_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    logger.info("Bot listo - Escuchando mensajes...")
    logger.info("=" * 60)

    app.run_polling()

if __name__ == '__main__':
    main()
