#!/usr/bin/env python3
"""UISP Cleanup Analysis - runs on VPS with pre-fetched JSON files."""
import json
from difflib import SequenceMatcher

# Load data
with open('/tmp/crm_svc.json') as f:
    services = json.load(f)
with open('/tmp/crm_clients.json') as f:
    clients = json.load(f)
with open('/tmp/nms_sites.json') as f:
    sites = json.load(f)
with open('/tmp/nms_devices.json') as f:
    devices = json.load(f)

print("=" * 70)
print("UISP CLEANUP ANALYSIS REPORT")
print("=" * 70)

# --- TASK 2: IP Conflicts ---
print("\n" + "=" * 70)
print("TASK 2: IP CONFLICTS IN NMS DEVICES")
print("=" * 70)
ip_devices = {}
for d in devices:
    ip = (d.get('ipAddress') or '').strip()
    if not ip:
        continue
    name = d.get('identification', {}).get('name', '') or '(no name)'
    mac = d.get('identification', {}).get('mac', '') or ''
    status = d.get('overview', {}).get('status', '') or ''
    model = d.get('identification', {}).get('model', '') or ''
    dev_id = d.get('identification', {}).get('id', '')
    site = d.get('identification', {}).get('site') or {}
    site_name = site.get('name', '') or ''
    ip_devices.setdefault(ip, []).append({
        'name': name, 'mac': mac, 'status': status, 'model': model, 'id': dev_id, 'site': site_name
    })

conflicts = {ip: devs for ip, devs in ip_devices.items() if len(devs) > 1}
print(f"Total devices: {len(devices)}")
print(f"Devices with IPs: {sum(len(v) for v in ip_devices.values())}")
print(f"Unique IPs: {len(ip_devices)}")
print(f"IP conflicts: {len(conflicts)}")
for ip, devs in sorted(conflicts.items()):
    print(f"\n  CONFLICT: {ip} ({len(devs)} devices)")
    for d in devs:
        print(f"    {d['name']} | MAC: {d['mac']} | {d['model']} | {d['status']} | Site: {d['site']}")

# --- TASK 3: Unlinked CRM services ---
print("\n" + "=" * 70)
print("TASK 3: CRM SERVICES WITHOUT NMS ENDPOINT LINK")
print("=" * 70)
status_map = {0: 'prepared', 1: 'active', 2: 'prepared', 3: 'suspended', 4: 'ended', 5: 'quoted', 6: 'obsolete'}
client_map = {}
for c in clients:
    cid = c.get('id')
    fname = (c.get('firstName') or '').strip()
    lname = (c.get('lastName') or '').strip()
    company = (c.get('companyName') or '').strip()
    name = (fname + ' ' + lname).strip() or company or 'Client#' + str(cid)
    client_map[cid] = name

unlinked = [s for s in services if not s.get('unmsClientSiteId')]
linked = [s for s in services if s.get('unmsClientSiteId')]
print(f"Total CRM services: {len(services)}")
print(f"Linked to NMS: {len(linked)}")
print(f"NOT linked to NMS: {len(unlinked)}")
for s in sorted(unlinked, key=lambda x: (x.get('status', 99), client_map.get(x.get('clientId', 0), ''))):
    st = status_map.get(s.get('status', 99), 'unk')
    plan = s.get('servicePlanName', '') or '(no plan)'
    cid = s.get('clientId', 0)
    cname = client_map.get(cid, '?')
    sid = s.get('id', 0)
    print(f"  [{st:>10}] Service #{sid:>3} | Client #{cid:>3} {cname} | {plan}")

# --- TASK 4: Duplicate CRM clients ---
print("\n" + "=" * 70)
print("TASK 4: POTENTIAL DUPLICATE CRM CLIENTS")
print("=" * 70)
client_names = []
for c in clients:
    cid = c.get('id')
    fname = (c.get('firstName') or '').strip()
    lname = (c.get('lastName') or '').strip()
    company = (c.get('companyName') or '').strip()
    full_name = (fname + ' ' + lname).strip() or company or 'Client#' + str(cid)
    client_names.append({'id': cid, 'name': full_name, 'firstName': fname, 'lastName': lname})

print(f"Total CRM clients: {len(client_names)}")
found = []
for i in range(len(client_names)):
    for j in range(i + 1, len(client_names)):
        a = client_names[i]
        b = client_names[j]
        na = a['name'].lower()
        nb = b['name'].lower()
        if len(na) < 3 or len(nb) < 3:
            continue
        ratio = SequenceMatcher(None, na, nb).ratio()
        if ratio >= 0.75:
            found.append((ratio, a, b))

found.sort(key=lambda x: -x[0])
if found:
    print(f"Potential duplicates (>= 75% name similarity): {len(found)}")
    for ratio, a, b in found:
        print(f"  {ratio:.0%} | Client #{a['id']:>3} \"{a['name']}\" <-> Client #{b['id']:>3} \"{b['name']}\"")
else:
    print("No potential duplicates found.")

# --- TASK 5: Orphan NMS sites ---
print("\n" + "=" * 70)
print("TASK 5: ORPHAN NMS SITES (NO DEVICES ASSIGNED)")
print("=" * 70)
sites_with_devices = set()
for d in devices:
    site = d.get('identification', {}).get('site')
    if site:
        sid = site.get('id', '')
        if sid:
            sites_with_devices.add(sid)

orphans = []
for s in sites:
    sid = s.get('identification', {}).get('id', '')
    sname = s.get('identification', {}).get('name', '') or '(unnamed)'
    stype = s.get('identification', {}).get('type', '') or ''
    status = s.get('identification', {}).get('status', '') or ''
    parent = s.get('identification', {}).get('parent') or {}
    parent_name = parent.get('name', '') or ''
    if sid not in sites_with_devices:
        orphans.append({
            'id': sid, 'name': sname, 'type': stype, 'status': status, 'parent': parent_name
        })

print(f"Total NMS sites: {len(sites)}")
print(f"Sites with at least 1 device: {len(sites_with_devices)}")
print(f"Orphan sites (0 devices): {len(orphans)}")
for o in sorted(orphans, key=lambda x: (x['type'], x['name'])):
    par = f" (parent: {o['parent']})" if o['parent'] else ''
    print(f"  [{o['type']:>12}] {o['name']}{par} | Status: {o['status']}")

# --- Summary ---
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Devices after phantom cleanup: {len(devices)}")
print(f"IP conflicts: {len(conflicts)}")
print(f"CRM services unlinked: {len(unlinked)}")
print(f"Potential duplicate clients: {len(found)}")
print(f"Orphan NMS sites: {len(orphans)}")
