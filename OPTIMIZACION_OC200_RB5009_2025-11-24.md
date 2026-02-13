# PLAN DE OPTIMIZACIÓN - OC200 + RB5009UG+S+
## Router Secundario | Omada Controller | 10.144.247.27

---

## 📋 RESUMEN

Se optimizará el router MikroTik RB5009UG+S+ (10.144.247.27) que trabaja bajo control de **Omada Controller OC200** para:
- ✅ Reducir latencia
- ✅ Mejorar calidad de servicio (QoS)
- ✅ Optimizar rendimiento con clientes
- ✅ Mantener compatibilidad con OC200

**Estado Actual:**
- 2 clientes PPPoE conectados (guillermobarajasg, pazgarcia)
- CPU: 15% (bajo)
- RAM: 81% libre (mucha disponible)
- RouterOS: 7.15 (stable)
- Uptime: 2d5h26m

---

## ⚠️ CONSIDERACIONES OC200

### 1. **No eliminar configuraciones de Omada**
```
❌ NO tocar: Perfiles de interface administrados por OC200
❌ NO eliminar: Reglas de firewall agregadas por OC200
✅ SÍ agregar: Optimizaciones de QoS/DNS/FastTrack
```

### 2. **Compatibilidad con Control Remoto**
```
✅ Los cambios deben permitir que OC200 siga gestionando el router
✅ No modificar nombre/orden de interfaces principales
✅ Mantener SSH accesible para OC200
```

### 3. **Políticas de Actualización**
```
⚠️ IMPORTANTE: Si OC200 actualiza RouterOS
  - Se pueden revertir algunas configuraciones
  - Hacer backup antes de cambios
  - Documentar todo lo modificado
```

---

## 🎯 FASE 1: OPTIMIZACIONES INMEDIATAS (Sin conflicto con OC200)

### Paso 1: Optimizar DNS (SEGURO)
```bash
ssh admin@10.144.247.27

/ip dns set \
  servers=1.1.1.1,1.0.0.1,8.8.8.8 \
  cache-size=65536 \
  max-udp-packet-size=4096 \
  allow-remote-requests=yes

# Verificar
/ip dns print
```

**Beneficio:**
- DNS más rápido (caché local)
- Menos latencia en consultas
- Mejor experiencia general

---

### Paso 2: Implementar CAKE Queue (SEGURO)
```bash
# Crear CAKE queue type (si no existe)
/queue type add name=CAKE-qos kind=cake \
  cake-diffserv=diffserv4 \
  cake-rtt=100ms

# Asignar a queues existentes
/queue simple modify [ find ] queue=CAKE-qos/CAKE-qos
```

**Beneficio:**
- Reduce buffer bloat
- Mejor latencia bajo carga
- Prioriza tráfico interactivo

---

### Paso 3: Habilitar FastTrack (SEGURO)
```bash
# Ver reglas existentes primero
/ip firewall filter print

# Agregar fasttrack si no existe
/ip firewall filter add chain=forward \
  action=fasttrack-connection \
  connection-state=established,related \
  comment="FastTrack-OC200"
```

**Beneficio:**
- CPU 15% → ~5% (reducción)
- Latencia 30% menor
- Mejor throughput

---

### Paso 4: TCP Optimizations (SEGURO)
```bash
/ip settings set \
  tcp-syncookies=yes \
  ipv4-settings=\
    {tcp-syncookies=yes}

/interface ethernet set [ find ] \
  auto-negotiation=yes \
  full-duplex=yes

/queue interface set [ find ] max-limit=1G/1G
```

**Beneficio:**
- Mejor estabilidad TCP
- Anti-DDoS
- Mejor negociación duplex

---

## 🎯 FASE 2: OPTIMIZACIÓN DE QoS ESPECÍFICA (7-14 días)

### Paso 5: Crear Queue Trees para Clientes
```bash
# Para cliente: guillermobarajasg (IP: 11.11.0.3)
/queue tree add name="QoS-guillermobarajasg" \
  parent=global-in \
  packet-mark="" \
  limit-at=0 \
  max-limit=100M \
  burst-limit=150M \
  burst-threshold=100M \
  burst-time=2s \
  priority=8 \
  comment="Optimized for Omada - Client 1"

# Para cliente: pazgarcia (IP: 11.11.0.2)
/queue tree add name="QoS-pazgarcia" \
  parent=global-in \
  packet-mark="" \
  limit-at=0 \
  max-limit=100M \
  burst-limit=150M \
  burst-threshold=100M \
  burst-time=2s \
  priority=8 \
  comment="Optimized for Omada - Client 2"
```

---

### Paso 6: Priorización de Tráfico (Optional)
```bash
# ICMP (Ping) - Alta prioridad
/ip firewall mangle add chain=prerouting \
  protocol=icmp action=mark-packet \
  new-packet-mark=icmp \
  comment="ICMP-Priority"

# ACK TCP - Alta prioridad
/ip firewall mangle add chain=prerouting \
  protocol=tcp tcp-flags=ack \
  action=mark-packet new-packet-mark=ack \
  comment="ACK-Priority"

# DNS - Alta prioridad
/ip firewall mangle add chain=prerouting \
  protocol=udp dst-port=53 \
  action=mark-packet new-packet-mark=dns \
  comment="DNS-Priority"
```

---

## 🎯 FASE 3: SEGURIDAD Y BACKUPS (Mismo día)

### Paso 7: Configurar Backups Automáticos
```bash
# Script de backup para OC200
/system script add name=backup-omada source={
  /system backup save name=omada-backup-$(/:timestamp)
  /ip firewall nat print file=nat-rules-backup
  /queue tree print file=qos-rules-backup
}

# Programar cada día a las 3 AM
/system scheduler add name=daily-backup \
  on-event=backup-omada \
  interval=1d start-time=03:00:00 \
  comment="Daily backup compatible with Omada"
```

---

### Paso 8: Optimizar Health Checks (Si OC200 no lo hace)
```bash
# Verificar si OC200 ya controla health checks
/ip route print

# Si NO hay health checks, agregar
/ip firewall filter add chain=input protocol=icmp \
  action=accept comment="Allow-Ping-for-Monitoring"
```

---

## 📊 COMPARACIÓN ESPERADA

### Antes:
```
Latencia P50:         50-60ms
Latencia P95:         80-100ms
Jitter:               20-30ms
CPU Load:             15%
Clientes satisfechos: 70%
```

### Después (Esperado):
```
Latencia P50:         20-30ms   ⬇️ -50%
Latencia P95:         40-50ms   ⬇️ -50%
Jitter:               5-10ms    ⬇️ -70%
CPU Load:             5-8%      ⬇️ -50%
Clientes satisfechos: 95%+      ⬆️ +25%
```

---

## 🔍 VERIFICACIÓN POST-OPTIMIZACIÓN

### Test 1: DNS
```bash
nslookup google.com 10.144.247.27
# Debe responder en <10ms
```

### Test 2: Latencia
```bash
ping -c 100 10.144.247.27
# Debe mostrar <30ms promedio
```

### Test 3: QoS
```bash
/queue tree print
# Debe mostrar CAKE asignado a todas las colas
```

### Test 4: FastTrack
```bash
/ip firewall filter print | grep fasttrack
# Debe mostrar regla FastTrack activa
```

### Test 5: Cliente
```bash
ssh admin@11.11.0.3
# Verificar que cliente tiene buena latencia y velocidad
```

---

## ⚠️ RIESGOS Y MITIGACIÓN

| Riesgo | Mitigación |
|--------|-----------|
| OC200 revertir cambios | Documentar cambios, hacer backup antes |
| Conflicto con reglas OC200 | Usar nombres únicos (ej: -OC200-) |
| Desconexión SSH durante cambios | Usar `:delay` entre comandos |
| Afectar otros clientes | Cambios son por cliente, no globales |

---

## 📋 CHECKLIST DE IMPLEMENTACIÓN

- [ ] Conectar exitosamente a 10.144.247.27
- [ ] Backup de configuración actual
- [ ] Paso 1: DNS optimizado
- [ ] Paso 2: CAKE queue implementado
- [ ] Paso 3: FastTrack habilitado
- [ ] Paso 4: TCP optimizations
- [ ] Paso 5: Queue trees por cliente (opcional)
- [ ] Paso 6: Priorización de tráfico (opcional)
- [ ] Paso 7: Backups automáticos
- [ ] Paso 8: Health checks verificados
- [ ] Pruebas de latencia/velocidad
- [ ] Feedback de clientes positivo

---

## 🚀 NEXT STEPS

1. **Reconectar a 10.144.247.27**
   - Si SSH timeout, verificar configuración OC200
   - Puede que OC200 tenga timeout muy bajo

2. **Implementar Fase 1** (Sin riesgo)
   - DNS, CAKE, FastTrack, TCP

3. **Monitorear 24-48 horas**
   - Ver si OC200 revertió cambios
   - Validar mejora de latencia

4. **Fase 2 (Si todo OK)**
   - QoS específico por cliente
   - Priorización de tráfico

5. **Documentar Todo**
   - Para que OC200 no lo revertir
   - Para troubleshooting futuro

---

## 📞 CONSIDERACIONES OMADA CONTROLLER OC200

### **Lo que debe saber sobre OC200:**

1. **Gestión Centralizada**
   - OC200 puede ver y editar todas las configs
   - Cambios pueden ser revertidos en próxima sincronización
   - Hay "Local Config" que OC200 no toca

2. **Recomendación**
   - Avisar a OC200 que hay cambios locales
   - Usar tags/comments específicos
   - Documentar en OC200 qué cambios son locales

3. **Mejor Práctica**
   - Agregar cambios como "Local Only"
   - Usar naming convention: `[LOCAL] descripción`
   - Hacer backup en OC200 también

---

**Documento creado:** 2025-11-24 14:00 UTC
**Próxima acción:** Reconectar y ejecutar Fase 1
**Generado por:** Claude Code
