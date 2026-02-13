with open("/home/yesswera/yesswera-app-mobile/app/driver/active-order.tsx", "r") as f:
    content = f.read()

# Add a forced display of driverCode right after the status badge
old_section = '''<View style={styles.statusCard}>
            <View style={[styles.statusBadge, { backgroundColor: getStatusColor(order.status) }]}>
              <Text style={styles.statusText}>{getStatusLabel(order.status)}</Text>
            </View>
          </View>'''

new_section = '''<View style={styles.statusCard}>
            <View style={[styles.statusBadge, { backgroundColor: getStatusColor(order.status) }]}>
              <Text style={styles.statusText}>{getStatusLabel(order.status)}</Text>
            </View>
          </View>

          {/* FORZAR MOSTRAR CODIGO PARA DEBUG */}
          <View style={{ backgroundColor: 'red', padding: 20, margin: 10, borderRadius: 10 }}>
            <Text style={{ color: 'white', fontSize: 18, fontWeight: 'bold', textAlign: 'center' }}>
              DEBUG - Tu codigo: {(order as any).driverCode || 'NO HAY CODIGO'}
            </Text>
            <Text style={{ color: 'white', fontSize: 14, textAlign: 'center' }}>
              Status: {order.status}
            </Text>
          </View>'''

content = content.replace(old_section, new_section)

with open("/home/yesswera/yesswera-app-mobile/app/driver/active-order.tsx", "w") as f:
    f.write(content)

print("Debug visual agregado - recuadro rojo con codigo")
