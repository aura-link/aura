with open("/home/yesswera/yesswera-app-mobile/app/driver/active-order.tsx", "r") as f:
    content = f.read()

# Add debug console.log after the driverCode line
old_code = '''const driverCode = (order as any).driverCode || '';
  const isDriverVerified = order.status === 'driver_verified';'''

new_code = '''const driverCode = (order as any).driverCode || '';

  // DEBUG - ver datos de orden
  console.log('[DEBUG] Order status:', order.status);
  console.log('[DEBUG] Order driverCode:', (order as any).driverCode);
  console.log('[DEBUG] Full order:', JSON.stringify(order, null, 2));

  const isDriverVerified = order.status === 'driver_verified';'''

content = content.replace(old_code, new_code)

with open("/home/yesswera/yesswera-app-mobile/app/driver/active-order.tsx", "w") as f:
    f.write(content)

print("Debug logs agregados")
