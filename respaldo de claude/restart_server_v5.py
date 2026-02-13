#!/usr/bin/env python3
import subprocess
import time

SERVER_IP = "192.168.100.3"
SERVER_USER = "yesswera"
SERVER_PASS = "1234"

def run_remote_cmd(cmd):
    """Ejecutar comando remoto con SSH"""
    ssh_process = subprocess.Popen(
        f'ssh -o PubkeyAuthentication=no -o StrictHostKeyChecking=no {SERVER_USER}@{SERVER_IP}',
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8'
    )
    stdout, stderr = ssh_process.communicate(input=SERVER_PASS + "\n" + cmd + "\nexit\n", timeout=30)
    return stdout, stderr

print("Deteniendo servidor v4...")
run_remote_cmd("pkill -9 -f 'server_jwt.py'")
time.sleep(2)

print("Iniciando servidor v5 con WebSockets...")
run_remote_cmd("""
cd /home/yesswera/YessweraWeb
nohup python3 server_enhanced_v5_websockets.py > /tmp/yesswera_v5.log 2>&1 &
sleep 3
""")

print("\nVerificando estado...")
stdout, stderr = run_remote_cmd("ps aux | grep -E 'server_enhanced_v5|server_jwt' | grep -v grep")
print(stdout)

if "server_enhanced_v5" in stdout:
    print("\n✅ Servidor v5 está corriendo correctamente")
else:
    print("\n❌ Servidor v5 no está corriendo")
    print("Viendo logs...")
    stdout, stderr = run_remote_cmd("tail -20 /tmp/yesswera_v5.log")
    print(stdout)

