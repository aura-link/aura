# NEW ENDPOINTS TO ADD TO server_jwt.py

# Add these file paths at the top with other DATA_DIR definitions (around line 40):
# GPS_FILE = DATA_DIR / "gps.json"
# RATINGS_FILE = DATA_DIR / "ratings.json"
# ADDRESSES_FILE = DATA_DIR / "addresses.json"

# ===========================================
# HANDLER METHODS (Add after handle_create_delivery, around line 1520)
# ===========================================

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

            # Filter orders by user ID
            user_orders = []
            for order_id, order in orders.items():
                if order.get('cliente_id') == user_id:
                    user_orders.append({
                        "id": order_id,
                        **order
                    })

            # Sort by timestamp (newest first)
            user_orders.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            self.send_json_response({
                "success": True,
                "orders": user_orders
            })
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

            self.send_json_response({
                "success": True,
                "order": {
                    "id": order_id,
                    **order
                }
            })
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_get_active_orders(self, user_id):
        """GET /api/orders/user/:userId/active - Get active orders for a user"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)

            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return

            orders = load_json_file(ORDERS_FILE)
            if not isinstance(orders, dict):
                orders = {}

            # Filter active orders (not delivered or cancelled)
            active_statuses = ['pendiente', 'aceptado', 'en_camino', 'recogido']
            active_orders = []

            for order_id, order in orders.items():
                if (order.get('cliente_id') == user_id and
                    order.get('estado') in active_statuses):
                    active_orders.append({
                        "id": order_id,
                        **order
                    })

            # Sort by timestamp (newest first)
            active_orders.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

            self.send_json_response({
                "success": True,
                "orders": active_orders
            })
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_cancel_order(self, order_id):
        """DELETE /api/orders/:orderId/cancel - Cancel an order"""
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

            # Verify user owns this order
            if order.get('cliente_id') != user_id:
                self.send_json_response({"error": "Unauthorized"}, 403)
                return

            # Check if order can be cancelled
            if order.get('estado') in ['entregado', 'cancelado']:
                self.send_json_response({"error": "Cannot cancel completed or cancelled order"}, 400)
                return

            # Update order status
            order['estado'] = 'cancelado'
            order['cancelado_timestamp'] = datetime.now().isoformat()
            orders[order_id] = order

            if save_json_file(ORDERS_FILE, orders):
                log_event("order_cancelled", {
                    "order_id": order_id,
                    "user_id": user_id
                })

                self.send_json_response({
                    "success": True,
                    "message": "Order cancelled successfully"
                })
            else:
                self.send_json_response({"error": "Failed to cancel order"}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_get_driver_location(self, order_id):
        """GET /api/gps/:orderId - Get driver GPS location for an order"""
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
                # Return mock data if no GPS data exists (for testing)
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
        """POST /api/ratings - Create rating for driver"""
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
                self.send_json_response({"error": "Stars must be between 1 and 5"}, 400)
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
                log_event("rating_created", {
                    "rating_id": rating_id,
                    "order_id": order_id,
                    "stars": stars
                })

                self.send_json_response({
                    "success": True,
                    "rating_id": rating_id,
                    "message": "Rating created successfully"
                })
            else:
                self.send_json_response({"error": "Failed to save rating"}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_get_user_addresses(self, user_id):
        """GET /api/addresses/user/:userId - Get all addresses for a user"""
        try:
            token = self.headers.get('Authorization', '').replace('Bearer ', '')
            payload = validate_token(token)

            if not payload:
                self.send_json_response({"error": "Invalid or expired token"}, 401)
                return

            addresses = load_json_file(ADDRESSES_FILE)
            if not isinstance(addresses, dict):
                addresses = {}

            # Filter addresses by user ID
            user_addresses = []
            for addr_id, addr in addresses.items():
                if addr.get('user_id') == user_id:
                    user_addresses.append({
                        "id": addr_id,
                        **addr
                    })

            self.send_json_response({
                "success": True,
                "addresses": user_addresses
            })
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

    def handle_create_address(self, data):
        """POST /api/addresses - Create new address"""
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
                self.send_json_response({
                    "success": True,
                    "address": new_address
                })
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

            # Verify user owns this address
            if address.get('user_id') != user_id:
                self.send_json_response({"error": "Unauthorized"}, 403)
                return

            # Update fields
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
                self.send_json_response({
                    "success": True,
                    "address": address
                })
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

            # Verify user owns this address
            if address.get('user_id') != user_id:
                self.send_json_response({"error": "Unauthorized"}, 403)
                return

            # Delete address
            del addresses[addr_id]

            if save_json_file(ADDRESSES_FILE, addresses):
                self.send_json_response({
                    "success": True,
                    "message": "Address deleted successfully"
                })
            else:
                self.send_json_response({"error": "Failed to delete address"}, 500)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 500)

# ===========================================
# ROUTING UPDATES
# ===========================================

# In do_GET method (around line 677), ADD these routes BEFORE the catch-all "/api/" check:
#
#         # Orders endpoints
#         elif path.startswith("/api/orders/user/") and path.endswith("/active"):
#             # GET /api/orders/user/:userId/active
#             user_id = path.split("/api/orders/user/")[1].split("/active")[0]
#             self.handle_get_active_orders(user_id)
#         elif path.startswith("/api/orders/user/"):
#             # GET /api/orders/user/:userId
#             user_id = path.split("/api/orders/user/")[1]
#             self.handle_get_user_orders(user_id)
#         elif path.startswith("/api/orders/"):
#             # GET /api/orders/:orderId
#             order_id = path.split("/api/orders/")[1]
#             self.handle_get_order_by_id(order_id)
#         # GPS endpoint
#         elif path.startswith("/api/gps/"):
#             # GET /api/gps/:orderId
#             order_id = path.split("/api/gps/")[1]
#             self.handle_get_driver_location(order_id)
#         # Addresses endpoints
#         elif path.startswith("/api/addresses/user/"):
#             # GET /api/addresses/user/:userId
#             user_id = path.split("/api/addresses/user/")[1]
#             self.handle_get_user_addresses(user_id)

# In do_POST method (around line 737), ADD these routes BEFORE the else/404:
#
#         elif path == "/api/orders":
#             # POST /api/orders (alias for /api/order)
#             self.handle_create_order(data)
#         elif path == "/api/ratings":
#             # POST /api/ratings
#             self.handle_create_rating(data)
#         elif path == "/api/addresses":
#             # POST /api/addresses
#             self.handle_create_address(data)

# Add a new do_PUT method (after do_POST):
#
#     def do_PUT(self):
#         """Handle PUT requests"""
#         parsed_path = urlparse(self.path)
#         path = parsed_path.path
#
#         content_length = int(self.headers.get('Content-Length', 0))
#         body = self.rfile.read(content_length).decode('utf-8', errors='ignore')
#
#         try:
#             data = json.loads(body) if body else {}
#         except json.JSONDecodeError:
#             data = {}
#
#         # PUT endpoints
#         if path.startswith("/api/addresses/"):
#             # PUT /api/addresses/:id
#             addr_id = path.split("/api/addresses/")[1]
#             self.handle_update_address(addr_id, data)
#         else:
#             self.send_error(404)

# Add a new do_DELETE method (after do_PUT):
#
#     def do_DELETE(self):
#         """Handle DELETE requests"""
#         parsed_path = urlparse(self.path)
#         path = parsed_path.path
#
#         # DELETE endpoints
#         if path.startswith("/api/orders/") and path.endswith("/cancel"):
#             # DELETE /api/orders/:orderId/cancel
#             order_id = path.split("/api/orders/")[1].split("/cancel")[0]
#             self.handle_cancel_order(order_id)
#         elif path.startswith("/api/addresses/"):
#             # DELETE /api/addresses/:id
#             addr_id = path.split("/api/addresses/")[1]
#             self.handle_delete_address(addr_id)
#         else:
#             self.send_error(404)
