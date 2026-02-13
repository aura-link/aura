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
import { ArrowLeft, CheckCircle, Package, QrCode, ShoppingBag, MapPin } from 'lucide-react-native';
import Colors from '@/constants/colors';
import { useAuth } from '@/contexts/auth';
import { API_BASE } from '@/constants/api';

export default function BusinessOrdersScreen() {
  const router = useRouter();
  const { user, token } = useAuth();
  const [orders, setOrders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const [showValidateModal, setShowValidateModal] = useState(false);
  const [driverCodeInput, setDriverCodeInput] = useState('');
  const [validating, setValidating] = useState(false);
  const [validatedOrder, setValidatedOrder] = useState<any>(null);
  const [showOrderDetails, setShowOrderDetails] = useState(false);

  const loadOrders = useCallback(async () => {
    if (!user || !token) return;
    try {
      const response = await fetch(`${API_BASE}/orders/business/${user.id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        const orderList = data.orders || data || [];
        const activeOrders = orderList.filter((o: any) =>
          ['pending', 'confirmed', 'accepted', 'assigned', 'preparing', 'ready'].includes(o.status)
        );
        setOrders(activeOrders);
      }
    } catch (error) {
      console.error('Error loading orders:', error);
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
    try {
      const response = await fetch(`${API_BASE}/orders/${orderId}/accept`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ estimatedTime: 20 }),
      });
      if (response.ok) {
        Alert.alert('Orden Aceptada', 'Tiempo estimado: 20 minutos');
        loadOrders();
      }
    } catch (error) {
      Alert.alert('Error', 'No se pudo aceptar');
    }
  };

  const validateDriverCode = async () => {
    if (!token || !driverCodeInput.trim()) {
      Alert.alert('Error', 'Ingresa el codigo del repartidor');
      return;
    }
    setValidating(true);
    try {
      const response = await fetch(`${API_BASE}/orders/validate-driver-code`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ driverCode: driverCodeInput.trim().toUpperCase(), businessId: user?.id }),
      });
      const data = await response.json();
      if (response.ok && data.success) {
        setValidatedOrder(data.order);
        setShowValidateModal(false);
        setShowOrderDetails(true);
        setDriverCodeInput('');
      } else {
        Alert.alert('Codigo Invalido', data.error || 'No corresponde a ninguna orden');
      }
    } catch (error) {
      Alert.alert('Error', 'Error al validar');
    } finally {
      setValidating(false);
    }
  };

  const confirmHandover = async () => {
    if (!validatedOrder || !token) return;
    try {
      const response = await fetch(`${API_BASE}/orders/${validatedOrder.id}/confirm-handover`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        Alert.alert('Entrega Confirmada', `Comanda #${validatedOrder.comandaCode} entregada al repartidor`, [{
          text: 'OK', onPress: () => { setShowOrderDetails(false); setValidatedOrder(null); loadOrders(); }
        }]);
      }
    } catch (error) {
      Alert.alert('Error', 'Error de conexion');
    }
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = { pending: '#FF9800', accepted: '#4CAF50', assigned: '#9C27B0', ready: '#00BCD4' };
    return colors[status] || '#666';
  };

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = { pending: 'Nueva', accepted: 'Aceptada', assigned: 'Asignada', ready: 'Lista' };
    return labels[status] || status;
  };

  return (
    <View style={styles.container}>
      <LinearGradient colors={[Colors.primary, Colors.primaryDark]} style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <ArrowLeft size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Ordenes</Text>
      </LinearGradient>

      <TouchableOpacity style={styles.mainValidateButton} onPress={() => setShowValidateModal(true)}>
        <QrCode size={28} color="#fff" />
        <View style={styles.mainValidateTextContainer}>
          <Text style={styles.mainValidateTitle}>Validar Repartidor</Text>
          <Text style={styles.mainValidateSubtitle}>Ingresa codigo para ver comanda</Text>
        </View>
      </TouchableOpacity>

      <ScrollView style={styles.scrollView} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); loadOrders(); }} />}>
        {orders.length === 0 ? (
          <View style={styles.emptyState}>
            <Package size={60} color={Colors.text.secondary} />
            <Text style={styles.emptyText}>No hay ordenes activas</Text>
          </View>
        ) : orders.map((order) => (
          <View key={order.id} style={styles.orderCard}>
            <View style={styles.orderHeader}>
              <View style={[styles.statusBadge, { backgroundColor: getStatusColor(order.status) }]}>
                <Text style={styles.statusText}>{getStatusLabel(order.status)}</Text>
              </View>
            </View>
            <Text style={styles.orderTotal}>${order.total?.toFixed(2)}</Text>
            <Text style={styles.itemCount}>{order.items?.length || 0} articulos</Text>
            {order.status === 'pending' && (
              <TouchableOpacity style={styles.acceptButton} onPress={() => handleAcceptOrder(order.id)}>
                <CheckCircle size={20} color="#fff" />
                <Text style={styles.acceptButtonText}>Aceptar Orden</Text>
              </TouchableOpacity>
            )}
          </View>
        ))}
      </ScrollView>

      <Modal visible={showValidateModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Validar Repartidor</Text>
            <Text style={styles.modalSubtitle}>Codigo de 4 caracteres</Text>
            <TextInput style={styles.codeInput} value={driverCodeInput} onChangeText={(t) => setDriverCodeInput(t.toUpperCase())} placeholder="XXXX" maxLength={4} autoCapitalize="characters" autoFocus />
            <View style={styles.modalButtons}>
              <TouchableOpacity style={styles.cancelButton} onPress={() => { setShowValidateModal(false); setDriverCodeInput(''); }}>
                <Text style={styles.cancelButtonText}>Cancelar</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.confirmButton} onPress={validateDriverCode} disabled={validating}>
                <Text style={styles.confirmButtonText}>{validating ? 'Validando...' : 'Validar'}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      <Modal visible={showOrderDetails} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={styles.orderDetailsModal}>
            <View style={styles.comandaHeader}>
              <Text style={styles.comandaTitle}>COMANDA</Text>
              <Text style={styles.comandaCode}>#{validatedOrder?.comandaCode}</Text>
            </View>
            <ScrollView style={styles.itemsList}>
              <Text style={styles.itemsTitle}>Articulos del pedido:</Text>
              {validatedOrder?.items?.map((item: any, i: number) => (
                <View key={i} style={styles.itemRow}>
                  <View style={styles.itemQuantity}><Text style={styles.quantityText}>{item.quantity}x</Text></View>
                  <Text style={styles.itemName}>{item.name}</Text>
                  <Text style={styles.itemPrice}>${(item.price * item.quantity).toFixed(2)}</Text>
                </View>
              ))}
              <View style={styles.totalRow}>
                <Text style={styles.totalLabel}>TOTAL</Text>
                <Text style={styles.totalAmount}>${validatedOrder?.total?.toFixed(2)}</Text>
              </View>
            </ScrollView>
            <View style={styles.deliveryInfo}>
              <MapPin size={16} color={Colors.text.secondary} />
              <Text style={styles.deliveryText}>Entregar: {validatedOrder?.deliveryAddress || 'Ver app repartidor'}</Text>
            </View>
            <View style={styles.codeReminder}>
              <Text style={styles.codeReminderLabel}>Codigo entrega (para cliente):</Text>
              <Text style={styles.deliveryCodeDisplay}>{validatedOrder?.deliveryCode}</Text>
            </View>
            <TouchableOpacity style={styles.handoverButton} onPress={confirmHandover}>
              <ShoppingBag size={24} color="#fff" />
              <Text style={styles.handoverButtonText}>Confirmar Entrega al Repartidor</Text>
            </TouchableOpacity>
            <TouchableOpacity style={styles.closeButton} onPress={() => { setShowOrderDetails(false); setValidatedOrder(null); }}>
              <Text style={styles.closeButtonText}>Cerrar</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  header: { flexDirection: 'row', alignItems: 'center', paddingTop: 50, paddingBottom: 20, paddingHorizontal: 20 },
  backButton: { marginRight: 15 },
  headerTitle: { fontSize: 20, fontWeight: 'bold', color: '#fff' },
  mainValidateButton: { flexDirection: 'row', alignItems: 'center', backgroundColor: Colors.primary, margin: 15, padding: 20, borderRadius: 15, elevation: 5 },
  mainValidateTextContainer: { marginLeft: 15, flex: 1 },
  mainValidateTitle: { fontSize: 18, fontWeight: 'bold', color: '#fff' },
  mainValidateSubtitle: { fontSize: 13, color: 'rgba(255,255,255,0.8)', marginTop: 2 },
  scrollView: { flex: 1, padding: 15 },
  emptyState: { alignItems: 'center', marginTop: 80 },
  emptyText: { fontSize: 18, fontWeight: '600', color: Colors.text.primary, marginTop: 20 },
  orderCard: { backgroundColor: '#fff', borderRadius: 12, padding: 15, marginBottom: 12, elevation: 2 },
  orderHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 },
  statusBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  statusText: { color: '#fff', fontSize: 12, fontWeight: '600' },
  orderTotal: { fontSize: 24, fontWeight: 'bold', color: Colors.text.primary },
  itemCount: { fontSize: 14, color: Colors.text.secondary },
  acceptButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: Colors.success, padding: 12, borderRadius: 8, marginTop: 12 },
  acceptButtonText: { color: '#fff', fontWeight: '600', marginLeft: 8 },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.6)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  modalContent: { backgroundColor: '#fff', borderRadius: 20, padding: 25, width: '100%', maxWidth: 350 },
  modalTitle: { fontSize: 22, fontWeight: 'bold', textAlign: 'center' },
  modalSubtitle: { fontSize: 14, color: Colors.text.secondary, textAlign: 'center', marginVertical: 15 },
  codeInput: { borderWidth: 2, borderColor: Colors.primary, borderRadius: 12, padding: 15, fontSize: 28, fontWeight: 'bold', textAlign: 'center', letterSpacing: 8 },
  modalButtons: { flexDirection: 'row', marginTop: 20, gap: 10 },
  cancelButton: { flex: 1, padding: 15, borderRadius: 10, backgroundColor: '#f0f0f0', alignItems: 'center' },
  cancelButtonText: { color: Colors.text.secondary, fontWeight: '600' },
  confirmButton: { flex: 1, padding: 15, borderRadius: 10, backgroundColor: Colors.primary, alignItems: 'center' },
  confirmButtonText: { color: '#fff', fontWeight: '600' },
  orderDetailsModal: { backgroundColor: '#fff', borderRadius: 20, width: '100%', maxWidth: 400, maxHeight: '85%' },
  comandaHeader: { backgroundColor: Colors.primary, padding: 20, borderTopLeftRadius: 20, borderTopRightRadius: 20, alignItems: 'center' },
  comandaTitle: { fontSize: 14, color: 'rgba(255,255,255,0.8)', fontWeight: '600' },
  comandaCode: { fontSize: 36, fontWeight: 'bold', color: '#fff', marginTop: 5 },
  itemsList: { padding: 20, maxHeight: 250 },
  itemsTitle: { fontSize: 16, fontWeight: '600', marginBottom: 15 },
  itemRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#f0f0f0' },
  itemQuantity: { backgroundColor: Colors.primary, borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4, marginRight: 12 },
  quantityText: { color: '#fff', fontWeight: 'bold' },
  itemName: { flex: 1, fontSize: 15 },
  itemPrice: { fontSize: 15, fontWeight: '600' },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 15, paddingTop: 15, borderTopWidth: 2, borderTopColor: Colors.primary },
  totalLabel: { fontSize: 18, fontWeight: 'bold' },
  totalAmount: { fontSize: 24, fontWeight: 'bold', color: Colors.primary },
  deliveryInfo: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 10, backgroundColor: '#f8f8f8' },
  deliveryText: { marginLeft: 8, fontSize: 13, color: Colors.text.secondary, flex: 1 },
  codeReminder: { padding: 15, backgroundColor: '#fff3e0', margin: 15, borderRadius: 10, alignItems: 'center' },
  codeReminderLabel: { fontSize: 12, color: '#e65100' },
  deliveryCodeDisplay: { fontSize: 24, fontWeight: 'bold', color: '#e65100', marginTop: 5 },
  handoverButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: Colors.success, margin: 15, marginTop: 5, padding: 18, borderRadius: 12 },
  handoverButtonText: { color: '#fff', fontSize: 16, fontWeight: 'bold', marginLeft: 10 },
  closeButton: { alignItems: 'center', padding: 15 },
  closeButtonText: { color: Colors.text.secondary },
});
