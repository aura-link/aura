#!/usr/bin/env python3
"""
Gestor de Suspensiones de Clientes
Maneja la lista de IPs suspendidas y configura MikroTik para mostrar el aviso
"""

import subprocess
import sys
import os
from pathlib import Path

# Configuración
ROUTER_IP = "10.147.17.11"
ROUTER_USER = "admin"
SUSPENDED_FILE = "/tmp/suspended_clients.txt"
LOCAL_SUSPENDED_FILE = "C:\\claude\\suspended_clients.txt"

def ssh_command(cmd):
    """Ejecuta un comando SSH en el router MikroTik"""
    try:
        result = subprocess.run(
            [
                'ssh',
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'PubkeyAuthentication=no',
                f'{ROUTER_USER}@{ROUTER_IP}',
                cmd
            ],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "Timeout", -1
    except Exception as e:
        return str(e), -1

def add_suspended_client(client_ip):
    """Agrega un cliente a la lista de suspendidos"""
    print(f"Agregando cliente suspendido: {client_ip}")

    # Leer archivo actual
    suspended_ips = set()
    if os.path.exists(LOCAL_SUSPENDED_FILE):
        with open(LOCAL_SUSPENDED_FILE, 'r') as f:
            suspended_ips = set(line.strip() for line in f if line.strip())

    # Agregar nuevo IP
    suspended_ips.add(client_ip)

    # Escribir archivo
    with open(LOCAL_SUSPENDED_FILE, 'w') as f:
        for ip in sorted(suspended_ips):
            f.write(f"{ip}\n")

    print(f"  Cliente {client_ip} agregado a suspensión")
    print(f"  Total de clientes suspendidos: {len(suspended_ips)}")

def remove_suspended_client(client_ip):
    """Remueve un cliente de la lista de suspendidos"""
    print(f"Removiendo cliente suspendido: {client_ip}")

    if not os.path.exists(LOCAL_SUSPENDED_FILE):
        print(f"  Archivo de suspensiones no encontrado")
        return

    # Leer archivo actual
    with open(LOCAL_SUSPENDED_FILE, 'r') as f:
        suspended_ips = set(line.strip() for line in f if line.strip())

    # Remover IP
    if client_ip in suspended_ips:
        suspended_ips.remove(client_ip)

        # Escribir archivo
        with open(LOCAL_SUSPENDED_FILE, 'w') as f:
            for ip in sorted(suspended_ips):
                f.write(f"{ip}\n")

        print(f"  Cliente {client_ip} removido de suspensión")
        print(f"  Total de clientes suspendidos: {len(suspended_ips)}")
    else:
        print(f"  Cliente {client_ip} no estaba en la lista de suspendidos")

def list_suspended_clients():
    """Lista todos los clientes suspendidos"""
    if not os.path.exists(LOCAL_SUSPENDED_FILE):
        print("No hay clientes suspendidos")
        return

    with open(LOCAL_SUSPENDED_FILE, 'r') as f:
        lines = f.readlines()

    print(f"Clientes suspendidos ({len(lines)}):")
    print("-" * 50)
    for i, line in enumerate(lines, 1):
        print(f"  {i}. {line.strip()}")
    print("-" * 50)

def configure_mikrotik_redirect(port=80):
    """Configura NAT en MikroTik para redirigir HTTP al servidor de suspensión"""
    print(f"Configurando MikroTik para redirigir HTTP al servidor de suspensión...")
    print(f"Puerto: {port}")

    # Obtener IP local (gateway MikroTik)
    # Esto debería ser tu IP local del servidor
    local_ip = "192.168.100.3"  # Cambiar según tu setup

    # Crear regla NAT en MikroTik
    # Esta regla redirige puertos HTTP (80) al servidor de suspensión
    nat_rule = f"""
    /ip firewall nat add chain=dstnat protocol=tcp dst-port={port} \
    action=redirect to-ports={port} comment="Aviso de Suspensión"
    """

    print("\nPara aplicar en MikroTik, ejecuta:")
    print(nat_rule)

    # También podemos usar IP específico si tenemos un servidor local
    print("\nAlternativa con IP específico:")
    print(f"""
    /ip firewall nat add chain=dstnat protocol=tcp dst-port={port} \\
    to-addresses={local_ip} to-ports={port} comment="Aviso de Suspensión"
    """)

def deploy_to_server():
    """Despliega los archivos al servidor"""
    print("Desplegando archivos de suspensión al servidor...")

    # Archivos a desplegar
    files_to_deploy = [
        ('C:\\claude\\suspension_page.html', '/home/yesswera/suspension/suspension_page.html'),
        ('C:\\claude\\suspension_server.py', '/home/yesswera/suspension/suspension_server.py'),
        ('C:\\claude\\suspended_clients.txt', '/home/yesswera/suspension/suspended_clients.txt'),
    ]

    print("\nArchivos a desplegar:")
    for local, remote in files_to_deploy:
        if os.path.exists(local):
            print(f"  ✓ {local}")
        else:
            print(f"  ✗ {local} (no encontrado)")

def show_help():
    """Muestra la ayuda"""
    help_text = """
    Gestor de Suspensiones de Clientes

    Uso: python manage_suspension.py [comando] [argumentos]

    Comandos:
      add <IP>          - Agregar un cliente a la lista de suspendidos
      remove <IP>       - Remover un cliente de la lista de suspendidos
      list              - Listar todos los clientes suspendidos
      configure         - Mostrar configuración necesaria en MikroTik
      deploy            - Desplegar archivos al servidor
      help              - Mostrar esta ayuda

    Ejemplos:
      python manage_suspension.py add 192.168.1.100
      python manage_suspension.py remove 192.168.1.100
      python manage_suspension.py list
      python manage_suspension.py configure
      python manage_suspension.py deploy
    """
    print(help_text)

def main():
    """Función principal"""
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    if command == 'add' and len(sys.argv) >= 3:
        add_suspended_client(sys.argv[2])
    elif command == 'remove' and len(sys.argv) >= 3:
        remove_suspended_client(sys.argv[2])
    elif command == 'list':
        list_suspended_clients()
    elif command == 'configure':
        configure_mikrotik_redirect()
    elif command == 'deploy':
        deploy_to_server()
    elif command in ['help', '-h', '--help']:
        show_help()
    else:
        print(f"Comando no reconocido: {command}")
        print("Usa 'help' para ver los comandos disponibles")

if __name__ == "__main__":
    main()
