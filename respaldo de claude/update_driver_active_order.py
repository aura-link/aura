#!/usr/bin/env python3
"""Update driver active-order.tsx to handle handed_to_driver status"""

with open("/home/yesswera/yesswera-app-mobile/app/driver/active-order.tsx", "r") as f:
    content = f.read()

# 1. Update status checks to include handed_to_driver
old_status_checks = '''// Status checks
  const driverCode = order.driverCode || '';


  const isDriverVerified = order.status === 'driver_verified';
  const isPickedUp = order.status === 'picked_up' || order.status === 'in_transit';
  const canShowDriverCode = !isDriverVerified && !isPickedUp &&
    (order.status === 'assigned' || order.status === 'accepted' || order.status === 'confirmed' || order.status === 'ready');
  const canConfirmPickup = isDriverVerified && !isPickedUp;
  const canDeliver = isPickedUp;'''

new_status_checks = '''// Status checks
  const driverCode = order.driverCode || '';

  const isDriverVerified = order.status === 'driver_verified';
  const isHandedToDriver = order.status === 'handed_to_driver';
  const isPickedUp = order.status === 'picked_up' || order.status === 'in_transit';
  const canShowDriverCode = !isDriverVerified && !isHandedToDriver && !isPickedUp &&
    (order.status === 'assigned' || order.status === 'accepted' || order.status === 'confirmed' || order.status === 'ready');
  const canConfirmPickup = (isDriverVerified || isHandedToDriver) && !isPickedUp;
  const canDeliver = isPickedUp;'''

content = content.replace(old_status_checks, new_status_checks)

# 2. Update the "Business verified" section to handle both statuses
old_verify_section = '''          {/* Step 1.5: Business verified, confirm pickup */}
          {canConfirmPickup && (
            <View style={styles.codeCard}>
              <View style={styles.stepHeader}>
                <CheckCircle size={24} color={Colors.success} />
                <Text style={styles.stepTitle}>Negocio Verificó tu Código</Text>
              </View>
              <Text style={styles.stepInstruction}>
                El negocio confirmó tu identidad. Recoge la orden y confirma:
              </Text>
              <TouchableOpacity
                style={[styles.confirmPickupButton, validating && styles.buttonDisabled]}
                onPress={handleConfirmPickup}
                disabled={validating}
              >
                {validating ? (
                  <ActivityIndicator size="small" color={Colors.white} />
                ) : (
                  <>
                    <Package size={22} color={Colors.white} />
                    <Text style={styles.confirmPickupText}>Confirmar Recogida</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          )}'''

new_verify_section = '''          {/* Step 1.5: Business verified/handed over, confirm pickup */}
          {canConfirmPickup && (
            <View style={styles.codeCard}>
              <View style={styles.stepHeader}>
                <CheckCircle size={24} color={Colors.success} />
                <Text style={styles.stepTitle}>
                  {isHandedToDriver ? '¡El Negocio Te Entregó la Orden!' : 'Negocio Verificó tu Código'}
                </Text>
              </View>
              <Text style={styles.stepInstruction}>
                {isHandedToDriver
                  ? 'El negocio ha confirmado la entrega. Presiona el botón para iniciar la ruta al cliente.'
                  : 'El negocio confirmó tu identidad. Recoge la orden y confirma:'}
              </Text>
              <TouchableOpacity
                style={[styles.confirmPickupButton, validating && styles.buttonDisabled]}
                onPress={handleConfirmPickup}
                disabled={validating}
              >
                {validating ? (
                  <ActivityIndicator size="small" color={Colors.white} />
                ) : (
                  <>
                    <Package size={22} color={Colors.white} />
                    <Text style={styles.confirmPickupText}>
                      {isHandedToDriver ? '¡Orden Recibida!' : 'Confirmar Recogida'}
                    </Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          )}'''

content = content.replace(old_verify_section, new_verify_section)

with open("/home/yesswera/yesswera-app-mobile/app/driver/active-order.tsx", "w") as f:
    f.write(content)

print("Driver active-order.tsx updated!")
print("Added support for 'handed_to_driver' status")
