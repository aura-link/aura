"""Definiciones de herramientas (tools) para Claude AI."""

TOOLS = [
    {
        "name": "consultar_saldo_cliente",
        "description": "Consulta el saldo, facturas pendientes y estado de pago de un cliente. Usa el client_id del cliente vinculado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "ID del cliente en el CRM de UISP",
                }
            },
            "required": ["client_id"],
        },
    },
    {
        "name": "consultar_servicio_cliente",
        "description": "Consulta los servicios de un cliente: plan, velocidad, estado.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "ID del cliente en el CRM de UISP",
                }
            },
            "required": ["client_id"],
        },
    },
    {
        "name": "diagnosticar_conexion_cliente",
        "description": "Diagnostica la conexion de un cliente: señal de antena, sesion PPPoE, ping. Util cuando el cliente reporta problemas.",
        "input_schema": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "ID del cliente en el CRM de UISP",
                }
            },
            "required": ["client_id"],
        },
    },
    {
        "name": "consultar_estado_red",
        "description": "Muestra el estado general de la red: dispositivos online/offline, clientes, sesiones PPPoE.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "buscar_cliente_por_nombre",
        "description": "Busca un cliente en el CRM por nombre. Retorna coincidencias.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {
                    "type": "string",
                    "description": "Nombre o parte del nombre del cliente",
                }
            },
            "required": ["nombre"],
        },
    },
    {
        "name": "listar_dispositivos_offline",
        "description": "Lista los dispositivos (antenas) que estan offline/desconectados.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "consultar_sesion_pppoe",
        "description": "Busca una sesion PPPoE activa por IP o nombre de usuario.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ip": {
                    "type": "string",
                    "description": "IP del cliente (ej: 10.10.1.X)",
                },
                "nombre": {
                    "type": "string",
                    "description": "Nombre de usuario PPPoE",
                },
            },
        },
    },
    {
        "name": "ping_dispositivo",
        "description": "Hace ping a una IP desde el MikroTik para verificar conectividad.",
        "input_schema": {
            "type": "object",
            "properties": {
                "ip": {
                    "type": "string",
                    "description": "IP a la que hacer ping",
                }
            },
            "required": ["ip"],
        },
    },
    {
        "name": "escalar_a_soporte",
        "description": "Crea un ticket de soporte para que un tecnico atienda al cliente. Usar solo cuando el problema no se puede resolver automaticamente.",
        "input_schema": {
            "type": "object",
            "properties": {
                "motivo": {
                    "type": "string",
                    "description": "Descripcion del problema o motivo de la escalacion",
                }
            },
            "required": ["motivo"],
        },
    },
]
