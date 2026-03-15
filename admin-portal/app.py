"""AURALINK Admin Portal — Backend API."""

import asyncio
import html
import json
import logging
import os
import ssl
import time
from pathlib import Path

import aiohttp
import aiosqlite
from aiohttp import web

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("admin-portal")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "auralink-admin-2026")
BOT_DB_PATH = os.getenv("BOT_DB_PATH", "/app/botdata/aura.db")
ADMIN_DB_PATH = os.getenv("ADMIN_DB_PATH", "/app/data/admin.db")
UISP_BASE = os.getenv("UISP_BASE_URL", "https://server.auralink.link")
UISP_TOKEN = os.getenv("UISP_API_TOKEN", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
PORT = int(os.getenv("PORT", "8092"))
BACKUPS_BASE = os.getenv("BACKUPS_BASE", "/app/backups")

# Registry of backup devices — add new MikroTiks here
BACKUP_DEVICES = {
    "mikrotik": {
        "name": "MikroTik RB5009 Balanceador",
        "description": "Balanceador principal — Tomatlan",
        "host": "10.147.17.11",
        "user": "admin",
        "dir": "mikrotik",
    },
}
SSL_CERT = os.getenv("SSL_CERT", "/app/certs/live.crt")
SSL_KEY = os.getenv("SSL_KEY", "/app/certs/live.key")

CRM_API = f"{UISP_BASE}/crm/api/v1.0"
NMS_API = f"{UISP_BASE}/nms/api/v2.1"
TG_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
_cache: dict[str, tuple[float, object]] = {}
CACHE_TTL = 60


def _cached(key: str):
    entry = _cache.get(key)
    if entry and time.time() - entry[0] < CACHE_TTL:
        return entry[1]
    return None


def _set_cache(key: str, val: object):
    _cache[key] = (time.time(), val)


# ---------------------------------------------------------------------------
# Admin DB (portal's own)
# ---------------------------------------------------------------------------
async def init_admin_db():
    async with aiosqlite.connect(ADMIN_DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS broadcast_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_text TEXT,
                category TEXT DEFAULT 'aviso',
                recipient_count INTEGER,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_by TEXT DEFAULT 'admin'
            );
            CREATE TABLE IF NOT EXISTS broadcast_recipients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                broadcast_id INTEGER REFERENCES broadcast_log(id),
                telegram_user_id INTEGER,
                client_name TEXT,
                status TEXT DEFAULT 'sent',
                error TEXT
            );
        """)
        await db.commit()


# ---------------------------------------------------------------------------
# UISP helpers
# ---------------------------------------------------------------------------
_session: aiohttp.ClientSession | None = None


def _uisp_headers():
    return {"x-auth-token": UISP_TOKEN}


async def _get(url: str) -> list | dict | None:
    global _session
    if _session is None or _session.closed:
        conn = aiohttp.TCPConnector(ssl=False)
        _session = aiohttp.ClientSession(connector=conn)
    try:
        async with _session.get(url, headers=_uisp_headers(), timeout=aiohttp.ClientTimeout(total=15)) as r:
            if r.status == 200:
                return await r.json()
            log.warning("GET %s → %s", url, r.status)
            return None
    except Exception as e:
        log.error("GET %s error: %s", url, e)
        return None


async def crm_clients():
    cached = _cached("crm_clients")
    if cached:
        return cached
    data = await _get(f"{CRM_API}/clients?direction=ASC&limit=500") or []
    _set_cache("crm_clients", data)
    return data


async def crm_services():
    cached = _cached("crm_services")
    if cached:
        return cached
    data = await _get(f"{CRM_API}/clients/services") or []
    _set_cache("crm_services", data)
    return data


async def crm_invoices_unpaid():
    cached = _cached("crm_invoices_unpaid")
    if cached:
        return cached
    data = await _get(f"{CRM_API}/invoices?statuses[]=1&statuses[]=2&limit=500") or []
    _set_cache("crm_invoices_unpaid", data)
    return data


async def nms_devices():
    cached = _cached("nms_devices")
    if cached:
        return cached
    data = await _get(f"{NMS_API}/devices") or []
    _set_cache("nms_devices", data)
    return data


async def nms_outages():
    cached = _cached("nms_outages")
    if cached:
        return cached
    data = await _get(f"{NMS_API}/outages?count=20&page=1&type=outage&affectedOnly=true") or []
    _set_cache("nms_outages", data)
    return data


async def nms_sites():
    cached = _cached("nms_sites")
    if cached:
        return cached
    data = await _get(f"{NMS_API}/sites") or []
    _set_cache("nms_sites", data)
    return data


# ---------------------------------------------------------------------------
# Bot DB helpers (read-only)
# ---------------------------------------------------------------------------
async def bot_db_query(sql: str, params=()) -> list[dict]:
    try:
        async with aiosqlite.connect(f"file:{BOT_DB_PATH}?mode=ro", uri=True) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]
    except Exception as e:
        log.error("Bot DB query error: %s", e)
        return []


async def get_registered_users() -> list[dict]:
    return await bot_db_query(
        "SELECT telegram_user_id, crm_client_id, crm_client_name, service_id, linked_at FROM customer_links"
    )


async def get_onboarding() -> list[dict]:
    return await bot_db_query("SELECT * FROM onboarding_tracking")


async def get_escalations() -> list[dict]:
    return await bot_db_query("SELECT * FROM escalations ORDER BY created_at DESC")


# ---------------------------------------------------------------------------
# Auth middleware
# ---------------------------------------------------------------------------
@web.middleware
async def auth_middleware(request, handler):
    if request.path.startswith("/api/"):
        token = request.headers.get("X-Admin-Token", "")
        if token != ADMIN_TOKEN:
            return web.json_response({"error": "unauthorized"}, status=401)
    return await handler(request)


# ---------------------------------------------------------------------------
# Excluded accounts (not real clients)
# ---------------------------------------------------------------------------
EXCLUDED_NAMES = {
    "martin pintor", "casa cristina", "mabil", "deportes", "dif tomatlan",
    "javier araiza", "laura cumbre", "marcia", "oscarsunyt", "pelonc",
    "peloncoco", "tia gloria",
}


def is_excluded(name: str) -> bool:
    n = name.lower().strip()
    for ex in EXCLUDED_NAMES:
        if ex in n or n in ex:
            return True
    return False


# ---------------------------------------------------------------------------
# Zone detection helper
# ---------------------------------------------------------------------------
ZONE_MAP = {
    "tomatl": "TML", "cumbre": "CBR", "penitas": "PNS", "peñitas": "PNS",
    "gloria": "GLR", "coco": "COC", "tule": "TUL", "nahuapa": "NAH",
    "bajez": "BJZ", "bajéz": "BJZ", "centro": "CTR", "sagra": "SGR",
    "corral": "CRL", "jaluco": "JAL", "aurora": "AUR", "colmen": "COL",
    "piedra": "PPM", "tierrit": "TIE",
}


def detect_zone(svc: dict) -> str:
    addr = (
        (svc.get("street") or "") + " " +
        (svc.get("city") or "") + " " +
        (svc.get("addressGpsLat") and "" or "")
    ).lower()
    for key, abbr in ZONE_MAP.items():
        if key in addr:
            return abbr
    return "OTR"


# ---------------------------------------------------------------------------
# API: Dashboard
# ---------------------------------------------------------------------------
async def api_dashboard(request):
    clients_raw, devices, registered, outages = await asyncio.gather(
        crm_clients(), nms_devices(), get_registered_users(), nms_outages()
    )
    services = await crm_services()
    clients = [c for c in clients_raw if not is_excluded(
        f'{c.get("firstName", "")} {c.get("lastName", "")}'.strip() or c.get("companyName", "")
    )]
    online = sum(1 for d in devices if d.get("overview", {}).get("status") == "active")
    offline = sum(1 for d in devices if d.get("overview", {}).get("status") in ("disconnected", "inactive"))

    morosos = sum(1 for s in services if s.get("status") == 3)

    # Registration timeline (last 14 days)
    timeline = await bot_db_query("""
        SELECT DATE(linked_at) as day, COUNT(*) as count
        FROM customer_links WHERE linked_at >= DATE('now', '-14 days')
        GROUP BY DATE(linked_at) ORDER BY day
    """)

    # Active outages
    active_outages = []
    if isinstance(outages, list):
        for o in outages:
            if not o.get("endTimestamp"):
                active_outages.append({
                    "id": o.get("id"),
                    "device": o.get("device", {}).get("name", "Unknown"),
                    "site": o.get("site", {}).get("name", ""),
                    "start": o.get("startTimestamp"),
                })

    return web.json_response({
        "clients_total": len(clients),
        "services_total": len(services),
        "registered": len(registered),
        "devices_online": online,
        "devices_offline": offline,
        "devices_total": len(devices),
        "morosos": morosos,
        "pppoe_active": sum(1 for s in services if s.get("status") == 1),
        "registration_timeline": timeline,
        "active_outages": active_outages,
    })


# ---------------------------------------------------------------------------
# API: Clients
# ---------------------------------------------------------------------------
async def api_clients(request):
    search = request.query.get("search", "").lower()
    zone_filter = request.query.get("zone", "")
    status_filter = request.query.get("status", "")

    clients, services, registered = await asyncio.gather(
        crm_clients(), crm_services(), get_registered_users()
    )

    reg_map = {r["crm_client_id"]: r for r in registered}
    svc_map: dict[int, list] = {}
    for s in services:
        cid = s.get("clientId")
        if cid:
            svc_map.setdefault(cid, []).append(s)

    result = []
    for c in clients:
        cid = c.get("id")
        name = f'{c.get("firstName", "")} {c.get("lastName", "")}'.strip()
        if not name:
            name = c.get("companyName", "Sin nombre")
        if is_excluded(name):
            continue
        svcs = svc_map.get(cid, [])
        svc = svcs[0] if svcs else {}
        zone = detect_zone(svc) if svc else "OTR"
        reg = reg_map.get(cid)
        plan = svc.get("servicePlanName", "")
        status = "moroso" if svc.get("status") == 3 else ("activo" if svc.get("status") == 1 else "otro")

        # Filters
        if search and search not in name.lower() and search not in (reg.get("service_id", "") if reg else "").lower() and search not in zone.lower():
            continue
        if zone_filter and zone != zone_filter:
            continue
        if status_filter == "activo" and status != "activo":
            continue
        if status_filter == "moroso" and status != "moroso":
            continue
        if status_filter == "registrado" and not reg:
            continue
        if status_filter == "no_registrado" and reg:
            continue

        result.append({
            "id": cid,
            "name": name,
            "service_id": reg.get("service_id", "") if reg else "",
            "plan": plan,
            "balance": c.get("accountBalance", 0),
            "status": status,
            "registered": bool(reg),
            "registered_at": reg.get("linked_at") if reg else None,
            "zone": zone,
            "ip": svc.get("addressGpsLat", ""),  # placeholder
            "service_status": svc.get("status"),
        })

    result.sort(key=lambda x: x["name"])
    return web.json_response(result)


async def api_client_detail(request):
    client_id = int(request.match_info["id"])
    client_data = await _get(f"{CRM_API}/clients/{client_id}")
    if not client_data:
        return web.json_response({"error": "not found"}, status=404)

    services, invoices, registered = await asyncio.gather(
        _get(f"{CRM_API}/clients/{client_id}/services") or [],
        _get(f"{CRM_API}/clients/{client_id}/invoices") or [],
        bot_db_query("SELECT * FROM customer_links WHERE crm_client_id=?", (client_id,))
    )

    return web.json_response({
        "client": client_data,
        "services": services or [],
        "invoices": invoices or [],
        "registration": registered[0] if registered else None,
    })


# ---------------------------------------------------------------------------
# API: Finance
# ---------------------------------------------------------------------------
async def api_finance_summary(request):
    services = await crm_services()
    invoices = await crm_invoices_unpaid()

    plan_counts: dict[str, int] = {}
    for s in services:
        if s.get("status") in (1, 3):
            plan = s.get("servicePlanName", "Otro")
            plan_counts[plan] = plan_counts.get(plan, 0) + 1

    total_unpaid = sum(float(inv.get("total", 0)) - float(inv.get("amountPaid", 0)) for inv in (invoices or []))
    morosos_count = sum(1 for s in services if s.get("status") == 3)

    return web.json_response({
        "total_unpaid": round(total_unpaid, 2),
        "morosos_count": morosos_count,
        "plan_distribution": plan_counts,
        "invoice_count": len(invoices) if invoices else 0,
    })


async def api_finance_morosos(request):
    clients, services = await asyncio.gather(crm_clients(), crm_services())
    client_map = {c["id"]: c for c in clients}

    morosos = []
    for s in services:
        if s.get("status") == 3:
            cid = s.get("clientId")
            c = client_map.get(cid, {})
            name = f'{c.get("firstName", "")} {c.get("lastName", "")}'.strip() or c.get("companyName", "?")
            balance = c.get("accountBalance", 0)
            morosos.append({
                "client_id": cid,
                "name": name,
                "balance": balance,
                "plan": s.get("servicePlanName", ""),
            })

    morosos.sort(key=lambda x: x["balance"])
    return web.json_response(morosos)


# ---------------------------------------------------------------------------
# API: Registrations
# ---------------------------------------------------------------------------
async def api_registrations(request):
    registered, onboarding, services, clients_raw = await asyncio.gather(
        get_registered_users(), get_onboarding(), crm_services(), crm_clients()
    )

    excluded_ids = {c["id"] for c in clients_raw if is_excluded(
        f'{c.get("firstName", "")} {c.get("lastName", "")}'.strip() or c.get("companyName", "")
    )}
    active_services = [s for s in services if s.get("status") in (1, 3) and s.get("clientId") not in excluded_ids]
    total_clients = len(active_services)

    zone_stats: dict[str, dict] = {}
    for s in active_services:
        z = detect_zone(s)
        if z not in zone_stats:
            zone_stats[z] = {"total": 0, "linked": 0, "contacted": 0, "pending": 0}
        zone_stats[z]["total"] += 1

    reg_client_ids = {r["crm_client_id"] for r in registered}
    contacted_ids = {o["crm_client_id"] for o in onboarding if o.get("status") == "contacted"}

    for s in active_services:
        z = detect_zone(s)
        cid = s.get("clientId")
        if cid in reg_client_ids:
            zone_stats[z]["linked"] += 1
        elif cid in contacted_ids:
            zone_stats[z]["contacted"] += 1
        else:
            zone_stats[z]["pending"] += 1

    return web.json_response({
        "total_clients": total_clients,
        "total_registered": len(registered),
        "percent": round(len(registered) / max(total_clients, 1) * 100, 1),
        "zone_stats": zone_stats,
        "registered_list": [
            {"name": r["crm_client_name"], "service_id": r.get("service_id", ""), "linked_at": r["linked_at"]}
            for r in registered
        ],
    })


async def api_registrations_timeline(request):
    rows = await bot_db_query("""
        SELECT DATE(linked_at) as day, COUNT(*) as count
        FROM customer_links WHERE linked_at IS NOT NULL
        GROUP BY DATE(linked_at) ORDER BY day
    """)
    # Build cumulative
    cumulative = []
    total = 0
    for r in rows:
        total += r["count"]
        cumulative.append({"day": r["day"], "count": r["count"], "cumulative": total})
    return web.json_response(cumulative)


# ---------------------------------------------------------------------------
# API: Network
# ---------------------------------------------------------------------------
async def api_network_overview(request):
    devices = await nms_devices()
    by_status = {"active": 0, "disconnected": 0, "inactive": 0, "other": 0}
    for d in devices:
        st = d.get("overview", {}).get("status", "other")
        if st in by_status:
            by_status[st] += 1
        else:
            by_status["other"] += 1
    return web.json_response({
        "total": len(devices),
        "by_status": by_status,
    })


async def api_network_outages(request):
    outages = await nms_outages()
    result = []
    if isinstance(outages, list):
        for o in outages:
            result.append({
                "id": o.get("id"),
                "device": o.get("device", {}).get("name", "?"),
                "site": o.get("site", {}).get("name", ""),
                "start": o.get("startTimestamp"),
                "end": o.get("endTimestamp"),
                "type": o.get("type"),
            })
    return web.json_response(result)


# ---------------------------------------------------------------------------
# API: Messages
# ---------------------------------------------------------------------------
async def api_messages_preview(request):
    body = await request.json()
    text = body.get("text", "")
    # Simple markdown→HTML preview
    preview_html = html.escape(text)
    preview_html = preview_html.replace("\n", "<br>")
    return web.json_response({"preview": preview_html, "length": len(text)})


async def api_messages_send(request):
    body = await request.json()
    text = body.get("text", "")
    recipient_ids = body.get("recipient_ids", [])
    category = body.get("category", "aviso")

    if not text or not recipient_ids:
        return web.json_response({"error": "text and recipient_ids required"}, status=400)

    # Create broadcast log
    async with aiosqlite.connect(ADMIN_DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO broadcast_log (message_text, category, recipient_count) VALUES (?, ?, ?)",
            (text, category, len(recipient_ids))
        )
        broadcast_id = cur.lastrowid

        sent = 0
        errors = 0
        for uid in recipient_ids:
            try:
                async with _session.post(
                    f"{TG_API}/sendMessage",
                    json={"chat_id": uid, "text": text, "parse_mode": "Markdown"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as r:
                    if r.status == 200:
                        await db.execute(
                            "INSERT INTO broadcast_recipients (broadcast_id, telegram_user_id, status) VALUES (?, ?, 'sent')",
                            (broadcast_id, uid)
                        )
                        sent += 1
                    else:
                        err = await r.text()
                        await db.execute(
                            "INSERT INTO broadcast_recipients (broadcast_id, telegram_user_id, status, error) VALUES (?, ?, 'failed', ?)",
                            (broadcast_id, uid, err[:200])
                        )
                        errors += 1
            except Exception as e:
                await db.execute(
                    "INSERT INTO broadcast_recipients (broadcast_id, telegram_user_id, status, error) VALUES (?, ?, 'failed', ?)",
                    (broadcast_id, uid, str(e)[:200])
                )
                errors += 1
            await asyncio.sleep(0.05)

        await db.commit()

    return web.json_response({"broadcast_id": broadcast_id, "sent": sent, "errors": errors})


async def api_messages_recipients(request):
    """Get available recipients (registered users)."""
    registered = await get_registered_users()
    zone_filter = request.query.get("zone", "")
    result = []
    services = await crm_services()
    svc_by_client = {}
    for s in services:
        cid = s.get("clientId")
        if cid:
            svc_by_client[cid] = s

    for r in registered:
        svc = svc_by_client.get(r["crm_client_id"], {})
        zone = detect_zone(svc) if svc else "OTR"
        if zone_filter and zone != zone_filter:
            continue
        result.append({
            "telegram_user_id": r["telegram_user_id"],
            "name": r["crm_client_name"],
            "zone": zone,
            "service_id": r.get("service_id", ""),
        })
    return web.json_response(result)


async def api_messages_history(request):
    async with aiosqlite.connect(ADMIN_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM broadcast_log ORDER BY sent_at DESC LIMIT 50") as cur:
            rows = await cur.fetchall()
            return web.json_response([dict(r) for r in rows])


# ---------------------------------------------------------------------------
# API: Support
# ---------------------------------------------------------------------------
async def api_support_tickets(request):
    tickets = await bot_db_query("""
        SELECT e.id, e.telegram_user_id, e.telegram_username, e.crm_client_id,
               e.issue, e.status, e.created_at, e.resolved_at,
               cl.crm_client_name
        FROM escalations e
        LEFT JOIN customer_links cl ON CAST(e.crm_client_id AS TEXT) = CAST(cl.crm_client_id AS TEXT)
        ORDER BY e.created_at DESC
    """)
    result = []
    for t in tickets:
        result.append({
            "id": t["id"],
            "client_name": t.get("crm_client_name") or t.get("telegram_username") or str(t.get("telegram_user_id", "?")),
            "details": t.get("issue", ""),
            "status": t.get("status", "open"),
            "created_at": t.get("created_at"),
            "resolved_at": t.get("resolved_at"),
            "telegram_user_id": t.get("telegram_user_id"),
            "crm_client_id": t.get("crm_client_id"),
        })
    return web.json_response(result)


async def api_support_resolve(request):
    ticket_id = int(request.match_info["id"])
    try:
        async with aiosqlite.connect(BOT_DB_PATH) as db:
            await db.execute(
                "UPDATE escalations SET status='resolved', resolved_at=CURRENT_TIMESTAMP WHERE id=?",
                (ticket_id,)
            )
            await db.commit()
        return web.json_response({"ok": True})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


# ---------------------------------------------------------------------------
# API: Backups (multi-device, grouped by month)
# ---------------------------------------------------------------------------
def _backup_dir(device_id: str) -> Path | None:
    dev = BACKUP_DEVICES.get(device_id)
    if not dev:
        return None
    return Path(BACKUPS_BASE) / dev["dir"]


def _parse_backup_date(filename: str) -> str | None:
    """Extract YYYY-MM-DD from backup-YYYY-MM-DD.ext"""
    import re
    m = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
    return m.group(1) if m else None


async def api_backup_devices(request):
    """List registered backup devices with last backup info."""
    result = []
    for dev_id, dev in BACKUP_DEVICES.items():
        bdir = Path(BACKUPS_BASE) / dev["dir"]
        last_backup = None
        backup_count = 0
        if bdir.exists():
            files = [f for f in bdir.iterdir() if f.is_file() and f.suffix in (".backup", ".rsc")]
            backup_count = len(files)
            if files:
                newest = max(files, key=lambda x: x.stat().st_mtime)
                last_backup = time.strftime("%Y-%m-%d %H:%M", time.localtime(newest.stat().st_mtime))
        result.append({
            "id": dev_id,
            "name": dev["name"],
            "description": dev["description"],
            "host": dev["host"],
            "last_backup": last_backup,
            "file_count": backup_count,
        })
    return web.json_response(result)


async def api_backup_files(request):
    """List backups for a device, grouped by month."""
    device_id = request.match_info["device_id"]
    bdir = _backup_dir(device_id)
    if bdir is None:
        return web.json_response({"error": "unknown device"}, status=404)

    # Collect files grouped by date
    by_date: dict[str, list] = {}
    if bdir.exists():
        for f in bdir.iterdir():
            if not f.is_file() or f.suffix not in (".backup", ".rsc"):
                continue
            date = _parse_backup_date(f.name)
            if not date:
                continue
            st = f.stat()
            by_date.setdefault(date, []).append({
                "filename": f.name,
                "type": "binary" if f.suffix == ".backup" else "export",
                "size": st.st_size,
                "size_human": f"{st.st_size/1024:.1f} KB" if st.st_size < 1048576 else f"{st.st_size/1048576:.1f} MB",
            })

    # Group by month
    months: dict[str, list] = {}
    for date in sorted(by_date.keys(), reverse=True):
        month_key = date[:7]  # YYYY-MM
        months.setdefault(month_key, []).append({
            "date": date,
            "files": sorted(by_date[date], key=lambda x: x["filename"]),
        })

    dev = BACKUP_DEVICES[device_id]
    return web.json_response({
        "device": {"id": device_id, "name": dev["name"], "description": dev["description"]},
        "months": [{"month": k, "days": v} for k, v in sorted(months.items(), reverse=True)],
    })


async def api_backup_download(request):
    """Download a specific backup file."""
    device_id = request.match_info["device_id"]
    filename = request.match_info["filename"]
    if not all(c.isalnum() or c in "-_." for c in filename):
        return web.json_response({"error": "invalid filename"}, status=400)
    bdir = _backup_dir(device_id)
    if bdir is None:
        return web.json_response({"error": "unknown device"}, status=404)
    fpath = bdir / filename
    if not fpath.exists() or not fpath.is_file():
        return web.json_response({"error": "not found"}, status=404)
    return web.FileResponse(fpath, headers={
        "Content-Disposition": f'attachment; filename="{filename}"'
    })


async def api_backup_create(request):
    """Trigger a new backup for a device via SSH."""
    import datetime
    device_id = request.match_info["device_id"]
    dev = BACKUP_DEVICES.get(device_id)
    if not dev:
        return web.json_response({"error": "unknown device"}, status=404)

    date_str = datetime.date.today().isoformat()
    fname = f"backup-{date_str}"
    ssh_opts = "-o StrictHostKeyChecking=no -o ConnectTimeout=10"
    host = dev["host"]
    user = dev["user"]

    # 1. Run backup on MikroTik
    cmd = (
        f"ssh {ssh_opts} {user}@{host} "
        f"'/system backup save name={fname} dont-encrypt=yes; /export file={fname}'"
    )
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

    if proc.returncode != 0 and b"Configuration backup saved" not in stdout:
        return web.json_response({
            "error": "backup command failed",
            "detail": (stderr or stdout or b"").decode()[:300]
        }, status=500)

    # 2. Pull files via SCP
    bdir = Path(BACKUPS_BASE) / dev["dir"]
    bdir.mkdir(parents=True, exist_ok=True)

    pulled = []
    for ext in (".backup", ".rsc"):
        scp_cmd = f"scp {ssh_opts} {user}@{host}:{fname}{ext} {bdir}/{fname}{ext}"
        scp_proc = await asyncio.create_subprocess_shell(
            scp_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await asyncio.wait_for(scp_proc.communicate(), timeout=30)
        if (bdir / f"{fname}{ext}").exists():
            pulled.append(f"{fname}{ext}")

    # 3. Cleanup old (keep 14 days)
    cutoff = time.time() - 14 * 86400
    for f in bdir.iterdir():
        if f.is_file() and f.name.startswith("backup-") and f.stat().st_mtime < cutoff:
            f.unlink()

    return web.json_response({"ok": True, "files": pulled, "date": date_str})


# ---------------------------------------------------------------------------
# API: Services (Docker container management)
# ---------------------------------------------------------------------------
MANAGED_SERVICES = {
    "aura-bot": {
        "name": "Aura Bot",
        "description": "Bot de Telegram (IA, registro, cobranza, monitoreo)",
        "compose_dir": "/root/aura-bot",
    },
    "avisos-portal": {
        "name": "Portal de Avisos",
        "description": "Captive portal para avisos a clientes",
        "compose_dir": "/root/avisos-portal",
    },
    "admin-portal": {
        "name": "Admin Portal",
        "description": "Este panel de administracion",
        "compose_dir": "/root/admin-portal",
    },
}


async def _run_ssh_cmd(cmd: str, timeout: int = 30) -> tuple[int, str, str]:
    """Run a command via shell. Returns (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_shell(
        cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return -1, "", "timeout"
    return proc.returncode, (stdout or b"").decode(), (stderr or b"").decode()


async def api_services_list(request):
    """List managed services with their Docker container status."""
    result = []
    for svc_id, svc in MANAGED_SERVICES.items():
        # Get container status
        rc, stdout, stderr = await _run_ssh_cmd(
            f"docker inspect --format '{{{{.State.Status}}}} {{{{.State.StartedAt}}}}' {svc_id} 2>/dev/null"
        )
        status = "unknown"
        started_at = ""
        if rc == 0 and stdout.strip():
            parts = stdout.strip().split(" ", 1)
            status = parts[0]
            started_at = parts[1] if len(parts) > 1 else ""

        result.append({
            "id": svc_id,
            "name": svc["name"],
            "description": svc["description"],
            "status": status,
            "started_at": started_at[:19].replace("T", " ") if started_at else "",
        })
    return web.json_response(result)


async def api_service_restart(request):
    """Restart a managed Docker service."""
    svc_id = request.match_info["service_id"]
    svc = MANAGED_SERVICES.get(svc_id)
    if not svc:
        return web.json_response({"error": "unknown service"}, status=404)

    compose_dir = svc["compose_dir"]
    log.info("Restarting service %s (dir: %s)", svc_id, compose_dir)

    rc, stdout, stderr = await _run_ssh_cmd(
        f"docker compose -f {compose_dir}/docker-compose.yml restart",
        timeout=60
    )

    if rc != 0:
        return web.json_response({
            "error": "restart failed",
            "detail": (stderr or stdout)[:500]
        }, status=500)

    return web.json_response({"ok": True, "service": svc_id})


async def api_service_logs(request):
    """Get recent logs for a managed Docker service."""
    svc_id = request.match_info["service_id"]
    if svc_id not in MANAGED_SERVICES:
        return web.json_response({"error": "unknown service"}, status=404)

    lines = int(request.query.get("lines", "50"))
    lines = min(lines, 200)

    rc, stdout, stderr = await _run_ssh_cmd(
        f"docker logs {svc_id} --tail {lines} 2>&1",
        timeout=15
    )

    return web.json_response({"logs": stdout or stderr, "lines": lines})


# ---------------------------------------------------------------------------
# Static files + App setup
# ---------------------------------------------------------------------------
async def on_startup(app):
    await init_admin_db()
    global _session
    conn = aiohttp.TCPConnector(ssl=False)
    _session = aiohttp.ClientSession(connector=conn)
    log.info("Admin portal started on port %d", PORT)


async def on_cleanup(app):
    global _session
    if _session and not _session.closed:
        await _session.close()


def create_app():
    app = web.Application(middlewares=[auth_middleware])

    # API routes
    app.router.add_get("/api/dashboard", api_dashboard)
    app.router.add_get("/api/clients", api_clients)
    app.router.add_get("/api/clients/{id}", api_client_detail)
    app.router.add_get("/api/finance/summary", api_finance_summary)
    app.router.add_get("/api/finance/morosos", api_finance_morosos)
    app.router.add_get("/api/registrations", api_registrations)
    app.router.add_get("/api/registrations/timeline", api_registrations_timeline)
    app.router.add_get("/api/network/overview", api_network_overview)
    app.router.add_get("/api/network/outages", api_network_outages)
    app.router.add_post("/api/messages/preview", api_messages_preview)
    app.router.add_post("/api/messages/send", api_messages_send)
    app.router.add_get("/api/messages/recipients", api_messages_recipients)
    app.router.add_get("/api/messages/history", api_messages_history)
    app.router.add_get("/api/support/tickets", api_support_tickets)
    app.router.add_post("/api/support/tickets/{id}/resolve", api_support_resolve)
    app.router.add_get("/api/backups/devices", api_backup_devices)
    app.router.add_get("/api/backups/devices/{device_id}/files", api_backup_files)
    app.router.add_get("/api/backups/devices/{device_id}/download/{filename}", api_backup_download)
    app.router.add_post("/api/backups/devices/{device_id}/create", api_backup_create)
    app.router.add_get("/api/services", api_services_list)
    app.router.add_post("/api/services/{service_id}/restart", api_service_restart)
    app.router.add_get("/api/services/{service_id}/logs", api_service_logs)

    # Static files
    app.router.add_static("/static", Path(__file__).parent / "static")
    # Root → serve index.html
    app.router.add_get("/", lambda r: web.FileResponse(Path(__file__).parent / "static" / "index.html"))

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    ssl_ctx = None
    if Path(SSL_CERT).exists() and Path(SSL_KEY).exists():
        ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_ctx.load_cert_chain(SSL_CERT, SSL_KEY)
        log.info("SSL enabled with %s", SSL_CERT)
    else:
        log.warning("SSL certs not found, running HTTP only")
    web.run_app(create_app(), port=PORT, ssl_context=ssl_ctx)
