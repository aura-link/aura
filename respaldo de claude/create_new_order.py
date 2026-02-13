import json
import uuid
from datetime import datetime
import random
import string

def generate_code(length):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

with open("/home/yesswera/YessweraWeb/data/orders.json", "r") as f:
    orders = json.load(f)

# Generate unique codes
driver_code = generate_code(4)
comanda_code = generate_code(4)
delivery_code = generate_code(5)

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
    "customerId": "cliente-test-456",
    "customerName": "Maria Lopez",
    "customerPhone": "3229876543",
    "businessId": "3c246c92-17ba-49fb-b0ac-81ac5ba9e2a8",
    "businessName": "Tienda Central",
    "pickupAddress": "Calle Insurgentes 789, Centro, Puerto Vallarta",
    "pickupLocation": {"latitude": 20.6550, "longitude": -105.2280},
    "deliveryAddress": "Av. Fluvial 321, Fluvial Vallarta",
    "deliveryLocation": {"latitude": 20.6620, "longitude": -105.2350},
    "items": [
        {"id": "item1", "name": "Tacos al Pastor", "price": 85.00, "quantity": 3},
        {"id": "item2", "name": "Agua de Jamaica", "price": 30.00, "quantity": 2}
    ],
    "subtotal": 315.00,
    "deliveryFee": 40.00,
    "total": 355.00,
    "driverCode": driver_code,
    "comandaCode": comanda_code,
    "deliveryCode": delivery_code,
    "createdAt": datetime.now().isoformat(),
    "estimatedTime": 20
}

orders[order_id] = new_order

with open("/home/yesswera/YessweraWeb/data/orders.json", "w") as f:
    json.dump(orders, f, indent=2)

print(f"=== NUEVA ORDEN CREADA ===")
print(f"ID: {order_id}")
print(f"Negocio: Tienda Central")
print(f"Total: $355.00 MXN")
print(f"")
print(f"=== CÓDIGOS (guárdalos) ===")
print(f"Driver Code (repartidor): {driver_code}")
print(f"Comanda Code (negocio): {comanda_code}")
print(f"Delivery Code (cliente): {delivery_code}")
