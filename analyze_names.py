"""Cross-reference NMS endpoint names with CRM subscriber names."""
import urllib.request, json, ssl, subprocess

ctx = ssl._create_unverified_context()

# CRM Clients
crm_token = "ViDGlWlbrRuV2j0itNL0Mvt4LOcmRTRCoLyQffMaIiaIc6eF"
req = urllib.request.Request(
    "https://server.auralink.link/crm/api/v1.0/clients?direction=ASC&limit=500",
    headers={"X-Auth-App-Key": crm_token},
)
crm_clients = json.loads(urllib.request.urlopen(req, context=ctx).read())
crm_by_id = {}
for c in crm_clients:
    cid = str(c.get("id", ""))
    fn = c.get("firstName", "") or ""
    ln = c.get("lastName", "") or ""
    cn = c.get("companyName", "") or ""
    name = (fn + " " + ln).strip() or cn
    crm_by_id[cid] = name

# NMS Sites
nms_token = subprocess.check_output(
    ["docker", "exec", "unms-postgres", "psql", "-U", "postgres", "-d", "unms",
     "-t", "-A", "-c", "SELECT token FROM unms.token LIMIT 1;"]
).decode().strip()
req2 = urllib.request.Request(
    "https://server.auralink.link/nms/api/v2.1/sites",
    headers={"x-auth-token": nms_token},
)
sites = json.loads(urllib.request.urlopen(req2, context=ctx).read())

# Build pairs: endpoint name <-> CRM client name
pairs = []
for s in sites:
    ident = s.get("identification", {}) or {}
    if ident.get("type") != "endpoint":
        continue
    ep_name = ident.get("name", "")
    ucrm = s.get("ucrm", {}) or {}
    client = ucrm.get("client", {}) or {}
    cid = str(client.get("id", ""))
    crm_name = crm_by_id.get(cid, "")
    pairs.append((ep_name, crm_name, cid))


def normalize(s):
    return s.lower().strip().replace("  ", " ")


def words_overlap(a, b):
    wa = set(normalize(a).split())
    wb = set(normalize(b).split())
    if not wa or not wb:
        return 0.0
    common = wa & wb
    return len(common) / max(len(wa), len(wb))


perfect = []
partial = []
mismatch = []
no_crm = []

for ep_name, crm_name, cid in pairs:
    if not crm_name:
        no_crm.append((ep_name, cid))
        continue

    en = normalize(ep_name)
    cn = normalize(crm_name)

    if en == cn:
        perfect.append((ep_name, crm_name, cid))
    elif words_overlap(ep_name, crm_name) > 0:
        partial.append((ep_name, crm_name, cid))
    else:
        if en in cn or cn in en:
            partial.append((ep_name, crm_name, cid))
        else:
            en_words = en.split()
            cn_words = cn.split()
            any_match = False
            for ew in en_words:
                if len(ew) < 3:
                    continue
                for cw in cn_words:
                    if len(cw) < 3:
                        continue
                    if ew in cw or cw in ew:
                        any_match = True
                        break
                if any_match:
                    break
            if any_match:
                partial.append((ep_name, crm_name, cid))
            else:
                mismatch.append((ep_name, crm_name, cid))

total_linked = len(pairs) - len(no_crm)
print("Total endpoints con CRM: {}".format(total_linked))
print("Nombre identico: {}".format(len(perfect)))
print("Nombre parcial/similar: {}".format(len(partial)))
print("Nombre NO coincide: {}".format(len(mismatch)))
print("Sin CRM: {}".format(len(no_crm)))

sep = "=" * 80
dash = "-" * 80

print("\n" + sep)
print("NOMBRES QUE NO COINCIDEN ({} casos)".format(len(mismatch)))
print(sep)
header = "{:<8} {:<40} {:<40}".format("CRM ID", "Antena (NMS)", "Suscriptor (CRM)")
print(header)
print(dash)
for ep, crm, cid in sorted(mismatch, key=lambda x: int(x[2]) if x[2].isdigit() else 0):
    line = "#{:<7} {:<40} {:<40}".format(cid, ep[:39], crm[:39])
    print(line)

print("\n" + sep)
print("NOMBRES PARCIALMENTE SIMILARES ({} casos)".format(len(partial)))
print(sep)
print(header)
print(dash)
for ep, crm, cid in sorted(partial, key=lambda x: int(x[2]) if x[2].isdigit() else 0):
    line = "#{:<7} {:<40} {:<40}".format(cid, ep[:39], crm[:39])
    print(line)

if no_crm:
    print("\n" + sep)
    print("ENDPOINTS SIN CRM ({})".format(len(no_crm)))
    print(sep)
    for ep, cid in no_crm:
        print("  - {}".format(ep))

print("\n" + sep)
print("NOMBRES IDENTICOS ({} casos) - Todo OK".format(len(perfect)))
print(sep)
for ep, crm, cid in sorted(perfect, key=lambda x: int(x[2]) if x[2].isdigit() else 0):
    line = "#{:<7} {}".format(cid, ep)
    print(line)
