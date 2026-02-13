import re

with open("/home/yesswera/YessweraWeb/server_jwt.py", "r") as f:
    content = f.read()

# Find position to add the new route - after the /business-validate route
route_marker = '''elif path.startswith("/api/orders/") and path.endswith("/business-validate"):
            # POST /api/orders/:orderId/business-validate - Negocio valida codigo del repartidor
            order_id = path.split("/")[3]
            self.handle_business_validate_driver(order_id, data)'''

new_route = '''elif path.startswith("/api/orders/") and path.endswith("/business-validate"):
            # POST /api/orders/:orderId/business-validate - Negocio valida codigo del repartidor
            order_id = path.split("/")[3]
            self.handle_business_validate_driver(order_id, data)
        elif path.startswith("/api/orders/") and path.endswith("/confirm-pickup"):
            # POST /api/orders/:orderId/confirm-pickup - Repartidor confirma recogida
            order_id = path.split("/")[3]
            self.handle_confirm_pickup(order_id)'''

content = content.replace(route_marker, new_route)

# Now add the handler function - find handle_business_validate_driver and add after it
handler_func = '''
    def handle_confirm_pickup(self, order_id):
        """POST /api/orders/:orderId/confirm-pickup - Repartidor confirma recogida sin codigo"""
        try:
            token = self.headers.get("Authorization", "").replace("Bearer ", "")
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid token"}, 401)
                return

            driver_id = payload.get("sub")

            orders = load_json_file(ORDERS_FILE)
            if order_id not in orders:
                self.send_json_response({"error": "Order not found"}, 404)
                return

            order = orders[order_id]

            # Verify the driver owns this order
            if order.get('driverId') != driver_id:
                self.send_json_response({"error": "No autorizado"}, 403)
                return

            # Verify order was verified by business
            if order.get('status') != 'driver_verified':
                self.send_json_response({"error": "El negocio debe verificar tu codigo primero"}, 400)
                return

            # Update order status
            order['status'] = 'in_transit'
            order['estado'] = 'en_camino'
            order['pickedUpAt'] = datetime.now().isoformat()
            order['pickupValidation'] = {
                'validated': True,
                'validatedAt': datetime.now().isoformat(),
                'validatedBy': driver_id
            }

            orders[order_id] = order
            if save_json_file(ORDERS_FILE, orders):
                self.send_json_response({
                    "success": True,
                    "message": "Orden recogida, ahora ve a entregar",
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

print("Confirm pickup endpoint added successfully")
