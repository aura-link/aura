import { useState, useEffect, useCallback } from 'react';
import { StyleSheet, Text, View, TouchableOpacity, ScrollView, RefreshControl, Alert } from 'react-native';
import { useRouter } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { ChefHat, Clock, CheckCircle, LogOut } from 'lucide-react-native';
import Colors from '@/constants/colors';
import { useAuth } from '@/contexts/auth';
import { API_BASE } from '@/constants/api';

export default function ComandasScreen() {
  const router = useRouter();
  const { user, token, logout } = useAuth();
  const [orders, setOrders] = useState<any[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const loadOrders = useCallback(async () => {
    if (!user || !token) return;
    try {
      const response = await fetch(API_BASE + '/orders/business/' + user.id, {
        headers: { Authorization: 'Bearer ' + token },
      });
      if (response.ok) {
        const data = await response.json();
        const activeOrders = (data.orders || []).filter((o: any) =>
          ['accepted', 'assigned', 'ready'].includes(o.status)
        );
        activeOrders.sort((a: any, b: any) =>
          new Date(a.createdAt || a.timestamp).getTime() - new Date(b.createdAt || b.timestamp).getTime()
        );
        setOrders(activeOrders);
      }
    } catch (error) {
      console.log('Error:', error);
    }
  }, [user, token]);

  useEffect(() => {
    loadOrders();
    const interval = setInterval(loadOrders, 5000);
    return () => clearInterval(interval);
  }, [loadOrders]);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadOrders();
    setRefreshing(false);
  };

  const markAsReady = async (orderId: string, comandaCode: string) => {
    Alert.alert('Marcar Lista', 'Comanda #' + comandaCode + ' lista?', [
      { text: 'Cancelar', style: 'cancel' },
      { text: 'Si', onPress: async () => {
        try {
          await fetch(API_BASE + '/orders/' + orderId + '/ready', {
            method: 'POST',
            headers: { Authorization: 'Bearer ' + token, 'Content-Type': 'application/json' },
          });
          loadOrders();
        } catch (e) { Alert.alert('Error'); }
      }},
    ]);
  };

  const handleLogout = async () => { await logout(); router.replace('/'); };

  const getTimeAgo = (ts: string) => {
    const mins = Math.floor((Date.now() - new Date(ts).getTime()) / 60000);
    if (mins < 1) return 'Ahora';
    if (mins < 60) return mins + ' min';
    return Math.floor(mins/60) + 'h';
  };

  const getStatus = (s: string) => {
    if (s === 'ready') return { label: 'LISTA', color: '#4CAF50', bg: '#E8F5E9' };
    if (s === 'assigned') return { label: 'ASIGNADA', color: '#9C27B0', bg: '#F3E5F5' };
    return { label: 'PREPARAR', color: '#FF9800', bg: '#FFF3E0' };
  };

  return (
    <View style={styles.container}>
      <LinearGradient colors={['#FF9800', '#F57C00']} style={styles.header}>
        <View style={styles.headerTop}>
          <ChefHat size={32} color="#fff" />
          <Text style={styles.title}>COMANDAS</Text>
          <TouchableOpacity onPress={handleLogout}><LogOut size={24} color="#fff" /></TouchableOpacity>
        </View>
        <View style={styles.stats}>
          <View style={styles.statBox}>
            <Text style={styles.statNum}>{orders.filter(o => o.status !== 'ready').length}</Text>
            <Text style={styles.statLabel}>Pendientes</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={styles.statNum}>{orders.filter(o => o.status === 'ready').length}</Text>
            <Text style={styles.statLabel}>Listas</Text>
          </View>
        </View>
      </LinearGradient>

      <ScrollView style={styles.content} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#FF9800']} />}>
        {orders.length === 0 ? (
          <View style={styles.empty}>
            <ChefHat size={80} color="#999" />
            <Text style={styles.emptyText}>No hay comandas</Text>
          </View>
        ) : orders.map((order, i) => {
          const st = getStatus(order.status);
          return (
            <View key={order.id} style={[styles.card, order.status === 'ready' && styles.cardDone]}>
              <View style={styles.cardTop}>
                <View>
                  <Text style={styles.label}>COMANDA</Text>
                  <Text style={styles.code}>#{order.comandaCode || '----'}</Text>
                </View>
                <View style={[styles.badge, { backgroundColor: st.bg }]}>
                  <Text style={[styles.badgeTxt, { color: st.color }]}>{st.label}</Text>
                </View>
              </View>
              <View style={styles.timeRow}>
                <Clock size={16} color="#666" />
                <Text style={styles.time}>{getTimeAgo(order.createdAt || order.timestamp)}</Text>
                <Text style={styles.queue}>#{i+1} en cola</Text>
              </View>
              <View style={styles.items}>
                {(order.items || []).map((item: any, idx: number) => (
                  <View key={idx} style={styles.itemRow}>
                    <Text style={styles.qty}>{item.quantity}x</Text>
                    <Text style={styles.name}>{item.name}</Text>
                  </View>
                ))}
              </View>
              {order.status !== 'ready' && (
                <TouchableOpacity style={styles.btn} onPress={() => markAsReady(order.id, order.comandaCode)}>
                  <CheckCircle size={20} color="#fff" />
                  <Text style={styles.btnTxt}>Marcar Lista</Text>
                </TouchableOpacity>
              )}
            </View>
          );
        })}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F5F5F5' },
  header: { paddingTop: 50, paddingBottom: 20, paddingHorizontal: 20 },
  headerTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  title: { fontSize: 24, fontWeight: 'bold', color: '#fff' },
  stats: { flexDirection: 'row', marginTop: 20, justifyContent: 'space-around' },
  statBox: { alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.2)', padding: 15, borderRadius: 12, minWidth: 100 },
  statNum: { fontSize: 32, fontWeight: 'bold', color: '#fff' },
  statLabel: { fontSize: 12, color: 'rgba(255,255,255,0.9)', marginTop: 4 },
  content: { flex: 1, padding: 15 },
  empty: { alignItems: 'center', marginTop: 80 },
  emptyText: { fontSize: 18, color: '#666', marginTop: 20 },
  card: { backgroundColor: '#fff', borderRadius: 16, padding: 16, marginBottom: 12, elevation: 3, borderLeftWidth: 5, borderLeftColor: '#FF9800' },
  cardDone: { borderLeftColor: '#4CAF50', opacity: 0.7 },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  label: { fontSize: 10, color: '#999', fontWeight: '600' },
  code: { fontSize: 28, fontWeight: 'bold', color: '#333' },
  badge: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20 },
  badgeTxt: { fontSize: 12, fontWeight: 'bold' },
  timeRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 12, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: '#EEE' },
  time: { fontSize: 14, color: '#666', marginLeft: 6 },
  queue: { fontSize: 12, color: '#999', marginLeft: 'auto' },
  items: { marginBottom: 12 },
  itemRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 6 },
  qty: { fontSize: 16, fontWeight: 'bold', color: '#2196F3', width: 35 },
  name: { fontSize: 16, color: '#333', flex: 1 },
  btn: { backgroundColor: '#4CAF50', flexDirection: 'row', alignItems: 'center', justifyContent: 'center', padding: 14, borderRadius: 12 },
  btnTxt: { color: '#fff', fontSize: 16, fontWeight: 'bold', marginLeft: 8 },
});
