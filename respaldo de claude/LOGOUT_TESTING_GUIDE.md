# Guía de Testing - Sistema Logout/Login Corregido

**Fecha**: November 12, 2025
**Objetivo**: Verificar que el logout limpia completamente la sesión
**Tiempo**: 5-10 minutos

---

## 🎯 Tests a Realizar

### TEST 1: Admin Logout y Reinicio

**Procedimiento**:
```
1. Abre navegador → http://localhost:3000/admin/
2. Ingresa password: admin123
3. Espera a que cargue dashboard
4. Abre DevTools: F12 → Application → localStorage
5. Busca "yesswera_admin_auth"
   ✅ Debe estar presente con valor: admin123
6. Cierra DevTools
7. Busca botón "Salir" (esquina inferior derecha)
8. Click en "Salir"
9. Abre DevTools nuevamente
10. Verifica localStorage
    ✅ "yesswera_admin_auth" DEBE ESTAR VACÍO/NO EXISTIR
11. Verifica que estés en login screen
    ✅ Campo de contraseña debe estar vacío
    ✅ Campo debe tener focus (cursor visible)
12. Ingresa admin123 otra vez
13. ✅ Dashboard debe cargar correctamente
14. Verifica localStorage
    ✅ "yesswera_admin_auth" debe estar de nuevo presente
```

**Resultado Esperado**: ✅ Admin logout limpia completamente

---

### TEST 2: Cambiar entre Usuarios (Portal)

**Procedimiento**:
```
1. Abre navegador → http://localhost:3000/portal/
2. Ingresa:
   - Email: juan@test.com
   - Contraseña: (cualquiera)
3. Espera 1.5 segundos
4. ✅ Redirige a http://localhost:3000/cliente/
5. Abre DevTools: F12 → Application → localStorage
6. Busca claves:
   ✅ "yesswera_session" - presente
   ✅ "yesswera_cart" - presente (puede estar vacío o con items)
   ✅ "yesswera_last_activity" - presente
7. Verifica en console:
   console.log(getUserType())
   ✅ Debe devolver: "cliente"
   console.log(JSON.parse(localStorage.yesswera_session).user.nombre)
   ✅ Debe devolver: "Juan Pérez" (o similar)
8. Busca botón "Salir" en dashboard
9. Click en "Salir"
10. ✅ Redirige a http://localhost:3000/portal/
11. Abre DevTools
12. Verifica localStorage
    ✅ "yesswera_session" DEBE ESTAR VACÍO/NO EXISTIR
    ✅ "yesswera_cart" DEBE ESTAR VACÍO/NO EXISTIR
    ✅ "yesswera_last_activity" DEBE ESTAR VACÍO/NO EXISTIR
13. Campo de email debe estar vacío
14. Campo de contraseña debe estar vacío
15. Ingresa:
    - Email: carlos@delivery.com
    - Contraseña: (cualquiera)
16. Espera 1.5 segundos
17. ✅ Redirige a http://localhost:3000/repartidor/ (NO /cliente/)
18. Abre DevTools
19. Verifica en console:
    console.log(getUserType())
    ✅ Debe devolver: "repartidor" (NO "cliente")
    console.log(JSON.parse(localStorage.yesswera_session).user.nombre)
    ✅ Debe devolver: "Carlos López" (NO "Juan Pérez")
20. Verifica localStorage
    ✅ "yesswera_cart" NO DEBE EXISTIR (es solo para cliente)
    ✅ "activeDelivery" puede existir (para repartidor)
```

**Resultado Esperado**: ✅ Login permite cambiar usuario sin problemas

---

### TEST 3: Verificar Limpieza Completa de localStorage

**Procedimiento**:
```
1. Abre navegador → http://localhost:3000/portal/
2. Abre DevTools: F12 → Application → localStorage
3. Limpia localStorage manualmente (haz click derecho → Clear All)
4. Ingresa usuario cliente: juan@test.com
5. Espera redireccionamiento a /cliente/
6. Abre DevTools y devTools de nuevo (para refrescar vista)
7. Verifica localStorage - debes ver:
   ✅ yesswera_session (con token)
   ✅ yesswera_last_activity (timestamp)
   ✅ yesswera_cart (puede estar vacío: [])
   ✅ yesswera_popups_shown ({})
   ✅ yesswera_last_popup_time (0)
8. Abre DevTools Console
9. Ejecuta:
   Object.keys(localStorage)
   ✅ Debe devolver array con ~5-6 items
10. Click "Salir"
11. Redirige a /portal/
12. Abre DevTools nuevamente
13. Verifica localStorage está COMPLETAMENTE VACÍO
    ✅ Object.keys(localStorage) debe devolver []
14. Verifica sessionStorage también
    ✅ Object.keys(sessionStorage) debe devolver []
```

**Resultado Esperado**: ✅ localStorage y sessionStorage completamente limpios

---

### TEST 4: Cambiar entre Tres Roles

**Procedimiento**:
```
1. Portal: Login como CLIENTE (juan@test.com)
   ✅ Redirige a /cliente/
   ✅ Ver carrito, órdenes, búsqueda

2. Salir → vuelve a /portal/
   ✅ localhost completamente limpio

3. Portal: Login como REPARTIDOR (carlos@delivery.com)
   ✅ Redirige a /repartidor/
   ✅ Ver entregas, earnings, vehículo
   ✅ NO hay carrito

4. Salir → vuelve a /portal/
   ✅ localStorage limpio

5. Portal: Login como NEGOCIO (maria@negocio.com)
   ✅ Redirige a /negocio/
   ✅ Ver órdenes, catálogo, ganancias
   ✅ NO hay carrito
   ✅ NO hay entregas

6. Salir → vuelve a /portal/
```

**Resultado Esperado**: ✅ Transiciones limpias entre roles

---

### TEST 5: Verificar Que Admin No Se Queda Conectado

**Procedimiento**:
```
1. Abre dos pestañas del navegador
   Tab 1: http://localhost:3000/admin/
   Tab 2: http://localhost:3000/portal/

2. En Tab 1: Login admin (admin123)
   ✅ Ver dashboard admin

3. En Tab 2: Login cliente (juan@test.com)
   ✅ Ver dashboard cliente

4. En Tab 1: Click "Salir"
   ✅ Logout admin
   ✅ Vuelve a login screen admin

5. En Tab 2: Click "Salir"
   ✅ Logout cliente
   ✅ Vuelve a portal

6. En Tab 1: Intenta login admin otra vez
   ✅ Debe aceptar admin123
   ✅ Dashboard carga correctamente

7. En Tab 2: Intenta login repartidor
   ✅ Debe ir a /repartidor/
   ✅ No debe estar mezclado con admin
```

**Resultado Esperado**: ✅ Admin y portal son sistemas independientes

---

## 🔍 Verificaciones Adicionales en DevTools

### Console Checks

**Después de login cliente**:
```javascript
// Copy & Paste en DevTools Console (F12 → Console):

// 1. Verificar token
console.log("Token:", getToken() ? "✅ Presente" : "❌ Ausente")

// 2. Verificar tipo de usuario
console.log("Tipo:", getUserType())

// 3. Verificar datos de usuario
console.log("Usuario:", getUser())

// 4. Verificar cart
console.log("Cart:", JSON.parse(localStorage.yesswera_cart || '[]'))

// 5. Verificar última actividad
console.log("Última actividad hace:",
  (Date.now() - parseInt(localStorage.yesswera_last_activity || 0)) / 1000,
  "segundos"
)

// 6. Verificar todo en localStorage
console.log("localStorage keys:", Object.keys(localStorage))
```

**Después de logout**:
```javascript
// Debe devolver:
// localStorage keys: [] (array vacío)
// Token: ❌ Ausente
// Tipo: null
```

---

## 📊 Checklist de Validación

### Admin Dashboard
- [ ] Login con admin123 funciona
- [ ] Dashboard carga correctamente
- [ ] "Salir" limpia localStorage.yesswera_admin_auth
- [ ] Campo de password se limpia
- [ ] Puedo volver a hacer login
- [ ] No hay sesión persistida

### Portal Cliente
- [ ] Login con juan@test.com funciona
- [ ] Redirige a /cliente/
- [ ] getUserType() devuelve "cliente"
- [ ] localStorage tiene yesswera_cart
- [ ] Click "Salir" limpia todo
- [ ] Puedo login como otro usuario

### Portal Repartidor
- [ ] Login con carlos@delivery.com funciona
- [ ] Redirige a /repartidor/
- [ ] getUserType() devuelve "repartidor"
- [ ] NO hay yesswera_cart (carrito cliente)
- [ ] Click "Salir" limpia todo
- [ ] Puedo login como otro usuario

### Portal Negocio
- [ ] Login con maria@negocio.com funciona
- [ ] Redirige a /negocio/
- [ ] getUserType() devuelve "negocio"
- [ ] NO hay yesswera_cart
- [ ] localStorage tiene negocio_products
- [ ] Click "Salir" limpia todo

### Limpieza General
- [ ] Después de logout, localStorage está VACÍO
- [ ] Después de logout, sessionStorage está VACÍO
- [ ] Campos de login están limpios
- [ ] No hay datos residuales

---

## 🐛 Troubleshooting

### Si logout no limpia localStorage

**Problema**: Después de logout, yesswera_session sigue ahí

**Solución**:
```javascript
// Manual cleanup en console
localStorage.clear()
sessionStorage.clear()
location.reload()
```

---

### Si admin se queda conectado

**Problema**: Logout admin no funciona

**Solución**:
```javascript
// En console del admin
localStorage.removeItem('yesswera_admin_auth')
sessionStorage.clear()
location.href = '/admin/'
```

---

### Si login no permite cambiar usuario

**Problema**: Login como usuario B pero muestra datos de usuario A

**Solución**:
1. Abre DevTools → Console
2. Ejecuta: `localStorage.clear(); sessionStorage.clear(); location.href='/portal/'`
3. Intenta login nuevamente

---

## ✅ Resultado Esperado Final

Si TODOS los tests pasan:

✅ Admin logout completo
✅ Portal logout completo
✅ Puedo cambiar entre usuarios sin problemas
✅ Cero datos residuales
✅ localStorage limpio después de logout
✅ sessionStorage limpio después de logout
✅ Seguridad mejorada

---

## 📝 Reporte de Testing

**Fecha**: ___________
**Tester**: ___________

**Resultado Admin Logout**: [ ] ✅ Pasó [ ] ❌ Falló
**Resultado Portal Logout**: [ ] ✅ Pasó [ ] ❌ Falló
**Resultado Cambio Usuarios**: [ ] ✅ Pasó [ ] ❌ Falló
**Resultado Limpieza localStorage**: [ ] ✅ Pasó [ ] ❌ Falló
**Resultado Cambio Roles**: [ ] ✅ Pasó [ ] ❌ Falló

**Notas Adicionales**:
_________________________________
_________________________________
_________________________________

---

**Si todos los tests pasan: ✅ Sistema está listo para producción**

🚀 ¡Logout/Login corregido exitosamente!
