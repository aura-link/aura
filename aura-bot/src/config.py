"""Configuracion central de Aura Bot. Carga variables de .env y valida."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env desde la raiz del proyecto
_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path)


def _require(name: str) -> str:
    val = os.getenv(name, "").strip()
    if not val:
        print(f"ERROR: Variable de entorno requerida no encontrada: {name}")
        sys.exit(1)
    return val


# Telegram
TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_ADMIN_IDS: set[int] = {
    int(x.strip())
    for x in os.getenv("TELEGRAM_ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

# UISP
UISP_BASE_URL: str = _require("UISP_BASE_URL").rstrip("/")
UISP_NMS_TOKEN: str = _require("UISP_NMS_TOKEN")
UISP_VERIFY_SSL: bool = os.getenv("UISP_VERIFY_SSL", "true").lower() == "true"

# MikroTik
MIKROTIK_HOST: str = os.getenv("MIKROTIK_HOST", "10.147.17.11")
MIKROTIK_PORT: int = int(os.getenv("MIKROTIK_PORT", "8728"))
MIKROTIK_USER: str = os.getenv("MIKROTIK_USER", "admin")
MIKROTIK_PASSWORD: str = os.getenv("MIKROTIK_PASSWORD", "")

# Anthropic / Claude
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# Base de datos
DB_PATH: str = os.getenv("DB_PATH", "data/aura.db")

# Constantes
MAX_CONVERSATION_HISTORY: int = 20
API_TIMEOUT: int = 30
CACHE_TTL: int = 60  # segundos

# Monitoreo proactivo
MONITOR_ENABLED: bool = os.getenv("MONITOR_ENABLED", "true").lower() == "true"
MONITOR_INTERVAL: int = int(os.getenv("MONITOR_INTERVAL", "120"))  # segundos entre polls
NOTIFICATION_COOLDOWN: int = int(os.getenv("NOTIFICATION_COOLDOWN", "1800"))  # 30 min anti-spam
ZONE_REFRESH_INTERVAL: int = int(os.getenv("ZONE_REFRESH_INTERVAL", "900"))  # 15 min rebuild zonas
