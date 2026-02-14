"""Formateo para moneda MXN, fechas en español, y texto general."""

from datetime import datetime, timezone


def format_mxn(amount: float | int | None) -> str:
    if amount is None:
        return "$0.00 MXN"
    return f"${amount:,.2f} MXN"


def format_signal(signal_dbm: float | int | None) -> str:
    if signal_dbm is None:
        return "Sin datos"
    val = int(signal_dbm)
    if val >= -60:
        quality = "Excelente"
    elif val >= -70:
        quality = "Buena"
    elif val >= -75:
        quality = "Aceptable"
    elif val >= -80:
        quality = "Baja"
    else:
        quality = "Mala"
    return f"{val} dBm ({quality})"


def format_uptime(seconds: int | float | None) -> str:
    if not seconds:
        return "Sin datos"
    s = int(seconds)
    days, s = divmod(s, 86400)
    hours, s = divmod(s, 3600)
    mins, _ = divmod(s, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if mins:
        parts.append(f"{mins}m")
    return " ".join(parts) or "< 1m"


def format_datetime(iso_str: str | None) -> str:
    if not iso_str:
        return "Sin datos"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except (ValueError, AttributeError):
        return str(iso_str)


def format_speed(bps: float | int | None) -> str:
    if not bps:
        return "Sin datos"
    mbps = bps / 1_000_000
    if mbps >= 1:
        return f"{mbps:.0f} Mbps"
    kbps = bps / 1_000
    return f"{kbps:.0f} Kbps"


def truncate(text: str, max_len: int = 4000) -> str:
    """Trunca texto para que quepa en un mensaje de Telegram."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def status_emoji(status: str | None) -> str:
    mapping = {
        "active": "🟢",
        "connected": "🟢",
        "online": "🟢",
        "inactive": "🔴",
        "disconnected": "🔴",
        "offline": "🔴",
        "suspended": "🟡",
        "unknown": "⚪",
    }
    return mapping.get((status or "").lower(), "⚪")
