#!/usr/bin/env python3
"""
Servidor de Aviso de Suspensión para Clientes Morosos
Redirige las solicitudes HTTP de clientes suspendidos a una página de aviso
"""

import http.server
import socketserver
import json
import os
from pathlib import Path

PORT = 80  # Puerto HTTP estándar
SUSPENSION_FILE = "/tmp/suspended_clients.txt"  # Lista de IPs suspendidas

class SuspensionPageHandler(http.server.BaseHTTPRequestHandler):
    """Maneja las solicitudes HTTP y muestra el aviso de suspensión"""

    def do_GET(self):
        """Maneja solicitudes GET"""

        # Si es una solicitud de verificación de estado
        if self.path == '/api/check-status':
            client_ip = self.client_address[0]

            # Verificar si el cliente está suspendido
            if self.is_suspended(client_ip):
                self.send_response(403)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'suspended'}).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'status': 'active'}).encode())
            return

        # Servir la página de suspensión para cualquier otra solicitud
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()

        try:
            with open('/tmp/suspension_page.html', 'r', encoding='utf-8') as f:
                page_content = f.read()
            self.wfile.write(page_content.encode('utf-8'))
        except FileNotFoundError:
            # Si no encuentra la página, mostrar una simple
            simple_page = self.get_simple_suspension_page()
            self.wfile.write(simple_page.encode('utf-8'))

    def do_POST(self):
        """Maneja solicitudes POST"""
        if self.path == '/api/check-status':
            self.do_GET()
        else:
            self.send_response(405)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'Method not allowed')

    def do_HEAD(self):
        """Maneja HEAD requests"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()

    def log_message(self, format, *args):
        """Registra los accesos"""
        client_ip = self.client_address[0]
        log_msg = f"[{self.log_date_time_string()}] {client_ip} - {format % args}"
        print(log_msg)

    @staticmethod
    def is_suspended(client_ip):
        """Verifica si una IP está suspendida"""
        try:
            if os.path.exists(SUSPENSION_FILE):
                with open(SUSPENSION_FILE, 'r') as f:
                    suspended_ips = f.read().strip().split('\n')
                    return client_ip in suspended_ips
        except Exception as e:
            print(f"Error checking suspension status: {e}")
        return False

    @staticmethod
    def get_simple_suspension_page():
        """Retorna una página HTML simple si la personalizada no existe"""
        return """
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Servicio Suspendido</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background: #f0f0f0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                }
                .container {
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 0 20px rgba(0,0,0,0.1);
                    max-width: 500px;
                    text-align: center;
                }
                h1 { color: #d63031; }
                p { color: #666; line-height: 1.6; }
                .contact {
                    background: #f9f9f9;
                    padding: 20px;
                    border-radius: 5px;
                    margin: 20px 0;
                }
                .phone {
                    font-size: 24px;
                    color: #d63031;
                    font-weight: bold;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>⚠️ Servicio Suspendido</h1>
                <p>Tu conexión ha sido suspendida por falta de pago.</p>
                <div class="contact">
                    <p><strong>Contactanos:</strong></p>
                    <p class="phone">+56 2 3655 099</p>
                    <p><small>Lunes a Viernes: 9:00 - 18:00</small></p>
                </div>
                <p>Deposita en tu cuenta y reporta tu pago para restaurar el servicio.</p>
            </div>
        </body>
        </html>
        """


def main():
    """Inicia el servidor"""
    Handler = SuspensionPageHandler

    with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
        print(f"\n{'='*60}")
        print("Servidor de Suspensión Iniciado")
        print(f"{'='*60}")
        print(f"Escuchando en puerto {PORT}")
        print(f"Redireccionando clientes morosos a aviso de suspensión")
        print(f"Archivo de clientes suspendidos: {SUSPENSION_FILE}")
        print(f"{'='*60}\n")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServidor detenido por el usuario")


if __name__ == "__main__":
    main()
