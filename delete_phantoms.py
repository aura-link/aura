import urllib.request, ssl, subprocess, json

ctx = ssl._create_unverified_context()
nms_token = subprocess.check_output(
    ["docker", "exec", "unms-postgres", "psql", "-U", "postgres", "-d", "unms",
     "-t", "-A", "-c", "SELECT token FROM unms.token LIMIT 1;"]
).decode().strip()

ids = """12c823a0-834b-4e84-92e3-66c1179c2cad
a52a2efa-5a64-4040-8f5f-733df79c5353
5b005d99-9ebe-4c81-bf2d-87baf48c4be1
34ecb982-2b36-4626-9c71-c9ecedb0ea05
1fc43225-9455-4d5a-8482-c92c322d0ee1
12aeca0f-2322-469f-afae-0a2bdf46fde6
0e901629-8151-4d6b-8bdb-dcdb85fb3bb0
40622989-1e93-41cc-ac6f-5f5ef2ea6983
6502feba-c111-4096-a829-d9173c925ea8
7af03714-121d-4adf-8f0c-41d0e2658381
f7e757e4-