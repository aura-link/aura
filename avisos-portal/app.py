#!/usr/bin/env python3
"""Avisos Portal - Announcement captive portal for AURALINK clients.

Serves dynamic announcements to clients and handles dismiss via
MikroTik address-list removal over SSH. Admin API for bot integration.
Verifies Telegram registration against bot's SQLite DB.
Supports 4 modes: soft (always internet), medium (strict verify + temp dismiss),
strict (5min temp dismiss for unregistered), persistent (same as strict, indefinite).
"""
import asyncio
import json
import logging
import os
import sqlite3
from html import escape
from pathlib import Path

import re

from aiohttp import web

_IP_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")


def _valid_ip(ip: str) -> bool:
    return bool(_IP_RE.match(ip))

MIKROTIK_IP = "10.147.17.11"
MIKROTIK_USER = "admin"
ALLOWED_PREFIXES = ("10.10.0.", "10.10.1.", "10.10.2.")
STATIC_DIR = Path(__file__).parent / "static"
DATA_DIR = Path(__file__).parent / "data"
CURRENT_FILE = DATA_DIR / "current.json"
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "auralink-avisos-2026")
BOT_DB_PATH = os.getenv("BOT_DB_PATH", "/app/botdata/aura.db")
SYNC_INTERVAL = 300  # 5 minutes

# Mode schedule: checked top-down, first match wins (must match bot's schedule)
from datetime import datetime, timezone, timedelta
_TZ = timezone(timedelta(hours=-6))  # CST Mexico
_MODE_SCHEDULE = [
    ((4, 1),  "persistent"),
    ((3, 26), "strict"),
    ((3, 16), "medium"),
    ((3, 1),  "soft"),
]


def _effective_mode(state: dict | None) -> str:
    """Determine mode from date, overriding whatever the state file says."""
    now = datetime.now(_TZ)
    for (month, day), mode in _MODE_SCHEDULE:
        if (now.month, now.day) >= (month, day):
            return mode
    return state.get("mode", "soft") if state else "soft"

# Accounts that should NEVER see avisos (not real clients)
EXCLUDED_PPP_NAMES = {
    "martinpintort", "casacristinat", "cristinavillasenorcc", "mabilaliat",
    "deportest", "diftomatlan", "javieraraizat", "lauracumbre", "marciat",
    "oscarsunyt", "pelonc", "peloncoco", "tiagloria", "renecumbre",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("avisos")

# Color themes: gradient CSS pairs
COLOR_THEMES = {
    "blue": ("linear-gradient(135deg,#2AABEE,#1a8fd1)", "rgba(42,171,238,0.1)", "rgba(42,171,238,0.3)"),
    "orange": ("linear-gradient(135deg,#f97316,#ea580c)", "rgba(249,115,22,0.1)", "rgba(249,115,22,0.3)"),
    "green": ("linear-gradient(135deg,#22c55e,#16a34a)", "rgba(34,197,94,0.1)", "rgba(34,197,94,0.3)"),
    "red": ("linear-gradient(135deg,#ef4444,#dc2626)", "rgba(239,68,68,0.1)", "rgba(239,68,68,0.3)"),
}


def _load_state() -> dict | None:
    """Load current announcement state from disk."""
    if not CURRENT_FILE.exists():
        return None
    try:
        data = json.loads(CURRENT_FILE.read_text(encoding="utf-8"))
        if data.get("active"):
            return data
    except (json.JSONDecodeError, OSError) as e:
        log.error("Error reading current.json: %s", e)
    return None


def _save_state(data: dict):
    """Save announcement state to disk."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CURRENT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _check_admin_token(request) -> bool:
    return request.headers.get("X-Admin-Token") == ADMIN_TOKEN


def _names_match(ppp_name: str, crm_name: str) -> bool:
    """Check if a PPPoE username matches a CRM client name.

    Uses multiple strategies: exact, substring, token overlap.
    Both inputs should be pre-normalized (lowercase, no spaces).
    """
    if not ppp_name or not crm_name:
        return False
    if crm_name == ppp_name or crm_name in ppp_name or ppp_name in crm_name:
        return True
    # Token overlap: check if 4-char tokens from ppp match crm
    ppp_tokens = [ppp_name[i:i+4] for i in range(0, len(ppp_name)-3)]
    if ppp_tokens:
        match_count = sum(1 for t in ppp_tokens if t in crm_name)
        if match_count >= len(ppp_tokens) * 0.5:
            return True
    return False


def _check_registered(ppp_name: str) -> bool:
    """Check if a PPPoE secret name has a linked Telegram account in the bot's DB."""
    if not Path(BOT_DB_PATH).exists():
        log.warning("Bot DB not found at %s", BOT_DB_PATH)
        return False
    # Excluded accounts count as "registered" to bypass the portal
    if ppp_name.lower() in EXCLUDED_PPP_NAMES:
        return True
    try:
        conn = sqlite3.connect(f"file:{BOT_DB_PATH}?mode=ro", uri=True)
        cursor = conn.execute("SELECT crm_client_name FROM customer_links")
        ppp_lower = ppp_name.lower().replace(" ", "")
        for row in cursor:
            crm_name = (row[0] or "").lower().replace(" ", "")
            if _names_match(ppp_lower, crm_name):
                conn.close()
                return True
        conn.close()
    except Exception as e:
        log.error("Error checking bot DB: %s", e)
    return False


async def _get_ppp_name(client_ip: str) -> str | None:
    """Get PPPoE secret name for a client IP via MikroTik SSH (terse output)."""
    if not _valid_ip(client_ip):
        return None
    mk_cmd = f"/ppp/active/print terse where address={client_ip}"
    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
            "-o", "BatchMode=yes", f"{MIKROTIK_USER}@{MIKROTIK_IP}", mk_cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        if proc.returncode == 0:
            for part in stdout.decode().strip().split():
                if part.startswith("name="):
                    return part[5:]
    except Exception as e:
        log.error("Error getting PPP name for %s: %s", client_ip, e)
    return None


async def _remove_from_avisos(client_ip: str) -> bool:
    """Remove client IP from avisos address-list only."""
    if not _valid_ip(client_ip):
        return False
    mk_cmd = f"/ip firewall address-list remove [find where list=avisos address={client_ip}]"
    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
            "-o", "BatchMode=yes", f"{MIKROTIK_USER}@{MIKROTIK_IP}", mk_cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=10)
        return proc.returncode == 0
    except Exception:
        return False


async def _temp_dismiss_24h(client_ip: str, ppp_name: str | None) -> bool:
    """Remove from avisos and add to avisos-visto permanently.
    The bot's aviso scheduler clears avisos-visto every 3 days when re-publishing,
    so clients will see the aviso again on the next cycle. Permanent entries survive reboots."""
    if not _valid_ip(client_ip):
        return False
    comment = re.sub(r'[^a-zA-Z0-9_. -]', '', ppp_name or "")
    mk_cmd = (
        f'/ip firewall address-list remove [find where list=avisos address={client_ip}]; '
        f'/ip firewall address-list remove [find where list=avisos-visto address={client_ip}]; '
        f'/ip firewall address-list add list=avisos-visto address={client_ip} comment="{comment}"'
    )
    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
            "-o", "BatchMode=yes", f"{MIKROTIK_USER}@{MIKROTIK_IP}", mk_cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=15)
        return proc.returncode == 0
    except Exception:
        return False


async def _temp_dismiss_5min(client_ip: str, ppp_name: str | None) -> bool:
    """Remove from avisos and add to avisos-visto with 5-minute timeout.
    Dynamic entry (flag D) that auto-expires after 5 min.
    When it expires, populate-avisos re-adds the client on its next cycle."""
    if not _valid_ip(client_ip):
        return False
    comment = re.sub(r'[^a-zA-Z0-9_. -]', '', ppp_name or "")
    mk_cmd = (
        f'/ip firewall address-list remove [find where list=avisos address={client_ip}]; '
        f'/ip firewall address-list remove [find where list=avisos-visto address={client_ip}]; '
        f'/ip firewall address-list add list=avisos-visto address={client_ip} timeout=00:05:00 comment="{comment}"'
    )
    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
            "-o", "BatchMode=yes", f"{MIKROTIK_USER}@{MIKROTIK_IP}", mk_cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=15)
        return proc.returncode == 0
    except Exception:
        return False


async def _permanent_dismiss(client_ip: str, ppp_name: str | None) -> bool:
    """Remove from avisos and add to avisos-visto (permanent dismiss)."""
    if not _valid_ip(client_ip):
        return False
    comment = re.sub(r'[^a-zA-Z0-9_. -]', '', ppp_name or "")
    mk_cmd = (
        f'/ip firewall address-list remove [find where list=avisos address={client_ip}]; '
        f'/ip firewall address-list add list=avisos-visto address={client_ip} comment="{comment}"'
    )
    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5",
            "-o", "BatchMode=yes", f"{MIKROTIK_USER}@{MIKROTIK_IP}", mk_cmd,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=15)
        return proc.returncode == 0
    except Exception:
        return False


def _render_html(state: dict, ppp_name: str = "") -> str:
    """Render dynamic HTML from announcement state."""
    title = escape(state.get("title", "Aviso Importante"))
    icon = state.get("icon", "&#128225;")
    body = escape(state.get("body", ""))
    dismiss_text = escape(state.get("dismiss_text", "Entendido"))
    color_theme = state.get("color_theme", "blue")
    details = state.get("details", [])
    show_bank = state.get("show_bank_info", False)
    show_telegram = state.get("show_telegram_bot", True)
    verify_registro = state.get("verify_registro", False)

    gradient, bg_light, border_light = COLOR_THEMES.get(color_theme, COLOR_THEMES["blue"])

    # Allow \n in body → <br>
    body = body.replace("\n", "<br>")

    # Build details HTML
    details_html = ""
    if details:
        items = "\n".join(
            f'        <li><span class="detail-dot"></span>{escape(d)}</li>' for d in details
        )
        details_html = f"""
    <div class="section anim-section">
      <h2 class="section-title">Detalles</h2>
      <ul class="detail-list">
{items}
      </ul>
    </div>"""

    # Build features HTML (list with custom icons)
    features = state.get("features", [])
    features_html = ""
    if features:
        items = "\n".join(
            f'        <li><span class="feat-icon">{f.get("icon", "&#10003;")}</span><span class="feat-text">{escape(f.get("text", ""))}</span></li>'
            for f in features
        )
        features_html = f"""
    <div class="section anim-section">
      <h2 class="section-title">Beneficios</h2>
      <ul class="feat-list">
{items}
      </ul>
    </div>"""

    # Build steps HTML (numbered list)
    steps = state.get("steps", [])
    steps_html = ""
    if steps:
        items = "\n".join(
            f'        <li><span class="step-num">{i+1}</span><span class="step-text">{escape(s)}</span></li>'
            for i, s in enumerate(steps)
        )
        steps_html = f"""
    <div class="section anim-section">
      <h2 class="section-title">Como registrarte</h2>
      <ol class="steps-list">
{items}
      </ol>
    </div>"""

    # Bank info section
    bank_html = ""
    if show_bank:
        bank_html = """
    <div class="section anim-section">
      <h2 class="section-title">Datos para pago</h2>
      <div class="bank-card">
        <div class="bank-row">
          <span class="bank-label">Banco</span>
          <span class="bank-value">BBVA Bancomer</span>
        </div>
        <div class="bank-row">
          <span class="bank-label">Titular</span>
          <span class="bank-value">Carlos E. Valenzuela R.</span>
        </div>
        <div class="bank-row">
          <span class="bank-label">Cuenta</span>
          <span class="bank-value"><span class="mono">285 958 9260</span> <button class="copy-btn" onclick="copy('2859589260')"><span class="copy-icon">&#128203;</span> Copiar</button></span>
        </div>
        <div class="bank-row">
          <span class="bank-label">Tarjeta</span>
          <span class="bank-value"><span class="mono">4152 3144 8622 9639</span> <button class="copy-btn" onclick="copy('4152314486229639')"><span class="copy-icon">&#128203;</span> Copiar</button></span>
        </div>
        <div class="bank-row">
          <span class="bank-label">CLABE</span>
          <span class="bank-value"><span class="mono">012400028595892607</span> <button class="copy-btn" onclick="copy('012400028595892607')"><span class="copy-icon">&#128203;</span> Copiar</button></span>
        </div>
      </div>
    </div>"""

    # Telegram section — with deep link if ppp_name is known
    telegram_html = ""
    if show_telegram:
        if ppp_name:
            # Deep link: one tap to open Telegram and auto-identify
            deep_link = f"https://t.me/auralinkmonitor_bot?start=link_{ppp_name}"
            telegram_html = f"""
    <div class="section anim-section">
      <h2 class="section-title">Vinculate en 1 paso</h2>
      <div class="tg-card">
        <div class="tg-hero-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z" fill="#2AABEE"/></svg>
        </div>
        <p class="tg-subtitle">Presiona el boton para vincular tu cuenta automaticamente:</p>
        <div class="tg-warning">
          <span class="tg-warning-icon">&#9888;</span>
          <p><strong>Importante:</strong> El numero de Telegram de este telefono quedara vinculado a la cuenta de AURALINK. Solo debe registrarse el <strong>titular del servicio</strong>.</p>
        </div>
        <a href="{deep_link}" class="tg-hero-btn" target="_blank">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" style="vertical-align:middle;margin-right:8px"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z" fill="white"/></svg>
          Vincular en Telegram
        </a>
        <p class="tg-hint">Se abrira Telegram con tu cuenta pre-identificada</p>
        <div class="tg-download">
          <p class="tg-dl-label">No tienes Telegram? Descargalo gratis:</p>
          <div class="tg-dl-btns">
            <a href="https://play.google.com/store/apps/details?id=org.telegram.messenger" target="_blank" class="tg-dl-btn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="#2AABEE"><path d="M17.523 2H6.477L2 6.477v11.046L6.477 22h11.046L22 17.523V6.477L17.523 2zM12 17.09c-2.81 0-5.09-2.28-5.09-5.09S9.19 6.91 12 6.91s5.09 2.28 5.09 5.09-2.28 5.09-5.09 5.09z"/></svg>
              Android
            </a>
            <a href="https://apps.apple.com/app/telegram-messenger/id686449807" target="_blank" class="tg-dl-btn">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="#2AABEE"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83z"/></svg>
              iPhone
            </a>
          </div>
          <p class="tg-dl-hint">Instala Telegram y luego presiona el boton de arriba</p>
        </div>
      </div>
    </div>"""
        else:
            telegram_html = """
    <div class="section anim-section">
      <h2 class="section-title">Bot de Telegram</h2>
      <div class="tg-card">
        <div class="tg-hero-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z" fill="#2AABEE"/></svg>
        </div>
        <p class="tg-subtitle">Busca en Telegram:</p>
        <div class="tg-username-box">
          <span class="tg-username">@auralinkmonitor_bot</span>
          <button class="copy-btn" onclick="copy('auralinkmonitor_bot')"><span class="copy-icon">&#128203;</span> Copiar</button>
        </div>
        <p class="tg-alias">Puede aparecer como <strong>AURA</strong></p>
        <a href="https://t.me/auralinkmonitor_bot" class="tg-hero-btn" target="_blank">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" style="vertical-align:middle;margin-right:8px"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z" fill="white"/></svg>
          Abrir en Telegram
        </a>
      </div>
    </div>"""

    # Mode determined by date (real-time, independent of bot's publish cycle)
    mode = _effective_mode(state)

    if mode == "soft":
        buttons_html = """
    <div class="btn-group">
      <button class="entendido-btn" onclick="softVerify()" id="btn-verify">Ya me registr&eacute;</button>
      <button class="later-btn" onclick="dismissTemp()" id="btn-later">Lo har&eacute; despu&eacute;s</button>
    </div>"""
    elif mode == "medium":
        buttons_html = """
    <div class="btn-group">
      <button class="entendido-btn" onclick="verifyRegistro()" id="btn-verify">Ya me registr&eacute;</button>
      <button class="later-btn" onclick="dismissTemp()" id="btn-later">Lo har&eacute; despu&eacute;s</button>
      <div id="error-msg" class="error-msg"></div>
    </div>"""
    elif mode in ("strict", "persistent"):
        buttons_html = """
    <div class="btn-group">
      <button class="entendido-btn" onclick="verifyRegistro()" id="btn-verify">Ya me registr&eacute;</button>
      <div id="error-msg" class="error-msg"></div>
    </div>"""
    else:
        buttons_html = f"""
    <div class="btn-group">
      <button class="entendido-btn" onclick="dismiss()">{dismiss_text}</button>
      <p class="btn-hint">Al presionar, este aviso no aparecera de nuevo</p>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>AURALINK - {title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}

/* --- Base & Typography --- */
body{{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;
  background:#060a1a;
  color:#e2e8f0;
  min-height:100vh;
  min-height:100dvh;
  display:flex;
  align-items:center;
  justify-content:center;
  padding:0;
  -webkit-font-smoothing:antialiased;
  -moz-osx-font-smoothing:grayscale;
  overflow-x:hidden
}}
body::before{{
  content:'';
  position:fixed;
  top:0;left:0;right:0;bottom:0;
  background:
    radial-gradient(ellipse 80% 50% at 50% -20%, rgba(42,171,238,0.15), transparent),
    radial-gradient(ellipse 60% 40% at 80% 100%, rgba(42,171,238,0.08), transparent);
  pointer-events:none;
  z-index:0
}}

/* --- Container --- */
.container{{
  position:relative;
  z-index:1;
  max-width:440px;
  width:100%;
  min-height:100vh;
  min-height:100dvh;
  background:rgba(14,17,40,0.85);
  backdrop-filter:blur(40px);
  -webkit-backdrop-filter:blur(40px);
  overflow:hidden;
  display:flex;
  flex-direction:column
}}
@media(min-width:480px){{
  .container{{
    min-height:auto;
    border-radius:24px;
    margin:20px auto;
    box-shadow:0 25px 80px rgba(0,0,0,0.6),0 0 0 1px rgba(42,171,238,0.1)
  }}
  body{{padding:20px}}
}}

/* --- Header --- */
.header{{
  position:relative;
  padding:40px 24px 32px;
  text-align:center;
  overflow:hidden
}}
.header::before{{
  content:'';
  position:absolute;
  top:0;left:0;right:0;bottom:0;
  background:{gradient};
  opacity:0.9
}}
.header::after{{
  content:'';
  position:absolute;
  bottom:0;left:0;right:0;
  height:60px;
  background:linear-gradient(to top,rgba(14,17,40,0.85),transparent);
  z-index:1
}}
.header-content{{
  position:relative;
  z-index:2
}}
.brand{{
  display:inline-flex;
  align-items:center;
  gap:6px;
  font-size:11px;
  font-weight:600;
  letter-spacing:3px;
  text-transform:uppercase;
  color:rgba(255,255,255,0.7);
  margin-bottom:16px
}}
.brand-dot{{
  width:6px;height:6px;
  border-radius:50%;
  background:#fff;
  opacity:0.5;
  display:inline-block
}}
.logo{{font-size:44px;margin-bottom:12px;filter:drop-shadow(0 4px 12px rgba(0,0,0,0.3))}}
.header h1{{
  font-size:24px;
  font-weight:800;
  color:#fff;
  margin-bottom:4px;
  letter-spacing:-0.3px;
  text-shadow:0 2px 12px rgba(0,0,0,0.3)
}}
.header-sub{{
  font-size:13px;
  color:rgba(255,255,255,0.75);
  font-weight:400
}}

/* --- Body --- */
.body{{padding:24px 20px 0;flex:1}}
@media(min-width:360px){{.body{{padding:28px 24px 0}}}}

/* --- Announce Card --- */
.announce{{
  background:{bg_light};
  border:1px solid {border_light};
  border-radius:16px;
  padding:20px;
  margin-bottom:24px;
  text-align:center;
  position:relative;
  overflow:hidden
}}
.announce::before{{
  content:'';
  position:absolute;
  top:0;left:50%;
  transform:translateX(-50%);
  width:60px;height:3px;
  border-radius:2px;
  background:{gradient}
}}
.announce p{{
  font-size:15px;
  line-height:1.7;
  color:#cbd5e1
}}

/* --- Section --- */
.section{{margin-bottom:24px}}
.section-title{{
  font-size:11px;
  text-transform:uppercase;
  letter-spacing:2px;
  font-weight:700;
  color:#64748b;
  margin-bottom:16px;
  padding-left:2px
}}

/* --- Details List --- */
.detail-list{{list-style:none}}
.detail-list li{{
  display:flex;
  align-items:flex-start;
  gap:12px;
  padding:10px 0;
  font-size:14px;
  line-height:1.6;
  color:#cbd5e1;
  border-bottom:1px solid rgba(255,255,255,0.04)
}}
.detail-list li:last-child{{border-bottom:none}}
.detail-dot{{
  flex-shrink:0;
  width:8px;height:8px;
  border-radius:50%;
  background:{gradient};
  margin-top:7px
}}

/* --- Features List --- */
.feat-list{{list-style:none}}
.feat-list li{{
  display:flex;
  align-items:flex-start;
  gap:14px;
  padding:14px 16px;
  margin-bottom:8px;
  background:rgba(255,255,255,0.03);
  border:1px solid rgba(255,255,255,0.05);
  border-radius:14px;
  transition:background 0.2s
}}
.feat-icon{{
  flex-shrink:0;
  width:36px;height:36px;
  display:flex;align-items:center;justify-content:center;
  font-size:20px;
  background:rgba(42,171,238,0.1);
  border-radius:10px
}}
.feat-text{{
  font-size:14px;
  line-height:1.6;
  color:#cbd5e1;
  padding-top:6px
}}

/* --- Steps Timeline --- */
.steps-list{{list-style:none;padding:0;position:relative}}
.steps-list::before{{
  content:'';
  position:absolute;
  left:19px;top:24px;bottom:24px;
  width:2px;
  background:linear-gradient(to bottom,rgba(42,171,238,0.3),rgba(42,171,238,0.05));
  border-radius:1px
}}
.steps-list li{{
  display:flex;
  align-items:flex-start;
  gap:16px;
  padding:12px 0;
  position:relative
}}
.step-num{{
  flex-shrink:0;
  width:40px;height:40px;
  border-radius:12px;
  background:{gradient};
  color:#fff;
  display:flex;align-items:center;justify-content:center;
  font-weight:800;
  font-size:15px;
  box-shadow:0 4px 16px rgba(42,171,238,0.3);
  position:relative;
  z-index:1
}}
.step-text{{
  font-size:14px;
  line-height:1.6;
  color:#cbd5e1;
  padding-top:8px
}}

/* --- Bank Card --- */
.bank-card{{
  background:rgba(255,255,255,0.03);
  border:1px solid rgba(255,255,255,0.06);
  border-radius:16px;
  padding:4px 0;
  overflow:hidden
}}
.bank-row{{
  display:flex;
  justify-content:space-between;
  align-items:center;
  padding:14px 18px;
  border-bottom:1px solid rgba(255,255,255,0.04)
}}
.bank-row:last-child{{border-bottom:none}}
.bank-label{{
  font-size:12px;
  color:#64748b;
  text-transform:uppercase;
  letter-spacing:0.5px;
  font-weight:600;
  flex-shrink:0
}}
.bank-value{{
  font-size:13px;
  font-weight:600;
  color:#e2e8f0;
  text-align:right;
  display:flex;
  align-items:center;
  gap:8px;
  flex-wrap:wrap;
  justify-content:flex-end
}}
.mono{{font-family:'SF Mono',SFMono-Regular,'Courier New',monospace;letter-spacing:0.5px}}
.copy-btn{{
  display:inline-flex;
  align-items:center;
  gap:4px;
  background:rgba(42,171,238,0.12);
  border:1px solid rgba(42,171,238,0.2);
  color:#2AABEE;
  padding:6px 12px;
  border-radius:8px;
  font-size:11px;
  font-weight:600;
  cursor:pointer;
  transition:all 0.2s;
  white-space:nowrap
}}
.copy-btn:active{{background:rgba(42,171,238,0.25);transform:scale(0.95)}}
.copy-icon{{font-size:13px}}

/* --- Telegram Card --- */
.tg-card{{
  background:linear-gradient(145deg,rgba(42,171,238,0.08),rgba(42,171,238,0.02));
  border:1px solid rgba(42,171,238,0.15);
  border-radius:20px;
  padding:28px 20px;
  text-align:center;
  position:relative;
  overflow:hidden
}}
.tg-card::before{{
  content:'';
  position:absolute;
  top:-50%;left:-50%;
  width:200%;height:200%;
  background:radial-gradient(circle at 50% 50%,rgba(42,171,238,0.06),transparent 60%);
  pointer-events:none
}}
.tg-hero-icon{{
  position:relative;
  margin-bottom:16px
}}
.tg-subtitle{{
  font-size:14px;
  color:#94a3b8;
  margin-bottom:16px;
  line-height:1.5;
  position:relative
}}
.tg-warning{{
  display:flex;
  gap:10px;
  align-items:flex-start;
  background:rgba(250,204,21,0.08);
  border:1px solid rgba(250,204,21,0.2);
  border-radius:12px;
  padding:14px 16px;
  margin-bottom:20px;
  text-align:left;
  position:relative
}}
.tg-warning-icon{{
  font-size:18px;
  flex-shrink:0;
  margin-top:1px
}}
.tg-warning p{{
  font-size:13px;
  color:#fbbf24;
  line-height:1.5;
  margin:0
}}
.tg-warning strong{{color:#fde68a}}
.tg-hero-btn{{
  display:flex;
  align-items:center;
  justify-content:center;
  width:100%;
  background:linear-gradient(135deg,#2AABEE,#1a8fd1);
  color:#fff;
  text-align:center;
  padding:18px 24px;
  border-radius:14px;
  text-decoration:none;
  font-size:17px;
  font-weight:700;
  letter-spacing:0.3px;
  box-shadow:0 8px 32px rgba(42,171,238,0.35),0 0 0 1px rgba(42,171,238,0.2);
  transition:all 0.2s;
  position:relative;
  overflow:hidden
}}
.tg-hero-btn::after{{
  content:'';
  position:absolute;
  top:0;left:-100%;
  width:100%;height:100%;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,0.1),transparent);
  animation:tg-shimmer 3s ease-in-out infinite
}}
.tg-hero-btn:active{{transform:scale(0.97);box-shadow:0 4px 16px rgba(42,171,238,0.3)}}
.tg-hint{{
  font-size:12px;
  color:#475569;
  margin-top:14px;
  position:relative
}}
.tg-download{{
  margin-top:20px;
  padding-top:20px;
  border-top:1px solid rgba(255,255,255,0.06);
  position:relative
}}
.tg-dl-label{{
  font-size:12px;
  color:#64748b;
  margin-bottom:12px
}}
.tg-dl-btns{{
  display:flex;
  gap:10px;
  justify-content:center
}}
.tg-dl-btn{{
  display:inline-flex;
  align-items:center;
  gap:6px;
  color:#2AABEE;
  font-size:13px;
  font-weight:600;
  text-decoration:none;
  padding:10px 20px;
  border:1px solid rgba(42,171,238,0.25);
  border-radius:10px;
  background:rgba(42,171,238,0.06);
  transition:all 0.2s
}}
.tg-dl-btn:active{{background:rgba(42,171,238,0.15);transform:scale(0.97)}}
.tg-dl-hint{{
  font-size:11px;
  color:#475569;
  margin-top:10px
}}
.tg-username-box{{
  display:flex;
  align-items:center;
  justify-content:center;
  gap:10px;
  background:rgba(6,10,26,0.6);
  border:1px solid rgba(255,255,255,0.08);
  border-radius:12px;
  padding:14px 18px;
  margin:12px 0;
  position:relative
}}
.tg-username{{
  font-size:16px;
  font-weight:700;
  color:#fff;
  font-family:'SF Mono',SFMono-Regular,'Courier New',monospace;
  letter-spacing:0.3px
}}
.tg-alias{{
  font-size:12px;
  color:#475569;
  margin-bottom:16px;
  position:relative
}}
.tg-alias strong{{color:#94a3b8}}

/* --- Buttons --- */
.btn-group{{
  padding:8px 0 24px;
  position:relative
}}
.entendido-btn{{
  display:flex;
  align-items:center;
  justify-content:center;
  width:100%;
  background:linear-gradient(135deg,#22c55e,#16a34a);
  color:#fff;
  text-align:center;
  padding:18px;
  border-radius:14px;
  border:none;
  font-size:16px;
  font-weight:700;
  cursor:pointer;
  transition:all 0.2s;
  letter-spacing:0.3px;
  box-shadow:0 8px 32px rgba(34,197,94,0.3),0 0 0 1px rgba(34,197,94,0.2);
  position:relative;
  overflow:hidden
}}
.entendido-btn::after{{
  content:'';
  position:absolute;
  top:0;left:-100%;
  width:100%;height:100%;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,0.1),transparent);
  animation:tg-shimmer 3s ease-in-out infinite 1.5s
}}
.entendido-btn:active{{transform:scale(0.97)}}
.entendido-btn:disabled{{
  opacity:0.5;
  cursor:not-allowed;
  transform:none;
  box-shadow:none
}}
.later-btn{{
  display:block;
  width:100%;
  background:transparent;
  color:#64748b;
  text-align:center;
  padding:16px;
  border-radius:14px;
  border:1px solid rgba(255,255,255,0.06);
  font-size:14px;
  font-weight:500;
  cursor:pointer;
  margin-top:10px;
  transition:all 0.2s
}}
.later-btn:active{{color:#94a3b8;background:rgba(255,255,255,0.03)}}
.later-btn:disabled{{opacity:0.4;cursor:not-allowed}}
.btn-hint{{
  text-align:center;
  font-size:12px;
  color:#475569;
  margin-top:10px
}}
.error-msg{{
  display:none;
  background:rgba(239,68,68,0.08);
  border:1px solid rgba(239,68,68,0.2);
  border-radius:14px;
  padding:16px;
  margin-top:14px;
  text-align:center;
  font-size:14px;
  color:#fca5a5;
  line-height:1.6
}}

/* --- Result Screens --- */
.success-msg{{
  display:none;
  text-align:center;
  padding:60px 28px
}}
.success-msg .res-icon{{
  width:80px;height:80px;
  border-radius:50%;
  background:rgba(34,197,94,0.1);
  border:2px solid rgba(34,197,94,0.3);
  display:flex;align-items:center;justify-content:center;
  margin:0 auto 20px;
  font-size:36px;
  animation:res-pop 0.5s cubic-bezier(0.175,0.885,0.32,1.275)
}}
.success-msg h2{{
  font-size:22px;
  font-weight:800;
  color:#22c55e;
  margin-bottom:10px
}}
.success-msg p{{
  font-size:14px;
  color:#94a3b8;
  line-height:1.7
}}

.temp-msg{{
  display:none;
  text-align:center;
  padding:48px 28px
}}
.temp-msg .res-icon{{
  width:80px;height:80px;
  border-radius:50%;
  background:rgba(245,158,11,0.1);
  border:2px solid rgba(245,158,11,0.3);
  display:flex;align-items:center;justify-content:center;
  margin:0 auto 20px;
  font-size:36px;
  animation:res-pop 0.5s cubic-bezier(0.175,0.885,0.32,1.275)
}}
.temp-msg h2{{
  font-size:22px;
  font-weight:800;
  color:#f59e0b;
  margin-bottom:10px
}}
.temp-msg p{{
  font-size:14px;
  color:#94a3b8;
  line-height:1.7
}}
.temp-msg .tg-hero-btn{{
  margin-top:24px;
  display:inline-flex;
  width:auto;
  padding:16px 32px
}}

/* --- Footer --- */
.footer{{
  text-align:center;
  padding:20px 24px;
  font-size:11px;
  color:#334155;
  letter-spacing:0.5px;
  border-top:1px solid rgba(255,255,255,0.04)
}}

/* --- Animations --- */
@keyframes tg-shimmer{{
  0%{{left:-100%}}
  50%{{left:100%}}
  100%{{left:100%}}
}}
@keyframes res-pop{{
  0%{{transform:scale(0);opacity:0}}
  100%{{transform:scale(1);opacity:1}}
}}
@keyframes fadeUp{{
  from{{opacity:0;transform:translateY(16px)}}
  to{{opacity:1;transform:translateY(0)}}
}}
.anim-section{{
  animation:fadeUp 0.5s ease-out both
}}
.anim-section:nth-child(2){{animation-delay:0.08s}}
.anim-section:nth-child(3){{animation-delay:0.16s}}
.anim-section:nth-child(4){{animation-delay:0.24s}}
.anim-section:nth-child(5){{animation-delay:0.32s}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="header-content">
      <div class="brand"><span class="brand-dot"></span> AURALINK INTERNET <span class="brand-dot"></span></div>
      <div class="logo">{icon}</div>
      <h1>{title}</h1>
      <p class="header-sub">Servicio de Internet</p>
    </div>
  </div>

  <div id="content" class="body">
    <div class="announce">
      <p>{body}</p>
    </div>
{details_html}
{features_html}
{steps_html}
{bank_html}
{telegram_html}
{buttons_html}
  </div>

  <div id="success" class="success-msg">
    <div class="res-icon">&#9989;</div>
    <h2>Registro verificado</h2>
    <p>Tu cuenta de Telegram esta vinculada correctamente.<br>Este aviso no aparecera de nuevo.</p>
  </div>

  <div id="temp-dismiss" class="temp-msg">
    <div class="res-icon">&#9200;</div>
    <h2>Aviso pendiente</h2>
    <p>Recuerda registrarte en Telegram.<br>Este aviso aparecera de nuevo la proxima vez que navegues.</p>
    <a href="https://t.me/auralinkmonitor_bot" class="tg-hero-btn" style="margin-top:24px" target="_blank">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" style="margin-right:8px"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z" fill="white"/></svg>
      Registrarme en Telegram
    </a>
  </div>

  <div id="temp-5min" class="temp-msg">
    <div class="res-icon">&#9203;</div>
    <h2>5 minutos de navegacion</h2>
    <p>No encontramos tu registro en Telegram.<br>Tienes <strong style="color:#f59e0b">5 minutos</strong> para navegar. Despues, este aviso aparecera de nuevo.<br><br>Usa este tiempo para descargar Telegram y registrarte.</p>
    <a href="https://t.me/auralinkmonitor_bot" class="tg-hero-btn" style="margin-top:24px" target="_blank">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" style="margin-right:8px"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z" fill="white"/></svg>
      Registrarme ahora
    </a>
  </div>

  <div id="soft-dismiss" class="temp-msg">
    <div class="res-icon">&#128075;</div>
    <h2>Ya puedes navegar</h2>
    <p>No encontramos tu registro en Telegram.<br>Recuerda registrarte antes del 31 de marzo para acceder a todos los beneficios del sistema.</p>
    <a href="https://t.me/auralinkmonitor_bot" class="tg-hero-btn" style="margin-top:24px" target="_blank">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" style="margin-right:8px"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z" fill="white"/></svg>
      Registrarme ahora
    </a>
  </div>

  <div class="footer">
    AURALINK &copy; 2026 &mdash; Tomatlan, Jalisco
  </div>
</div>
<script>
function copy(t){{
  if(navigator.clipboard){{navigator.clipboard.writeText(t).then(()=>{{event.target.textContent='Copiado!';setTimeout(()=>{{event.target.innerHTML='<span class="copy-icon">&#128203;</span> Copiar'}},1500)}})}}
  else{{var a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();document.execCommand('copy');document.body.removeChild(a);event.target.textContent='Copiado!';setTimeout(()=>{{event.target.innerHTML='<span class="copy-icon">&#128203;</span> Copiar'}},1500)}}
}}
function verifyRegistro(){{
  var btn=document.getElementById('btn-verify');
  var btnL=document.getElementById('btn-later');
  var errDiv=document.getElementById('error-msg');
  btn.disabled=true;
  if(btnL)btnL.disabled=true;
  btn.textContent='Verificando...';
  errDiv.style.display='none';
  fetch('/api/verify-registro',{{method:'POST'}})
    .then(function(r){{return r.json()}})
    .then(function(d){{
      if(d.ok){{
        document.getElementById('content').style.display='none';
        document.getElementById('success').style.display='block';
      }}else if(d.temp_dismiss){{
        document.getElementById('content').style.display='none';
        document.getElementById('temp-5min').style.display='block';
        setTimeout(function(){{window.location.href='http://www.google.com'}},2000);
      }}else{{
        btn.disabled=false;
        if(btnL)btnL.disabled=false;
        btn.innerHTML='Ya me registr&eacute;';
        errDiv.innerHTML=d.message||'No encontramos tu registro. Sigue los pasos de arriba para registrarte en Telegram.';
        errDiv.style.display='block';
      }}
    }})
    .catch(function(){{
      btn.disabled=false;
      if(btnL)btnL.disabled=false;
      btn.innerHTML='Ya me registr&eacute;';
      errDiv.textContent='Error de conexion. Intenta de nuevo.';
      errDiv.style.display='block';
    }});
}}
function softVerify(){{
  var btn=document.getElementById('btn-verify');
  var btnL=document.getElementById('btn-later');
  btn.disabled=true;
  if(btnL)btnL.disabled=true;
  btn.textContent='Verificando...';
  fetch('/api/verify-registro',{{method:'POST'}})
    .then(function(r){{return r.json()}})
    .then(function(d){{
      if(d.registered){{
        document.getElementById('content').style.display='none';
        document.getElementById('success').style.display='block';
      }}else{{
        document.getElementById('content').style.display='none';
        document.getElementById('soft-dismiss').style.display='block';
      }}
    }})
    .catch(function(){{
      document.getElementById('content').style.display='none';
      document.getElementById('soft-dismiss').style.display='block';
    }});
}}
function dismissTemp(){{
  var btn=document.getElementById('btn-later');
  var btnV=document.getElementById('btn-verify');
  btn.disabled=true;
  if(btnV)btnV.disabled=true;
  btn.textContent='Procesando...';
  fetch('/api/dismiss-temp',{{method:'POST'}})
    .then(function(r){{return r.json()}})
    .then(function(){{
      setTimeout(function(){{window.location.href='http://www.google.com'}},500);
    }})
    .catch(function(){{
      setTimeout(function(){{window.location.href='http://www.google.com'}},500);
    }});
}}
function dismiss(){{
  var btn=document.querySelector('.entendido-btn');
  btn.disabled=true;
  btn.textContent='Procesando...';
  fetch('/api/entendido',{{method:'POST'}})
    .then(function(r){{return r.json()}})
    .then(function(d){{
      if(d.ok){{
        document.getElementById('content').style.display='none';
        document.getElementById('success').style.display='block';
      }}else{{
        btn.disabled=false;
        btn.textContent='{dismiss_text}';
      }}
    }})
    .catch(function(){{
      btn.disabled=false;
      btn.textContent='{dismiss_text}';
    }});
}}
</script>
</body>
</html>"""


async def index(request):
    """Serve dynamic announcement page or 204 if no active announcement."""
    # Smart TVs (Samsung, LG, etc.) can't display captive portals — let them through.
    # They send User-Agent with keywords like "SmartTV", "Tizen", "WebOS", "SMART-TV", etc.
    ua = (request.headers.get("User-Agent") or "").lower()
    tv_keywords = ("smarttv", "tizen", "webos", "smart-tv", "lgwebos",
                   "netcast", "viera", "hbbtv", "roku", "firetv", "crkey",
                   "chromecast", "appletv", "apple tv", "androidtv", "android tv")
    if any(kw in ua for kw in tv_keywords):
        return web.Response(status=204)

    # Non-browser requests (no Accept: text/html) are likely APIs/services, not humans.
    # Only show portal to actual browsers that can render and interact with it.
    accept = request.headers.get("Accept") or ""
    if "text/html" not in accept and accept != "*/*" and accept:
        return web.Response(status=204)

    state = _load_state()
    if not state:
        # No active announcement — return 204 (captive portal interprets as "internet OK")
        return web.Response(status=204)

    # Auto-dismiss: if client is registered, dismiss and return 204 (internet OK)
    client_ip = request.remote
    ppp_name = ""
    if client_ip and client_ip.startswith(ALLOWED_PREFIXES):
        try:
            ppp_name = await _get_ppp_name(client_ip) or ""
            if ppp_name and _check_registered(ppp_name):
                await _permanent_dismiss(client_ip, ppp_name)
                log.info("Auto-dismiss on load: %s (%s) is registered", ppp_name, client_ip)
                return web.Response(status=204)
        except Exception as e:
            log.warning("Auto-dismiss check failed for %s: %s", client_ip, e)

    html = _render_html(state, ppp_name=ppp_name)
    return web.Response(text=html, content_type="text/html")


def _captive_ok_response(path: str) -> web.Response:
    """Return the correct 'internet OK' response for each captive portal detection endpoint."""
    if path in ("/generate_204", "/gen_204"):
        return web.Response(status=204)
    if path == "/success.txt":
        return web.Response(text="success\n")
    if path == "/connecttest.txt":
        return web.Response(text="Microsoft Connect Test")
    if path in ("/hotspot-detect.html", "/library/test/success.html"):
        return web.Response(text="<HTML><HEAD><TITLE>Success</TITLE></HEAD><BODY>Success</BODY></HTML>",
                            content_type="text/html")
    return web.Response(status=204)


async def captive_redirect(request):
    """Always return 'internet OK' for captive portal detection endpoints.

    This prevents phones from reporting 'no internet'. The aviso is only
    shown when a client visits an actual HTTP page (handled by index()).
    Registered clients are auto-dismissed here to avoid even the page redirect.
    """
    # Auto-dismiss registered clients (removes from avisos, adds to avisos-visto)
    state = _load_state()
    if state:
        client_ip = request.remote
        if client_ip and client_ip.startswith(ALLOWED_PREFIXES):
            try:
                ppp_name = await _get_ppp_name(client_ip)
                if ppp_name and _check_registered(ppp_name):
                    await _permanent_dismiss(client_ip, ppp_name)
                    log.info("Auto-dismiss captive check: %s (%s) is registered", ppp_name, client_ip)
            except Exception as e:
                log.warning("Auto-dismiss captive check failed for %s: %s", client_ip, e)

    # Always return "internet OK" — never trigger captive portal popup
    return _captive_ok_response(request.path)


async def verify_registro(request):
    """Verify if client is registered in Telegram. Behavior depends on mode."""
    state = _load_state()
    mode = _effective_mode(state)

    client_ip = request.remote
    log.info("Verify registro from %s (mode=%s)", client_ip, mode)

    if not client_ip or not client_ip.startswith(ALLOWED_PREFIXES):
        return web.json_response({"ok": False, "message": "IP no valida"}, status=403)

    try:
        ppp_name = await _get_ppp_name(client_ip)
        if not ppp_name:
            log.warning("No PPPoE session found for %s", client_ip)
            if mode == "soft":
                return web.json_response({"ok": True, "registered": False})
            return web.json_response({
                "ok": False,
                "message": "No se pudo identificar tu cuenta. Intenta de nuevo."
            })

        registered = _check_registered(ppp_name)

        if mode == "soft":
            if registered:
                await _permanent_dismiss(client_ip, ppp_name)
                log.info("Soft verify: %s (%s) registered=True — permanent dismiss", ppp_name, client_ip)
            else:
                await _temp_dismiss_24h(client_ip, ppp_name)
                log.info("Soft verify: %s (%s) registered=False — 24h temp dismiss", ppp_name, client_ip)
            return web.json_response({"ok": True, "registered": registered})
        elif mode == "medium":
            if registered:
                await _permanent_dismiss(client_ip, ppp_name)
                log.info("Verified registered: %s (%s) — permanent dismiss", ppp_name, client_ip)
                return web.json_response({"ok": True, "registered": True})
            else:
                log.info("Not registered (medium): %s (%s)", ppp_name, client_ip)
                return web.json_response({
                    "ok": False,
                    "registered": False,
                    "message": "No encontramos tu registro en Telegram.<br><br>"
                               "Abre Telegram, busca <b>@auralinkmonitor_bot</b>, "
                               "presiona <b>Iniciar</b> y vincula tu cuenta con tu nombre."
                })
        else:
            # Strict/Persistent: 5-min temp dismiss for unregistered
            if registered:
                await _permanent_dismiss(client_ip, ppp_name)
                log.info("Verified registered: %s (%s) — permanent dismiss", ppp_name, client_ip)
                return web.json_response({"ok": True, "registered": True})
            else:
                await _temp_dismiss_5min(client_ip, ppp_name)
                log.info("Not registered (strict/persistent): %s (%s) — 5min temp dismiss", ppp_name, client_ip)
                return web.json_response({
                    "ok": False,
                    "temp_dismiss": True,
                    "message": "No encontramos tu registro. Tienes 5 minutos para navegar."
                })

    except Exception as e:
        log.error("Verify error for %s: %s", client_ip, e)
        if mode == "soft":
            return web.json_response({"ok": True, "registered": False})
        return web.json_response({"ok": False, "message": "Error de verificacion. Intenta de nuevo."})


async def dismiss_temp(request):
    """Temporary dismiss: remove from avisos and add to avisos-visto with 24h timeout.
    Client won't see the portal again for 24 hours."""
    client_ip = request.remote
    log.info("Temp dismiss from %s", client_ip)

    if not client_ip or not client_ip.startswith(ALLOWED_PREFIXES):
        return web.json_response({"ok": False, "error": "IP no valida"}, status=403)

    try:
        ppp_name = await _get_ppp_name(client_ip)
        comment = ppp_name or ""
        # Remove from avisos + add to avisos-visto permanently (survives reboot)
        safe_comment = re.sub(r'[^a-zA-Z0-9_. -]', '', comment)
        mk_script = (
            f'/ip firewall address-list remove [find where list=avisos address={client_ip}]; '
            f'/ip firewall address-list remove [find where list=avisos-visto address={client_ip}]; '
            f'/ip firewall address-list add list=avisos-visto address={client_ip} comment="{safe_comment}"'
        )
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
            f"{MIKROTIK_USER}@{MIKROTIK_IP}", mk_script,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=15)
        log.info("Temp dismissed %s (%s) for 24h", ppp_name or "unknown", client_ip)
        return web.json_response({"ok": True})
    except Exception as e:
        log.error("Temp dismiss error for %s: %s", client_ip, e)
        return web.json_response({"ok": True})  # still show temp-dismiss screen


async def dismiss(request):
    """Permanent dismiss (for non-verify announcements)."""
    client_ip = request.remote
    log.info("Dismiss request from %s", client_ip)

    if not client_ip or not client_ip.startswith(ALLOWED_PREFIXES):
        log.warning("Rejected dismiss from non-client IP: %s", client_ip)
        return web.json_response({"ok": False, "error": "IP no valida"}, status=403)

    try:
        ppp_name = await _get_ppp_name(client_ip)
        ok = await _permanent_dismiss(client_ip, ppp_name)

        if ok:
            log.info("Dismissed %s from avisos list", client_ip)
            return web.json_response({"ok": True})

        # Fallback: try simple remove + add
        fallback_mk = (
            f'/ip firewall address-list remove [find where list=avisos address={client_ip}]; '
            f'/ip firewall address-list add list=avisos-visto address={client_ip}'
        )
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
            f"{MIKROTIK_USER}@{MIKROTIK_IP}", fallback_mk,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=10)
        if proc.returncode == 0:
            return web.json_response({"ok": True})
        return web.json_response({"ok": False, "error": "Error interno"}, status=500)

    except asyncio.TimeoutError:
        log.error("SSH timeout for %s", client_ip)
        return web.json_response({"ok": False, "error": "Timeout"}, status=504)
    except Exception as e:
        log.error("Exception dismissing %s: %s", client_ip, e)
        return web.json_response({"ok": False, "error": "Error interno"}, status=500)


# --- Admin API ---

async def admin_update(request):
    """Update the current announcement."""
    if not _check_admin_token(request):
        return web.json_response({"ok": False, "error": "Unauthorized"}, status=401)
    try:
        data = await request.json()
    except (json.JSONDecodeError, Exception):
        return web.json_response({"ok": False, "error": "Invalid JSON"}, status=400)

    # Validate required fields
    required = ["title", "body"]
    for field in required:
        if field not in data:
            return web.json_response({"ok": False, "error": f"Missing field: {field}"}, status=400)

    # Set defaults
    data.setdefault("active", True)
    data.setdefault("icon", "&#128225;")
    data.setdefault("color_theme", "blue")
    data.setdefault("details", [])
    data.setdefault("show_bank_info", False)
    data.setdefault("show_telegram_bot", True)
    data.setdefault("dismiss_text", "Entendido")

    _save_state(data)
    log.info("Announcement updated: %s", data.get("title"))
    return web.json_response({"ok": True})


async def admin_deactivate(request):
    """Deactivate the current announcement."""
    if not _check_admin_token(request):
        return web.json_response({"ok": False, "error": "Unauthorized"}, status=401)
    state = _load_state()
    if state:
        state["active"] = False
        _save_state(state)
        log.info("Announcement deactivated")
    return web.json_response({"ok": True})


async def admin_status(request):
    """Return current announcement status."""
    if not _check_admin_token(request):
        return web.json_response({"ok": False, "error": "Unauthorized"}, status=401)
    state = _load_state()
    if state:
        return web.json_response({
            "ok": True,
            "active": True,
            "title": state.get("title", ""),
            "color_theme": state.get("color_theme", "blue"),
        })
    return web.json_response({"ok": True, "active": False})


# ---------------------------------------------------------------------------
# Background sync: auto-exclude registered + excluded accounts from avisos
# ---------------------------------------------------------------------------
async def _get_active_ppp_sessions() -> dict[str, str]:
    """Get all active PPPoE sessions as {username: ip} using terse output."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
            f"{MIKROTIK_USER}@{MIKROTIK_IP}", "/ppp/active/print terse",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=20)
        if proc.returncode == 0:
            result = {}
            for line in stdout.decode().strip().split("\n"):
                name = addr = ""
                for part in line.strip().split():
                    if part.startswith("name="):
                        name = part[5:]
                    elif part.startswith("address="):
                        addr = part[8:]
                if name and addr:
                    result[name] = addr
            return result
    except Exception as e:
        log.error("Error getting PPP sessions: %s", e)
    return {}


async def _get_avisos_visto_ips() -> set[str]:
    """Get all IPs currently in avisos-visto using terse output."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
            f"{MIKROTIK_USER}@{MIKROTIK_IP}", "/ip firewall address-list print terse where list=avisos-visto",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        if proc.returncode == 0:
            ips = set()
            for line in stdout.decode().strip().split("\n"):
                for part in line.strip().split():
                    if part.startswith("address="):
                        ips.add(part[8:])
            return ips
    except Exception as e:
        log.error("Error getting avisos-visto: %s", e)
    return set()


def _get_registered_names() -> set[str]:
    """Get all CRM client names from bot DB that are registered (linked)."""
    if not Path(BOT_DB_PATH).exists():
        return set()
    try:
        conn = sqlite3.connect(f"file:{BOT_DB_PATH}?mode=ro", uri=True)
        cursor = conn.execute("SELECT crm_client_name FROM customer_links")
        names = {(row[0] or "").lower().replace(" ", "") for row in cursor if row[0]}
        conn.close()
        return names
    except Exception as e:
        log.error("Error reading registered names: %s", e)
        return set()


def _ppp_matches_registered(ppp_name: str, registered_names: set[str]) -> bool:
    """Check if a PPPoE username matches any registered CRM name."""
    ppp_lower = ppp_name.lower().replace(" ", "")
    for crm_name in registered_names:
        if _names_match(ppp_lower, crm_name):
            return True
    return False


async def _add_to_avisos_visto(ip: str, comment: str) -> bool:
    """Add IP to avisos-visto permanently and remove from avisos."""
    if not _valid_ip(ip):
        return False
    safe_comment = re.sub(r'[^a-zA-Z0-9_. -]', '', comment)
    mk_script = (
        f'/ip firewall address-list remove [find where list=avisos address={ip}]; '
        f'/ip firewall address-list add list=avisos-visto address={ip} comment="{safe_comment}"'
    )
    try:
        proc = await asyncio.create_subprocess_exec(
            "ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
            f"{MIKROTIK_USER}@{MIKROTIK_IP}", mk_script,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=10)
        return proc.returncode == 0
    except Exception:
        return False


async def sync_avisos_exclusions():
    """Background task: auto-add registered + excluded accounts to avisos-visto."""
    await asyncio.sleep(10)  # wait for startup
    while True:
        try:
            log.info("Sync: starting cycle...")
            sessions = await _get_active_ppp_sessions()
            log.info("Sync: found %d PPP sessions", len(sessions))
            if not sessions:
                log.warning("Sync: no PPP sessions found, skipping")
                await asyncio.sleep(SYNC_INTERVAL)
                continue

            visto_ips = await _get_avisos_visto_ips()
            registered_names = _get_registered_names()
            log.info("Sync: %d in avisos-visto, %d registered names", len(visto_ips), len(registered_names))
            added = 0

            for username, ip in sessions.items():
                if ip in visto_ips:
                    continue
                # Check if excluded account
                if username.lower() in EXCLUDED_PPP_NAMES:
                    await _add_to_avisos_visto(ip, username)
                    added += 1
                    log.info("Sync: excluded %s (%s)", username, ip)
                    continue
                # Check if registered in Telegram
                if _ppp_matches_registered(username, registered_names):
                    await _add_to_avisos_visto(ip, username)
                    added += 1
                    log.info("Sync: registered %s (%s)", username, ip)

            log.info("Sync: cycle complete, added %d to avisos-visto", added)
        except Exception as e:
            log.error("Sync error: %s", e)
        await asyncio.sleep(SYNC_INTERVAL)


async def on_startup(app_instance):
    app_instance["sync_task"] = asyncio.create_task(sync_avisos_exclusions())


async def on_cleanup(app_instance):
    task = app_instance.get("sync_task")
    if task:
        task.cancel()


app = web.Application()
app.on_startup.append(on_startup)
app.on_cleanup.append(on_cleanup)
app.router.add_get("/", index)
app.router.add_post("/api/entendido", dismiss)
app.router.add_post("/api/verify-registro", verify_registro)
app.router.add_post("/api/dismiss-temp", dismiss_temp)
app.router.add_post("/api/admin/update", admin_update)
app.router.add_post("/api/admin/deactivate", admin_deactivate)
app.router.add_get("/api/admin/status", admin_status)

# Captive portal detection endpoints (Android, iOS, Windows, Firefox)
for path in [
    "/generate_204", "/gen_204",          # Android
    "/hotspot-detect.html",               # Apple
    "/connecttest.txt", "/ncsi.txt",      # Windows
    "/success.txt",                       # Firefox
    "/library/test/success.html",         # Apple alt
    "/kindle-wifi/wifistub.html",         # Kindle
]:
    app.router.add_get(path, captive_redirect)

# Serve static files (CSS, images if any)
app.router.add_static("/static/", STATIC_DIR)


async def catch_all(request):
    """Any unmatched route returns 204. Smart TVs and IoT devices hit random
    URLs (/fts/gftsDownload.lge, /v1/stargazer, /check.xml, etc) and interpret
    non-200 responses as 'no internet'. Returning 204 tells them internet is OK."""
    return web.Response(status=204)

# Catch-all must be last — matches any GET/POST/etc not handled above
app.router.add_route("*", "/{path_info:.*}", catch_all)


if __name__ == "__main__":
    log.info("Starting avisos portal on port 8090")
    web.run_app(app, host="0.0.0.0", port=8090, print=None)
