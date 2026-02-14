"""Handlers para /start, /help, /menu."""

from telegram import Update
from telegram.ext import ContextTypes
from src.bot.roles import get_role, Role
from src.bot import keyboards


WELCOME_MSG = (
    "👋 *Hola! Soy Aura*, tu asistente virtual de AURALINK.\n\n"
    "Puedo ayudarte con:\n"
    "• Consultar tu saldo y pagos\n"
    "• Ver el estado de tu servicio\n"
    "• Diagnosticar tu conexion\n"
    "• Reportar problemas\n\n"
    "Tambien puedes escribirme cualquier pregunta en español.\n\n"
    "Usa /help para ver todos los comandos."
)

HELP_CUSTOMER = (
    "📋 *Comandos disponibles:*\n\n"
    "💰 /misaldo — Saldo y estado de pago\n"
    "📡 /miservicio — Plan, velocidad, estado\n"
    "📶 /miconexion — Señal, PPPoE, diagnostico\n"
    "🔧 /reportar — Diagnostico automatico\n"
    "🆘 /soporte — Escalar a tecnico\n"
    "📋 /menu — Menu principal\n\n"
    "💬 O escribe cualquier pregunta!"
)

HELP_ADMIN = (
    "🛠 *Comandos de administrador:*\n\n"
    "🌐 /red — Overview de la red\n"
    "👥 /clientes — Resumen de clientes\n"
    "🔍 /buscar <nombre> — Buscar cliente\n"
    "📡 /dispositivos — Dispositivos offline\n"
    "📊 /pppoe — Sesiones PPPoE activas\n"
    "🏓 /diagnostico <ip> — Ping desde MikroTik\n"
    "⚠️ /caidas — Outages activos\n"
)

HELP_GUEST = (
    "Para acceder a tus datos, primero necesitas vincular tu cuenta.\n\n"
    "Usa /vincular para comenzar."
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message:
        return

    db = context.bot_data["db"]
    link = await db.get_customer_link(user.id)
    role = get_role(user.id, is_linked=link is not None)

    if role == Role.ADMIN:
        kb = keyboards.main_menu_admin()
    elif role == Role.CUSTOMER:
        kb = keyboards.main_menu_customer()
    else:
        kb = keyboards.main_menu_guest()

    await update.message.reply_text(
        WELCOME_MSG, parse_mode="Markdown", reply_markup=kb
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message:
        return

    db = context.bot_data["db"]
    link = await db.get_customer_link(user.id)
    role = get_role(user.id, is_linked=link is not None)

    text = HELP_CUSTOMER
    if role == Role.ADMIN:
        text = HELP_CUSTOMER + "\n" + HELP_ADMIN
    elif role == Role.GUEST:
        text = HELP_GUEST

    await update.message.reply_text(text, parse_mode="Markdown")


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or not update.message:
        return

    db = context.bot_data["db"]
    link = await db.get_customer_link(user.id)
    role = get_role(user.id, is_linked=link is not None)

    if role == Role.ADMIN:
        kb = keyboards.main_menu_admin()
    elif role == Role.CUSTOMER:
        kb = keyboards.main_menu_customer()
    else:
        kb = keyboards.main_menu_guest()

    await update.message.reply_text(
        "📋 *Menu principal:*", parse_mode="Markdown", reply_markup=kb
    )
