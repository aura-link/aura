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
- **Interfaz PPPoE**: SFP-LAN, Pool 10.10.1.2-254 + 10.10.2.2-254 (506 IPs total)
- **~196 sesiones PPPoE activas**, 254 secrets (clienteprueba deshabilitado)
- **WANs activas (7)**: WAN1 (Starlink2/ether1), WAN2 (Sergio/ether2-WAN), WAN5 (StarlinkMini/ether3), WAN6 (StarlinkTotin/ether4), WAN7 (Chuy1/ether5), WAN8 (Chuy2/ether6), WAN9 (StarlinkAurora/ether7)
- **WANs deshabilitadas**: WAN3 (Presidencia40), WAN4 (Presidencia169), WAN10 (Chaviton/ether8 — 10 Mbps, no vale la pena)
- **PCC**: Per-Connection Classifier src-address:8/x distribuyendo en 7 WANs activas (slot 7 de WAN10 vacío)
- **QoS**: CAKE queue discipline por WAN + TLS SNI-based classification (reemplazó Layer 7) — ICMP/ACK p1, DNS/Gaming/VoIP p2, VideoCall/Chat p3, Video p6, Social p7
- **Morosos**: perfil "Morosos" (64k/64k) + address-list + firewall drop + captive portal HTTP+HTTPS + allow UISP 443 (para que morosos reporten a UISP)
- **Servicios deshabilitados**: FTP, Telnet, WWW, api-ssl, bandwidth-server
- **SSH**: strong-crypto=yes, neighbor discovery deshabilitado
- **Firewall**: input chain asegurada (established/related → drop invalid → accept servicios → drop-all), forward chain con drop-all al final, address-list `local-networks` (10.0.0.0/8 + 172.168.0.0/16)
- **Mangle PCC fix**: regla `dst-address-type=local action=accept` antes de PCC rules para evitar que tráfico local sea enrutado por tablas PCC (que solo tienen default routes a WANs)
- **NAT ZT→Infra**: masquerade `src=10.147.17.0/24 dst=10.1.1.0/24` para que dispositivos de infra (sin default gateway) puedan responder a tráfico ZeroTier
- **Backups**: MikroTik crea backup diario local a las 3 AM, VPS lo jala via SCP a las 4:30 AM (cron), retención 14 días en `/root/backups/mikrotik/`

### MikroTik La Gloria
- **IP**: 10.144.247.27
- **User**: admin (password: Izan2021)

### Antenas Ubiquiti (clientes)
- **Rango IP**: 10.10.1.x/24 (asignado por PPPoE)
- **Gateway**: 10.10.0.1 (MikroTik)
- **Firmware**: XW.v6.3.24 (mayoría, actualizado 2026-02-17) / XW.v6.2.0 (algunas pendientes)
- **OpenSSL**: 1.0.0 (libssl.so.1.0.0)
- **Credenciales SSH**: ubnt/Auralink2021 o AURALINK/Auralink2021 o ubnt/Casimposible*7719Varce*1010
- **SSH requiere**: `-o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa`
- **Total Ubiquiti en PPP**: 184
- **Total en UISP**: 207 (178 activos, 29 desconectados — incluye infraestructura)

### Infraestructura de red (10.1.1.x)
- Equipos de infraestructura (APs, bridges, routers) en la red 10.1.1.x
- Estos se conectan directamente al UISP (no via PPPoE)
- **No tienen default gateway** — solo responden a tráfico del mismo /24 (por eso se necesita masquerade desde ZeroTier)
- Accesibles via ZeroTier gracias a NAT masquerade + mangle PCC fix

### ZeroTier - Red BalanceadorTomatlan
- **Network ID**: 9f77fc393ecd131f
- **API Token**: A4ZIMEclLHgZ4coje9hQFqQWfdwYUdJH (nombre: Claude-Code)
- **API Base**: `https://api.zerotier.com/api/v1/`
- **Auth header**: `Authorization: token A4ZIMEclLHgZ4coje9hQFqQWfdwYUdJH`
- **Rutas managed**: `10.10.1.0/24 via 10.147.17.11`, `10.1.1.0/24 via 10.147.17.11`, `10.147.17.0/24` (directo)
- **9 miembros**: Asus LAP (.101), VPS (.92), Servidor Aura (.155), Nuevo Servidor UISP (.243), Server UISP viejo (.73), GenesisPRO (.220), S24 (.120), Yesswera (.16), sin nombre (.91)
- **MikroTik** (.11) usa cliente ZeroTier integrado de RouterOS — no aparece como miembro normal en Central API
- **Endpoints API útiles**: GET `/network/{NWID}` (config red), GET `/network/{NWID}/member` (listar miembros), POST `/network/{NWID}/member/{ID}` (autorizar/desautorizar)

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
wss://server.auralink.link:443+sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV+allowUntrustedCertificate
```
**Nota**: El flag correcto es `+allowUntrustedCertificate`, NO `+allowSelfSignedCertificate`.

### Certificado SSL
- Let's Encrypt RSA (issuer R13) en `/home/unms/data/cert/live.crt` y `live.key`
- Se cambió de ECDSA a RSA para compatibilidad con firmware viejo

### CRM
- 261 clientes / 262 servicios (actualizado 2026-02-17)
- 224 sitios NMS endpoint (todos enlazados 1:1 a CRM, 38 servicios CRM sin enlace NMS)
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

### 9. Fix masivo UISP: 60→178 dispositivos activos (2026-02-17)
**Problema**: Solo 60 de 213 dispositivos aparecían activos en UISP. Al investigar, 41 antenas con PPPoE activo no reportaban a UISP.

**Causas raíz descubiertas (3)**:
1. **Firewall morosos bloqueaba UISP WebSocket**: La regla `drop src-address-list=morosos` en forward chain bloqueaba tráfico saliente a UISP (puerto 443). Las antenas de clientes morosos no podían conectar al WebSocket de UISP.
2. **Firmware v6.2.0 incompatible**: El `udapi-bridge` de XW.v6.2.0 recibía "ws upgrade response not 101" al intentar conectar a UISP v3.0.151. El WebSocket handshake fallaba por incompatibilidad.
3. **Encryption key desincronizada**: 20+ antenas tenían device-specific keys viejas que UISP no reconocía tras la migración. Requerían reset a master key.

**Solución aplicada (3 rondas)**:
- **Ronda 1**: Script masivo SSH → 41 targets, muchos fallos por timeout en morosos (64k/64k)
- **Ronda 2**: Filtrado solo Ubiquiti MACs, ajustes SSH → mejoró pero aún fallos
- **Ronda 3**: Regla firewall temporal para SSH morosos + heredoc approach → **14/14 éxito**

**Acciones ejecutadas**:
1. Regla firewall permanente en MikroTik: `chain=forward action=accept protocol=tcp src-address-list=morosos dst-address=217.216.85.65 dst-port=443` — permite que morosos reporten a UISP
2. Reset master key en 20 antenas (reemplazó device-specific key vieja por master key en system.cfg)
3. Eliminados 39 dispositivos fantasma adicionales via PostgreSQL (71 total en el día: 32 via API + 39 via BD)
4. Reiniciados 5 contenedores `app-device-ws-*` para recargar datos de keys
5. Autorizados 2 dispositivos nuevos (.116, .204)
6. Actualizado firmware a XW.v6.3.24 en 10.10.1.122 + 14 antenas morosas (en background)
7. Guardada config a flash en todas las antenas corregidas (`cfgmtd -w -p /etc/`)

**Resultado**: 207 dispositivos en UISP, 178 activos (era 60 al inicio del día). 29 desconectados restantes son: ~14 en proceso de upgrade firmware, ~15 requieren acceso manual o tienen firmware no-Ubiquiti.

**Dato clave SSH con MikroTik**: Para enviar comandos con `$` (como nombres de perfiles `$300 Basico`), usar heredoc pipe para evitar interpolación de shell a través de múltiples hops SSH:
```bash
cat << "SCRIPT" | ssh vps "ssh -o StrictHostKeyChecking=no admin@10.147.17.11"
/ppp secret set [find where name=NOMBRE] profile="$300 Basico 3M/8M"
SCRIPT
```

### 10. Clienteprueba migrado y deshabilitado (2026-02-17)
**Problema**: 6 sesiones PPPoE usaban el secret compartido `clienteprueba` (riesgo de seguridad).
**Hallazgo**: Los 6 clientes ya tenían secrets individuales creados por el admin. Las sesiones con `clienteprueba` eran porque las antenas aún no habían sido reconfiguradas.
**Acciones**:
1. Verificado que todos tienen secrets individuales con perfiles correctos
2. Deshabilitado secret `clienteprueba` con flag `X` (disabled)
3. Corregido perfil de `nicolasahumada`: estaba en `$800 Profesional` pero su plan CRM es `$300 Basico` → corregido a `$300 Basico 3M/8M`
4. Confirmado `eliseovaldovinosr` en perfil `Morosos` (es correcto, está suspendido)

**Secrets individuales creados por el admin:**
| Secret | IP anterior clienteprueba | Perfil |
|--------|--------------------------|--------|
| josenicolasm | 10.10.1.119 | $300 Basico 3M/8M |
| rafaelcalderon | 10.10.1.133 | $500 Residencial 4M/12M |
| oscarepano | 10.10.1.212 | $500 Residencial 4M/12M |
| briana_nava | 10.10.1.237 | $500 Residencial 4M/12M |
| erickcumbre | 10.10.1.195 | $300 Basico 3M/8M |

### 11. Decryption errors en loop: device-specific keys huérfanas (2026-02-17 noche)
**Problema**: ~300 errores de decryption por hora en los 5 contenedores `app-device-ws-*`. Las antenas intentaban conectar cada ~2 minutos y fallaban constantemente.

**Causa raíz**: Al eliminar dispositivos fantasma de la BD de UISP, se borraban las device-specific keys almacenadas del lado del servidor. Pero las antenas conservaban esas keys (terminan en `AAAAA`) en su `system.cfg`. Al reconectar:
1. La antena encripta con su device-specific key vieja
2. UISP no tiene esa key → intenta master key `sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV`
3. No coincide → "Decryption failed" → la antena reintenta en ~2 min → loop infinito

**6 MACs ofensoras identificadas:**
| MAC | IP | Tipo | Key error | Causa |
|-----|-----|------|-----------|-------|
| 60:22:32:b2:c6:2c | - | Rogue (Pilitas) | master key | Dispositivo externo (otro ISP) con connection string de AURALINK |
| 60:22:32:b6:f5:64 | - | Phantom externo | master key | Dispositivo desconocido sin entrada en BD |
| 28:70:4e:ae:07:25 | 10.10.1.146 | PPPoE (mireyajarac) | master key | Device key huérfana tras limpieza BD |
| 28:70:4e:a8:07:b4 | 10.10.1.194 | PPPoE (landinc) | master key | Device key huérfana, sin acceso SSH |
| f4:e2:c6:94:6f:88 | 10.1.1.231 | Infra | device key | Key en BD corrupta/desincronizada |
| e4:38:83:b2:b9:89 | 10.1.1.229 | Infra | device key | Key en BD corrupta/desincronizada |

**Solución aplicada:**
1. Eliminados 22 dispositivos fantasma (unauthorized + disconnected) de la BD
2. Reseteadas device keys corruptas en BD para 2 infra devices (SET key=NULL, key_exchange_status=NULL)
3. Reset key a master key en system.cfg de 3 antenas accesibles (.146, 10.1.1.231, 10.1.1.229)
4. Reiniciados 5 contenedores `app-device-ws-*` para recargar datos de keys
5. Guardada config a flash en las 3 antenas (`cfgmtd -w -p /etc/`)

**Resultado**: Errores de decryption: **~300/hora → ~4/minuto** (97% reducción). Los 2 restantes son 1 dispositivo externo incontrolable + 1 antena sin acceso SSH.

**Prevención futura**: Antes de eliminar un dispositivo de la BD de UISP, si la antena sigue activa, primero resetear su key en `system.cfg` al master key. Si no es posible acceder a la antena, al menos anotar que necesitará reset de key cuando sea accesible.

**Cómo diagnosticar**: `docker logs app-device-ws-1 --since 1h 2>&1 | grep "Decryption failed" | grep -oP 'mac":"[^"]+"' | sort | uniq -c | sort -rn`

**Cómo arreglar una antena específica**:
```bash
# 1. SSH a la antena y resetear key
sshpass -p "Auralink2021" ssh [SSH_OPTS] ubnt@IP "
sed -i 's|unms.uri=.*|unms.uri=wss://server.auralink.link:443+sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV+allowUntrustedCertificate|' /tmp/system.cfg
cfgmtd -w -p /etc/
rm -f /tmp/running.cfg
killall -9 udapi-bridge"
# 2. Si tiene device key corrupta en BD:
# UPDATE unms.device SET key=NULL, key_exchange_status=NULL WHERE mac='XX:XX:XX:XX:XX:XX';
```

### 12. Fix masivo device-specific key desync (2026-02-18)
**Problema**: 28 dispositivos desconectados de UISP a pesar de tener internet funcional (PPPoE activo, ping OK). Muchos con device-specific keys (terminan en AAAAA) en su system.cfg pero key=NULL en la BD de UISP.

**Causas raíz encontradas (3)**:
1. **Device-specific key desync** (principal): Al limpiar fantasmas de la BD, se eliminaron las device keys del servidor. Las antenas seguían enviando con su key vieja → "Decryption failed using master key" → loop 30s.
2. **PCC routing para infra**: Tráfico de 10.1.1.x al VPS (217.216.85.65) era ruteado por PCC a WANs Starlink con CGNAT, que bloqueaban la conexión WebSocket.
3. **Missing running.cfg**: `udapi-bridge` necesita `/tmp/running.cfg` para almacenar nuevos connection strings tras key exchange.

**Fix aplicado masivamente**:
```bash
# 1. Limpiar known_hosts (host keys cambian tras reboot)
ssh-keygen -f /root/.ssh/known_hosts -R <IP>
# 2. Reset a master key + guardar + recrear running.cfg + restart
sed -i "s|unms.uri=.*|unms.uri=wss://server.auralink.link:443+sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV+allowUntrustedCertificate|" /tmp/system.cfg
cfgmtd -w -p /etc/
rm -f /tmp/running.cfg && cp /tmp/system.cfg /tmp/running.cfg
killall -9 udapi-bridge
```

**Fix infra adicional**: Mangle rule `Infra-to-UISP-via-WAN8` — fuerza todo tráfico de 10.1.1.0/24 a address-list `uisp-server` (217.216.85.65) por WAN8 (Chuy2, IP pública real sin CGNAT).

**Resultado**: 155 activos → 179 activos (+24 recuperados). Solo 5 desconectados restantes.

**Dato clave**: Tras el fix, UISP hace key exchange nuevo y asigna device-specific key fresca. La antena reconecta en ~30 segundos. No requiere reboot (solo restart udapi-bridge), pero el reboot confirma persistencia.

### 13. MikroTik como Third Party en UISP (2026-02-18)
- Descubierto automáticamente como tipo `blackBox` en IP 10.1.1.1
- Autorizado via API: `POST /devices/{id}/authorize` con siteId de Matriz Tomatlan
- Nombre asignado: "MikroTik RB5009 Balanceador"
- UISP monitorea por ping (connected=true)
- VPS alcanza MikroTik via ZeroTier (10.147.17.11) y via 10.1.1.1

### 14. Ping Watchdog confirmado en red (2026-02-18)
- Script `/root/enable-watchdog.sh` en VPS para deploy masivo
- Resultado: **175/176 antenas ya tenían watchdog habilitado** (configuración original del ISP)
- Config: `wpsd.status=enabled`, `wpsd.ip=<gateway>`, `wpsd.delay=300`, `wpsd.period=300`, `wpsd.retry=3`
- Clientes (10.10.1.x): ping target = 10.10.0.1 (MikroTik PPPoE)
- Infra (10.1.1.x): ping target = 10.1.1.1 (MikroTik LAN)
- Tolerancia: 15 minutos sin respuesta antes de auto-reboot (seguro ante mantenimiento MikroTik de 2-3 min)

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
- **Bot Telegram**: AURA — @auralinkmonitor_bot (ID: 8318058273)
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
| Cliente | /misaldo, /miservicio, /miconexion, /reportar, /soporte, /vincular + enviar foto comprobante |
| Admin | /red, /clientes, /buscar, /dispositivos, /pppoe, /diagnostico, /caidas, /pagos, /morosos, /reactivar, /cobranza, /sinvincular, /progreso, /mensaje |
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

### Signup Autoservicio con ID de Servicio (implementado 2026-02-17)
Flujo mejorado de vinculacion Telegram → CRM:
1. Cliente usa `/start` (guest ve bienvenida + boton "Vincular mi cuenta")
2. `/vincular` pregunta nombre completo
3. Muestra teclado con 12 zonas (Tomatlan, La Cumbre, El Coco, etc.)
4. Fuzzy match contra CRM filtrado por zona, muestra info (nombre, plan, IP antena)
5. Al confirmar, genera **ID de servicio** `ZONA-ID` (ej: `CBR-213`)
6. Escribe `userIdent` en CRM via PATCH y guarda link en DB local
7. Clientes ya vinculados NO aparecen como opcion para otros usuarios

**Abreviaturas de zona**: TML, CBR, PNS, GLR, COC, TUL, NAH, BJZ, CTR, SGR, CRL, JAL

**Archivos del signup:**
| Archivo | Funcion |
|---------|---------|
| `src/bot/handlers/registration.py` | ConversationHandler 3 estados: nombre→zona→confirmar |
| `src/bot/keyboards.py` | `zone_selection()` teclado inline 12 zonas |

### Estado del bot (2026-02-18)
- ✅ Desplegado en VPS (217.216.85.65) con Docker
- ✅ Bot renombrado a "AURA" en BotFather (@auralinkmonitor_bot)
- ✅ Botones inline funcionando
- ✅ Claude AI responde con datos reales de UISP y MikroTik
- ✅ Consulta de saldos, dispositivos offline, sesiones PPPoE
- ✅ Pre-filtro y rate limiting implementados
- ✅ Monitor de red corriendo (interval=120s, 25 zonas, 174 endpoints, 17 infra tracked)
- ✅ Comandos /zonas, /incidentes, /monitor, /mantenimiento funcionando
- ✅ Signup autoservicio con ID de servicio y seleccion de zona
- ✅ Clientes ya vinculados excluidos de registro (evita duplicados)
- ✅ Sistema de cobranza automatizada implementado (2026-02-16)
- ✅ Sistema de onboarding interactivo implementado (2026-02-18)
- ✅ 6 bugs corregidos: monitor device_id, payment crm_payment_id, next_month x2, filter dup, PPPoE matching
- ⚠️ Pendiente: Haiku da error 529 (overloaded), usando Sonnet por ahora

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

### Sistema de Onboarding Interactivo (implementado 2026-02-18)
Sistema para rastrear y gestionar la vinculacion de clientes a Telegram antes de abril 2026.

**Comandos admin:**
- `/sinvincular` — Sincroniza CRM, muestra clientes sin vincular agrupados por zona con botones interactivos
- `/progreso` — Dashboard con barra de progreso por zona (%) y totales
- `/mensaje` — Muestra mensaje de WhatsApp listo para copiar y enviar a clientes

**Flujo interactivo:**
1. `/sinvincular` sincroniza todos los clientes CRM activos y los agrupa por zona (detecta zona desde campo city/street del servicio CRM)
2. Muestra resumen: X vinculados, Y contactados, Z pendientes
3. Botones por zona con contadores: "Tomatlan (15 pend, 3 cont)"
4. Al tocar zona: lista de clientes con botones "Contactado" y "Omitir" individuales
5. Boton "Marcar todos" para marcar toda una zona de golpe
6. Boton "Ver contactados" para ver quienes fueron contactados pero no se vincularon
7. Paginacion automatica (8 clientes por pagina)

**Archivos:**
| Archivo | Funcion |
|---------|---------|
| `src/bot/handlers/onboarding_admin.py` | /sinvincular, /progreso, /mensaje + callbacks |

**Tabla DB nueva:** `onboarding_tracking` (crm_client_id, crm_client_name, zone, status [pending/contacted/linked/skipped], contacted_at, contacted_via, notes)

**Zonas detectadas automáticamente:** TML, CBR, PNS, GLR, COC, TUL, NAH, BJZ, CTR, SGR, CRL, JAL, OTR

**Integración con /vincular:** Cuando un cliente se vincula via `/vincular`, la tabla onboarding se actualiza automáticamente a status "linked"

### Bugs corregidos en Aura Bot (2026-02-18)

| # | Bug | Archivo | Fix |
|---|-----|---------|-----|
| 1 | `create_payment_report()` faltaba param `crm_payment_id` → TypeError al auto-aprobar transferencias | `db.py` | Agregado parametro con default None |
| 2 | `next_month` calculaba mes actual en vez del siguiente | `receipts.py` | `now.month % 12 + 1` |
| 3 | PPPoE secret name mismatch (CRM "Juan Lopez" vs secret "juanlopez") | `mikrotik.py` | Matching bidireccional + sin espacios + `find_secret_by_ip()` |
| 4 | Condicion duplicada en filter (`"mi "` x2) | `filter.py` | `"mi "` + `"mis "` |
| 5 | Dead code `next_month` en billing_admin | `billing_admin.py` | Misma correccion que #2 |
| 6 | Monitor siempre 0 devices — `device.get("id")` es None, ID esta en `identification.id` | `monitor.py` | `device.get("identification", {}).get("id")` |

### Portal de Morosos / Captive Portal (implementado 2026-02-17)
Cuando un cliente es suspendido, al intentar navegar ve una página de aviso en lugar de internet.

**Arquitectura completa:**
1. **PPP Profile "Morosos"** (64k/64k) → throttle de velocidad
2. **Script `morosos-on-up`** → agrega IP del cliente a address-list "morosos" al conectar
3. **Script `morosos-on-down`** → remueve IP de address-list al desconectar
4. **NAT dst-nat** → redirige HTTP (port 80) de address-list "morosos" a VPS:8088
5. **Firewall filter** → permite acceso al portal (217.216.85.65:8088) y a Telegram (443), bloquea todo lo demás
6. **Container `morosos-portal`** → nginx:alpine en VPS sirviendo página HTML
7. **Script `sync-morosos`** → sincroniza address-list "morosos" con perfiles PPP cada 1 minuto (scheduler)

**Reglas MikroTik:**
- NAT: `chain=dstnat action=dst-nat to-addresses=217.216.85.65 to-ports=8088 protocol=tcp src-address-list=morosos dst-port=80`
- Filter: `chain=forward action=accept protocol=tcp dst-address=217.216.85.65 src-address-list=morosos dst-port=8088` (permite portal)
- Filter: `chain=forward action=accept protocol=tcp src-address-list=morosos dst-address-list=telegram-servers dst-port=443` (permite Telegram)
- Filter: `chain=forward action=accept protocol=udp src-address-list=morosos dst-port=53` (permite DNS)
- Filter: `chain=forward action=accept protocol=tcp src-address-list=morosos dst-port=53` (permite DNS TCP)
- Filter: `chain=forward action=drop src-address-list=morosos` (bloquea todo lo demás)
- Address-list `telegram-servers`: 149.154.160.0/20, 91.108.4.0/22, 91.108.8.0/22, 91.108.12.0/22, 91.108.16.0/22, 91.108.20.0/22, 91.108.56.0/22

**Script `sync-morosos`:**
- Problema: `morosos-on-up` solo se ejecuta al conectar PPPoE, no cuando se cambia el perfil mid-session
- Solución: script que itera sesiones activas y sincroniza address-list con perfil del secret
- Si secret tiene perfil "Morosos" y IP no está en address-list → la agrega
- Si IP está en address-list pero secret no es "Morosos" → la remueve
- Scheduler `sync-morosos-schedule` ejecuta cada 1 minuto
- Subido como `.rsc` via SCP e importado (RouterOS no acepta scripts complejos inline por SSH)

**Portal HTML (VPS):**
- **Ubicación VPS**: `/root/morosos-portal/` (docker-compose.yml + index.html + nginx.conf)
- **Ubicación local**: `C:\claude2\morosos-portal\`
- **Container**: `morosos-portal` (nginx:alpine, puertos 8088:80 + 8443:443, restart: unless-stopped)
- **HTTPS**: Self-signed cert (`selfsigned.crt/key`) para interceptar tráfico HTTPS — browser muestra warning pero carga portal
- **Contenido**: Aviso "Servicio Suspendido", cargo reconexión $80, datos BBVA (cuenta/tarjeta/CLABE con botones copiar), pasos para reactivar, nombre del bot @auralinkmonitor_bot copiable
- **Captive portal detection**: Intercepta URLs de conectividad de Android, iOS, Windows, Firefox → redirect al portal (HTTP y HTTPS)
- **NAT rules**: dst-nat port 80→VPS:8088, skip Telegram 443, dst-nat port 443→VPS:8443
- **Forward rules**: allow VPS:8088, allow VPS:8443, allow Telegram, allow DNS, drop morosos

**Estado actual**: 15 clientes en address-list "morosos", portal corriendo HTTP+HTTPS. Sync-morosos scheduler activo (cada 1 min). DNS + Telegram + UISP (443) permitidos.

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

### Fixes MikroTik adicionales (2026-02-18)

**WAN10 PCC mangle deshabilitado:**
- WAN10 (Chaviton/ether8) tiene interfaz deshabilitada pero sus 3 reglas mangle (PCC, Route-to, Download) seguían activas
- Deshabilitadas: rules 26 (Download-WAN10), 47 (PCC-WAN10), 48 (Route-to-WAN10)

**WAN1 Netwatch corregido:**
- Monitoreaba 192.168.1.1 (gateway compartido con WAN2) — daba status incorrecto
- Cambiado a monitorear 8.8.8.8 con `src-address=192.168.1.135` (IP de WAN1)
- Status: UP y funcional

**WAN2 CAKE QoS arreglado:**
- Download mangle tenía `in-interface=ether2-WAN` pero tráfico entra por `WAN2 macvlan Sergio`
- Cambiado a `in-interface=WAN2 macvlan Sergio` — macvlan NO se tocó, solo la regla mangle
- CAKE queue ahora recibe tráfico correctamente

**Fasttrack deshabilitado:**
- Rule 15 (fasttrack established/related) bypaseaba TODO el queue tree y mangle
- Deshabilitado para que QoS CAKE funcione en todas las WANs

**Rule 31 connection-state corregido:**
- Tenía `connection-state=established,related,new` — "new" permitía todo el tráfico
- Corregido a `connection-state=established,related`

**2 reglas TEMP-morosos eliminadas:**
- Reglas temporales de prueba que ya no eran necesarias

**33 dispositivos fantasma UISP eliminados:**
- `DELETE FROM unms.device WHERE name IS NULL AND connected=false AND authorized=false` → 33 rows

**172.168.x.x sin internet — RESUELTO (2026-02-18 noche):**
- `172.168.0.0/16` fue removido de address-list `local-networks` en sesión anterior (pendiente de migrar a RFC1918)
- Firewall rule 30 (`accept new src-address-list=local-networks`) dejó de matchear tráfico 172.168.x.x
- Tráfico caía a rule 33 (drop-all) → clientes sin internet
- **Fix**: Re-agregado `172.168.0.0/16` a `local-networks` — internet restaurado inmediatamente

**Enlace PtP AP Tomatlan-Colmena ↔ ST Colmenares optimizado (2026-02-18 noche):**
- Equipos: 2x Rocket 5AC Lite con dishes 34 dBi, distancia 10 km
- IPs: AP 10.1.1.253, Station 10.1.1.252
- Credenciales: AURALINK / Auralink2021
- Cambios aplicados: PTMP → PtP, 40 MHz → 80 MHz, deshabilitado 11ac/11n compat
- Frecuencia cambió automáticamente de 5905 a 5830 MHz (DFS)
- Resultados: TX rate +93% (243→468 Mbps), downlink capacity +88% (132→248 Mbps), CPU AP -23% (84→61%), latencia 10ms→0ms

**CRITICO 5 — PCC hijacking tráfico local (2026-02-17 noche):**
- Las mangle PCC rules (`in-interface=SFP-LAN, connection-mark=no-mark`) marcaban tráfico destinado al MikroTik (10.1.1.1) con routing marks (to_isp1, to_isp2, etc.)
- Las tablas PCC solo tienen `0.0.0.0/0 → WAN gateway` — NO tienen rutas locales
- Resultado: replies ICMP/TCP de dispositivos de infra (10.1.1.x) se enviaban por una WAN en vez de entregarse localmente
- **Diagnóstico**: sniffer en SFP-LAN mostraba que los replies LLEGABAN pero el ping reportaba timeout. ARP-ping (Layer 2) funcionaba, ICMP ping (Layer 3) no.
- **Fix**: `/ip firewall mangle add chain=prerouting dst-address-type=local action=accept` antes de las reglas PCC
- Esto excluye tráfico local del PCC, permitiendo entrega correcta al IP stack

**ALTA — Dispositivos infra sin gateway (2026-02-17 noche):**
- Los equipos de infraestructura (10.1.1.x) no tienen default gateway configurado
- Solo responden a tráfico de su mismo /24, no pueden rutear responses a 10.147.17.x (ZeroTier)
- **Fix**: NAT masquerade `src-address=10.147.17.0/24 dst-address=10.1.1.0/24`
- El tráfico desde ZeroTier aparece como 10.1.1.1 (MikroTik) para los dispositivos

**MEDIA — Input chain order incorrecto (2026-02-17 noche):**
- "Drop Invalid Input" (rule 8) estaba antes de "Accept Established/Related" (rule 13)
- Corregido: established/related ahora va primero en la cadena input

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

### PPP Profiles (actualizado 2026-02-17)

| Perfil | Rate Limit | CRM Plan | Overshoot |
|--------|-----------|----------|-----------|
| $300 Basico 3M/8M | 4M/10M | Basico $300 (3M/8M) | 33%/25% |
| $500 Residencial 4M/12M | 5M/15M | Residencial $500 (4M/12M) | 25%/25% |
| $800 Profesional 5M/15M | 6M/18M | Profesional $800 (5M/15M) | 20%/20% |
| $1000 Empresarial 8M/20M | 10M/25M | Empresarial $1,000 (8M/20M) | 25%/25% |
| Morosos | 64k/64k | Suspendido | - |
| Casas Nodos | 3M/4M | Especial | - |
| 20Mb | 10M/20M | Especial | - |
| default / default_Matriz | - | Nodos | - |
| cruz | - | Cruz de Loreto | - |

Perfiles eliminados (0 usuarios): Tecnologico, teque, simétrico

### Pendientes MikroTik
- [x] Recalcular PCC divisor — actualizado a :8, 7 WANs activas + WAN10 deshabilitado
- [x] Expandir pool PPPoE — expandido a 506 IPs (10.10.1.2-254 + 10.10.2.2-254)
- [x] Limpiar config WAN3/WAN4 — rutas eliminadas, schedulers retry deshabilitados, netwatch deshabilitado
- [x] Fix backups — email deshabilitado, VPS jala por SCP diario (cron 4:30 AM)
- [x] Layer 7 QoS — reemplazado con TLS SNI matching (7 reglas mangle)
- [x] Firewall forward chain — drop-all al final, address-list local-networks
- [x] Servicios inseguros deshabilitados — FTP, Telnet, WWW, api-ssl, bandwidth-server
- [x] SSH strong-crypto + neighbor discovery off + user py deshabilitado
- [x] Portal morosos HTTPS — self-signed cert en VPS:8443, NAT redirect con bypass Telegram
- [x] Perfiles PPP — Empresarial bumped a 10M/25M, 3 perfiles sin uso eliminados
- [ ] Migrar red 172.168.x.x a rango RFC1918 correcto (172.16-31.x.x)
- [x] 17 antenas con RPC timeout — 10 resueltas con fix masivo + firmware upgrade, 7 aún desconectadas

## Auditoría UISP (2026-02-15 → actualizada 2026-02-17)

### Análisis cruzado PPPoE ↔ CRM ↔ NMS
- **224/262 CRM servicios enlazados a endpoints NMS** — todos los 224 sitios NMS endpoint enlazados 1:1 (0 duplicados, 0 huérfanos)
- **38 servicios CRM sin enlace NMS** — clientes sin antena registrada en UISP o con antena aún desconectada
- **2 "Luz Mariscal"** en CRM: no son duplicados, son direcciones distintas (Nahuapa vs otro)
- Se eliminaron 4 endpoints huérfanos en auditoría previa: Olivia Cumbre, Alma Gloria, Enrique Pulido, Tule Mabel
- **Duplicado CRM #254 (Kareli Meza Coco)** eliminado ($0 balance, sin servicio)
- **Naming consistente**: NMS usa "Zona, Nombre" / CRM usa "Nombre Zona" — todos hacen match

### PPPoE
- 254 secrets total (clienteprueba deshabilitado, actualizado 2026-02-17)
- ~196 sesiones activas
- 0 sesiones "clienteprueba" — secret deshabilitado, todos migrados a individuales
- 15 clientes en perfil "Morosos" (confirmados legítimos)

### Clienteprueba — RESUELTO (2026-02-17)
Todos los 6 clientes que usaban `clienteprueba` ya tienen secrets individuales. El secret compartido fue deshabilitado.
Ver detalle en Problema Resuelto #10.

### Limpieza realizada (acumulado)
- Eliminados **104 dispositivos fantasma** total (32 via API + 39 via PostgreSQL + 33 via PostgreSQL 2026-02-18)
- Eliminados 4 endpoints NMS huérfanos
- Eliminado 1 duplicado CRM
- Corregidas ~20 secuencias PostgreSQL del CRM
- Autorización de 2 dispositivos nuevos (.116, .204)
- Firmware upgrade masivo a XW.v6.3.24 (15+ antenas)

## Pendientes

- [x] Asignar antenas de clientes a suscriptores CRM — **100% completado (248/248)**
- [ ] Revisar antenas 10.10.1.45 y 10.10.1.162 (fallaron SSH)
- [x] Agente IA para UISP (Telegram Bot + Python) — implementado como Aura Bot
- [x] Deploy Aura Bot en VPS (Docker) — corriendo en 217.216.85.65
- [x] Sistema de monitoreo proactivo — implementado y corriendo
- [x] Crear PPPoE secrets individuales para 6 clienteprueba — ya estaban creados por admin, clienteprueba deshabilitado
- [x] Revisar morosos conectados — 15 confirmados legítimos
- [ ] Probar diferenciacion admin/cliente en system prompt
- [x] Flujo /vincular mejorado con zonas, fuzzy match y ID de servicio — implementado
- [x] Renombrar bot en BotFather a "AURA" — hecho
- [x] Fix masivo UISP — 60→179 activos (97%), device-specific key desync fue causa raíz principal
- [x] 71 fantasmas eliminados — 32 via API + 39 via PostgreSQL
- [x] Fix keys sesión 02-18 — +24 dispositivos recuperados (155→179), reset master key masivo
- [ ] 5 dispositivos desconectados — 1 credenciales custom (10.1.1.211), 4 pendientes revisar
- [ ] 38 servicios CRM sin enlace a endpoint NMS — enlazar o revisar
- [x] Sistema de cobranza automatizada — implementado y desplegado
- [x] Deploy cobranza en VPS — corriendo con BILLING_START_MONTH=2026-04
- [x] Docker volume para data/ — ya mapeado en docker-compose.yml
- [ ] Limpiar facturas de marzo generadas por UISP antes de que arranque abril
- [ ] Probar ciclo completo con /cobranza aviso (trigger manual)
- [x] Vincular clientes a Telegram — sistema de onboarding interactivo con /sinvincular, /progreso, /mensaje
- [x] Auditoria MikroTik completa — firewall, PCC, QoS, morosos, scripts corregidos
- [x] Portal cautivo morosos — página HTML, NAT redirect, captive portal detection
- [x] Sync-morosos scheduler — sincroniza address-list cada 1 min al cambiar perfil mid-session
- [x] Telegram permitido para morosos — address-list telegram-servers + firewall rule
- [x] Recalcular PCC divisor — :8 con 7 WANs activas (WAN10 deshabilitado, slot 7 vacío)
- [ ] Migrar red 172.168.x.x a RFC1918 correcto (172.168.0.0/16 re-agregado a local-networks como fix temporal)
- [x] Fix PCC hijacking tráfico local — mangle dst-address-type=local accept
- [x] Fix ZeroTier acceso a infra 10.1.1.x — NAT masquerade + PCC local fix
- [x] ZeroTier API configurada — token Claude-Code para gestión REST
- [x] Aura Bot 14 fixes desplegados en VPS — container healthy
- [x] Regla firewall morosos→UISP — permite que morosos reporten a UISP (443)
- [x] Firmware upgrade masivo a XW.v6.3.24 — 15+ antenas actualizadas
- [x] nicolasahumada perfil corregido — $800→$300 Basico 3M/8M
- [x] Firmware upgrades morosos — 3/14 actualizadas a v6.3.24, 2 son AC (no aplica XW), 9 sin acceso SSH
- [x] Decryption errors reducidos 97% — 22 phantoms eliminados, 3 keys reseteadas, 2 DB keys limpiadas
- [ ] ~53 antenas con credenciales SSH desconocidas — requieren acceso web/físico
- [ ] 172.168.x.x — removido de local-networks, pendiente migrar a RFC1918 correcto
- [x] Ping Watchdog verificado — 175/176 antenas ya lo tenían activo (target=gateway, period=300s, retry=3)
- [x] MikroTik en UISP — agregado como Third Party (blackBox) en Matriz Tomatlan
- [x] Mangle Infra→UISP — fuerza tráfico infra al VPS por WAN8 (evita CGNAT Starlink)

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

## Estado Actual (2026-02-18 noche)
- **184 dispositivos** en UISP: **179 activos** (97%), 5 desconectados, 0 fantasmas (33 adicionales eliminados hoy)
- **261 CRM clientes / 262 servicios** — 224 enlazados 1:1 a NMS endpoints (38 sin enlace)
- **254 PPPoE secrets** (~198 sesiones activas), clienteprueba deshabilitado, pool 506 IPs
- **MikroTik**: PCC en 7 WANs activas (WAN10 deshabilitado), fasttrack OFF, QoS CAKE funcional en todas las WANs, WAN1/WAN2 netwatch corregidos
- **Aura Bot "AURA"** en produccion en VPS con Docker — 6 bugs corregidos + onboarding desplegado
- **Monitor de red** corriendo: 25 zonas, 174 endpoints, 17 infra tracked, polling cada 2 min
- **Sistema de cobranza** activo: BILLING_START_MONTH=2026-04, listo para abril
- **Sistema de onboarding**: /sinvincular, /progreso, /mensaje — listo para campana de vinculacion
- **Portal morosos** operativo: HTTP + HTTPS redirect, sync-morosos cada 1 min, Telegram permitido
- **Backups automatizados**: MikroTik + Aura DB a VPS diario (cron 4:30/4:35 AM), retencion 14 dias
- **5 desconectados restantes**: 10.1.1.211 (credenciales custom), 10.10.1.150, .171, .180, .227
- **~53 antenas con credenciales SSH desconocidas** — requieren acceso web/fisico
- **Enlace PtP optimizado**: AP Tomatlan-Colmena ↔ ST Colmenares — PtP+80MHz, capacity 248 Mbps (+88%)
- **172.168.x.x restaurado**: re-agregado a local-networks (fix temporal hasta migrar a RFC1918)
- **Prioridad**: vincular clientes a Telegram antes de abril (0 vinculados actualmente)
