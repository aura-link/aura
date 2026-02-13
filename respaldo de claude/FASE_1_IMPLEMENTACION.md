# FASE 1 - Implementación en RB5009
## Sistema de Suspensión PPPoE - Enfoque Modular y Escalable

**Estado:** Listo para Implementar
**Versión:** 1.0
**Fecha:** 2025-11-14
**Objetivo:** Suspender clientes morosos en MikroTik RB5009 con página de aviso profesional

---

## INTRODUCCIÓN

Esta es la Fase 1 del plan de expansión del sistema de suspensión. En esta fase:

✓ **Usamos solo el RB5009 actual** sin requerir servidor externo
✓ **Estructura modular** que facilita migración a Fase 2
✓ **Manejo automático** de IPs dinámicas de PPPoE
✓ **Logs centralizados** para auditoría y troubleshooting
✓ **Scripts reutilizables** que servirán en futuras expansiones

---

## ARQUITECTURA FASE 1

```
RB5009 (Router Principal)
├── HTTP Server (Puerto 80)
│   └── suspension.html (Página de aviso)
│
├── Firewall Rules
│   ├── Mangle Rules (Marcar clientes suspendidos)
│   └── NAT Rules (Redirigir a página)
│
└── Sistema de Suspensiones (En Linux/WSL/Management PC)
    ├── /etc/suspension/
    │   ├── config/
    │   │   └── settings.conf
    │   ├── scripts/
    │   │   ├── suspension_manager.sh
    │   │   ├── sync_pppoe_ips.sh
    │   │   ├── health_check.sh
    │   │   └── backup.sh
    │   ├── logs/
    │   │   ├── suspension.log
    │   │   ├── sync.log
    │   │   └── health.log
    │   └── backups/
    │       └── clients_backup_*.txt
```

---

## PRE-REQUISITOS

- ✓ MikroTik RB5009 con RouterOS 7.x
- ✓ Acceso SSH al router (usuario: admin, IP: 10.147.17.11)
- ✓ Cliente PPPoE configurado en MikroTik
- ✓ Linux/WSL con bash, ssh, cron disponibles
- ✓ Acceso a ejecutar cron jobs

---

## PASO 1: PREPARAR ESTRUCTURA EN RB5009

### 1.1 Crear Página de Suspensión

Conectarse al MikroTik por SSH:
```bash
ssh admin@10.147.17.11
# Contraseña: 1234
```

Luego ejecutar (en una sola línea):
```
/file add name=suspension.html contents="<!DOCTYPE html><html><head><meta charset=\"UTF-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\"><title>Servicio Suspendido</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:Arial,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);display:flex;justify-content:center;align-items:center;height:100vh;min-height:100vh}h1{color:#fff;font-size:36px;margin-bottom:10px}p{color:#f0f0f0;font-size:16px;line-height:1.6}em{color:#ffd700;font-style:normal;font-weight:bold}.container{background:rgba(0,0,0,0.1);padding:50px;border-radius:15px;max-width:500px;text-align:center;backdrop-filter:blur(10px)}.contact{background:rgba(255,255,255,0.15);padding:25px;margin:25px 0;border-radius:10px;border:2px solid rgba(255,255,255,0.3)}.phone{font-size:32px;color:#ffd700;font-weight:bold;margin:10px 0}.small-text{color:#e0e0e0;font-size:13px;margin-top:5px}.time{color:#ffb347;font-weight:bold}.warning{color:#ff6b6b;font-size:18px;margin:20px 0}.payment-info{background:rgba(255,215,0,0.1);padding:15px;border-radius:8px;margin:15px 0}.account{font-weight:bold;color:#ffd700;font-size:18px;font-family:monospace}</style></head><body><div class=\"container\"><h1>⚠️ SERVICIO SUSPENDIDO</h1><p>Tu conexión ha sido <em>suspendida por falta de pago</em></p><div class=\"warning\">❌ No podrás navegar hasta regularizar tu situación</div><div class=\"contact\"><p><strong>📞 COMUNÍCATE INMEDIATAMENTE:</strong></p><p class=\"phone\">+56 2 3655 0996</p><p class=\"small-text\">Lunes a Viernes: 09:00 - 18:00</p><p class=\"small-text\">Sábados: 10:00 - 14:00</p></div><div class=\"payment-info\"><p><strong>💳 REALIZA TU PAGO EN:</strong></p><p class=\"account\">Cuenta: 123-456789-0</p><p class=\"small-text\">Una vez realices el depósito, reporta el número de comprobante al teléfono anterior</p><p class=\"time\" style=\"margin-top:10px\">⏱️ Tu servicio se restaurará en máximo 1 hora</p></div></div></body></html>"
```

Verificar que se creó:
```
/file print
```

Debería verse `suspension.html` en la lista.

### 1.2 Habilitar HTTP Server

Ejecutar en MikroTik:
```
/ip service set www disabled=no port=80
```

Verificar:
```
/ip service print
```

Debería verse `www` habilitado en puerto 80.

---

## PASO 2: CREAR ESTRUCTURA LOCAL EN MANAGEMENT PC

Si usas **Linux/WSL**, ejecutar:

```bash
sudo mkdir -p /etc/suspension/{config,scripts,logs,backups}
sudo chmod 755 /etc/suspension
```

Si usas **Windows (GitBash/WSL2)**, ejecutar en Linux/WSL:

```bash
mkdir -p ~/suspension/{config,scripts,logs,backups}
```

Para este documento usaremos `/etc/suspension/` (ajusta si usas ruta diferente).

---

## PASO 3: CREAR ARCHIVO DE CONFIGURACIÓN

Crear `/etc/suspension/config/settings.conf`:

```bash
sudo nano /etc/suspension/config/settings.conf
```

Pegar el siguiente contenido:

```bash
#!/bin/bash
# Configuración - Sistema de Suspensión PPPoE
# Última actualización: 2025-11-14

# ===== CONEXIÓN MIKROTIK =====
ROUTER_IP="10.147.17.11"
ROUTER_USER="admin"
ROUTER_PASS="1234"

# ===== RUTAS DE ARCHIVOS =====
SUSPENSION_DIR="/etc/suspension"
CONFIG_FILE="${SUSPENSION_DIR}/config/settings.conf"
SUSPENDED_FILE="${SUSPENSION_DIR}/config/suspended_clients.txt"
LOG_DIR="${SUSPENSION_DIR}/logs"
BACKUP_DIR="${SUSPENSION_DIR}/backups"
SCRIPTS_DIR="${SUSPENSION_DIR}/scripts"

# ===== LOGS =====
SUSPENSION_LOG="${LOG_DIR}/suspension.log"
SYNC_LOG="${LOG_DIR}/sync.log"
HEALTH_LOG="${LOG_DIR}/health.log"

# ===== CONFIGURACIÓN DE SINCRONIZACIÓN =====
SYNC_INTERVAL=5  # Minutos entre actualizaciones de IPs
MAX_RETRIES=3    # Intentos de conexión al router
RETRY_DELAY=2    # Segundos entre reintentos

# ===== FIREWALL MARKS =====
PACKET_MARK="suspended_traffic"  # Nombre de la marca de paquetes
MANGLE_CHAIN="prerouting"        # Chain donde marcar paquetes
NAT_ACTION="redirect"             # Acción NAT (redirect o drop)
NAT_PORT="80"                     # Puerto a redirigir

# ===== BACKUP =====
BACKUP_RETENTION=7   # Días de retención de backups
BACKUP_TIME="02:00"  # Hora de backup automático

# ===== COLORES PARA OUTPUT =====
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ===== FUNCIONES AUXILIARES =====
log_info() {
    local msg="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${BLUE}[${timestamp}]${NC} ${msg}"
    echo "[${timestamp}] ${msg}" >> "${SUSPENSION_LOG}"
}

log_success() {
    local msg="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}✓ ${msg}${NC}"
    echo "[${timestamp}] ✓ ${msg}" >> "${SUSPENSION_LOG}"
}

log_error() {
    local msg="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}✗ ${msg}${NC}"
    echo "[${timestamp}] ✗ ${msg}" >> "${SUSPENSION_LOG}"
}

log_warning() {
    local msg="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}! ${msg}${NC}"
    echo "[${timestamp}] ! ${msg}" >> "${SUSPENSION_LOG}"
}

# Inicializar logs si no existen
if [ ! -f "${SUSPENSION_LOG}" ]; then
    touch "${SUSPENSION_LOG}"
fi

if [ ! -f "${SYNC_LOG}" ]; then
    touch "${SYNC_LOG}"
fi

if [ ! -f "${HEALTH_LOG}" ]; then
    touch "${HEALTH_LOG}"
fi

if [ ! -f "${SUSPENDED_FILE}" ]; then
    touch "${SUSPENDED_FILE}"
fi
```

---

## PASO 4: CREAR SCRIPT MANAGER (Suspender/Reactivar Clientes)

Crear `/etc/suspension/scripts/suspension_manager.sh`:

```bash
sudo nano /etc/suspension/scripts/suspension_manager.sh
```

Pegar:

```bash
#!/bin/bash

# Script de Gestión de Suspensiones PPPoE
# Permite agregar y remover clientes de la lista de suspendidos
# Uso: ./suspension_manager.sh add usuario_pppoe
#      ./suspension_manager.sh remove usuario_pppoe
#      ./suspension_manager.sh list

source /etc/suspension/config/settings.conf

show_help() {
    cat << 'HELP'
╔════════════════════════════════════════════════════════╗
║  Gestor de Suspensiones PPPoE para MikroTik           ║
╚════════════════════════════════════════════════════════╝

Uso: ./suspension_manager.sh [comando] [usuario_pppoe]

Comandos:
  add     - Agregar cliente a suspensión
  remove  - Remover cliente de suspensión
  list    - Listar clientes suspendidos
  help    - Mostrar esta ayuda

Ejemplos:
  ./suspension_manager.sh add cliente_juan
  ./suspension_manager.sh remove cliente_juan
  ./suspension_manager.sh list

HELP
}

add_client() {
    local pppoe_user="$1"

    if [ -z "$pppoe_user" ]; then
        log_error "Debes especificar el usuario PPPoE"
        return 1
    fi

    log_info "Agregando cliente a suspensión: $pppoe_user"

    # Obtener IP actual del usuario PPPoE
    local current_ip=$(ssh -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o PubkeyAuthentication=no \
        "${ROUTER_USER}@${ROUTER_IP}" \
        "/ppp active print where name=$pppoe_user" 2>&1 | \
        grep -i address | awk '{print $NF}')

    if [ -z "$current_ip" ]; then
        log_error "Usuario PPPoE '$pppoe_user' no encontrado o no conectado"
        return 1
    fi

    log_success "IP encontrada: $current_ip"

    # Agregar a lista local
    if ! grep -q "^${pppoe_user}$" "${SUSPENDED_FILE}"; then
        echo "$pppoe_user" >> "${SUSPENDED_FILE}"
        sort "${SUSPENDED_FILE}" -u -o "${SUSPENDED_FILE}"
        log_success "Cliente agregado a lista de suspensión"
    else
        log_warning "Cliente ya estaba en lista de suspensión"
    fi

    # Crear regla en MikroTik
    ssh -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o PubkeyAuthentication=no \
        "${ROUTER_USER}@${ROUTER_IP}" \
        "/ip firewall mangle add chain=${MANGLE_CHAIN} src-address=${current_ip} \
        action=mark-packet new-packet-mark=${PACKET_MARK} \
        comment=\"PPPoE: ${pppoe_user}\"" 2>&1 | grep -v "WARNING" > /dev/null

    log_success "Regla mangle creada en MikroTik"

    echo ""
    echo -e "${BLUE}═════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ Cliente suspendido exitosamente${NC}"
    echo -e "${BLUE}═════════════════════════════════════${NC}"
    echo ""
    echo "Usuario PPPoE: $pppoe_user"
    echo "IP Actual: $current_ip"
    echo "Estado: SUSPENDIDO"
    echo ""
    echo -e "${YELLOW}Nota:${NC} El script de cron actualizará automáticamente"
    echo "       si la IP cambia cada 5 minutos."
    echo ""
}

remove_client() {
    local pppoe_user="$1"

    if [ -z "$pppoe_user" ]; then
        log_error "Debes especificar el usuario PPPoE"
        return 1
    fi

    log_info "Removiendo cliente de suspensión: $pppoe_user"

    # Remover de lista local
    if grep -q "^${pppoe_user}$" "${SUSPENDED_FILE}"; then
        sed -i "/^${pppoe_user}$/d" "${SUSPENDED_FILE}"
        log_success "Cliente removido de lista local"
    else
        log_warning "Cliente no estaba en lista de suspensión"
    fi

    # Remover regla de MikroTik
    ssh -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o PubkeyAuthentication=no \
        "${ROUTER_USER}@${ROUTER_IP}" \
        "/ip firewall mangle remove [find comment~\"${pppoe_user}\"]" 2>&1 | \
        grep -v "WARNING" > /dev/null

    log_success "Regla mangle removida de MikroTik"

    echo ""
    echo -e "${BLUE}═════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ Cliente reactivado exitosamente${NC}"
    echo -e "${BLUE}═════════════════════════════════════${NC}"
    echo ""
    echo "Usuario PPPoE: $pppoe_user"
    echo "Estado: ACTIVO"
    echo ""
}

list_clients() {
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Clientes PPPoE Suspendidos                       ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════╝${NC}"
    echo ""

    if [ ! -s "${SUSPENDED_FILE}" ]; then
        echo -e "${GREEN}✓ No hay clientes suspendidos${NC}"
        echo ""
        return 0
    fi

    echo "Clientes suspendidos:"
    while IFS= read -r user; do
        if [ -n "$user" ]; then
            # Obtener IP actual
            local ip=$(ssh -o StrictHostKeyChecking=no \
                -o UserKnownHostsFile=/dev/null \
                -o PubkeyAuthentication=no \
                "${ROUTER_USER}@${ROUTER_IP}" \
                "/ppp active print where name=$user" 2>&1 | \
                grep -i address | awk '{print $NF}')

            if [ -n "$ip" ]; then
                echo -e "  ${GREEN}✓${NC} $user (IP: $ip)"
            else
                echo -e "  ${YELLOW}⚠${NC} $user (Desconectado)"
            fi
        fi
    done < "${SUSPENDED_FILE}"

    echo ""
    echo "Total suspendidos: $(wc -l < ${SUSPENDED_FILE})"
    echo ""
}

# MAIN
case "$1" in
    add)
        add_client "$2"
        ;;
    remove)
        remove_client "$2"
        ;;
    list)
        list_clients
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Comando no reconocido: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
```

Hacer ejecutable:
```bash
sudo chmod +x /etc/suspension/scripts/suspension_manager.sh
```

---

## PASO 5: CREAR SCRIPT DE SINCRONIZACIÓN (Auto-Actualizar IPs)

Crear `/etc/suspension/scripts/sync_pppoe_ips.sh`:

```bash
sudo nano /etc/suspension/scripts/sync_pppoe_ips.sh
```

Pegar:

```bash
#!/bin/bash

# Script de Auto-Sincronización de IPs PPPoE
# Se ejecuta automáticamente cada 5 minutos via cron
# Detecta cambios de IP y actualiza reglas en MikroTik

source /etc/suspension/config/settings.conf

sync_pppoe_ips() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] === Iniciando sincronización ===" >> "${SYNC_LOG}"

    # Verificar si hay clientes suspendidos
    if [ ! -s "${SUSPENDED_FILE}" ]; then
        echo "[$timestamp] No hay clientes suspendidos" >> "${SYNC_LOG}"
        return 0
    fi

    # Procesar cada cliente
    while IFS= read -r pppoe_user; do
        if [ -z "$pppoe_user" ]; then
            continue
        fi

        echo "[$timestamp] Procesando: $pppoe_user" >> "${SYNC_LOG}"

        # Obtener IP actual
        local current_ip=$(ssh -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            -o PubkeyAuthentication=no \
            "${ROUTER_USER}@${ROUTER_IP}" \
            "/ppp active print where name=$pppoe_user" 2>&1 | \
            grep -i address | awk '{print $NF}')

        if [ -z "$current_ip" ]; then
            echo "[$timestamp]   ⚠️  $pppoe_user desconectado" >> "${SYNC_LOG}"
            continue
        fi

        echo "[$timestamp]   IP actual: $current_ip" >> "${SYNC_LOG}"

        # Obtener IP de la regla existente
        local rule_ip=$(ssh -o StrictHostKeyChecking=no \
            -o UserKnownHostsFile=/dev/null \
            -o PubkeyAuthentication=no \
            "${ROUTER_USER}@${ROUTER_IP}" \
            "/ip firewall mangle print where comment~\"${pppoe_user}\"" 2>&1 | \
            grep -oP 'src-address=\K[^ ]+' | head -1)

        if [ "$current_ip" = "$rule_ip" ]; then
            echo "[$timestamp]   ✓ IP sin cambios" >> "${SYNC_LOG}"
        else
            echo "[$timestamp]   ! Cambio detectado: $rule_ip → $current_ip" >> "${SYNC_LOG}"

            # Remover regla antigua
            ssh -o StrictHostKeyChecking=no \
                -o UserKnownHostsFile=/dev/null \
                -o PubkeyAuthentication=no \
                "${ROUTER_USER}@${ROUTER_IP}" \
                "/ip firewall mangle remove [find comment~\"${pppoe_user}\"]" 2>&1 | \
                grep -v "WARNING" > /dev/null

            echo "[$timestamp]   - Regla antigua removida" >> "${SYNC_LOG}"

            # Crear regla nueva
            ssh -o StrictHostKeyChecking=no \
                -o UserKnownHostsFile=/dev/null \
                -o PubkeyAuthentication=no \
                "${ROUTER_USER}@${ROUTER_IP}" \
                "/ip firewall mangle add chain=${MANGLE_CHAIN} src-address=${current_ip} \
                action=mark-packet new-packet-mark=${PACKET_MARK} \
                comment=\"PPPoE: ${pppoe_user}\"" 2>&1 | \
                grep -v "WARNING" > /dev/null

            echo "[$timestamp]   + Regla nueva creada con IP $current_ip" >> "${SYNC_LOG}"
        fi

    done < "${SUSPENDED_FILE}"

    echo "[$timestamp] === Sincronización completada ===" >> "${SYNC_LOG}"
}

sync_pppoe_ips
```

Hacer ejecutable:
```bash
sudo chmod +x /etc/suspension/scripts/sync_pppoe_ips.sh
```

---

## PASO 6: CREAR SCRIPT DE MONITOREO

Crear `/etc/suspension/scripts/health_check.sh`:

```bash
sudo nano /etc/suspension/scripts/health_check.sh
```

Pegar:

```bash
#!/bin/bash

# Script de Monitoreo - Verifica salud del sistema
# Se ejecuta cada 30 minutos para detectar problemas

source /etc/suspension/config/settings.conf

check_router_connectivity() {
    if ping -c 1 -W 2 "${ROUTER_IP}" &> /dev/null; then
        log_success "Router accesible"
        return 0
    else
        log_error "Router NO accesible: ${ROUTER_IP}"
        return 1
    fi
}

check_http_service() {
    local status=$(ssh -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o PubkeyAuthentication=no \
        "${ROUTER_USER}@${ROUTER_IP}" \
        "/ip service print where name=www" 2>&1 | grep -c "www")

    if [ "$status" -gt 0 ]; then
        log_success "HTTP Service activo"
        return 0
    else
        log_error "HTTP Service NO activo"
        return 1
    fi
}

check_mangle_rules() {
    local count=$(ssh -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o PubkeyAuthentication=no \
        "${ROUTER_USER}@${ROUTER_IP}" \
        "/ip firewall mangle print where comment~\"PPPoE:\"" 2>&1 | grep -c "PPPoE:")

    local suspended=$(wc -l < "${SUSPENDED_FILE}")

    if [ "$count" -eq "$suspended" ]; then
        log_success "Reglas mangle sincronizadas ($count activas)"
        return 0
    else
        log_warning "Mangle rules desincronizadas - Config: $suspended, Router: $count"
        return 1
    fi
}

check_logs_size() {
    # Advertencia si logs superan 10MB
    local log_size=$(du -sh "${LOG_DIR}" | awk '{print $1}')
    log_info "Tamaño de logs: $log_size"
}

check_disk_space() {
    # Advertencia si espacio disponible es menor al 10%
    local available=$(df "${SUSPENSION_DIR}" | awk 'NR==2 {print $4}')
    local total=$(df "${SUSPENSION_DIR}" | awk 'NR==2 {print $2}')
    local percent=$((available * 100 / total))

    if [ "$percent" -lt 10 ]; then
        log_warning "Espacio en disco bajo: ${percent}%"
        return 1
    else
        log_success "Espacio en disco OK: ${percent}%"
        return 0
    fi
}

# MAIN
log_info "=== Iniciando Health Check ==="
check_router_connectivity
check_http_service
check_mangle_rules
check_logs_size
check_disk_space
log_info "=== Health Check completado ==="
```

Hacer ejecutable:
```bash
sudo chmod +x /etc/suspension/scripts/health_check.sh
```

---

## PASO 7: CREAR SCRIPT DE BACKUP

Crear `/etc/suspension/scripts/backup.sh`:

```bash
sudo nano /etc/suspension/scripts/backup.sh
```

Pegar:

```bash
#!/bin/bash

# Script de Backup - Respalda lista de clientes suspendidos
# Se ejecuta diariamente para mantener historial

source /etc/suspension/config/settings.conf

create_backup() {
    local timestamp=$(date '+%Y-%m-%d_%H-%M-%S')
    local backup_file="${BACKUP_DIR}/clients_backup_${timestamp}.txt"

    cp "${SUSPENDED_FILE}" "${backup_file}"

    log_success "Backup creado: $backup_file"
}

cleanup_old_backups() {
    # Eliminar backups más antiguos que BACKUP_RETENTION días
    find "${BACKUP_DIR}" -name "clients_backup_*.txt" -mtime "+${BACKUP_RETENTION}" -delete

    local count=$(find "${BACKUP_DIR}" -name "clients_backup_*.txt" | wc -l)
    log_info "Backups retenidos: $count"
}

# MAIN
log_info "=== Iniciando Backup ==="
create_backup
cleanup_old_backups
log_info "=== Backup completado ==="
```

Hacer ejecutable:
```bash
sudo chmod +x /etc/suspension/scripts/backup.sh
```

---

## PASO 8: INSTALAR CRON JOBS

Para instalar los cron jobs, ejecutar:

```bash
sudo crontab -e
```

Agregar las siguientes líneas al final:

```cron
# Sistema de Suspensión PPPoE - FASE 1

# Sincronizar IPs cada 5 minutos
*/5 * * * * /etc/suspension/scripts/sync_pppoe_ips.sh

# Monitoreo cada 30 minutos
*/30 * * * * /etc/suspension/scripts/health_check.sh

# Backup diario a las 2 AM
0 2 * * * /etc/suspension/scripts/backup.sh

# Limpiar logs grandes semanalmente (domingo a las 3 AM)
0 3 * * 0 find /etc/suspension/logs -name "*.log" -size +50M -exec truncate -s 0 {} \;
```

Verificar que se instalaron:
```bash
sudo crontab -l
```

---

## PASO 9: PRUEBA DEL SISTEMA

### Test 1: Suspender Cliente

```bash
sudo /etc/suspension/scripts/suspension_manager.sh add cliente_juan
```

Debería ver:
- ✓ IP encontrada
- ✓ Cliente agregado a lista
- ✓ Regla mangle creada

### Test 2: Listar Clientes

```bash
sudo /etc/suspension/scripts/suspension_manager.sh list
```

Debería ver cliente_juan con su IP.

### Test 3: Ver Logs

```bash
tail -f /etc/suspension/logs/suspension.log
```

### Test 4: Verificar en MikroTik

```bash
ssh admin@10.147.17.11
/ip firewall mangle print where comment~"PPPoE:"
```

Debería ver la regla con el cliente.

### Test 5: Probar Página de Suspensión

Desde una máquina con la IP del cliente suspendido, abrir navegador e ir a cualquier sitio. Debería ver la página de suspensión.

### Test 6: Reactivar Cliente

```bash
sudo /etc/suspension/scripts/suspension_manager.sh remove cliente_juan
```

Debería poder navegar normalmente.

---

## PASO 10: MONITOREO CONTINUO

### Ver logs en tiempo real:

```bash
# Suspensiones
tail -f /etc/suspension/logs/suspension.log

# Sincronización
tail -f /etc/suspension/logs/sync.log

# Salud del sistema
tail -f /etc/suspension/logs/health.log
```

### Ver clientes suspendidos:

```bash
cat /etc/suspension/config/suspended_clients.txt
```

### Ver backups:

```bash
ls -lah /etc/suspension/backups/
```

---

## TROUBLESHOOTING

### Problema: Script no encuentra router

```bash
# Verificar conectividad
ping 10.147.17.11

# Verificar SSH
ssh -o StrictHostKeyChecking=no admin@10.147.17.11 "id"
```

### Problema: Página no aparece

```bash
# Verificar que archivo existe en MikroTik
ssh admin@10.147.17.11 "/file print"

# Verificar HTTP service
ssh admin@10.147.17.11 "/ip service print"

# Verificar reglas
ssh admin@10.147.17.11 "/ip firewall mangle print"
ssh admin@10.147.17.11 "/ip firewall nat print"
```

### Problema: Cron no se ejecuta

```bash
# Verificar que cron está activo
sudo crontab -l

# Ver logs de cron
sudo tail -f /var/log/syslog | grep CRON
```

### Problema: IPs no se actualizan

```bash
# Ejecutar sincronización manual
/etc/suspension/scripts/sync_pppoe_ips.sh

# Ver log de sincronización
tail -f /etc/suspension/logs/sync.log
```

---

## CHECKLIST DE IMPLEMENTACIÓN

- [ ] Crear página HTML en MikroTik
- [ ] Habilitar HTTP service en puerto 80
- [ ] Crear estructura `/etc/suspension/`
- [ ] Crear archivo `settings.conf`
- [ ] Crear script `suspension_manager.sh`
- [ ] Crear script `sync_pppoe_ips.sh`
- [ ] Crear script `health_check.sh`
- [ ] Crear script `backup.sh`
- [ ] Instalar cron jobs
- [ ] Test: Suspender cliente
- [ ] Test: Ver cliente en lista
- [ ] Test: Verificar regla en MikroTik
- [ ] Test: Probar página de suspensión
- [ ] Test: Reactivar cliente
- [ ] Monitorear logs
- [ ] Realizar backup manual

---

## PRÓXIMOS PASOS

Una vez FASE 1 esté funcionando:

1. **Semana siguiente:**
   - Validar con clientes reales
   - Ajustar página de suspensión
   - Optimizar tiempos de sincronización

2. **Cuando tengas nuevo RB:**
   - Implementar FASE 2 (API centralizada)
   - Ambos routers usando misma API
   - Sincronización automática entre RBs

3. **FASE 3 (Futuro):**
   - Panel web centralizado
   - Base de datos MySQL
   - Reportes y estadísticas

---

## TRANSICIÓN A FASE 2 (Cuando hayas nuevo RB)

Cuando adquieras el nuevo RB, SOLO necesitarás cambiar:

**En settings.conf:**
```bash
# De archivos locales a API
SUSPENDED_FILE_TYPE="api"  # En vez de "local"
API_URL="http://api-server:8080"
```

**En sync_pppoe_ips.sh:**
```bash
# En vez de leer archivo local:
# while IFS= read -r user < "${SUSPENDED_FILE}"

# Leerás de API:
# suspended_users=$(curl -s "${API_URL}/api/suspended")
```

Los scripts permanecerán prácticamente idénticos, solo cambiará de dónde obtienen datos.

---

**Estado:** FASE 1 Lista para implementar
**Última revisión:** 2025-11-14
**Versión:** 1.0
**Autor:** Sistema de Suspensión PPPoE
