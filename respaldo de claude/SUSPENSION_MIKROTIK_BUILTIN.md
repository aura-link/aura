# Sistema de Aviso de Suspensión - MikroTik Built-in
**Ubicación:** Directamente en el MikroTik 10.147.17.11
**Método:** Usando capacidades nativas de MikroTik (sin servidor externo)

---

## Opción 1: HTTP Redirect Simple (RECOMENDADO)

### Funcionamiento
1. Cliente suspendido intenta acceder a cualquier sitio HTTP
2. MikroTik redirige al puerto HTTP del router mismo
3. MikroTik muestra página de aviso HTML almacenada localmente

### Paso 1: Crear archivo HTML en MikroTik

Conectate por SSH al router y ejecuta esto:

```
/file print
```

Copia el siguiente comando (reemplaza con tu información):

```
/file add name=suspension.html contents="<!DOCTYPE html>
<html lang=\"es\">
<head>
<meta charset=\"UTF-8\">
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
<title>Servicio Suspendido</title>
<style>
body { font-family: Arial; background: #f0f0f0; display: flex; justify-content: center; align-items: center; height: 100vh; }
.container { background: white; padding: 40px; border-radius: 10px; text-align: center; }
h1 { color: #d63031; }
.contact { background: #f9f9f9; padding: 20px; margin: 20px 0; border-radius: 5px; }
.phone { font-size: 24px; color: #d63031; font-weight: bold; }
</style>
</head>
<body>
<div class=\"container\">
<h1>⚠️ Servicio Suspendido</h1>
<p>Tu conexión ha sido suspendida por falta de pago.</p>
<div class=\"contact\">
<p><strong>Contactanos:</strong></p>
<p class=\"phone\">+56 2 3655 099</p>
<p><small>Lunes a Viernes: 9:00 - 18:00</small></p>
</div>
<p><strong>Deposita en tu cuenta y reporta tu pago para restaurar el servicio.</strong></p>
</div>
</body>
</html>"
```

### Paso 2: Habilitar HTTP Server en MikroTik

```
/ip service set www disabled=no port=80
```

Verificar:
```
/ip service print
```

Deberías ver `www` habilitado en puerto 80.

### Paso 3: Crear NAT para redirigir HTTP

Para cada cliente suspendido, ejecuta esto (ejemplo: 192.168.1.100):

```
/ip firewall mangle add chain=prerouting src-address=192.168.1.100 \
action=mark-packet new-packet-mark=suspended_traffic \
comment="Cliente Suspendido 192.168.1.100"

/ip firewall nat add chain=dstnat packet-mark=suspended_traffic \
protocol=tcp dst-port=80 action=redirect to-ports=80 \
comment="Redirigir a aviso suspensión"
```

Verificar:
```
/ip firewall mangle print
/ip firewall nat print
```

### Paso 4: Probar

Cliente suspendido intenta navegar a google.com:
- Debería ver la página de aviso

Cliente normal (no suspendido):
- Debería navegar normalmente

---

## Opción 2: DNS Hijacking (Alternativa)

Si prefieres redirigir por DNS:

```
/ip dns static add name=*.* address=10.147.17.11 comment="Redirect a Suspensión"
```

Esto redirige TODOS los dominios a la IP del router.

---

## Opción 3: Script de MikroTik para Aviso Dinámico

Crear un script que genere el aviso automáticamente:

```
/system script add name=suspension-page comment="Página de suspensión" source={
:local clientip [/ip firewall mangle print [find comment="Cliente Suspendido 192.168.1.100"]]
:local output "<html><body><h1>Servicio Suspendido</h1><p>Contacta al +56 2 3655 099</p></body></html>"
:put $output
}
```

---

## Gestión de Clientes Suspendidos

### Agregar Cliente

```bash
# Ejecutar en MikroTik
/ip firewall mangle add chain=prerouting src-address=192.168.1.100 \
action=mark-packet new-packet-mark=suspended_traffic \
comment="Juan Pérez"

/ip firewall nat add chain=dstnat packet-mark=suspended_traffic \
protocol=tcp dst-port=80 action=redirect to-ports=80 \
comment="Redirigir Juan a aviso"
```

### Ver Clientes Suspendidos

```
/ip firewall mangle print where chain=prerouting
```

### Remover Cliente

```
/ip firewall mangle remove [find comment="Juan Pérez"]
/ip firewall nat remove [find comment="Redirigir Juan a aviso"]
```

---

## Ventajas de Esta Solución

✓ No requiere servidor externo
✓ Funciona directamente en el MikroTik
✓ Bajo consumo de recursos
✓ Página se sirve en ~ms
✓ Fácil de implementar
✓ Personalizable

---

## Pasos Detallados para Implementar

### 1. Conectar al MikroTik

```bash
ssh admin@10.147.17.11
# Password: 1234
```

### 2. Crear archivo HTML

Pega esta línea completa en la terminal SSH:

```
/file add name=suspension.html contents="<!DOCTYPE html><html><head><meta charset=\"UTF-8\"><title>Servicio Suspendido</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:Arial,sans-serif;background:#f0f0f0;display:flex;justify-content:center;align-items:center;height:100vh}.container{background:white;padding:40px;border-radius:10px;box-shadow:0 0 20px rgba(0,0,0,0.1);max-width:500px;text-align:center}h1{color:#d63031;font-size:32px;margin-bottom:10px}p{color:#666;line-height:1.6;margin-bottom:20px}.contact{background:#f9f9f9;padding:20px;border-radius:5px;margin:20px 0}.phone{font-size:24px;color:#d63031;font-weight:bold}</style></head><body><div class=\"container\"><h1>⚠️ Servicio Suspendido</h1><p>Tu conexión ha sido suspendida por falta de pago.</p><div class=\"contact\"><p><strong>Contactanos:</strong></p><p class=\"phone\">+56 2 3655 099</p><p><small>Lunes a Viernes: 9:00 - 18:00</small></p></div><p><strong>Deposita en tu cuenta y reporta tu pago.</strong></p></div></body></html>"
```

### 3. Habilitar WWW Service

```
/ip service set www disabled=no port=80
```

### 4. Verificar archivo fue creado

```
/file print
```

Deberías ver `suspension.html` en la lista.

### 5. Servir la página

MikroTik buscará un archivo `index.html` por defecto. Renombra:

```
/file set [find name=suspension.html] name=index.html
```

O configura directamente en web service (más avanzado).

### 6. Crear regla para cliente de prueba

```
/ip firewall mangle add chain=prerouting src-address=192.168.1.100 \
action=mark-packet new-packet-mark=suspended_traffic \
comment="Cliente Prueba"

/ip firewall nat add chain=dstnat packet-mark=suspended_traffic \
protocol=tcp dst-port=80 action=redirect to-ports=80 \
comment="Redirigir a suspension"
```

### 7. Probar

Desde máquina con IP 192.168.1.100:
```
curl http://google.com
```

O abrir navegador e ir a cualquier sitio.

---

## Solución Alternativa: Usar Portal Cautivo

MikroTik tiene una función de "Hotspot" que puede servir una página cautiva:

```
/ip hotspot setup

# Luego configurar:
/ip hotspot profile set [find] redirect-to-folder="/flash/hotspot"
```

Esto es más robusto pero requiere más configuración.

---

## Información Importante

- **Puerto 80:** El servidor web de MikroTik escucha en puerto 80
- **Archivos:** Se guardan en la memoria del router (reinicio = pérdida)
- **Backup:** Hacer backup antes de cambios: `/system backup save`
- **Restore:** `/system backup restore name=nombre-backup`

---

**Creado con:** Claude Code
**Fecha:** 2025-11-14
**Router:** MikroTik RB5009UG+S+ (RouterOS 7.19.2)
