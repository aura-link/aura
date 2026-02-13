with open("/home/yesswera/YessweraWeb/server_jwt.py", "r") as f:
    content = f.read()

# Add business-validate and confirm-pickup routes after /take route
old_take_route = '''elif path.startswith("/api/orders/") and path.endswith("/take"):
            # POST /api/orders/:orderId/take - Driver takes an order
            order_id = path.split("/")[-2]
            self.handle_driver_take_order(order_id, data)
        elif path == "/api/products":'''

new_routes = '''elif path.startswith("/api/orders/") and path.endswith("/take"):
            # POST /api/orders/:orderId/take - Driver takes an order
            order_id = path.split("/")[-2]
            self.handle_driver_take_order(order_id, data)
        elif path.startswith("/api/orders/") and path.endswith("/business-validate"):
            # POST /api/orders/:orderId/business-validate - Negocio valida codigo del repartidor
            order_id = path.split("/")[-2]
            self.handle_business_validate_driver(order_id, data)
        elif path.startswith("/api/orders/") and path.endswith("/confirm-pickup"):
            # POST /api/orders/:orderId/confirm-pickup - Repartidor confirma recogida
            order_id = path.split("/")[-2]
            self.handle_confirm_pickup(order_id)
        elif path == "/api/products":'''

content = content.replace(old_take_route, new_routes)

with open("/home/yesswera/YessweraWeb/server_jwt.py", "w") as f:
    f.write(content)

print("Rutas agregadas correctamente")
