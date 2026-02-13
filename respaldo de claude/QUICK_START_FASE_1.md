# QUICK START - FASE 1 (Guía Rápida)

**Para implementar el sistema en 30 minutos**

---

## RESUMEN

Suspender clientes morosos con página profesional en MikroTik RB5009. El sistema:
- ✓ Maneja IPs dinámicas de PPPoE
- ✓ Se actualiza automáticamente cada 5 minutos
- ✓ Modular y escalable para Fase 2

---

## PASO 1: Página de Suspensión en MikroTik (5 min)

Conectarte por SSH:
```bash
ssh admin@10.147.17.11
```

Ejecutar (una sola línea - copiar completo):
```
/file add name=suspension.html contents="<!DOCTYPE html><html><head><meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\"><title>Servicio Suspendido</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:Arial,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);display:flex;justify-content:center;align-items:center;height:100vh;min-height:100vh}h1{color:#fff;font-size:36px;margin-bottom:10px}p{color:#f0f0f0;font-size:16px;line-height:1.6}em{color:#ffd700;font-style:normal;font-weight:bold}.container{background:rgba(0,0,0,0.1);padding:50px;border-radius:15px;max-width:500px;text-align:center;backdrop-filter:blur(10px)}.contact{background:rgba(255,255,255,0.15);padding:25px;margin:25px 0;border-radius:10px;border:2px solid rgba(255,255,255,0.3)}.phone{font-size:32px;color:#ffd700;font-weight:bold;margin:10px 0}.small-text{color:#e0e0e0;font-size:13px;margin-top:5px}.time{color:#ffb347;font-weight:bold}.warning{color:#ff6b6b;font-size:18px;margin:20px 0}.payment-info{background:rgba(255,215,0,0.1);padding:15px;border-radius:8px;margin:15px 0}.account{font-weight:bold;color:#ffd700;font-size:18px;font-family:monospace}</style></head><body><div class=\"container\"><h1>⚠️ SERVICIO SUSPENDIDO</h1><p>Tu conexión ha sido <em>suspendida por falta de pago</em></p><div class=\"warning\">❌ No podrás navegar hasta regularizar tu situación</div><div class=\"contact\"><p><strong>📞 COMUNÍCATE INMEDIATAMENTE:</strong></p><p class=\"phone\">+56 2 3655 0996</p><p class=\"small-text\">Lunes a Viernes: 09:00 - 18:00</p><p class=\"small-text\">Sábados: 10:00 - 14:00</p></div><div class=\"payment-info\"><p><strong>💳 REALIZA TU PAGO EN:</strong></p><p class=\"account\">Cuenta: 123-456789-0</p><p class=\"small-text\">Una vez realices el depósito, reporta el número de comprobante al teléfono anterior</p><p class=\"time\" style=\"margin-top:10px\">⏱️ Tu servicio se restaurará en máximo 1 hora</p></div></div></body></html>"
```

Verificar:
```
/file print
```

Habilitar HTTP:
```
/ip service set www disabled=no port=80
```

---

## PASO 2: Crear Estructura Local (5 min)

En tu Linux/WSL ejecutar:

```bash
# Crear carpetas
sudo mkdir -p /etc/suspension/{config,scripts,logs,backups}

# Crear archivo de configuración
sudo nano /etc/suspension/config/settings.conf
```

Pega este contenido en `settings.conf`:
```bash
#!/bin/bash
ROUTER_IP="10.147.17.11"
ROUTER_USER="admin"
SUSPENSION_DIR="/etc/suspension"
SUSPENDED_FILE="${SUSPENSION_DIR}/config/suspended_clients.txt"
LOG_DIR="${SUSPENSION_DIR}/logs"
BACKUP_DIR="${SUSPENSION_DIR}/backups"
SCRIPTS_DIR="${SUSPENSION_DIR}/scripts"
SUSPENSION_LOG="${LOG_DIR}/suspension.log"
SYNC_LOG="${LOG_DIR}/sync.log"
HEALTH_LOG="${LOG_DIR}/health.log"
SYNC_INTERVAL=5
PACKET_MARK="suspended_traffic"
MANGLE_CHAIN="prerouting"
NAT_PORT="80"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" >> "${SUSPENSION_LOG}"; }
log_success() { echo -e "${GREEN}✓ $1${NC}" >> "${SUSPENSION_LOG}"; }
log_error() { echo -e "${RED}✗ $1${NC}" >> "${SUSPENSION_LOG}"; }

[ ! -f "${SUSPENSION_LOG}" ] && touch "${SUSPENSION_LOG}"
[ ! -f "${SYNC_LOG}" ] && touch "${SYNC_LOG}"
[ ! -f "${HEALTH_LOG}" ] && touch "${HEALTH_LOG}"
[ ! -f "${SUSPENDED_FILE}" ] && touch "${SUSPENDED_FILE}"
```

Guardar: `Ctrl+X`, `Y`, `Enter`

---

## PASO 3: Script Manager (5 min)

```bash
sudo nano /etc/suspension/scripts/suspension_manager.sh
```

Copiar todo de `FASE_1_IMPLEMENTACION.md` sección "PASO 4: CREAR SCRIPT MANAGER"

Hacer ejecutable:
```bash
sudo chmod +x /etc/suspension/scripts/suspension_manager.sh
```

---

## PASO 4: Script de Sincronización (5 min)

```bash
sudo nano /etc/suspension/scripts/sync_pppoe_ips.sh
```

Copiar todo de `FASE_1_IMPLEMENTACION.md` sección "PASO 5: CREAR SCRIPT DE SINCRONIZACIÓN"

Hacer ejecutable:
```bash
sudo chmod +x /etc/suspension/scripts/sync_pppoe_ips.sh
```

---

## PASO 5: Instalar Cron (2 min)

```bash
sudo crontab -e
```

Agregar al final:
```cron
*/5 * * * * /etc/suspension/scripts/sync_pppoe_ips.sh
```

Guardar y salir.

---

## PASO 6: Primer Uso (3 min)

Suspender cliente:
```bash
sudo /etc/suspension/scripts/suspension_manager.sh add cliente_juan
```

Ver clientes:
```bash
sudo /etc/suspension/scripts/suspension_manager.sh list
```

Ver logs:
```bash
tail -f /etc/suspension/logs/suspension.log
```

Reactivar:
```bash
sudo /etc/suspension/scripts/suspension_manager.sh remove cliente_juan
```

---

## COMANDOS PRINCIPALES

### Suspender Cliente
```bash
sudo /etc/suspension/scripts/suspension_manager.sh add usuario_pppoe
```

### Reactivar Cliente
```bash
sudo /etc/suspension/scripts/suspension_manager.sh remove usuario_pppoe
```

### Ver Clientes Suspendidos
```bash
sudo /etc/suspension/scripts/suspension_manager.sh list
```

### Ver Logs en Tiempo Real
```bash
tail -f /etc/suspension/logs/suspension.log
tail -f /etc/suspension/logs/sync.log
```

### Ver Lista de Suspendidos
```bash
cat /etc/suspension/config/suspended_clients.txt
```

### Verificar en MikroTik
```bash
ssh admin@10.147.17.11 "/ip firewall mangle print where comment~PPPoE:"
```

---

## TROUBLESHOOTING RÁPIDO

**Problema:** "Usuario no encontrado"
- El cliente debe estar conectado al PPPoE cuando ejecutas el script

**Problema:** "SSH Connection Refused"
- Verificar que puedas conectar: `ssh admin@10.147.17.11`
- Usar: `ssh -o StrictHostKeyChecking=no admin@10.147.17.11`

**Problema:** "Página no aparece"
- Verificar HTML en MikroTik: `ssh admin@10.147.17.11 "/file print"`
- Verificar HTTP: `ssh admin@10.147.17.11 "/ip service print"`

**Problema:** "Cron no ejecuta"
- Verificar: `sudo crontab -l`
- Ver logs: `sudo tail -f /var/log/syslog | grep CRON`

---

## SIGUIENTE PASO

Una vez todo funcione con clientes reales:

1. Ajustar teléfono y cuenta bancaria en HTML (línea de `contents=`)
2. Customizar tiempos de sync si es necesario (default: 5 min)
3. Ver `FASE_1_IMPLEMENTACION.md` para scripts adicionales (health check, backup)

Cuando tengas nuevo RB, pasar a FASE 2 (API centralizada) - cambios mínimos en código.

---

**Estado:** Listo para usar
**Tiempo total:** ~30 minutos
**Próxima fase:** FASE 2 (cuando tengas nuevo RB)
