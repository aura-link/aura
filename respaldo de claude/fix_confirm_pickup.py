#!/usr/bin/env python3
"""Fix confirm-pickup to accept handed_to_driver status"""

with open("/home/yesswera/YessweraWeb/server_jwt.py", "r") as f:
    content = f.read()

# Update the status check to accept both statuses
old_check = '''            # Verify order was verified by business
            if order.get('status') != 'driver_verified':
                self.send_json_response({"error": "El negocio debe verificar tu codigo primero"}, 400)
                return'''

new_check = '''            # Verify order was verified/handed over by business
            if order.get('status') not in ['driver_verified', 'handed_to_driver']:
                self.send_json_response({"error": "El negocio debe verificar tu codigo o confirmar la entrega primero"}, 400)
                return'''

content = content.replace(old_check, new_check)

with open("/home/yesswera/YessweraWeb/server_jwt.py", "w") as f:
    f.write(content)

print("confirm-pickup handler updated to accept handed_to_driver status")
