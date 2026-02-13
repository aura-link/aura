with open("/home/yesswera/yesswera-app-mobile/app/driver/active-order.tsx", "r") as f:
    content = f.read()

# Replace the debug box to show ALL order keys
old_debug = '''<View style={{ backgroundColor: 'red', padding: 20, margin: 10, borderRadius: 10 }}>
            <Text style={{ color: 'white', fontSize: 18, fontWeight: 'bold', textAlign: 'center' }}>
              DEBUG - Tu codigo: {(order as any).driverCode || 'NO HAY CODIGO'}
            </Text>
            <Text style={{ color: 'white', fontSize: 14, textAlign: 'center' }}>
              Status: {order.status}
            </Text>
          </View>'''

new_debug = '''<View style={{ backgroundColor: 'red', padding: 20, margin: 10, borderRadius: 10 }}>
            <Text style={{ color: 'white', fontSize: 18, fontWeight: 'bold', textAlign: 'center' }}>
              DEBUG - Tu codigo: {(order as any).driverCode || 'NO HAY CODIGO'}
            </Text>
            <Text style={{ color: 'white', fontSize: 12, textAlign: 'center' }}>
              Status: {order.status}
            </Text>
            <Text style={{ color: 'yellow', fontSize: 10, textAlign: 'center', marginTop: 5 }}>
              Keys: {Object.keys(order).join(', ')}
            </Text>
          </View>'''

content = content.replace(old_debug, new_debug)

with open("/home/yesswera/yesswera-app-mobile/app/driver/active-order.tsx", "w") as f:
    f.write(content)

print("Debug actualizado para mostrar todas las keys del order")
