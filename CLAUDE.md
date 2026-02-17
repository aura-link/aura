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
- **SSH**: `ssh vps "ssh -o StrictHostKeyChecking=no admin@10.147.17.11 '...'"` (via VPS jump)
- **Modelo**: RB5009UG+S+ (RouterOS 7.19.2 stable)
- **Función**: PPPoE server, PCC load balancing con múltiples WANs
- **Interfaz PPPoE**: SFP-LAN, Pool 10.10.1.2-254
- **~198 sesiones PPPoE activas**, 255 secrets total
- **WANs activas**: WAN1 (Starlink2/ether1), WAN2 (Sergio/ether2), WAN5 (StarlinkMini/ether3), WAN6 (StarlinkTotin/ether4), WAN7 (Chuy1/ether5), WAN8 (Chuy2/ether6), WAN9 (StarlinkAurora/ether7), WAN10 (Chaviton/ether8)
- **WANs caidas**: WAN3 (Presidencia40), WAN4 (Presidencia169)
- **PCC**: Per-Connection Classifier src-address:7/x distribuyendo en 8 WANs activas
- **QoS**: CAKE queue discipline por WAN + priority queues (ICMP/ACK p1, DNS/Gaming/VoIP p2, VideoCall/Chat p3, Video p6, Social p7)
- **Morosos**: perfil "Morosos" (64k/64k) + address-list + firewall drop

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
- 261 clientes / 262 servicios (actualizado 2026-02-15 noche)
- 225 sitios NMS endpoint (225 enlazados a CRM, 37 servicios sin enlace NMS)
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

### 7. 17 antenas con "Decryption failed using master key" (2026-02-15 noche)
**Causa raíz (doble)**:
1. El script `uisp-key-update.sh` puso `+allowSelfSignedCertificate` en el URI, pero UISP v3.0.151 espera `+allowUntrustedCertificate`. Esto causaba que la encriptación inicial fallara para antenas nuevas.
2. Algunas antenas tenían **device-specific keys viejas** en su `system.cfg` (de una sesión anterior). Al eliminar las entradas de la BD, UISP no reconocía esas keys.

**Síntomas**: Logs mostraban `"Decryption failed for device MAC using master key"` en los contenedores `app-device-ws-*`. Las antenas estaban en PPPoE (internet funcionaba) pero NO aparecían en UISP.

**Solución aplicada**:
1. Actualizar `system.cfg` en cada antena: reemplazar toda la URI con `wss://server.auralink.link:443+sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV+allowUntrustedCertificate`
2. Guardar a flash: `cfgmtd -w -p /etc/`
3. Eliminar entradas fantasma de la BD: `DELETE FROM unms.device WHERE (name IS NULL OR name = '') AND ip IS NULL AND connected = false AND authorized = false;`
4. Reiniciar udapi-bridge (matar proceso hijo)

**Resultado**: Decryption errors eliminados. Key exchange completa. Pero las 17 antenas tienen **RPC timeout** (`"RPC request timeouted: cmd"`) que impide que UISP obtenga la info del dispositivo. Esto es un problema separado que puede ser de compatibilidad firmware o resolverse con tiempo.

**Antenas afectadas**: 10.10.1.95, .67, .249, .98, .88, .216, .160, .86, .159, .149, .245, .194, .162, .169, .112, .226, .62, .124

**Scripts**: `fix-masterkey-all.sh`, `fix-restart-all.sh`, `fix-flag-all.sh`

**Dato clave**: Las antenas que SÍ funcionan tienen device-specific keys únicas (terminan en `AAAAA`) en su URI, asignadas automáticamente por UISP tras key exchange exitoso. El flag correcto es `+allowUntrustedCertificate`, NO `+allowSelfSignedCertificate`.

### 8. Dispositivo rogue "Elizabeth Pilitas" (2026-02-15 noche)
**Causa**: Antena LiteBeam M5 (MAC 60:22:32:b2:c6:2c) con IP pública 12.13.3.155/22, conectada a SSID "WISP B&V 5G" (otro ISP). Se registró en UISP con connection string de AURALINK pero no pertenece a la red.
**Solución**: Eliminada via API junto con su sitio huérfano "Pilitas".

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
| `cleanup_uisp.py` | Script Python para limpiar fantasmas, unknowns y duplicados desconectados via API |
| `delete_phantoms.py` | Script Python para eliminar dispositivos fantasma específicos por UUID via API |
| `reboot-fixed.sh` | Script bash para reiniciar masivamente las 151 antenas corregidas |
| `fix-masterkey-all.sh` | Script para forzar master key + flag correcto en 18 antenas |
| `fix-restart-all.sh` | Script para reiniciar udapi-bridge con config correcta en 18 antenas |
| `fix-flag-all.sh` | Script para cambiar allowSelfSignedCertificate→allowUntrustedCertificate |
| `fix-udapi-19.sh` | Script para fix masivo de udapi-bridge (rm running.cfg + kill) |
| `cross_reference.py` | Script para cruce PPPoE ↔ UISP por MAC e IP |

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
- ✅ Sistema de cobranza automatizada implementado (2026-02-16)

### Sistema de Cobranza Automatizada (implementado 2026-02-16)
El bot incluye un sistema de cobranza que:
- Envia avisos automaticos de factura (dia 1), recordatorio (dia 3), advertencia (dia 7)
- Suspende morosos automaticamente (dia 8) en MikroTik + CRM
- Recibe fotos de comprobantes → Claude Vision analiza → auto-registra pago en CRM
- Pagos en efectivo requieren aprobacion del admin via botones inline
- Fraude: 2 advertencias, al 3er reporte falso = suspension automatica
- Reactivacion: restaura perfil MikroTik + servicio CRM + notifica cliente
- Comprobantes guardados en `data/receipts/` (Docker volume)

**Archivos del billing:**
| Archivo | Funcion |
|---------|---------|
| `src/billing/__init__.py` | Package |
| `src/billing/scheduler.py` | Loop diario: avisa dia 1/3/7, suspende dia 8 |
| `src/billing/payments.py` | Analisis IA de comprobantes, registro CRM, fraude |
| `src/billing/receipt_storage.py` | Guarda imagenes en disco |
| `src/bot/handlers/receipts.py` | Handler de fotos de Telegram |
| `src/bot/handlers/billing_admin.py` | /pagos, /morosos, /reactivar |

**Tablas DB nuevas:** payment_reports, billing_notifications, fraud_strikes, suspension_log

**Comandos nuevos:** /pagos (admin), /morosos (admin), /reactivar (admin)

**Comandos admin:** /pagos, /morosos, /reactivar, /cobranza (trigger manual)

**Config vars:** BILLING_ENABLED, BILLING_DAY_INVOICE (1), BILLING_DAY_REMINDER (3), BILLING_DAY_WARNING (7), BILLING_DAY_SUSPEND (8), RECONNECTION_FEE (80), RECEIPT_STORAGE_PATH, BILLING_START_MONTH (2026-04)

**Características clave:**
- **Self-recovery**: si el bot estuvo caído en dia de acción, al reiniciar ejecuta todas las acciones pendientes del mes
- **Todos los clientes**: itera TODOS los clientes CRM con planes facturables (no solo vinculados a Telegram)
- **Reconexion $80**: clientes suspendidos ven total necesario (deuda + $80), el handler valida que el monto cubra la deuda
- **Duplicados**: detecta comprobantes repetidos por referencia y por monto reciente (24h)
- **Admin ve comprobante**: botón "Ver comprobante" en /pagos envía la foto
- **Trigger manual**: /cobranza aviso|recordatorio|advertencia|suspender
- **BILLING_START_MONTH=2026-04**: no hace nada hasta abril (marzo es mes de setup)

**CRM API endpoints usados:**
| Endpoint | Metodo | Funcion |
|----------|--------|---------|
| `/invoices?clientId=X&statuses[]=1` | GET | Facturas impagas |
| `/payments` | POST | Registrar pago |
| `/payments/{id}` | DELETE | Reversar pago |
| `/clients/services/{id}` | PATCH | Suspender (status=3) / Activar (status=1) |

**MikroTik:** suspend_client() cambia perfil a "Morosos", unsuspend_client() restaura perfil original

## Auditoría MikroTik RB5009 (2026-02-17)

### Problemas encontrados y corregidos

**CRITICO 1 — Script morosos-on-up roto:**
- `/ppp active get [find where name=$usr] profile` no funciona en RouterOS 7
- Corregido a: `/ppp secret get [find where name=$usr] profile`
- Address-list "morosos" ahora se puebla correctamente con 14 clientes activos

**CRITICO 2 — Firewall input chain abierta:**
- Solo tenia reglas para forward, no habia drop en input
- Agregadas 7 reglas: accept established/related, allow ICMP/DNS/DHCP desde LAN, drop-all al final

**CRITICO 3 — Scripts check-WAN* sin permisos:**
- Netwatch creaba schedulers con policy limitada, scripts fallaban con "not enough permissions"
- Corregido: `dont-require-permissions=yes` en 7 scripts (check-WAN1,3,4,5,6,7,9)
- Resultado: auto-recovery de WANs funciona correctamente

**CRITICO 4 — PCC completamente no funcional:**
- TODAS las rutas PCC estaban deshabilitadas, trafico iba solo por ECMP (3 WANs)
- Habilitadas rutas PCC para WAN1,2,5,6,7,8,9 — trafico ahora distribuido en 8 WANs

**ALTA — WAN7/WAN8 con IPs y gateways obsoletos:**
- ISPs cambiaron subnets: WAN7 192.168.12.x→192.168.101.x, WAN8 192.168.11.x→192.168.100.x
- Eliminadas IPs estaticas viejas, actualizados gateways PCC y netwatch
- WAN8: gateway no responde ICMP → netwatch monitorea 8.8.8.8 con src-address binding
- WAN8 PCC route: `check-gateway=none` (por bloqueo ICMP del ISP)

**MEDIA — Mangle WAN9 deshabilitado:**
- 3 reglas mangle (PCC, Route-to, Download) estaban deshabilitadas con WAN9 activa
- Habilitadas las 3 reglas

**MEDIA — Queue Tree incompleto:**
- WAN1-Download estaba deshabilitado → habilitado (CAKE-qos 140M)
- WAN2-Download no existia → creado (CAKE-qos 140M, Sergio)
- WAN7/WAN8 max-limit=40M muy bajo para enlaces 100M → ajustado a 90M

**Rutas stale eliminadas:** 3 rutas con gateways obsoletos (192.168.12.1, 192.168.11.1, 192.168.8.1)

### Estado post-auditoria Queue Tree

| WAN | Queue | CAKE max-limit | Estado |
|-----|-------|---------------|--------|
| WAN1 (Starlink2) | WAN1-Download | 140M | Habilitado |
| WAN2 (Sergio) | WAN2-Download | 140M | Creado nuevo |
| WAN3 (Presidencia40) | WAN3-Download | 60M | Deshabilitado (WAN caida) |
| WAN4 (Presidencia169) | WAN4-Download | 60M | Deshabilitado (WAN caida) |
| WAN5 (StarlinkMini) | WAN5-Download | 180M | OK |
| WAN6 (StarlinkTotin) | WAN6-Download | 180M | OK |
| WAN7 (Chuy1) | WAN7-Download | 90M | Ajustado (era 40M) |
| WAN8 (Chuy2) | WAN8-Download | 90M | Ajustado (era 40M) |
| WAN9 (StarlinkAurora) | WAN9-Download | 180M | OK |
| WAN10 (Chaviton) | WAN10 | 100M | OK |

### PPP Profiles

| Perfil | Rate Limit | Precio |
|--------|-----------|--------|
| default | - | - |
| $300 Basico | 4M/10M | $300 |
| $500 Residencial | 5M/15M | $500 |
| $800 Profesional | 6M/18M | $800 |
| $1000 Empresarial | 10M/22M | $1,000 |
| Morosos | 64k/64k | Suspendido |
| Tecnologico | 10M/30M | Especial |
| Casas Nodos | 10M/20M | Especial |
| 20Mb | 20M/20M | Especial |

### Pendientes MikroTik
- [ ] Recalcular PCC divisor (actualmente :7 con 2 WANs muertas, ideal :8 para 8 WANs activas)
- [ ] Migrar red 172.168.x.x a rango RFC1918 correcto (172.16-31.x.x)
- [ ] Limpiar config WAN3/WAN4 (scripts, mangle, routes) o mantener para reconexion futura
- [ ] Expandir pool PPPoE si se acercan a 253 clientes
- [ ] Fix/remover scripts de backup por email (SMTP config rota)
- [ ] 17 antenas con RPC timeout pendientes de investigar

## Auditoría UISP (2026-02-15)

### Análisis cruzado PPPoE ↔ CRM ↔ NMS
- **225/262 CRM servicios enlazados a endpoints NMS** — 86% cobertura (37 sin enlace)
- Se eliminaron 4 endpoints huérfanos en auditoría previa: Olivia Cumbre, Alma Gloria, Enrique Pulido, Tule Mabel
- **Duplicado CRM #254 (Kareli Meza Coco)** eliminado ($0 balance, sin servicio)
- **Naming consistente**: NMS usa "Zona, Nombre" / CRM usa "Nombre Zona" — todos hacen match
- **13 clientes nuevos** agregados al CRM desde la auditoría original (248→261)
- **23 endpoints NMS eliminados** (248→225) — posible consolidación

### PPPoE
- 255 secrets total (actualizado 2026-02-15 noche)
- ~201 sesiones activas
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
- [ ] ~16 dispositivos desconectados pendientes de revisar (+5 nuevos)
- [ ] 3 dispositivos unauthorized con nombre: Rafael Rodriguez, Eliseo Hernandez, Miriam Cumbre
- [ ] 3 dispositivos con status "unknown" — investigar
- [ ] 37 servicios CRM sin enlace a endpoint NMS — enlazar o revisar
- [ ] Investigar por qué se redujeron endpoints NMS de 248 a 225
- [x] Sistema de cobranza automatizada — implementado y desplegado
- [x] Deploy cobranza en VPS — corriendo con BILLING_START_MONTH=2026-04
- [x] Docker volume para data/ — ya mapeado en docker-compose.yml
- [ ] Limpiar facturas de marzo generadas por UISP antes de que arranque abril
- [ ] Probar ciclo completo con /cobranza aviso (trigger manual)
- [ ] Vincular clientes a Telegram para que reciban notificaciones
- [x] Auditoria MikroTik completa — firewall, PCC, QoS, morosos, scripts corregidos
- [ ] Recalcular PCC divisor para 8 WANs activas (actualmente :7)
- [ ] Migrar red 172.168.x.x a RFC1918 correcto

## Planes de servicio (UISP CRM)

| Plan | Precio/mes | Velocidad | Cobro automatico |
|------|-----------|-----------|-----------------|
| Basico Tomatlan | $300 | 3M/8M | Si |
| Residencial | $500 | 4M/12M | Si |
| Profesional | $800 | 5M/15M | Si |
| Empresarial | $1,000 | 8M/20M | Si |
| Socios Auralink | $400 | 10M/15M | No (plan especial) |
| Servicio basico descuento | $200 | 2M/4M | No (plan especial) |

Solo los 4 planes principales reciben avisos automaticos de cobranza y suspension.

## Datos bancarios para cobranza

- **Banco**: BBVA Bancomer
- **Titular**: Carlos Eduardo Valenzuela Rios
- **Cuenta**: 285 958 9260
- **Tarjeta**: 4152 3144 8622 9639
- **CLABE**: 012 400 02859589260 7

Estos datos se envian automaticamente en los recordatorios (dia 3), advertencia (dia 7) y aviso de suspension (dia 8).

## Estado Actual (2026-02-17)
- **205 dispositivos** en UISP: 187 activos, 15 desconectados, 3 unknown
- **3 dispositivos autorizados**: Rafael Rodriguez, Eliseo Hernandez, Miriam Cumbre
- **17 antenas con RPC timeout** — decryption fix aplicado, key exchange funciona, pendiente RPC
- **261 CRM clientes / 262 servicios** — 225 enlazados a NMS endpoints (37 sin enlace)
- **224 endpoints NMS + 27 infra** = 251 sitios total
- **255 PPPoE secrets**, ~198 sesiones activas
- **SSH sin contraseña** configurado para VPS, Aura y MikroTik
- **Aura Bot** en produccion en VPS con Docker (container: aura-bot)
- **Monitor de red** corriendo (25 zonas, 172 endpoints, polling cada 2 min)
- **Sistema de cobranza** activo (dia 1/3/7/8, Vision IA, fraude, suspension)
- **Certificado SSL**: Let's Encrypt RSA válido hasta mayo 2026
- **MikroTik auditado** (2026-02-17): PCC funcional en 8 WANs, firewall asegurado, QoS CAKE en todas las WANs, morosos script corregido, auto-recovery de WANs operativo
