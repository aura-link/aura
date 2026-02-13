# YESSWERA - Documentación Completa del Sistema
## Plataforma de Delivery con Sistema de 3 Códigos de Seguridad

**Fecha de actualización:** 29 de Enero 2026

---

## 1. ARQUITECTURA DEL SISTEMA

### Componentes Principales
- **Backend:** Python (server_jwt.py) con JWT authentication
- **Frontend Mobile:** React Native con Expo Router
- **Base de datos:** Archivos JSON (users.json, orders.json)
- **Servidor:** VPS en 147.79.101.73
- **Túnel:** Cloudflare Tunnel para acceso externo

### Servicios Systemd
```bash
# Backend API
sudo systemctl status yesswera-backend.service
sudo systemctl restart yesswera-backend.service

# Expo Development Server
sudo systemctl status yesswera-expo.service
sudo systemctl restart yesswera-expo.service
```

### URLs de Acceso
- **API Backend:** https://api.yesswera.com/api/
- **Expo Metro:** https://expo.yesswera.com (para desarrollo)
- **Web:** https://www.yesswera.com (Vercel)

---

## 2. REGISTRO DE USUARIOS

### Endpoint
```
POST /api/register
```

### Campos Requeridos (TODOS los tipos)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `tipo` | string | Tipo de usuario: `cliente`, `negocio`, `repartidor` |
| `email` | string | Email único del usuario |
| `nombre` | string | Nombre completo |

### Campos Opcionales (TODOS los tipos)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `password` | string | Contraseña (default: "default123") |
| `phone` o `telefono` | string | Número de teléfono |
| `address` o `direccion` | string | Dirección |

### Campos Adicionales por Tipo

#### Para Repartidor (`tipo: "repartidor"`)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `transporte` | string | Tipo de vehículo |
| `placa` | string | Placa del vehículo |

#### Para Negocio (`tipo: "negocio"`)
| Campo | Tipo | Descripción |
|-------|------|-------------|
| `negocio_nombre` | string | Nombre del negocio |

### Ejemplos de Registro

#### Cliente
```json
{
  "tipo": "cliente",
  "email": "cliente@email.com",
  "nombre": "Juan Pérez",
  "password": "mipassword123",
  "telefono": "3001234567",
  "direccion": "Calle 123 #45-67"
}
```

#### Repartidor
```json
{
  "tipo": "repartidor",
  "email": "repartidor@email.com",
  "nombre": "Carlos García",
  "password": "mipassword123",
  "telefono": "3009876543",
  "transporte": "moto",
  "placa": "ABC123"
}
```

#### Negocio
```json
{
  "tipo": "negocio",
  "email": "restaurante@email.com",
  "nombre": "Pedro Martínez",
  "password": "mipassword123",
  "telefono": "3005556666",
  "negocio_nombre": "Restaurante El Sabor",
  "direccion": "Avenida Principal #100"
}
```

---

## 3. LOGIN Y AUTENTICACIÓN

### Endpoint
```
POST /api/login
```

### Request
```json
{
  "email": "usuario@email.com",
  "password": "password123"
}
```

### Response
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": "uuid",
    "tipo": "cliente|negocio|repartidor",
    "nombre": "Nombre",
    "email": "email@example.com"
  }
}
```

---

## 4. FLUJO COMPLETO DE ORDEN

### Estados de la Orden
```
pending → accepted → assigned → handed_to_driver → in_transit → delivered
```

### Paso a Paso

#### 1. Cliente crea orden
```
POST /api/orders
Headers: Authorization: Bearer {token}
Body: { businessId, items, deliveryAddress }
```

#### 2. Negocio acepta orden
```
POST /api/orders/{orderId}/accept
Headers: Authorization: Bearer {token}
```
- Genera `businessCode` (código de 4 dígitos para el negocio)

#### 3. Repartidor toma orden
```
POST /api/orders/{orderId}/take
Headers: Authorization: Bearer {token}
```
- Asigna el repartidor a la orden
- Estado cambia a `assigned`

#### 4. Negocio valida código del repartidor
```
POST /api/orders/{orderId}/validate-driver
Headers: Authorization: Bearer {token}
Body: { code: "XXXX" }
```
- Genera `handoverCode` (código para confirmar entrega al repartidor)
- Estado cambia a `driver_verified`

#### 5. Repartidor confirma recepción
```
POST /api/orders/{orderId}/confirm-handover
Headers: Authorization: Bearer {token}
Body: { handoverCode: "XXXX" }
```
- Genera `deliveryCode` (código para el cliente)
- Estado cambia a `handed_to_driver`

#### 6. Repartidor confirma pickup
```
POST /api/orders/{orderId}/confirm-pickup
Headers: Authorization: Bearer {token}
```
- Estado cambia a `in_transit`

#### 7. Repartidor valida entrega con cliente
```
POST /api/orders/{orderId}/validate-delivery
Headers: Authorization: Bearer {token}
Body: { code: "XXXX" }
```
- Estado cambia a `delivered`

---

## 5. SISTEMA DE 3 CÓDIGOS DE SEGURIDAD

| Código | Generado en | Quién lo ve | Quién lo ingresa | Propósito |
|--------|-------------|-------------|------------------|-----------|
| `businessCode` | Accept orden | Negocio | Repartidor muestra al negocio | Verificar identidad del repartidor |
| `handoverCode` | Validate-driver | Negocio muestra | Repartidor ingresa | Confirmar que negocio entregó la orden |
| `deliveryCode` | Confirm-handover | Repartidor | Cliente dice al repartidor | Confirmar entrega al cliente final |

---

## 6. SISTEMA DE MODOS PARA NEGOCIO

### Pantalla de Selección de Modo
Después del login, el negocio ve dos opciones:

#### Modo Completo
- Acceso a dashboard completo
- Puede aceptar/rechazar órdenes
- Puede ver comandas
- Puede validar códigos de repartidores

#### Modo Cocina (Comandas)
- Solo ve lista de comandas en orden FIFO
- Puede marcar órdenes como "Lista"
- No puede aceptar nuevas órdenes
- Ideal para personal de cocina

### Endpoint para Marcar Lista
```
POST /api/orders/{orderId}/ready
Headers: Authorization: Bearer {token}
```

---

## 7. FUNCIONALIDADES POR PERFIL

### Cliente
- Ver menú de negocios
- Crear órdenes
- Ver tracking en tiempo real
- Ver código de entrega
- Historial de órdenes (con opción de ocultar)

### Negocio
- **Modo Completo:**
  - Dashboard con estadísticas
  - Aceptar/rechazar órdenes
  - Ver comandas con número prominente
  - Validar código del repartidor
  - Mostrar código handover

- **Modo Cocina:**
  - Lista de comandas ordenadas por llegada
  - Contador de pendientes/listas
  - Marcar órdenes como listas
  - Auto-refresh cada 5 segundos

### Repartidor
- Toggle online/offline (persiste al cerrar app)
- No puede desconectarse con orden activa
- Ver órdenes disponibles
- Tomar órdenes
- Mostrar código al negocio
- Ingresar código handover
- Confirmar pickup
- Ingresar código de entrega del cliente

---

## 8. ARCHIVOS PRINCIPALES DEL PROYECTO

### Backend (Servidor)
```
/home/yesswera/YessweraWeb/
├── server_jwt.py          # Servidor principal con JWT
├── data/
│   ├── users.json         # Base de datos de usuarios
│   └── orders.json        # Base de datos de órdenes
```

### Frontend Mobile
```
/home/yesswera/yesswera-app-mobile/
├── app/
│   ├── index.tsx              # Pantalla principal (3 botones)
│   ├── login.tsx              # Login universal
│   ├── register.tsx           # Registro de usuarios
│   ├── _layout.tsx            # Layout con configuración de navegación
│   ├── business/
│   │   ├── mode-select.tsx    # Selección de modo
│   │   ├── dashboard.tsx      # Dashboard completo
│   │   ├── orders.tsx         # Lista de órdenes
│   │   └── comandas.tsx       # Vista de cocina
│   ├── driver/
│   │   ├── dashboard.tsx      # Dashboard repartidor
│   │   └── active-order.tsx   # Orden activa
│   └── client/
│       ├── dashboard.tsx      # Dashboard cliente
│       └── order-tracking.tsx # Tracking de orden
├── contexts/
│   └── auth.tsx               # Contexto de autenticación
└── constants/
    ├── api.ts                 # URL base del API
    └── colors.ts              # Colores del tema
```

---

## 9. CONFIGURACIONES IMPORTANTES

### Bloqueo de Navegación
Los perfiles de negocio y repartidor tienen bloqueado:
- Botón back del hardware (BackHandler)
- Botón back del header (headerShown: false)
- Solo pueden salir con logout

### Persistencia de Estado Online (Repartidor)
```typescript
// Se guarda en AsyncStorage
storage.setItem('driver_online_status', 'true'|'false')
```

### Auto-refresh
- Comandas: cada 5 segundos
- Dashboard repartidor: cada 10 segundos
- Order tracking: cada 5 segundos

---

## 10. COMANDOS ÚTILES

### Reiniciar Servicios
```bash
sudo systemctl restart yesswera-backend.service
sudo systemctl restart yesswera-expo.service
```

### Ver Logs
```bash
sudo journalctl -u yesswera-backend.service -f
sudo journalctl -u yesswera-expo.service -f
```

### Limpiar Órdenes (Desarrollo)
```bash
echo '{}' > /home/yesswera/YessweraWeb/data/orders.json
```

### Test de API
```bash
# Ping
curl https://api.yesswera.com/api/ping

# Login
curl -X POST https://api.yesswera.com/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"password"}'

# Registro
curl -X POST https://api.yesswera.com/api/register \
  -H "Content-Type: application/json" \
  -d '{"tipo":"cliente","email":"nuevo@test.com","nombre":"Test User","password":"123456"}'
```

---

## 11. PROBLEMAS CONOCIDOS Y SOLUCIONES

### Teclado oculta campos de código
**Solución:** Implementado `KeyboardAvoidingView` con offset de 100px en:
- business/orders.tsx (modal de código)
- driver/active-order.tsx (campos de código)

### Driver se desconecta automáticamente
**Solución:**
- Estado online persiste en AsyncStorage
- Validación antes de permitir offline con orden activa

### Pantalla blanca al presionar back
**Solución:**
- Cambiar de `useEffect` a `useFocusEffect` para BackHandler
- Agregar `headerShown: false` en _layout.tsx

---

## 12. PRÓXIMAS MEJORAS SUGERIDAS

1. **Impresión de comandas** - Conectar con impresora térmica
2. **Notificaciones push** - FCM para alertas en tiempo real
3. **Historial de ganancias** - Para repartidores
4. **Calificaciones** - Sistema de rating
5. **Zonas de cobertura** - Geofencing para negocios
6. **Pagos integrados** - Pasarela de pagos

---

## 13. CONTACTO Y SOPORTE

**Servidor:** VPS Hostinger 147.79.101.73
**Dominio:** yesswera.auralink.lat
**Túnel:** Cloudflare Tunnel

---

*Documentación generada automáticamente - Yesswera Delivery Platform v1.0*
