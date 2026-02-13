# Arquitectura Escalable - Sistema de Suspensión PPPoE

## Visión Actual vs Futura

### AHORA (Fase 1 - Transición)
```
RB5009 (Actual) - Balanceador
├── HTTP Server (Suspensión)
├── Mangle Rules (Marcar clientes)
└── NAT Rules (Redirigir)
```

### FUTURO (Fase 2 - Escalable)
```
RB Nuevo (PPPoE + Control)           RB5009 (Solo Balanceador)
├── PPPoE Server                     ├── Failover
├── HTTP Server (Suspensión)         ├── Traffic Distribution
├── Mangle Rules                     └── Health Check
├── NAT Rules
└── Database (Clientes)

         ↓ (Sincronizado)

Servidor Linux (Central)
├── API de Suspensiones
├── Database MySQL
├── Logs Centralizados
└── Panel de Control
```

---

## Estrategia de 3 Fases

### FASE 1: Ahora (Arquitectura Aislada)
**Objetivo:** Sistema funcional y modular en RB5009

1. Scripts separados por funcionalidad:
   - `suspension_manager.sh` - Gestión de suspensiones
   - `sync_pppoe_ips.sh` - Actualizar IPs dinámicas (Cron)
   - `health_check.sh` - Monitoreo del sistema

2. Almacenamiento local:
   - `/etc/suspension/suspended_clients.txt` - Lista de suspendidos
   - `/var/log/suspension/` - Logs

3. Independencia total:
   - No depende de servidores externos
   - Funciona de forma autónoma

---

### FASE 2: Transición (Preparar para nuevo RB)
**Objetivo:** Preparar la infraestructura sin cambiar lo existente

1. Centralizar en Servidor Linux:
   - Crear API REST para suspensiones
   - Base de datos MySQL con lista de clientes
   - Scripts que se comuniquen con API

2. RB5009 comunica con servidor:
   ```
   RB5009 --> API Server Linux:8080 --> MySQL
   ```

3. Nuevo RB también usa misma API:
   ```
   Nuevo RB --> API Server Linux:8080 --> MySQL
   ```

4. Ambos RBs sincronizados automáticamente

---

### FASE 3: Futuro (Arquitectura Distribuida)
**Objetivo:** Sistema profesional y escalable

```
Cliente 1 (RB Nuevo)  ──┐
Cliente 2 (RB5009)    ──┼─→ API Central ──→ MySQL ──→ Panel Web
Cliente 3 (Futuro RB) ──┘
```

Ventajas:
- Un único punto de verdad (MySQL)
- Fácil agregar más RBs
- Dashboard centralizado
- Reportes y estadísticas
- Integración con facturación

---

## Plan de Acción - Fase 1 Mejorada

### Paso 1: Estructura Modular Correcta

**En RB5009, crear carpeta estructura:**
```
/etc/suspension/
├── config/
│   ├── settings.conf          # Configuración
│   └── suspended_clients.txt   # Lista (actualizada por cron)
├── scripts/
│   ├── suspension_manager.sh   # Add/Remove (Manual)
│   ├── sync_pppoe_ips.sh       # Auto-Update (Cron cada 5min)
│   ├── health_check.sh         # Monitoreo
│   └── backup.sh               # Respaldos
├── logs/
│   ├── suspension.log
│   ├── sync.log
│   └── health.log
└── backups/
    └── clients_backup_*.txt
```

### Paso 2: Scripts Modular

**suspension_manager.sh** (Manual)
- Add/Remove clientes
- Reutilizable desde Fase 2

**sync_pppoe_ips.sh** (Automático - Cron)
- Lee `/etc/suspension/suspended_clients.txt`
- Actualiza IPs en MikroTik
- Logs detallados

**health_check.sh** (Monitoreo)
- Verifica que HTTP server funciona
- Verifica reglas mangle/nat
- Alerta si algo falla

### Paso 3: Preparar para API (Sin cambios ahora)

Usar misma estructura pero:
- `/etc/suspension/suspended_clients.txt` será reemplazado por API call
- Scripts listos para cambio futuro
- Solo 2-3 líneas de código cambiarían

---

## Implementación Fase 1 Mejorada

### Paso 1: Crear estructura
```bash
sudo mkdir -p /etc/suspension/{config,scripts,logs,backups}
```

### Paso 2: Archivo de configuración
**`/etc/suspension/config/settings.conf`:**
```bash
# MikroTik Configuration
ROUTER_IP="10.147.17.11"
ROUTER_USER="admin"

# Suspensión
SUSPENDED_FILE="/etc/suspension/config/suspended_clients.txt"
LOG_DIR="/etc/suspension/logs"

# Sincronización
SYNC_INTERVAL=5  # minutos
```

### Paso 3: Script Manager (Mejorado)

**`/etc/suspension/scripts/suspension_manager.sh`:**
```bash
#!/bin/bash

source /etc/suspension/config/settings.conf

add_client() {
    local user=$1
    echo "$user" >> "$SUSPENDED_FILE"
    sort "$SUSPENDED_FILE" -u -o "$SUSPENDED_FILE"
    logger "Added: $user"
}

remove_client() {
    local user=$1
    sed -i "/^${user}$/d" "$SUSPENDED_FILE"
    logger "Removed: $user"
}

# Ejecutar desde: /etc/suspension/scripts/
# ./suspension_manager.sh add usuario_juan
```

### Paso 4: Script Sync (Cron)

**`/etc/suspension/scripts/sync_pppoe_ips.sh`:**
```bash
#!/bin/bash

source /etc/suspension/config/settings.conf

while IFS= read -r user; do
    # Obtener IP actual
    ip=$(ssh -o StrictHostKeyChecking=no "${ROUTER_USER}@${ROUTER_IP}" \
        "/ppp active print where name=$user" | grep address | awk '{print $NF}')

    if [ -n "$ip" ]; then
        # Actualizar regla en MikroTik
        ssh ... (update rule)
    fi
done < "$SUSPENDED_FILE"
```

### Paso 5: Cron Job
```bash
sudo crontab -e
```

Agregar:
```
*/5 * * * * /etc/suspension/scripts/sync_pppoe_ips.sh >> /etc/suspension/logs/sync.log 2>&1
```

---

## Ventajas de Esta Arquitectura

✓ **Modular** - Cada script tiene una función
✓ **Portable** - Fácil mover a nuevo RB
✓ **Mantenible** - Configuración centralizada
✓ **Escalable** - API se integra sin cambios mayores
✓ **Monitoreable** - Logs organizados
✓ **Respaldable** - Backups automáticos

---

## Transición a Fase 2 (Cuando tengas nuevo RB)

### Solo cambiaría:

1. **Reemplazar archivo por API:**
```bash
# ANTES:
suspended_users=$(cat /etc/suspension/config/suspended_clients.txt)

# DESPUÉS:
suspended_users=$(curl -s http://api-server:8080/api/suspended)
```

2. **Agregar cliente via API:**
```bash
# ANTES:
./suspension_manager.sh add usuario_juan

# DESPUÉS:
curl -X POST http://api-server:8080/api/suspend \
  -d "user=usuario_juan&router=rb5009"
```

3. **Ambos RBs sincronizados:**
```bash
# RB5009
curl http://api-server:8080/api/suspended?router=rb5009

# Nuevo RB
curl http://api-server:8080/api/suspended?router=nuevo_rb
```

---

## Timeline Recomendado

### Semana 1-2 (Ahora)
- Implementar Fase 1 con estructura modular
- Validar que funcione en RB5009
- Crear documentación

### Semana 3-4
- Adquirir nuevo RB
- Configurar como solo PPPoE/Control
- RB5009 como balanceador

### Semana 5-6
- Implementar API en servidor Linux
- Migrar gestión de clientes a API
- Ambos RBs usando misma API

### Semana 7+
- Panel web centralizado
- Reportes y estadísticas
- Integración con facturación

---

## Diagrama de Datos - Fase 1

```
Manual Input
    ↓
./suspension_manager.sh add user
    ↓
/etc/suspension/config/suspended_clients.txt (actualizado)
    ↓
Cron ejecuta sync_pppoe_ips.sh (cada 5 min)
    ↓
Lee suspended_clients.txt
    ↓
Obtiene IP actual de usuario PPPoE
    ↓
Actualiza regla mangle en MikroTik
    ↓
Cliente ve página de suspensión
```

---

## Diagrama de Datos - Fase 2+

```
Web Panel / API
    ↓
API Server (Linux)
    ↓
MySQL Database (Clientes)
    ↓
Webhook → RB5009 + Nuevo RB
    ↓
Ambos sincronizados automáticamente
    ↓
Clientes ven página (donde sea)
```

---

## Checklist Fase 1

- [ ] Crear estructura `/etc/suspension/`
- [ ] Copiar scripts modulares
- [ ] Crear archivo de configuración
- [ ] Instalar en cron
- [ ] Validar funcionamiento
- [ ] Crear backups automáticos
- [ ] Documentar proceso
- [ ] Preparar para API (comentarios en código)

---

## Próximo Paso

¿Implementamos la Fase 1 con esta estructura modular?

Esto te deja todo listo para cuando tengas el nuevo RB sin necesidad de cambios mayores.

**Estado:** Propuesta de Arquitectura
**Versión:** 1.0
**Fecha:** 2025-11-14
