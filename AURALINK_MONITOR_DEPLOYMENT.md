# AURALINK Monitor - Telegram Bot para UISP
## Sistema Inteligente de Monitoreo con IA

---

## 📋 TABLA DE CONTENIDOS
1. [Descripción General](#descripción-general)
2. [Requisitos](#requisitos)
3. [Instalación](#instalación)
4. [Configuración](#configuración)
5. [Uso](#uso)
6. [Comandos Disponibles](#comandos-disponibles)
7. [Ejemplos de Uso](#ejemplos-de-uso)
8. [Troubleshooting](#troubleshooting)

---

## 📱 DESCRIPCIÓN GENERAL

**AURALINK Monitor** es un bot de Telegram que conecta con tu servidor UISP para:

✅ Monitoreo en tiempo real de clientes y dispositivos
✅ Consultas naturales en lenguaje Telegram ("¿Cuál es la IP del cliente X?")
✅ Gráficas y reportes de consumo
✅ Alertas automáticas de problemas
✅ Gestión centralizada desde tu teléfono

### Arquitectura:
```
Telegram (@auralinkmonitor_bot)
    ↓
Python + python-telegram-bot
    ↓
UISP API (10.1.1.254)
    ↓
Datos de clientes, dispositivos, estadísticas
```

---

## ⚙️ REQUISITOS

**Instalados y Verificados:**
- ✓ Python 3.12.3
- ✓ python-telegram-bot 22.5
- ✓ matplotlib 3.10.7
- ✓ pandas 2.3.3
- ✓ plotly 6.5.0
- ✓ Pillow 12.0.0
- ✓ requests 2.31.0

**Servidores:**
- ✓ UISP Server: 10.1.1.254 (usuario: AURALINK, pass: 1234)
- ✓ Telegram Bot: @auralinkmonitor_bot (Token: 8318058273:AAEiKpg6L8gG9DSb4zLrtnPUS1Z6urYe_UI)

---

## 🚀 INSTALACIÓN

### Paso 1: Verificar que todo está instalado

```bash
# Conectarse al servidor UISP
ssh uisp@10.1.1.254

# Verificar estructura
ls -la /home/uisp/auralink_monitor/

# Salida esperada:
# -rwxr-xr-x  auralink_monitor.py
# drwxrwxr-x  bin/
# drwxrwxr-x  lib/
```

### Paso 2: Instalar el servicio systemd

```bash
# Desde tu máquina local o servidor
sudo bash INSTALAR_SERVICIO.sh
```

Esto hará:
1. Copiar archivo de servicio a `/etc/systemd/system/`
2. Recargar systemd
3. Habilitar servicio (se inicia automáticamente)
4. Iniciar el bot

### Paso 3: Verificar que está corriendo

```bash
# Ver estado
sudo systemctl status auralink-monitor

# Ver logs en tiempo real
sudo journalctl -u auralink-monitor -f
```

---

## ⚙️ CONFIGURACIÓN

### Token de Telegram
El token ya está configurado en el script:
```
8318058273:AAEiKpg6L8gG9DSb4zLrtnPUS1Z6urYe_UI
```

### Credenciales UISP
```
Host: 10.1.1.254
Usuario: AURALINK
Contraseña: 1234
```

### Autorizar Usuarios
El bot autoriza automáticamente el primer usuario que envía `/start`.

Para agregar más usuarios manualmente, editar `auralink_monitor.py`:
```python
AUTHORIZED_USERS = {123456789, 987654321}  # IDs de Telegram
```

---

## 📱 USO

### Paso 1: Iniciar el Bot en Telegram

Busca **@auralinkmonitor_bot** en Telegram y envía:
```
/start
```

Respuesta esperada:
```
🌐 AURALINK Monitor
Monitoreo inteligente de UISP vía Telegram + IA
...
```

### Paso 2: Usar Comandos

**Comandos básicos:**
```
/help         - Ver ayuda
/status       - Estado general
/clients      - Listar clientes
/devices      - Listar dispositivos
```

**Consultas naturales:**
```
¿Cuál es la IP del cliente Zuri?
Muéstrame el consumo de Roman Cervantes
¿Cuántos clientes están activos?
¿Qué dispositivos están offline?
```

---

## 🎯 COMANDOS DISPONIBLES

| Comando | Descripción |
|---------|------------|
| `/start` | Iniciar bot y autorizar usuario |
| `/help` | Ver guía de uso |
| `/status` | Estado general del sistema |
| `/clients` | Listar clientes (primeros 20) |
| `/devices` | Listar dispositivos (primeros 15) |
| Mensaje libre | Bot interpreta consultas naturales |

---

## 💡 EJEMPLOS DE USO

### Ejemplo 1: Consultar IP de un cliente
```
Usuario: ¿Cuál es la IP del cliente Zuri?

Bot: ✅ Cliente Encontrado
Nombre: Zuri
ID: xxxx-xxxx-xxxx
Estado: 🟢 Activo
Ubicación: La Gloria
```

### Ejemplo 2: Ver estado general
```
Usuario: /status

Bot: ✅ Estado AURALINK Monitor

📊 Estadísticas:
• Clientes activos: 45/68
• Dispositivos: 12
• Servidor UISP: 🟢 Online

⏰ Última actualización: 2025-11-30 14:22:15
```

### Ejemplo 3: Listar dispositivos
```
Usuario: /devices

Bot: 🖥️ Dispositivos:
1. 🟢 AP-Gloria-01 (EAP225)
2. 🟢 AP-Gloria-02 (EAP225)
3. 🟢 Switch-Main (TL-SG3210)
... y 9 más
```

---

## 🔧 TROUBLESHOOTING

### El bot no responde

**Verificar que está corriendo:**
```bash
sudo systemctl status auralink-monitor
```

**Ver logs:**
```bash
sudo journalctl -u auralink-monitor -f
```

**Errores comunes:**

1. **"Error conectando a UISP"**
   - Verificar que 10.1.1.254 es alcanzable
   - Verificar credenciales AURALINK / 1234
   - Verificar certificado SSL (accept all para ahora)

2. **"Telegram API error"**
   - Verificar que el token sea correcto
   - Verificar conectividad a internet
   - Revisar logs: `sudo journalctl -u auralink-monitor -n 50`

3. **"Comando no disponible"**
   - Usuario no está autorizado
   - Enviar `/start` primero para autorizar

### Reiniciar el servicio

```bash
# Detener
sudo systemctl stop auralink-monitor

# Iniciar
sudo systemctl start auralink-monitor

# O directamente reiniciar
sudo systemctl restart auralink-monitor
```

### Ver logs detallados

```bash
# Últimas 50 líneas
sudo journalctl -u auralink-monitor -n 50

# Últimas 100 líneas
sudo journalctl -u auralink-monitor -n 100

# En tiempo real
sudo journalctl -u auralink-monitor -f

# Con nivel de debug
sudo journalctl -u auralink-monitor -p debug -n 100
```

---

## 📊 PRÓXIMAS FUNCIONALIDADES

**En desarrollo:**
- [ ] Gráficas de consumo en tiempo real
- [ ] Integración con Claude AI para consultas inteligentes
- [ ] Alertas automáticas (CPU > 80%, latencia > 100ms)
- [ ] Reportes diarios/semanales
- [ ] Gestión de antennas Ubiquiti
- [ ] Exportar datos a archivos

---

## 🔐 SEGURIDAD

- ✓ Credenciales almacenadas localmente (no en la nube)
- ✓ Solo usuarios autorizados pueden usar el bot
- ✓ HTTPS para comunicación con UISP (SSL auto-firmado tolerado)
- ✓ Logs almacenados en `/home/uisp/auralink_monitor/monitor.log`

**Recomendaciones:**
- Cambiar contraseña UISP después de testing
- Limitar acceso al servidor UISP
- Revisar logs regularmente

---

## 📞 SOPORTE

**Logs del sistema:**
```bash
sudo journalctl -u auralink-monitor -f
```

**Archivo de log:**
```bash
cat /home/uisp/auralink_monitor/monitor.log
```

**Información del servidor UISP:**
```bash
ssh uisp@10.1.1.254
free -h        # RAM
df -h          # Disco
top -n 1       # Procesos
```

---

## 📝 CHANGELOG

### v1.0 (2025-11-30)
- ✅ Conexión a UISP API
- ✅ Bot de Telegram funcional
- ✅ Comandos básicos (/start, /help, /status, /clients, /devices)
- ✅ Búsqueda de clientes por nombre
- ✅ Servicio systemd para ejecución 24/7

### Próximas versiones:
- v1.1: Gráficas y estadísticas
- v1.2: Integración IA (Claude)
- v1.3: Alertas automáticas
- v2.0: API pública para extensiones

---

**Generado:** 2025-11-30
**Versión:** 1.0
**Estado:** 🟢 OPERACIONAL

