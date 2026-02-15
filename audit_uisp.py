"""Audit UISP: find all unauthorized/phantom devices."""
import urllib.request, json, ssl, subprocess

ctx = ssl._create_unverified_context()

nms_token = subprocess.check_output(
    ["docker", "exec", "unms-postgres", "psql", "-U", "postgres", "-d", "unms",
     "-t", "-A", "-c", "SELECT token FROM unms.token LIMIT 1;"]
).decode().strip()

# All devices
req = urllib.request.Request(
    "https://server.auralink.link/nms/api/v2.1/devices",
    headers={"x-auth-token": nms_token},
)
devices = json.loads(urllib.request.urlopen(req, context=ctx).read())

# Categorize
active = []
disconnected = []
unauthorized = []
unknown = []

for d in devices:
    ident = d.get("identification", {}) or {}
    ov = d.get("overview", {}) or {}
    status = ov.get("status", "")
    name = ident.get("name") or ident.get("hostname") or "(sin nombre)"
    mac = ident.get("mac") or "?"
    ip = (ident.get("ip") or "").split("/")[0] or "(sin IP)"
    model = ident.get("model") or ident.get("modelName") or "?"
    role = ident.get("role") or "?"
    did = d.get("id") or "?"

    info = {
        "id": did, "name": name, "mac": mac, "ip": ip,
        "model": model, "role": role, "status": status,
    }

    if status == "active":
        active.append(info)
    elif status == "disconnected":
        disconnected.append(info)
    elif status == "unauthorized":
        unauthorized.append(info)
    else:
        unknown.append(info)

print("=" * 90)
print("AUDITORIA UISP - DISPOSITIVOS")
print("=" * 90)
print("Total: {}  |  Active: {}  |  Disconnected: {}  |  Unauthorized: {}  |  Unknown: {}".format(
    len(devices), len(active), len(disconnected), len(unauthorized), len(unknown)))

# Unauthorized (pending adoption)
print("\n" + "=" * 90)
print("PENDIENTES DE ADOPCION / UNAUTHORIZED ({})".format(len(unauthorized)))
print("=" * 90)
print("{:<3} {:<22} {:<18} {:<16} {:<12} {}".format("#", "Nombre", "MAC", "IP", "Modelo", "ID"))
print("-" * 90)
n = 1
for d in unauthorized:
    print("{:<3} {:<22} {:<18} {:<16} {:<12} {}".format(
        n, d["name"][:21], d["mac"], d["ip"][:15], d["model"][:11], d["id"][:36]))
    n += 1

# Disconnected
print("\n" + "=" * 90)
print("DESCONECTADOS ({})".format(len(disconnected)))
print("=" * 90)
print("{:<3} {:<22} {:<18} {:<16} {:<12}".format("#", "Nombre", "MAC", "IP", "Modelo"))
print("-" * 90)
n = 1
for d in disconnected:
    print("{:<3} {:<22} {:<18} {:<16} {:<12}".format(
        n, d["name"][:21], d["mac"], d["ip"][:15], d["model"][:11]))
    n += 1

# Unknown
if unknown:
    print("\n" + "=" * 90)
    print("UNKNOWN ({})".format(len(unknown)))
    print("=" * 90)
    for d in unknown:
        print("  {} | {} | {} | {} | status={}".format(
            d["name"], d["mac"], d["ip"], d["model"], d["status"]))

# Phantom check: devices with no name AND no IP
phantoms = [d for d in devices if
    not (d.get("identification", {}) or {}).get("name") and
    not (d.get("identification", {}) or {}).get("ip")]
print("\n" + "=" * 90)
print("DISPOSITIVOS FANTASMA (sin nombre Y sin IP): {}".format(len(phantoms)))
print("=" * 90)
for d in phantoms:
    ident = d.get("identification", {}) or {}
    ov = d.get("overview", {}) or {}
    mac = ident.get("mac") or "?"
    model = ident.get("model") or "?"
    status = ov.get("status", "?")
    did = d.get("id") or "?"
    print("  MAC: {:<18} Model: {:<12} Status: {:<14} ID: {}".format(mac, model, status, did))
