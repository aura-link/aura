import re

with open("/home/yesswera/YessweraWeb/server_jwt.py", "r") as f:
    content = f.read()

# Find position to add the new route - after the /accept route
route_marker = '''elif path.startswith("/api/orders/") and path.endswith("/accept"):
            # POST /api/orders/:orderId/accept
            order_id = path.split("/")[3]
            self.handle_order_accept(order_id, data)'''

new_route = '''elif path.startswith("/api/orders/") and path.endswith("/accept"):
            # POST /api/orders/:orderId/accept
            order_id = path.split("/")[3]
            self.handle_order_accept(order_id, data)
        elif path.startswith("/api/orders/") and path.endswith("/business-validate"):
            # POST /api/orders/:orderId/business-validate - Negocio valida codigo del repartidor
            order_id = path.split("/")[3]
            self.handle_business_validate_driver(order_id, data)'''

content = content.replace(route_marker, new_route)

# Now add the handler function - find handle_validate_pickup and add before it
handler_func = '''
    def handle_business_validate_driver(self, order_id, data):
        """POST /api/orders/:orderId/business-validate - Negocio valida codigo del repartidor"""
        try:
            token = self.headers.get("Authorization", "").replace("Bearer ", "")
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid token"}, 401)
                return

            driver_code = data.get('driverCode', '').upper()
            if not driver_code:
                self.send_json_response({"error": "Driver code required"}, 400)
                return

            orders = load_json_file(ORDERS_FILE)
            if order_id not in orders:
                self.send_json_response({"error": "Order not found"}, 404)
                return

            order = orders[order_id]

            # Verify the driver code matches
            if order.get('driverCode', '').upper() != driver_code:
                self.send_json_response({"error": "Codigo de repartidor incorrecto"}, 400)
                return

            # Update order status - driver is verified, business can hand over order
            order['status'] = 'driver_verified'
            order['estado'] = 'repartidor_verificado'
            order['driverVerifiedAt'] = datetime.now().isoformat()

            orders[order_id] = order
            if save_json_file(ORDERS_FILE, orders):
                self.send_json_response({
                    "success": True,
                    "message": "Repartidor verificado correctamente",
                    "comandaCode": order.get('comandaCode', ''),
                    "order": order
                })
            else:
                self.send_json_response({"error": "Failed to update order"}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

'''

# Find the handle_validate_pickup function and add before it
pickup_marker = "def handle_validate_pickup(self, order_id, data):"
content = content.replace(pickup_marker, handler_func + "    " + pickup_marker)

with open("/home/yesswera/YessweraWeb/server_jwt.py", "w") as f:
    f.write(content)

print("Business validate endpoint added successfully")
