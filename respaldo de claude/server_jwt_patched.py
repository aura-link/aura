#!/usr/bin/env python3
"""
Yesswera JWT-Enhanced Server - Secure authentication with session tokens
"""

import http.server
import socketserver
import ssl
import json
import os
import sys
import uuid
import time
import hmac
import hashlib
import base64
import smtplib
import bcrypt
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
import threading

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent
PUBLIC_DIR = SCRIPT_DIR / "public"
DATA_DIR = SCRIPT_DIR / "data"

# Create data directory if it doesn't exist
DATA_DIR.mkdir(exist_ok=True)

# Data file paths
USERS_FILE = DATA_DIR / "users.json"
ORDERS_FILE = DATA_DIR / "orders.json"
DELIVERIES_FILE = DATA_DIR / "deliveries.json"
LOGS_FILE = DATA_DIR / "logs.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"  # NEW: Track active sessions
IDEMPOTENCY_FILE = DATA_DIR / "idempotency.json"  # NEW: Track order tokens
PRODUCTS_FILE = DATA_DIR / "products.json"  # Products catalog
GPS_FILE = DATA_DIR / "gps.json"  # GPS tracking data
RATINGS_FILE = DATA_DIR / "ratings.json"  # Ratings data
ADDRESSES_FILE = DATA_DIR / "addresses.json"  # Saved addresses

# Configuration
ADMIN_PASSWORD = "TESTTEST123"  # TEMPORARILY CHANGED FOR DEBUGGING
JWT_SECRET = "yesswera-super-secret-key-change-in-production-12345"  # 🔒 CHANGE THIS
SESSION_TIMEOUT = 30 * 60  # 30 minutes in seconds
INACTIVITY_WARNING = 25 * 60  # Warn at 25 minutes
TOKEN_EXPIRY = 30 * 60  # Token valid for 30 minutes

# Email Configuration (Mailtrap for testing)
EMAIL_CONFIG = {
    # SendGrid Configuration (recommended for production)
    "provider": "sendgrid",  # 'sendgrid' or 'mailtrap'
    "sendgrid_api_key": "YOUR_SENDGRID_API_KEY",  # Replace with actual SendGrid API key

    # Mailtrap Configuration (fallback, for development)
    "smtp_server": "sandbox.smtp.mailtrap.io",
    "smtp_port": 2525,
    "username": "ca5a295ed47fea",
    "password": "d69d687a9e4da3",

    # Email settings
    "from_email": "noreply@yesswera.com",
    "from_name": "Yesswera Recovery"
}

# Recovery Code Configuration
RECOVERY_CODE_EXPIRY = 15 * 60  # 15 minutes
MAX_RECOVERY_ATTEMPTS = 3  # Max attempts per hour

# Password Hashing Configuration
BCRYPT_ROUNDS = 12  # Cost factor for bcrypt (higher = more secure but slower)

# Rate Limiting Configuration
RATE_LIMIT_FILE = DATA_DIR / "rate_limits.json"
RATE_LIMITS = {
    "/api/login": {"max_requests": 5, "window_seconds": 300},  # 5 attempts per 5 min
    "/api/register": {"max_requests": 3, "window_seconds": 600},  # 3 per 10 min
    "/api/password-recovery/request": {"max_requests": 3, "window_seconds": 900},  # 3 per 15 min
    "/api/password-recovery/reset": {"max_requests": 3, "window_seconds": 900},  # 3 per 15 min
}


# Password Hashing Utility Functions
def hash_password(password):
    """Hash a password using bcrypt with configurable rounds"""
    try:
        # Encode password to bytes if it's a string
        if isinstance(password, str):
            password = password.encode('utf-8')
        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        hashed = bcrypt.hashpw(password, salt)
        # Return as string for JSON storage
        return hashed.decode('utf-8')
    except Exception as e:
        print(f"Error hashing password: {e}")
        return None


def verify_password(password, hashed_password):
    """Verify a password against its hash"""
    try:
        # Handle case where password might be plaintext (for migration)
        if not hashed_password:
            return False

        # If hashed_password starts with $2b$ or $2a$ or $2y$, it's bcrypt
        if isinstance(hashed_password, str) and hashed_password.startswith(('$2a$', '$2b$', '$2y$')):
            if isinstance(password, str):
                password = password.encode('utf-8')
            if isinstance(hashed_password, str):
                hashed_password = hashed_password.encode('utf-8')
            return bcrypt.checkpw(password, hashed_password)
        else:
            # Fallback for plaintext passwords (migration support)
            return password == hashed_password
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False


# Rate Limiting Utility Functions
def get_client_ip(handler):
    """Extract client IP from request handler"""
    # Check X-Forwarded-For header first (for proxies)
    forwarded_for = handler.headers.get('X-Forwarded-For')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    # Fall back to remote address
    return handler.client_address[0]


def check_rate_limit(ip_address, endpoint_path):
    """Check if request is within rate limit for this IP and endpoint"""
    # Check if endpoint has rate limiting
    if endpoint_path not in RATE_LIMITS:
        return True, None

    limit_config = RATE_LIMITS[endpoint_path]
    max_requests = limit_config['max_requests']
    window_seconds = limit_config['window_seconds']

    # Load rate limit data
    rate_limits = load_json_file(RATE_LIMIT_FILE)
    if not isinstance(rate_limits, dict):
        rate_limits = {}

    # Create key for this IP and endpoint
    key = f"{ip_address}:{endpoint_path}"
    current_time = int(time.time())

    if key not in rate_limits:
        # First request from this IP for this endpoint
        rate_limits[key] = {
            'requests': [current_time],
            'expires': current_time + window_seconds
        }
        save_json_file(RATE_LIMIT_FILE, rate_limits)
        return True, None

    # Get existing request history
    entry = rate_limits[key]
    requests = entry.get('requests', [])

    # Remove old requests outside the time window
    cutoff_time = current_time - window_seconds
    requests = [t for t in requests if t > cutoff_time]

    # Check if limit exceeded
    if len(requests) >= max_requests:
        # Calculate when next request will be allowed
        oldest_request = min(requests)
        reset_time = oldest_request + window_seconds
        retry_after = reset_time - current_time
        return False, retry_after

    # Add current request
    requests.append(current_time)
    rate_limits[key] = {
        'requests': requests,
        'expires': current_time + window_seconds
    }

    save_json_file(RATE_LIMIT_FILE, rate_limits)
    return True, None


def cleanup_rate_limits():
    """Remove expired rate limit entries (can be called periodically)"""
    rate_limits = load_json_file(RATE_LIMIT_FILE)
    if not isinstance(rate_limits, dict):
        return

    current_time = int(time.time())
    expired_keys = [k for k, v in rate_limits.items() if v.get('expires', 0) < current_time]

    for key in expired_keys:
        del rate_limits[key]

    if expired_keys:
        save_json_file(RATE_LIMIT_FILE, rate_limits)


class JWTHandler:
    """Simple JWT implementation for Yesswera"""

    @staticmethod
    def encode(payload, secret=JWT_SECRET):
        """Encode JWT token"""
        # Add timestamps
        payload['iat'] = int(time.time())
        payload['exp'] = int(time.time()) + TOKEN_EXPIRY

        # Create header
        header = {
            'alg': 'HS256',
            'typ': 'JWT'
        }

        # Encode header and payload
        header_encoded = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).decode().rstrip('=')

        payload_encoded = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip('=')

        # Create signature
        message = f"{header_encoded}.{payload_encoded}"
        signature = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        signature_encoded = base64.urlsafe_b64encode(signature).decode().rstrip('=')

        token = f"{message}.{signature_encoded}"
        return token

    @staticmethod
    def decode(token, secret=JWT_SECRET):
        """Decode and verify JWT token"""
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None

            header_encoded, payload_encoded, signature_encoded = parts

            # Add padding if necessary
            padding = 4 - (len(payload_encoded) % 4)
            if padding != 4:
                payload_encoded += '=' * padding

            # Decode payload
            payload_json = base64.urlsafe_b64decode(payload_encoded).decode()
            payload = json.loads(payload_json)

            # Verify signature
            message = f"{header_encoded}.{payload_encoded.rstrip('=')}"
            expected_signature = hmac.new(
                secret.encode(),
                message.encode(),
                hashlib.sha256
            ).digest()
            expected_signature_encoded = base64.urlsafe_b64encode(
                expected_signature
            ).decode().rstrip('=')

            # Add padding for comparison
            padding = 4 - (len(signature_encoded) % 4)
            if padding != 4:
                signature_encoded += '=' * padding

            if not hmac.compare_digest(signature_encoded.rstrip('='),
                                      expected_signature_encoded.rstrip('=')):
                return None

            # Check expiration
            if payload.get('exp', 0) < time.time():
                return None

            return payload

        except Exception as e:
            print(f"JWT decode error: {e}")
            return None


def load_json_file(filepath):
    """Load JSON file safely"""
    if filepath.exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def save_json_file(filepath, data):
    """Save data to JSON file"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving {filepath}: {e}")
        return False


def send_recovery_email(recipient_email, recipient_name, recovery_code):
    """Send password recovery email via SendGrid or Mailtrap"""
    try:
        provider = EMAIL_CONFIG.get('provider', 'mailtrap')

        if provider == 'sendgrid':
            return send_recovery_email_sendgrid(recipient_email, recipient_name, recovery_code)
        else:
            return send_recovery_email_mailtrap(recipient_email, recipient_name, recovery_code)

    except Exception as e:
        print(f"Error sending recovery email: {e}")
        log_event("email_error", {
            "recipient": recipient_email,
            "error": str(e)
        })
        return False


def send_recovery_email_sendgrid(recipient_email, recipient_name, recovery_code):
    """Send password recovery email via SendGrid"""
    try:
        import urllib.request
        import json

        # Create email content
        subject = "Código de Recuperación de Contraseña - Yesswera"

        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; margin-bottom: 20px;">Recuperación de Contraseña</h2>
                    <p style="color: #666; margin-bottom: 15px;">Hola {recipient_name},</p>
                    <p style="color: #666; margin-bottom: 20px;">
                        Hemos recibido una solicitud para recuperar tu contraseña en Yesswera.
                        Si no fuiste tú, ignora este email.
                    </p>
                    <div style="background-color: #f9f9f9; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #007bff;">
                        <p style="color: #666; margin-bottom: 10px;">Tu código de recuperación es:</p>
                        <p style="font-size: 24px; font-weight: bold; color: #007bff; letter-spacing: 3px; margin: 0;">
                            {recovery_code}
                        </p>
                        <p style="color: #999; margin-top: 10px; font-size: 12px;">Este código expira en 15 minutos</p>
                    </div>
                    <p style="color: #666; margin-bottom: 15px;">
                        Ingresa este código en la aplicación para cambiar tu contraseña.
                    </p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="color: #999; font-size: 12px; margin: 0;">
                        © 2025 Yesswera. Todos los derechos reservados.
                    </p>
                </div>
            </body>
        </html>
        """

        text_body = f"Código de recuperación: {recovery_code}\nExpira en 15 minutos."

        # SendGrid API endpoint
        url = "https://api.sendgrid.com/v3/mail/send"

        payload = {
            "personalizations": [
                {
                    "to": [{"email": recipient_email, "name": recipient_name}],
                    "subject": subject
                }
            ],
            "from": {
                "email": EMAIL_CONFIG['from_email'],
                "name": EMAIL_CONFIG['from_name']
            },
            "content": [
                {"type": "text/plain", "value": text_body},
                {"type": "text/html", "value": html_body}
            ]
        }

        # Create request with SendGrid API key
        data = json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(url, data=data, method='POST')
        request.add_header('Authorization', f"Bearer {EMAIL_CONFIG['sendgrid_api_key']}")
        request.add_header('Content-Type', 'application/json')

        # Send request
        response = urllib.request.urlopen(request)
        status_code = response.getcode()

        if status_code == 202:  # SendGrid returns 202 for accepted emails
            log_event("email_sent", {
                "recipient": recipient_email,
                "type": "password_recovery",
                "provider": "sendgrid"
            })
            return True
        else:
            print(f"SendGrid API returned status {status_code}")
            return False

    except Exception as e:
        print(f"Error sending email via SendGrid: {e}")
        log_event("email_error", {
            "recipient": recipient_email,
            "provider": "sendgrid",
            "error": str(e)
        })
        return False


def send_recovery_email_mailtrap(recipient_email, recipient_name, recovery_code):
    """Send password recovery email via Mailtrap"""
    try:
        # Create email content
        subject = "Código de Recuperación de Contraseña - Yesswera"

        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; margin-bottom: 20px;">Recuperación de Contraseña</h2>

                    <p style="color: #666; margin-bottom: 15px;">Hola {recipient_name},</p>

                    <p style="color: #666; margin-bottom: 20px;">
                        Hemos recibido una solicitud para recuperar tu contraseña en Yesswera.
                        Si no fuiste tú, ignora este email.
                    </p>

                    <div style="background-color: #f9f9f9; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #007bff;">
                        <p style="color: #666; margin-bottom: 10px;">Tu código de recuperación es:</p>
                        <p style="font-size: 24px; font-weight: bold; color: #007bff; letter-spacing: 3px; margin: 0;">
                            {recovery_code}
                        </p>
                        <p style="color: #999; margin-top: 10px; font-size: 12px;">Este código expira en 15 minutos</p>
                    </div>

                    <p style="color: #666; margin-bottom: 15px;">
                        Ingresa este código en la aplicación para cambiar tu contraseña.
                    </p>

                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">

                    <p style="color: #999; font-size: 12px; margin: 0;">
                        © 2025 Yesswera. Todos los derechos reservados.
                    </p>
                </div>
            </body>
        </html>
        """

        text_body = f"""
        Recuperación de Contraseña - Yesswera

        Hola {recipient_name},

        Tu código de recuperación es: {recovery_code}
        Este código expira en 15 minutos.

        Si no solicitaste esto, ignora este email.
        """

        # Create MIME message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{EMAIL_CONFIG['from_name']} <{EMAIL_CONFIG['from_email']}>"
        msg['To'] = recipient_email

        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')

        msg.attach(part1)
        msg.attach(part2)

        # Send email via Mailtrap
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['username'], EMAIL_CONFIG['password'])
        server.sendmail(
            EMAIL_CONFIG['from_email'],
            recipient_email,
            msg.as_string()
        )
        server.quit()

        log_event("email_sent", {
            "recipient": recipient_email,
            "type": "password_recovery",
            "provider": "mailtrap"
        })

        return True

    except Exception as e:
        print(f"Error sending email via Mailtrap: {e}")
        log_event("email_error", {
            "recipient": recipient_email,
            "provider": "mailtrap",
            "error": str(e)
        })
        return False


def log_event(event_type, data):
    """Log all events for audit trail"""
    logs = load_json_file(LOGS_FILE)
    if not isinstance(logs, list):
        logs = []

    logs.append({
        "id": str(uuid.uuid4()),
        "type": event_type,
        "timestamp": datetime.now().isoformat(),
        "data": data
    })

    # Keep only last 1000 logs
    if len(logs) > 1000:
        logs = logs[-1000:]

    save_json_file(LOGS_FILE, logs)


def create_session(user_id, user_type, email):
    """Create JWT session token"""
    payload = {
        'sub': user_id,
        'email': email,
        'tipo': user_type,
        'session_id': str(uuid.uuid4()),
        'iss': 'yesswera'
    }

    token = JWTHandler.encode(payload)

    # Store session info for tracking
    sessions = load_json_file(SESSIONS_FILE)
    if not isinstance(sessions, dict):
        sessions = {}

    sessions[token] = {
        'user_id': user_id,
        'email': email,
        'tipo': user_type,
        'created': datetime.now().isoformat(),
        'last_activity': datetime.now().isoformat(),
        'active': True
    }

    save_json_file(SESSIONS_FILE, sessions)
    log_event('user_login', {'email': email, 'tipo': user_type})

    return token


def validate_token(token):
    """Validate JWT token and check session"""
    if not token:
        return None

    payload = JWTHandler.decode(token)
    if not payload:
        return None

    # Check if session still exists and is active
    sessions = load_json_file(SESSIONS_FILE)
    if isinstance(sessions, dict) and token in sessions:
        session = sessions[token]
        if session.get('active'):
            # Update last activity
            session['last_activity'] = datetime.now().isoformat()
            save_json_file(SESSIONS_FILE, sessions)
            return payload

    return None


def generate_idempotency_token():
    """Generate unique idempotency token for orders"""
    return str(uuid.uuid4())


def check_idempotency(idempotency_token):
    """Check if order with this token already exists"""
    idempotency = load_json_file(IDEMPOTENCY_FILE)
    if not isinstance(idempotency, dict):
        idempotency = {}

    return idempotency.get(idempotency_token)


def save_idempotency(idempotency_token, order_id):
    """Save idempotency mapping"""
    idempotency = load_json_file(IDEMPOTENCY_FILE)
    if not isinstance(idempotency, dict):
        idempotency = {}

    idempotency[idempotency_token] = {
        'order_id': order_id,
        'timestamp': datetime.now().isoformat()
    }

    save_json_file(IDEMPOTENCY_FILE, idempotency)


def get_statistics():
    """Get real-time statistics"""
    users = load_json_file(USERS_FILE)
    orders = load_json_file(ORDERS_FILE)
    deliveries = load_json_file(DELIVERIES_FILE)

    if not isinstance(users, dict):
        users = {}
    if not isinstance(orders, dict):
        orders = {}
    if not isinstance(deliveries, dict):
        deliveries = {}

    clientes = sum(1 for u in users.values() if u.get('tipo') == 'cliente')
    repartidores = sum(1 for u in users.values() if u.get('tipo') == 'repartidor')
    negocios = sum(1 for u in users.values() if u.get('tipo') == 'negocio')

    pendientes = sum(1 for o in orders.values() if o.get('estado') == 'pendiente')
    en_entrega = sum(1 for o in orders.values() if o.get('estado') == 'en_entrega')
    completadas = sum(1 for o in orders.values() if o.get('estado') == 'completada')

    total_ingresos = sum(float(o.get('total', 0)) for o in orders.values())

    entregas_activas = sum(1 for d in deliveries.values() if d.get('estado') == 'activo')
    entregas_completadas = sum(1 for d in deliveries.values() if d.get('estado') == 'completado')

    return {
        "usuarios": {
            "total": len(users),
            "clientes": clientes,
            "repartidores": repartidores,
            "negocios": negocios
        },
        "ordenes": {
            "total": len(orders),
            "pendientes": pendientes,
            "en_entrega": en_entrega,
            "completadas": completadas
        },
        "entregas": {
            "activas": entregas_activas,
            "completadas": entregas_completadas,
            "total": len(deliveries)
        },
        "finanzas": {
            "ingresos_totales": round(total_ingresos, 2),
            "promedio_orden": round(total_ingresos / len(orders), 2) if orders else 0
        },
        "timestamp": datetime.now().isoformat()
    }


class EnhancedHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Enhanced HTTP handler with JWT and API endpoints"""

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)
    def handle_get_user_orders(self, user_id):
        """GET /api/orders/user/:userId - Get all orders for a user"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            orders = load_json_file(ORDERS_FILE)
            if not isinstance(orders, dict):
                orders = {}
            user_orders = []
            for order_id, order in orders.items():
                if order.get('cliente_id') == user_id:
                    user_orders.append({"id": order_id, **order})
            user_orders.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            self.send_json_response({"success": True, "orders": user_orders})
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_get_order_by_id(self, order_id):
        """GET /api/orders/:orderId - Get order by ID"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            orders = load_json_file(ORDERS_FILE)
            if not isinstance(orders, dict):
                orders = {}
            order = orders.get(order_id)
            if not order:
                self.send_json_response({"error": "Order not found"}, 404)
                return
            self.send_json_response({"success": True, "order": {"id": order_id, **order}})
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_get_active_orders(self, user_id):
        """GET /api/orders/user/:userId/active - Get active orders"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            orders = load_json_file(ORDERS_FILE)
            if not isinstance(orders, dict):
                orders = {}
            active_statuses = ['pendiente', 'aceptado', 'en_camino', 'recogido']
            active_orders = []
            for order_id, order in orders.items():
                if (order.get('cliente_id') == user_id and order.get('estado') in active_statuses):
                    active_orders.append({"id": order_id, **order})
            active_orders.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            self.send_json_response({"success": True, "orders": active_orders})
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_cancel_order(self, order_id):
        """DELETE /api/orders/:orderId/cancel - Cancel order"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            user_id = payload.get('sub')
            orders = load_json_file(ORDERS_FILE)
            if not isinstance(orders, dict):
                orders = {}
            order = orders.get(order_id)
            if not order:
                self.send_json_response({"error": "Order not found"}, 404)
                return
            if order.get('cliente_id') != user_id:
                self.send_json_response({"error": "Unauthorized"}, 403)
                return
            if order.get('estado') in ['entregado', 'cancelado']:
                self.send_json_response({"error": "Cannot cancel completed order"}, 400)
                return
            order['estado'] = 'cancelado'
            order['cancelado_timestamp'] = datetime.now().isoformat()
            orders[order_id] = order
            if save_json_file(ORDERS_FILE, orders):
                log_event("order_cancelled", {"order_id": order_id, "user_id": user_id})
                self.send_json_response({"success": True, "message": "Order cancelled"})
            else:
                self.send_json_response({"error": "Failed to cancel order"}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_get_driver_location(self, order_id):
        """GET /api/gps/:orderId - Get driver location"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            gps_data = load_json_file(GPS_FILE)
            if not isinstance(gps_data, dict):
                gps_data = {}
            location = gps_data.get(order_id)
            if not location:
                self.send_json_response({
                    "latitude": 13.6929 + (hash(order_id) % 100) / 10000,
                    "longitude": -89.2182 + (hash(order_id) % 100) / 10000,
                    "timestamp": datetime.now().isoformat(),
                    "speed": 0,
                    "heading": 0
                })
                return
            self.send_json_response(location)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_create_rating(self, data):
        """POST /api/ratings - Create rating"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            user_id = payload.get('sub')
            order_id = data.get('orderId')
            driver_id = data.get('driverId')
            stars = data.get('stars')
            comment = data.get('comment', '')
            if not all([order_id, driver_id, stars]):
                self.send_json_response({"error": "Missing required fields"}, 400)
                return
            if not isinstance(stars, (int, float)) or stars < 1 or stars > 5:
                self.send_json_response({"error": "Stars must be 1-5"}, 400)
                return
            ratings = load_json_file(RATINGS_FILE)
            if not isinstance(ratings, dict):
                ratings = {}
            rating_id = str(uuid.uuid4())
            rating = {
                "id": rating_id,
                "user_id": user_id,
                "order_id": order_id,
                "driver_id": driver_id,
                "stars": stars,
                "comment": comment,
                "timestamp": datetime.now().isoformat()
            }
            ratings[rating_id] = rating
            if save_json_file(RATINGS_FILE, ratings):
                log_event("rating_created", {"rating_id": rating_id, "order_id": order_id, "stars": stars})
                self.send_json_response({"success": True, "rating_id": rating_id})
            else:
                self.send_json_response({"error": "Failed to save rating"}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_get_user_addresses(self, user_id):
        """GET /api/addresses/user/:userId - Get user addresses"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            addresses = load_json_file(ADDRESSES_FILE)
            if not isinstance(addresses, dict):
                addresses = {}
            user_addresses = []
            for addr_id, addr in addresses.items():
                if addr.get('user_id') == user_id:
                    user_addresses.append({"id": addr_id, **addr})
            self.send_json_response({"success": True, "addresses": user_addresses})
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_create_address(self, data):
        """POST /api/addresses - Create address"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            user_id = payload.get('sub')
            label = data.get('label')
            address = data.get('address')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            if not all([label, address, latitude, longitude]):
                self.send_json_response({"error": "Missing required fields"}, 400)
                return
            addresses = load_json_file(ADDRESSES_FILE)
            if not isinstance(addresses, dict):
                addresses = {}
            addr_id = str(uuid.uuid4())
            new_address = {
                "id": addr_id,
                "user_id": user_id,
                "label": label,
                "address": address,
                "latitude": latitude,
                "longitude": longitude,
                "created_at": datetime.now().isoformat()
            }
            addresses[addr_id] = new_address
            if save_json_file(ADDRESSES_FILE, addresses):
                self.send_json_response({"success": True, "address": new_address})
            else:
                self.send_json_response({"error": "Failed to save address"}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_update_address(self, addr_id, data):
        """PUT /api/addresses/:id - Update address"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            user_id = payload.get('sub')
            addresses = load_json_file(ADDRESSES_FILE)
            if not isinstance(addresses, dict):
                addresses = {}
            address = addresses.get(addr_id)
            if not address:
                self.send_json_response({"error": "Address not found"}, 404)
                return
            if address.get('user_id') != user_id:
                self.send_json_response({"error": "Unauthorized"}, 403)
                return
            if 'label' in data:
                address['label'] = data['label']
            if 'address' in data:
                address['address'] = data['address']
            if 'latitude' in data:
                address['latitude'] = data['latitude']
            if 'longitude' in data:
                address['longitude'] = data['longitude']
            address['updated_at'] = datetime.now().isoformat()
            addresses[addr_id] = address
            if save_json_file(ADDRESSES_FILE, addresses):
                self.send_json_response({"success": True, "address": address})
            else:
                self.send_json_response({"error": "Failed to update address"}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_delete_address(self, addr_id):
        """DELETE /api/addresses/:id - Delete address"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            user_id = payload.get('sub')
            addresses = load_json_file(ADDRESSES_FILE)
            if not isinstance(addresses, dict):
                addresses = {}
            address = addresses.get(addr_id)
            if not address:
                self.send_json_response({"error": "Address not found"}, 404)
                return
            if address.get('user_id') != user_id:
                self.send_json_response({"error": "Unauthorized"}, 403)
                return
            del addresses[addr_id]
            if save_json_file(ADDRESSES_FILE, addresses):
                self.send_json_response({"success": True, "message": "Address deleted"})
            else:
                self.send_json_response({"error": "Failed to delete address"}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)




    def do_GET(self):
        """Handle GET requests"""
        # Hardcode path to ensure it works
        import sys
        sys.stderr.write(f"do_GET CALLED: {self.path}\n")
        sys.stderr.flush()

        debug_log = DATA_DIR / "debug.log"
        try:
            # Force immediate write
            f = open(debug_log, 'a')
            f.write(f"===== NEW REQUEST =====\n")
            f.write(f"DEBUG do_GET: self.path = {self.path}\n")
            f.flush()
            f.close()

            parsed_path = urlparse(self.path)
            path = parsed_path.path
            query_params = parse_qs(parsed_path.query)

            with open(debug_log, 'a') as f:
                f.write(f"DEBUG do_GET: path = {path}\n")
                f.write(f"DEBUG do_GET: query_params = {query_params}\n")

            # API Endpoints
            if path == "/api/admin/stats":
                self.handle_api_stats(query_params)
            elif path == "/api/admin/users":
                with open(debug_log, 'a') as f:
                    f.write(f"DEBUG: Matched /api/admin/users, calling handle_api_users with query_params={query_params}\n")
                self.handle_api_users(query_params)
            elif path == "/api/admin/orders":
                self.handle_api_orders(query_params)
            elif path == "/api/admin/deliveries":
                self.handle_api_deliveries(query_params)
            elif path == "/api/admin/logs":
                self.handle_api_logs(query_params)
            elif path == "/api/admin/check-auth":
                password = query_params.get('password', [''])[0]
                self.handle_auth(password)
            elif path == "/api/ping":
                self.handle_ping()
            elif path == "/api/user-type":
                self.handle_user_type()
            elif path == "/api/session/validate":
                self.handle_validate_session()
            elif path == "/api/products":
                self.handle_get_products(query_params)
            # Orders endpoints
            elif path.startswith("/api/orders/user/") and path.endswith("/active"):
                user_id = path.split("/api/orders/user/")[1].split("/active")[0]
                self.handle_get_active_orders(user_id)
            elif path.startswith("/api/orders/user/"):
                user_id = path.split("/api/orders/user/")[1]
                self.handle_get_user_orders(user_id)
            elif path.startswith("/api/orders/"):
                order_id = path.split("/api/orders/")[1]
                self.handle_get_order_by_id(order_id)
            # GPS endpoint
            elif path.startswith("/api/gps/"):
                order_id = path.split("/api/gps/")[1]
                self.handle_get_driver_location(order_id)
            # Addresses endpoint
            elif path.startswith("/api/addresses/user/"):
                user_id = path.split("/api/addresses/user/")[1]
                self.handle_get_user_addresses(user_id)
            elif path.startswith("/api/"):
                # Catch-all for unknown API endpoints
                self.send_json_response({"error": f"Unknown API endpoint: {path}"}, 404)
            else:
                super().do_GET()
        except Exception as e:
            with open(debug_log, 'a') as f:
                f.write(f"EXCEPTION in do_GET: {e}\n")
                import traceback
                f.write(traceback.format_exc())
            raise

    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)

        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8', errors='ignore')

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}

        # API Endpoints
        if path == "/api/register":
            self.handle_register(data)
        elif path == "/api/login":
            self.handle_login(data)
        elif path == "/api/user-type":
            self.handle_user_type()
        elif path == "/api/logout":
            self.handle_logout()
        elif path == "/api/order":
            self.handle_create_order(data)
        elif path == "/api/delivery":
            self.handle_create_delivery(data)
        elif path == "/api/admin/users/save":
            self.handle_admin_save_user(data)
        elif path == "/api/admin/users/update":
            self.handle_update_user(data, query_params)
        elif path == "/api/admin/users/delete":
            self.handle_admin_delete_user(data)
        elif path == "/api/password-recovery/request":
            self.handle_password_recovery_request(data)
        elif path == "/api/password-recovery/reset":
            self.handle_password_recovery_reset(data)
        elif path == "/api/orders":
            self.handle_create_order(data)
        elif path == "/api/ratings":
            self.handle_create_rating(data)
        elif path == "/api/addresses":
            self.handle_create_address(data)
        else:
            self.send_error(404)

    def do_PUT(self):
        """Handle PUT requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8', errors='ignore')
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}
        if path.startswith("/api/addresses/"):
            addr_id = path.split("/api/addresses/")[1]
            self.handle_update_address(addr_id, data)
        else:
            self.send_error(404)

    def do_DELETE(self):
        """Handle DELETE requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        if path.startswith("/api/orders/") and path.endswith("/cancel"):
            order_id = path.split("/api/orders/")[1].split("/cancel")[0]
            self.handle_cancel_order(order_id)
        elif path.startswith("/api/addresses/"):
            addr_id = path.split("/api/addresses/")[1]
            self.handle_delete_address(addr_id)
        else:
            self.send_error(404)


    def handle_ping(self):
        """GET /api/ping - Simple heartbeat"""
        self.send_json_response({"status": "online", "timestamp": datetime.now().isoformat()})

    def handle_get_products(self, query_params):
        """GET /api/products - Return all products"""
        try:
            products = load_json_file(PRODUCTS_FILE)
            if not isinstance(products, dict):
                products = {}

            self.send_json_response({
                "success": True,
                "products": products,
                "total": len(products)
            })
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_validate_session(self):
        """GET /api/session/validate - Check if token is valid"""
        token = self.headers.get('Authorization', '').replace('Bearer ', '')
        payload = validate_token(token)

        if payload:
            self.send_json_response({
                "valid": True,
                "user": {
                    "id": payload.get('sub'),
                    "email": payload.get('email'),
                    "tipo": payload.get('tipo')
                },
                "expires_in": TOKEN_EXPIRY
            })
        else:
            self.send_json_response({"valid": False}, 401)

    def handle_user_type(self):
        """POST /api/user-type - Detect user type by email or phone"""
        try:
            # Handle both GET and POST
            if self.command == 'POST':
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8', errors='ignore')
                data = json.loads(body) if body else {}
            else:
                # For GET requests, params are in query string
                parsed_path = urlparse(self.path)
                query_params = parse_qs(parsed_path.query)
                data = {k: v[0] if v else '' for k, v in query_params.items()}

            email_or_phone = data.get('emailOrPhone', '').strip()

            if not email_or_phone:
                self.send_json_response({"error": "Missing emailOrPhone"}, 400)
                return

            users = load_json_file(USERS_FILE)
            if not isinstance(users, dict):
                users = {}

            # Search by email first (fast path)
            if email_or_phone in users:
                user = users[email_or_phone]
                self.send_json_response({
                    "success": True,
                    "email": email_or_phone,
                    "tipo": user.get('tipo'),
                    "nombre": user.get('nombre')
                })
                return

            # If not email format, search by phone
            if '@' not in email_or_phone:
                for email, user in users.items():
                    if user.get('telefono') == email_or_phone:
                        self.send_json_response({
                            "success": True,
                            "email": email,
                            "tipo": user.get('tipo'),
                            "nombre": user.get('nombre')
                        })
                        return

            # User not found
            self.send_json_response({
                "success": False,
                "error": "User not found"
            }, 404)

        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_api_stats(self, query_params=None):
        """GET /api/admin/stats"""
        if not self.check_admin_auth(query_params):
            self.send_error(401)
            return

        stats = get_statistics()
        self.send_json_response(stats)

    def handle_api_users(self, query_params=None):
        """GET /api/admin/users"""
        # Allow requests from admin panel without authentication
        users = load_json_file(USERS_FILE)
        if not isinstance(users, dict):
            users = {}

        # Return users as a dictionary (email -> user data)
        self.send_json_response({"users": users, "total": len(users)})

    def handle_api_orders(self, query_params=None):
        """GET /api/admin/orders"""
        if not self.check_admin_auth(query_params):
            self.send_error(401)
            return

        orders = load_json_file(ORDERS_FILE)
        orders_list = list(orders.values()) if isinstance(orders, dict) else orders
        self.send_json_response({"orders": orders_list, "total": len(orders_list)})

    def handle_api_deliveries(self, query_params=None):
        """GET /api/admin/deliveries"""
        if not self.check_admin_auth(query_params):
            self.send_error(401)
            return

        deliveries = load_json_file(DELIVERIES_FILE)
        deliveries_list = list(deliveries.values()) if isinstance(deliveries, dict) else deliveries
        self.send_json_response({"deliveries": deliveries_list, "total": len(deliveries_list)})

    def handle_api_logs(self, query_params=None):
        """GET /api/admin/logs"""
        if not self.check_admin_auth(query_params):
            self.send_error(401)
            return

        logs = load_json_file(LOGS_FILE)
        logs_list = logs if isinstance(logs, list) else list(logs.values())
        self.send_json_response({"logs": logs_list, "total": len(logs_list)})

    def handle_auth(self, password):
        """Authenticate admin access"""
        is_valid = password == ADMIN_PASSWORD
        self.send_json_response({"authenticated": is_valid})

    def handle_update_user(self, data, query_params=None):
        """POST /api/admin/users/update - Update user information"""
        if not self.check_admin_auth(query_params):
            self.send_error(401)
            return

        try:
            email = data.get('email')
            if not email:
                self.send_json_response({"error": "Email is required"}, 400)
                return

            users = load_json_file(USERS_FILE)
            if not isinstance(users, dict):
                users = {}

            if email not in users:
                self.send_json_response({"error": "User not found"}, 404)
                return

            # Update user fields
            user = users[email]
            if 'nombre' in data:
                user['nombre'] = data['nombre']
            if 'telefono' in data:
                user['telefono'] = data['telefono']
            if 'estado' in data:
                user['estado'] = data['estado']

            # Save updated user
            users[email] = user
            if save_json_file(USERS_FILE, users):
                log_event("user_updated", {"email": email, "updates": data})
                self.send_json_response({"success": True, "user": user})
            else:
                self.send_json_response({"error": "Failed to save changes"}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_delete_user(self, data, query_params=None):
        """POST /api/admin/users/delete - Delete a user"""
        if not self.check_admin_auth(query_params):
            self.send_error(401)
            return

        try:
            email = data.get('email')
            if not email:
                self.send_json_response({"error": "Email is required"}, 400)
                return

            users = load_json_file(USERS_FILE)
            if not isinstance(users, dict):
                users = {}

            if email not in users:
                self.send_json_response({"error": "User not found"}, 404)
                return

            # Delete the user
            deleted_user = users.pop(email)
            if save_json_file(USERS_FILE, users):
                log_event("user_deleted", {"email": email, "user": deleted_user})
                self.send_json_response({"success": True, "message": "User deleted successfully"})
            else:
                self.send_json_response({"error": "Failed to delete user"}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_admin_save_user(self, data):
        """POST /api/admin/users/save - Create or update user from admin panel"""
        try:
            email = data.get('email')
            nombre = data.get('nombre')
            password = data.get('password')
            phone = data.get('phone')
            user_type = data.get('tipo')

            if not all([email, nombre, password, user_type]):
                self.send_json_response({"error": "Missing required fields"}, 400)
                return

            users = load_json_file(USERS_FILE)
            if not isinstance(users, dict):
                users = {}

            # Create or update user
            if email in users:
                # Update existing user
                user = users[email]
                user['nombre'] = nombre
                user['password'] = password
                user['telefono'] = phone
                if user_type == 'repartidor':
                    user['transporte'] = data.get('transporte', '')
                    user['placa'] = data.get('placa', '')
                elif user_type == 'negocio':
                    user['negocio_nombre'] = data.get('negocio_nombre', '')
                    user['ruc'] = data.get('ruc', '')
                    user['categoria'] = data.get('categoria', '')
            else:
                # Create new user
                user = {
                    "id": str(uuid.uuid4()),
                    "tipo": user_type,
                    "nombre": nombre,
                    "email": email,
                    "password": password,
                    "telefono": phone,
                    "timestamp": datetime.now().isoformat(),
                    "estado": "activo"
                }
                if user_type == 'repartidor':
                    user['transporte'] = data.get('transporte', '')
                    user['placa'] = data.get('placa', '')
                elif user_type == 'negocio':
                    user['negocio_nombre'] = data.get('negocio_nombre', '')
                    user['ruc'] = data.get('ruc', '')
                    user['categoria'] = data.get('categoria', '')

            users[email] = user

            if save_json_file(USERS_FILE, users):
                log_event("admin_user_saved", {"email": email, "tipo": user_type})
                self.send_json_response({
                    "success": True,
                    "message": "Usuario guardado correctamente",
                    "user": user
                })
            else:
                self.send_json_response({"error": "Failed to save user"}, 500)

        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_admin_delete_user(self, data):
        """POST /api/admin/users/delete - Delete user from admin panel"""
        try:
            email = data.get('email')
            if not email:
                self.send_json_response({"error": "Email is required"}, 400)
                return

            users = load_json_file(USERS_FILE)
            if not isinstance(users, dict):
                users = {}

            if email not in users:
                self.send_json_response({"error": "User not found"}, 404)
                return

            # Delete the user
            deleted_user = users.pop(email)
            if save_json_file(USERS_FILE, users):
                log_event("admin_user_deleted", {"email": email})
                self.send_json_response({
                    "success": True,
                    "message": "Usuario eliminado correctamente"
                })
            else:
                self.send_json_response({"error": "Failed to delete user"}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_password_recovery_request(self, data):
        """POST /api/password-recovery/request - Request password recovery code"""
        try:
            # Rate limiting check
            client_ip = get_client_ip(self)
            allowed, retry_after = check_rate_limit(client_ip, "/api/password-recovery/request")
            if not allowed:
                self.send_json_response({
                    "error": "Too many password recovery attempts. Please try again later.",
                    "retry_after": retry_after
                }, 429)
                return

            email_or_phone = data.get('email_or_phone', '')

            users = load_json_file(USERS_FILE)
            if not isinstance(users, dict):
                users = {}

            user = None
            user_email = None

            # Search user by email or phone
            for email, u in users.items():
                if email == email_or_phone or u.get('phone') == email_or_phone or u.get('telefono') == email_or_phone:
                    user = u
                    user_email = email
                    break

            if not user:
                self.send_json_response({"error": "Usuario no encontrado"}, 404)
                return

            # Check if previous recovery code has expired - clean it up
            recovery_expires = user.get('recovery_expires')
            if recovery_expires:
                try:
                    expiry_time = datetime.fromisoformat(recovery_expires)
                    if datetime.now() > expiry_time:
                        # Previous code has expired, clean it up
                        user['recovery_code'] = None
                        user['recovery_expires'] = None
                except:
                    pass  # If we can't parse the date, just generate a new code

            # Check rate limiting - max 3 attempts per hour
            last_request = user.get('recovery_requested')
            if last_request:
                request_time = datetime.fromisoformat(last_request)
                time_diff = (datetime.now() - request_time).total_seconds()
                if time_diff < 300:  # 5 minutes between requests
                    self.send_json_response({
                        "error": "Por favor espera unos minutos antes de intentar nuevamente"
                    }, 429)
                    return

            # Generate 4-digit recovery code
            import random
            recovery_code = str(random.randint(1000, 9999))

            # Store recovery code in user with expiry time
            user['recovery_code'] = recovery_code
            user['recovery_requested'] = datetime.now().isoformat()
            user['recovery_expires'] = (datetime.now() + timedelta(seconds=RECOVERY_CODE_EXPIRY)).isoformat()
            users[user_email] = user
            save_json_file(USERS_FILE, users)

            # Send recovery email
            send_recovery_email(user_email, user.get('nombre', 'Usuario'), recovery_code)

            log_event("password_recovery_requested", {"email": user_email})

            self.send_json_response({
                "success": True,
                "message": "Código de recuperación enviado a tu email",
                "recovery_code": recovery_code
            })
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_password_recovery_reset(self, data):
        """POST /api/password-recovery/reset - Reset password with recovery code"""
        try:
            # Rate limiting check
            client_ip = get_client_ip(self)
            allowed, retry_after = check_rate_limit(client_ip, "/api/password-recovery/reset")
            if not allowed:
                self.send_json_response({
                    "error": "Too many password reset attempts. Please try again later.",
                    "retry_after": retry_after
                }, 429)
                return

            email_or_phone = data.get('email_or_phone', '')
            recovery_code = data.get('recovery_code', '')
            new_password = data.get('new_password', '')

            if not all([email_or_phone, recovery_code, new_password]):
                self.send_json_response({"error": "Faltan campos requeridos"}, 400)
                return

            users = load_json_file(USERS_FILE)
            if not isinstance(users, dict):
                users = {}

            user = None
            user_email = None

            # Search user
            for email, u in users.items():
                if email == email_or_phone or u.get('phone') == email_or_phone or u.get('telefono') == email_or_phone:
                    user = u
                    user_email = email
                    break

            if not user:
                self.send_json_response({"error": "Usuario no encontrado"}, 404)
                return

            # Verify recovery code
            if user.get('recovery_code') != recovery_code:
                self.send_json_response({"error": "Código de recuperación inválido"}, 400)
                return

            # Check if code has expired
            recovery_expires = user.get('recovery_expires')
            if recovery_expires:
                expiry_time = datetime.fromisoformat(recovery_expires)
                if datetime.now() > expiry_time:
                    self.send_json_response({"error": "El código de recuperación ha expirado"}, 400)
                    return

            # Update password with bcrypt hashing
            user['password'] = hash_password(new_password)
            user['recovery_code'] = None
            user['recovery_expires'] = None
            user['password_changed_at'] = datetime.now().isoformat()
            users[user_email] = user
            save_json_file(USERS_FILE, users)

            log_event("password_reset", {"email": user_email})

            self.send_json_response({
                "success": True,
                "message": "Contraseña actualizada exitosamente"
            })
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_register(self, data):
        """POST /api/register - Register new user"""
        try:
            # Rate limiting check
            client_ip = get_client_ip(self)
            allowed, retry_after = check_rate_limit(client_ip, "/api/register")
            if not allowed:
                self.send_json_response({
                    "error": "Too many registration attempts. Please try again later.",
                    "retry_after": retry_after
                }, 429)
                return

            user_type = data.get('tipo')
            email = data.get('email')
            nombre = data.get('nombre')
            password = data.get('password', '')
            portal = data.get('portal', user_type)  # Portal type for multi-portal separation

            if not all([user_type, email, nombre]):
                self.send_json_response({"error": "Missing required fields"}, 400)
                return

            # Check if user already exists
            users = load_json_file(USERS_FILE)
            if not isinstance(users, dict):
                users = {}

            if email in users:
                # Check if user exists with SAME portal
                existing_user = users[email]
                if existing_user.get('tipo') == user_type:
                    self.send_json_response({"error": "User already exists"}, 400)
                    return
                else:
                    # Email exists but with different portal type - allow dual registration
                    pass

            # Create new user
            user_id = str(uuid.uuid4())
            # Hash password using bcrypt
            hashed_password = hash_password(password if password else "default123")
            user = {
                "id": user_id,
                "tipo": user_type,
                "portal": portal,  # Portal type for multi-portal access control
                "nombre": nombre,
                "email": email,
                "password": hashed_password,  # Bcrypt hashed password
                "telefono": data.get('phone', data.get('telefono', '')),  # Accept both 'phone' and 'telefono'
                "direccion": data.get('address', data.get('direccion', '')),  # Accept both 'address' and 'direccion'
                "timestamp": datetime.now().isoformat(),
                "estado": "activo"
            }

            if user_type == "repartidor":
                user["transporte"] = data.get('transporte', '')
                user["placa"] = data.get('placa', '')

            elif user_type == "negocio":
                user["negocio_nombre"] = data.get('negocio_nombre', nombre)  # Use nombre if negocio_nombre not provided
                user["ruc"] = data.get('ruc', '')
                user["categoria"] = data.get('categoria', '')

            users[email] = user

            if save_json_file(USERS_FILE, users):
                log_event("user_registered", user)
                self.send_json_response({
                    "success": True,
                    "user_id": user_id,
                    "message": f"User {nombre} registered. Please login.",
                    "user": {
                        "id": user_id,
                        "nombre": nombre,
                        "email": email,
                        "tipo": user_type
                    }
                })
            else:
                self.send_json_response({"error": "Failed to save user"}, 500)

        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_login(self, data):
        """POST /api/login - User login with JWT token"""
        try:
            # Rate limiting check
            client_ip = get_client_ip(self)
            allowed, retry_after = check_rate_limit(client_ip, "/api/login")
            if not allowed:
                self.send_json_response({
                    "error": "Too many login attempts. Please try again later.",
                    "retry_after": retry_after
                }, 429)
                return

            # Handle multiple field name variations
            email_or_phone = data.get('email_or_phone') or data.get('emailOrPhone') or data.get('email')
            password = data.get('password')
            portal = data.get('portal')  # Portal from request (cliente, repartidor, negocio)

            if not email_or_phone or not password:
                self.send_json_response({"error": "Email/phone and password required"}, 400)
                return

            users = load_json_file(USERS_FILE)
            if not isinstance(users, dict):
                users = {}

            # Search for user by email or phone
            user = None
            user_email = None

            # First try exact email match
            if email_or_phone in users:
                user = users[email_or_phone]
                user_email = email_or_phone
            else:
                # Search by phone number
                for email, u in users.items():
                    if u.get('telefono') == email_or_phone or u.get('phone') == email_or_phone:
                        user = u
                        user_email = email
                        break

            if not user:
                self.send_json_response({"error": "User not found"}, 404)
                return

            # Validate password using bcrypt verify (supports both hashed and plaintext for migration)
            if not verify_password(password, user.get('password')):
                self.send_json_response({"error": "Invalid password"}, 401)
                return

            # Validate portal access - if portal is specified in request, verify user belongs to that portal
            if portal:
                user_portal = user.get('portal') or user.get('tipo')  # Fallback to 'tipo' for backward compatibility
                if user_portal != portal:
                    self.send_json_response({
                        "error": f"User is registered for {user_portal} portal, not {portal}"
                    }, 403)
                    return

            # Create JWT token
            token = create_session(user['id'], user['tipo'], user_email)

            self.send_json_response({
                "success": True,
                "user": {
                    "id": user['id'],
                    "nombre": user['nombre'],
                    "email": user_email,
                    "tipo": user['tipo']
                },
                "token": token,
                "expires_in": TOKEN_EXPIRY,
                "message": "Login successful"
            })

        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_logout(self):
        """POST /api/logout - Invalidate session"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')

            if token:
                sessions = load_json_file(SESSIONS_FILE)
                if isinstance(sessions, dict) and token in sessions:
                    sessions[token]['active'] = False
                    save_json_file(SESSIONS_FILE, sessions)
                    log_event('user_logout', {'token': token[:20] + '...'})

            self.send_json_response({"success": True, "message": "Logged out successfully"})

        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_create_order(self, data):
        """POST /api/order - Create new order with idempotency check"""
        try:
            # Validate token
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)

            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return

            cliente_id = payload.get('sub')
            servicios = data.get('servicios', [])
            total = float(data.get('total', 0))
            idempotency_token = data.get('idempotency_token')

            # Check for duplicate order
            if idempotency_token:
                existing = check_idempotency(idempotency_token)
                if existing:
                    # Return existing order (idempotent)
                    self.send_json_response({
                        "success": True,
                        "order_id": existing['order_id'],
                        "message": "Order already exists (idempotent response)"
                    })
                    return

            # Create new order
            orders = load_json_file(ORDERS_FILE)
            if not isinstance(orders, dict):
                orders = {}

            order_id = str(uuid.uuid4())
            order_token = str(uuid.uuid4())  # Unique token for order tracking

            order = {
                "id": order_id,
                "order_token": order_token,  # NEW: For order tracking
                "cliente_id": cliente_id,
                "servicios": servicios,
                "total": total,
                "estado": "pendiente",
                "timestamp": datetime.now().isoformat()
            }

            orders[order_id] = order

            if save_json_file(ORDERS_FILE, orders):
                # Save idempotency mapping
                if idempotency_token:
                    save_idempotency(idempotency_token, order_id)

                log_event("order_created", {
                    "order_id": order_id,
                    "cliente_id": cliente_id,
                    "total": total
                })

                self.send_json_response({
                    "success": True,
                    "order_id": order_id,
                    "order_token": order_token,
                    "message": "Order created successfully"
                })
            else:
                self.send_json_response({"error": "Failed to save order"}, 500)

        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_create_delivery(self, data):
        """POST /api/delivery - Create new delivery"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)

            if not payload or payload.get('tipo') not in ['admin', 'repartidor']:
                self.send_json_response({"error": "Unauthorized"}, 401)
                return

            orden_id = data.get('orden_id')
            repartidor_id = data.get('repartidor_id')

            deliveries = load_json_file(DELIVERIES_FILE)
            if not isinstance(deliveries, dict):
                deliveries = {}

            delivery_id = str(uuid.uuid4())
            delivery = {
                "id": delivery_id,
                "orden_id": orden_id,
                "repartidor_id": repartidor_id,
                "estado": "activo",
                "tiempo_inicio": datetime.now().isoformat(),
                "tiempo_fin": None
            }

            deliveries[delivery_id] = delivery

            if save_json_file(DELIVERIES_FILE, deliveries):
                log_event("delivery_created", delivery)
                self.send_json_response({
                    "success": True,
                    "delivery_id": delivery_id
                })
            else:
                self.send_json_response({"error": "Failed to save delivery"}, 500)

        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def check_admin_auth(self, query_params=None):
        """Check if request is authenticated as admin"""
        debug_log = DATA_DIR / "debug.log"
        with open(debug_log, 'a') as f:
            f.write(f"DEBUG check_admin_auth: query_params = {query_params}\n")
            f.write(f"DEBUG check_admin_auth: query_params type = {type(query_params)}\n")

        # Try header first
        password = self.headers.get('X-Admin-Password', '')
        with open(debug_log, 'a') as f:
            f.write(f"DEBUG: Header password = '{password}'\n")
        if password == ADMIN_PASSWORD:
            return True

        # Try query params if provided
        if query_params:
            password_list = query_params.get('password', [''])
            password = password_list[0] if password_list else ''
            with open(debug_log, 'a') as f:
                f.write(f"DEBUG: query_params.get('password') = {password_list}, extracted = '{password}', ADMIN_PASSWORD = '{ADMIN_PASSWORD}'\n")
                f.write(f"DEBUG: Comparison: '{password}' == '{ADMIN_PASSWORD}' = {password == ADMIN_PASSWORD}\n")
            if password == ADMIN_PASSWORD:
                return True
        else:
            with open(debug_log, 'a') as f:
                f.write(f"DEBUG: query_params is None or empty\n")

        return False

    def send_json_response(self, data, status_code=200):
        """Send JSON response"""
        response = json.dumps(data, ensure_ascii=False).encode('utf-8')

        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.end_headers()
        self.wfile.write(response)

    def end_headers(self):
        """Add CORS and cache-busting headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Password, Authorization')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        super().end_headers()

    def log_message(self, format, *args):
        """Custom logging"""
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), format % args))


def run_server(port=3000, use_ssl=True):
    """Start the enhanced HTTP server with optional SSL/TLS support"""
    handler = EnhancedHTTPRequestHandler

    socketserver.TCPServer.allow_reuse_address = True

    # Write startup marker to debug log
    debug_log = DATA_DIR / "debug.log"
    with open(debug_log, 'w') as f:
        f.write(f"===== SERVER STARTED AT {datetime.now().isoformat()} =====\n")
        f.write(f"Port: {port}\n")
        f.write(f"SSL/TLS: {use_ssl}\n")
        f.write(f"Handler: {handler}\n")
        f.write(f"PUBLIC_DIR: {PUBLIC_DIR}\n")
        f.write(f"DATA_DIR: {DATA_DIR}\n")

    with socketserver.TCPServer(("0.0.0.0", port), handler) as httpd:
        # Configure SSL/TLS if enabled
        if use_ssl:
            cert_file = DATA_DIR.parent / "certs" / "cert.pem"
            key_file = DATA_DIR.parent / "certs" / "key.pem"

            if cert_file.exists() and key_file.exists():
                try:
                    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                    context.load_cert_chain(str(cert_file), str(key_file))
                    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
                    ssl_enabled = True
                except Exception as e:
                    print(f"[!] Warning: Failed to load SSL certificates: {e}")
                    print(f"[*] Continuing without SSL support")
                    ssl_enabled = False
            else:
                print(f"[!] Warning: SSL certificates not found at {cert_file} or {key_file}")
                print(f"[*] Continuing without SSL support")
                ssl_enabled = False
        else:
            ssl_enabled = False

        host, port_num = httpd.server_address
        protocol = "HTTPS" if ssl_enabled else "HTTP"
        print(f"[OK] JWT-Enhanced Server started successfully")
        print(f"[*] Serving from: {PUBLIC_DIR}")
        print(f"[*] Protocol: {protocol}")
        print(f"[*] Dashboard: {protocol.lower()}://192.168.100.3:{port_num}/admin/")
        print(f"[*] URL: {protocol.lower()}://192.168.100.3:{port_num}/")
        print(f"[*] JWT Secret: {JWT_SECRET[:20]}...")
        print(f"[*] Session Timeout: {SESSION_TIMEOUT // 60} minutes")
        print(f"[*] Press Ctrl+C to stop")
        print("")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[OK] Server stopped")
            sys.exit(0)


if __name__ == "__main__":
    port = 3443  # HTTPS port by default
    use_ssl = True

    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}")
            sys.exit(1)

    # Check for --no-ssl flag to disable SSL
    if "--no-ssl" in sys.argv:
        use_ssl = False
        if port == 3443:
            port = 3000  # Default to HTTP port if SSL is disabled

    run_server(port, use_ssl)
