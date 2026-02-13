import { useState, useEffect, useCallback, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  Alert,
  TextInput,
  ScrollView,
  ActivityIndicator,
  Platform,
  Keyboard,
  Linking,
} from 'react-native';
import { useRouter } from 'expo-router';
import * as Location from 'expo-location';
import { updateDriverLocation } from '@/services/gps';
import { LinearGradient } from 'expo-linear-gradient';
import { MapPin, Clock, Package, CheckCircle, ArrowLeft, Navigation, MessageCircle, Phone, Store, User } from 'lucide-react-native';
import Colors from '@/constants/colors';
import { useAuth } from '@/contexts/auth';
import { getActiveOrders, validateDeliveryCode } from '@/services/orders';
import { Order } from '@/constants/types';
import { API_BASE } from '@/constants/api';

export default function ActiveOrderScreen() {
  const router = useRouter();
  const { user, token } = useAuth();
  const [order, setOrder] = useState<Order | null>(null);
  const [deliveryCodeInput, setDeliveryCodeInput] = useState('');
  const [loading, setLoading] = useState(true);
  const [validating, setValidating] = useState(false);
  const [locationSubscription, setLocationSubscription] = useState<Location.LocationSubscription | null>(null);
  const [isTrackingLocation, setIsTrackingLocation] = useState(false);

  // GPS Tracking - enviar ubicación cada 5 segundos
  const startLocationTracking = useCallback(async (orderId: string) => {
    try {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        console.log('[GPS] Permiso de ubicación denegado');
        return;
      }

      console.log('[GPS] Iniciando tracking para orden:', orderId);
      setIsTrackingLocation(true);

      const subscription = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.High,
          timeInterval: 5000,
          distanceInterval: 10,
        },
        async (location) => {
          if (user && token) {
            await updateDriverLocation({
              orderId: orderId,
              driverId: user.id,
              latitude: location.coords.latitude,
              longitude: location.coords.longitude,
              speed: location.coords.speed || 0,
              heading: location.coords.heading || 0,
              accuracy: location.coords.accuracy || 0,
            }, token);
          }
        }
      );

      setLocationSubscription(subscription);
    } catch (error) {
      console.error('[GPS] Error iniciando tracking:', error);
    }
  }, [user, token]);

  const stopLocationTracking = useCallback(() => {
    if (locationSubscription) {
      locationSubscription.remove();
      setLocationSubscription(null);
      setIsTrackingLocation(false);
      console.log('[GPS] Tracking detenido');
    }
  }, [locationSubscription]);

  // Iniciar tracking cuando hay orden activa
  useEffect(() => {
    if (order && order.status !== 'delivered' && order.status !== 'cancelled' && !isTrackingLocation) {
      startLocationTracking(order.id.toString());
    }
    return () => {
      stopLocationTracking();
    };
  }, [order?.id, order?.status]);

  const deliveryInputRef = useRef<TextInput>(null);

  const loadActiveOrder = useCallback(async () => {
    if (!user || !token) return;

    try {
      const activeOrders = await getActiveOrders(user.id, token);
      if (activeOrders.length > 0) {
        setOrder(activeOrders[0]);
      } else {
        Alert.alert('Sin órdenes', 'No tienes órdenes activas', [
          { text: 'OK', onPress: () => router.back() },
        ]);
      }
    } catch (error) {
      console.error('Error loading active order:', error);
      Alert.alert('Error', 'No se pudo cargar la orden');
    } finally {
      setLoading(false);
    }
  }, [user, token, router]);

  useEffect(() => {
    loadActiveOrder();
    const interval = setInterval(loadActiveOrder, 10000);
    return () => clearInterval(interval);
  }, [loadActiveOrder]);

  const handleConfirmPickup = async () => {
    if (!order || !token) return;

    Alert.alert(
      'Confirmar Recogida',
      '¿Confirmas que has recogido la orden del negocio?',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Confirmar',
          onPress: async () => {
            setValidating(true);
            try {
              const response = await fetch(`${API_BASE}/orders/${order.id}/confirm-pickup`, {
                method: 'POST',
                headers: {
                  'Authorization': `Bearer ${token}`,
                  'Content-Type': 'application/json',
                },
              });

              if (response.ok) {
                Alert.alert('¡Orden Recogida!', 'Ahora ve a entregar al cliente');
                await loadActiveOrder();
              } else {
                const data = await response.json();
                Alert.alert('Error', data.error || 'No se pudo confirmar');
              }
            } catch (error) {
              Alert.alert('Error', 'Error de conexión');
            } finally {
              setValidating(false);
            }
          },
        },
      ]
    );
  };

  const handleValidateDelivery = async () => {
    if (!order || !token || !deliveryCodeInput) {
      Alert.alert('Error', 'Ingresa el código de entrega');
      return;
    }

    setValidating(true);
    try {
      const result = await validateDeliveryCode(order.id.toString(), deliveryCodeInput, token);
      if (result.success) {
        Alert.alert(
          '¡Orden Completada!',
          'Entrega registrada exitosamente',
          [{ text: 'OK', onPress: () => router.push('/driver/dashboard') }]
        );
        setDeliveryCodeInput('');
      } else {
        Alert.alert('Código Incorrecto', result.message);
      }
    } catch (error: any) {
      Alert.alert('Error', error.message || 'No se pudo validar el código');
    } finally {
      setValidating(false);
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={Colors.primary} />
        <Text style={styles.loadingText}>Cargando orden...</Text>
      </View>
    );
  }

  if (!order) {
    return null;
  }

  // Status checks
  const driverCode = (order as any).driverCode || '';
  const isDriverVerified = order.status === 'driver_verified';
  const isPickedUp = order.status === 'picked_up' || order.status === 'in_transit';
  const canShowDriverCode = !isDriverVerified && !isPickedUp &&
    (order.status === 'assigned' || order.status === 'accepted' || order.status === 'confirmed' || order.status === 'ready');
  const canConfirmPickup = isDriverVerified && !isPickedUp;
  const canDeliver = isPickedUp;

  const openNavigation = (address: string, location?: { latitude: number; longitude: number }) => {
    let url: string;

    if (location?.latitude && location?.longitude) {
      url = Platform.select({
        ios: `maps:?daddr=${location.latitude},${location.longitude}&dirflg=d`,
        android: `google.navigation:q=${location.latitude},${location.longitude}`,
      }) || `https://www.google.com/maps/dir/?api=1&destination=${location.latitude},${location.longitude}`;

      Linking.canOpenURL('waze://').then((supported) => {
        if (supported) {
          Linking.openURL(`waze://?ll=${location.latitude},${location.longitude}&navigate=yes`);
        } else {
          Linking.openURL(url);
        }
      });
    } else {
      const encodedAddress = encodeURIComponent(address);
      url = `https://www.google.com/maps/search/?api=1&query=${encodedAddress}`;
      Linking.openURL(url);
    }
  };

  const callClient = () => {
    if (order.customerPhone) {
      Linking.openURL(`tel:${order.customerPhone}`);
    } else {
      Alert.alert('Sin teléfono', 'No hay número de contacto disponible');
    }
  };

  const getPickupAddress = () => {
    if (typeof order.pickupAddress === 'string') return order.pickupAddress;
    if ((order.pickupAddress as any)?.address) return (order.pickupAddress as any).address;
    return 'Ver en mapa';
  };

  const getDeliveryAddress = () => {
    if (typeof order.deliveryAddress === 'string') return order.deliveryAddress;
    if ((order.deliveryAddress as any)?.address) return (order.deliveryAddress as any).address;
    return 'Ver en mapa';
  };

  return (
    <LinearGradient
      colors={[Colors.primary, Colors.primaryDark]}
      style={styles.container}
    >
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <ArrowLeft size={24} color={Colors.white} />
        </TouchableOpacity>
        <Text style={styles.title}>Orden Activa</Text>
        <View style={styles.placeholder} />
      </View>

      <View style={styles.content}>
        <ScrollView showsVerticalScrollIndicator={false}>
          <View style={styles.statusCard}>
            <View style={[styles.statusBadge, { backgroundColor: getStatusColor(order.status) }]}>
              <Text style={styles.statusText}>{getStatusLabel(order.status)}</Text>
            </View>
          </View>

          {/* Step 1: Show driver code to business */}
          {canShowDriverCode && driverCode && (
            <View style={styles.codeCard}>
              <View style={styles.stepHeader}>
                <Store size={24} color={Colors.primary} />
                <Text style={styles.stepTitle}>Paso 1: Ir al Negocio</Text>
              </View>
              <Text style={styles.stepInstruction}>
                Muestra este código al negocio para recoger la orden:
              </Text>
              <View style={styles.driverCodeContainer}>
                <Text style={styles.driverCodeLabel}>TU CÓDIGO DE REPARTIDOR</Text>
                <Text style={styles.driverCode}>{driverCode}</Text>
              </View>
              <Text style={styles.codeHint}>
                El negocio validará tu código antes de entregarte la orden
              </Text>
            </View>
          )}

          {/* Step 1.5: Business verified, confirm pickup */}
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
          )}

          {/* Picked up success message */}
          {isPickedUp && (
            <View style={[styles.codeCard, styles.successCard]}>
              <CheckCircle size={32} color={Colors.success} />
              <Text style={styles.successText}>Orden Recogida</Text>
              <Text style={styles.successSubtext}>Ahora ve a entregar al cliente</Text>
            </View>
          )}

          {/* Order details card */}
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Detalles de la Orden</Text>

            <View style={styles.addressCard}>
              <View style={styles.addressHeader}>
                <Store size={18} color={Colors.primary} />
                <Text style={styles.addressTitle}>Recogida (Negocio)</Text>
              </View>
              <Text style={styles.addressText}>{getPickupAddress()}</Text>
              {!isPickedUp && (
                <TouchableOpacity
                  style={styles.navButtonSmall}
                  onPress={() => openNavigation(getPickupAddress(), (order as any).pickupLocation)}
                >
                  <Navigation size={16} color={Colors.white} />
                  <Text style={styles.navButtonSmallText}>Ir al negocio</Text>
                </TouchableOpacity>
              )}
            </View>

            <View style={styles.addressCard}>
              <View style={styles.addressHeader}>
                <User size={18} color={Colors.success} />
                <Text style={styles.addressTitle}>Entrega (Cliente)</Text>
              </View>
              <Text style={styles.addressText}>{getDeliveryAddress()}</Text>
              {isPickedUp && (
                <TouchableOpacity
                  style={[styles.navButtonSmall, styles.navButtonGreen]}
                  onPress={() => openNavigation(getDeliveryAddress(), (order as any).deliveryLocation)}
                >
                  <Navigation size={16} color={Colors.white} />
                  <Text style={styles.navButtonSmallText}>Ir al cliente</Text>
                </TouchableOpacity>
              )}
            </View>

            <View style={styles.contactActions}>
              <TouchableOpacity style={styles.contactButton} onPress={callClient}>
                <Phone size={18} color={Colors.primary} />
                <Text style={styles.contactButtonText}>Llamar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.contactButton}
                onPress={() => router.push(`/chat/${order.id}` as any)}
              >
                <MessageCircle size={18} color={Colors.accent} />
                <Text style={styles.contactButtonText}>Chat</Text>
              </TouchableOpacity>
            </View>

            <View style={styles.detailRow}>
              <Clock size={18} color={Colors.warning} />
              <View style={styles.detailTextContainer}>
                <Text style={styles.detailLabel}>Hora:</Text>
                <Text style={styles.detailText}>
                  {new Date(order.createdAt).toLocaleTimeString('es-MX', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </Text>
              </View>
            </View>
            <View style={styles.totalRow}>
              <Text style={styles.totalLabel}>Total:</Text>
              <Text style={styles.totalText}>${order.total.toFixed(2)} MXN</Text>
            </View>
          </View>

          {/* Step 2: Delivery - get code from customer */}
          {canDeliver && (
            <View style={styles.codeCard}>
              <View style={styles.stepHeader}>
                <User size={24} color={Colors.success} />
                <Text style={styles.stepTitle}>Paso 2: Entregar al Cliente</Text>
              </View>
              <Text style={styles.stepInstruction}>
                Pide al cliente su código de entrega de 5 caracteres:
              </Text>
              <TouchableOpacity
                activeOpacity={1}
                onPress={() => deliveryInputRef.current?.focus()}
              >
                <TextInput
                  ref={deliveryInputRef}
                  style={styles.codeInput}
                  placeholder="XXXXX"
                  placeholderTextColor={Colors.text.tertiary}
                  value={deliveryCodeInput}
                  onChangeText={(text) => setDeliveryCodeInput(text.toUpperCase())}
                  maxLength={5}
                  autoCapitalize="characters"
                  editable={!validating}
                  keyboardType="default"
                  returnKeyType="done"
                  autoCorrect={false}
                  blurOnSubmit={true}
                  onSubmitEditing={() => Keyboard.dismiss()}
                  selectTextOnFocus={true}
                />
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.deliveryButton,
                  (deliveryCodeInput.length !== 5 || validating) && styles.buttonDisabled,
                ]}
                onPress={handleValidateDelivery}
                disabled={deliveryCodeInput.length !== 5 || validating}
              >
                {validating ? (
                  <ActivityIndicator size="small" color={Colors.white} />
                ) : (
                  <>
                    <CheckCircle size={20} color={Colors.white} />
                    <Text style={styles.deliveryButtonText}>Completar Entrega</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          )}
        </ScrollView>
      </View>
    </LinearGradient>
  );
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: 'Pendiente',
    assigned: 'Asignada',
    accepted: 'Aceptada',
    confirmed: 'Confirmada',
    preparing: 'Preparando',
    ready: 'Lista',
    driver_verified: 'Verificado por Negocio',
    picked_up: 'En Camino',
    in_transit: 'En Camino al Cliente',
    delivered: 'Entregada',
    cancelled: 'Cancelada',
  };
  return labels[status] || status;
}

function getStatusColor(status: string): string {
  if (status === 'pending') return Colors.warning;
  if (status === 'assigned' || status === 'accepted' || status === 'confirmed') return Colors.accent;
  if (status === 'driver_verified') return '#4CAF50';
  if (status === 'picked_up' || status === 'in_transit') return Colors.primary;
  if (status === 'delivered') return Colors.success;
  if (status === 'cancelled') return Colors.error;
  return Colors.mediumGray;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 20,
  },
  backButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: '700',
    color: Colors.white,
  },
  placeholder: {
    width: 40,
  },
  content: {
    flex: 1,
    backgroundColor: Colors.background.primary,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingTop: 20,
    paddingHorizontal: 20,
  },
  statusCard: {
    alignItems: 'center',
    marginBottom: 16,
  },
  statusBadge: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
  },
  statusText: {
    fontSize: 14,
    fontWeight: '700',
    color: Colors.white,
  },
  codeCard: {
    backgroundColor: Colors.white,
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 4,
  },
  stepHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  stepTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: Colors.text.primary,
    marginLeft: 10,
  },
  stepInstruction: {
    fontSize: 14,
    color: Colors.text.secondary,
    marginBottom: 16,
    lineHeight: 20,
  },
  driverCodeContainer: {
    backgroundColor: Colors.primary,
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    marginBottom: 12,
  },
  driverCodeLabel: {
    fontSize: 12,
    color: 'rgba(255,255,255,0.8)',
    fontWeight: '600',
    marginBottom: 8,
    letterSpacing: 1,
  },
  driverCode: {
    fontSize: 48,
    fontWeight: '800',
    color: Colors.white,
    letterSpacing: 12,
  },
  codeHint: {
    fontSize: 12,
    color: Colors.text.tertiary,
    textAlign: 'center',
  },
  confirmPickupButton: {
    backgroundColor: Colors.success,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    borderRadius: 12,
    marginTop: 8,
  },
  confirmPickupText: {
    fontSize: 18,
    fontWeight: '700',
    color: Colors.white,
    marginLeft: 10,
  },
  successCard: {
    alignItems: 'center',
    backgroundColor: '#E8F5E9',
    borderWidth: 2,
    borderColor: Colors.success,
  },
  successText: {
    fontSize: 18,
    fontWeight: '700',
    color: Colors.success,
    marginTop: 12,
  },
  successSubtext: {
    fontSize: 14,
    color: Colors.text.secondary,
    marginTop: 4,
  },
  card: {
    backgroundColor: Colors.white,
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 2,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: Colors.text.primary,
    marginBottom: 16,
  },
  addressCard: {
    backgroundColor: Colors.background.secondary,
    borderRadius: 10,
    padding: 12,
    marginBottom: 12,
  },
  addressHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
    gap: 6,
  },
  addressTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: Colors.text.primary,
  },
  addressText: {
    fontSize: 14,
    color: Colors.text.secondary,
    marginBottom: 10,
  },
  navButtonSmall: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.accent,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
    gap: 6,
  },
  navButtonGreen: {
    backgroundColor: Colors.success,
  },
  navButtonSmallText: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.white,
  },
  contactActions: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 12,
  },
  contactButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: Colors.white,
    borderWidth: 1.5,
    borderColor: Colors.border.light,
    paddingVertical: 10,
    borderRadius: 8,
    gap: 6,
  },
  contactButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: Colors.text.primary,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  detailTextContainer: {
    flex: 1,
    marginLeft: 8,
  },
  detailLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: Colors.text.secondary,
    marginBottom: 2,
  },
  detailText: {
    fontSize: 14,
    color: Colors.text.primary,
  },
  totalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 8,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: Colors.border.light,
  },
  totalLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: Colors.text.primary,
  },
  totalText: {
    fontSize: 18,
    fontWeight: '700',
    color: Colors.primary,
  },
  codeInput: {
    backgroundColor: '#F5F5F5',
    borderRadius: 12,
    paddingVertical: 16,
    paddingHorizontal: 20,
    fontSize: 32,
    fontWeight: '700',
    textAlign: 'center',
    letterSpacing: 8,
    marginBottom: 16,
    color: Colors.text.primary,
  },
  deliveryButton: {
    backgroundColor: Colors.success,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    borderRadius: 12,
  },
  deliveryButtonText: {
    fontSize: 18,
    fontWeight: '700',
    color: Colors.white,
    marginLeft: 10,
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: Colors.background.primary,
  },
  loadingText: {
    fontSize: 16,
    color: Colors.text.secondary,
    marginTop: 12,
  },
});
