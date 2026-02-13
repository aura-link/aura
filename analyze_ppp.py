import re

ubnt_prefixes = {'24:5A:4C', '28:70:4E', '60:22:32', '9C:05:D6', '0C:EA:14',
                 'E4:38:83', '70:A7:41', '44:D9:E7', '74:83:C2', '04:18:D6',
                 'AC:84:C6', '78:8A:20', 'B4:FB:E4', '68:72:51'}

ubnt = []
other = []
other_prefixes = {}

with open('C:/claude2/ppp_raw.txt') as f:
    for line in f:
        m_mac = re.search(r'caller-id=([0-9A-Fa-f:]+)', line)
        m_ip = re.search(r'address=([0-9.]+)', line)
        m_name = re.search(r'name=(\S+)', line)
        if not m_mac or not m_ip: continue

        mac = m_mac.group(1).upper()
        ip = m_ip.group(1)
        name = m_name.group(1) if m_name else '?'
        prefix = mac[:8]

        if prefix in {p.upper() for p in ubnt_prefixes}:
            ubnt.append((name, ip, mac))
        else:
            other.append((name, ip, mac))
            other_prefixes[prefix] = other_prefixes.get(prefix, 0) + 1

print(f'PPP con MAC Ubiquiti: {len(ubnt)}')
print(f'PPP con MAC NO-Ubiquiti: {len(other)}')
print()
if other_prefixes:
    print('Fabricantes no-Ubiquiti:')
    for p, c in sorted(other_prefixes.items(), key=lambda x: -x[1]):
        print(f'  {p}: {c} dispositivos')
    print()
    print('Listado no-Ubiquiti:')
    for n, i, m in other:
        print(f'  {n:35s} {i:15s} {m}')
