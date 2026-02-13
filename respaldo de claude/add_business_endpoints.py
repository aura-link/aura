#!/usr/bin/env python3
"""Add business order endpoints to server_jwt.py"""

with open("/home/yesswera/YessweraWeb/server_jwt.py", "r") as f:
    content = f.read()

# 1. Add GET /api/orders/business/:businessId route (before /api/orders/:orderId catch-all)
old_get_route = '''elif path == "/api/orders/available":
                # GET /api/orders/available
                self.handle_get_available_orders()
            elif path.startswith("/api/orders/"):
                # GET /api/orders/:orderId'''

new_get_route = '''elif path == "/api/orders/available":
                # GET /api/orders/available
                self.handle_get_available_orders()
            elif path.startswith("/api/orders/business/"):
                # GET /api/orders/business/:businessId
                business_id = path.split("/")[-1]
                self.handle_get_business_orders(business_id)
            elif path.startswith("/api/orders/"):
                # GET /api/orders/:orderId'''

content = content.replace(old_get_route, new_get_route)

# 2. Add POST routes for validate-driver-code and confirm-handover
old_post_route = '''elif path.startswith("/api/orders/") and path.endswith("/confirm-pickup"):
            # POST /api/orders/:orderId/confirm-pickup - Repartidor confirma recogida
            order_id = path.split("/")[-2]
            self.handle_confirm_pickup(order_id)
        elif path == "/api/products":'''

new_post_route = '''elif path.startswith("/api/orders/") and path.endswith("/confirm-pickup"):
            # POST /api/orders/:orderId/confirm-pickup - Repartidor confirma recogida
            order_id = path.split("/")[-2]
            self.handle_confirm_pickup(order_id)
        elif path == "/api/orders/validate-driver-code":
            # POST /api/orders/validate-driver-code - Negocio valida codigo de cualquier repartidor
            self.handle_validate_driver_code_global(data)
        elif path.startswith("/api/orders/") and path.endswith("/confirm-handover"):
            # POST /api/orders/:orderId/confirm-handover - Negocio confirma entrega al repartidor
            order_id = path.split("/")[-2]
            self.handle_confirm_handover(order_id)
        elif path == "/api/products":'''

content = content.replace(old_post_route, new_post_route)

# 3. Add the handler functions after handle_confirm_pickup
old_handler = '''    def handle_validate_pickup(self, order_id, data):
        """POST /api/orders/:orderId/validate-pickup - Validate pickup code"""'''

new_handlers = '''    def handle_get_business_orders(self, business_id):
        """GET /api/orders/business/:businessId - Get all orders for a business"""
        try:
            token = self.headers.get("Authorization", "").replace("Bearer ", "")
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid token"}, 401)
                return

            orders = load_json_file(ORDERS_FILE)
            business_orders = []

            for order_id, order in orders.items():
                if order.get('businessId') == business_id:
                    order['id'] = order_id
                    business_orders.append(order)

            # Sort by creation date (newest first)
            business_orders.sort(key=lambda x: x.get('createdAt', ''), reverse=True)

            self.send_json_response({"orders": business_orders})
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_validate_driver_code_global(self, data):
        """POST /api/orders/validate-driver-code - Negocio valida codigo de cualquier repartidor"""
        try:
            token = self.headers.get("Authorization", "").replace("Bearer ", "")
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid token"}, 401)
                return

            driver_code = data.get('driverCode', '').upper()
            business_id = data.get('businessId', '')

            if not driver_code:
                self.send_json_response({"error": "Driver code required"}, 400)
                return

            orders = load_json_file(ORDERS_FILE)
            matching_order = None
            matching_order_id = None

            # Search for order with this driver code belonging to this business
            for order_id, order in orders.items():
                if (order.get('driverCode', '').upper() == driver_code and
                    order.get('businessId') == business_id and
                    order.get('status') in ['assigned', 'accepted', 'ready', 'driver_verified']):
                    matching_order = order
                    matching_order_id = order_id
                    break

            if not matching_order:
                self.send_json_response({
                    "success": False,
                    "error": "Codigo no encontrado o no corresponde a una orden activa"
                }, 404)
                return

            # Add order ID to response
            matching_order['id'] = matching_order_id

            self.send_json_response({
                "success": True,
                "message": "Codigo validado correctamente",
                "order": matching_order
            })
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_confirm_handover(self, order_id):
        """POST /api/orders/:orderId/confirm-handover - Negocio confirma entrega al repartidor"""
        try:
            token = self.headers.get("Authorization", "").replace("Bearer ", "")
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid token"}, 401)
                return

            orders = load_json_file(ORDERS_FILE)
            if order_id not in orders:
                self.send_json_response({"error": "Order not found"}, 404)
                return

            order = orders[order_id]

            # Update order status - business has handed over to driver
            order['status'] = 'handed_to_driver'
            order['estado'] = 'entregado_a_repartidor'
            order['handedToDriverAt'] = datetime.now().isoformat()
            order['businessHandover'] = {
                'confirmed': True,
                'confirmedAt': datetime.now().isoformat(),
                'confirmedBy': payload.get('sub')
            }

            orders[order_id] = order
            if save_json_file(ORDERS_FILE, orders):
                # TODO: Send push notification to driver that order is ready for pickup
                self.send_json_response({
                    "success": True,
                    "message": "Entrega confirmada al repartidor",
                    "order": order
                })
            else:
                self.send_json_response({"error": "Failed to update order"}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_validate_pickup(self, order_id, data):
        """POST /api/orders/:orderId/validate-pickup - Validate pickup code"""'''

content = content.replace(old_handler, new_handlers)

with open("/home/yesswera/YessweraWeb/server_jwt.py", "w") as f:
    f.write(content)

print("Business endpoints added successfully!")
print("Added:")
print("  - GET /api/orders/business/:businessId")
print("  - POST /api/orders/validate-driver-code")
print("  - POST /api/orders/:orderId/confirm-handover")
