import requests
import json

# Login
login_response = requests.post(
    'http://192.168.100.2:3000/api/login',
    json={'email': 'juan@test.com', 'password': 'testPassword123'}
)

if login_response.status_code == 200:
    data = login_response.json()
    token = data.get('token')
    user_id = data['user']['id']

    print(f"Login exitoso - User ID: {user_id}")

    # Get active orders
    orders_response = requests.get(
        f'http://192.168.100.2:3000/api/orders/user/{user_id}/active',
        headers={'Authorization': f'Bearer {token}'}
    )

    print(f"\nActive Orders Response ({orders_response.status_code}):")
    print(json.dumps(orders_response.json(), indent=2))
else:
    print(f"Login failed: {login_response.status_code}")
    print(login_response.text)
