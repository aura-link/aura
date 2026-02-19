#!/usr/bin/env python3
import json, re
from pathlib import Path

PPP_FILE = Path("C:/claude2/ppp_active_now.txt")
UISP_FILE = Path("C:/claude2/uisp_stations_now.json")

def parse_pppoe(filepath):
    sessions = []
    current = {}
    text = filepath.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^\d+\s+", line):
            if current:
                sessions.append(current)
            current = {}
        for m in re.finditer(r'(\w[\w-]*)="([^"]*)"', line):
            current[m.group(1)] = m.group(2)
        for m in re.finditer(r'(\w[\w-]*)=([^\s"]+)', line):
            if m.group(1) not in current:
                current[m.group(1)] = m.group(2)
    if current:
        sessions.append(current)
    return sessions

def parse_uisp(filepath):
    raw = json.loads(filepath.read_text(encoding="utf-8"))
    devices = []
    for d in raw:
        ident = d.get("identification", {})
        ov = d.get("overview", {})
        ip = d.get("ipAddress", "")
        if ip and "/" in ip:
            ip = ip.split("/")[0]
        devices.append({
            "name": ident.get("name") or ident.get("hostname") or "",
            "ip": ip,
            "mac": ident.get("mac", "").upper(),
            "status": ov.get("status", "unknown"),
            "model": ident.get("model", ""),
        })
    return devices

def nmac(mac):
    return mac.upper().replace("-", ":").strip()

def main():
    S = "=" * 95
    D = "-"
    print(S)
    print("CROSS-REFERENCE: PPPoE Active Sessions vs UISP Device Status")
    print(S)

    ppp_all = parse_pppoe(PPP_FILE)
    uisp_all = parse_uisp(UISP_FILE)

    ppp_clients = [s for s in ppp_all if s.get("address","").startswith("10.10.1.")]
    ppp_real = [s for s in ppp_clients if s.get("name","") != "clienteprueba"]
    ppp_prueba = [s for s in ppp_clients if s.get("name","") == "clienteprueba"]

    print()
    print(f"PPPoE total active sessions: {len(ppp_all)}")
    print(f"PPPoE client sessions (10.10.1.x): {len(ppp_clients)}")
    print(f"  - Real clients: {len(ppp_real)}")
    print(f"  - clienteprueba: {len(ppp_prueba)}")
    print(f"UISP station devices: {len(uisp_all)}")

    uisp_by_ip = {d["ip"]: d for d in uisp_all if d["ip"]}
    uisp_by_mac = {nmac(d["mac"]): d for d in uisp_all if d["mac"]}

    disconnected = []
    no_uisp = []
    active = []

    for s in ppp_real:
        ip = s.get("address","")
        mac = nmac(s.get("caller-id",""))
        name = s.get("name","")
        um = uisp_by_ip.get(ip)
        mb = "IP"
        if not um and mac:
            um = uisp_by_mac.get(mac)
            mb = "MAC"
        if um:
            st = um["status"]
            entry = {"ppp_name":name, "ip":ip, "ppp_mac":mac, "uisp_name":um["name"],
                     "uisp_status":st, "uisp_mac":um["mac"], "uisp_model":um["model"], "matched_by":mb}
            if st == "active":
                active.append(entry)
            else:
                disconnected.append(entry)
        else:
            no_uisp.append({"ppp_name":name, "ip":ip, "ppp_mac":mac})

    prueba_details = []
    for s in ppp_prueba:
        ip = s.get("address","")
        mac = nmac(s.get("caller-id",""))
        um = uisp_by_ip.get(ip) or (uisp_by_mac.get(mac) if mac else None)
        prueba_details.append({
            "ip":ip, "mac":mac,
            "uisp_name": um["name"] if um else "NOT IN UISP",
            "uisp_status": um["status"] if um else "-",
        })

    print()
    print(S)
    print("SUMMARY")
    print(S)
    print(f"  PPPoE active + UISP active (healthy):       {len(active)}")
    print(f"  PPPoE active + UISP DISCONNECTED/UNKNOWN:    {len(disconnected)}")
    print(f"  PPPoE active + NO UISP device at all:        {len(no_uisp)}")
    print(f"  clienteprueba sessions:                       {len(ppp_prueba)}")

    if disconnected:
        print()
        print(S)
        h = f"PPPoE ACTIVE but UISP DISCONNECTED/UNKNOWN ({len(disconnected)} devices)"
        print(h)
        print("These antennas have internet working but are not reporting to UISP")
        print(S)
        print(f"{'PPPoE Name':<28} {'IP':<14} {'PPPoE MAC':<19} {'UISP Name':<28} {'Status':<12} {'Match'}")
        print(f"{D*28} {D*14} {D*19} {D*28} {D*12} {D*5}")
        for d in sorted(disconnected, key=lambda x: x["uisp_status"]):
            print(f"{d['ppp_name']:<28} {d['ip']:<14} {d['ppp_mac']:<19} {d['uisp_name']:<28} {d['uisp_status']:<12} {d['matched_by']}")

    if no_uisp:
        print()
        print(S)
        h = f"PPPoE ACTIVE but NO MATCHING UISP DEVICE ({len(no_uisp)} sessions)"
        print(h)
        print("These antennas are connected via PPPoE but have no UISP entry (by IP or MAC)")
        print(S)
        print(f"{'PPPoE Name':<35} {'IP':<16} {'MAC'}")
        print(f"{D*35} {D*16} {D*19}")
        for d in sorted(no_uisp, key=lambda x: x["ip"]):
            print(f"{d['ppp_name']:<35} {d['ip']:<16} {d['ppp_mac']}")

    if prueba_details:
        print()
        print(S)
        h = f"CLIENTEPRUEBA Sessions ({len(prueba_details)} active)"
        print(h)
        print(S)
        print(f"{'IP':<16} {'MAC':<19} {'UISP Name':<30} {'UISP Status'}")
        print(f"{D*16} {D*19} {D*30} {D*12}")
        for d in prueba_details:
            print(f"{d['ip']:<16} {d['mac']:<19} {d['uisp_name']:<30} {d['uisp_status']}")

    ppp_ips = {s.get("address","") for s in ppp_all}
    ppp_macs = {nmac(s.get("caller-id","")) for s in ppp_all}
    truly_offline = []
    for d in uisp_all:
        if d["status"] != "active":
            if d["ip"] not in ppp_ips and (not d["mac"] or nmac(d["mac"]) not in ppp_macs):
                truly_offline.append(d)

    if truly_offline:
        print()
        print(S)
        h = f"UISP DISCONNECTED with NO active PPPoE ({len(truly_offline)} devices)"
        print(h)
        print("These devices are offline in UISP AND have no PPPoE session (truly offline)")
        print(S)
        print(f"{'UISP Name':<35} {'IP':<16} {'MAC':<19} {'Status':<12} {'Model'}")
        print(f"{D*35} {D*16} {D*19} {D*12} {D*20}")
        for d in sorted(truly_offline, key=lambda x: x["status"]):
            ipd = d["ip"] or "N/A"
            print(f"{d['name']:<35} {ipd:<16} {d['mac']:<19} {d['status']:<12} {d['model']}")

    print()
    print(S)
    print("DONE")
    print(S)

if __name__ == "__main__":
    main()
