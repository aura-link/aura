# AURALINK WISP - Memoria Operativa

## Sincronización de Memoria (IMPORTANTE)

Claude Code corre en 2 ubicaciones. Cuando el usuario diga **"actualiza tu memoria"**, actualizar CLAUDE.md y sincronizar:

**Desde LAPTOP (C:\claude2):**
```bash
scp C:/claude2/CLAUDE.md vps:/root/claude2/CLAUDE.md
```

**Desde VPS (/root/claude2):**
```bash
scp /root/claude2/CLAUDE.md vps:/root/claude2/CLAUDE.md   # ya es local, no necesita scp
# Para que la laptop tenga la última versión, el usuario debe ejecutar desde la laptop:
# scp vps:/root/claude2/CLAUDE.md C:/claude2/CLAUDE.md
```

**Regla**: Siempre que actualices CLAUDE.md, sincroniza al otro lado. Si estás en la laptop, scp al VPS. Si estás en el VPS, el archivo ya queda ahí — la laptop jalará la próxima vez.

**Nota sobre SSH a antenas**: El usuario pidió explícitamente que NO se acceda a antenas (SSH) sin pedir permiso primero. Siempre preguntar antes de conectar a cualquier dispositivo de la red.

## Proyecto
Migración de UISP desde servidor local (laptop 10.1.1.254) a VPS en la nube (Contabo).

## Infraestructura

### VPS - UISP Cloud
- **IP**: 217.216.85.65 (Contabo)
- **DNS**: server.auralink.link → 217.216.85.65
- **Contabo login**: auralinkclientes@gmail.com / f8FWcAgJFQ8GeZAG (contraseña VPS root: IWQ240f8)
- **OS**: Debian/Ubuntu con Docker
- **UISP**: v3.0.159 (Docker containers, updated 2026-03-01 from v3.0.151)
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
- **~199 sesiones PPPoE activas**, 254 secrets (clienteprueba deshabilitado)
- **WANs activas (6)**: WAN1 (Starlink2/ether1, :6/0), WAN5 (StarlinkMini/ether3, :6/1), WAN10 (Chaviton/macvlan ether8, :6/2), WAN7 (Chuy1/ether5, :6/3), WAN8 (Chuy2/ether6, :6/4), WAN9 (StarlinkAurora/ether7, :6/5)
- **WANs deshabilitadas**: WAN2 (Sergio/ether2-WAN — <10 Mbps), WAN3 (Presidencia40), WAN4 (Presidencia169), WAN6 (StarlinkTotin/ether4 — ISP Force200 issues, deshabilitada 2026-02-27)
- **WAN11 pendiente**: macvlan bajo ether8-WAN (192.168.104.10/24), ISP no activo aún — gateway no responde
- **ether8-WAN**: interfaz física padre de macvlans WAN10 y WAN11, NO hace masquerade — cada macvlan es independiente
- **PCC**: Per-Connection Classifier src-address:6/x distribuyendo en 6 WANs activas (0 slots vacíos)
- **QoS**: CAKE queue discipline por WAN + TLS SNI-based classification (reemplazó Layer 7) — ICMP/ACK p1, DNS/Gaming/VoIP p2, VideoCall/Chat p3, Video p6, Social p7
- **QUIC bloqueado**: `chain=forward action=drop protocol=udp dst-port=443 in-interface=SFP-LAN` — fuerza TCP para que QoS SNI funcione (96% del tráfico video/social usaba QUIC bypaseando SNI)
- **QoS SNI wildcards**: usar `*keyword*` no `*.domain.com` en RouterOS 7 tls-host
- **Morosos**: perfil "Morosos" (64k/64k) + address-list + firewall drop + captive portal HTTP+HTTPS + allow UISP 443 (para que morosos reporten a UISP)
- **Servicios deshabilitados**: FTP, Telnet, WWW, api-ssl, bandwidth-server
- **SSH**: strong-crypto=yes, neighbor discovery deshabilitado
- **Firewall**: input chain asegurada (established/related → drop invalid → accept servicios → drop-all), forward chain con drop-all al final, address-list `local-networks` (10.0.0.0/8 + 172.168.0.0/16)
- **Mangle PCC fix**: regla `dst-address-type=local action=accept` antes de PCC rules para evitar que tráfico local sea enrutado por tablas PCC (que solo tienen default routes a WANs)
- **Mangle Skip-PCC-for-UISP-VPS**: `chain=prerouting action=accept dst-address=217.216.85.65 in-interface=SFP-LAN` — bypasea PCC para tráfico de antenas al VPS, forzando uso de ruta estática ZeroTier
- **Ruta estática UISP VPS**: `217.216.85.65/32 via 10.147.17.92` (ZeroTier) — todo tráfico al VPS va por túnel ZeroTier (~90-130ms), independiente de PCC/WANs
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
- **Total en UISP**: 204 autorizados (203 conectados, 1 desconectado — incluye infraestructura)

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
- **Ruta MikroTik estática**: `217.216.85.65/32 via 10.147.17.92` — asegura que todo tráfico de antenas al VPS pase por ZeroTier (bypass PCC)
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
**Nota**: El flag correcto es `+allowUntrustedCertificate`, NO `+allowSelfSignedCertificate`. UISP v3.0.151 tenía un bug que mostraba el flag incorrecto en la UI — corregido manualmente en 4 archivos del contenedor `unms-api` (ver Problema #16). Tras actualizaciones de UISP, verificar que no regrese el bug.

### Certificado SSL
- Let's Encrypt RSA (issuer R13) en `/home/unms/data/cert/live.crt` y `live.key`
- Se cambió de ECDSA a RSA para compatibilidad con firmware viejo

### CRM
- 240 clientes / 241 servicios (actualizado 2026-02-20, user eliminó 21 no-clientes)
- 222 sitios NMS endpoint (todos enlazados 1:1 a CRM, 19 servicios CRM sin enlace NMS)
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

### 15. 35 antenas UISP desconectadas por PCC routing (2026-02-19)
**Problema**: Cross-reference PPPoE ↔ UISP reveló 35 antenas con internet funcional (PPPoE activo) pero desconectadas de UISP. Adicionalmente, 48 antenas con PPPoE activo no tenían ninguna entrada en UISP.

**Causa raíz**: PCC load balancing enviaba el tráfico de las antenas al VPS (217.216.85.65) por WANs con CGNAT (Starlink) u otras WANs que no podían alcanzar el VPS. Ping desde antenas desconectadas al VPS = 100% packet loss. Antenas que sí conectaban a UISP tenían WANs con ruta funcional al VPS.

**Diagnóstico**: SSH a antenas desconectadas y `ping 217.216.85.65` → 0% success. SSH a antenas conectadas → 100% success. La diferencia era qué WAN les asignaba PCC.

**Solución permanente (2 partes)**:
1. **Mangle bypass PCC**: `chain=prerouting action=accept dst-address=217.216.85.65 in-interface=SFP-LAN comment="Skip-PCC-for-UISP-VPS"` — colocada antes de las reglas PCC. Impide que PCC marque tráfico al VPS, forzando uso de tabla de ruteo principal.
2. **Ruta estática ZeroTier**: `217.216.85.65/32 via 10.147.17.92 comment="UISP-VPS-via-ZeroTier"` — todo tráfico al VPS va por túnel ZeroTier (latencia ~90-130ms, pero 100% confiable).

**Ejecución**:
- Batch 1: 16 antenas (12 fixed, 4 failed credentials)
- Batch 2: 19 antenas (10 fixed, 9 failed credentials)
- Post-ZeroTier route: 31 antenas restantes reiniciadas (28 OK, 3 failed credentials)
- 3 restantes arregladas manualmente (Magda Mora, Ana Esther, Jose Nicolas)

**Caso especial 10.10.1.53 (Jose Nicolas Mariscal)**:
- Tenía `failed_decryption=true` en BD → DELETE entry + reset master key
- Después: `udapi-bridge` entraba en loop `"cannot read file /tmp/running.cfg"` → `"failed to store new connection string"` → desconexión
- **Descubrimiento**: `udapi-bridge` NECESITA `/tmp/running.cfg` para guardar el nuevo connection string tras key exchange. Sin este archivo, no puede persistir la device-specific key.
- **Fix**: `cp /tmp/system.cfg /tmp/running.cfg` antes de matar udapi-bridge → key exchange exitoso
- **Regla**: NO eliminar `running.cfg` en antenas que necesitan key exchange fresco. Solo eliminarlo si ya tienen device-specific key funcional.

**Resultado**: **35/35 recuperadas (100%)**. UISP pasó de 112 activas a 182 conectadas.

**Scripts**: `fix-35-disconnected.sh`, `fix-remaining.sh`, `fix-restart-udapi.sh`, `fix3.sh`, `fix53.sh`, `fix-nicolas.sh`

### 16. Bug UISP: connection string mostraba allowSelfSignedCertificate (2026-02-19)
**Problema**: La página de settings de UISP (`/nms/settings/devices`) generaba el connection string con `+allowSelfSignedCertificate` en vez de `+allowUntrustedCertificate`. Esto causaba que antenas configuradas con la key copiada del UI tuvieran problemas de encriptación.

**Causa raíz**: Bug en UISP v3.0.151 — el código fuente hardcodea `allowSelfSignedCertificate` en múltiples archivos (frontend y backend).

**Archivos corregidos** (dentro del contenedor `unms-api`):
| Archivo | Ocurrencias | Función |
|---------|:-:|---------|
| `/home/app/unms/api.js` | 3 | Backend API — genera connection string |
| `/home/app/unms/device-ws.js` | 2 | WebSocket handler |
| `/home/app/unms/cli/unms-key.js` | 1 | CLI key generator |
| `/home/app/unms/public/assets/index-9_kxL8KA.js` | 1 | Frontend JS (era `index-BF6PYhCd.js` en v3.0.151) |

**Fix aplicado**: `sed -i 's/allowSelfSignedCertificate/allowUntrustedCertificate/g'` en los 4 archivos + `docker restart unms-api`.

**Advertencia**: Estos cambios están DENTRO del contenedor Docker. Si UISP se actualiza o el contenedor se recrea desde la imagen base, los cambios se pierden. Verificar tras cualquier actualización de UISP.

### 17. 27 antenas Ubiquiti sin entrada UISP (2026-02-19)
**Problema**: 27 antenas Ubiquiti con PPPoE activo pero sin ningún dispositivo correspondiente en UISP.
**Intento de fix**: Script `fix-27-missing.sh` para configurar connection string via SSH.
**Resultado**: Solo 4 de 27 accesibles (1 configurada, 3 ya tenían config correcta). 23 fallaron por credenciales desconocidas o inaccesibilidad SSH.
**Pendiente**: Requieren acceso web o físico para configurar UISP connection string.

### 18. Limpieza CRM + phantoms + decryption fix (2026-02-20)

**CRM cleanup**: User eliminó manualmente 21 servicios de no-clientes de Auralink (262→241 servicios). Quedan 19 servicios CRM sin enlace a endpoint NMS — todos tienen PPPoE secret pero sus antenas no están registradas en UISP.

**42 phantoms eliminados**: Segunda ronda de limpieza de dispositivos fantasma en BD UISP. Query: `DELETE FROM unms.device WHERE NOT connected AND NOT authorized AND (name IS NULL OR name='') AND site_id IS NULL`. 1 conservado con sitio "Recursos" (MAC e4:38:83:b8:64:e5, posible infra real).

**7 antenas con decryption errors fijadas**: Script `fix-decryption-7.sh` reseteó master key en 7 antenas que tenían device-specific keys huérfanas (terminan en AAAAA) causando ~165 errores/hora.

| Antena | Cliente | Resultado |
|--------|---------|-----------|
| 10.10.1.55 | hugomanzot | RESET OK — apareció en UISP |
| 10.10.1.54 | veronicatenoriot | RESET OK — apareció en UISP |
| 10.10.1.222 | dianacornejoc | RESET OK — apareció en UISP |
| 10.10.1.161 | veronicachavarinc | RESET OK |
| 10.10.1.86 | landinc | RESET OK |
| 10.10.1.75 | danielayonc | RESET OK (desconectada) |
| 10.10.1.184 | diftomatlan | FALLÓ (inalcanzable) |

**Resultado**: Decryption errors: ~165/hora → ~34 en 5 min (~90% reducción). 3 dispositivos nuevos aparecieron en UISP. 6 MACs restantes no fixeables remotamente (1 inalcanzable, 1 rogue externo, 2 desconocidas, 1 moroso sin SSH, 1 desconectada).

**4 antenas de 19 sin UISP intentadas**: Script `fix-19-uisp.sh` — solo 4 online de 19. Resultado: 1 ya configurada (.84), 3 morosos inalcanzables (firewall + credenciales desconocidas).

### 19. 4 infra devices desconectadas UISP por DNS (2026-02-25)
**Problema**: 4 dispositivos de infraestructura (Sectorial Matriz Tom_Norte, ST Aurora, ST Piedra Poma, ST Tierritas) aparecían como desconectados en UISP a pesar de responder a ping y tener udapi-bridge corriendo con device-specific keys válidas.

**Causa raíz**: DNS. Los dispositivos infra (10.1.1.x) tenían DNS configurado como 8.8.8.8 y 1.1.1.1, pero **no podían alcanzar servidores DNS externos** porque su tráfico general (fuera del mangle Infra-to-UISP-via-WAN8 que solo cubre tráfico al VPS) se rutea por PCC que no funciona correctamente para IPs de infra. `udapi-bridge` no podía resolver `server.auralink.link` → loop "Name or service not known" cada ~60 segundos.

**Diagnóstico**: `cat /var/log/unms.log` en la antena mostraba `"Name or service not known 'server.auralink.link'"` en loop. `ping 8.8.8.8` desde la antena = 100% packet loss. `ping 217.216.85.65` = 0% loss (funciona por mangle especial).

**Solución**: Cambiar DNS primario a 10.1.1.1 (MikroTik DNS proxy, `allow-remote-requests=yes`) en las 4 antenas:
```bash
sed -i "s/resolv.nameserver.1.ip=8.8.8.8/resolv.nameserver.1.ip=10.1.1.1/" /tmp/system.cfg
sed -i "s/resolv.nameserver.2.ip=1.1.1.1/resolv.nameserver.2.ip=8.8.8.8/" /tmp/system.cfg
echo "nameserver 10.1.1.1" > /etc/resolv.conf
echo "nameserver 8.8.8.8" >> /etc/resolv.conf
cfgmtd -w -p /etc/
```

**Dispositivos fijados:**
| Dispositivo | IP | Firmware | User |
|---|---|---|---|
| Sectorial Matriz Tom_Norte | 10.1.1.244 | WA.v8.7.17 | AURALINK |
| ST Aurora | 10.1.1.94 | XW.v6.3.24 | ubnt |
| ST Piedra Poma | 10.1.1.247 | WA.v8.7.17 | AURALINK |
| ST Tierritas | 10.1.1.98 | WA.v8.7.11 | AURALINK |

**También**: Eliminados 4 phantoms de la BD (entradas sin nombre/MAC/autorización con las mismas IPs).

**Resultado**: 4/4 reconectadas a UISP. Total: 204 autorizados, 201 conectados.

**Prevención**: Otros dispositivos de infra podrían tener el mismo problema de DNS. Si un infra device aparece desconectado de UISP pero responde a ping, verificar `/var/log/unms.log` por "Name or service not known" y cambiar DNS a 10.1.1.1.

### 20. 10.1.1.212 y 10.1.1.229 desconectadas por device-specific key huérfana (2026-02-26)
**Problema**: 2 dispositivos de infraestructura (Recuros-Gloria LiteBeam 5AC y Sectorial Cumbre LiteAP GPS) con RPC timeout en UISP — se conectaban al WebSocket, recibían `unmsSetup`, pero UISP no obtenía respuesta a pings/statistics → "reconnecting after 30s of inactivity" → loop infinito.

**Causa raíz**: Device-specific keys huérfanas (terminan en AAAAA) en `system.cfg` de las antenas, sin matching key en la BD de UISP (fueron limpiadas en sesiones anteriores). La antena encriptaba con key vieja, UISP hacía key exchange pero los RPC requests timeouted.

**Solución**:
1. Reset URI en system.cfg a master key: `sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV`
2. `cfgmtd -w -p /etc/` (guardar a flash)
3. `rm -f /tmp/running.cfg && cp /tmp/system.cfg /tmp/running.cfg`
4. `killall -9 udapi-bridge`
5. Reset key en BD: `UPDATE unms.device SET key=NULL, key_exchange_status=NULL WHERE mac='...'`
6. Reboot de la antena (para confirmar persistencia)

**Dispositivos fijados:**
| Dispositivo | IP | MAC | Firmware |
|---|---|---|---|
| Recuros-Gloria | 10.1.1.212 | f4:e2:c6:94:6f:88 | XW.v6.3.24 |
| Sectorial Cumbre | 10.1.1.229 | e4:38:83:b2:b9:89 | WA.v8.7.18 |

**Nota 10.1.1.229**: En primer intento, el fix se aplicó pero no se guardó correctamente a flash — tras reboot volvió a cargar la key vieja. Segundo intento con `cfgmtd -w -p /etc/` explícito + reboot → conectada correctamente.

**Resultado**: Ambas reconectadas. UISP: 204 autorizados, 203 conectados.

### 21. Auto-dismiss avisos fallaba por matching de nombres (2026-02-26)
**Problema**: Clientes registrados (ej: Abel de Loera, IP 10.10.1.170) seguían viendo el captive portal de avisos. La función `_dismiss_from_avisos()` en registration.py intentaba matchear el nombre CRM "Abel Loera Tomatlan" contra el PPPoE username "abelt" usando substring matching — fallaba porque "abelt" no es substring de "abelloeratomattan" ni viceversa.

**Fix**: Reescrita `_dismiss_from_avisos()` con 2 estrategias:
1. **Match por IP del dispositivo CRM** (más confiable): usa la IP que ya se obtuvo del CRM durante el registro (`reg_matches[].ip`) y busca la sesión PPPoE activa con esa IP
2. **Fallback por find_secret_by_name()**: usa la función existente del MikroTik client que tiene matching robusto (exacto, parcial, sin espacios)

**Archivo**: `aura-bot/src/bot/handlers/registration.py` — función `_dismiss_from_avisos(mk, client_name, device_ip="")`

### 22. Sectorial Cumbre (10.1.1.229) caía por CPU saturado (2026-03-01)
**Problema**: LiteAP GPS en 10.1.1.229 entraba en loop "connection established → 30s inactivity → reconnecting" con UISP. RPC requests (statistics, ping) timeouted constantemente. CPU no se "estresaba" según el usuario.

**Causa raíz**: `ubntspecd` (airview/spectrum analyzer) habilitado en producción consumía 22% CPU constante. Combinado con `ustatsd` (16%), `ksoftirqd` (11%, tráfico WiFi), y `ubnt-gps-reader` (5%), el CPU solo tenía **7% idle**. `udapi-bridge` no tenía suficiente CPU para responder RPC requests dentro del timeout de 30s.

**Solución**: Desactivar airview: `sed -i 's/airview.status=enabled/airview.status=disabled/' /tmp/system.cfg && cfgmtd -w -p /etc/` + reboot. CPU idle subió de 7%→50%, load average de 1.85→0.59. Conexión UISP estable.

**Nota**: `ubnt-gps-reader` es hardcoded en firmware WA (LiteAP GPS), no se puede desactivar desde system.cfg. Pero sin airview, el CPU tiene suficiente margen.

### 23. Monitor de red spammeaba notificaciones a clientes (2026-03-01)
**Problema**: Clientes vinculados a Telegram recibían muchas notificaciones de "infraestructura caída" y "servicio restaurado" por equipos que flapping (suben y bajan repetidamente). Ej: Sectorial Cumbre generó 4 incidentes en 2 horas (40 clientes x 2 notificaciones x 4 veces = spam).

**3 causas:**
1. Anti-flap muy corto (1 poll = 2 min) — equipos que bajan 3-4 min ya generaban incidente
2. Cooldown usaba `incident_id` como referencia — cada incidente nuevo bypaseaba el cooldown de 30 min
3. Recovery notificaba a clientes incluso en caídas cortísimas (2-4 min)

**Fix (3 cambios en `monitor.py`):**
1. Anti-flap: `MONITOR_INTERVAL * 1` → `MONITOR_INTERVAL * 3` (~6 min) antes de confirmar caída
2. Cooldown clientes: `ref_id = str(incident_id)` → `ref_id = f"outage_dev_{device_id}"` — cooldown por dispositivo, no por incidente
3. Recovery a clientes: solo si `duration_secs >= 600` (>10 min) — flaps cortos no molestan

Admins siguen recibiendo TODAS las notificaciones para visibilidad completa.

### 24. UISP actualizado v3.0.151 → v3.0.159 (2026-03-01)
**Pre-update backups**:
- PostgreSQL: `/root/backups/uisp-pre-update-20260301.sql` (581 MB)
- Data: `/root/backups/uisp-data-pre-update-20260301.tar.gz` (5.5 GB)
- MikroTik: `pre-uisp-update.backup`

**Proceso**: Bootstrap installer desde `https://uisp.ui.com/install` → `install-full.sh --update --unattended`. Requirió `docker compose down` manual antes de ejecutar (containers deben estar parados).

**Post-update fixes**:
1. `docker update --cpus=2 ucrm` — se pierde al recrear containers
2. Connection string flag fix re-aplicado en 4 archivos (frontend cambió de `index-BF6PYhCd.js` a `index-9_kxL8KA.js`)
3. CRM también se actualizó a v4.5.33

**Cambios API detectados en v3.0.159**:
- `GET /devices` ya NO acepta params `count` ni `page`/`pageSize` — devuelve todos los devices sin paginación

**Resultado**: 194 conectados / 16 desconectados (mismos que antes del update). Infra devices hicieron flap durante el update pero el anti-flap del monitor los descartó correctamente ("flap descartado"). Sin notificaciones falsas a clientes.

### 25. 5 infra devices DNS fix + 4 client antennas UISP fix (2026-03-01)
**5 infra con DNS 8.8.8.8 inalcanzable**: AP Poblado (.101), ST Nahuapa (.203), ST Recursos (.250), ST Sergio (.189), Sectorial Nahuapa (.223), AP Recursos Sur (.249). Cambiado DNS a 10.1.1.1. Misma causa raíz que Problema #19.

**4 antenas cliente**: .128 y .84 tenían URI viejo (10.1.1.254), .132 y .124 tenían device-specific key desync. Fix: URI corregido / key reseteada + reboot.

**16 antenas sin acceso SSH**: Credenciales desconocidas, requieren acceso físico/web.

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
| `cross_ref_ppp_uisp.py` | Cross-reference PPPoE activo vs UISP stations (2026-02-19) |
| `fix-35-disconnected.sh` | Fix 35 antenas desconectadas: rm running.cfg + kill udapi-bridge |
| `fix-remaining.sh` | Batch 2 de fix para 19 antenas restantes |
| `fix-restart-udapi.sh` | Restart udapi-bridge en 31 antenas post-ZeroTier route |
| `fix3.sh` | Fix últimas 3 antenas (Magda Mora, Ana Esther, Jose Nicolas) |
| `fix53.sh` | Fix 10.10.1.53 + 10.10.1.219 (reset master key) |
| `fix-nicolas.sh` | Nuclear fix 10.10.1.53: delete BD + clean system.cfg + restart |
| `fix-27-missing.sh` | Configurar UISP connection string en 27 antenas sin entrada UISP |
| `fix-decryption-7.sh` | Reset master key en 7 antenas con device-specific keys huérfanas |
| `fix-19-uisp.sh` | Configurar UISP en 4 antenas online de 19 servicios CRM sin enlace NMS |
| `admin-portal/app.py` | Backend admin portal: API endpoints + serve frontend (aiohttp) |
| `admin-portal/static/index.html` | Frontend SPA: 7 pestañas (dashboard, clientes, mensajes, finanzas, registros, soporte, backups) |
| `admin-portal/docker-compose.yml` | Container config, puerto 8092, volumes (bot DB, certs, backups, SSH) |

## Datos Técnicos airOS

- **Config persistente**: `/tmp/system.cfg` (se guarda a flash con `cfgmtd -w -p /etc/`)
- **Config runtime**: `/tmp/running.cfg` (si existe, `udapi-bridge` la usa en lugar de system.cfg). **IMPORTANTE**: udapi-bridge NECESITA running.cfg para guardar device-specific keys tras key exchange. NO eliminarlo si la antena necesita key exchange fresco; en ese caso usar `cp /tmp/system.cfg /tmp/running.cfg`.
- **Proceso UISP**: `udapi-bridge` (hijo con prefijo `{exe}`) - es el que conecta via WebSocket
- **Proceso informd**: `infctld` - controlador inform (menos relevante para conexión UISP)
- **Logs UISP**: `/var/log/unms.log`
- **Logs sistema**: `/var/log/messages`
- **Guardar config**: `cfgmtd -w -p /etc/`
- **MAC Ubiquiti prefixes**: 24:5A:4C, 28:70:4E, 60:22:32, 9C:05:D6, 0C:EA:14, E4:38:83, 70:A7:41, 44:D9:E7, 74:83:C2, 04:18:D6, AC:84:C6, 78:8A:20
- **IMPORTANTE — Fix de antenas**: Siempre usar `edit system.cfg → cfgmtd -w -p /etc/ → reboot`. NO matar procesos manualmente (kill udapi-bridge) — no es confiable, los cambios solo aplican correctamente tras reboot.

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
| Cliente | /misaldo, /miservicio, /miconexion, /reportar, /soporte, /vincular, /cambiarplan + enviar foto comprobante |
| Admin | /red, /clientes, /buscar, /dispositivos, /pppoe, /diagnostico, /caidas, /pagos, /morosos, /reactivar, /cobranza, /sinvincular, /progreso, /mensaje, /aviso, /registrados |
| Todos | /start, /help, /menu + mensajes libres en español via Claude AI |

### Archivos clave del bot
| Archivo | Funcion |
|---------|---------|
| `src/main.py` | Entry point |
| `src/config.py` | Carga .env |
| `src/bot/app.py` | Telegram Application + handlers + schedulers |
| `src/bot/handlers/conversation.py` | Mensajes libres → Tier 1 diagnostico + Claude AI (con filtro + rate limit) |
| `src/bot/handlers/avisos_admin.py` | /aviso, /registrados + aviso scheduler (3 modos) |
| `src/bot/handlers/plan_change.py` | /cambiarplan + aprobacion admin + aplicacion dia 1 |
| `src/bot/handlers/registration.py` | /vincular + fallback soporte humano |
| `src/diagnostics/__init__.py` | Package diagnostico automatico |
| `src/diagnostics/engine.py` | DiagnosticEngine: CRM + UISP + PPPoE + Ping → clasificacion |
| `src/diagnostics/auto_responder.py` | Respuestas automaticas para high/critical + format_diagnostic_context |
| `src/ai/claude_client.py` | Anthropic SDK wrapper con tool use loop + diagnostic_context |
| `src/ai/system_prompt.py` | System prompt dinamico por rol + diagnostico pre-ejecutado |
| `src/ai/tools.py` | 9 tool definitions para Claude |
| `src/ai/tool_executor.py` | Despacha tool calls → UISP/MikroTik |
| `src/integrations/uisp_nms.py` | UISP NMS client + find_device_by_site_id |
| `src/integrations/uisp_crm.py` | UISP CRM client |
| `src/integrations/mikrotik.py` | MikroTik RouterOS API (ping fix librouteros 4.0) |
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
- Anti-flap: confirma caída solo si persiste 3 polls consecutivos (~6 min)
- Responde automáticamente durante incidentes/mantenimiento (sin llamar Claude, $0)
- Notificaciones a clientes: cooldown 30 min por dispositivo, recovery solo si caída >10 min (evita spam por flapping)

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

### Sistema de Diagnostico Automatico 3 Niveles (implementado 2026-02-28)
Cuando un cliente reporta un problema de conexion, el bot ejecuta diagnostico automatico ANTES de llamar a Claude AI:

**Flujo:**
```
Mensaje → Pre-filtro → Rate limit → Incidente/Maint → Intent detection
  → Si es problema conexion: DiagnosticEngine.diagnose()
    → Severidad critical/high → Respuesta automatica ($0)
    → Severidad medium/none → Pasa diagnostico a Claude como contexto (~$0.02)
  → Si NO es problema conexion: Directo a Claude AI (comportamiento anterior)
```

**DiagnosticEngine pasos (asyncio.gather para 3+4):**
1. CRM: servicio → plan, status, unmsClientSiteId
2. UISP NMS: find_device_by_site_id → nombre, modelo, status, signal, IP
3. MikroTik: PPPoE session por IP → username, uptime, profile
4. MikroTik: ping IP (3 paquetes) → success, avg_ms, loss
5. DB: incidentes/mantenimiento activos en zona
6. Clasificacion severidad

**Arbol de clasificacion:**
| Condicion | Severidad | Auto-responde? |
|-----------|-----------|----------------|
| Incidente/mantenimiento zona | critical | Si — "Interrupcion detectada..." |
| Servicio suspendido | critical | Si — "Tu servicio esta suspendido..." |
| Antena offline + sin PPPoE | high | Si — "Tu antena esta desconectada..." |
| Antena online + sin PPPoE | high | Si — "Antena encendida pero sin conexion..." |
| PPPoE activo + ping falla | high | Si — "Problemas de comunicacion..." |
| Senal < -80 dBm | medium | No → Claude con contexto |
| Latencia > 100ms | medium | No → Claude con contexto |
| Packet loss > 0% | medium | No → Claude con contexto |
| Todo OK | none | No → Claude con contexto |

**Intent detection keywords** (`_is_connection_problem`): lento, no jala, sin internet, no conecta, se cae, falla, señal, antena, no tengo internet, etc.

**Archivos:**
| Archivo | Funcion |
|---------|---------|
| `src/diagnostics/engine.py` | DiagnosticResult dataclass + DiagnosticEngine |
| `src/diagnostics/auto_responder.py` | auto_respond() + format_diagnostic_context() |
| `src/bot/handlers/conversation.py` | Capa 2.7: intent detection + engine call |

**Refactors:**
- `/miconexion` y `/reportar` en customer.py ahora usan DiagnosticEngine (eliminada logica duplicada)
- `tool_executor.py` corregido: usa find_device_by_site_id (antes usaba get_device con site ID → 404)
- `mikrotik.py` ping fix: librouteros 4.0 requiere `path("/ping")("", **params)` (no `path("/ping", **params)`)
- `uisp_nms.py`: nuevo metodo find_device_by_site_id() busca en cache por identification.site.id

### Estado del bot (2026-02-28)
- ✅ Desplegado en VPS (217.216.85.65) con Docker
- ✅ Bot renombrado a "AURA" en BotFather (@auralinkmonitor_bot)
- ✅ Botones inline funcionando
- ✅ Claude AI responde con datos reales de UISP y MikroTik
- ✅ Consulta de saldos, dispositivos offline, sesiones PPPoE
- ✅ Pre-filtro y rate limiting implementados
- ✅ Monitor de red corriendo (interval=120s, 25 zonas, 175 endpoints, 18 infra tracked)
- ✅ Comandos /zonas, /incidentes, /monitor, /mantenimiento funcionando
- ✅ Signup autoservicio con ID de servicio y seleccion de zona + fallback soporte humano
- ✅ Clientes ya vinculados excluidos de registro (evita duplicados)
- ✅ Sistema de cobranza automatizada implementado (2026-02-16)
- ✅ Sistema de onboarding interactivo implementado (2026-02-18)
- ✅ Portal de avisos con verificacion de registro y 3 modos (2026-02-25)
- ✅ /cambiarplan: cliente solicita, admin aprueba, aplica dia 1 del mes siguiente (2026-02-25)
- ✅ /registrados: cruce PPPoE vs registros en tiempo real (2026-02-25)
- ✅ Aviso scheduler: re-publica cada 3 dias, transiciona modos, auto-excluye registrados
- ✅ Diagnostico automatico Tier 1: responde problemas claros $0, pasa contexto a Claude para ambiguos (2026-02-28)
- ✅ Ping MikroTik corregido (librouteros 4.0 API change) + find_device_by_site_id (2026-02-28)
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

### Portal de Avisos con Registro Verificado (implementado 2026-02-25)
Sistema de captive portal para avisos a clientes con verificacion de registro en Telegram.

**Arquitectura:**
1. **Portal web** (`avisos-portal` en VPS:8090) — sirve avisos HTML dinamicos
2. **MikroTik NAT** redirige HTTP de address-list `avisos` al portal
3. **Script `populate-avisos`** (cada 5 min) agrega clientes activos a `avisos` (excluye morosos y avisos-visto)
4. **Bot Telegram** (`/aviso`) publica avisos, Claude IA estructura texto libre
5. **Aviso scheduler** (background task) re-publica cada 3 dias y transiciona modos

**3 modos de operacion (rollout por fases):**
| Periodo | Modo | Comportamiento |
|---------|------|----------------|
| Feb 25 → Mar 14 | **soft** | Aviso aparece, verifica registro, pero SIEMPRE da internet. Muestra mensaje diferente si no registrado. |
| Mar 15 → Mar 27 | **medium** | "Ya me registre" bloquea si no registrado. "Lo hare despues" da internet temporal (~5 min). |
| Mar 28 → Mar 31 | **strict** | Solo "Ya me registre". Sin opcion temporal. Debe registrarse o no navega. |
| Abr 1+ | off | Scheduler auto-desactiva todo. |

**Aviso scheduler** (background task en bot):
- Corre cada 6 horas, checa fecha actual
- Re-publica aviso cada 3 dias (limpia avisos-visto, re-puebla avisos)
- Auto-excluye clientes registrados (agrega a avisos-visto)
- Transiciona modo automaticamente segun fecha
- Notifica admin de cada re-publicacion

**Verificacion de registro:**
- Portal lee DB del bot via volume mount Docker (read-only)
- Fuzzy match PPPoE name ↔ customer_links.crm_client_name (case-insensitive, sin espacios)
- En modo soft: siempre permanent dismiss (avisos-visto), muestra status
- En modo medium/strict: bloquea si no registrado

**Comandos admin:**
- `/aviso` — estado del portal
- `/aviso registro` — template hardcoded de registro con features/steps/verify
- `/aviso <texto>` — Claude IA estructura aviso libre
- `/aviso off` — desactiva portal
- `/registrados` — cruce PPPoE vs registros en tiempo real (boton en /admin)

**Archivos:**
| Archivo | Funcion |
|---------|---------|
| `avisos-portal/app.py` | Portal web: HTML dinamico, verificacion, 3 modos |
| `avisos-portal/docker-compose.yml` | Container config + volume mount bot DB |
| `aura-bot/src/bot/handlers/avisos_admin.py` | /aviso, /registrados, scheduler, auto-dismiss |

**Config portal (docker-compose.yml):**
- `ADMIN_TOKEN=auralink-avisos-2026`
- `BOT_DB_PATH=/app/botdata/aura.db`
- Volumes: `/root/.ssh:/root/.ssh:ro`, `./data:/app/data`, `/root/aura-bot/data:/app/botdata:ro`

**MikroTik resources:**
- NAT: `comment="Avisos: redirect HTTP a portal de anuncios"` (disabled when no aviso active)
- Script: `populate-avisos` (excluye morosos y avisos-visto)
- Scheduler: `populate-avisos-schedule` (cada 5 min, disabled when no aviso active)
- Address-lists: `avisos` (clientes que ven aviso), `avisos-visto` (clientes que ya vieron)

### Cambio de Plan por Cliente (implementado 2026-02-25)
Sistema para que clientes soliciten cambio de plan → admin aprueba → aplica dia 1 del mes siguiente.

**Flujo cliente:**
1. `/cambiarplan` (o boton en menu cliente)
2. Verifica cuenta vinculada + no tiene solicitud pendiente
3. Busca secret PPPoE actual via MikroTik
4. Muestra plan actual + botones con planes disponibles
5. Cliente selecciona → se guarda en DB con status `pending`
6. Admin recibe notificacion con botones Aprobar/Rechazar

**Flujo admin:**
- Aprobar: status→approved, notifica cliente "Tu cambio aplica el {fecha}"
- Rechazar: status→rejected, notifica cliente

**Aplicacion automatica (dia 1 de cada mes):**
- BillingScheduler llama `apply_approved_changes()` el dia 1
- Actualiza PPP secret profile + desconecta sesion (para que reconecte con nuevo perfil)
- Marca como `applied` en DB + notifica cliente

**Planes disponibles:**
| Perfil MikroTik | Display |
|-----------------|---------|
| $300 basico 3m/8m | Basico $300 (3M/8M) |
| $500 residencial 4m/12m | Residencial $500 (4M/12M) |
| $800 profesional 5m/15m | Profesional $800 (5M/15M) |
| $1000 empresarial 8m/20m | Empresarial $1,000 (8M/20M) |

**Tabla DB:** `pending_plan_changes` (id, crm_client_id, client_name, telegram_user_id, current_plan, requested_plan, status, requested_at, approved_at, effective_date, applied_at)

**Archivos:**
| Archivo | Funcion |
|---------|---------|
| `src/bot/handlers/plan_change.py` | /cambiarplan + callbacks + apply_approved_changes |
| `src/database/db.py` | Tabla + 5 metodos (create, get, update, get_approved, has_pending) |
| `src/billing/scheduler.py` | Llama apply_approved_changes dia 1 |

### Soporte Humano en Registro (implementado 2026-02-25)
Cuando un cliente no puede vincular su cuenta (sin matches o selecciona "Ninguno"), aparece boton "Contactar Soporte" que:
1. Crea ticket de escalacion en DB
2. Notifica admins via Telegram con datos del cliente
3. Responde al cliente con numero de ticket

**Callback:** `reg_soporte` → `_handle_reg_soporte()` en app.py

### Bugs corregidos en Aura Bot (2026-02-18)

| # | Bug | Archivo | Fix |
|---|-----|---------|-----|
| 1 | `create_payment_report()` faltaba param `crm_payment_id` → TypeError al auto-aprobar transferencias | `db.py` | Agregado parametro con default None |
| 2 | `next_month` calculaba mes actual en vez del siguiente | `receipts.py` | `now.month % 12 + 1` |
| 3 | PPPoE secret name mismatch (CRM "Juan Lopez" vs secret "juanlopez") | `mikrotik.py` | Matching bidireccional + sin espacios + `find_secret_by_ip()` |
| 4 | Condicion duplicada en filter (`"mi "` x2) | `filter.py` | `"mi "` + `"mis "` |
| 5 | Dead code `next_month` en billing_admin | `billing_admin.py` | Misma correccion que #2 |
| 6 | Monitor siempre 0 devices — `device.get("id")` es None, ID esta en `identification.id` | `monitor.py` | `device.get("identification", {}).get("id")` |
| 7 | `nms.get_device(unmsClientSiteId)` retornaba 404 — unmsClientSiteId es site ID no device ID | `tool_executor.py`, `engine.py` | Nuevo `nms.find_device_by_site_id()` busca en cache por identification.site.id |
| 8 | MikroTik ping roto — `api.path("/ping", **params)` no funciona en librouteros 4.0 | `mikrotik.py` | Cambiado a `api.path("/ping")("", **params)` |
| 9 | Ping time parsing — formato `19ms285us` no `19ms` | `mikrotik.py` | Split en "ms" para extraer parte entera |

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
| WAN2 (Sergio) | WAN2-Download | 140M | Deshabilitado (<10Mbps, 2026-02-24) |
| WAN3 (Presidencia40) | WAN3-Download | 60M | Deshabilitado (WAN caida) |
| WAN4 (Presidencia169) | WAN4-Download | 60M | Deshabilitado (WAN caida) |
| WAN5 (StarlinkMini) | WAN5-Download | 180M | OK |
| WAN6 (StarlinkTotin) | WAN6-Download | 180M | Deshabilitado (ISP Force200 issues, 2026-02-27) |
| WAN7 (Chuy1) | WAN7-Download | 90M | Ajustado (era 40M) |
| WAN8 (Chuy2) | WAN8-Download | 90M | Ajustado (era 40M) |
| WAN9 (StarlinkAurora) | WAN9-Download | 180M | OK |
| WAN10 (Chaviton) | WAN10 | 80M | OK (macvlan, era 100M, ISP 100M down/30M up) |

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
- [x] Recalcular PCC divisor — actualizado a :6, 6 WANs activas (WAN2+WAN10 deshabilitados, 2026-02-24)
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

## Auditoría UISP (2026-02-15 → actualizada 2026-02-20)

### Análisis cruzado PPPoE ↔ CRM ↔ NMS
- **222/241 CRM servicios enlazados a endpoints NMS** — todos los 222 sitios NMS endpoint enlazados 1:1 (0 duplicados, 0 huérfanos)
- **19 servicios CRM sin enlace NMS** — todos tienen PPPoE secret pero antena no está en UISP (15 offline, 3 morosos sin acceso SSH, 1 ya enlazada a otro servicio)
- **2 "Luz Mariscal"** en CRM: no son duplicados, son direcciones distintas (Nahuapa vs otro)
- Se eliminaron 4 endpoints huérfanos en auditoría previa: Olivia Cumbre, Alma Gloria, Enrique Pulido, Tule Mabel
- **Duplicado CRM #254 (Kareli Meza Coco)** eliminado ($0 balance, sin servicio)
- **Naming consistente**: NMS usa "Zona, Nombre" / CRM usa "Nombre Zona" — todos hacen match

### PPPoE
- 254 secrets total (clienteprueba deshabilitado, actualizado 2026-02-20)
- ~198 sesiones activas
- 0 sesiones "clienteprueba" — secret deshabilitado, todos migrados a individuales
- 15 clientes en perfil "Morosos" (confirmados legítimos)

### Clienteprueba — RESUELTO (2026-02-17)
Todos los 6 clientes que usaban `clienteprueba` ya tienen secrets individuales. El secret compartido fue deshabilitado.
Ver detalle en Problema Resuelto #10.

### Limpieza realizada (acumulado)
- Eliminados **146 dispositivos fantasma** total (32 via API + 39 via PostgreSQL + 33 via PostgreSQL 2026-02-18 + 42 via PostgreSQL 2026-02-20)
- Eliminados 4 endpoints NMS huérfanos
- Eliminado 1 duplicado CRM
- Corregidas ~20 secuencias PostgreSQL del CRM
- Autorización de 2 dispositivos nuevos (.116, .204)
- Firmware upgrade masivo a XW.v6.3.24 (15+ antenas)
- Fix PCC routing UISP: ZeroTier route + mangle bypass → 35 antenas recuperadas (2026-02-19)
- Bug connection string UISP corregido en 4 archivos backend/frontend (2026-02-19)
- 21 no-clientes eliminados del CRM por user (262→241 servicios) (2026-02-20)
- 7 antenas decryption fix: 6 reseteadas a master key, 3 nuevas aparecieron en UISP (2026-02-20)

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
- [x] Fix masivo UISP — 60→182 conectados, device-specific key desync + PCC routing fueron causas raíz
- [x] 71 fantasmas eliminados — 32 via API + 39 via PostgreSQL
- [x] Fix keys sesión 02-18 — +24 dispositivos recuperados (155→179), reset master key masivo
- [x] Fix PCC→UISP sesión 02-19 — +35 antenas recuperadas (112→182), ZeroTier route permanente
- [x] Connection string UISP corregido — allowSelfSignedCertificate→allowUntrustedCertificate en 4 archivos
- [x] 4 infra desconectadas UISP — DNS no resolvía server.auralink.link, cambiado a 10.1.1.1 (MikroTik proxy), 4 phantoms eliminados (2026-02-25)
- [ ] ~20 dispositivos desconectados no autorizados — posibles phantoms o antenas sin configurar (42 phantoms eliminados 2026-02-20)
- [ ] ~23 antenas Ubiquiti con PPPoE pero sin UISP — credenciales SSH desconocidas, requieren acceso físico
- [ ] 19 servicios CRM sin enlace a endpoint NMS — antenas no están en UISP (15 offline, 3 morosos sin acceso, 1 ya enlazada)
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
- [x] Recalcular PCC divisor — :6 con 6 WANs activas (WAN2 deshabilitada <10Mbps + WAN10 deshabilitada, 2026-02-24)
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
- [ ] 172.168.x.x — removido de local-networks, pendiente migrar a RFC1918 correcto
- [x] Ping Watchdog verificado — 175/176 antenas ya lo tenían activo (target=gateway, period=300s, retry=3)
- [x] MikroTik en UISP — agregado como Third Party (blackBox) en Matriz Tomatlan
- [x] Mangle Infra→UISP — fuerza tráfico infra al VPS por WAN8 (evita CGNAT Starlink)
- [x] ZeroTier route para UISP VPS — 217.216.85.65/32 via 10.147.17.92 + mangle Skip-PCC-for-UISP-VPS
- [x] 35 antenas desconectadas UISP — recuperadas 100% via ZeroTier route + udapi-bridge restart
- [x] Bug connection string UISP — corregido allowSelfSignedCertificate en 4 archivos (api.js, device-ws.js, unms-key.js, frontend)
- [x] Verificar connection string flag tras actualizaciones UISP — re-aplicado en update v3.0.159 (2026-03-01), frontend cambió a `index-9_kxL8KA.js`
- [x] CRM limpieza — user eliminó 21 no-clientes (262→241 servicios)
- [x] 42 phantoms UISP eliminados — segunda ronda limpieza BD (total acumulado: 146)
- [x] 7 antenas decryption fix — 6/7 reseteadas a master key, 3 nuevas en UISP (+hugomanzot, veronicatenoriot, dianacornejoc)
- [ ] 6 MACs decryption restantes — diftomatlan (inalcanzable), rogue Pilitas (externo), 2 desconocidas, Maria Cristina (moroso), danielayonc (desconectada)
- [ ] Dispositivo "Recursos" en UISP — MAC e4:38:83:b8:64:e5, verificar si es infra real o phantom
- [x] PCC WAN10 reglas mangle deshabilitadas — 3 reglas (mark-connection, mark-routing, mark-packet) estaban activas con interfaz deshabilitada, causando 12.5% tráfico sin PCC sticky (2026-02-24)
- [x] WAN2 Sergio deshabilitada — macvlan estaba disabled, se habilitó y verificó pero entrega <10 Mbps, user pidió deshabilitar (2026-02-24)
- [x] PCC recalculado a :6 — 6 WANs activas, 0 slots vacíos, 100% tráfico con PCC sticky (2026-02-24)
- [x] ucrm CPU limit verificado — docker update --cpus=2 sigue aplicado (2026-02-24)
- [x] Avisos Portal implementado — /aviso en bot + API admin en portal + Claude IA estructura avisos (2026-02-24)
- [x] PtP Colmenares fix — CPU 100% por 80MHz en Rocket 5AC Lite, user bajó a 40MHz + upgrade XC.v8.7.19 (2026-02-24)
- [x] ucrm CPU spikes — causaban desconexiones masivas UISP (416% CPU en cron jobs), limitado a 2 CPUs (2026-02-24)
- [x] Avisos Portal phased rollout — 3 modos (soft/medium/strict), verificacion registro, auto-dismiss registrados (2026-02-25)
- [x] Aviso scheduler — re-publica cada 3 dias, transiciona modos automaticamente, notifica admin (2026-02-25)
- [x] /cambiarplan — cliente solicita cambio, admin aprueba/rechaza, aplica dia 1 del mes siguiente (2026-02-25)
- [x] Soporte humano en registro — boton "Contactar Soporte" cuando /vincular falla, crea ticket + notifica admin (2026-02-25)
- [x] /registrados — cruce PPPoE vs registros en tiempo real, boton en panel admin (2026-02-25)
- [x] Portal avisos-portal lee DB del bot — volume mount Docker read-only para verificar registros (2026-02-25)
- [x] 4 infra desconectadas por DNS — cambiado DNS a 10.1.1.1 (MikroTik), 4/4 reconectadas, 4 phantoms eliminados (2026-02-25)
- [ ] Verificar DNS en otros infra devices — podrían tener 8.8.8.8 inalcanzable, misma causa raíz que Problema #19
- [x] Avisos: auto-dismiss al vincular — registration.py remueve de avisos + agrega a avisos-visto inmediatamente (2026-02-26)
- [x] Avisos: "Lo haré después" → 24h — dismiss_temp ahora agrega a avisos-visto con timeout=24h (era 5 min) (2026-02-26)
- [x] Avisos: populate-avisos corregido — ahora limpia de avisos a los que ya están en avisos-visto por address (2026-02-26)
- [x] /progreso sync — ahora sincroniza CRM antes de mostrar datos + lista de registrados con nombres y fechas (2026-02-26)
- [x] 10.1.1.212 + 10.1.1.229 — device-specific key huérfana causaba RPC timeout, reseteadas a master key, ambas conectadas (2026-02-26)
- [x] Auto-dismiss avisos fix — reescrito matching: usa IP del CRM en vez de nombre, fallback a find_secret_by_name() (2026-02-26)
- [x] WAN10 Chaviton configurada — macvlan bajo ether8-WAN, IP fija 192.168.102.10/24, PCC :6/2, CAKE 80M, netwatch 8.8.8.8 (2026-02-27)
- [x] WAN6 StarlinkTotin deshabilitada — ISP Force200 issues, user desconectó (2026-02-27)
- [x] WAN9 StarlinkAurora re-habilitada — netwatch la deshabilitó por false-down (8.8.8.8 via CGNAT), cambiado a monitorear 100.64.0.1 (2026-02-27)
- [x] QUIC bloqueado — UDP 443 drop en forward chain, fuerza TCP para QoS SNI (96% tráfico video/social usaba QUIC) (2026-02-27)
- [x] QoS SNI wildcards corregidos — `*keyword*` formato en RouterOS 7 (no `*.domain.com`) en 7 reglas (2026-02-27)
- [ ] WAN11 pendiente — macvlan bajo ether8-WAN (192.168.104.10/24), gateway no responde, ISP debe activar
- [ ] Cambium Force 200 AP — enlace caído, user revisará físicamente el AP
- [x] MikroTik scripts cleanup — 10 scripts + 12 schedulers obsoletos eliminados (2026-02-28)
- [x] MikroTik backup diario restaurado — scheduler backup-diario-schedule 3AM + VPS pull 4:30AM (2026-02-28)
- [x] Admin portal backups — pestaña Backups multi-dispositivo con agrupación mes→día (2026-02-28)
- [x] Diagnostico automatico Tier 1 — DiagnosticEngine + auto_responder, responde problemas claros $0, pasa contexto a Claude (2026-02-28)
- [x] MikroTik ping fix — librouteros 4.0 requiere path("/ping")("", **params), time parsing "19ms285us" (2026-02-28)
- [x] find_device_by_site_id — unmsClientSiteId es site ID no device ID, nuevo metodo en uisp_nms.py (2026-02-28)
- [x] /miconexion y /reportar refactorizados — usan DiagnosticEngine en vez de logica inline duplicada (2026-02-28)
- [x] Avisos solo para aurora — desactivado populate-avisos scheduler, limpiada address-list, solo aurora (10.10.0.254) para pruebas (2026-03-01)
- [x] 10.1.1.229 Sectorial Cumbre CPU fix — airview.status=disabled, CPU idle 7%→50%, UISP conexión estable (2026-03-01)
- [x] Monitor anti-spam clientes — anti-flap 3 polls, cooldown por device_id, recovery solo >10 min (2026-03-01)

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

## Estado Actual (2026-03-03)
- **219 dispositivos** en UISP: **189 conectados**, ~24 desconectados autorizados, 35 phantoms eliminados hoy
- **247 CRM servicios activos** (+6 nuevos clientes) + 60 quoted (borradores viejos) + 3 ended = 310 total
- **258 PPPoE secrets** (~207 sesiones activas), clienteprueba deshabilitado, pool 506 IPs
- **MikroTik**: PCC src-address:**7** en **7 WANs activas**, fasttrack OFF, QoS CAKE funcional, QUIC bloqueado, SNI wildcards corregidos
- **WANs activas (7)**: WAN1 (Starlink2, :7/0), WAN5 (StarlinkMini, :7/1), WAN6 (StarlinkTotin, :7/2), WAN7 (Chuy1, :7/3), WAN8 (Chuy2, :7/4), WAN9 (StarlinkAurora, :7/5), WAN10 (Chaviton macvlan, :7/6)
- **WANs deshabilitadas**: WAN2 (Sergio <10Mbps), WAN3/WAN4 (Presidencia)
- **WAN6 reactivada**: ISP Force200 issues resueltos, reconectada 2026-03-03. Netwatch src-address corregido a 192.168.4.51
- **WAN11 pendiente**: macvlan bajo ether8-WAN (192.168.104.10/24), ISP no activo — necesita slot :7/x cuando se active (requiere recalcular a :8)
- **25 morosos** en address-list (era 15 en Mar 1)
- **UISP VPS routing**: Todo tráfico de antenas al VPS va por ZeroTier (mangle Skip-PCC + ruta estática 217.216.85.65/32 via 10.147.17.92)
- **Connection string UISP**: Flag `allowUntrustedCertificate` corregido en 4 archivos del contenedor unms-api
- **ucrm CPU limitado**: `docker update --cpus=2 ucrm` aplicado para evitar spikes que desconectan antenas (se pierde al actualizar UISP)
- **Aura Bot "AURA"** en produccion en VPS con Docker — diagnostico automatico + avisos portal + cambio plan + soporte humano
- **Diagnostico Tier 1**: problemas claros (antena off, suspendido, sin PPPoE) → respuesta automatica $0. Ambiguos (lento, señal baja) → pasa contexto pre-ejecutado a Claude (~$0.02, sin re-ejecutar tools)
- **Avisos Portal EN PRODUCCION**: 134 clientes en avisos, 11 en avisos-visto (registrados), populate-avisos habilitado (cada 5 min)
- **Aviso scheduler HABILITADO**: AVISO_SCHEDULER_ENABLED=true, auto-transiciones: soft (→Mar15) → medium (→Mar25) → strict (→Mar31) → persistent (Abr1+)
- **Avisos 4 fases**: soft (informativo, dismiss libre), medium (verifica estricto, "después" da internet), strict/persistent (solo "Ya me registré", 5 min internet si no registrado)
- **Avisos dismiss mejorado**: Registrados se excluyen inmediatamente al vincular. "Lo haré después" da 24h de gracia (soft/medium). Script populate-avisos limpia registrados en cada ejecución.
- **Cambio de plan**: /cambiarplan disponible para clientes, admin aprueba, aplica dia 1 del mes siguiente. 1 pendiente de aprobación.
- **Monitor de red** corriendo: 25 zonas, 176 endpoints, 18 infra tracked, polling cada 2 min, anti-flap 3 polls, cooldown clientes por device_id, recovery solo >10 min
- **Sistema de cobranza** activo: BILLING_START_MONTH=2026-04, listo para abril
- **Sistema de onboarding**: /sinvincular, /progreso (con sync + lista registrados), /mensaje — **13 clientes vinculados** (era 8)
- **Portal morosos** operativo: HTTP + HTTPS redirect, sync-morosos cada 1 min, Telegram permitido
- **Admin portal** en produccion: https://server.auralink.link:8092 — 7 pestañas (Dashboard, Clientes, Mensajes, Finanzas, Registros, Soporte, Backups)
- **Backups automatizados**: MikroTik backup-diario (3AM) + VPS pull SCP (cron 4:30/4:35 AM), retencion 14 dias, descargables desde admin-portal pestaña Backups
- **SSL cert**: Let's Encrypt expira 17 mayo 2026 (~75 días)
- **VPS saludable**: Load 0.49, RAM 73% libre, Disco 88% libre, 17 containers all healthy
- **172.168.x.x restaurado**: re-agregado a local-networks (fix temporal hasta migrar a RFC1918)
- **~23 antenas sin UISP**: tienen PPPoE pero credenciales SSH desconocidas, requieren acceso fisico
- **Prioridad**: vincular clientes a Telegram antes de abril (13/258 = 5%, avisos portal activado para empujar registros)
- **UISP v3.0.159**: Actualizado 2026-03-01 (era v3.0.151). CRM v4.5.33. Connection string flag + ucrm CPU limit re-aplicados post-update.
