with open("/home/yesswera/yesswera-app-mobile/services/orders.ts", "r") as f:
    content = f.read()

# Add detailed logging to getActiveOrders
old_code = '''const data = await response.json();
    console.log('[getActiveOrders] Success, found', data.length, 'active orders');
    return data;'''

new_code = '''const data = await response.json();
    console.log('[getActiveOrders] Success, found', data.length, 'active orders');
    console.log('[getActiveOrders] FULL DATA:', JSON.stringify(data, null, 2));
    if (data.length > 0) {
      console.log('[getActiveOrders] First order driverCode:', data[0].driverCode);
      console.log('[getActiveOrders] First order keys:', Object.keys(data[0]));
    }
    return data;'''

content = content.replace(old_code, new_code)

with open("/home/yesswera/yesswera-app-mobile/services/orders.ts", "w") as f:
    f.write(content)

print("Debug logs agregados al servicio")
