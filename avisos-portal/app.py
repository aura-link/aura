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

from aiohttp import web

MIKROTIK_IP = "10.147.17.11"
MIKROTIK_USER = "admin"
ALLOWED_PREFIXES = ("10.10.0.", "10.10.1.", "10.10.2.")
STATIC_DIR = Path(__file__).parent / "static"
DATA_DIR = Path(__file__).parent / "data"
CURRENT_FILE = DATA_DIR / "current.json"
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "auralink-avisos-2026")
BOT_DB_PATH = os.getenv("BOT_DB_PATH", "/app/botdata/aura.db")
SYNC_INTERVAL = 300  # 5 minutes

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
    cmd = (
        f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes "
        f"{MIKROTIK_USER}@{MIKROTIK_IP} /ppp/active/print\\ terse\\ where\\ address={client_ip}"
    )
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
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
    cmd = (
        f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes "
        f"{MIKROTIK_USER}@{MIKROTIK_IP} "
        f'"/ip firewall address-list remove [find where list=avisos address={client_ip}]"'
    )
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=10)
        return proc.returncode == 0
    except Exception:
        return False


async def _temp_dismiss_24h(client_ip: str, ppp_name: str | None) -> bool:
    """Remove from avisos and add to avisos-visto permanently.
    The bot's aviso scheduler clears avisos-visto every 3 days when re-publishing,
    so clients will see the aviso again on the next cycle. Permanent entries survive reboots."""
    comment = ppp_name or ""
    mk_script = (
        f'/ip firewall address-list remove [find where list=avisos address={client_ip}]; '
        f'/ip firewall address-list remove [find where list=avisos-visto address={client_ip}]; '
        f'/ip firewall address-list add list=avisos-visto address={client_ip} comment="{comment}"'
    )
    cmd = (
        f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes "
        f'{MIKROTIK_USER}@{MIKROTIK_IP} "{mk_script}"'
    )
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=15)
        return proc.returncode == 0
    except Exception:
        return False


async def _temp_dismiss_5min(client_ip: str, ppp_name: str | None) -> bool:
    """Remove from avisos and add to avisos-visto with 5-minute timeout.
    Dynamic entry (flag D) that auto-expires after 5 min.
    When it expires, populate-avisos re-adds the client on its next cycle."""
    comment = ppp_name or ""
    mk_script = (
        f'/ip firewall address-list remove [find where list=avisos address={client_ip}]; '
        f'/ip firewall address-list remove [find where list=avisos-visto address={client_ip}]; '
        f'/ip firewall address-list add list=avisos-visto address={client_ip} timeout=00:05:00 comment="{comment}"'
    )
    cmd = (
        f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes "
        f'{MIKROTIK_USER}@{MIKROTIK_IP} "{mk_script}"'
    )
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=15)
        return proc.returncode == 0
    except Exception:
        return False


async def _permanent_dismiss(client_ip: str, ppp_name: str | None) -> bool:
    """Remove from avisos and add to avisos-visto (permanent dismiss)."""
    comment = ppp_name if ppp_name else ""
    mk_script = (
        f'/ip firewall address-list remove [find where list=avisos address={client_ip}]; '
        f'/ip firewall address-list add list=avisos-visto address={client_ip} comment="{comment}"'
    )
    cmd = (
        f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes "
        f'{MIKROTIK_USER}@{MIKROTIK_IP} "{mk_script}"'
    )
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=15)
        return proc.returncode == 0
    except Exception:
        return False


def _render_html(state: dict) -> str:
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
            f'        <li data-icon="&#9679;">{escape(d)}</li>' for d in details
        )
        details_html = f"""
    <div class="section">
      <h2>Detalles</h2>
      <ul class="features">
{items}
      </ul>
    </div>"""

    # Build features HTML (list with custom icons)
    features = state.get("features", [])
    features_html = ""
    if features:
        items = "\n".join(
            f'        <li data-icon="{f.get("icon", "✓")}">{escape(f.get("text", ""))}</li>'
            for f in features
        )
        features_html = f"""
    <div class="section">
      <h2>Beneficios</h2>
      <ul class="features">
{items}
      </ul>
    </div>"""

    # Build steps HTML (numbered list)
    steps = state.get("steps", [])
    steps_html = ""
    if steps:
        items = "\n".join(
            f'        <li><span class="step-num">{i+1}</span>{escape(s)}</li>'
            for i, s in enumerate(steps)
        )
        steps_html = f"""
    <div class="section">
      <h2>Como registrarte</h2>
      <ol class="steps-list">
{items}
      </ol>
    </div>"""

    # Bank info section
    bank_html = ""
    if show_bank:
        bank_html = """
    <div class="section">
      <h2>Datos para pago</h2>
      <div class="bank-info">
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
          <span class="bank-value">285 958 9260 <button class="copy-btn" onclick="copy('2859589260')">Copiar</button></span>
        </div>
        <div class="bank-row">
          <span class="bank-label">Tarjeta</span>
          <span class="bank-value">4152 3144 8622 9639 <button class="copy-btn" onclick="copy('4152314486229639')">Copiar</button></span>
        </div>
        <div class="bank-row">
          <span class="bank-label">CLABE</span>
          <span class="bank-value">012400028595892607 <button class="copy-btn" onclick="copy('012400028595892607')">Copiar</button></span>
        </div>
      </div>
    </div>"""

    # Telegram section
    telegram_html = ""
    if show_telegram:
        telegram_html = """
    <div class="section">
      <h2>Bot de Telegram</h2>
      <div class="telegram-box">
        <div style="font-size:28px;margin-bottom:8px">&#129302;</div>
        <p style="font-size:14px;color:#aaa;margin-bottom:4px">Busca en Telegram:</p>
        <div style="background:#0a0e27;border-radius:8px;padding:12px;margin:8px 0;display:flex;align-items:center;justify-content:center;gap:8px">
          <span style="font-size:17px;font-weight:700;color:#fff;font-family:'Courier New',monospace">@auralinkmonitor_bot</span>
          <button class="copy-btn" onclick="copy('auralinkmonitor_bot')" style="padding:6px 14px;font-size:13px">Copiar</button>
        </div>
        <p style="font-size:12px;color:#666;margin-bottom:10px">Puede aparecer como <strong style="color:#aaa">AURA</strong></p>
        <a href="https://t.me/auralinkmonitor_bot" class="telegram-link" target="_blank">Abrir en Telegram</a>
      </div>
    </div>"""

    # Mode: soft (always internet), medium (verify strict + temp dismiss), strict/persistent (verify only, 5min temp)
    mode = state.get("mode", "normal")
    if verify_registro and mode == "normal":
        mode = "strict"  # backward compatibility

    if mode == "soft":
        buttons_html = """
    <button class="entendido-btn" onclick="softVerify()" id="btn-verify">Ya me registr&eacute;</button>
    <button class="later-btn" onclick="dismissTemp()" id="btn-later">Lo har&eacute; despu&eacute;s</button>"""
    elif mode == "medium":
        buttons_html = """
    <button class="entendido-btn" onclick="verifyRegistro()" id="btn-verify">Ya me registr&eacute;</button>
    <button class="later-btn" onclick="dismissTemp()" id="btn-later">Lo har&eacute; despu&eacute;s</button>
    <div id="error-msg" class="error-msg"></div>"""
    elif mode in ("strict", "persistent"):
        buttons_html = """
    <button class="entendido-btn" onclick="verifyRegistro()" id="btn-verify">Ya me registr&eacute;</button>
    <div id="error-msg" class="error-msg"></div>"""
    else:
        buttons_html = f"""
    <button class="entendido-btn" onclick="dismiss()">{dismiss_text}</button>
    <p style="text-align:center;font-size:12px;color:#555;margin-top:8px">Al presionar, este aviso no aparecera de nuevo</p>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AURALINK - {title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0e27;color:#e0e0e0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}
.container{{max-width:480px;width:100%;background:#141833;border-radius:16px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,0.5)}}
.header{{background:{gradient};padding:30px 24px;text-align:center}}
.header h1{{font-size:22px;font-weight:700;color:#fff;margin-bottom:6px}}
.header p{{font-size:14px;color:rgba(255,255,255,0.85)}}
.logo{{font-size:36px;margin-bottom:10px}}
.body{{padding:24px}}
.announce{{background:{bg_light};border:1px solid {border_light};border-radius:10px;padding:16px;margin-bottom:20px;text-align:center}}
.announce p{{font-size:15px;line-height:1.6}}
.section{{margin-bottom:20px}}
.section h2{{font-size:14px;text-transform:uppercase;letter-spacing:1px;color:#7b8cde;margin-bottom:12px;padding-bottom:6px;border-bottom:1px solid rgba(123,140,222,0.2)}}
.features{{list-style:none}}
.features li{{padding:10px 0 10px 36px;position:relative;font-size:14px;line-height:1.5;border-bottom:1px solid rgba(255,255,255,0.04)}}
.features li:last-child{{border-bottom:none}}
.features li::before{{content:attr(data-icon);position:absolute;left:0;top:10px;font-size:18px}}
.steps-list{{list-style:none;padding:0}}
.steps-list li{{padding:12px 0 12px 48px;position:relative;font-size:14px;line-height:1.5;border-bottom:1px solid rgba(255,255,255,0.04)}}
.steps-list li:last-child{{border-bottom:none}}
.step-num{{position:absolute;left:0;top:10px;width:32px;height:32px;border-radius:50%;background:{gradient};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px}}
.bank-info{{background:#1a1f3d;border-radius:10px;padding:16px}}
.bank-row{{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.06)}}
.bank-row:last-child{{border-bottom:none}}
.bank-label{{font-size:13px;color:#888}}
.bank-value{{font-size:14px;font-weight:600;color:#fff;font-family:'Courier New',monospace;letter-spacing:0.5px}}
.copy-btn{{background:rgba(123,140,222,0.2);border:none;color:#7b8cde;padding:4px 10px;border-radius:6px;font-size:12px;cursor:pointer;margin-left:8px}}
.copy-btn:active{{background:rgba(123,140,222,0.4)}}
.telegram-box{{background:#1a1f3d;border-radius:10px;padding:16px;text-align:center}}
.telegram-link{{display:block;background:linear-gradient(135deg,#2AABEE,#229ED9);color:#fff;text-align:center;padding:14px;border-radius:10px;text-decoration:none;font-size:15px;font-weight:600;margin-top:12px;transition:opacity 0.2s}}
.telegram-link:hover{{opacity:0.9}}
.entendido-btn{{display:block;width:100%;background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff;text-align:center;padding:16px;border-radius:12px;border:none;font-size:16px;font-weight:700;cursor:pointer;margin-top:8px;transition:all 0.2s;letter-spacing:0.5px}}
.entendido-btn:hover{{opacity:0.9;transform:scale(1.01)}}
.entendido-btn:active{{transform:scale(0.98)}}
.entendido-btn:disabled{{opacity:0.6;cursor:not-allowed;transform:none}}
.later-btn{{display:block;width:100%;background:transparent;color:#888;text-align:center;padding:14px;border-radius:12px;border:1px solid rgba(255,255,255,0.1);font-size:14px;cursor:pointer;margin-top:8px;transition:all 0.2s}}
.later-btn:hover{{color:#aaa;border-color:rgba(255,255,255,0.2)}}
.later-btn:disabled{{opacity:0.5;cursor:not-allowed}}
.error-msg{{display:none;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:10px;padding:14px;margin-top:12px;text-align:center;font-size:14px;color:#f87171;line-height:1.5}}
.success-msg{{display:none;text-align:center;padding:40px 24px}}
.success-msg .icon{{font-size:48px;margin-bottom:16px}}
.success-msg h2{{font-size:20px;color:#22c55e;margin-bottom:8px}}
.success-msg p{{font-size:14px;color:#aaa;line-height:1.5}}
.temp-msg{{display:none;text-align:center;padding:40px 24px}}
.temp-msg .icon{{font-size:48px;margin-bottom:16px}}
.temp-msg h2{{font-size:20px;color:#f59e0b;margin-bottom:8px}}
.temp-msg p{{font-size:14px;color:#aaa;line-height:1.5}}
.footer{{text-align:center;padding:16px 24px;font-size:12px;color:#555;border-top:1px solid rgba(255,255,255,0.06)}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="logo">{icon}</div>
    <h1>{title}</h1>
    <p>AURALINK Internet</p>
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
    <div class="icon">&#9989;</div>
    <h2>Registro verificado</h2>
    <p>Tu cuenta de Telegram esta vinculada correctamente.<br>Este aviso no aparecera de nuevo.</p>
  </div>

  <div id="temp-dismiss" class="temp-msg">
    <div class="icon">&#9200;</div>
    <h2>Aviso pendiente</h2>
    <p>Recuerda registrarte en Telegram.<br>Este aviso aparecera de nuevo la proxima vez que navegues.</p>
    <a href="https://t.me/auralinkmonitor_bot" class="telegram-link" style="margin-top:20px" target="_blank">Abrir Telegram para registrarme</a>
  </div>

  <div id="temp-5min" class="temp-msg">
    <div class="icon">&#9203;</div>
    <h2>5 minutos de navegacion</h2>
    <p>No encontramos tu registro en Telegram.<br>Tienes <strong style="color:#f59e0b">5 minutos</strong> para navegar. Despues, este aviso aparecera de nuevo.<br><br>Usa este tiempo para descargar Telegram y registrarte.</p>
    <a href="https://t.me/auralinkmonitor_bot" class="telegram-link" style="margin-top:20px" target="_blank">Registrarme ahora en Telegram</a>
  </div>

  <div id="soft-dismiss" class="temp-msg">
    <div class="icon">&#128075;</div>
    <h2>Ya puedes navegar</h2>
    <p>No encontramos tu registro en Telegram.<br>Recuerda registrarte antes del 31 de marzo para acceder a todos los beneficios del sistema.</p>
    <a href="https://t.me/auralinkmonitor_bot" class="telegram-link" style="margin-top:20px" target="_blank">Registrarme ahora en Telegram</a>
  </div>

  <div class="footer">
    AURALINK &copy; 2026 &mdash; Tomatlan, Jalisco
  </div>
</div>
<script>
function copy(t){{
  if(navigator.clipboard){{navigator.clipboard.writeText(t).then(()=>{{event.target.textContent='OK!';setTimeout(()=>{{event.target.textContent='Copiar'}},1500)}})}}
  else{{var a=document.createElement('textarea');a.value=t;document.body.appendChild(a);a.select();document.execCommand('copy');document.body.removeChild(a);event.target.textContent='OK!';setTimeout(()=>{{event.target.textContent='Copiar'}},1500)}}
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
    state = _load_state()
    if not state:
        # No active announcement — return 204 (captive portal interprets as "internet OK")
        return web.Response(status=204)

    # Auto-dismiss: if client is registered, dismiss and return 204 (internet OK)
    client_ip = request.remote
    if client_ip and client_ip.startswith(ALLOWED_PREFIXES):
        try:
            ppp_name = await _get_ppp_name(client_ip)
            if ppp_name and _check_registered(ppp_name):
                await _permanent_dismiss(client_ip, ppp_name)
                log.info("Auto-dismiss on load: %s (%s) is registered", ppp_name, client_ip)
                return web.Response(status=204)
        except Exception as e:
            log.warning("Auto-dismiss check failed for %s: %s", client_ip, e)

    html = _render_html(state)
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
    """Redirect to portal only if there's an active announcement and client is not registered."""
    state = _load_state()
    if not state:
        return _captive_ok_response(request.path)

    # Auto-dismiss: if client is registered, return "internet OK" (no captive portal popup)
    client_ip = request.remote
    if client_ip and client_ip.startswith(ALLOWED_PREFIXES):
        try:
            ppp_name = await _get_ppp_name(client_ip)
            if ppp_name and _check_registered(ppp_name):
                await _permanent_dismiss(client_ip, ppp_name)
                log.info("Auto-dismiss captive check: %s (%s) is registered", ppp_name, client_ip)
                return _captive_ok_response(request.path)
        except Exception as e:
            log.warning("Auto-dismiss captive check failed for %s: %s", client_ip, e)

    raise web.HTTPFound("/")


async def verify_registro(request):
    """Verify if client is registered in Telegram. Behavior depends on mode."""
    state = _load_state()
    mode = "strict"
    if state:
        mode = state.get("mode", "normal")
        if state.get("verify_registro") and mode == "normal":
            mode = "strict"

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
        mk_script = (
            f'/ip firewall address-list remove [find where list=avisos address={client_ip}]; '
            f'/ip firewall address-list remove [find where list=avisos-visto address={client_ip}]; '
            f'/ip firewall address-list add list=avisos-visto address={client_ip} comment="{comment}"'
        )
        cmd = (
            f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes "
            f'{MIKROTIK_USER}@{MIKROTIK_IP} "{mk_script}"'
        )
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
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
        fallback_cmd = (
            f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes "
            f"{MIKROTIK_USER}@{MIKROTIK_IP} "
            f'"/ip firewall address-list remove [find where list=avisos address={client_ip}]; '
            f'/ip firewall address-list add list=avisos-visto address={client_ip}"'
        )
        proc = await asyncio.create_subprocess_shell(
            fallback_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
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
    cmd = (
        f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes "
        f"{MIKROTIK_USER}@{MIKROTIK_IP} /ppp/active/print\\ terse"
    )
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
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
    cmd = (
        f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes "
        f'{MIKROTIK_USER}@{MIKROTIK_IP} "/ip firewall address-list print terse where list=avisos-visto"'
    )
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
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
    mk_script = (
        f'/ip firewall address-list remove [find where list=avisos address={ip}]; '
        f'/ip firewall address-list add list=avisos-visto address={ip} comment="{comment}"'
    )
    cmd = (
        f"ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes "
        f'{MIKROTIK_USER}@{MIKROTIK_IP} "{mk_script}"'
    )
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
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

if __name__ == "__main__":
    log.info("Starting avisos portal on port 8090")
    web.run_app(app, host="0.0.0.0", port=8090, print=None)
