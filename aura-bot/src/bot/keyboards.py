"""Teclados inline para Telegram."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_customer() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Mi Saldo", callback_data="cmd_misaldo"),
         InlineKeyboardButton("📡 Mi Servicio", callback_data="cmd_miservicio")],
        [InlineKeyboardButton("📶 Mi Conexion", callback_data="cmd_miconexion"),
         InlineKeyboardButton("🔧 Reportar", callback_data="cmd_reportar")],
        [InlineKeyboardButton("🆘 Soporte", callback_data="cmd_soporte")],
    ])


def main_menu_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Red", callback_data="cmd_red"),
         InlineKeyboardButton("👥 Clientes", callback_data="cmd_clientes")],
        [InlineKeyboardButton("📡 Dispositivos", callback_data="cmd_dispositivos"),
         InlineKeyboardButton("📊 PPPoE", callback_data="cmd_pppoe")],
        [InlineKeyboardButton("⚠️ Caidas", callback_data="cmd_caidas")],
    ])


def main_menu_guest() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Vincular mi cuenta", callback_data="cmd_vincular")],
    ])


def client_selection(clients: list[dict]) -> InlineKeyboardMarkup:
    """Genera teclado para seleccionar cliente CRM durante registro."""
    buttons = []
    for c in clients[:5]:
        name = c.get("name", "Sin nombre")
        cid = c.get("id", "")
        buttons.append([InlineKeyboardButton(name, callback_data=f"link_{cid}")])
    buttons.append([InlineKeyboardButton("❌ Ninguno", callback_data="link_none")])
    return InlineKeyboardMarkup(buttons)


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Si", callback_data="confirm_yes"),
         InlineKeyboardButton("❌ No", callback_data="confirm_no")],
    ])
