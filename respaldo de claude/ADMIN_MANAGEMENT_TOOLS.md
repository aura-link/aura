# Herramientas Administrativas - Admin Dashboard

**Fecha**: November 12, 2025
**Status**: ✅ **HERRAMIENTAS ADMINISTRATIVAS AGREGADAS**
**Ubicación**: http://localhost:3000/admin/

---

## 🎯 Nuevas Funcionalidades

Se han agregado herramientas administrativas completas al panel del admin para gestionar usuarios (clientes, repartidores y negocios).

---

## 📋 Nuevo Tab: "Gestion"

### Ubicación
Admin Dashboard → Tab "Gestion"

### Características

#### 1. **Filtro por Rol**
Dropdown para filtrar usuarios por tipo:
- Todos los roles
- Clientes
- Repartidores
- Negocios

#### 2. **Tabla de Usuarios**
Muestra todos los usuarios con columnas:
- **Tipo**: cliente, repartidor, o negocio
- **Nombre**: Nombre completo del usuario
- **Email**: Email registrado
- **Teléfono**: Número de teléfono
- **Estado**: activo, inactivo, suspendido
- **Acciones**: Botones para editar y eliminar

#### 3. **Botones de Acción**

**Editar**
- Abre modal con formulario
- Permite modificar:
  - Nombre
  - Teléfono
  - Estado (Activo/Inactivo/Suspendido)
- Email y Tipo son de solo lectura (no se pueden cambiar)

**Eliminar**
- Solicita confirmación
- Elimina usuario de la lista
- Se muestra alerta de confirmación

---

## 🖥️ Cómo Usar

### Acceder a Gestión de Usuarios

1. Ve a http://localhost:3000/admin/
2. Ingresa contraseña: `admin123`
3. Click en tab "Gestion"

### Filtrar Usuarios por Rol

1. En la sección "Gestion", busca el dropdown
2. Selecciona:
   - "Clientes" → Ver solo clientes
   - "Repartidores" → Ver solo repartidores
   - "Negocios" → Ver solo negocios
   - "Todos los roles" → Ver todos

### Editar un Usuario

1. Encuentra el usuario en la tabla
2. Click en botón "Editar"
3. Se abre modal con formulario
4. Modifica los datos:
   - Nombre: Cambia el nombre del usuario
   - Teléfono: Actualiza número
   - Estado: Cambia a Activo/Inactivo/Suspendido
5. Click "Guardar Cambios"
6. Usuario se actualiza en la tabla

### Eliminar un Usuario

1. Encuentra el usuario en la tabla
2. Click en botón "Eliminar" (rojo)
3. Confirma eliminación en popup
4. Usuario se elimina de la tabla

---

## 📊 Estado del Usuario

Los estados disponibles son:

| Estado | Color | Significado |
|--------|-------|------------|
| **Activo** | Verde | Usuario puede usar la plataforma |
| **Inactivo** | Rojo | Usuario no puede iniciar sesión |
| **Suspendido** | Rojo | Cuenta suspendida por violación de términos |

---

## 🔧 Características Técnicas

### Frontend
✅ Nuevo tab "Gestion" en HTML
✅ Modal para editar usuarios
✅ Filtro dinámico por rol
✅ Tabla con información completa
✅ Botones de editar y eliminar

### Funciones JavaScript Agregadas

1. **loadGestionTable()**
   - Carga usuarios desde `/api/admin/users`
   - Actualiza tabla de gestión

2. **updateGestionTable(users)**
   - Renderiza tabla con usuarios
   - Muestra estado con color
   - Agrega botones de acción

3. **filterUsersByRol(rol)**
   - Filtra usuarios por tipo
   - Actualiza tabla dinámicamente

4. **openEditUserModal(email, user)**
   - Abre modal de edición
   - Precarga datos del usuario
   - Setup del form

5. **saveUserChanges(email)**
   - Guarda cambios de usuario
   - Actualiza tabla
   - Muestra confirmación

6. **deleteUser(email)**
   - Solicita confirmación
   - Elimina usuario
   - Actualiza tabla

---

## 💾 Almacenamiento

Actualmente, los cambios se guardan en **localStorage** con key:
```
admin_user_{email}
```

**Para producción**, se requiere implementar:
- Endpoint POST `/api/admin/users/update`
- Endpoint DELETE `/api/admin/users/delete`
- Actualización de `users.json` en servidor

---

## 🚀 Próximas Mejoras (Backend)

Para completar la funcionalidad, se necesita:

### 1. Endpoint: Actualizar Usuario
```
POST /api/admin/users/update
Body: {
  email: string,
  nombre: string,
  telefono: string,
  estado: string
}
Response: { success: true, user: {...} }
```

### 2. Endpoint: Eliminar Usuario
```
DELETE /api/admin/users/:email
Response: { success: true, message: "User deleted" }
```

### 3. Endpoint: Crear Usuario
```
POST /api/admin/users/create
Body: {
  tipo: string,
  nombre: string,
  email: string,
  telefono: string
}
Response: { success: true, user: {...} }
```

---

## ✅ Checklist de Uso

### Tab Gestion
- [ ] Acceder a http://localhost:3000/admin/
- [ ] Ingresar contraseña admin123
- [ ] Ver tab "Gestion"
- [ ] Ver lista de usuarios
- [ ] Filtro por rol funciona
- [ ] Botón "Editar" abre modal
- [ ] Modal muestra datos correcto
- [ ] Puedo editar nombre
- [ ] Puedo editar teléfono
- [ ] Puedo cambiar estado
- [ ] Botón "Guardar Cambios" funciona
- [ ] Botón "Cancelar" cierra modal
- [ ] Botón "Eliminar" solicita confirmación
- [ ] Usuario se elimina tras confirmar

---

## 🎨 Interfaz

### Modal de Edición

```
┌─────────────────────────────────┐
│ Editar Usuario              [X] │
├─────────────────────────────────┤
│ Tipo: cliente               [RO]│
│ Nombre: Juan Pérez        [Edit]│
│ Email: juan@test.com        [RO]│
│ Telefono: 1234567890      [Edit]│
│ Estado: [▼ Activo/Inactivo]     │
│                                 │
│ [Guardar Cambios] [Cancelar]    │
└─────────────────────────────────┘
```

### Tabla de Usuarios

```
┌─────────────────────────────────────┐
│ Gestion de Usuarios    [▼ Rol...]   │
├─────────────────────────────────────┤
│ Tipo │ Nombre │ Email │ Acciones    │
├─────────────────────────────────────┤
│ cliente │ Juan │ juan@... │ [Editar] │
│ repartidor │ Carlos │ carlos@... │ [×] │
│ negocio │ Maria │ maria@... │ [Editar]│
└─────────────────────────────────────┘
```

---

## 🔐 Seguridad

✅ Solo admin puede acceder
✅ Confirmación antes de eliminar
✅ Email y Tipo no editables
✅ Validación de campos requeridos
✅ Modal con overlay

---

## 📱 Responsividad

Las herramientas se adaptan a:
- ✅ Desktop (pantalla completa)
- ✅ Tablet (tabla scrollable)
- ✅ Móvil (ajustes automáticos)

---

## 🆘 Troubleshooting

### Modal no abre
```
Solución:
1. Revisa DevTools Console (F12)
2. Verifica que editUserModal exista
3. Recarga página (Ctrl+F5)
```

### Tabla vacía
```
Solución:
1. Verifica que API /api/admin/users responda
2. Abre DevTools Network tab
3. Busca request a /api/admin/users
4. Verifica response JSON
```

### Filtro no funciona
```
Solución:
1. Abre Console (F12)
2. Verifica que filterUsersByRol() existe
3. Comprueba que allUsers tiene datos
```

---

## 📝 Cambios Realizados

### Archivo Modificado
- `public/admin/index.html`

### Nuevos Elementos HTML
- Tab button: "Gestion"
- Div id="gestion" (contenido del tab)
- Select id="filterRol" (filtro)
- Tbody id="gestionTableBody" (tabla)
- Modal id="editUserModal" (edición)
- Form id="editUserForm" (formulario)

### Nuevas Funciones JavaScript
- loadGestionTable()
- updateGestionTable()
- filterUsersByRol()
- openEditUserModal()
- closeEditModal()
- saveUserChanges()
- deleteUser()

### Líneas de Código Agregadas
- HTML: +40 líneas
- JavaScript: +110 líneas
- Total: +150 líneas

---

## 🎯 Ejemplo de Uso Completo

```
1. Admin abre http://localhost:3000/admin/
2. Ingresa password: admin123
3. Hace click en tab "Gestion"
4. Ve lista de 6 usuarios
5. Selecciona "Clientes" en filtro
6. Ahora ve solo 3 clientes
7. Hace click en "Editar" de Juan Pérez
8. Modal abre con datos de Juan
9. Cambia nombre a "Juan Carlos Pérez"
10. Cambia estado a "inactivo"
11. Click "Guardar Cambios"
12. Modal se cierra
13. Tabla se actualiza
14. Ve nombre y estado actualizados
```

---

## ✨ Próximas Funciones (Roadmap)

- [ ] Crear nuevo usuario desde admin
- [ ] Buscar usuarios por nombre/email
- [ ] Exportar lista de usuarios
- [ ] Cambiar permisos por usuario
- [ ] Ver historial de cambios
- [ ] Asignar repartidor a órdenes
- [ ] Generar reportes

---

**Status**: ✅ FUNCIONALIDAD AGREGADA Y LISTA PARA USAR

🚀 ¡Las herramientas administrativas están disponibles en el tab "Gestion" del admin!
