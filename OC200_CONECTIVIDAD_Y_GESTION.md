# OC200 - Conectividad y Gestión Remota

## 1. INFORMACIÓN DEL DISPOSITIVO

### Identificación:
- **Dispositivo:** TP-Link Omada Controller (OC200)
- **IP Actual:** 12.12.2.12 (Estática via DHCP - MAC: 00:5F:67:59:E2:C2)
- **Subnet:** 12.12.0.0/20 (Gateway: 12.12.0.1)
- **Ubicación:** "Controller OMADA" en la red La Gloria
- **Estado:** ✓ Operacional

### Conectividad Verificada:
- ✓ **Ping:** 0% pérdida, latencia ~750µs desde 12.12.0.1
- ✓ **Puerto 443 (HTTPS):** ABIERTO - Certificado SSL TP-Link detectado
- ✓ **Puerto 80 (HTTP):** ABIERTO - Redirige a HTTPS
- ❌ **Puerto 8080:** CERRADO - No disponible
- ❌ **Puerto 22 (SSH):** Requiere credenciales específicas (no admin)

---

## 2. ACCESO A OC200

### A. Interfaz Web (Recomendado)

**URL:** `https://12.12.2.12/`

**Características:**
- Interfaz gráfica completa
- Gestión de dispositivos Omada (AP, Switch, Router)
- Configuración centralizada
- Monitoreo en tiempo real
- Provisioning automático

**Credenciales:** [Usar las que mencionaste - no compartidas aquí por seguridad]

**Puertos activos:**
- 443/HTTPS (primario)
- 80/HTTP (redirige a HTTPS)

---

## 3. PROTOCOLOS DE COMUNICACIÓN DEL OC200

### Protocolos Activos Identificados:

| Protocolo | Puerto | Estado | Propósito |
|-----------|--------|--------|-----------|
| HTTPS | 443 | ✓ Abierto | Interfaz Web, API REST |
| HTTP | 80 | ✓ Abierto | Redirige a HTTPS |
| SSH | 22 | Presente | CLI (credenciales requeridas) |
| SNMP | 161 | [No verificado] | Monitoreo (si habilitado) |
| NTP | 123 | [No verificado] | Sincronización de tiempo |
| DNS | 53 | [No verificado] | Si actúa como resolver |
| Omada Discovery | 29810/UDP | [No verificado] | Descubrimiento de APs |

---

## 4. CERTIFICADO SSL

**Detalles del Certificado:**
```
Subject: CN=localhost, O=TP-Link, OU=TP-Link
Issuer:  CN=localhost, O=TP-Link, OU=TP-Link
Tipo:    Auto-firmado (Self-signed)
```

**Nota:** Es un certificado auto-firmado. Los navegadores mostrarán advertencia de seguridad. Esto es NORMAL en dispositivos LAN.

---

## 5. ACCESO REMOTO DESDE ZEROTIER

Para acceder al OC200 remotamente vía ZeroTier desde 12.12.0.0/20:

### Requisitos:
1. ✓ ZeroTier activo en cliente remoto
2. ✓ Ruta ZeroTier: 12.12.0.0/20 via 10.144.53.102 (ya configurada)
3. ✓ Firewall rules: ICMP + TCP permitidos (líneas 20-21 en 12.12.0.1)

### Acceso:
```
https://12.12.2.12/
```
(Funciona igual desde ZeroTier que localmente)

---

## 6. OPCIONES DE CONECTIVIDAD CLI

### Opción A: SSH (Si credenciales disponibles)
```bash
ssh -o KexAlgorithms=diffie-hellman-group14-sha1 \
    -o HostKeyAlgorithms=ssh-rsa \
    usuario@12.12.2.12
```

**Nota:** Requiere usuario específico (no "admin" estándar)
**Credenciales válidas:** [Investigar en OC200 o documentación TP-Link]

### Opción B: Web UI (RECOMENDADO)
```
https://12.12.2.12/
```
- Más intuitiva
- Soporte completo de características
- No requiere CLI

### Opción C: MAC-Telnet (Si disponible en MikroTik)
```bash
ssh admin@12.12.0.1 /tool mac-telnet 00:5F:67:59:E2:C2
```

---

## 7. OPTIMIZACIONES Y MEJORAS SUGERIDAS

### Actualmente en OC200:
- ✓ Certificado SSL activo (HTTPS)
- ✓ Redireccionamiento HTTP → HTTPS
- ✓ Conectividad verificada

### Mejoras Recomendadas:

1. **Seguridad SSH:**
   - Habilitar SSH con clave pública/privada
   - Cambiar puerto 22 a uno aleatorio
   - Usar algoritmos modernos

2. **API REST:**
   - Documentar endpoints disponibles
   - Habilitar autenticación API token
   - Usar para automatización

3. **Monitoreo:**
   - Habilitar SNMP para alertas
   - Integrar con sistema de monitoreo central
   - Configurar traps SNMP

4. **Firewall:**
   - Revisar reglas en 12.12.0.1 para tráfico del OC200
   - Limitar acceso SSH a redes específicas
   - Habilitar logging de acceso

---

## 8. FLUJO DE CONECTIVIDAD ZEROTIER → OC200

```
Cliente Windows (ZeroTier)
         ↓ ping 12.12.2.12
    Interfaz zt1
         ↓
Ruta ZeroTier: 12.12.0.0/20 via 10.144.53.102
         ↓
Router Secundario (10.144.247.27)
         ↓
Puente Bridge1 (12.12.0.1)
         ↓
Firewall Rules (ICMP + TCP)
         ↓
OC200 (12.12.2.12) ✓
```

**Estado:** ✓ OPERACIONAL

---

## 9. PRÓXIMOS PASOS RECOMENDADOS

1. **Verificar acceso SSH al OC200:**
   - Obtener credenciales de SSH específicas
   - Intentar conexión directa
   - Documentar comandos CLI disponibles

2. **Integración de Monitoreo:**
   - Configurar SNMP en OC200
   - Conectar a sistema de monitoreo (Prometheus, Grafana, etc.)
   - Alertas automáticas

3. **Backup Automático:**
   - Exportar configuración del OC200
   - Programar backups periódicos
   - Almacenar en ubicación segura

4. **Documentación:**
   - Mapear todas las APs bajo control del OC200
   - Documentar políticas de seguridad
   - Crear guía de troubleshooting

---

## 10. CONTACTO Y REFERENCIAS

**Fabricante:** TP-Link
**Modelo:** OC200
**Documentación oficial:** https://www.tp-link.com/us/business/omada/oc200/

**Comandos útiles en MikroTik (12.12.0.1):**
```bash
# Ver si OC200 está alcanzable
/ping 12.12.2.12 count=5

# Ver entrada ARP
/ip arp print where address=12.12.2.12

# Ver tráfico hacia OC200
/ip firewall filter print where dst-address=12.12.2.12
```

---

**Documento generado:** 2025-11-28
**Estado:** ✓ Verificado y operacional
