"""Clean up UISP: delete phantom and unknown devices."""
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

# Find phantoms (no name AND no IP) and unknowns
to_delete = []
for d in devices:
    ident = d.get("identification", {}) or {}
    ov = d.get("overview", {}) or {}
    status = ov.get("status", "")
    name = ident.get("name") or ident.get("hostname") or ""
    ip = (ident.get("ip") or "").split("/")[0]
    mac = ident.get("mac") or "?"
    model = ident.get("model") or ""
    did = d.get("id", "")

    # Phantom: no name AND no IP
    is_phantom = not name and not ip
    # Unknown model
    is_unknown = model == "UNKNOWN" or status == "unknown"

    if is_phantom or is_unknown:
        reason = "fantasma" if is_phantom else "unknown"
        to_delete.append({
            "id": did, "mac": mac, "name": name or "(sin nombre)",
            "model": model, "status": status, "reason": reason
        })

# Also check for disconnected duplicates: same name exists as active
active_names = set()
for d in devices:
    ident = d.get("identification", {}) or {}
    ov = d.get("overview", {}) or {}
    if ov.get("status") == "active":
        n = (ident.get("name") or "").lower().strip()
        if n:
            active_names.add(n)

for d in devices:
    ident = d.get("identification", {}) or {}
    ov = d.get("overview", {}) or {}
    status = ov.get("status", "")
    name = ident.get("name") or ""
    did = d.get("id", "")
    mac = ident.get("mac") or "?"
    model = ident.get("model") or ""

    if status == "disconnected" and name and name.lower().strip() in active_names:
        already = any(x["id"] == did for x in to_delete)
        if not already:
            to_delete.append({
                "id": did, "mac": mac, "name": name,
                "model": model, "status": status, "reason": "duplicado (activo existe)"
            })

print("DISPOSITIVOS A ELIMINAR: {}".format(len(to_delete)))
print("=" * 90)

deleted = 0
failed = 0
no_id = 0

for d in to_delete:
    did = d["id"]
    print("  {} | {} | {} | {} | {}".format(
        d["reason"], d["name"], d["mac"], d["model"], d["status"]), end="")

    if not did:
        print(" -> SIN ID, buscando por MAC...")
        # Try to delete via MAC - need to find ID in raw response
        for raw in devices:
            raw_ident = raw.get("identification", {}) or {}
            if (raw_ident.get("mac") or "") == d["mac"]:
                did = raw.get("id", "")
                break

    if not did:
        print(" -> NO SE PUEDE ELIMINAR (sin ID)")
        no_id += 1
        continue

    try:
        dreq = urllib.request.Request(
            "https://server.auralink.link/nms/api/v2.1/devices/{}".format(did),
            method="DELETE",
            headers={"x-auth-token": nms_token},
        )
        resp = urllib.request.urlopen(dreq, context=ctx)
        print(" -> ELIMINADO")
        deleted += 1
    except Exception as e:
        print(" -> ERROR: {}".format(e))
        failed += 1

print("\n" + "=" * 90)
print("RESULTADO: {} eliminados, {} fallidos, {} sin ID".format(deleted, failed, no_id))

# Final count
req2 = urllib.request.Request(
    "https://server.auralink.link/nms/api/v2.1/devices",
    headers={"x-auth-token": nms_token},
)
devices2 = json.loads(urllib.request.urlopen(req2, context=ctx).read())
active2 = sum(1 for d in devices2 if (d.get("overview", {}) or {}).get("status") == "active")
total2 = len(devices2)
print("\nDISPOSITIVOS DESPUES DE LIMPIEZA: {} total, {} activos".format(total2, active2))
