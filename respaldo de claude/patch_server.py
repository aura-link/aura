#!/usr/bin/env python3
"""
Script to patch server_jwt.py with new endpoints
"""

import re

def patch_server(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add new file paths after PRODUCTS_FILE definition
    products_file_line = "PRODUCTS_FILE = DATA_DIR / \"products.json\"  # Products catalog"
    if products_file_line in content and "GPS_FILE" not in content:
        new_files = """PRODUCTS_FILE = DATA_DIR / "products.json"  # Products catalog
GPS_FILE = DATA_DIR / "gps.json"  # GPS tracking data
RATINGS_FILE = DATA_DIR / "ratings.json"  # Ratings data
ADDRESSES_FILE = DATA_DIR / "addresses.json"  # Saved addresses"""
        content = content.replace(products_file_line, new_files)
        print("[OK] Added new file path definitions")

    # 2. Add new handler methods before the do_GET method (find line with "def do_GET")
    do_get_pattern = r"(\s+def do_GET\(self\):)"

    new_handlers = '''
    def handle_get_user_orders(self, user_id):
        """GET /api/orders/user/:userId - Get all orders for a user"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            orders = load_json_file(ORDERS_FILE)
            if not isinstance(orders, dict):
                orders = {}
            user_orders = []
            for order_id, order in orders.items():
                if order.get('cliente_id') == user_id:
                    user_orders.append({"id": order_id, **order})
            user_orders.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            self.send_json_response({"success": True, "orders": user_orders})
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_get_order_by_id(self, order_id):
        """GET /api/orders/:orderId - Get order by ID"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            orders = load_json_file(ORDERS_FILE)
            if not isinstance(orders, dict):
                orders = {}
            order = orders.get(order_id)
            if not order:
                self.send_json_response({"error": "Order not found"}, 404)
                return
            self.send_json_response({"success": True, "order": {"id": order_id, **order}})
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_get_active_orders(self, user_id):
        """GET /api/orders/user/:userId/active - Get active orders"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            orders = load_json_file(ORDERS_FILE)
            if not isinstance(orders, dict):
                orders = {}
            active_statuses = ['pendiente', 'aceptado', 'en_camino', 'recogido']
            active_orders = []
            for order_id, order in orders.items():
                if (order.get('cliente_id') == user_id and order.get('estado') in active_statuses):
                    active_orders.append({"id": order_id, **order})
            active_orders.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            self.send_json_response({"success": True, "orders": active_orders})
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_cancel_order(self, order_id):
        """DELETE /api/orders/:orderId/cancel - Cancel order"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            user_id = payload.get('sub')
            orders = load_json_file(ORDERS_FILE)
            if not isinstance(orders, dict):
                orders = {}
            order = orders.get(order_id)
            if not order:
                self.send_json_response({"error": "Order not found"}, 404)
                return
            if order.get('cliente_id') != user_id:
                self.send_json_response({"error": "Unauthorized"}, 403)
                return
            if order.get('estado') in ['entregado', 'cancelado']:
                self.send_json_response({"error": "Cannot cancel completed order"}, 400)
                return
            order['estado'] = 'cancelado'
            order['cancelado_timestamp'] = datetime.now().isoformat()
            orders[order_id] = order
            if save_json_file(ORDERS_FILE, orders):
                log_event("order_cancelled", {"order_id": order_id, "user_id": user_id})
                self.send_json_response({"success": True, "message": "Order cancelled"})
            else:
                self.send_json_response({"error": "Failed to cancel order"}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_get_driver_location(self, order_id):
        """GET /api/gps/:orderId - Get driver location"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            gps_data = load_json_file(GPS_FILE)
            if not isinstance(gps_data, dict):
                gps_data = {}
            location = gps_data.get(order_id)
            if not location:
                self.send_json_response({
                    "latitude": 13.6929 + (hash(order_id) % 100) / 10000,
                    "longitude": -89.2182 + (hash(order_id) % 100) / 10000,
                    "timestamp": datetime.now().isoformat(),
                    "speed": 0,
                    "heading": 0
                })
                return
            self.send_json_response(location)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_create_rating(self, data):
        """POST /api/ratings - Create rating"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            user_id = payload.get('sub')
            order_id = data.get('orderId')
            driver_id = data.get('driverId')
            stars = data.get('stars')
            comment = data.get('comment', '')
            if not all([order_id, driver_id, stars]):
                self.send_json_response({"error": "Missing required fields"}, 400)
                return
            if not isinstance(stars, (int, float)) or stars < 1 or stars > 5:
                self.send_json_response({"error": "Stars must be 1-5"}, 400)
                return
            ratings = load_json_file(RATINGS_FILE)
            if not isinstance(ratings, dict):
                ratings = {}
            rating_id = str(uuid.uuid4())
            rating = {
                "id": rating_id,
                "user_id": user_id,
                "order_id": order_id,
                "driver_id": driver_id,
                "stars": stars,
                "comment": comment,
                "timestamp": datetime.now().isoformat()
            }
            ratings[rating_id] = rating
            if save_json_file(RATINGS_FILE, ratings):
                log_event("rating_created", {"rating_id": rating_id, "order_id": order_id, "stars": stars})
                self.send_json_response({"success": True, "rating_id": rating_id})
            else:
                self.send_json_response({"error": "Failed to save rating"}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_get_user_addresses(self, user_id):
        """GET /api/addresses/user/:userId - Get user addresses"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            addresses = load_json_file(ADDRESSES_FILE)
            if not isinstance(addresses, dict):
                addresses = {}
            user_addresses = []
            for addr_id, addr in addresses.items():
                if addr.get('user_id') == user_id:
                    user_addresses.append({"id": addr_id, **addr})
            self.send_json_response({"success": True, "addresses": user_addresses})
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_create_address(self, data):
        """POST /api/addresses - Create address"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            user_id = payload.get('sub')
            label = data.get('label')
            address = data.get('address')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            if not all([label, address, latitude, longitude]):
                self.send_json_response({"error": "Missing required fields"}, 400)
                return
            addresses = load_json_file(ADDRESSES_FILE)
            if not isinstance(addresses, dict):
                addresses = {}
            addr_id = str(uuid.uuid4())
            new_address = {
                "id": addr_id,
                "user_id": user_id,
                "label": label,
                "address": address,
                "latitude": latitude,
                "longitude": longitude,
                "created_at": datetime.now().isoformat()
            }
            addresses[addr_id] = new_address
            if save_json_file(ADDRESSES_FILE, addresses):
                self.send_json_response({"success": True, "address": new_address})
            else:
                self.send_json_response({"error": "Failed to save address"}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_update_address(self, addr_id, data):
        """PUT /api/addresses/:id - Update address"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            user_id = payload.get('sub')
            addresses = load_json_file(ADDRESSES_FILE)
            if not isinstance(addresses, dict):
                addresses = {}
            address = addresses.get(addr_id)
            if not address:
                self.send_json_response({"error": "Address not found"}, 404)
                return
            if address.get('user_id') != user_id:
                self.send_json_response({"error": "Unauthorized"}, 403)
                return
            if 'label' in data:
                address['label'] = data['label']
            if 'address' in data:
                address['address'] = data['address']
            if 'latitude' in data:
                address['latitude'] = data['latitude']
            if 'longitude' in data:
                address['longitude'] = data['longitude']
            address['updated_at'] = datetime.now().isoformat()
            addresses[addr_id] = address
            if save_json_file(ADDRESSES_FILE, addresses):
                self.send_json_response({"success": True, "address": address})
            else:
                self.send_json_response({"error": "Failed to update address"}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_delete_address(self, addr_id):
        """DELETE /api/addresses/:id - Delete address"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)
            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return
            user_id = payload.get('sub')
            addresses = load_json_file(ADDRESSES_FILE)
            if not isinstance(addresses, dict):
                addresses = {}
            address = addresses.get(addr_id)
            if not address:
                self.send_json_response({"error": "Address not found"}, 404)
                return
            if address.get('user_id') != user_id:
                self.send_json_response({"error": "Unauthorized"}, 403)
                return
            del addresses[addr_id]
            if save_json_file(ADDRESSES_FILE, addresses):
                self.send_json_response({"success": True, "message": "Address deleted"})
            else:
                self.send_json_response({"error": "Failed to delete address"}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

'''

    if "def handle_get_user_orders" not in content:
        content = re.sub(do_get_pattern, new_handlers + r'\n\1', content)
        print("[OK] Added new handler methods")

    # 3. Add new routes to do_GET before the catch-all
    catchall_pattern = r'(\s+elif path\.startswith\("/api/"\):[\s\S]*?# Catch-all for unknown API endpoints)'

    new_get_routes = '''        # Orders endpoints
        elif path.startswith("/api/orders/user/") and path.endswith("/active"):
            user_id = path.split("/api/orders/user/")[1].split("/active")[0]
            self.handle_get_active_orders(user_id)
        elif path.startswith("/api/orders/user/"):
            user_id = path.split("/api/orders/user/")[1]
            self.handle_get_user_orders(user_id)
        elif path.startswith("/api/orders/"):
            order_id = path.split("/api/orders/")[1]
            self.handle_get_order_by_id(order_id)
        # GPS endpoint
        elif path.startswith("/api/gps/"):
            order_id = path.split("/api/gps/")[1]
            self.handle_get_driver_location(order_id)
        # Addresses endpoint
        elif path.startswith("/api/addresses/user/"):
            user_id = path.split("/api/addresses/user/")[1]
            self.handle_get_user_addresses(user_id)
        '''

    if '"/api/orders/user/"' not in content:
        content = re.sub(catchall_pattern, new_get_routes + r'\1', content)
        print("[OK] Added GET routes")

    # 4. Add new routes to do_POST before the else
    post_else_pattern = r'(\s+elif path == "/api/password-recovery/reset":[\s\S]*?self\.handle_password_recovery_reset\(data\))\s+(else:)'

    new_post_routes = '''        elif path == "/api/orders":
            self.handle_create_order(data)
        elif path == "/api/ratings":
            self.handle_create_rating(data)
        elif path == "/api/addresses":
            self.handle_create_address(data)
        '''

    if '"/api/ratings"' not in content:
        content = re.sub(post_else_pattern, r'\1\n' + new_post_routes + r'\2', content)
        print("[OK] Added POST routes")

    # 5. Add do_PUT method after do_POST
    do_post_end_pattern = r'(    def do_POST\(self\):[\s\S]*?else:\s+self\.send_error\(404\))'

    new_put_method = '''

    def do_PUT(self):
        """Handle PUT requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8', errors='ignore')
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}
        if path.startswith("/api/addresses/"):
            addr_id = path.split("/api/addresses/")[1]
            self.handle_update_address(addr_id, data)
        else:
            self.send_error(404)

    def do_DELETE(self):
        """Handle DELETE requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        if path.startswith("/api/orders/") and path.endswith("/cancel"):
            order_id = path.split("/api/orders/")[1].split("/cancel")[0]
            self.handle_cancel_order(order_id)
        elif path.startswith("/api/addresses/"):
            addr_id = path.split("/api/addresses/")[1]
            self.handle_delete_address(addr_id)
        else:
            self.send_error(404)
'''

    if "def do_PUT" not in content:
        content = re.sub(do_post_end_pattern, r'\1' + new_put_method, content)
        print("[OK] Added PUT and DELETE methods")

    # Write patched content
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\n[OK] Server patched successfully! Output: {output_file}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python patch_server.py <input_file> <output_file>")
        sys.exit(1)

    patch_server(sys.argv[1], sys.argv[2])
