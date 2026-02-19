#!/usr/bin/env python3
"""Cross-reference MikroTik PPPoE active sessions against UISP devices."""
import json, re, sys, os

home = os.path.expanduser("~")
base = os.path.join(home, ".claude", "projects", "C--claude2", "b4b842ae-15bf-4b66-97ed-3496b06f9a26", "tool-results")

files = []
for fn in os.listdir(base):
    fp = os.path.join(base, fn)
    files.append((os.path.getsize(fp), fp, fn))
files.sort(key=lambda x: x[0])

PPP_FILE = files[0][1]
UISP_FILE = files[1][1]

# Parse PPP data
with open(PPP_FILE, "r") as f:
    ppp_raw = f.read()

sessions = []
current = {}
for line in ppp_raw.split("\n"):
    line = line.strip()
    if line.startswith("Flags:") or not line:
        continue
    num_match = re.match(r"^\d+", line)
    if num_match and current:
        sessions.append(current)
        current = {}
    for field in ["name=", "address=", "caller-id=", "service=", "uptime="]:
        if field in line:
            val = line.split(field)[1].split()[0].strip('"')
            current[field.rstrip("=")] = val
if current:
    sessions.append(current)

ppp_ips = {s.get("address", ""): s for s in sessions if s.get("address")}
ppp_macs = {}
for s in sessions:
    mac = s.get("caller-id", "").upper()
    if mac:
        ppp_macs[mac] = s

print(f"PPP active sessions parsed: {len(sessions)}")
print(f"PPP sessions with IP (10.10.x.x): {len([ip for ip in ppp_ips if ip.startswith('10.10.')])}")

# Parse UISP - IP is at d["ipAddress"], not d["identification"]["ip"]
with open(UISP_FILE, "r") as f:
    devices = json.load(f)

uisp_macs = {}
uisp_ips = {}
for d in devices:
    ident = d.get("identification", {}) or {}
    mac = (ident.get("mac") or "").upper()
    # IP is at root level, not in identification
    ip = (d.get("ipAddress") or "").split("/")[0]
    name = ident.get("name") or ident.get("displayName") or ""
    status = (d.get("overview", {}) or {}).get("status", "")
    authorized = ident.get("authorized", False)
    site_name = ""
    site = ident.get("site", {})
    if site:
        site_name = site.get("name", "")
    if mac:
        uisp_macs[mac] = {"name": name, "ip": ip, "status": status, "authorized": authorized, "site": site_name}
    if ip:
        uisp_ips[ip] = {"name": name, "mac": mac, "status": status, "authorized": authorized, "site": site_name}

print(f"UISP devices parsed: {len(devices)}")
print(f"UISP devices with IP: {len(uisp_ips)}")
print(f"UISP devices with MAC: {len(uisp_macs)}")
print()

# === PPP sessions NOT in UISP (by IP) ===
print("=" * 70)
print("=== PPP ACTIVE SESSIONS NOT IN UISP (by IP or MAC) ===")
print("=" * 70)
missing = 0
for ip in sorted(ppp_ips.keys()):
    s = ppp_ips[ip]
    if not ip.startswith("10.10."):
        continue
    mac = s.get("caller-id", "").upper()
    in_uisp_by_ip = ip in uisp_ips
    in_uisp_by_mac = mac in uisp_macs
    if not in_uisp_by_ip and not in_uisp_by_mac:
        print(f"  IP: {ip:15s} | Name: {s.get('name','?'):30s} | MAC: {mac}")
        missing += 1
print(f"\nTotal PPP active NOT in UISP (by IP or MAC): {missing}")
print()

# === PPP sessions where IP doesn't match UISP IP (by MAC) ===
print("=" * 70)
print("=== PPP <-> UISP IP MISMATCHES (same MAC, different IP) ===")
print("=" * 70)
mismatch = 0
for ip in sorted(ppp_ips.keys()):
    s = ppp_ips[ip]
    if not ip.startswith("10.10."):
        continue
    mac = s.get("caller-id", "").upper()
    if mac in uisp_macs:
        uisp_ip = uisp_macs[mac]["ip"]
        if uisp_ip and uisp_ip != ip:
            print(f"  PPP: {ip:15s} | UISP: {uisp_ip:15s} | Name: {s.get('name','?'):25s} | UISP Name: {uisp_macs[mac]['name']:25s} | MAC: {mac}")
            mismatch += 1
print(f"\nTotal IP mismatches: {mismatch}")
print()

# === UISP active devices NOT in PPP (clients only, 10.10.x.x) ===
print("=" * 70)
print("=== UISP ACTIVE DEVICES (10.10.x.x) NOT IN PPP ===")
print("=" * 70)
missing2 = 0
for mac in sorted(uisp_macs.keys()):
    info = uisp_macs[mac]
    if info["ip"].startswith("10.10.") and info["status"] == "active":
        if info["ip"] not in ppp_ips and mac not in ppp_macs:
            print(f"  {info['name']:30s} | IP: {info['ip']:15s} | MAC: {mac} | Site: {info['site']}")
            missing2 += 1
print(f"\nTotal UISP active NOT in PPP: {missing2}")
print()

# === UISP disconnected/unauthorized devices (10.10.x.x) ===
print("=" * 70)
print("=== UISP DISCONNECTED/UNAUTHORIZED DEVICES (10.10.x.x) ===")
print("=" * 70)
disc_count = 0
for mac in sorted(uisp_macs.keys()):
    info = uisp_macs[mac]
    if info["ip"].startswith("10.10.") and info["status"] != "active":
        in_ppp = "YES" if info["ip"] in ppp_ips or mac in ppp_macs else "NO"
        print(f"  {info['name']:30s} | IP: {info['ip']:15s} | Status: {info['status']:15s} | Auth: {str(info['authorized']):5s} | In PPP: {in_ppp}")
        disc_count += 1
print(f"\nTotal: {disc_count}")
print()

# === PPP sessions using 'clienteprueba' ===
print("=" * 70)
print("=== PPP SESSIONS USING 'clienteprueba' ===")
print("=" * 70)
cp_count = 0
for ip in sorted(ppp_ips.keys()):
    s = ppp_ips[ip]
    if s.get("name", "") == "clienteprueba":
        mac = s.get("caller-id", "").upper()
        uisp_info = ""
        if ip in uisp_ips:
            u = uisp_ips[ip]
            uisp_info = f" [UISP: '{u['name']}' status:{u['status']}]"
        elif mac in uisp_macs:
            u = uisp_macs[mac]
            uisp_info = f" [UISP by MAC: '{u['name']}' IP:{u['ip']} status:{u['status']}]"
        else:
            uisp_info = " [NOT in UISP]"
        print(f"  IP: {ip:15s} | MAC: {s.get('caller-id','?')}{uisp_info}")
        cp_count += 1
print(f"\nTotal: {cp_count}")
print()

# === Summary ===
print("=" * 70)
print("=== SUMMARY ===")
print("=" * 70)
ppp_client_ips = {ip for ip in ppp_ips if ip.startswith("10.10.")}
ppp_client_macs = {s.get("caller-id", "").upper() for s in sessions if s.get("address", "").startswith("10.10.")}
uisp_client_ips = {ip for ip, info in uisp_ips.items() if ip.startswith("10.10.")}
uisp_active_client_ips = {ip for ip, info in uisp_ips.items() if ip.startswith("10.10.") and info["status"] == "active"}
uisp_client_macs = {mac for mac, info in uisp_macs.items() if info["ip"].startswith("10.10.")}

# Count by MAC match (more reliable than IP since PPPoE IPs are dynamic)
matched_macs = ppp_client_macs & set(uisp_macs.keys())
ppp_only_macs = ppp_client_macs - set(uisp_macs.keys())
uisp_only_macs = uisp_client_macs - ppp_client_macs

print(f"PPP active sessions (10.10.x.x):     {len(ppp_client_ips)}")
print(f"UISP devices (10.10.x.x):            {len(uisp_client_ips)}")
print(f"UISP active devices (10.10.x.x):     {len(uisp_active_client_ips)}")
print()
print(f"--- By IP ---")
print(f"In both (by IP):                      {len(ppp_client_ips & uisp_client_ips)}")
print(f"In PPP only (not in UISP by IP):      {len(ppp_client_ips - uisp_client_ips)}")
print(f"In UISP active only (not in PPP):     {len(uisp_active_client_ips - ppp_client_ips)}")
print()
print(f"--- By MAC (more reliable) ---")
print(f"Matched by MAC:                       {len(matched_macs)}")
print(f"PPP MACs not in UISP:                 {len(ppp_only_macs)}")
print(f"UISP client MACs not in PPP:          {len(uisp_only_macs)}")
