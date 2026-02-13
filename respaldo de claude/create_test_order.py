import json
import uuid
from datetime import datetime
import random
import string

def generate_code(length):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# Load orders
with open("/home/yesswera/YessweraWeb/data/orders.json", "r") as f:
    orders = json.load(f)

# Generate codes
driver_code = generate_code(4)
comanda_code = generate_code(4)
delivery_code = generate_code(5)

# Ensure unique
while driver_code == comanda_code or driver_code == delivery_code or comanda_code == delivery_code:
    driver_code = generate_code(4)
    comanda_code = generate_code(4)
    delivery_code = generate_code(5)

order_id = str(uuid.uuid4())

new_order = {
    "id": order_id,
    "orderNumber": f"ORD-{order_id[:8].upper()}",
    "type": "food",
    "status": "confirmed",
    "estado": "confirmada",
    "customerId": "cliente-test-123",
    "customerName": "Cliente Prueba",
    "customerPhone": "3221234567",
    "businessId": "3c246c92-17ba-49fb-b0ac-81ac5ba9e2a8",
    "businessName": "Tienda Central",
    "pickupAddress": "Av. Mexico 123, Centro, Puerto Vallarta",
    "pickupLocation": {"latitude": 20.6534, "longitude": -105.2253},
    "deliveryAddress": "Calle Hidalgo 456, Zona Romantica, Puerto Vallarta",
    "deliveryLocation": {"latitude": 20.6580, "longitude": -105.2300},
    "items": [
        {"id": "item1", "name": "Hamburguesa Especial", "price": 120.00, "quantity": 2},
        {"id": "item2", "name": "Papas Fritas", "price": 45.00, "quantity": 1},
        {"id": "item3", "name": "Refresco", "price": 25.00, "quantity": 2}
    ],
    "subtotal": 335.00,
    "deliveryFee": 35.00,
    "total": 370.00,
    "driverCode": driver_code,
    "comandaCode": comanda_code,
    "deliveryCode": delivery_code,
    "createdAt": datetime.now().isoformat(),
    "estimatedTime": 25
}

orders[order_id] = new_order

with open("/home/yesswera/YessweraWeb/data/orders.json", "w") as f:
    json.dump(orders, f, indent=2)

print(f"Orden creada: {order_id}")
print(f"Driver Code: {driver_code}")
print(f"Comanda Code: {comanda_code}")
print(f"Delivery Code: {delivery_code}")
print(f"Status: confirmed (lista para repartidor)")
