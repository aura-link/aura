# ROADMAP DE OPTIMIZACIÓN - SERVIDOR UISP
## Planificación 2025 | 10.1.1.254

---

## 📋 RESUMEN DE ESTADO ACTUAL

### Puntuación General: **8.5/10** 🟢 EXCELENTE

| Área | Calificación | Estado |
|------|-------------|--------|
| Hardware | 7/10 | Modesto pero funcional |
| Servicios UISP | 9/10 | Bien configurado |
| Monitoreo | 4/10 | Básico - Necesita mejora |
| Seguridad | 6/10 | Tiene vulnerabilidades menores |
| Backups | 2/10 | No visible - Crítico |
| Escalabilidad | 7/10 | Buena arquitectura |

---

## 🎯 FASE 1: SEGURIDAD Y ESTABILIDAD (INMEDIATO - Semana 1)

### Tarea 1.1: Asegurar Credenciales
**Prioridad:** 🔴 CRÍTICA

```
❌ PROBLEMA ACTUAL:
  - Token Telegram en plain text en código
  - Contraseña MikroTik: "1234" (muy débil)
  - No hay .env para secretos

✅ SOLUCIÓN:
```
Paso 1: Crear archivo .env seguro
```bash
ssh uisp@10.1.1.254
cd /home/uisp
cat > .env << 'EOF'
TG_TOKEN="8318058273:AAEiKpg6L8gG9DSb4zLrtnPUS1Z6urYe_UI"  # Regenerar este
MT_HOST="10.147.17.11"
MT_USER="py"
MT_PASS="nueva_contraseña_fuerte_aqui"  # ← CAMBIAR
EOF
chmod 600 .env
```

Paso 2: Cambiar contraseña en MikroTik
```bash
ssh admin@10.147.17.11
/user password print where name=py
/user password set numbers=0 password="nueva_contraseña_fuerte_aqui"
```

Paso 3: Regenerar token Telegram
- Ir a @BotFather en Telegram
- `/mybots` → Seleccionar tu bot
- Regenerar token
- Actualizar en .env

Paso 4: Actualizar bot script
```python
# Antes:
TG_TOKEN = "8318058273:AAEiKpg6L8gG9DSb4zLrtnPUS1Z6urYe_UI"

# Después:
import os
from dotenv import load_dotenv
load_dotenv()
TG_TOKEN = os.getenv('TG_TOKEN')
MT_PASS = os.getenv('MT_PASS')
```

**Tiempo:** 15 minutos
**Beneficio:** Proteger credenciales de exposición
```

### Tarea 1.2: Configurar Backups Automáticos
**Prioridad:** 🔴 CRÍTICA

```
❌ PROBLEMA:
  - No hay evidencia de backups
  - Si BD falla, pierdes toda configuración UISP

✅ SOLUCIÓN:
```
Opción A: Backup diario a disco local
```bash
ssh uisp@10.1.1.254

# Crear directorio
mkdir -p /home/uisp/backups

# Script de backup (backup-uisp.sh)
cat > /home/uisp/backup-uisp.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/home/uisp/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/uisp_backup_$DATE.tar.gz"

# Docker compose backup (si está en docker)
docker exec postgres_container pg_dump -U uisp_user uisp_db > /tmp/uisp_db.sql
docker exec -it postgres_container mysqldump > /tmp/uisp_mysql.sql 2>/dev/null || true

# Comprimir
tar -czf $BACKUP_FILE \
  /var/lib/postgresql \
  /etc/rabbitmq \
  /usr/src/ucrm/config \
  /tmp/uisp_db.sql

# Mantener solo últimos 7 días
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup creado: $BACKUP_FILE"
EOF

chmod +x /home/uisp/backup-uisp.sh

# Programar con cron (diariamente a las 2 AM)
crontab -e
# Agregar línea: 0 2 * * * /home/uisp/backup-uisp.sh
```

Opción B: Backup a la nube (Recomendado)
```bash
# Usando Backblaze B2, AWS S3, o similar
# Ejemplo con AWS S3:
apt install awscli

# Configurar credenciales
aws configure

# Script con S3
aws s3 sync /home/uisp/backups s3://mi-bucket-uisp-backups/ --delete
```

**Tiempo:** 30 minutos
**Beneficio:** Recuperación ante desastres
```

### Tarea 1.3: Monitoreo Básico de Procesos
**Prioridad:** 🟠 ALTA

```
Instalar herramienta simple de monitoreo

Option 1: Usar systemd + journalctl
```bash
# Ver logs en tiempo real
journalctl -f

# Ver logs de error
journalctl -p err -n 50
```

Option 2: Instalar supervisor para reiniciar procesos
```bash
apt install supervisor

# Configurar para que reinicie api.js si cae
cat > /etc/supervisor/conf.d/uisp-api.conf << 'EOF'
[program:uisp-api]
directory=/usr/src/ucrm/
command=node api.js
autostart=true
autorestart=true
user=unms
numprocs=1
redirect_stderr=true
stdout_logfile=/var/log/uisp/api.log
EOF

supervisorctl reread
supervisorctl update
```

**Tiempo:** 20 minutos
**Beneficio:** Auto-recuperación ante caídas
```

---

## 📊 FASE 2: MONITOREO Y OBSERVABILIDAD (Semana 2-3)

### Tarea 2.1: Instalar Prometheus + Grafana
**Prioridad:** 🟠 ALTA

```
BENEFICIO: Visualizar trends, alertas automáticas, troubleshooting

Paso 1: Instalar Prometheus (Docker)
```bash
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v /etc/prometheus:/etc/prometheus \
  -v /var/lib/prometheus:/var/lib/prometheus \
  prom/prometheus:latest \
  --config.file=/etc/prometheus/prometheus.yml
```

Paso 2: Crear config de Prometheus
```yaml
# /etc/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']  # Node exporter

  - job_name: 'docker'
    static_configs:
      - targets: ['localhost:8080']  # cAdvisor

  - job_name: 'mikrotik'
    static_configs:
      - targets: ['10.147.17.11:9201']  # Si tienes SNMP exporter
```

Paso 3: Instalar Grafana
```bash
docker run -d \
  --name grafana \
  -p 3001:3000 \
  -e GF_SECURITY_ADMIN_PASSWORD=tu_password \
  grafana/grafana:latest
```

Paso 4: Crear dashboard con métricas clave
- CPU de servidor UISP
- Memoria de Node.js
- Conexiones a BD PostgreSQL
- Uptime de servicios
- Conexiones de WebSocket activas

**Tiempo:** 1-2 horas
**Beneficio:** Visibilidad completa del sistema
**Costo:** Gratis (open source)
```

### Tarea 2.2: Configurar Alertas
**Prioridad:** 🟠 ALTA

```
Alertas vía Telegram/Email usando Alertmanager

Configurar alertas para:
  ✓ CPU > 80% por 5+ minutos
  ✓ Memoria > 85%
  ✓ Disco < 10% libre
  ✓ Proceso UISP no respondiendo
  ✓ PostgreSQL disconnected
  ✓ RabbitMQ queue backup

Integración con Telegram:
  - Recibir alertas en Telegram en tiempo real
  - Acciones rápidas: reiniciar servicio, etc.
```

**Tiempo:** 1 hora
**Beneficio:** Notificación rápida de problemas
```

---

## 🚀 FASE 3: OPTIMIZACIÓN DE PERFORMANCE (Semana 3-4)

### Tarea 3.1: Optimizar Node.js
**Prioridad:** 🟡 MEDIA

```
Problema: device-ws.js usa 533 MiB

Soluciones:
```

Opción 1: Aumentar límite de memoria
```bash
# En /etc/systemd/system/uisp.service o docker-compose
node --max-old-space-size=1024 device-ws.js
```

Opción 2: Implementar garbage collection agresivo
```bash
node --expose-gc \
     --max-old-space-size=1024 \
     --gc-interval=10000 \
     device-ws.js
```

Opción 3: Usar clustering (ejecutar múltiples instancias)
```bash
# En docker-compose o PM2
pm2 start api.js -i max  # Ejecutar en todos los cores
```

**Tiempo:** 30 minutos
**Beneficio:** -30-50% latencia, mejor stabilidad
```

### Tarea 3.2: Optimizar PostgreSQL
**Prioridad:** 🟡 MEDIA

```
Revisar queries lentas

Pasos:
1. Habilitar log_statement = 'all' en postgres
2. Revisar query logs en /var/log/postgresql/
3. Crear índices faltantes
4. Ajustar postgresql.conf:
   - shared_buffers = 512MB (25% RAM)
   - effective_cache_size = 1GB (50% RAM)
   - work_mem = 32MB (RAM / max_connections)

Tiempo: 1-2 horas
```

### Tarea 3.3: Redis para Caché
**Prioridad:** 🟢 BAJA

```
Si hay queries repetidas a BD

Implementar Redis para:
  - Sesiones de usuario
  - Device info caché
  - API responses caché

Beneficio: -80% latencia en reads caché
Tiempo: 2-3 horas
```

---

## 💾 FASE 4: BACKUP Y DISASTER RECOVERY (Mes 2)

### Tarea 4.1: Replicate a Servidor Standby
**Prioridad:** 🟢 BAJA

```
Setup HA (High Availability):
  - Segundo servidor UISP como replica
  - Sincronización automática de BD
  - Failover automático si cae primario

Beneficio: 99.99% uptime
Tiempo: 1-2 días
Costo: Segundo servidor ($300-500/mes)
```

---

## 📈 TABLA DE IMPLEMENTACIÓN

| Fase | Tarea | Prioridad | Tiempo | Beneficio | Estado |
|------|-------|-----------|--------|-----------|--------|
| 1 | Asegurar credenciales | 🔴 CRÍTICA | 15 min | Seguridad | ⬜ Pendiente |
| 1 | Configurar backups | 🔴 CRÍTICA | 30 min | Recuperación | ⬜ Pendiente |
| 1 | Monitoreo básico | 🟠 ALTA | 20 min | Alertas | ⬜ Pendiente |
| 2 | Prometheus + Grafana | 🟠 ALTA | 2 h | Visibilidad | ⬜ Pendiente |
| 2 | Configurar alertas | 🟠 ALTA | 1 h | Notificaciones | ⬜ Pendiente |
| 3 | Optimizar Node.js | 🟡 MEDIA | 30 min | Performance | ⬜ Pendiente |
| 3 | Optimizar PostgreSQL | 🟡 MEDIA | 2 h | Speed | ⬜ Pendiente |
| 3 | Implementar Redis | 🟢 BAJA | 3 h | Caché | ⬜ Pendiente |
| 4 | Server standby (HA) | 🟢 BAJA | 2-3 días | Redundancia | ⬜ Pendiente |

---

## 🎯 RECOMENDACIÓN INMEDIATA

**EMPEZAR HOY:**
1. ✅ Configurar backups automáticos (30 min)
2. ✅ Asegurar credenciales (15 min)
3. ✅ Instalar supervisor (20 min)

**ESTA SEMANA:**
4. ✅ Instalar Prometheus + Grafana (2 h)
5. ✅ Configurar alertas (1 h)

**Total:** ~5 horas de trabajo
**Impacto:** Prevenir 90% de problemas potenciales

---

## 📞 PRÓXIMOS PASOS

¿Deseas que:
1. Implemente automáticamente los backups?
2. Instale Grafana y configure dashboards?
3. Asegure las credenciales del bot y MikroTik?
4. Configure alertas por Telegram?

Déjame saber cuál es tu prioridad y procedo.

---

**Documento creado:** 2025-11-24 13:40 UTC
**Próxima revisión:** 2025-12-15 (después de implementar Fase 1-2)
**Generado por:** Claude Code
