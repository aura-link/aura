import re

with open("/home/yesswera/YessweraWeb/server_jwt.py", "r") as f:
    content = f.read()

# 1. Update the line that calls generate_order_codes to receive 3 values
old_call = "pickup_code, delivery_code = generate_order_codes()"
new_call = "driver_code, comanda_code, delivery_code = generate_order_codes()"
content = content.replace(old_call, new_call)

# 2. Update the order object to store the new codes
old_codes = '''"pickupCode": pickup_code,     # Business shows to driver
                "deliveryCode": delivery_code,  # Customer shows to driver'''

new_codes = '''"driverCode": driver_code,       # Repartidor dice al negocio
                "comandaCode": comanda_code,     # ID comanda interna del negocio
                "deliveryCode": delivery_code,   # Cliente dice al repartidor'''

content = content.replace(old_codes, new_codes)

# 3. Also update any 'pickupCode' reference in validation to 'driverCode'
content = content.replace("order.get('pickupCode'", "order.get('driverCode'")
content = content.replace("data.get('pickupCode'", "data.get('driverCode'")
content = content.replace("'pickupCode':", "'driverCode':")

with open("/home/yesswera/YessweraWeb/server_jwt.py", "w") as f:
    f.write(content)

print("Order codes updated successfully")
