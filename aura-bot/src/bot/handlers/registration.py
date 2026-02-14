"""Flujo de vinculacion Telegram → CRM (ConversationHandler)."""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from rapidfuzz import fuzz
from src.bot import keyboards
from src.utils.logger import log

# States
WAITING_NAME, WAITING_SELECTION = range(2)


async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inicia el flujo de vinculacion."""
    user = update.effective_user
    if not user:
        return ConversationHandler.END

    # Check if already linked
    db = context.bot_data["db"]
    link = await db.get_customer_link(user.id)
    if link:
        msg = update.message or update.callback_query.message
        await msg.reply_text(
            f"✅ Ya estas vinculado como *{link['crm_client_name']}*.\n\n"
            "Si necesitas cambiar tu cuenta, contacta a soporte.",
            parse_mode="Markdown",
        )
        return ConversationHandler.END

    msg = update.message or update.callback_query.message
    if update.callback_query:
        await update.callback_query.answer()

    await msg.reply_text(
        "🔗 *Vinculacion de cuenta*\n\n"
        "Por favor, escribe tu *nombre completo* tal como esta registrado en AURALINK.\n\n"
        "Ejemplo: Juan Perez Garcia\n\n"
        "Escribe /cancelar para cancelar.",
        parse_mode="Markdown",
    )
    return WAITING_NAME


async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recibe el nombre y busca en CRM con fuzzy matching."""
    user = update.effective_user
    if not user or not update.message:
        return ConversationHandler.END

    query = update.message.text.strip()
    if len(query) < 3:
        await update.message.reply_text("Por favor escribe al menos 3 caracteres.")
        return WAITING_NAME

    crm = context.bot_data["uisp_crm"]
    clients = await crm.get_clients()

    # Fuzzy match
    scored = []
    for c in clients:
        name = crm.get_client_name(c)
        score = fuzz.token_sort_ratio(query.lower(), name.lower())
        if score >= 50:
            scored.append((score, c, name))

    scored.sort(key=lambda x: x[0], reverse=True)
    matches = scored[:5]

    if not matches:
        await update.message.reply_text(
            f"❌ No encontre cuentas similares a '{query}'.\n\n"
            "Intenta de nuevo con tu nombre completo, o escribe /cancelar."
        )
        return WAITING_NAME

    # Store matches in context for selection
    context.user_data["registration_matches"] = [
        {"id": c.get("id"), "name": name, "score": score}
        for score, c, name in matches
    ]

    buttons = []
    for i, (score, c, name) in enumerate(matches):
        cid = c.get("id", "")
        pct = f"{score}%"
        buttons.append([InlineKeyboardButton(f"{name} ({pct})", callback_data=f"link_{cid}")])
    buttons.append([InlineKeyboardButton("❌ Ninguno de estos", callback_data="link_none")])

    await update.message.reply_text(
        "🔍 *Encontre estas cuentas:*\n\nSelecciona la tuya:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return WAITING_SELECTION


async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa la seleccion del cliente."""
    query = update.callback_query
    if not query:
        return ConversationHandler.END

    await query.answer()
    data = query.data

    if data == "link_none":
        await query.message.reply_text(
            "No hay problema. Intenta de nuevo con /vincular o contacta a soporte."
        )
        return ConversationHandler.END

    if not data.startswith("link_"):
        return WAITING_SELECTION

    client_id = data[5:]  # Remove "link_" prefix
    user = update.effective_user

    # Get client info from CRM
    crm = context.bot_data["uisp_crm"]
    client = await crm.get_client(client_id)

    if not client:
        await query.message.reply_text("❌ Error al obtener datos del cliente. Intenta de nuevo.")
        return ConversationHandler.END

    client_name = crm.get_client_name(client)

    # Save the link
    db = context.bot_data["db"]
    await db.link_customer(
        telegram_user_id=user.id,
        telegram_username=user.username,
        crm_client_id=client_id,
        crm_client_name=client_name,
    )

    log.info("Cliente vinculado: Telegram %d -> CRM %s (%s)", user.id, client_id, client_name)

    await query.message.reply_text(
        f"✅ *Cuenta vinculada exitosamente!*\n\n"
        f"Bienvenido/a, *{client_name}*!\n\n"
        "Ahora puedes usar:\n"
        "💰 /misaldo — Ver tu saldo\n"
        "📡 /miservicio — Ver tu servicio\n"
        "📶 /miconexion — Diagnosticar tu conexion\n\n"
        "O simplemente escríbeme cualquier pregunta. 😊",
        parse_mode="Markdown",
        reply_markup=keyboards.main_menu_customer(),
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancela el flujo de registro."""
    if update.message:
        await update.message.reply_text("Registro cancelado. Usa /vincular cuando quieras intentar de nuevo.")
    return ConversationHandler.END


def get_registration_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CommandHandler("vincular", start_registration),
            CallbackQueryHandler(start_registration, pattern="^cmd_vincular$"),
        ],
        states={
            WAITING_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name),
            ],
            WAITING_SELECTION: [
                CallbackQueryHandler(handle_selection, pattern="^link_"),
            ],
        },
        fallbacks=[
            CommandHandler("cancelar", cancel),
        ],
    )
