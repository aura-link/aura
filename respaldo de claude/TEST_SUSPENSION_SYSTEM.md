# Guía de Prueba - Sistema de Aviso de Suspensión

## Prueba Rápida Local (Antes de Desplegar)

### Paso 1: Iniciar servidor localmente en Windows

```bash
# Abre una terminal en la carpeta C:\claude
cd C:\claude

# Instala Python si no lo tienes (Python 3.x)
# Luego ejecuta:
python suspension_server.py
```

### Paso 2: Probar la página

En tu navegador, ve a:
```
http://localhost:80
```

O desde otra máquina en tu red:
```
http://192.168.100.3:80
```

**Esperado:** Deberías ver la página de suspensión profesional con el aviso

### Paso 3: Probar API de verificación

```bash
curl http://localhost/api/check-status
```

**Esperado:** Deberías recibir `{"status": "active"}` (JSON)

---

## Prueba Completa con MikroTik

### Fase 1: Preparación

#### 1.1 Verificar conectividad

```bash
ping 10.147.17.11
```

**Esperado:** Respuesta del router

#### 1.2 Copiar archivos al servidor

```bash
# Conectar al servidor por SCP
scp suspension_page.html yesswera@192.168.100.3:/tmp/
scp suspension_server.py yesswera@192.168.100.3:/tmp/
```

#### 1.3 Crear carpeta de suspensiones

```bash
ssh yesswera@192.168.100.3 "mkdir -p /home/yesswera/suspension"
ssh yesswera@192.168.100.3 "mv /tmp/suspension* /home/yesswera/suspension/"
ssh yesswera@192.168.100.3 "chmod +x /home/yesswera/suspension/suspension_server.py"
```

### Fase 2: Iniciar Servidor

```bash
# Ejecutar en background
ssh yesswera@192.168.100.3 "nohup python3 /home/yesswera/suspension/suspension_server.py > /tmp/suspension.log 2>&1 &"

# Verificar que está ejecutándose
ssh yesswera@192.168.100.3 "ps aux | grep suspension_server"
```

**Esperado:** Ver el proceso de Python ejecutándose

### Fase 3: Configurar MikroTik

#### 3.1 Agregar cliente de prueba a suspendidos

```bash
# Crear archivo con cliente de prueba
echo "192.168.1.100" > /tmp/suspended_clients.txt

# Copiar a servidor
scp /tmp/suspended_clients.txt yesswera@192.168.100.3:/tmp/
```

#### 3.2 Agregar reglas de prueba en MikroTik

Conectarse por SSH al router:

```bash
ssh admin@10.147.17.11
# Password: 1234
```

Luego ejecutar (línea por línea):

```
/ip firewall mangle add chain=prerouting src-address=192.168.1.100 \
action=mark-packet new-packet-mark=suspended_traffic \
comment="Cliente Prueba"

/ip firewall nat add chain=dstnat packet-mark=suspended_traffic \
protocol=tcp dst-port=80 action=redirect to-ports=80 \
comment="Redirigir a aviso de suspensión"
```

Verificar:
```
/ip firewall mangle print
/ip firewall nat print
```

### Fase 4: Prueba de Funcionamiento

#### 4.1 Cliente Normal (No suspendido)

Desde máquina con IP 192.168.1.50:
```bash
curl http://8.8.8.8  # O cualquier sitio
```

**Esperado:** Acceso normal, sin redireccionamiento

#### 4.2 Cliente Suspendido (Prueba)

Desde máquina con IP 192.168.1.100:
```bash
curl http://google.com
```

**Esperado:** Redirección a la página de suspensión

#### 4.3 Navegador del Cliente Suspendido

Desde máquina 192.168.1.100:
1. Abrir navegador
2. Ir a cualquier sitio (google.com, facebook.com, etc)
3. Esperar 2-3 segundos

**Esperado:** Ver la página de aviso profesional

---

## Verificaciones

### Checklist de Funcionamiento

- [ ] Servidor Python inicia sin errores
- [ ] Página se carga en navegador
- [ ] Página se ve bien (sin errores de formato)
- [ ] Número telefónico es visible
- [ ] Botón "Verificar Estado" funciona
- [ ] Cliente suspendido ve el aviso
- [ ] Cliente normal puede navegar
- [ ] Servidor registra accesos (check logs)

### Monitoreo

```bash
# Ver logs del servidor
tail -f /tmp/suspension.log

# Ver procesos activos
ps aux | grep suspension_server

# Ver conexiones HTTP
netstat -an | grep :80
```

### Prueba de Cambios

```bash
# Agregar cliente a suspendidos
python manage_suspension.py add 192.168.1.101

# Ver cliente agregado
python manage_suspension.py list

# Remover cliente
python manage_suspension.py remove 192.168.1.100
```

---

## Solución Rápida de Problemas

### "Conexión rechazada" en puerto 80

**Problema:** `Connection refused`

**Solución:**
```bash
# Matar proceso anterior
pkill -f suspension_server.py

# Esperar 5 segundos
sleep 5

# Reiniciar
python3 suspension_server.py
```

### "Puerto 80 ya en uso"

**Problema:** `Address already in use`

**Solución:**
```bash
# Ver qué proceso está usando puerto 80
netstat -tlnp | grep :80

# Matar el proceso (ejemplo: PID 1234)
kill -9 1234

# O usar un puerto diferente (cambiar en código)
```

### "Cliente no ve la página"

**Checklist:**
1. ¿Servidor Python está ejecutándose?
   ```bash
   ps aux | grep suspension_server
   ```

2. ¿Puerto 80 está escuchando?
   ```bash
   netstat -an | grep :80
   ```

3. ¿Reglas MikroTik están activas?
   ```bash
   ssh admin@10.147.17.11
   /ip firewall mangle print
   /ip firewall nat print
   ```

4. ¿Cliente tiene IP correcta?
   ```bash
   ipconfig /all  (Windows)
   ifconfig      (Linux)
   ```

---

## Resultados Esperados

### Ejecución Exitosa

```
Servidor de Suspensión Iniciado
============================================================
Escuchando en puerto 80
Redireccionando clientes morosos a aviso de suspensión
Archivo de clientes suspendidos: /tmp/suspended_clients.txt
============================================================

[IP_Cliente] - GET / HTTP/1.1" 200 -
[IP_Cliente] - GET /api/check-status HTTP/1.1" 403 -
```

### Página Visible en Navegador

Deberías ver:
- Icono de advertencia (⚠️)
- Título "Servicio Suspendido" en rojo
- Información de contacto (+56 2 3655 099)
- Sección bancaria
- Botón "Verificar Estado"
- Auto-actualización cada 30 segundos

---

## Próximos Pasos

Una vez confirmada la funcionalidad:

1. **Personalizar:**
   - Cambiar número de teléfono
   - Agregar información bancaria real
   - Ajustar colores según tu marca

2. **Automatizar:**
   - Crear script que agregue suspensiones automáticamente
   - Integrar con sistema de facturación
   - Enviar notificaciones por correo

3. **Monitorear:**
   - Revisar logs regularmente
   - Alertas si el servidor se cae
   - Reportes de clientes suspendidos

4. **Mejorar:**
   - Agregar HTTPS (SSL/TLS)
   - Multi-idioma (Español/Inglés)
   - QR code con método de pago
   - Contador de días suspendido

---

**Creado con:** Claude Code
**Fecha:** 2025-11-14
