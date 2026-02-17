"""Teclados inline para Telegram."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_customer() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Mi Saldo", callback_data="cmd_misaldo"),
         InlineKeyboardButton("📡 Mi Servicio", callback_data="cmd_miservicio")],
        [InlineKeyboardButton("📶 Mi Conexion", callback_data="cmd_miconexion"),
         InlineKeyboardButton("🔧 Reportar", callback_data="cmd_reportar")],
        [InlineKeyboardButton("💳 Reportar Pago", callback_data="cmd_reportar_pago")],
        [InlineKeyboardButton("🆘 Soporte", callback_data="cmd_soporte")],
    ])


def main_menu_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 Red", callback_data="cmd_red"),
         InlineKeyboardButton("👥 Clientes", callback_data="cmd_clientes")],
        [InlineKeyboardButton("📡 Dispositivos", callback_data="cmd_dispositivos"),
         InlineKeyboardButton("📊 PPPoE", callback_data="cmd_pppoe")],
        [InlineKeyboardButton("⚠️ Caidas", callback_data="cmd_caidas"),
         InlineKeyboardButton("🚨 Incidentes", callback_data="cmd_incidentes")],
        [InlineKeyboardButton("📍 Zonas", callback_data="cmd_zonas"),
         InlineKeyboardButton("📊 Monitor", callback_data="cmd_monitor")],
        [InlineKeyboardButton("🛠 Panel Admin", callback_data="cmd_admin")],
    ])


def admin_panel() -> InlineKeyboardMarkup:
    """Menu completo de administracion con todas las herramientas."""
    return InlineKeyboardMarkup([
        # -- Red --
        [InlineKeyboardButton("── Red & Monitoreo ──", callback_data="noop")],
        [InlineKeyboardButton("🌐 Estado Red", callback_data="cmd_red"),
         InlineKeyboardButton("📡 Offline", callback_data="cmd_dispositivos")],
        [InlineKeyboardButton("📊 PPPoE", callback_data="cmd_pppoe"),
         InlineKeyboardButton("⚠️ Caidas", callback_data="cmd_caidas")],
        [InlineKeyboardButton("📊 Monitor", callback_data="cmd_monitor"),
         InlineKeyboardButton("🚨 Incidentes", callback_data="cmd_incidentes")],
        [InlineKeyboardButton("📍 Zonas", callback_data="cmd_zonas"),
         InlineKeyboardButton("🔧 Mantenimiento", callback_data="cmd_mantenimiento")],
        [InlineKeyboardButton("📡 TP-Link", callback_data="cmd_tplink")],
        # -- Clientes --
        [InlineKeyboardButton("── Clientes ──", callback_data="noop")],
        [InlineKeyboardButton("👥 Clientes CRM", callback_data="cmd_clientes"),
         InlineKeyboardButton("🔍 Buscar", callback_data="cmd_buscar_help")],
        # -- Gestion --
        [InlineKeyboardButton("── Gestion Rapida ──", callback_data="noop")],
        [InlineKeyboardButton("➕ Alta Cliente", callback_data="cmd_alta_help"),
         InlineKeyboardButton("📋 Cambiar Plan", callback_data="cmd_plan_help")],
        [InlineKeyboardButton("🏓 Diagnostico", callback_data="cmd_diag_help")],
        # -- Cobranza --
        [InlineKeyboardButton("── Cobranza ──", callback_data="noop")],
        [InlineKeyboardButton("💳 Pagos Pendientes", callback_data="cmd_pagos"),
         InlineKeyboardButton("🔴 Morosos", callback_data="cmd_morosos")],
    ])


def main_menu_guest() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Vincular mi cuenta", callback_data="cmd_vincular")],
    ])


def zone_selection() -> InlineKeyboardMarkup:
    """Teclado de zonas para registro de clientes (2 por fila, ordenadas por frecuencia)."""
    zones = [
        ("Tomatlan", "TML"), ("La Cumbre", "CBR"),
        ("Jose Maria Pino Suarez", "PNS"), ("La Gloria", "GLR"),
        ("El Coco", "COC"), ("El Tule", "TUL"),
        ("Nahuapa", "NAH"), ("Benito Juarez", "BJZ"),
        ("Centro", "CTR"), ("Campamento SAGAR", "SGR"),
        ("La Cruz de Loreto", "CRL"), ("Jalisco", "JAL"),
    ]
    buttons = []
    for i in range(0, len(zones), 2):
        row = []
        for name, abbr in zones[i:i+2]:
            row.append(InlineKeyboardButton(name, callback_data=f"zone_{abbr}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton("Otra zona", callback_data="zone_OTHER")])
    return InlineKeyboardMarkup(buttons)


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
