"""Pre-filtro local para mensajes. Rechaza mensajes no relacionados a AURALINK sin llamar a Claude."""

import re

# Palabras clave que indican un tema relevante a AURALINK/ISP
_RELEVANT_KEYWORDS = {
    # Servicio / cuenta
    "internet", "servicio", "plan", "velocidad", "megas", "mbps",
    "saldo", "pago", "debo", "deuda", "factura", "cobro", "recibo", "monto",
    "cuenta", "cliente", "contrato", "suspendido", "cortado", "reconexion",
    # Conexion / problemas
    "conexion", "conecta", "desconecta", "señal", "antena", "lento", "lenta",
    "rapido", "rapida", "cae", "caida", "caido", "falla", "fallo", "problema",
    "funciona", "no jala", "no sirve", "no carga", "no abre", "sin internet",
    "intermitente", "inestable", "ping", "latencia", "lag",
    # Tecnico
    "router", "modem", "wifi", "pppoe", "mikrotik", "ubiquiti", "antena",
    "dispositivo", "equipo", "cable", "red", "ip", "dns",
    # Soporte
    "soporte", "ayuda", "tecnico", "reportar", "reporte", "ticket",
    "reparar", "arreglar", "visita", "revisar",
    # AURALINK
    "auralink", "aura",
    # Saludos / cortesia (permitir)
    "hola", "buenos dias", "buenas tardes", "buenas noches", "gracias",
    "oye", "disculpa", "por favor", "adios", "bye",
    # Preguntas sobre el servicio
    "horario", "oficina", "telefono", "contacto", "donde", "cobertura",
    "precio", "costo", "paquete", "promocion", "cambio de plan",
}

# Patrones regex adicionales
_RELEVANT_PATTERNS = [
    r"\b10\.10\.\d+\.\d+\b",       # IPs de clientes
    r"\b10\.1\.1\.\d+\b",          # IPs de infraestructura
    r"\$\s*\d+",                    # Montos ($500, $ 200)
    r"\d+\s*mbps",                  # Velocidades
    r"\d+\s*megas",
]

_compiled_patterns = [re.compile(p, re.IGNORECASE) for p in _RELEVANT_PATTERNS]


def is_relevant(text: str) -> bool:
    """Retorna True si el mensaje parece relacionado a AURALINK."""
    text_lower = text.lower().strip()

    # Mensajes muy cortos (< 3 palabras) — permitir, pueden ser respuestas
    if len(text_lower.split()) <= 3:
        return True

    # Buscar keywords
    for kw in _RELEVANT_KEYWORDS:
        if kw in text_lower:
            return True

    # Buscar patrones regex
    for pattern in _compiled_patterns:
        if pattern.search(text_lower):
            return True

    # Preguntas con signos de interrogacion sobre "mi" algo
    if "?" in text_lower and ("mi " in text_lower or "mi " in text_lower):
        return True

    return False


# Mensaje de rechazo
REJECTION_MESSAGE = (
    "😊 Soy Aura, asistente de *AURALINK*. "
    "Solo puedo ayudarte con temas de tu servicio de internet:\n\n"
    "• Saldo y pagos → /misaldo\n"
    "• Tu servicio → /miservicio\n"
    "• Problemas de conexion → /miconexion\n"
    "• Soporte tecnico → /soporte\n\n"
    "Escribe tu consulta o usa los comandos. 👆"
)
