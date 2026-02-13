# Sistema de Aviso de Suspensión para Clientes Morosos
**Fecha:** 2025-11-14
**Sistema:** MikroTik + Servidor Web

---

## 📋 Resumen

Sistema automático que muestra una página de aviso profesional a clientes con pagos pendientes. Cuando un cliente intenta acceder a cualquier sitio web, se le redirige a una página que muestra:

- Motivo de la suspensión
- Número de contacto (WhatsApp)
- Información bancaria para realizar el pago
- Instrucciones para reportar el pago

---

## 🎯 Componentes

### 1. Página HTML de Suspensión
**Archivo:** `suspension_page.html`
**Descripción:** Página profesional y responsiva con:
- Diseño moderno con gradientes y animaciones
- Información clara del problema
- Datos de contacto destacados
- Información bancaria
- Botón de verificación de estado
- Auto-actualización cada 30 segundos

**Características:**
- Responsive design (funciona en móvil, tablet, desktop)
- Animaciones suaves
- Colores profesionales (rojo para alerta)
- Información bancaria editable

### 2. Servidor Python
**Archivo:** `suspension_server.py`
**Descripción:** Servidor HTTP ligero que:
- Sirve la página de suspensión
- Verifica si el cliente está suspendido
- Proporciona endpoint `/api/check-status` para verificación
- Registra accesos con IP y hora

**Puerto:** 80 (HTTP)
**Requisitos:** Python 3.x (no requiere librerías externas)

### 3. Gestor de Suspensiones
**Archivo:** `manage_suspension.py`
**Descripción:** Herramienta CLI para:
- Agregar/remover clientes de la lista de suspendidos
- Listar clientes suspendidos
- Configurar MikroTik
- Desplegar archivos al servidor

---

## 🚀 Instalación y Configuración

### Paso 1: Preparar Archivos

Los archivos ya están creados en:
- `C:\claude\suspension_page.html`
- `C:\claude\suspension_server.py`
- `C:\claude\manage_suspension.py`

### Paso 2: Desplegar en Servidor (192.168.100.3)

```bash
# 1. Crear carpeta para el sistema
mkdir -p /home/yesswera/suspension

# 2. Copiar archivos
cp suspension_page.html /home/yesswera/suspension/
cp suspension_server.py /home/yesswera/suspension/
chmod +x /home/yesswera/suspension/suspension_server.py

# 3. Crear archivo de clientes suspendidos
touch /tmp/suspended_clients.txt
```

### Paso 3: Iniciar Servidor en Linux

```bash
# Opción A: Ejecución manual
python3 /home/yesswera/suspension/suspension_server.py

# Opción B: En background con nohup
nohup python3 /home/yesswera/suspension/suspension_server.py > /tmp/suspension.log 2>&1 &

# Opción C: Como servicio systemd (recomendado)
# Crear archivo /etc/systemd/system/suspension.service:

[Unit]
Description=Servidor de Aviso de Suspensión
After=network.target

[Service]
Type=simple
User=yesswera
WorkingDirectory=/home/yesswera/suspension
ExecStart=/usr/bin/python3 /home/yesswera/suspension/suspension_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

# Luego ejecutar:
systemctl daemon-reload
systemctl start suspension
systemctl enable suspension
systemctl status suspension
```

### Paso 4: Configurar MikroTik NAT

#### Opción A: Redirigir TODO el tráfico HTTP

```
/ip firewall nat add chain=dstnat protocol=tcp dst-port=80 \
action=redirect to-ports=80 \
comment="Aviso de Suspensión - Clientes Morosos"
```

**Ventaja:** Funciona para todos los clientes
**Desventaja:** Todos los clientes van a la página de suspensión inicialmente

#### Opción B: Redirigir solo IPs específicas (RECOMENDADO)

Para cada cliente suspendido, usar mangle + NAT:

```
# Ejemplo para cliente 192.168.1.100:

# Paso 1: Marcar el tráfico del cliente
/ip firewall mangle add chain=prerouting src-address=192.168.1.100 \
action=mark-packet new-packet-mark=suspended_traffic \
comment="Marcar cliente suspendido 192.168.1.100"

# Paso 2: Redirigir el tráfico marcado
/ip firewall nat add chain=dstnat packet-mark=suspended_traffic \
protocol=tcp dst-port=80 action=redirect to-ports=80 \
comment="Redirigir cliente suspendido 192.168.1.100"
```

---

## 📱 Uso

### Agregar Cliente Suspendido

```bash
python3 manage_suspension.py add 192.168.1.100
```

Esto:
1. Agrega la IP a la lista de suspendidos
2. En MikroTik, debes crear las reglas mangle + NAT

### Remover Cliente Suspendido

```bash
python3 manage_suspension.py remove 192.168.1.100
```

Esto:
1. Remueve la IP de la lista de suspendidos
2. Debes remover las reglas mangle + NAT en MikroTik

### Ver Clientes Suspendidos

```bash
python3 manage_suspension.py list
```

### Ver Configuración Necesaria en MikroTik

```bash
python3 manage_suspension.py configure
```

---

## 🔧 Personalización

### Cambiar Número de Teléfono

Editar `suspension_page.html`:

```html
<!-- Buscar esta línea -->
<div class="contact-value">+56 2 3655 099</div>

<!-- Cambiar a -->
<div class="contact-value">+56 2 TU_NUMERO</div>
```

### Cambiar Información Bancaria

Editar en `suspension_page.html`:

```html
<!-- Buscar sección "Realiza tu Pago" -->
<div class="bank-info">
    <h3>🏦 Realiza tu Pago</h3>
    <div class="bank-detail">
        <label>Banco Destino</label>
        <value>TU_BANCO</value>
    </div>
    <div class="bank-detail">
        <label>Número de Cuenta</label>
        <value>TU_NUMERO_CUENTA</value>
    </div>
    <!-- etc... -->
</div>
```

### Cambiar Colores

Editar los códigos de color en `suspension_page.html`:

```css
/* Color rojo de alerta */
color: #d63031;  /* Cambiar este hex */

/* Color degradado de fondo */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
/* Cambiar estos hex */
```

---

## 📊 Flujo de Funcionamiento

```
Cliente intenta acceder a www.google.com
        ↓
Consulta DNS → MikroTik resuelve
        ↓
Cliente intenta conectar a IP de google.com
        ↓
MikroTik verifica si IP está marcada como suspendida
        ↓
Si SÍ está suspendida:
  - MikroTik redirige tráfico HTTP al servidor de suspensión (puerto 80)
  - Servidor muestra suspension_page.html
  - Cliente ve el aviso profesional
        ↓
Si NO está suspendida:
  - Tráfico normal hacia el destino
```

---

## ⚙️ Monitoreo

### Ver logs del servidor

```bash
# Opción A: Si está en background
tail -f /tmp/suspension.log

# Opción B: Si está como servicio
journalctl -u suspension -f

# Opción C: Revisar accesos HTTP
netstat -an | grep :80
```

### Verificar clientes suspendidos

```bash
# Ver archivo de suspendidos
cat /tmp/suspended_clients.txt

# Verificar en tiempo real
python3 manage_suspension.py list
```

### Probar la página

```bash
# Desde otro cliente:
curl http://192.168.100.3

# O abrir navegador:
http://192.168.100.3
```

---

## 🔐 Seguridad

### Notas Importantes

1. **Puerto 80:** Asegurar que solo el servidor de suspensión escuche en puerto 80
2. **HTTPS:** Para versión segura, agregar certificado SSL/TLS (futura mejora)
3. **Acceso SSH:** Limitar acceso SSH solo a administradores
4. **Logs:** Monitorear logs para detectar accesos sospechosos

---

## 🛠️ Solución de Problemas

### Problema: Clientes no ven la página

**Solución:**
1. Verificar que servidor Python está ejecutándose:
   ```bash
   ps aux | grep suspension_server
   ```
2. Verificar que puerto 80 está escuchando:
   ```bash
   netstat -an | grep :80
   ```
3. Verificar reglas MikroTik:
   ```bash
   /ip firewall nat print
   /ip firewall mangle print
   ```

### Problema: Error de permisos en puerto 80

**Solución:**
```bash
# Opción A: Ejecutar como root
sudo python3 suspension_server.py

# Opción B: Usar puertos > 1024 y redirigir con iptables
sudo iptables -t nat -A PREROUTING -p tcp --dport 80 \
  -j REDIRECT --to-port 8080
```

### Problema: Página se ve distorsionada

**Solución:**
1. Limpiar caché del navegador (Ctrl+Shift+Del)
2. Probar en navegador de incógnito
3. Verificar que `suspension_page.html` se copió correctamente

---

## 📝 Ejemplo Práctico Completo

### Escenario: Suspender cliente Juan (IP: 192.168.1.50)

**Paso 1: Agregar a lista de suspendidos**
```bash
python3 manage_suspension.py add 192.168.1.50
```

**Paso 2: Configurar MikroTik (vía SSH o WinBox)**

Ejecutar en terminal SSH del MikroTik:
```
/ip firewall mangle add chain=prerouting src-address=192.168.1.50 \
action=mark-packet new-packet-mark=suspended_traffic comment="Juan"

/ip firewall nat add chain=dstnat packet-mark=suspended_traffic \
protocol=tcp dst-port=80 action=redirect to-ports=80 \
comment="Redirigir Juan a aviso"
```

**Paso 3: Cliente intenta navegar**
- Abre navegador
- Intenta ir a google.com
- VE EL AVISO DE SUSPENSIÓN

**Paso 4: Juan paga**
- Llama al número mostrado
- Realiza el depósito
- Reporta el comprobante

**Paso 5: Remover de suspendidos**
```bash
python3 manage_suspension.py remove 192.168.1.50
```

**Paso 6: Remover reglas MikroTik**

En terminal SSH del MikroTik:
```
/ip firewall mangle remove [find comment="Juan"]
/ip firewall nat remove [find comment="Redirigir Juan a aviso"]
```

---

## 📞 Soporte

Para más información o customización:
- Revisar documentación de MikroTik
- Documentación de Python http.server
- Ver comentarios en los scripts

---

**Creado con:** Claude Code
**Última actualización:** 2025-11-14
