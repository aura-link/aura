# Guía Rápida - Registro de Usuarios Yesswera

## URL del API
```
https://api.yesswera.com/api/register
```

## Método
```
POST
```

## Headers
```
Content-Type: application/json
```

---

## Registrar CLIENTE

```bash
curl -X POST https://api.yesswera.com/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "tipo": "cliente",
    "email": "cliente@ejemplo.com",
    "nombre": "Nombre del Cliente",
    "password": "contraseña123",
    "telefono": "3001234567",
    "direccion": "Calle 123 #45-67, Ciudad"
  }'
```

---

## Registrar REPARTIDOR

```bash
curl -X POST https://api.yesswera.com/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "tipo": "repartidor",
    "email": "repartidor@ejemplo.com",
    "nombre": "Nombre del Repartidor",
    "password": "contraseña123",
    "telefono": "3009876543",
    "transporte": "moto",
    "placa": "ABC123"
  }'
```

---

## Registrar NEGOCIO

```bash
curl -X POST https://api.yesswera.com/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "tipo": "negocio",
    "email": "negocio@ejemplo.com",
    "nombre": "Nombre del Propietario",
    "password": "contraseña123",
    "telefono": "3005556666",
    "negocio_nombre": "Nombre del Restaurante",
    "direccion": "Avenida Principal #100"
  }'
```

---

## Campos Obligatorios

| Campo | Descripción |
|-------|-------------|
| `tipo` | `cliente`, `negocio`, o `repartidor` |
| `email` | Email único |
| `nombre` | Nombre completo |

## Campos Opcionales

| Campo | Descripción |
|-------|-------------|
| `password` | Si no se envía, usa "default123" |
| `telefono` | Número de contacto |
| `direccion` | Dirección física |

## Campos Específicos

### Solo para Repartidor:
- `transporte`: Tipo de vehículo (moto, bicicleta, carro)
- `placa`: Placa del vehículo

### Solo para Negocio:
- `negocio_nombre`: Nombre comercial del negocio

---

## Respuesta Exitosa (201)

```json
{
  "success": true,
  "message": "User registered successfully",
  "user": {
    "id": "uuid-generado",
    "tipo": "cliente",
    "nombre": "Nombre",
    "email": "email@ejemplo.com"
  }
}
```

## Errores Comunes

### 400 - Campos faltantes
```json
{"error": "Missing required fields"}
```
**Solución:** Verificar que `tipo`, `email` y `nombre` estén presentes.

### 400 - Usuario existe
```json
{"error": "User already exists"}
```
**Solución:** Usar otro email.

### 429 - Rate limit
```json
{"error": "Too many registration attempts. Please try again later."}
```
**Solución:** Esperar unos minutos.

---

## Verificar Registro (Login)

```bash
curl -X POST https://api.yesswera.com/api/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "cliente@ejemplo.com",
    "password": "contraseña123"
  }'
```
