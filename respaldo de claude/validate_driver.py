import json
from datetime import datetime

with open("/home/yesswera/YessweraWeb/data/orders.json", "r") as f:
    orders = json.load(f)

order_id = "dc4c02b3-8aba-4ce9-94bb-94acaa26b030"

if order_id in orders:
    order = orders[order_id]
    order['status'] = 'driver_verified'
    order['estado'] = 'repartidor_verificado'
    order['driverVerifiedAt'] = datetime.now().isoformat()
    orders[order_id] = order

    with open("/home/yesswera/YessweraWeb/data/orders.json", "w") as f:
        json.dump(orders, f, indent=2)

    print(f"Negocio validó tu código 84XP")
    print(f"Status: driver_verified")
    print(f"Código comanda para el negocio: {order.get('comandaCode', 'N/A')}")
else:
    print("Orden no encontrada")
