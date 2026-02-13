# AURALINK WISP - Memoria Operativa

## Proyecto
Migración de UISP desde servidor local (laptop 10.1.1.254) a VPS en la nube (Contabo).

## Infraestructura

### VPS - UISP Cloud
- **IP**: 217.216.85.65 (Contabo)
- **DNS**: server.auralink.link → 217.216.85.65
- **OS**: Debian/Ubuntu con Docker
- **UISP**: v3.0.151 (Docker containers)
- **SSH**: `ssh vps` (root, key auth configurado)
- **ZeroTier IP**: 10.147.17.92 (red BalanceadorTomatlan - 9f77fc393ecd131f)

### Contenedores Docker UISP
- unms-nginx (OpenResty, puerto 443)
- unms-api
- app-device-ws-1 a 5 (WebSocket para dispositivos)
- unms-postgres (base de datos)
- unms-rabbitmq
- unms-siridb
- unms-fluentd
- unms-netflow (puerto 2055)
- ucrm (CRM)

### Servidor Aura (local)
- **IP**: 10.147.17.155
- **User**: aura (sudo password: 1234)
- **SSH**: `ssh aura` (key auth via ProxyJump por VPS)
- **Rol**: Jump host para acceder a antenas

### MikroTik Balanceador
- **IP**: 10.147.17.11
- **User**: admin (password: 1234)
- **SSH**: `ssh mikrotik` (key auth via ProxyJump por VPS)
- **Función**: PPPoE server, ECMP load balancing con múltiples Starlinks
- **Interfaz PPPoE**: SFP-LAN
- **~213 clientes PPP activos**

### MikroTik La Gloria
- **IP**: 10.144.247.27
- **User**: admin (password: Izan2021)

### Antenas Ubiquiti (clientes)
- **Rango IP**: 10.10.1.x/24 (asignado por PPPoE)
- **Gateway**: 10.10.0.1 (MikroTik)
- **Firmware**: XW.v6.2.0 (airOS, julio 2019)
- **OpenSSL**: 1.0.0 (libssl.so.1.0.0)
- **Credenciales SSH**: ubnt/Auralink2021 o AURALINK/Auralink2021 o ubnt/Casimposible*7719Varce*1010
- **SSH requiere**: `-o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa`
- **Total Ubiquiti en PPP**: 184
- **Total en UISP**: 213 (incluye infraestructura)

### Infraestructura de red (10.1.1.x)
- Equipos de infraestructura (APs, bridges, routers) en la red 10.1.1.x
- Estos se conectan directamente al UISP (no via PPPoE)

## UISP - Datos Importantes

### API
- **Base URL**: https://server.auralink.link/nms/api/v2.1/
- **Token**: Se obtiene de la tabla `unms.token` en PostgreSQL
- **Obtener token**: `docker exec unms-postgres psql -U postgres -d unms -t -A -c "SELECT token FROM \"unms\".\"token\" LIMIT 1;"`
- **Endpoints clave**:
  - GET /devices - listar dispositivos
  - POST /devices/{id}/authorize - autorizar dispositivo (body: {"siteId": "..."})
  - GET /sites - listar sitios

### Connection String UISP
```
wss://server.auralink.link:443+sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV+allowSelfSignedCertificate
```

### Certificado SSL
- Let's Encrypt RSA (issuer R13) en `/home/unms/data/cert/live.crt` y `live.key`
- Se cambió de ECDSA a RSA para compatibilidad con firmware viejo

### CRM
- 248 clientes / 248 servicios
- 279 sitios NMS (18 activos, 261 inactivos)

## Problemas Resueltos

### 1. Solo 60 dispositivos aparecían en UISP (de ~200+)
**Causa raíz**: El proceso `udapi-bridge` (NO infctld) es el que conecta al UISP. Este proceso leía la configuración de `/tmp/running.cfg` que tenía el URI del servidor viejo (`wss://10.1.1.254:443+OLD_KEY`). Aunque `/tmp/system.cfg` fue actualizado con el nuevo URI, `udapi-bridge` no lo leía.

**Solución**:
1. Eliminar `/tmp/running.cfg` en cada antena
2. Matar el proceso hijo `{exe} /bin/udapi-bridge` (kill -9)
3. El proceso padre lo respawna y el nuevo hijo lee de `system.cfg`

**Script**: `fix-final.sh` - procesó 184 antenas (151 corregidas, 31 ya OK, 2 fallaron)

### 2. SSH sin contraseña
- VPS: SSH key auth desde Windows
- Aura: SSH key auth via ProxyJump por VPS
- MikroTik: SSH key importada via `/user/ssh-keys/import`
- Config SSH en `~/.ssh/config` con aliases: vps, aura, mikrotik

### 3. Certificado ECDSA incompatible
- airOS v6.2.0 no soporta ECDSA
- Se generó certificado RSA con Let's Encrypt

## Archivos Importantes en este Repositorio

| Archivo | Descripción |
|---------|-------------|
| `credencialesaccesos.txt` | Credenciales de todos los equipos |
| `fix-final.sh` | Script definitivo para corregir antenas (mata udapi-bridge) |
| `fix-running-cfg.sh` | Script v1 (solo running.cfg, no suficiente) |
| `fix-running-cfg2.sh` | Script v2 (running.cfg + infctld, no suficiente) |
| `restart-agents.sh` | Script para reiniciar infctld en todas las antenas |
| `uisp-key-update.sh` | Script para actualizar key UISP en system.cfg |
| `ubnt_ppp_ips.txt` | 184 IPs de antenas Ubiquiti en PPPoE |
| `uisp_ips.txt` | IPs de dispositivos en UISP |
| `truly_missing.txt` | IPs que estaban en PPP pero no en UISP |
| `ppp_raw.txt` | Dump completo de conexiones PPP del MikroTik |
| `analyze_ppp.py` | Script Python para analizar MACs de PPP |
| `missing_ubnt.txt` | IPs Ubiquiti que no aparecían en UISP |

## Datos Técnicos airOS

- **Config persistente**: `/tmp/system.cfg` (se guarda a flash con `cfgmtd -w -p /etc/`)
- **Config runtime**: `/tmp/running.cfg` (si existe, `udapi-bridge` la usa en lugar de system.cfg)
- **Proceso UISP**: `udapi-bridge` (hijo con prefijo `{exe}`) - es el que conecta via WebSocket
- **Proceso informd**: `infctld` - controlador inform (menos relevante para conexión UISP)
- **Logs UISP**: `/var/log/unms.log`
- **Logs sistema**: `/var/log/messages`
- **Guardar config**: `cfgmtd -w -p /etc/`
- **MAC Ubiquiti prefixes**: 24:5A:4C, 28:70:4E, 60:22:32, 9C:05:D6, 0C:EA:14, E4:38:83, 70:A7:41, 44:D9:E7, 74:83:C2, 04:18:D6, AC:84:C6, 78:8A:20

## Nginx UISP - Notas

- El entrypoint `/entrypoint.sh` regenera TODA la config nginx desde templates al reiniciar
- Templates en: `/usr/local/openresty/nginx/templates/snippets/`
- Los cambios a la config nginx dentro del contenedor se pierden al reiniciar
- Para cambios persistentes: modificar los templates, NO los archivos de config
- SSL config template: `templates/snippets/ssl-cert.conf`
- Actualmente: `ssl_protocols TLSv1.2;` (solo TLS 1.2)

## Pendientes

- [ ] Asignar ~170+ antenas de clientes a sus suscriptores CRM (manual por el usuario)
- [ ] Revisar antenas 10.10.1.45 y 10.10.1.162 (fallaron SSH)
- [ ] Revisar 5 dispositivos en estado "unknown"
- [ ] Agente IA para UISP (Telegram Bot + Python, deferred)
- [ ] ~60 dispositivos desconectados que deberían reconectarse gradualmente

## Estado Actual (2026-02-13)
- **213 dispositivos** en UISP (148 activos, 60 desconectados, 5 unknown)
- **0 unauthorized** (todos autorizados)
- **SSH sin contraseña** configurado para VPS, Aura y MikroTik
