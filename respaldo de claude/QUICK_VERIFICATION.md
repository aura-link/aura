# Yesswera - Quick Verification Checklist

**Date**: November 12, 2025
**Status**: Ready to verify
**Time Required**: 10 minutes

---

## ✅ Quick Verification Steps

### Step 1: Server Status (1 minute)

```bash
# Check if server is running
curl http://192.168.100.3:3000/api/ping
```

**Expected Output**:
```json
{
  "status": "online",
  "timestamp": "2025-11-12T..."
}
```

✅ **If you see this**: Server is running correctly

---

### Step 2: App Access (2 minutes)

**Open in Browser**:
```
http://192.168.100.3:3000/
```

**You should see**:
- ✅ Yesswera header (green logo)
- ✅ Search bar
- ✅ 6 service cards (🏪🍕📦💊🎁📚)
- ✅ "Soy Cliente" button
- ✅ "Soy Repartidor" button
- ✅ "Tengo un Negocio" button
- ✅ Cart icon (🛒) in top right

✅ **If you see all these**: Frontend is working

---

### Step 3: JWT Login Test (3 minutes)

**Click**: "Iniciar Sesión"

**Enter**: juan@test.com

**Click**: "Iniciar Sesión"

**Expected**:
- ✅ Modal closes
- ✅ Your name appears: "👤 Juan Pérez"
- ✅ "Iniciar Sesión" button becomes "Salir"
- ✅ You see "Conectado" status (green indicator)

✅ **If you see all these**: JWT login is working

---

### Step 4: Shopping Cart (2 minutes)

**Click**: Any service card (e.g., 🏪 Compras en Tienda)

**Expected**:
- ✅ Cart badge shows "1" in top right
- ✅ Alert: "✅ Compras en Tienda agregado al carrito"

**Click**: Another service card

**Expected**:
- ✅ Cart badge now shows "2"

✅ **If you see both**: Cart is working

---

### Step 5: Connection Detection (1 minute)

**Simulate Offline** (DevTools):
1. F12 → Network tab
2. Throttling → "Offline"
3. Try to click anything

**Expected**:
- ✅ Red banner at top: "⚠️ No tienes conexión"
- ✅ Status indicator turns red: "Desconectado"
- ✅ Red line at top of page

**Back Online** (DevTools):
1. Throttling → "Online"

**Expected**:
- ✅ Red banner disappears
- ✅ Status turns green: "Conectado"

✅ **If you see both**: Offline detection is working

---

### Step 6: Admin Dashboard (1 minute)

**Open in Browser**:
```
http://192.168.100.3:3000/admin/
```

**Enter Password**: `admin123`

**Click**: "Ingresar"

**Expected Dashboard Shows**:
- ✅ 4 overview cards with statistics
- ✅ 2 real-time charts
- ✅ Tabs: Overview, Usuarios, Órdenes, Entregas, Logs
- ✅ Green pulsing indicator: "Conectado"
- ✅ 6 users in table
- ✅ 5 orders in table
- ✅ 4 deliveries in table

✅ **If you see all these**: Admin dashboard is working

---

## 🧪 Advanced Verification (Optional)

### Test JWT Token

**Command**:
```bash
curl -X POST http://192.168.100.3:3000/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"maria@test.com"}'
```

**Expected**: Response with `"token"` field (long JWT string)

✅ **JWT tokens are being generated**

---

### Test Idempotency

**In Browser DevTools Console** (F12 → Console):

```javascript
// Get idempotency token
console.log(yessweraAuth.getIdempotencyToken());
```

**Expected**: Output like `idmp_a3c5f_1731356406`

✅ **Idempotency tokens are working**

---

### Test Activity Detection

**In Browser DevTools Console** (F12 → Console):

```javascript
// Check last activity time
console.log(localStorage.getItem('yesswera_last_activity'));
```

**Now click somewhere on the page**

```javascript
// Check again
console.log(localStorage.getItem('yesswera_last_activity'));
```

**Expected**: Timestamp changes (recent time)

✅ **Activity detection is working**

---

### Test Session Storage

**In Browser DevTools**:
1. F12 → Application
2. Storage → Local Storage
3. Click http://192.168.100.3:3000

**Should see**:
- `yesswera_session` (contains token)
- `yesswera_cart` (contains items)
- `yesswera_last_activity` (timestamp)

✅ **Session storage is working**

---

## 📊 Summary Table

| Feature | ✅ Status | Location | Time |
|---------|-----------|----------|------|
| Server Ping | Check | /api/ping | 1 min |
| Public App | Check | :3000/ | 2 min |
| JWT Login | Check | Login modal | 3 min |
| Shopping Cart | Check | Add items | 2 min |
| Offline Detection | Check | DevTools offline | 1 min |
| Admin Dashboard | Check | :3000/admin/ | 1 min |
| **TOTAL** | **CHECK ALL** | **10 items** | **10 min** |

---

## 🎯 All Verification Tests

```
✅ Server is running
✅ Public app loads
✅ Services visible
✅ JWT login works
✅ User info shows
✅ Cart adds items
✅ Online status shows
✅ Offline detection works
✅ Admin dashboard loads
✅ Statistics display
✅ Real-time updates
```

---

## ❌ Troubleshooting

### If Server Doesn't Respond
```bash
# Check service status
ssh user@192.168.100.3 "sudo systemctl status yesswera-web"

# Restart service
ssh user@192.168.100.3 "sudo systemctl restart yesswera-web"
```

### If Login Fails
- Verify user exists: Check "Usuarios" tab in admin
- Check JWT secret hasn't changed: Verify in server_jwt.py

### If Admin Dashboard Blank
- Refresh: Ctrl+F5
- Clear localStorage: DevTools → Application → Clear All
- Check admin password: admin123

### If Offline Detection Doesn't Work
- Make sure DevTools throttling is set to "Offline"
- Check console for errors: F12 → Console
- Try disabling network adapter instead

---

## 🚀 Next Steps After Verification

Once all checks pass:

1. **Load Testing**: Test with multiple users
2. **Security Review**: Check for XSS/CSRF
3. **Browser Testing**: Try Chrome, Firefox, Safari, Edge
4. **Mobile Testing**: Test on actual phones
5. **Stress Testing**: Create many orders
6. **Production Setup**: HTTPS, change passwords, enable backups

---

## 📞 Support

**If something doesn't work**:

1. **Check server logs**:
   ```bash
   ssh user@192.168.100.3 "tail -f ~/YessweraWeb/nohup.out"
   ```

2. **Check browser console** (F12 → Console):
   - Look for red error messages
   - Note the error text

3. **Check admin logs** (admin → Logs tab):
   - Scroll through recent events
   - Look for errors

4. **Reference documentation**:
   - JWT_SESSION_TESTING_GUIDE.md - Detailed tests
   - ARCHITECTURE_SUMMARY_JWT.md - System overview
   - ADMIN_DASHBOARD_GUIDE.md - Admin features

---

## ✨ You're Done!

If all checks above passed ✅, then:

```
  ╔════════════════════════════════════╗
  ║   Yesswera v4.0 is WORKING! 🎉   ║
  ╠════════════════════════════════════╣
  ║ ✅ JWT Authentication              ║
  ║ ✅ Session Timeout Management     ║
  ║ ✅ Offline Detection               ║
  ║ ✅ Admin Dashboard                 ║
  ║ ✅ Order Idempotency              ║
  ║ ✅ Real-Time Statistics           ║
  ║                                    ║
  ║  Ready for production! 🚀          ║
  ╚════════════════════════════════════╝
```

---

**Time to Complete**: ~10 minutes
**Difficulty**: Easy
**Success Rate**: Should be 100% if deployed correctly

Go ahead and verify! 💪

