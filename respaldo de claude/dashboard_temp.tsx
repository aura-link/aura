import { useState, useEffect, useCallback, useRef } from "react";
import { StyleSheet, Text, View, TouchableOpacity, ScrollView, Alert, Modal, Vibration } from "react-native";
import { useRouter } from "expo-router";
import { Package, DollarSign, Star, Clock, MapPin, Power, Navigation } from "lucide-react-native";
import { LinearGradient } from "expo-linear-gradient";
import Colors from "@/constants/colors";
import { useAuth } from "@/contexts/auth";
import { API_BASE } from "@/constants/api";

export default function DriverDashboardScreen() {
  const router = useRouter();
  const { user, token, logout } = useAuth();
  const [isOnline, setIsOnline] = useState(false);
  const [availableOrders, setAvailableOrders] = useState<any[]>([]);
  const [showOrderNotification, setShowOrderNotification] = useState(false);
  const [notificationOrder, setNotificationOrder] = useState<any>(null);
  const seenOrderIds = useRef<Set<string>>(new Set());

  const [stats] = useState({
    todayDeliveries: 0,
    todayEarnings: 0,
    rating: 4.5,
    totalBalance: 0,
  });

  const loadAvailableOrders = useCallback(async () => {
    if (!user || !token || !isOnline) {
      setAvailableOrders([]);
      return;
    }
    try {
      const response = await fetch(`${API_BASE}/orders/available`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        const orders = data.orders || [];
        setAvailableOrders(orders);
        if (orders.length > 0) {
          const newOrder = orders.find((o: any) => !seenOrderIds.current.has(o.id));
          if (newOrder) {
            seenOrderIds.current.add(newOrder.id);
            setNotificationOrder(newOrder);
            setShowOrderNotification(true);
            Vibration.vibrate([0, 500, 200, 500]);
          }
        }
      }
    } catch (error) {
      console.log("Error loading orders:", error);
    }
  }, [user, token, isOnline]);

  useEffect(() => {
    if (isOnline) {
      loadAvailableOrders();
      const interval = setInterval(loadAvailableOrders, 10000);
      return () => clearInterval(interval);
    }
  }, [isOnline, loadAvailableOrders]);

  const toggleOnlineStatus = () => {
    const newStatus = !isOnline;
    setIsOnline(newStatus);
    if (newStatus) {
      Alert.alert("En Linea", "Ahora recibiras ordenes disponibles");
    } else {
      Alert.alert("Desconectado", "No recibiras nuevas ordenes");
      setAvailableOrders([]);
    }
  };

  const acceptOrder = async (orderId: string) => {
    if (!token || !user) return;
    try {
      const response = await fetch(`${API_BASE}/driver/accept/${orderId}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ driverId: user.id }),
      });
      if (response.ok) {
        Alert.alert("Orden Aceptada!", "Ve a recoger el pedido", [
          { text: "Ir a Orden", onPress: () => router.push("/driver/active-order") },
        ]);
        setAvailableOrders((prev) => prev.filter((o) => o.id !== orderId));
      } else {
        Alert.alert("Error", "No se pudo aceptar la orden");
      }
    } catch {
      Alert.alert("Error", "Error de conexion");
    }
  };

  const getAddress = (addr: any): string => {
    if (typeof addr === "string") return addr;
    if (addr?.address) return addr.address;
    return "Ver en mapa";
  };

  return (
    <View style={styles.container}>
      <Modal visible={showOrderNotification} transparent={true} animationType="slide" onRequestClose={() => setShowOrderNotification(false)}>
        <View style={styles.modalOverlay}>
          <View style={styles.orderNotificationModal}>
            <View style={styles.notificationHeader}>
              <Text style={styles.notificationTitle}>Nueva Orden!</Text>
            </View>
            {notificationOrder && (
              <>
                <View style={styles.notificationBody}>
                  <Text style={styles.notificationBusiness}>{notificationOrder.businessName || "Cliente"}</Text>
                  <Text style={styles.notificationType}>{notificationOrder.type === "food" ? "Comida" : "Paquete"}</Text>
                  <View style={styles.notificationDetail}>
                    <MapPin size={16} color={Colors.text.secondary} />
                    <Text style={styles.notificationDetailText}>{getAddress(notificationOrder.pickupAddress)}</Text>
                  </View>
                  <View style={styles.notificationDetail}>
                    <Navigation size={16} color={Colors.text.secondary} />
                    <Text style={styles.notificationDetailText}>{getAddress(notificationOrder.deliveryAddress)}</Text>
                  </View>
                  <Text style={styles.notificationEarnings}>${(notificationOrder.deliveryFee || 25).toFixed(2)} MXN</Text>
                </View>
                <View style={styles.notificationActions}>
                  <TouchableOpacity style={styles.rejectButton} onPress={() => setShowOrderNotification(false)}>
                    <Text style={styles.rejectButtonText}>Rechazar</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.acceptButton} onPress={() => { setShowOrderNotification(false); acceptOrder(notificationOrder.id); }}>
                    <Text style={styles.acceptButtonText}>Aceptar</Text>
                  </TouchableOpacity>
                </View>
              </>
            )}
          </View>
        </View>
      </Modal>

      <ScrollView style={styles.scrollView} showsVerticalScrollIndicator={false}>
        <LinearGradient colors={[Colors.primary, Colors.primaryDark]} style={styles.header}>
          <View style={styles.headerContent}>
            <Text style={styles.greeting}>Hola, {user?.nombre || "Repartidor"}</Text>
            <Text style={styles.subtitle}>Panel de Repartidor</Text>
            <TouchableOpacity style={[styles.statusButton, isOnline && styles.statusButtonOnline]} onPress={toggleOnlineStatus}>
              <Power size={20} color={isOnline ? Colors.white : Colors.text.secondary} />
              <Text style={[styles.statusText, isOnline && styles.statusTextOnline]}>{isOnline ? "En Linea" : "Desconectado"}</Text>
            </TouchableOpacity>
          </View>
        </LinearGradient>

        <View style={styles.statsContainer}>
          <View style={styles.statCard}><Package size={24} color={Colors.primary} /><Text style={styles.statValue}>{stats.todayDeliveries}</Text><Text style={styles.statLabel}>Entregas Hoy</Text></View>
          <View style={styles.statCard}><DollarSign size={24} color={Colors.success} /><Text style={styles.statValue}>${stats.todayEarnings.toFixed(2)}</Text><Text style={styles.statLabel}>Ganancias</Text></View>
          <View style={styles.statCard}><Star size={24} color={Colors.warning} /><Text style={styles.statValue}>{stats.rating}</Text><Text style={styles.statLabel}>Calificacion</Text></View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Ordenes Disponibles</Text>
          {!isOnline ? (
            <View style={styles.offlineMessage}><Text style={styles.offlineText}>Activa En Linea para ver ordenes</Text></View>
          ) : availableOrders.length === 0 ? (
            <View style={styles.emptyOrders}><Clock size={40} color={Colors.text.tertiary} /><Text style={styles.emptyText}>Esperando ordenes...</Text></View>
          ) : (
            availableOrders.map((order) => (
              <View key={order.id} style={styles.orderCard}>
                <View style={styles.orderHeader}><Text style={styles.businessName}>{order.businessName || "Cliente"}</Text><Text style={styles.orderEarnings}>${(order.deliveryFee || order.earnings || 25).toFixed(2)}</Text></View>
                <View style={styles.addressSection}><Text style={styles.addressLabel}>Recogida:</Text><Text style={styles.addressText}>{getAddress(order.pickupAddress)}</Text><Text style={styles.addressLabel}>Entrega:</Text><Text style={styles.addressText}>{getAddress(order.deliveryAddress)}</Text></View>
                <TouchableOpacity style={styles.acceptOrderButton} onPress={() => acceptOrder(order.id)}><Text style={styles.acceptOrderText}>Aceptar Orden</Text></TouchableOpacity>
              </View>
            ))
          )}
        </View>

        <TouchableOpacity style={styles.activeOrderButton} onPress={() => router.push("/driver/active-order")}><Text style={styles.activeOrderText}>Ver Orden Activa</Text></TouchableOpacity>
        <TouchableOpacity style={styles.logoutButton} onPress={logout}><Text style={styles.logoutText}>Cerrar Sesion</Text></TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scrollView: { flex: 1 },
  header: { padding: 20, paddingTop: 60, borderBottomLeftRadius: 30, borderBottomRightRadius: 30 },
  headerContent: { alignItems: "center" },
  greeting: { fontSize: 24, fontWeight: "700", color: Colors.white },
  subtitle: { fontSize: 14, color: "rgba(255,255,255,0.8)", marginTop: 4 },
  statusButton: { flexDirection: "row", alignItems: "center", backgroundColor: Colors.white, paddingHorizontal: 20, paddingVertical: 12, borderRadius: 25, marginTop: 20 },
  statusButtonOnline: { backgroundColor: Colors.success },
  statusText: { marginLeft: 8, fontSize: 16, fontWeight: "600", color: Colors.text.secondary },
  statusTextOnline: { color: Colors.white },
  statsContainer: { flexDirection: "row", justifyContent: "space-around", padding: 20, marginTop: -20 },
  statCard: { backgroundColor: Colors.white, padding: 16, borderRadius: 16, alignItems: "center", width: "30%", shadowColor: "#000", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3 },
  statValue: { fontSize: 20, fontWeight: "700", color: Colors.text.primary, marginTop: 8 },
  statLabel: { fontSize: 11, color: Colors.text.secondary, marginTop: 4 },
  section: { padding: 20 },
  sectionTitle: { fontSize: 18, fontWeight: "700", color: Colors.text.primary, marginBottom: 16 },
  offlineMessage: { backgroundColor: Colors.surface, padding: 30, borderRadius: 16, alignItems: "center" },
  offlineText: { fontSize: 14, color: Colors.text.secondary },
  emptyOrders: { backgroundColor: Colors.surface, padding: 40, borderRadius: 16, alignItems: "center" },
  emptyText: { fontSize: 14, color: Colors.text.tertiary, marginTop: 12 },
  orderCard: { backgroundColor: Colors.white, borderRadius: 16, padding: 16, marginBottom: 12, shadowColor: "#000", shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4, elevation: 3 },
  orderHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  businessName: { fontSize: 16, fontWeight: "700", color: Colors.text.primary },
  orderEarnings: { fontSize: 18, fontWeight: "700", color: Colors.success },
  addressSection: { marginBottom: 12 },
  addressLabel: { fontSize: 12, color: Colors.text.tertiary, marginTop: 8 },
  addressText: { fontSize: 14, color: Colors.text.secondary },
  acceptOrderButton: { backgroundColor: Colors.primary, padding: 14, borderRadius: 12, alignItems: "center" },
  acceptOrderText: { color: Colors.white, fontSize: 16, fontWeight: "600" },
  activeOrderButton: { backgroundColor: Colors.primaryDark, margin: 20, padding: 16, borderRadius: 12, alignItems: "center" },
  activeOrderText: { color: Colors.white, fontSize: 16, fontWeight: "600" },
  logoutButton: { margin: 20, marginTop: 0, padding: 16, borderRadius: 12, alignItems: "center", backgroundColor: Colors.surface },
  logoutText: { color: Colors.error, fontSize: 16, fontWeight: "600" },
  modalOverlay: { flex: 1, backgroundColor: "rgba(0, 0, 0, 0.6)", justifyContent: "center", alignItems: "center", padding: 20 },
  orderNotificationModal: { backgroundColor: Colors.white, borderRadius: 20, width: "100%", maxWidth: 350, overflow: "hidden" },
  notificationHeader: { backgroundColor: Colors.primary, padding: 20, alignItems: "center" },
  notificationTitle: { fontSize: 22, fontWeight: "800", color: Colors.white },
  notificationBody: { padding: 20 },
  notificationBusiness: { fontSize: 20, fontWeight: "700", color: Colors.text.primary, marginBottom: 8, textAlign: "center" },
  notificationType: { fontSize: 16, color: Colors.text.secondary, textAlign: "center", marginBottom: 16 },
  notificationDetail: { flexDirection: "row", alignItems: "center", marginBottom: 10, paddingHorizontal: 10 },
  notificationDetailText: { fontSize: 14, color: Colors.text.secondary, marginLeft: 10, flex: 1 },
  notificationEarnings: { fontSize: 24, fontWeight: "800", color: Colors.success, textAlign: "center", marginTop: 16 },
  notificationActions: { flexDirection: "row", borderTopWidth: 1, borderTopColor: Colors.border },
  rejectButton: { flex: 1, padding: 18, alignItems: "center", borderRightWidth: 1, borderRightColor: Colors.border },
  rejectButtonText: { fontSize: 16, fontWeight: "600", color: Colors.text.secondary },
  acceptButton: { flex: 1, padding: 18, alignItems: "center", backgroundColor: Colors.success },
  acceptButtonText: { fontSize: 16, fontWeight: "700", color: Colors.white },
});
