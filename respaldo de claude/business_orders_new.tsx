import { useState, useEffect, useCallback } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  Alert,
  RefreshControl,
  TextInput,
  Modal,
} from 'react-native';
import { useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { Clock, MapPin, CheckCircle, ArrowLeft, UserCheck, Package } from 'lucide-react-native';
import Colors from '@/constants/colors';
import { useAuth } from '@/contexts/auth';
import { getUserOrders, acceptOrder } from '@/services/orders';
import { Order } from '@/constants/types';
import { API_BASE } from '@/constants/api';

export default function BusinessOrdersScreen() {
  const router = useRouter();
  const { user, token } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showValidateModal, setShowValidateModal] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [driverCodeInput, setDriverCodeInput] = useState('');
  const [validating, setValidating] = useState(false);

  const loadOrders = useCallback(async () => {
    if (!user || !token) return;

    try {
      const fetchedOrders = await getUserOrders(user.id, token);
      const businessOrders = fetchedOrders.filter(
        (order) => order.businessId === user.id
      );
      setOrders(businessOrders);
    } catch (error) {
      console.error('Error loading orders:', error);
      Alert.alert('Error', 'No se pudieron cargar las órdenes');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [user, token]);

  useEffect(() => {
    loadOrders();
    const interval = setInterval(loadOrders, 10000);
    return () => clearInterval(interval);
  }, [loadOrders]);

  const handleAcceptOrder = async (orderId: string) => {
    if (!token) return;

    Alert.alert(
      'Aceptar Orden',
      '¿Confirmar aceptación? (Tiempo estimado: 20 min)',
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Aceptar',
          onPress: async () => {
            try {
              await acceptOrder(orderId, 20, token);
              Alert.alert('Éxito', 'Orden aceptada');
              loadOrders();
            } catch (error) {
              console.error('Error accepting order:', error);
              Alert.alert('Error', 'No se pudo aceptar la orden');
            }
          },
        },
      ]
    );
  };

  const openValidateModal = (order: Order) => {
    setSelectedOrder(order);
    setDriverCodeInput('');
    setShowValidateModal(true);
  };

  const validateDriverCode = async () => {
    if (!selectedOrder || !token || !driverCodeInput.trim()) {
      Alert.alert('Error', 'Ingresa el código del repartidor');
      return;
    }

    setValidating(true);
    try {
      const response = await fetch(`${API_BASE}/orders/${selectedOrder.id}/business-validate`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ driverCode: driverCodeInput.trim().toUpperCase() }),
      });

      const data = await response.json();

      if (response.ok) {
        setShowValidateModal(false);
        Alert.alert(
          'Repartidor Verificado',
          `Entrega la orden con el código de comanda: ${data.comandaCode}`,
          [{ text: 'OK', onPress: loadOrders }]
        );
      } else {
        Alert.alert('Error', data.error || 'Código incorrecto');
      }
    } catch (error) {
      console.error('Error validating driver:', error);
      Alert.alert('Error', 'No se pudo validar el código');
    } finally {
      setValidating(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadOrders();
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      pending: 'Pendiente',
      accepted: 'Aceptada',
      confirmed: 'Confirmada',
      assigned: 'Repartidor Asignado',
      preparing: 'Preparando',
      ready: 'Lista',
      driver_verified: 'Repartidor Verificado',
      picked_up: 'Recogida',
      delivered: 'Entregada',
      cancelled: 'Cancelada',
    };
    return labels[status] || status;
  };

  const getStatusColor = (status: string) => {
    if (status === 'pending') return Colors.warning;
    if (status === 'accepted' || status === 'confirmed' || status === 'preparing') return Colors.accent;
    if (status === 'assigned') return '#9C27B0';
    if (status === 'driver_verified') return '#4CAF50';
    if (status === 'ready' || status === 'picked_up') return Colors.primary;
    if (status === 'delivered') return Colors.success;
    if (status === 'cancelled') return Colors.error;
    return Colors.mediumGray;
  };

  const renderOrder = (order: Order) => {
    const isPending = order.status === 'pending';
    const isAssigned = order.status === 'assigned' || order.status === 'accepted' || order.status === 'confirmed';
    const isDriverVerified = order.status === 'driver_verified';
    const comandaCode = (order as any).comandaCode;

    return (
      <View key={order.id} style={styles.orderCard}>
        <View style={styles.orderHeader}>
          <Text style={styles.orderNumber}>Orden #{order.id.toString().slice(0, 8)}</Text>
          <View
            style={[
              styles.statusBadge,
              { backgroundColor: `${getStatusColor(order.status)}15` },
            ]}
          >
            <Text style={[styles.statusText, { color: getStatusColor(order.status) }]}>
              {getStatusLabel(order.status)}
            </Text>
          </View>
        </View>

        <View style={styles.orderDetails}>
          <View style={styles.detailRow}>
            <MapPin size={16} color={Colors.primary} />
            <Text style={styles.detailText} numberOfLines={2}>
              {typeof order.deliveryAddress === 'string' ? order.deliveryAddress : (order.deliveryAddress as any)?.address || 'Ver mapa'}
            </Text>
          </View>

          <View style={styles.detailRow}>
            <Clock size={16} color={Colors.accent} />
            <Text style={styles.detailText}>
              {new Date(order.createdAt).toLocaleTimeString('es-MX', {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </Text>
          </View>

          {order.items && order.items.length > 0 && (
            <View style={styles.itemsList}>
              <Text style={styles.itemsTitle}>Productos:</Text>
              {order.items.map((item, index) => (
                <Text key={index} style={styles.itemText}>
                  • {item.quantity}x {item.name}
                </Text>
              ))}
            </View>
          )}

          <Text style={styles.totalText}>Total: ${order.total.toFixed(2)} MXN</Text>
        </View>

        {/* Pending - Accept button */}
        {isPending && (
          <TouchableOpacity
            style={styles.acceptButton}
            onPress={() => handleAcceptOrder(order.id.toString())}
          >
            <CheckCircle size={20} color="#fff" />
            <Text style={styles.acceptButtonText}>Aceptar Orden</Text>
          </TouchableOpacity>
        )}

        {/* Assigned - Waiting for driver, show validate button */}
        {isAssigned && (order as any).driverId && (
          <View style={styles.driverSection}>
            <Text style={styles.driverInfo}>
              Repartidor: {(order as any).driverName || 'Asignado'}
            </Text>
            <TouchableOpacity
              style={styles.validateButton}
              onPress={() => openValidateModal(order)}
            >
              <UserCheck size={20} color="#fff" />
              <Text style={styles.validateButtonText}>Validar Repartidor</Text>
            </TouchableOpacity>
            <Text style={styles.validateHint}>
              Pide al repartidor su código de 4 caracteres
            </Text>
          </View>
        )}

        {/* Driver Verified - Show comanda code */}
        {isDriverVerified && comandaCode && (
          <View style={styles.comandaSection}>
            <Package size={24} color={Colors.success} />
            <Text style={styles.comandaLabel}>Código de Comanda:</Text>
            <View style={styles.comandaBadge}>
              <Text style={styles.comandaCode}>{comandaCode}</Text>
            </View>
            <Text style={styles.comandaHint}>
              Este código identifica la orden física. Entrega al repartidor.
            </Text>
          </View>
        )}
      </View>
    );
  };

  return (
    <LinearGradient
      colors={[Colors.secondary, Colors.secondaryDark]}
      style={styles.container}
    >
      {/* Driver Validation Modal */}
      <Modal
        visible={showValidateModal}
        transparent={true}
        animationType="slide"
        onRequestClose={() => setShowValidateModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Validar Repartidor</Text>
            <Text style={styles.modalSubtitle}>
              Pide al repartidor su código de verificación
            </Text>

            <TextInput
              style={styles.codeInput}
              value={driverCodeInput}
              onChangeText={setDriverCodeInput}
              placeholder="XXXX"
              placeholderTextColor={Colors.text.tertiary}
              maxLength={4}
              autoCapitalize="characters"
              textAlign="center"
            />

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.cancelButton}
                onPress={() => setShowValidateModal(false)}
              >
                <Text style={styles.cancelButtonText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.confirmButton, validating && styles.buttonDisabled]}
                onPress={validateDriverCode}
                disabled={validating}
              >
                <Text style={styles.confirmButtonText}>
                  {validating ? 'Validando...' : 'Validar'}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <ArrowLeft size={24} color={Colors.white} />
        </TouchableOpacity>
        <Text style={styles.title}>Órdenes</Text>
        <View style={styles.placeholder} />
      </View>

      <View style={styles.content}>
        <ScrollView
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
          }
        >
          {loading ? (
            <Text style={styles.loadingText}>Cargando órdenes...</Text>
          ) : orders.length === 0 ? (
            <Text style={styles.emptyText}>No hay órdenes</Text>
          ) : (
            orders.map(renderOrder)
          )}
        </ScrollView>
      </View>
    </LinearGradient>
  );
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
  orderCard: {
    backgroundColor: Colors.white,
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    shadowColor: Colors.shadow.medium,
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 2,
  },
  orderHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  orderNumber: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.text.primary,
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
  },
  orderDetails: {
    marginBottom: 12,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  detailText: {
    fontSize: 14,
    color: Colors.text.secondary,
    marginLeft: 8,
    flex: 1,
  },
  itemsList: {
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: Colors.border.light,
  },
  itemsTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: Colors.text.primary,
    marginBottom: 4,
  },
  itemText: {
    fontSize: 13,
    color: Colors.text.secondary,
    marginBottom: 2,
  },
  totalText: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.secondary,
    marginTop: 8,
  },
  acceptButton: {
    backgroundColor: Colors.success,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    borderRadius: 8,
    marginTop: 12,
  },
  acceptButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.white,
    marginLeft: 8,
  },
  driverSection: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: Colors.border.light,
    alignItems: 'center',
  },
  driverInfo: {
    fontSize: 14,
    color: Colors.text.secondary,
    marginBottom: 12,
  },
  validateButton: {
    backgroundColor: '#9C27B0',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 12,
    width: '100%',
  },
  validateButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.white,
    marginLeft: 8,
  },
  validateHint: {
    fontSize: 12,
    color: Colors.text.tertiary,
    marginTop: 8,
    textAlign: 'center',
  },
  comandaSection: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: Colors.border.light,
    alignItems: 'center',
    backgroundColor: '#E8F5E9',
    marginHorizontal: -16,
    marginBottom: -16,
    paddingBottom: 16,
    paddingHorizontal: 16,
    borderBottomLeftRadius: 12,
    borderBottomRightRadius: 12,
  },
  comandaLabel: {
    fontSize: 14,
    color: Colors.text.secondary,
    marginTop: 8,
  },
  comandaBadge: {
    backgroundColor: Colors.success,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
    marginVertical: 12,
  },
  comandaCode: {
    fontSize: 28,
    fontWeight: '800',
    color: Colors.white,
    letterSpacing: 6,
  },
  comandaHint: {
    fontSize: 12,
    color: Colors.text.secondary,
    textAlign: 'center',
  },
  loadingText: {
    fontSize: 16,
    color: Colors.text.secondary,
    textAlign: 'center',
    marginTop: 40,
  },
  emptyText: {
    fontSize: 16,
    color: Colors.text.secondary,
    textAlign: 'center',
    marginTop: 40,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: Colors.white,
    borderRadius: 20,
    padding: 24,
    width: '100%',
    maxWidth: 340,
    alignItems: 'center',
  },
  modalTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: Colors.text.primary,
    marginBottom: 8,
  },
  modalSubtitle: {
    fontSize: 14,
    color: Colors.text.secondary,
    textAlign: 'center',
    marginBottom: 24,
  },
  codeInput: {
    width: '100%',
    backgroundColor: '#F5F5F5',
    borderRadius: 12,
    padding: 16,
    fontSize: 32,
    fontWeight: '700',
    letterSpacing: 8,
    color: Colors.text.primary,
    marginBottom: 24,
  },
  modalActions: {
    flexDirection: 'row',
    gap: 12,
    width: '100%',
  },
  cancelButton: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 12,
    backgroundColor: '#F5F5F5',
    alignItems: 'center',
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: Colors.text.secondary,
  },
  confirmButton: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: 12,
    backgroundColor: '#9C27B0',
    alignItems: 'center',
  },
  confirmButtonText: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.white,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
});
