import subprocess
import os
import signal
import time
import psutil

# Kill existing Python server processes
print("Deteniendo servidores Python...")
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['name'] in ['python.exe', 'python3.exe']:
            cmdline = proc.info['cmdline']
            if cmdline and 'server_jwt.py' in ' '.join(cmdline):
                print(f"  Matando proceso {proc.info['pid']}")
                proc.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

time.sleep(2)

# Start server
print("Iniciando servidor...")
os.chdir(r'C:\claude\Yesswera')
subprocess.Popen(['python3', 'server_jwt.py', '3000', '--no-ssl'])

print("Servidor iniciado. Esperando 3 segundos...")
time.sleep(3)

# Test endpoint
print("\nProbando endpoint...")
exec(open(r'C:\claude\test_active_orders.py').read())
