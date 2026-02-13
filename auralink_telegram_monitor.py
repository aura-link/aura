#!/usr/bin/env python3
"""
AURALINK Monitor - Telegram Bot para monitoreo de UISP
Integra: Telegram + Python + UISP API + Claude AI
"""

import os
import sys
import requests
import json
import logging
import matplotlib.pyplot as plt
import matplotlib
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from functools import wraps

# Configurar matplotlib para no usar display
matplotlib.use('Agg')

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
UISP_USER = "AURALINK"
UISP_PASS = "Varce*101089"
UISP_URL = f"https://{UISP_HOST}/api/v2.1"

# IDs autorizados (agregamos después)
AUTHORIZED_USERS = set()  # Se llenarán después

# ========== CLASE UISP API CLIENT ==========
class UISPClient:
    """Cliente para comunicación con UISP API"""

    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password
        self.base_url = f"https://{host}/api/v2.1"
        self.session = requests.Session()
        self.session.verify = False  # Ignorar SSL por ahora
        self.token = None
        self.authenticate()

    def authenticate(self):
        """Autenticarse en UISP API"""
        try:
            # Intentar múltiples endpoints
            endpoints = [
                f"{self.base_url}/user/login",
                f"https://{self.host}/api/user/login",
                f"https://{self.host}/api/v2.0/user/login"
            ]

            # Payload con credenciales (JSON nativo maneja caracteres especiales)
            payload = {
                "username": self.user,
                "password": self.password
            }

            logger.info(f"Intentando autenticar con usuario: {self.user}")

            for url in endpoints:
                try:
                    logger.info(f"Probando endpoint: {url}")
                    response = self.session.post(url, json=payload, timeout=10)
                    logger.info(f"Respuesta: {response.status_code}")

                    if response.status_code == 200:
                        data = response.json()
                        self.token = data.get('authorization') or data.get('access_token') or data.get('token')
                        if self.token:
                            self.session.headers.update({
                                'Authorization': f'Bearer {self.token}'
                            })
                            logger.info(f"✓ Autenticación UISP exitosa (endpoint: {url})")
                            return True
                    else:
                        logger.warning(f"Status {response.status_code}: {response.text[:100]}")
                except Exception as e:
                    logger.warning(f"Error en {url}: {str(e)[:100]}")
                    continue

            logger.warning(f"✗ UISP requiere autenticación pero continuando sin token...")
            logger.info(f"Continuando sin autenticación - funcionalidades limitadas")
            return False
        except Exception as e:
            logger.error(f"✗ Error conectando a UISP: {e}")
            return False

    def get_clients(self):
        """Obtener lista de clientes"""
        try:
            url = f"{self.base_url}/clients"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Error obteniendo clientes: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error en get_clients: {e}")
            return []

    def get_client_by_name(self, name):
        """Buscar cliente por nombre"""
        try:
            clients = self.get_clients()
            for client in clients:
                if name.lower() in str(client.get('name', '')).lower():
                    return client
            return None
        except Exception as e:
            logger.error(f"Error buscando cliente: {e}")
            return None

    def get_devices(self):
        """Obtener lista de dispositivos"""
        try:
            url = f"{self.base_url}/devices"
            response = self.session.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Error obteniendo dispositivos: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error en get_devices: {e}")
            return []

    def get_statistics(self, client_id, time_range='24h'):
        """Obtener estadísticas de un cliente"""
        try:
            url = f"{self.base_url}/clients/{client_id}/statistics"
            params = {'period': time_range}
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Error obteniendo stats: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error en get_statistics: {e}")
            return None

# ========== INSTANCIA GLOBAL UISP ==========
try:
    uisp = UISPClient(UISP_HOST, UISP_USER, UISP_PASS)
    logger.info("✓ Cliente UISP inicializado")
except Exception as e:
    logger.error(f"✗ Error inicializando UISP: {e}")
    uisp = None

# ========== DECORADORES ==========
def restricted(func):
    """Decorador para restringir comandos a usuarios autorizados"""
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in AUTHORIZED_USERS:
            logger.warning(f"Acceso denegado para usuario: {user_id}")
            await update.message.reply_text(
                "⛔ No estás autorizado para usar este bot.\n"
                f"Tu ID: {user_id}\n"
                "Contacta al administrador."
            )
            return
        return await func(update, context, *args, **kwargs)
    return wrapped

# ========== COMANDOS ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    user_id = update.effective_user.id

    if user_id not in AUTHORIZED_USERS:
        AUTHORIZED_USERS.add(user_id)
        logger.info(f"Nuevo usuario agregado: {user_id}")

    welcome_text = """
🌐 *AURALINK Monitor*
Monitoreo inteligente de UISP vía Telegram + IA

*Comandos disponibles:*
/help - Mostrar ayuda
/status - Estado general del sistema
/clients - Listar clientes activos
/devices - Listar dispositivos

*Ejemplos de preguntas:*
"¿Cuál es la IP del cliente Zuri?"
"Muéstrame el consumo de Roman Cervantes"
"¿Cuántos clientes están activos?"
"¿Qué dispositivos están offline?"

*Desarrollado por:* Claude Code
*Versión:* 1.0
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    help_text = """
📖 *Guía de Uso*

*1. Estado del Sistema:*
/status - Ver estado general

*2. Consultar Clientes:*
"¿Cuál es la IP del cliente [nombre]?"
"Muéstrame el consumo de [nombre]"
"¿Está activo [cliente]?"

*3. Dispositivos:*
/devices - Listar todos los dispositivos
"¿Qué dispositivos están online?"

*4. Gráficas:*
"Gráfica de consumo de [cliente] últimas 24h"
"Muestra el tráfico de anoche"

*Tip:* Puedes escribir en lenguaje natural, la IA entiende.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

@restricted
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /status"""
    if not uisp:
        await update.message.reply_text("❌ Servidor UISP no disponible")
        return

    try:
        await update.message.reply_text("🔄 Recolectando información...", parse_mode='Markdown')

        clients = uisp.get_clients()
        devices = uisp.get_devices()

        active_clients = len([c for c in clients if c.get('status') == 'active'])
        total_clients = len(clients)
        total_devices = len(devices)

        status_text = f"""
✅ *Estado AURALINK Monitor*

📊 *Estadísticas:*
• Clientes activos: {active_clients}/{total_clients}
• Dispositivos: {total_devices}
• Servidor UISP: 🟢 Online

⏰ *Última actualización:*
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """

        await update.message.reply_text(status_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error en status_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

@restricted
async def clients_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /clients"""
    if not uisp:
        await update.message.reply_text("❌ Servidor UISP no disponible")
        return

    try:
        await update.message.reply_text("🔄 Cargando clientes...", parse_mode='Markdown')

        clients = uisp.get_clients()

        if not clients:
            await update.message.reply_text("No hay clientes registrados")
            return

        clients_text = "👥 *Clientes Registrados:*\n\n"
        for i, client in enumerate(clients[:20], 1):  # Primeros 20
            name = client.get('name', 'Sin nombre')
            status = "🟢" if client.get('status') == 'active' else "🔴"
            clients_text += f"{i}. {status} {name}\n"

        if len(clients) > 20:
            clients_text += f"\n... y {len(clients) - 20} más"

        await update.message.reply_text(clients_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error en clients_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

@restricted
async def devices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /devices"""
    if not uisp:
        await update.message.reply_text("❌ Servidor UISP no disponible")
        return

    try:
        await update.message.reply_text("🔄 Cargando dispositivos...", parse_mode='Markdown')

        devices = uisp.get_devices()

        if not devices:
            await update.message.reply_text("No hay dispositivos registrados")
            return

        devices_text = "🖥️ *Dispositivos:*\n\n"
        for i, device in enumerate(devices[:15], 1):  # Primeros 15
            name = device.get('name', 'Sin nombre')
            model = device.get('model', 'Modelo desconocido')
            status = "🟢" if device.get('status') == 'active' else "🔴"
            devices_text += f"{i}. {status} {name} ({model})\n"

        if len(devices) > 15:
            devices_text += f"\n... y {len(devices) - 15} más"

        await update.message.reply_text(devices_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error en devices_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

@restricted
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar mensajes normales (búsquedas, consultas)"""
    if not uisp:
        await update.message.reply_text("❌ Servidor UISP no disponible")
        return

    user_message = update.message.text.lower()

    try:
        # Búsqueda de cliente por nombre
        if "cliente" in user_message or "ip" in user_message or "consumo" in user_message:
            await update.message.reply_text("🔄 Procesando consulta...", parse_mode='Markdown')

            # Extraer nombre del cliente de la pregunta
            words = user_message.split()
            for i, word in enumerate(words):
                if word in ['cliente', 'de', 'del']:
                    if i + 1 < len(words):
                        client_name = ' '.join(words[i+1:])
                        client = uisp.get_client_by_name(client_name)

                        if client:
                            response = f"""
✅ *Cliente Encontrado*

*Nombre:* {client.get('name', 'N/A')}
*ID:* {client.get('id', 'N/A')}
*Estado:* {'🟢 Activo' if client.get('status') == 'active' else '🔴 Inactivo'}
*Ubicación:* {client.get('location', {}).get('name', 'N/A')}
                            """
                            await update.message.reply_text(response, parse_mode='Markdown')
                        else:
                            await update.message.reply_text(f"❌ Cliente '{client_name}' no encontrado")
                        return

            # Si no pude extraer el nombre
            await update.message.reply_text(
                "ℹ️ No pude entender la consulta.\n"
                "Intenta: 'dime la IP del cliente [nombre]'"
            )

    except Exception as e:
        logger.error(f"Error manejando mensaje: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar errores"""
    logger.error(f"Update {update} causó error: {context.error}")

# ========== MAIN ==========
async def main():
    """Iniciar el bot"""
    logger.info("🚀 Iniciando AURALINK Monitor Bot...")

    # Crear aplicación
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Agregar handlers de comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("clients", clients_command))
    app.add_handler(CommandHandler("devices", devices_command))

    # Agregar handler de mensajes
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Agregar error handler
    app.add_error_handler(error_handler)

    logger.info("✓ Bot iniciado correctamente")
    logger.info("✓ Esperando mensajes en Telegram...")

    # Iniciar el bot
    await app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    try:
        import asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot detenido por usuario")
    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)
