# MikroTik Balanceador - Análisis Completo y Recomendaciones

**Generado**: 14 Nov 2025
**Router**: Balanceador (10.147.17.11)
**Usuario**: admin

---

## 1. RESUMEN EJECUTIVO

Tu router MikroTik está **bien configurado pero incompleto**:

✅ **Funciona:**
- Balanceo de carga entre 9 ISPs
- QoS granular para clientes individuales (200+ queues)
- NAT masquerade en todas las WANs
- Clasificación de tráfico (video, VoIP, chat, DNS)

❌ **Falta:**
- Health check (netwatch) para detectar ISPs caídos
- Failover automático cuando un ISP se cae
- Rutas específicas con routing marks (todas usan tabla "main")
- WAN10 (Aurora) deshabilitado/inválido

⚠️ **Riesgo:**
Si un ISP cae, **el tráfico de esos clientes se interrumpe** porque no hay reconexión automática.

---

## 2. ANÁLISIS DETALLADO

### 2.1 RUTAS (IP Routes)

**Estado**: Parcialmente correcta pero simplista

```
Rutas de default (0.0.0.0/0):
- 192.168.40.1 (WAN3 - Presidencia)      [As+ Active Static]
- 192.169.1.1 (WAN4 - Presidencia)       [As+ Active Static]
- 192.168.40.1 (WAN3 duplicada)          [As+ Active Static]
- 192.168.4.1 (ether4-WAN6)              [As+ Active Static]
- 192.168.1.1 (WAN2 - Sergio)            [As+ Active Static]
- 192.168.2.1 (ether3-WAN5)              [As+ Active Static]
- 192.168.8.1 (WAN10 - Aurora)           [Is INACTIVE - deshabilitada]
- 192.168.201.1 (ether1-WAN1)            [DAd+ Dynamic]
- 100.64.0.1 (ether7-WAN9)               [DAd+ Dynamic]
- 192.168.5.1 (ether6-WAN8)              [DAd+ Dynamic]
- 192.168.101.1 (ether5-WAN7)            [DAd+ Dynamic]
```

**Problemas encontrados:**

1. **No hay rutas con routing-mark**: Las mangle rules marcan con:
   - `routing-mark=to_isp1, to_isp2, ... to_isp9`
   - Pero NO existen rutas que usen estos marks
   - Resultado: Los marks se ignoran, se usa la tabla "main"

2. **WAN10 está INACTIVA**: Gateway 192.168.8.1 nunca responde
   - Probablemente la interfaz Aurora no tiene conectividad
   - Debería deshabilitarse la regla mangle para WAN10

3. **Rutas duplicadas**: WAN3 aparece 2 veces
   - Es redundancia (bueno) pero podría optimizarse

4. **Flags confusos**:
   - `As+` = Active Static (configuración manual)
   - `Is` = Inactive Static
   - `DAd+` = Dynamic, Active default
   - `DAc` = Dynamic, Active, Connected

---

### 2.2 HEALTH CHECK (Netwatch)

**Estado**: NO CONFIGURADO ❌

```
/tool netwatch print
[vacío]
```

**¿Qué significa?**
- No hay monitoreo de si los ISPs están activos/caídos
- Si un gateway no responde, el router **NO lo detecta**
- El tráfico se envía a un ISP caído hasta timeout

**Impacto**:
- Pérdida de conexión de 5-30 segundos cuando un ISP cae
- Clientes afectados: Los que se balancearon a ese ISP

---

### 2.3 QUEUES (QoS)

**Estado**: Muy bien configurado ✅

```
Total de queues: 200+
Tipos:
1. Simple queues por cliente (individual IP)
2. Límites personalizados por cliente
3. Prioridades definidas
4. Burst allowance para picos
```

**Ejemplos de configuración:**

```
Cliente: ST SEDER (199.168.0.118)
├─ limit-at: 768k DOWN / 2M UP (garantizado)
├─ max-limit: 1M DOWN / 2M UP (máximo)
└─ Priority: 8 (baja prioridad, compartirá si otros necesitan)

Cliente: Contraloria (172.168.8.112)
├─ limit-at: 0 / 0 (sin garantía)
├─ max-limit: 4M DOWN / 5M UP
└─ Priority: 8

Cliente: Fede2 (172.168.8.152) - PRIORITARIO
├─ limit-at: 1M DOWN / 1M UP (garantizado)
├─ max-limit: 1M DOWN / 2M UP
├─ burst-limit: 2M DOWN / 3M UP (puede usar más si disponible)
├─ burst-time: 15s / 5s
└─ Priority: 5 (alta prioridad)
```

**Problemas detectados:**

1. **Muchas queues deshabilitadas (D)**: ~150 de 200 están inactivas
   - Probablemente clientes PPPoE sin servicio activo
   - Debería limpiarlas periodicamente

2. **Límites muy restrictivos en algunos**: Hotel Hacienda tiene 1k/1k (1 Mbps)
   - ¿Es intencional o error?

3. **Sin prioridad por tipo de tráfico**: Aunque hay packet marks (rtp, video, chat)
   - No hay queues tree que usen estos packet marks
   - El QoS de application-specific no se aplica

---

## 3. PROBLEMAS CRÍTICOS Y SOLUCIONES

### PROBLEMA 1: Sin Health Check → ISPs caídos no se detectan

**Síntomas**:
- Clientes se quejan que internet se cae 10-30 segundos
- Solo se recuperan por timeout TCP

**Causa**:
- Sin netwatch, el router asume todos los gateways están vivos
- Envía tráfico a un ISP caído

**Solución**:
Configurar health check para cada ISP:

```mikrotik
/tool netwatch add host=192.168.40.1 comment="WAN3-Presidencia" up-script="/routing route enable [find where dst-address=0.0.0.0/0 && gateway=192.168.40.1]" down-script="/routing route disable [find where dst-address=0.0.0.0/0 && gateway=192.168.40.1]"

/tool netwatch add host=192.169.1.1 comment="WAN4-Presidencia" ...
/tool netwatch add host=192.168.4.1 comment="WAN6-ether4" ...
/tool netwatch add host=192.168.1.1 comment="WAN2-Sergio" ...
/tool netwatch add host=192.168.2.1 comment="WAN5-ether3" ...
/tool netwatch add host=192.168.201.1 comment="WAN1-ether1" ...
/tool netwatch add host=100.64.0.1 comment="WAN9-ether7" ...
/tool netwatch add host=192.168.5.1 comment="WAN8-ether6" ...
/tool netwatch add host=192.168.101.1 comment="WAN7-ether5" ...
```

**Mejora**: Detección en <1 segundo, failover automático

---

### PROBLEMA 2: Mangle rules marcan pero no hay rutas con routing-mark

**Síntomas**:
- Tráfico no se distribuye según per-connection-classifier
- Algunos clientes siempre usan el mismo ISP (por coincidencia de ruta default)

**Causa**:
- Reglas 3-11 marcan con `routing-mark=main`
- Reglas 33-40 marcan con `routing-mark=to_isp1, to_isp2, ...`
- Pero NO existen rutas que usen estos marks

**Solución**:
Crear rutas con routing marks para cada ISP:

```mikrotik
/ip route add dst-address=0.0.0.0/0 gateway=192.168.40.1 routing-mark=to_isp1 comment="WAN3-Presidencia"
/ip route add dst-address=0.0.0.0/0 gateway=192.169.1.1 routing-mark=to_isp2 comment="WAN4-Presidencia"
/ip route add dst-address=0.0.0.0/0 gateway=192.168.4.1 routing-mark=to_isp3 comment="WAN6-ether4"
/ip route add dst-address=0.0.0.0/0 gateway=192.168.1.1 routing-mark=to_isp4 comment="WAN2-Sergio"
/ip route add dst-address=0.0.0.0/0 gateway=192.168.2.1 routing-mark=to_isp5 comment="WAN5-ether3"
/ip route add dst-address=0.0.0.0/0 gateway=192.168.201.1 routing-mark=to_isp6 comment="WAN1-ether1"
/ip route add dst-address=0.0.0.0/0 gateway=100.64.0.1 routing-mark=to_isp7 comment="WAN9-ether7"
/ip route add dst-address=0.0.0.0/0 gateway=192.168.5.1 routing-mark=to_isp8 comment="WAN8-ether6"
/ip route add dst-address=0.0.0.0/0 gateway=192.168.101.1 routing-mark=to_isp9 comment="WAN7-ether5"
```

**Mejora**: Balanceo real activado, carga distribuida entre ISPs

---

### PROBLEMA 3: WAN10 (Aurora) está inactivo pero marcado en mangle

**Síntomas**:
- Regla mangle #12 intenta usar WAN10
- Pero la ruta no responde (192.168.8.1)
- Puede causar timeouts para clientes asignados a WAN10

**Causa**:
- Interfaz no está configurada correctamente
- O ISP Aurora no tiene servicio activo

**Solución Temporal**:
Deshabilitar las reglas mangle para WAN10:

```mikrotik
/ip firewall mangle disable 12,22,32,41
```

**Solución Permanente**:
1. Verificar por qué WAN10 no responde
2. O eliminar completamente la configuración de WAN10

---

### PROBLEMA 4: QoS sin aplicación de application-specific priorities

**Síntomas**:
- Aunque se marcan paquetes (video, VoIP, chat)
- No hay jerarquía de queues que respete estos marks

**Causa**:
- Existen packet marks en mangle (reglas 45-54)
- Pero no hay queues tree que los use

**Solución**:
Crear queue tree para aplicar QoS basado en application-specific:

```mikrotik
/queue tree add name="VoIP-Priority" parent=global-in queue=pcq-download-default packet-marks=rtp priority=1
/queue tree add name="Video-Normal" parent=global-in queue=default packet-marks=video priority=3
/queue tree add name="Chat-Low" parent=global-in queue=default-small packet-marks=chat priority=7
```

---

## 4. PLAN DE MEJORA RECOMENDADO

### FASE 1 (CRÍTICA - Implementar inmediatamente):
```
[ ] 1. Deshabilitar WAN10 en mangle rules (12, 22, 32, 41)
[ ] 2. Configurar health check (/tool netwatch)
[ ] 3. Crear rutas con routing-mark para cada ISP
Tiempo estimado: 30 minutos
Beneficio: ISPs caídos se detectan, failover automático
```

### FASE 2 (IMPORTANTE - Próximas 2 semanas):
```
[ ] 4. Auditar queues deshabilitadas (limpiar las inactivas)
[ ] 5. Implementar queue tree para QoS por application
[ ] 6. Revisar límites de ancho de banda (algunos muy restrictivos)
Tiempo: 2 horas
Beneficio: Mejor utilización, menor desperdicio de ancho
```

### FASE 3 (MEJORA - Próximo mes):
```
[ ] 7. Implementar logging de ISP failovers
[ ] 8. Crear alertas en Telegram/Email para caídas
[ ] 9. Dashboard de monitoreo de estado de ISPs
Tiempo: 4 horas
Beneficio: Visibilidad, respuesta rápida a problemas
```

---

## 5. CHECKLIST DE VALIDACIÓN

Después de implementar cambios, verificar:

```
[ ] ping 8.8.8.8 funciona desde todos los ISPs
[ ] Apagar ISP1, verificar que los clientes se reconecten en <1s
[ ] Apagar ISP2, verificar automático failover
[ ] Revisar logs: /log print where message~"WAN"
[ ] Ejecutar speed test desde diferentes clientes
[ ] Verificar video streams en clientes prioritarios
[ ] Revisar uso de bandwidth por ISP: /ip firewall nat print stats
```

---

## 6. ESTADÍSTICAS ACTUALES

```
Interfaces WAN activas: 9/10 (WAN10 inactiva)
Clientes con QoS: 200+
Queues activas: ~50
Queues inactivas (PPPoE): ~150

Ancho de banda teórico (suma límites max):
- Presidencia: 9M (WAN3 + WAN4)
- Sergio: 2M (WAN2)
- Otros: ~20M (WAN1, 5, 6, 7, 8, 9)
Total máximo: ~31M agregado
```

---

## 7. RECOMENDACIONES FINALES

1. **Implementar health check inmediatamente** - Es crítico para confiabilidad
2. **Limpiar queues inactivas** - Reduce la carga de configuración
3. **Auditar límites de ancho** - Algunos parecen errores (1k/1k)
4. **Documentar la configuración** - Agregar comentarios en cada regla
5. **Hacer backup** - `/system backup save name=balanceador_20251114`
6. **Testear failover** - Desconectar ISPs uno por uno para verificar

---

**¿Necesitas que implemente alguno de estos cambios?**
Puedo hacerlo vía SSH si lo deseas.

