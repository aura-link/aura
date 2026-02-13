# Sistema Multi-Portal - Guía de Implementación

**Status**: Iniciando Fase 2
**Objetivo**: Crear portales separados para Cliente, Repartidor y Negocio
**Timeline**: ~10-12 horas de desarrollo

---

## 📋 Resumen Ejecutivo

Vamos a crear un sistema donde:

✅ **Portal Unificado** (login.html)
- Input: Email O Teléfono + Contraseña
- El sistema detecta automáticamente si es Cliente, Repartidor o Negocio
- Redirige al dashboard correspondiente

✅ **3 Dashboards Independientes**
- `/cliente/` - Para clientes (carrito, órdenes, búsqueda)
- `/repartidor/` - Para repartidores (entregas, ganancias, mapa)
- `/negocio/` - Para negocios (órdenes, catálogo, ganancias)

✅ **App Pública Sigue Funcionando**
- Búsqueda de productos
- Carrito
- Pop-ups publicitarios
- Login/Registro normal

---

## 🗂️ Estructura de Carpetas

```
C:/claude/YessweraWeb/public/
├── index.html (v4 - App pública)
├── js/
│   ├── auth.js (JWT)
│   └── shared.js (Funciones compartidas)
├── css/
│   ├── portals.css (Estilos portales)
│   └── popups.css (Estilos pop-ups)
├── portal/
│   ├── index.html (Login unificado)
│   └── js/
│       └── portal.js (Lógica login)
├── cliente/
│   ├── index.html (Dashboard cliente)
│   └── js/
│       └── dashboard.js (Lógica cliente)
├── repartidor/
│   ├── index.html (Dashboard repartidor)
│   └── js/
│       └── dashboard.js (Lógica repartidor)
├── negocio/
│   ├── index.html (Dashboard negocio)
│   └── js/
│       └── dashboard.js (Lógica negocio)
└── admin/
    └── index.html (Dashboard admin - existente)
```

---

## 1️⃣ PASO 1: Backend - Agregar Endpoint de Detección

**Archivo**: `server_jwt.py`

**Agregar método**:
```python
def handle_user_type(self):
    """POST /api/user-type - Detectar tipo de usuario por email o teléfono"""
    try:
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8', errors='ignore')
        data = json.loads(body) if body else {}

        email_or_phone = data.get('emailOrPhone', '').strip()

        if not email_or_phone:
            self.send_json_response({"error": "Missing emailOrPhone"}, 400)
            return

        users = load_json_file(USERS_FILE)
        if not isinstance(users, dict):
            users = {}

        # Buscar por email o teléfono
        user = None
        user_email = None

        if '@' in email_or_phone:
            if email_or_phone in users:
                user = users[email_or_phone]
                user_email = email_or_phone
        else:
            for email, usr in users.items():
                if usr.get('telefono') == email_or_phone:
                    user = usr
                    user_email = email
                    break

        if not user:
            self.send_json_response({"success": False, "error": "User not found"}, 404)
            return

        self.send_json_response({
            "success": True,
            "email": user_email,
            "tipo": user.get('tipo'),
            "nombre": user.get('nombre')
        })

    except Exception as e:
        self.send_json_response({"error": str(e)}, 500)
```

**En do_POST**, agregar**:
```python
elif path == "/api/user-type":
    self.handle_user_type()
```

**En do_GET**, agregar**:
```python
elif path == "/api/user-type":
    self.handle_user_type()
```

---

## 2️⃣ PASO 2: Portal Login (portal/index.html)

✅ **CREADO** - Ver archivo en C:/claude/YessweraWeb/public/portal/index.html

**Características**:
- Login con email O teléfono
- Auto-detección de tipo de usuario
- Redirect automático a dashboard correcto
- Estilos Yesswera (verde, dark theme)

---

## 3️⃣ PASO 3: Dashboard Cliente

**Archivo**: `cliente/index.html`

**Secciones**:
1. **Header** - Nombre usuario, perfil, salir
2. **Mi Carrito Activo** - Items, total, confirmar
3. **Mis Órdenes en Progreso** - Estado, repartidor, mapa
4. **Búsqueda Integrada** - Buscar productos, agregar
5. **Historial** - Órdenes pasadas, repetir
6. **Mi Perfil** - Datos, dirección, métodos pago

**API Endpoints Necesarios**:
```
GET  /api/cliente/cart           → Obtener carrito
POST /api/cliente/cart           → Agregar item
POST /api/orden/confirm          → Confirmar orden
GET  /api/cliente/ordenes        → Mis órdenes
GET  /api/cliente/ordenes/:id    → Detalles orden
GET  /api/cliente/historial      → Historial
GET  /api/productos              → Buscar productos
```

---

## 4️⃣ PASO 4: Dashboard Repartidor

**Archivo**: `repartidor/index.html`

**Secciones**:
1. **Header** - Nombre repartidor, vehículo, ganancias
2. **Entregas Disponibles** - Listar entregas sin asignar, aceptar
3. **Mi Entrega Activa** - Orden actual, mapa, "Llegué", "Completar"
4. **Historial de Entregas** - Todas las entregas hechas, ganancias
5. **Mi Vehículo** - Tipo, placa, documentos
6. **Mis Ganancias** - Gráfico, total día/semana/mes

**API Endpoints Necesarios**:
```
GET  /api/repartidor/entregas-disponibles
POST /api/repartidor/aceptar-entrega/:id
GET  /api/repartidor/entrega-activa
POST /api/repartidor/entrega/llegue
POST /api/repartidor/entrega/completar
GET  /api/repartidor/historial
GET  /api/repartidor/ganancias
```

---

## 5️⃣ PASO 5: Dashboard Negocio

**Archivo**: `negocio/index.html`

**Secciones**:
1. **Header** - Nombre negocio, órdenes hoy, ingresos
2. **Dashboard Overview** - Órdenes, ingresos, pendientes
3. **Mi Catálogo** - Productos, agregar, editar, stock
4. **Órdenes Recibidas** - Pendientes, en preparación, listas
5. **Gestión Entregas** - Seleccionar repartidor, estado
6. **Ganancias** - Gráfico, ingresos, productos top
7. **Mi Perfil** - Datos negocio, horarios, documentos

**API Endpoints Necesarios**:
```
GET  /api/negocio/ordenes-pendientes
POST /api/negocio/orden/confirmar/:id
POST /api/negocio/orden/listo/:id
GET  /api/negocio/catalogo
POST /api/negocio/producto/agregar
POST /api/negocio/producto/editar/:id
GET  /api/negocio/ganancias
GET  /api/negocio/repartidores-disponibles
```

---

## 6️⃣ PASO 6: Sistema de Pop-ups Publicitarios

**Archivo**: `js/popups.js`

**Pop-up Types**:
```javascript
const POPUP_TYPES = {
    WELCOME: { title: "Bienvenido", message: "20% en tu primer pedido", duration: 15000 },
    FLASH_SALE: { title: "¡Oferta Flash!", message: "50% en pizzas - Solo 1 hora", duration: 10000 },
    REFERRAL: { title: "Gana Dinero", message: "Invita amigos y gana $10", duration: 10000 },
    NEARBY: { title: "Repartidor Cerca", message: "¡Realiza tu pedido ahora!", duration: 8000 },
    REMINDER: { title: "¿Tienes hambre?", message: "Tu comida favorita te espera", duration: 12000 }
};
```

**Mostrar**:
- Al cargar página (Welcome)
- Cada 5 minutos (random)
- Al agregar al carrito (sugerencia)
- Al ver catálogo (flash sale)

**Funcionalidad**:
- Cerrar con X
- Auto-cerrar después de duración
- Click en botón = tomar acción

---

## 7️⃣ PASO 7: Archivo Compartido js/shared.js

```javascript
/**
 * Funciones compartidas entre portales
 */

// Obtener tipo de usuario desde localStorage
function getUserType() {
    const session = JSON.parse(localStorage.getItem('yesswera_session') || '{}');
    return session.tipo || null;
}

// Obtener datos del usuario
function getUser() {
    const session = JSON.parse(localStorage.getItem('yesswera_session') || '{}');
    return session.user || null;
}

// Obtener token
function getToken() {
    const session = JSON.parse(localStorage.getItem('yesswera_session') || '{}');
    return session.token || null;
}

// Headers para API requests
function getAuthHeaders() {
    return {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
    };
}

// Verificar autenticación
function checkAuth() {
    const token = getToken();
    if (!token) {
        window.location.href = '/portal/';
        return false;
    }
    return true;
}

// Verificar tipo de usuario
function requireRole(role) {
    const userType = getUserType();
    if (userType !== role) {
        window.location.href = '/';
        return false;
    }
    return true;
}

// Logout
function logout() {
    localStorage.removeItem('yesswera_session');
    window.location.href = '/portal/';
}
```

---

## 8️⃣ PASO 8: CSS Portal - portals.css

```css
/* Variables por perfil */
:root {
    --cliente-color: #4CAF50;    /* Verde */
    --repartidor-color: #2196F3;  /* Azul */
    --negocio-color: #FF9800;     /* Naranja */
    --admin-color: #F44336;       /* Rojo */
}

/* Dashboard header */
.dashboard-header {
    background: linear-gradient(135deg, var(--profile-color) 0%, rgba(0,0,0,0.8) 100%);
    padding: 20px;
    margin-bottom: 30px;
    border-radius: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.user-greeting {
    font-size: 1.5em;
    font-weight: bold;
    color: #fff;
}

.user-actions {
    display: flex;
    gap: 15px;
}

/* Cards */
.card {
    background: #1a1a1a;
    border: 1px solid #333;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 20px;
    transition: all 0.3s;
}

.card:hover {
    border-color: var(--profile-color);
    transform: translateY(-5px);
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}

.card-title {
    font-size: 1.2em;
    font-weight: bold;
    margin-bottom: 15px;
    color: var(--profile-color);
}

/* Botones */
.btn-profile {
    background: var(--profile-color);
    color: #fff;
    padding: 10px 20px;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: bold;
    transition: all 0.3s;
}

.btn-profile:hover {
    opacity: 0.8;
    transform: translateY(-2px);
}
```

---

## 📊 Datos Necesarios en JSON

### users.json (Actualizado)
```json
{
    "juan@test.com": {
        "id": "uuid",
        "tipo": "cliente",
        "nombre": "Juan Pérez",
        "email": "juan@test.com",
        "telefono": "1234567890",
        "timestamp": "2025-11-12...",
        "estado": "activo",
        "direccion": "Calle Principal 123",
        "metodos_pago": ["tarjeta", "efectivo"]
    }
}
```

### catalogo.json (Nuevo)
```json
{
    "negocio_id": {
        "nombre_negocio": "Mi Negocio",
        "productos": [
            {
                "id": "uuid",
                "nombre": "Hamburguesa",
                "descripcion": "Con queso y tomate",
                "precio": 15,
                "categoria": "Comida",
                "stock": 50,
                "activo": true,
                "imagen": "url"
            }
        ]
    }
}
```

### ordenes.json (Actualizado con más campos)
```json
{
    "order_id": {
        "id": "uuid",
        "cliente_id": "uuid",
        "negocio_id": "uuid",
        "repartidor_id": "uuid",
        "estado": "pendiente|confirmado|en_prep|listo|en_entrega|completado",
        "items": [
            {"producto_id": "uuid", "nombre": "Pizza", "cantidad": 2, "precio": 20}
        ],
        "total": 50,
        "direccion_entrega": "Calle X 123",
        "coordenadas": {"lat": 0, "lng": 0},
        "timestamp": "2025-11-12...",
        "entrega_id": "uuid"
    }
}
```

---

## 🔄 Flujos de Usuario

### Cliente
```
1. Accede a http://192.168.100.3:3000/
2. Navega, busca "Pizzas"
3. Ve pop-up: "20% descuento"
4. Agrega 2 pizzas al carrito
5. Click "Comprar" → Redirige a /portal
6. Login con email + password
7. Sistema detecta: CLIENTE
8. Redirige a /cliente
9. Ve su carrito con las pizzas
10. Confirma orden
11. Sigue orden en tiempo real (mapa)
12. Recibe en dirección
```

### Repartidor
```
1. Accede a /portal
2. Login con teléfono + password
3. Sistema detecta: REPARTIDOR
4. Redirige a /repartidor
5. Ve "Entregas Disponibles"
6. Click "Aceptar" en una
7. Ve mapa con ruta
8. Navega a dirección
9. Click "Llegué" → Toma foto
10. Click "Completar" → Entrega lista
11. Gana $, actualiza saldo
```

### Negocio
```
1. Accede a /portal
2. Login con email + password
3. Sistema detecta: NEGOCIO
4. Redirige a /negocio
5. Ve "3 órdenes pendientes"
6. Confirma recepciones
7. Prepara comida
8. Click "Listo" → A los repartidores
9. Repartidor toma y entrega
10. Recibe su pago (80%)
```

---

## ✅ Checklist de Implementación

### Backend
- [ ] Agregar POST /api/user-type
- [ ] Actualizar POST /api/login (retornar tipo)
- [ ] Agregar GET /api/repartidor/entregas-disponibles
- [ ] Agregar POST /api/negocio/catalogo
- [ ] Actualizar data files (catalogo.json, ordenes actualizado)

### Frontend
- [ ] Crear portal/index.html ✅ (CREADO)
- [ ] Crear cliente/index.html
- [ ] Crear repartidor/index.html
- [ ] Crear negocio/index.html
- [ ] Crear js/portals.js (compartido)
- [ ] Crear js/popups.js
- [ ] Crear css/portals.css
- [ ] Agregar pop-ups a index.html público

### Testing
- [ ] Test login con email
- [ ] Test login con teléfono
- [ ] Test auto-redirect cliente
- [ ] Test auto-redirect repartidor
- [ ] Test auto-redirect negocio
- [ ] Test pop-ups
- [ ] Test carrito cliente
- [ ] Test aceptar entrega repartidor
- [ ] Test confirmar orden negocio

---

## 🚀 Próximos Pasos

1. **Implementar backend** (user-type endpoint)
2. **Crear 3 dashboards** (cliente, repartidor, negocio)
3. **Agregar pop-ups** a app pública
4. **Testing completo**
5. **Deploy a servidor**

---

## 📚 Referencia de API

Todos los endpoints nuevos requieren JWT token:

```bash
curl -X POST http://192.168.100.3:3000/api/user-type \
  -H "Content-Type: application/json" \
  -d '{"emailOrPhone": "juan@test.com"}'

# Respuesta:
{
  "success": true,
  "email": "juan@test.com",
  "tipo": "cliente",
  "nombre": "Juan Pérez"
}
```

---

**Status**: Plan completo, listo para implementar
**Estimado**: 10-12 horas de desarrollo
**Inicio**: Inmediato

¿Empezamos? 🚀

