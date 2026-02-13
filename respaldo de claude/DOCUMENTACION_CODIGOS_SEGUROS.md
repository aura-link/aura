# Sistema de Códigos Seguros - Yesswera

## Fecha: 22 Enero 2026

## Resumen del Sistema

Sistema de verificación con 3 códigos para asegurar entregas:

| Código | Longitud | Quién lo usa | Para qué |
|--------|----------|--------------|----------|
| driverCode | 4 chars | Repartidor → Negocio | Verificar identidad del repartidor |
| comandaCode | 4 chars | Negocio (interno) | Identificar la comanda física |
| deliveryCode | 5 chars | Cliente → Repartidor | Verificar entrega correcta |

## Flujo Completo

1. **Cliente hace pedido** → Se generan los 3 códigos
2. **Negocio acepta** → Status: `confirmed`
3. **Repartidor acepta** → Status: `assigned`
4. **Repartidor llega al negocio** → Muestra su `driverCode` (4 chars)
5. **Negocio valida código** → Status: `driver_verified`, ve `comandaCode`
6. **Repartidor confirma recogida** → Status: `in_transit`
7. **Repartidor llega al cliente** → Pide `deliveryCode` (5 chars)
8. **Repartidor valida código** → Status: `delivered`

---

## Cambios en Backend (server_jwt.py)

### 1. Función generate_order_codes() - Línea ~152

```python
def generate_order_codes():
    """Generate verification codes for secure order flow

    Returns:
        Tuple of (driver_code, comanda_code, delivery_code)
        - driver_code: 4 chars - Repartidor dice este codigo al negocio
        - comanda_code: 4 chars - Identificador de comanda/pedido fisico en negocio
        - delivery_code: 5 chars - Cliente dice este codigo al repartidor
    """
    driver_code = generate_verification_code(4)
    comanda_code = generate_verification_code(4)
    delivery_code = generate_verification_code(5)

    # Ensure all codes are different
    codes = [driver_code, comanda_code, delivery_code]
    while len(codes) != len(set(codes)):
        driver_code = generate_verification_code(4)
        comanda_code = generate_verification_code(4)
        delivery_code = generate_verification_code(5)
        codes = [driver_code, comanda_code, delivery_code]

    return driver_code, comanda_code, delivery_code
```

### 2. Creación de orden usa 3 códigos - Línea ~4277

```python
driver_code, comanda_code, delivery_code = generate_order_codes()
# ...
"driverCode": driver_code,
"comandaCode": comanda_code,
"deliveryCode": delivery_code,
```

### 3. Nuevo Endpoint: POST /api/orders/:orderId/business-validate

Permite al negocio validar el código del repartidor.

```python
def handle_business_validate_driver(self, order_id, data):
    # Valida driverCode
    # Cambia status a 'driver_verified'
    # Retorna comandaCode al negocio
```

### 4. Nuevo Endpoint: POST /api/orders/:orderId/confirm-pickup

Permite al repartidor confirmar recogida después de ser validado.

```python
def handle_confirm_pickup(self, order_id):
    # Verifica que status sea 'driver_verified'
    # Cambia status a 'in_transit'
```

### 5. Active statuses incluye driver_verified

```python
active_statuses = [
    'pending', 'confirmed', 'preparing', 'ready', 'accepted',
    'assigned', 'driver_verified', 'in_transit', 'picked_up',
    ...
]
```

---

## Cambios en App Mobile

### 1. app/business/orders.tsx (COMPLETO)

- Modal para validar código del repartidor
- Input de 4 caracteres
- Llama a `/api/orders/:orderId/business-validate`
- Muestra comandaCode después de validar

### 2. app/driver/active-order.tsx (COMPLETO)

- Muestra driverCode prominente (4 chars) cuando status es assigned
- Botón "Confirmar Recogida" después de ser validado
- Input para deliveryCode (5 chars) al entregar
- Lógica de estados actualizada

### 3. app/orders/[orderId].tsx (COMPLETO)

- Muestra deliveryCode prominente cuando orden está en camino
- Sección visual destacada con instrucciones

### 4. app/driver/dashboard.tsx

- URL corregida: `/orders/${orderId}/take`

---

## Archivos Modificados en Servidor

```
/home/yesswera/YessweraWeb/server_jwt.py
/home/yesswera/yesswera-app-mobile/app/business/orders.tsx
/home/yesswera/yesswera-app-mobile/app/driver/active-order.tsx
/home/yesswera/yesswera-app-mobile/app/driver/dashboard.tsx
/home/yesswera/yesswera-app-mobile/app/orders/[orderId].tsx
```

---

## Problema Pendiente

El código del repartidor (driverCode) no se muestra en la pantalla active-order.tsx aunque:
- El archivo está actualizado correctamente
- La lógica es correcta (canShowDriverCode && driverCode)
- El orden tiene driverCode en la base de datos

**Posibles causas:**
1. Cache de Metro bundler
2. El componente no está recibiendo el driverCode del API
3. Necesita debug con console.log para ver qué datos llegan

**Para investigar:**
- Agregar console.log en active-order.tsx para ver `order` y `driverCode`
- Verificar que getActiveOrders retorna el campo driverCode
- Limpiar cache: `npx expo start --clear`

---

## Comandos Útiles

```bash
# Reiniciar servidor
ssh yesswera@10.147.17.16 "cd /home/yesswera/YessweraWeb && pkill -f server_jwt; nohup python3 server_jwt.py > server.log 2>&1 &"

# Ver logs del servidor
ssh yesswera@10.147.17.16 "tail -50 /home/yesswera/YessweraWeb/server.log"

# Crear orden de prueba
ssh yesswera@10.147.17.16 "python3 /home/yesswera/create_new_order.py"

# Limpiar cache Expo
npx expo start --clear
```

---

## Conexión

- **Servidor:** 10.147.17.16 (ZeroTier)
- **Usuario:** yesswera
- **Puerto API:** 3000 (HTTPS)
