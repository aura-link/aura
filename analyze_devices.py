import json

with open('C:/claude2/uisp_devices.json') as f:
    devices = json.load(f)

print(f'Total devices from API: {len(devices)}')
print()

def get(d, *keys, default='unknown'):
    val = d
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            return default
    return val if val is not None else default

print('='*80)
print('FULL DEVICE BREAKDOWN BY MODEL / FIRMWARE / STATUS')
print('='*80)
models = {}
for d in devices:
    model = get(d, 'identification', 'model')
    model_name = get(d, 'identification', 'modelName')
    fw = get(d, 'identification', 'firmwareVersion')
    status = get(d, 'overview', 'status')
    key = (model, model_name, fw, status)
    models[key] = models.get(key, 0) + 1

for (model, model_name, fw, status), count in sorted(models.items(), key=lambda x: -x[1]):
    print(f'  {count:>3}x  {model:<16} ({model_name:<22})  fw={fw:<20} {status}')

print()
print('='*80)
print('LITEBEAM M5 DEVICES (model=LB5)')
print('='*80)
lb5_devices = [d for d in devices if get(d, 'identification', 'model') == 'LB5']
print(f'Total LiteBeam M5 (LB5): {len(lb5_devices)}')
print()

lb5_fw = {}
for d in lb5_devices:
    fw = get(d, 'identification', 'firmwareVersion')
    status = get(d, 'overview', 'status')
    key = (fw, status)
    lb5_fw[key] = lb5_fw.get(key, 0) + 1

print('  Firmware / Status breakdown:')
for (fw, status), count in sorted(lb5_fw.items(), key=lambda x: -x[1]):
    print(f'    {count:>3}x  fw={fw:<20} status={status}')

active = sum(1 for d in lb5_devices if get(d, 'overview', 'status') == 'active')
disconnected = sum(1 for d in lb5_devices if get(d, 'overview', 'status') == 'disconnected')
unknown_s = sum(1 for d in lb5_devices if get(d, 'overview', 'status') == 'unknown')
unauth = sum(1 for d in lb5_devices if get(d, 'overview', 'status') == 'unauthorized')
print(f'\n  Active:        {active}')
print(f'  Disconnected:  {disconnected}')
print(f'  Unknown:       {unknown_s}')
print(f'  Unauthorized:  {unauth}')

print()
print('='*80)
print('LITEBEAM 5AC Gen2 DEVICES (model=LBE-5AC-Gen2)')
print('='*80)
lbe5ac = [d for d in devices if get(d, 'identification', 'model') == 'LBE-5AC-Gen2']
print(f'Total LiteBeam 5AC Gen2: {len(lbe5ac)}')
lbe_fw = {}
for d in lbe5ac:
    fw = get(d, 'identification', 'firmwareVersion')
    status = get(d, 'overview', 'status')
    key = (fw, status)
    lbe_fw[key] = lbe_fw.get(key, 0) + 1
for (fw, status), count in sorted(lbe_fw.items(), key=lambda x: -x[1]):
    print(f'    {count:>3}x  fw={fw:<20} status={status}')

active_lbe = sum(1 for d in lbe5ac if get(d, 'overview', 'status') == 'active')
disconnected_lbe = sum(1 for d in lbe5ac if get(d, 'overview', 'status') == 'disconnected')
print(f'\n  Active:        {active_lbe}')
print(f'  Disconnected:  {disconnected_lbe}')

print()
print('='*80)
print('ALL MODELS SUMMARY')
print('='*80)
all_models = {}
for d in devices:
    model = get(d, 'identification', 'model')
    model_name = get(d, 'identification', 'modelName')
    all_models[(model, model_name)] = all_models.get((model, model_name), 0) + 1

for (model, model_name), count in sorted(all_models.items(), key=lambda x: -x[1]):
    print(f'    {count:>3}x  {model:<16} ({model_name})')

print()
print('='*80)
print('AIRMAX DEVICES (identification.type)')
print('='*80)
type_count = {}
for d in devices:
    t = get(d, 'identification', 'type')
    type_count[t] = type_count.get(t, 0) + 1
for t, count in sorted(type_count.items(), key=lambda x: -x[1]):
    print(f'  {count:>3}x  type={t}')

airmax = [d for d in devices if get(d, 'identification', 'type') == 'airMax']
print(f'\nTotal airMax: {len(airmax)}')

non_airmax = [d for d in devices if get(d, 'identification', 'type') != 'airMax']
if non_airmax:
    print(f'Non-airMax: {len(non_airmax)}')
    for d in non_airmax:
        name = get(d, 'identification', 'name')
        model = get(d, 'identification', 'model')
        dtype = get(d, 'identification', 'type')
        status = get(d, 'overview', 'status')
        print(f'  - {name} | model={model} | type={dtype} | {status}')

print()
print('='*80)
print('FIRMWARE VERSION SUMMARY (all devices)')
print('='*80)
fw_count = {}
for d in devices:
    fw = get(d, 'identification', 'firmwareVersion')
    fw_count[fw] = fw_count.get(fw, 0) + 1
for fw, count in sorted(fw_count.items(), key=lambda x: -x[1]):
    print(f'  {count:>3}x  {fw}')

print()
print('='*80)
print('PLATFORM BREAKDOWN')
print('='*80)
platforms = {}
for d in devices:
    p = get(d, 'identification', 'platformId')
    platforms[p] = platforms.get(p, 0) + 1
for p, count in sorted(platforms.items(), key=lambda x: -x[1]):
    print(f'  {count:>3}x  platform={p}')

print()
print('='*80)
print('GRAND SUMMARY')
print('='*80)
total_active = sum(1 for d in devices if get(d, 'overview', 'status') == 'active')
total_disc = sum(1 for d in devices if get(d, 'overview', 'status') == 'disconnected')
total_unk = sum(1 for d in devices if get(d, 'overview', 'status') == 'unknown')
total_unauth = sum(1 for d in devices if get(d, 'overview', 'status') == 'unauthorized')
print(f'  Total devices in UISP:  {len(devices)}')
print(f'  Total airMax:           {len(airmax)}')
print(f'  Active:                 {total_active}')
print(f'  Disconnected:           {total_disc}')
print(f'  Unknown:                {total_unk}')
print(f'  Unauthorized:           {total_unauth}')
print(f'  ---')
print(f'  LiteBeam M5 (LB5):     {len(lb5_devices):>3}  ({active} active, {disconnected} disconnected, {unknown_s} unknown, {unauth} unauthorized)')
print(f'  LiteBeam 5AC Gen2:     {len(lbe5ac):>3}  ({active_lbe} active, {disconnected_lbe} disconnected)')
print(f'  All LiteBeam variants: {len(lb5_devices) + len(lbe5ac):>3}')
