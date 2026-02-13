# MikroTik Balanceador - Análisis de Configuración

## Información General
- **Router**: Balanceador
- **IP**: 10.147.17.11/24
- **Interfaces LAN**: SFP-LAN (múltiples conexiones)
- **Número de WANs**: 10 (9 activos + 1 deshabilitado)

---

## FIREWALL NAT - REGLAS SRCNAT (Masquerade)

Todas las interfaces WAN tienen reglas de masquerade para permitir que el tráfico salga:

| # | Interface | Estado |
|---|-----------|--------|
| 0 | back-to-home-vpn | DESHABILITADO (D) |
| 1 | ether1-WAN1 | Activo |
| 2 | WAN2 macvlan Sergio | Activo |
| 3 | WAN3 macvlan 40 Presidencia | Activo |
| 4 | WAN4 macvlan169 Presidencia | Activo |
| 5 | ether3-WAN5 | Activo |
| 6 | ether4-WAN6 | Activo |
| 7 | ether5-WAN7 | Activo |
| 8 | ether6-WAN8 | Activo |
| 9 | ether7-WAN9 | Activo |
| 10 | WAN10 macvlan 8.1 Aurora | INVÁLIDO (I) |

**Conclusión NAT**: Configuración básica, todas las interfaces enmascaradas correctamente.

---

## FIREWALL MANGLE - REGLAS DE BALANCEO

### SECCIÓN 1: Balanceo por Per-Connection-Classifier (Reglas 3-12)

**Propósito**: Distribuir conexiones entre los 9 ISPs por dirección fuente del cliente

| Regla | Origen | Destino | Per-Connection-Classifier | Estado |
|-------|--------|---------|---------------------------|--------|
| 3 | SFP-LAN | - | src-address:10/0 → WAN1_conn | ✓ Activo |
| 4 | SFP-LAN | - | src-address:10/1 → WAN2_conn | ✓ Activo |
| 5 | SFP-LAN | - | src-address:10/2 → WAN3_conn | ✓ Activo |
| 6 | SFP-LAN | - | src-address:10/3 → WAN4_conn | ✓ Activo |
| 7 | SFP-LAN | - | src-address:10/4 → WAN5_conn | ✓ Activo |
| 8 | SFP-LAN | - | src-address:10/5 → WAN6_conn | ✓ Activo |
| 9 | SFP-LAN | - | src-address:10/6 → WAN7_conn | ✓ Activo |
| 10 | SFP-LAN | - | src-address:10/7 → WAN8_conn | ✓ Activo |
| 11 | SFP-LAN | - | src-address:10/8 → WAN9_conn | ✓ Activo |
| 12 | SFP-LAN | - | src-address:10/9 → WAN10_conn | ✗ DESHABILITADO |

**Mecanismo**: Cada cliente obtiene un hash basado en su IP y se asigna a un ISP específico.

---

### SECCIÓN 2: Mark-Routing por Connection Mark (Reglas 13-22)

**Propósito**: Rutear tráfico marcado a través del routing mark correcto

Todas las conexiones marcadas en el paso anterior se marcan con routing-mark="main"

| Reglas | Connection Mark | Routing Mark | Estado |
|--------|-----------------|--------------|--------|
| 13-21 | WAN1_conn - WAN9_conn | main | ✓ Todos Activos |
| 22 | WAN10_conn | main | ✗ DESHABILITADO |

---

### SECCIÓN 3: Marcas por ISP Individual (Reglas 23-32)

**Propósito**: Marcar conexiones TCP por interfaz de entrada (backup/redundancia)

| Regla | Interface | Connection Mark | Protocolo | Estado |
|-------|-----------|-----------------|-----------|--------|
| 23 | ether1-WAN1 | isp1_conn | TCP | ✓ Activo |
| 24 | WAN2 macvlan Sergio | isp2_conn | TCP | ✓ Activo |
| 25 | WAN3 macvlan 40 | isp3_conn | TCP | ✓ Activo |
| 26 | WAN4 macvlan169 | isp4_conn | TCP | ✓ Activo |
| 27 | ether3-WAN5 | isp5_conn | TCP | ✓ Activo |
| 28 | ether4-WAN6 | isp6_conn | TCP | ✓ Activo |
| 29 | ether5-WAN7 | isp7_conn | TCP | ✓ Activo |
| 30 | ether6-WAN8 | isp8_conn | TCP | ✓ Activo |
| 31 | ether7-WAN9 | isp9_conn | TCP | ✓ Activo |
| 32 | WAN10 macvlan Aurora | isp10_conn | TCP | ✗ DESHABILITADO |

---

### SECCIÓN 4: Mark-Routing por ISP (Reglas 33-40)

**Propósito**: Asignar routing marks individuales para cada ISP

| Regla | Connection Mark | Routing Mark | Estado |
|-------|-----------------|--------------|--------|
| 33 | isp1_conn | to_isp1 | ✓ Activo |
| 34 | isp2_conn | to_isp2 | ✓ Activo |
| 35 | isp3_conn | to_isp3 | ✓ Activo |
| 36 | isp4_conn | to_isp4 | ✓ Activo |
| 37 | isp5_conn | to_isp5 | ✓ Activo |
| 38 | isp6_conn | to_isp6 | ✓ Activo |
| 39 | isp7_conn | to_isp7 | ✓ Activo |
| 40 | isp8_conn | to_isp8 | ✓ Activo |
| 41 | WAN10_conn | to_isp10 | ✗ DESHABILITADO |

---

### SECCIÓN 5: Balanceo PCC (Per-Connection Classifier) - DESHABILITADO

**Reglas 42-44**: Balanceo avanzado basado en connection-rate

| Regla | Protocolo | Puertos | Estado |
|-------|-----------|---------|--------|
| 42 | TCP | 80,443 | ✗ DESHABILITADO |
| 43 | TCP | 80,443 | ✗ DESHABILITADO |
| 44 | TCP | 80,443 | ✗ DESHABILITADO |

**Nota**: Estas reglas están deshabilitadas, probablemente porque el balanceo por Per-Connection-Classifier (Sección 1) es suficiente.

---

### SECCIÓN 6: Clasificación de Tráfico (Reglas 45-54)

**Propósito**: Marcar paquetes específicos para QoS/Priority

| Regla | Tipo | Layer7/Puerto | Packet Mark | Estado |
|-------|------|---------------|-------------|--------|
| 45 | VoIP/Juegos | UDP 10000-20000 (RTP) | rtp | ✓ Activo |
| 46 | Google Meet | UDP 3478,5349 (STUN) | meet | ✓ Activo |
| 47 | WhatsApp | Layer7: whatsapp | chat | ✓ Activo |
| 48 | YouTube | Layer7: youtube | video | ✓ Activo |
| 49 | Netflix | Layer7: netflix | video | ✓ Activo |
| 50 | Twitch | Layer7: twitch | video | ✓ Activo |
| 51 | Facebook | Layer7: facebook | social | ✓ Activo |
| 52 | Instagram | Layer7: instagram | social | ✓ Activo |
| 53 | X / Twitter | Layer7: x | social | ✓ Activo |
| 54 | DNS | UDP 53 | dns | ✓ Activo |

---

## ANÁLISIS Y RECOMENDACIONES

### ✅ Lo que funciona bien:

1. **Balanceo robusto**: Per-Connection-Classifier distribuye uniformemente
2. **Redundancia**: Hay reglas de backup por ISP individual
3. **QoS configurado**: Clasificación de tráfico para priorizar servicios críticos
4. **9 ISPs activos**: Sistema escalable y resiliente

### ⚠️ Problemas detectados:

1. **WAN10 deshabilitado**: Está marcado como INVÁLIDO en direcciones IP, probablemente interfaz no lista
2. **No hay routing rules configuradas**: Las reglas de mangle marcan, pero falta ver `/ip route` para confirmar que existen las rutas con los marks
3. **No hay failover explícito**: Si un ISP cae, no hay mecanismo visible de reconexión automática

### 🔧 Recomendaciones:

1. **Verificar WAN10**: ¿Por qué está deshabilitado? ¿Falta configuración?
2. **Revisar rutas**: Necesito ver `/ip route` para confirmar que cada routing-mark tiene su ruta
3. **Agregar health check**: Considerar usar `/tool netwatch` para monitorear ISPs y cambiar rutas si alguno cae
4. **Optimizar PCC**: Las reglas 42-44 (PCC) podrían ayudar si hay desbalanceo

---

¿Quieres que revise:
- Las rutas (`/ip route print`)?
- Las políticas de health check (`/tool netwatch`)?
- La configuración de queues para QoS?
- Algo más específico?
