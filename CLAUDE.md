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
- 248 sitios NMS endpoint (1:1 con CRM, 100% enlazados)
- 28 sitios NMS infraestructura
- **CRM API Key** (X-Auth-App-Key): usa el token del .env, NO el de postgres
- **Secuencias PostgreSQL**: se desincronizaron tras migración. Si da error 500 al crear suscriptor, resetear con: `SELECT setval('ucrm.SEQUENCE_NAME', (SELECT MAX(col) FROM ucrm.TABLE));`
- Secuencias ya corregidas (2026-02-15): user, client, client_contact, service, invoice, invoice_item, payment, entity_log, email_log, y 10 más

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

### 4. CRM 500 Error al crear suscriptores (2026-02-15)
**Causa raíz**: Secuencias auto-increment de PostgreSQL desincronizadas tras migración/restauración de BD. Al crear un suscriptor, INSERT fallaba con `UniqueConstraintViolationException` porque la secuencia generaba IDs que ya existían.
**Solución**: Resetear todas las secuencias del schema `ucrm` con `setval()` al MAX de cada tabla.
- Primera vez: `user_user_id_seq` (1002 vs max 1271)
- Segunda vez: `client_contact_client_contact_id_seq` (3 vs max 270)
- Se corrigieron ~20 secuencias en total para prevenir futuros errores.

### 5. Dispositivos fantasma en UISP (2026-02-15)
**Causa**: Antenas que intentaron conectar con key de encriptación desincronizada. UISP registraba la MAC pero el handshake fallaba ("Decryption failed for device using device key"). Quedaban como dispositivos sin nombre, sin IP, sin UUID válido.
**Solución**: DELETE directo en PostgreSQL: `DELETE FROM unms.device WHERE (name IS NULL OR name = '') AND ip IS NULL AND connected = false AND authorized = false;` — eliminó 20 fantasmas.
**Prevención**: Si una antena no conecta a UISP pero la key es correcta, revisar logs de `app-device-ws-1` por "Decryption failed". Solución: eliminar el dispositivo fantasma de la BD y reiniciar udapi-bridge en la antena.

### 6. Antena 10.10.1.139 no conectaba a UISP (2026-02-15)
**Causa**: UISP tenía guardada una key vieja para MAC 28:70:4E:A8:16:99. La antena (Guadalupe Llamas, LiteBeam M5) se conectaba pero UISP no podía descifrar → loop de "connection established → 30s inactivity → reconnecting".
**Solución**: Eliminar dispositivo fantasma via API (`DELETE /devices/{id}`) y reiniciar udapi-bridge. Tras eso UISP la redescubre con key nueva.

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

## Aura Bot - Agente IA Telegram

### Ubicacion
- **Directorio**: `C:\claude2\aura-bot\`
- **Bot Telegram**: @auralinkmonitor_bot (ID: 8318058273)
- **Admin Telegram**: Carlos Eduardo Valenzuela Rios (ID: 1900491583)

### Stack
- Python 3.13 + python-telegram-bot 21.9 + Anthropic SDK + aiohttp + librouteros + aiosqlite + rapidfuzz
- Claude Sonnet 4 para respuestas IA (~$0.02/consulta, ~$18 USD/mes estimado con 30 consultas/dia)

### Integraciones funcionando
- **UISP NMS**: dispositivos, sitios, outages (API v2.1 con token)
- **UISP CRM**: clientes, servicios, facturas, saldos
- **MikroTik**: sesiones PPPoE, ping (RouterOS API puerto 8728 via librouteros)
- **Claude AI**: tool use con 9 herramientas, system prompt dinamico por rol

### Proteccion de costos (3 capas)
1. **Pre-filtro local** (`src/utils/filter.py`): keywords relevantes a ISP, rechaza mensajes off-topic sin llamar API
2. **Rate limiting**: 15 consultas AI/dia por cliente (admins sin limite)
3. **System prompt**: instruye a Claude responder breve y rechazar temas no relacionados

### Comandos implementados
| Rol | Comandos |
|-----|----------|
| Cliente | /misaldo, /miservicio, /miconexion, /reportar, /soporte, /vincular |
| Admin | /red, /clientes, /buscar, /dispositivos, /pppoe, /diagnostico, /caidas |
| Todos | /start, /help, /menu + mensajes libres en español via Claude AI |

### Archivos clave del bot
| Archivo | Funcion |
|---------|---------|
| `src/main.py` | Entry point |
| `src/config.py` | Carga .env |
| `src/bot/app.py` | Telegram Application + handlers |
| `src/bot/handlers/conversation.py` | Mensajes libres → Claude AI (con filtro + rate limit) |
| `src/ai/claude_client.py` | Anthropic SDK wrapper con tool use loop |
| `src/ai/system_prompt.py` | System prompt dinamico por rol |
| `src/ai/tools.py` | 9 tool definitions para Claude |
| `src/ai/tool_executor.py` | Despacha tool calls → UISP/MikroTik |
| `src/integrations/uisp_nms.py` | UISP NMS client |
| `src/integrations/uisp_crm.py` | UISP CRM client |
| `src/integrations/mikrotik.py` | MikroTik RouterOS API |
| `src/utils/filter.py` | Pre-filtro de relevancia |

### Ejecucion
- **Local**: `cd aura-bot && PYTHONPATH=. python -m src.main`
- **Docker**: `docker compose up -d --build`
- **Python correcto en Windows**: `"/c/Users/eduar/AppData/Local/Microsoft/WindowsApps/python3.13.exe"`

### Deploy en VPS
- **Ubicacion VPS**: `/root/aura-bot/`
- **Container**: `aura-bot` (restart: unless-stopped)
- **Rebuild**: `ssh vps "cd /root/aura-bot && docker compose up -d --build"`
- **Logs**: `ssh vps "docker logs aura-bot --tail 50"`
- **Restart**: `ssh vps "docker compose -f /root/aura-bot/docker-compose.yml restart"`
- **Actualizar archivos**: `scp -r C:/claude2/aura-bot/src C:/claude2/aura-bot/.env vps:/root/aura-bot/`

### Sistema de Monitoreo Proactivo (implementado 2026-02-14)
El bot incluye un monitor de red en background que:
- Detecta caídas de infraestructura cada 2 min (polling UISP)
- Identifica clientes afectados via jerarquía de sitios (zone_mapping)
- Envía notificaciones Telegram automáticas (con anti-spam 30 min cooldown)
- Anti-flap: confirma caída solo si persiste 2 polls consecutivos
- Responde automáticamente durante incidentes/mantenimiento (sin llamar Claude, $0)

**Archivos del monitor:**
| Archivo | Funcion |
|---------|---------|
| `src/monitoring/__init__.py` | Package |
| `src/monitoring/monitor.py` | Background poll loop + anti-flap |
| `src/monitoring/zones.py` | Mapeo infra → clientes desde UISP sites |
| `src/monitoring/notifications.py` | Templates + envío Telegram + anti-spam |
| `src/monitoring/maintenance.py` | CRUD ventanas de mantenimiento |
| `src/bot/handlers/monitoring_admin.py` | /zonas, /incidentes, /monitor, /mantenimiento |

**Tablas DB nuevas:** device_state, zone_mapping, incidents, maintenance_windows, notification_log

**Comandos admin nuevos:** /zonas, /incidentes, /monitor, /mantenimiento

**Config vars:** MONITOR_ENABLED, MONITOR_INTERVAL (120s), NOTIFICATION_COOLDOWN (1800s), ZONE_REFRESH_INTERVAL (900s)

### Estado del bot (2026-02-15)
- ✅ Desplegado en VPS (217.216.85.65) con Docker
- ✅ Botones inline funcionando
- ✅ Claude AI responde con datos reales de UISP y MikroTik
- ✅ Consulta de saldos, dispositivos offline, sesiones PPPoE
- ✅ Pre-filtro y rate limiting implementados
- ✅ Monitor de red corriendo (interval=120s, 28 zonas, 184+ endpoints mapeados)
- ✅ Comandos /zonas, /incidentes, /monitor, /mantenimiento funcionando
- ⚠️ Pendiente: pruebas de diferenciacion admin vs cliente
- ⚠️ Pendiente: Haiku da error 529 (overloaded), usando Sonnet por ahora

## Auditoría UISP (2026-02-15)

### Análisis cruzado PPPoE ↔ CRM ↔ NMS
- **248/248 CRM clientes enlazados a endpoints NMS** — 100% cobertura
- **0 endpoints huérfanos** (se eliminaron 4: Olivia Cumbre, Alma Gloria, Enrique Pulido, Tule Mabel)
- **Duplicado CRM #254 (Kareli Meza Coco)** eliminado ($0 balance, sin servicio)
- **Naming consistente**: NMS usa "Zona, Nombre" / CRM usa "Nombre Zona" — todos hacen match

### PPPoE
- 250 secrets total: 219 habilitados, 31 deshabilitados (suspendidos)
- ~211 sesiones activas
- 6 sesiones "clienteprueba" (secret compartido para instalaciones nuevas)
- 18 clientes en perfil "Morosos" conectados (revisar)

### Clienteprueba identificados
| IP | Cliente | Estado UISP |
|----|---------|-------------|
| 10.10.1.119 | Jose Nicolas Mariscal | En UISP, activo |
| 10.10.1.133 | Calderon | En UISP, activo |
| 10.10.1.212 | Oscar Eduardo Pano | NO en UISP |
| 10.10.1.237 | Briana Nava | En UISP, unauthorized |
| 10.10.1.195 | Erick Cumbre | En UISP, unauthorized |
| 10.10.1.170 | Desconocido (SSID: Wisp B&V Recursos Sur) | NO en UISP |

### Limpieza realizada
- Eliminados 20 dispositivos fantasma (MACs sin nombre/IP/UUID, key desincronizada)
- Eliminados 4 endpoints NMS huérfanos
- Eliminado 1 duplicado CRM
- Corregidas ~20 secuencias PostgreSQL del CRM

## Pendientes

- [x] Asignar antenas de clientes a suscriptores CRM — **100% completado (248/248)**
- [ ] Revisar antenas 10.10.1.45 y 10.10.1.162 (fallaron SSH)
- [x] Agente IA para UISP (Telegram Bot + Python) — implementado como Aura Bot
- [x] Deploy Aura Bot en VPS (Docker) — corriendo en 217.216.85.65
- [x] Sistema de monitoreo proactivo — implementado y corriendo
- [ ] Crear PPPoE secrets individuales para 6 clienteprueba
- [ ] Revisar 18 morosos conectados (perfil Morosos en MikroTik)
- [ ] Probar diferenciacion admin/cliente en system prompt
- [ ] Probar vinculacion de clientes (/vincular con fuzzy matching)
- [ ] Renombrar bot en BotFather a "Aura - AURALINK"
- [ ] ~11 dispositivos desconectados con nombre pendientes de revisar
- [ ] 3 dispositivos unauthorized con nombre: Rafael Rodriguez, Eliseo Hernandez, Miriam Cumbre

## Estado Actual (2026-02-15)
- **202 dispositivos** en UISP (tras limpieza): 185 activos, 11 desconectados con nombre, 3 unauthorized, 3 unauthorized con nombre
- **248 CRM ↔ 248 NMS endpoints** enlazados 1:1
- **SSH sin contraseña** configurado para VPS, Aura y MikroTik
- **Aura Bot** en produccion en VPS con Docker (container: aura-bot)
- **Monitor de red** corriendo (28 zonas, polling cada 2 min)
- **Certificado SSL**: Let's Encrypt RSA válido hasta mayo 2026 (cadena completa, verificado OK desde servidor)
