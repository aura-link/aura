# MikroTik ISP Load Balancer - Configuración Documentada
## Fecha: Enero 2026

---

## Infraestructura General
- **Equipo:** Router MikroTik (RouterOS 7)
- **Función:** Balanceador de carga ISP con múltiples WAN
- **Clientes:** ~200 usuarios PPPoE

---

## WANs Configuradas

| WAN | Interface | Tipo | IP | Estado |
|-----|-----------|------|-----|--------|
| WAN1 | ether1-WAN1 | Starlink | DHCP | Activa |
| WAN2 | ether2-WAN2 | - | - | Deshabilitada |
| WAN3 | ether3-WAN3 | Presidencia | IP Fija | Activa |
| WAN4 | ether5-WAN4 | Presidencia | IP Fija | Activa |
| WAN5 | ether6-WAN5 | Starlink | DHCP | Activa |
| WAN6 | ether4-WAN6 | Starlink Totin | DHCP | Activa (revisar cable - 222 FCS errors) |
| WAN7 | ether7-WAN7 | Chuy | DHCP | Activa |
| WAN8 | - | - | - | Deshabilitada (problemas ISP) |
| WAN9 | ether8-WAN9 | Starlink | DHCP | Activa |
| WAN10 | - | - | - | Deshabilitada |

**Total WANs Activas:** 7

---

## PCC Load Balancing
- **Método:** Per Connection Classifier
- **Divisor:** 7 (igual al número de WANs activas)
- **Mangle Rules:** Marcado de conexiones y rutas por WAN
- **Comentarios:** Cada regla tiene comentario con nombre de WAN para fácil identificación

---

## Queue Tree con QoS

### Estructura
```
Global-Download (parent)
├── Download-WAN1 (CAKE-qos)
├── Download-WAN3 (CAKE-qos)
├── Download-WAN4 (CAKE-qos)
├── Download-WAN5 (CAKE-qos)
├── Download-WAN6 (CAKE-qos)
├── Download-WAN7 (CAKE-qos)
└── Download-WAN9 (CAKE-qos)
```

### Prioridades QoS
| Prioridad | Tipo | Descripción |
|-----------|------|-------------|
| 1 | QoS-ICMP | Ping/diagnóstico (10M limit) |
| 1 | QoS-ACK | Acknowledgments TCP |
| 2 | QoS-DNS | Resolución DNS |
| 3 | QoS-Gaming | Juegos online |
| 3 | QoS-VoIP | Voz sobre IP |
| 5 | QoS-Video | Streaming video |
| 6 | QoS-Social | Redes sociales |

---

## Sistema de Failover y Recuperación Automática

### Netwatch
- **Intervalo:** 15 segundos
- **Destino:** Gateway de cada WAN
- **Acción Down:** Deshabilita mangle + route, crea scheduler retry 30min
- **Acción Up:** Ejecuta script de verificación

### Scripts de Verificación (check-WAN1 a check-WAN9)
Cada script realiza doble verificación:
1. **Ping:** 3 intentos a 8.8.8.8, requiere >1 exitoso
2. **Tráfico:** Verifica que rx-byte aumente en 2 segundos

```routeros
:local ping [/ping 8.8.8.8 count=3 interface=ether1-WAN1]
:local rx1 [/interface get ether1-WAN1 rx-byte]
:delay 2s
:local rx2 [/interface get ether1-WAN1 rx-byte]
:if ($ping > 1 && $rx2 > $rx1) do={
  /ip firewall mangle enable [find comment~"WAN1"]
  /ip route enable [find comment~"PCC-Route-WAN1"]
  :log warning ">>> WAN1 RECUPERADA - Ping OK + Trafico OK <<<"
  /system scheduler remove [find name=retry-WAN1]
} else={
  :log error "WAN1 fallo verificacion - retry 30min"
}
```

### Ciclo de Recuperación
1. WAN cae → Netwatch detecta en 15s
2. Se deshabilitan mangle y rutas de esa WAN
3. Se crea scheduler para reintentar en 30min
4. A los 30min ejecuta script check-WANx
5. Si pasa verificación (ping + tráfico) → reactiva WAN
6. Si falla → espera otros 30min y repite

---

## Firewall

### Filter Rules
- Drop Invalid connections habilitado
- Protección básica contra ataques

### NAT
- Masquerade habilitado para todas las WANs activas
- Comentarios identificando cada WAN

---

## Backup Automático
- **Scheduler:** backup-diario
- **Hora:** 3:00 AM
- **Archivos generados:**
  - backup-YYYY-MM-DD.backup (binario)
  - backup-YYYY-MM-DD.rsc (texto exportable)

---

## Archivos de Configuración Guardados en Router
- config-7wan-pcc.backup / .rsc
- config-firewall-fix.backup / .rsc
- config-final-optimizado.backup / .rsc
- config-recovery-30min.backup / .rsc
- config-recovery-ping-traffic.backup / .rsc

---

## Problemas Identificados y Soluciones

| Problema | Solución |
|----------|----------|
| WAN3/WAN7 Netwatch down incorrecto | Actualizar src-address con IP actual |
| WAN3 mangle deshabilitados | Habilitar Download-WAN3 y Route-to-WAN3 |
| WAN7/WAN8 rutas inactivas | Recrear con gateway correcto |
| QoS-ICMP drops (179K) | Aumentar límite de 1M a 10M |
| WAN6 errores FCS | PENDIENTE: Revisar cable físico ether4 |

---

## Tareas Pendientes
- [ ] Revisar cable físico ether4 (WAN6 - Starlink Totin) - 222 errores FCS
- [ ] Futuro: Implementar verificación de velocidad en scripts de recuperación

---

## Comandos Útiles

```routeros
# Ver estado de WANs
/interface print where running=yes

# Ver errores en interfaces
/interface ethernet print stats

# Ver clientes PPPoE
/ppp active print count-only

# Ver Queue Tree
/queue tree print

# Ver mangle rules
/ip firewall mangle print

# Ver Netwatch
/tool netwatch print

# Ejecutar backup manual
/system backup save name=backup-manual
/export file=backup-manual

# Ver logs
/log print where topics~"warning|error"
```

---

## Notas Adicionales
- El router tiene configurado servidor PPPoE para los clientes
- Los clientes suspendidos por falta de pago generan errores de autenticación en logs (normal)
- WAN8 deshabilitada intencionalmente por problemas con el ISP
