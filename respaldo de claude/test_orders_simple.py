import requests

# Login
print("=== Login ===")
r = requests.post('http://192.168.100.2:3000/api/login',
    json={'email': 'juan@test.com', 'password': 'testPassword123'})
data = r.json()
print(f"Status: {r.status_code}")

if r.status_code == 200:
    token = data['token']
    user_id = data['user']['id']
    print(f"User: {data['user']['nombre']}")
    print(f"User ID: {user_id}")

    # Get all orders
    print("\n=== Get All Orders ===")
    r2 = requests.get(f'http://192.168.100.2:3000/api/orders/user/{user_id}',
        headers={'Authorization': f'Bearer {token}'})
    print(f"Status: {r2.status_code}")
    if r2.status_code == 200:
        orders = r2.json()
        print(f"Total orders: {len(orders)}")
        for order in orders:
            print(f"  - {order['id'][:8]}... status={order.get('status')} estado={order.get('estado')}")
    else:
        print(f"Error: {r2.text}")

    # Get active orders
    print("\n=== Get Active Orders ===")
    r3 = requests.get(f'http://192.168.100.2:3000/api/orders/user/{user_id}/active',
        headers={'Authorization': f'Bearer {token}'})
    print(f"Status: {r3.status_code}")
    if r3.status_code == 200:
        active = r3.json()
        print(f"Active orders: {len(active)}")
        for order in active:
            print(f"  - {order['id'][:8]}... status={order.get('status')} estado={order.get('estado')}")
    else:
        print(f"Error: {r3.text}")
else:
    print(f"Login failed: {data}")
