# Yesswera Admin Dashboard - Guía Completa

**Status**: ✅ ACTIVO Y FUNCIONAL
**Fecha**: 11 de Noviembre, 2025
**Versión**: 1.0

---

## Acceso Rápido

### 🌐 URLs

| Componente | URL | Descripción |
|-----------|-----|-------------|
| **App Pública** | http://192.168.100.3:3000/ | Interfaz para usuarios |
| **Admin Dashboard** | http://192.168.100.3:3000/admin/ | Panel administrativo |
| **API Stats** | http://192.168.100.3:3000/api/admin/stats | Estadísticas en tiempo real |
| **API Usuarios** | http://192.168.100.3:3000/api/admin/users | Lista de usuarios |
| **API Órdenes** | http://192.168.100.3:3000/api/admin/orders | Lista de órdenes |
| **API Entregas** | http://192.168.100.3:3000/api/admin/deliveries | Lista de entregas |

### 🔐 Credenciales Admin

```
Contraseña: admin123
```

⚠️ **IMPORTANTE**: Cambiar en producción

---

## Características del Dashboard

### 📊 Overview (Resumen)

Mostración en tiempo real de:
- **Usuarios Totales**: 👥 Cantidad de clientes, repartidores y negocios
- **Órdenes Totales**: 📦 Cantidad de pedidos pendientes, en entrega y completadas
- **Entregas Activas**: 🚚 Entregas en progreso y completadas hoy
- **Ingresos**: 💰 Total de ingresos y promedio por orden

### 📈 Gráficos

**Dos gráficos interactivos usando Chart.js:**

1. **Usuarios por Tipo** (Doughnut Chart)
   - Clientes (azul)
   - Repartidores (azul claro)
   - Negocios (amarillo)

2. **Órdenes por Estado** (Doughnut Chart)
   - Pendientes (rojo)
   - En Entrega (amarillo)
   - Completadas (verde)

### 👥 Pestaña Usuarios

**Tabla completa de usuarios registrados:**

Columnas:
- Tipo (badge: cliente, repartidor, negocio)
- Nombre completo
- Email
- Teléfono
- Fecha de Registro
- Botón Ver detalles

**Datos Mostrados:**
- Para Clientes: info básica
- Para Repartidores: tipo de transporte, placa de vehículo
- Para Negocios: nombre del negocio, RUC/NIT, categoría

### 📦 Pestaña Órdenes

**Tabla en tiempo real de todas las órdenes:**

Columnas:
- ID Orden (primeros 8 caracteres)
- Cliente (ID primeros 8 caracteres)
- Total ($)
- Estado (badge con color):
  - 🔴 Pendiente (rojo)
  - 🟡 En Entrega (amarillo)
  - 🟢 Completada (verde)
- Fecha de Creación
- Botón Ver detalles

**Detalles disponibles:**
- ID completo de orden
- ID del cliente
- Monto total
- Lista de servicios incluidos
- Timestamp exacto

### 🚚 Pestaña Entregas

**Tabla en tiempo real de entregas:**

Columnas:
- ID Entrega (primeros 8 caracteres)
- ID Orden (primeros 8 caracteres)
- ID Repartidor (primeros 8 caracteres)
- Estado (badge):
  - 🟡 Activo (en progreso)
  - 🟢 Completado
- Tiempo de Inicio
- Botón Ver detalles

**Detalles disponibles:**
- ID completo
- Orden asociada
- Repartidor asignado
- Estado actual
- Horarios de inicio y finalización

### 📋 Pestaña Logs

**Registro de auditoría de todos los eventos:**

Tipos de eventos registrados:
- `user_registered` - ✨ Nuevo usuario registrado
- `order_created` - 📦 Nueva orden creada
- `delivery_created` - 🚚 Nueva entrega asignada
- `user_login` - 👤 Usuario inició sesión

**Información por log:**
- Tipo de evento
- Descripción legible
- Timestamp exacto
- Detalles completos del evento

---

## Datos de Prueba Disponibles

El sistema viene precargado con datos de demostración:

### 👥 6 Usuarios Registrados

**Clientes (2):**
1. Juan Pérez (juan@test.com)
2. María García (maria@test.com)

**Repartidores (2):**
1. Carlos López - Moto - ABC-123
2. Pedro Rodríguez - Bicicleta

**Negocios (2):**
1. Tienda Central - RUC: 123456789
2. Restaurante La Casa - RUC: 987654321

### 📦 5 Órdenes

- 2 completadas ($25 + $20)
- 2 en entrega ($35 + $45)
- 1 pendiente ($60)

**Ingresos totales**: $185
**Promedio por orden**: $37

### 🚚 4 Entregas

- 2 completadas
- 2 activas (en progreso)

---

## Cómo Usar el Dashboard

### Paso 1: Acceder

1. Abre: http://192.168.100.3:3000/admin/
2. Ingresa contraseña: `admin123`
3. Haz clic en "Ingresar"

### Paso 2: Ver Overview

La pantalla de bienvenida muestra:
- 4 tarjetas con estadísticas principales
- 2 gráficos de distribución
- Total de usuarios, órdenes, entregas e ingresos

### Paso 3: Navegar por Pestañas

**Overview** 📊
- Gráficos de distribución
- Estadísticas resumidas

**Usuarios** 👥
- Lista completa de registrados
- Filtrados por tipo (cliente/repartidor/negocio)
- Hacer clic en "Ver" para detalles completos

**Órdenes** 📦
- Todas las órdenes en tiempo real
- Estados y montos
- Servicios incluidos en cada orden

**Entregas** 🚚
- Todas las entregas activas y completadas
- Repartidor asignado
- Tiempos de entrega

**Logs** 📋
- Registro de actividad
- Eventos de registro, órdenes y entregas
- Auditoría completa

### Paso 4: Ver Detalles

Haz clic en el botón "Ver" de cualquier fila para abrir un modal con:
- Todos los campos del registro
- Información completa y sin truncar
- Timestamps formateados

### Paso 5: Cerrar Sesión

Haz clic en "Salir" en la esquina superior derecha

---

## Actualización en Tiempo Real

El dashboard se actualiza **automáticamente cada 5 segundos**:

### Indicador de Estado

En la esquina superior derecha:
- 🟢 Verde pulsante: "Conectado" - Datos actualizados
- 🟡 Amarillo pulsante: "Actualizando..." - Trayendo nuevos datos
- 🔴 Rojo: "Error de conexión" - Problema con la conexión

### Auto-Refresh

Las siguientes secciones se actualizan automáticamente:
- Estadísticas generales
- Tabla de usuarios
- Tabla de órdenes
- Tabla de entregas
- Tabla de logs
- Gráficos

No es necesario refrescar manualmente la página.

---

## Integración con App Pública

La app pública ahora se integra completamente con el backend:

### Flujo de Registro

1. Usuario accede a http://192.168.100.3:3000/
2. Elige rol: Cliente, Repartidor o Negocio
3. Completa formulario con datos específicos del rol
4. Datos se guardan en `/data/users.json`
5. Dashboard admin muestra al nuevo usuario en tiempo real

### Flujo de Órdenes

1. Usuario agrega servicios al carrito
2. Crea cuenta o inicia sesión
3. Confirma la orden
4. Orden se guarda en `/data/orders.json`
5. Dashboard muestra orden como "pendiente"
6. Sistema puede asignar automáticamente repartidor
7. Entrega se crea en `/data/deliveries.json`
8. Dashboard muestra entrega como "activa"

### Sincronización

- Los cambios en la app pública se reflejan en el dashboard en < 5 segundos
- Los datos se guardan automáticamente en JSON
- No se requiere actualización manual

---

## API REST Endpoints

Todos los endpoints requieren autenticación:

```bash
curl -H "X-Admin-Password: admin123" http://192.168.100.3:3000/api/admin/ENDPOINT
```

### GET /api/admin/stats

**Devuelve:** Estadísticas en tiempo real

**Respuesta:**
```json
{
  "usuarios": {
    "total": 6,
    "clientes": 2,
    "repartidores": 2,
    "negocios": 2
  },
  "ordenes": {
    "total": 5,
    "pendientes": 1,
    "en_entrega": 2,
    "completadas": 2
  },
  "entregas": {
    "activas": 2,
    "completadas": 2,
    "total": 4
  },
  "finanzas": {
    "ingresos_totales": 185.0,
    "promedio_orden": 37.0
  },
  "timestamp": "2025-11-11T17:25:50.399239"
}
```

### GET /api/admin/users

**Devuelve:** Lista completa de usuarios

**Respuesta:**
```json
{
  "users": [
    {
      "id": "uuid",
      "tipo": "cliente",
      "nombre": "Juan Pérez",
      "email": "juan@test.com",
      "telefono": "1234567890",
      "timestamp": "2025-11-11T17:25:00Z",
      "estado": "activo"
    }
  ],
  "total": 6
}
```

### GET /api/admin/orders

**Devuelve:** Lista completa de órdenes

**Respuesta:**
```json
{
  "orders": [
    {
      "id": "uuid",
      "cliente_id": "uuid",
      "servicios": [...],
      "total": 25.0,
      "estado": "completada",
      "timestamp": "2025-11-11T17:25:00Z"
    }
  ],
  "total": 5
}
```

### GET /api/admin/deliveries

**Devuelve:** Lista completa de entregas

### GET /api/admin/logs

**Devuelve:** Log de auditoría completo

---

## Archivos de Datos

**Ubicación en servidor:** `/home/yesswera/YessweraWeb/data/`

### users.json
- Usuarios registrados
- Claves: email del usuario
- Valores: objeto usuario completo

### orders.json
- Órdenes creadas
- Claves: UUID único de orden
- Valores: datos de orden

### deliveries.json
- Entregas asignadas
- Claves: UUID único de entrega
- Valores: datos de entrega

### logs.json
- Registro de auditoría
- Array de eventos
- Máximo 1000 eventos (se rotan)

---

## Cambios de Producción Requeridos

⚠️ **ANTES DE USAR EN PRODUCCIÓN:**

1. **Cambiar contraseña admin** (línea 32 en server_enhanced.py):
   ```python
   ADMIN_PASSWORD = "una_contraseña_fuerte_aqui"
   ```

2. **Implementar base de datos real** en lugar de JSON:
   - PostgreSQL, MySQL, MongoDB, etc.
   - ORM para mapeo de objetos

3. **Implementar autenticación segura**:
   - JWT tokens en lugar de contraseña simple
   - Hash de contraseñas (bcrypt)
   - Sessions seguras

4. **Habilitar HTTPS**:
   - Certificado SSL/TLS
   - Redirección de HTTP a HTTPS

5. **Rate limiting**:
   - Limitar intentos de login
   - Prevenir fuerza bruta

6. **Validación de entrada**:
   - Sanitizar datos
   - Validar en backend

7. **Backups automáticos**:
   - Copias diarias de datos
   - Sistema de recuperación

---

## Troubleshooting

### Dashboard no carga

**Solución:**
1. Hard refresh: `Ctrl+F5` o `Cmd+Shift+R`
2. Verificar URL: http://192.168.100.3:3000/admin/
3. Verificar contraseña: `admin123`
4. Revisar consola (F12) para errores

### Datos no se actualizan

**Solución:**
1. Verificar conexión al servidor: ping 192.168.100.3
2. Revisar indicador de estado (esquina superior derecha)
3. Recargar página (F5)
4. Verificar que el servidor está corriendo

### Error 401 Unauthorized

**Solución:**
1. Contraseña incorrecta
2. Regenerar token de autenticación
3. Limpiar localStorage: Abrir DevTools > Application > Storage > Clear All

### Tabla vacía

**Solución:**
1. Los datos pueden no estar creados aún
2. Crear datos de prueba si es necesario
3. Verificar permisos de archivo en servidor

---

## Próximas Mejoras

### Corto Plazo
- [ ] Estadísticas por rango de fechas
- [ ] Exportar datos a CSV/Excel
- [ ] Búsqueda avanzada en tablas
- [ ] Filtros por estado/tipo

### Mediano Plazo
- [ ] Mapas de entregas en tiempo real
- [ ] Sistema de notificaciones
- [ ] Reportes automáticos
- [ ] Análisis de datos

### Largo Plazo
- [ ] Machine Learning para optimización
- [ ] Predicción de demanda
- [ ] Sistema de recomendaciones
- [ ] Mobile app admin

---

## Soporte

Para reportar problemas o solicitar cambios:
1. Documentar los pasos para reproducir
2. Incluir screenshots o videos
3. Anotar timestamp del evento
4. Revisar logs (/data/logs.json)

---

## Conclusión

El **Yesswera Admin Dashboard** está completamente funcional y listo para usar:

✅ Dashboard en tiempo real
✅ Datos de prueba precargados
✅ API REST funcional
✅ Integración con app pública
✅ Logs y auditoría
✅ Gráficos interactivos
✅ Detalles modales
✅ Auto-refresh cada 5 segundos

**URL**: http://192.168.100.3:3000/admin/
**Contraseña**: admin123

¡Listo para administrar tu plataforma Yesswera! 🚀

