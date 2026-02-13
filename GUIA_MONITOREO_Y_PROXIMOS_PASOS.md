# GUÍA DE MONITOREO Y PRÓXIMOS PASOS
## WISP - RB5009UG+S+

---

## 🔍 CÓMO MONITOREAR TUS MEJORAS

### 1. **Verificar Latencia en Tiempo Real**

Desde una terminal en tu PC:

```bash
# Ping constante a tu router
ping 10.147.17.11

# Medir latencia a un cliente específico
ping 10.10.1.100

# Test de velocidad contra speedtest.net
curl -O https://speedtest.net/api/js/latency.js
```

**Qué observar:**
- Latencia debe estar entre 20-50ms
- Muy pocas pérdidas de paquetes (<1%)
- Jitter bajo (<10ms)

### 2. **Verificar Salud de ISPs Desde el Router**

Conéctate vía SSH:

```bash
ssh admin@10.147.17.11

# Ver logs de health check
/log print where message~"ISP"

# Hacer ping manual a cada gateway
/ping 8.8.8.8 count=10 gateway=192.168.201.1  # ISP1
/ping 8.8.8.8 count=10 gateway=192.168.1.1    # ISP2
/ping 8.8.8.8 count=10 gateway=192.168.40.1   # ISP3
# ... etc para cada ISP
```

**Qué indica un problema:**
- 0 respuestas = ISP caído
- >100ms = ISP lento (probablemente saturado)
- Pérdida >10% = ISP inestable

### 3. **Ver Carga de CPU y Memoria**

```bash
ssh admin@10.147.17.11

# Ver recursos en tiempo real
/system resource print

# Ver tendencia en últimas 24 horas
/log print where message~"MonitorCPU"  # Si tienes script de monitoreo
```

**Valores normales después de optimización:**
- CPU: 25-40%
- Memoria: <50%
- Uptime: máximo posible

### 4. **Ver Estadísticas de Clientes**

```bash
ssh admin@10.147.17.11

# Ver conexiones PPPoE activas
/ppp active print

# Ver ancho de banda usado por cliente
/ip firewall nat print stats
```

---

## 📊 PANEL RECOMENDADO: INSTALACIÓN DE MONITOREO VISUAL

### Opción 1: **LibreNMS** (Recomendado para WISP)

```bash
# 1. Instalar en servidor Linux/Windows
# Ir a https://www.librenms.org/

# 2. Configurar SNMP en tu RB5009
ssh admin@10.147.17.11

/snmp set enabled=yes
/snmp community add name=public security=public
/ip firewall filter add chain=input in-interface=ether1-WAN1 protocol=udp dst-port=161 action=accept

# 3. Agregar el router en LibreNMS
# Ir al panel, agregar device: 10.147.17.11, SNMP community: public

# 4. En 5 minutos verás gráficos de:
# - CPU, memoria, disco
# - Tráfico por interfaz
# - Conexiones PPPoE
# - Latencia a ISPs (si configuras ping probe)
```

### Opción 2: **Grafana + Prometheus** (Más avanzado)

```bash
# 1. Instalar Prometheus y node-exporter en tu servidor
# 2. Exportar métricas desde RB5009
# 3. Crear dashboards personalizados
```

### Opción 3: **Dude** (Ya incluido en MikroTik)

```bash
# Ya vi que tienes TheDude habilitado en tu router
# 1. Conéctate a tu servidor Dude
# 2. Agregar el router como monitored device
# 3. Crear alertas para CPU >80%, cualquier ISP caído, etc.
```

---

## 🎯 PRÓXIMAS OPTIMIZACIONES (Fase 2)

### Semana 1: Validación
- [ ] Monitorear latencia por 7 días
- [ ] Registrar datos de CPU/memoria
- [ ] Documentar cualquier caída de ISP
- [ ] Solicitar feedback de clientes sobre velocidad

### Semana 2: Mejoras de QoS
- [ ] Aplicar CAKE queue a TODOS los queues simples:
  ```bash
  /queue simple modify [ find ] queue=CAKE-qos/CAKE-qos
  ```
- [ ] Ajustar RTT del CAKE según tu latencia real
- [ ] Pruebas de speedtest antes/después

### Semana 3: Monitoreo Avanzado
- [ ] Instalar LibreNMS o Grafana
- [ ] Configurar alertas automáticas
- [ ] Crear reportes semanales de performance

### Semana 4: Escalabilidad
- [ ] Evaluar agregar 10mo ISP como respaldo
- [ ] Considerar HA (VRRP) con otro router
- [ ] Optimizar antenas (alineación, potencia)

---

## ⚡ COMANDOS ÚTILES RÁPIDOS

### Ver Top 10 Clientes por Consumo Ancho de Banda

```bash
ssh admin@10.147.17.11

# Ver estadísticas de firewall
/ip firewall nat print stats

# O ver conexiones PPPoE y su consumo
/ppp active print stats

# Ver interfaces Ethernet
/interface ethernet print stats
```

### Forzar Reinicio Limpio del Router

```bash
ssh admin@10.147.17.11

# Backup primero
/system backup save name=backup-antes-reinicio

# Esperar a que se guarde
/system reboot
```

### Ver Logs de Últimas Errores

```bash
ssh admin@10.147.17.11

/log print where level=error tail=100
/log print where level=warning tail=100
```

### Prueba de Latencia a Múltiples ISPs

```bash
ssh admin@10.147.17.11

:foreach gateway in 192.168.201.1 192.168.1.1 192.168.40.1 192.169.1.1 192.168.2.1 192.168.4.1 192.168.101.1 192.168.5.1 192.168.8.1 {
  /ping 8.8.8.8 count=4 gateway=$gateway
}
```

---

## 🚨 TROUBLESHOOTING

### Si la latencia NO mejora:

1. **Verificar que FastTrack esté activo:**
   ```bash
   /ip firewall filter print where action=fasttrack-connection
   # Debería mostrar la regla que agregamos
   ```

2. **Verificar que CAKE esté asignado:**
   ```bash
   /queue simple print | grep queue
   # Debería mostrar CAKE-qos/CAKE-qos en las colas importantes
   ```

3. **Verificar saturación de ISPs:**
   ```bash
   # Ver interfaces WAN
   /interface ethernet print stats
   # Si algún WAN está 100% utilizado, ese es el cuello de botella
   ```

4. **Revisar scripts de monitoreo:**
   ```bash
   /system script print where name=isp-health-check
   /system scheduler print where name=run-isp-health-check
   ```

### Si falla un ISP y no detecta:

1. **Asegurarse que el script está programado:**
   ```bash
   /system scheduler print
   # Debería haber un scheduler llamado "run-isp-health-check"
   ```

2. **Verificar logs manualmente:**
   ```bash
   /log print where message~"ISP"
   ```

3. **Ejecutar el script manualmente:**
   ```bash
   /system script run isp-health-check
   /log print where message~"ISP" tail=10
   ```

---

## 📞 SOPORTE Y REFERENCIAS

### MikroTik Documentation
- CAKE Queue: https://wiki.mikrotik.com/wiki/Manual:Queue#CAKE
- FastTrack: https://wiki.mikrotik.com/wiki/Manual:IP/Firewall/Filter#fasttrack-connection
- PPPoE Server: https://wiki.mikrotik.com/wiki/Manual:PPP#PPPoE_Server

### Herramientas de Diagnóstico Recomendadas
- **mtr** (My TraceRoute) - Latencia y pérdida de paquetes
- **speedtest-cli** - Pruebas de velocidad desde línea de comandos
- **iperf3** - Medir ancho de banda entre dos puntos

### Comunidades de Ayuda
- MikroTik Forum: https://forum.mikrotik.com/
- Reddit: r/mikrotik
- Discord: MikroTik Community (varios servidores)

---

## 📋 CHECKLIST DE VALIDACIÓN

- [ ] Latencia medida en clientes (< 50ms esperado)
- [ ] Todos los ISPs online y respondiendo
- [ ] CPU load entre 30-40%
- [ ] Memoria disponible >200MB
- [ ] Health checks ejecutándose cada 5min
- [ ] No hay errores en los logs
- [ ] Clientes reportan mejor velocidad
- [ ] Monitoreo visual implementado (opcional pero recomendado)

---

## 🎓 EXPLICACIÓN TÉCNICA RÁPIDA

**¿Por qué estas optimizaciones funcionan?**

1. **CAKE:** Reemplaza el queuing tradicional con un algoritmo que:
   - Detecta tráfico interactivo (VoIP, gaming)
   - Lo prioriza automáticamente
   - Limita buffer para reducir latencia

2. **FastTrack:** Para conexiones ya validadas:
   - Salta todo el procesamiento de firewall
   - Los paquetes van directo a hardware
   - Reduce CPU hasta 30%

3. **DNS mejorado:**
   - Caché local = resolver local sin ir a internet
   - RTT cae de 100ms a <10ms

4. **Health Checks:**
   - Detectan problemas en segundos
   - Permiten failover rápido a otro ISP

---

**Última actualización:** 2025-11-24
**Próxima revisión sugerida:** 2025-11-25 (después de 24h de operación)

*Mantén este documento a mano para futuras optimizaciones y troubleshooting.*
