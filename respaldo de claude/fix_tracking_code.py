with open("/home/yesswera/yesswera-app-mobile/app/tracking/[orderId].tsx", "r") as f:
    content = f.read()

# First, make sure we get user from useAuth
old_auth = "const { token } = useAuth();"
new_auth = "const { token, user } = useAuth();"
content = content.replace(old_auth, new_auth)

# Now fix the delivery code section to only show for clients
old_code_section = """{order.deliveryCode && order.status !== 'delivered' && order.status !== 'cancelled' && (
          <View style={styles.deliveryCodeCard}>
            <View style={styles.deliveryCodeHeader}>
              <Key size={24} color={Colors.white} />
              <Text style={styles.deliveryCodeLabel}>Código de Entrega</Text>
            </View>
            <Text style={styles.deliveryCodeText}>{order.deliveryCode}</Text>
            <Text style={styles.deliveryCodeHint}>Proporciona este código al repartidor</Text>
          </View>
        )}"""

new_code_section = """{/* Solo mostrar código de entrega a clientes, no a repartidores */}
        {order.deliveryCode && order.status !== 'delivered' && order.status !== 'cancelled' && user?.userType === 'cliente' && (
          <View style={styles.deliveryCodeCard}>
            <View style={styles.deliveryCodeHeader}>
              <Key size={24} color={Colors.white} />
              <Text style={styles.deliveryCodeLabel}>Código de Entrega</Text>
            </View>
            <Text style={styles.deliveryCodeText}>{order.deliveryCode}</Text>
            <Text style={styles.deliveryCodeHint}>Proporciona este código al repartidor</Text>
          </View>
        )}"""

content = content.replace(old_code_section, new_code_section)

with open("/home/yesswera/yesswera-app-mobile/app/tracking/[orderId].tsx", "w") as f:
    f.write(content)

print("Tracking screen actualizado - código solo visible para clientes")
