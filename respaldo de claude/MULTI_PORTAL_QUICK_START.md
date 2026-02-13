# Yesswera Multi-Portal System - Quick Start Guide

**Date**: November 12, 2025
**Status**: Ready for Testing & Deployment

---

## 🚀 Quick Access

### Local Testing
```
Portal Login:     http://localhost:3000/portal/
Cliente:          http://localhost:3000/cliente/
Repartidor:       http://localhost:3000/repartidor/
Negocio:          http://localhost:3000/negocio/
Public App:       http://localhost:3000/
```

### Remote Server (if deployed)
```
Portal Login:     http://192.168.100.3:3000/portal/
Cliente:          http://192.168.100.3:3000/cliente/
Repartidor:       http://192.168.100.3:3000/repartidor/
Negocio:          http://192.168.100.3:3000/negocio/
Public App:       http://192.168.100.3:3000/
```

---

## 🔑 Test Accounts

### Cliente (Customer)
- **Email**: juan@test.com
- **Phone**: 1234567890
- **Type**: cliente
- **Password**: Any password (JWT doesn't validate)

### Repartidor (Delivery Person)
- **Email**: carlos@delivery.com
- **Phone**: 5555555555
- **Type**: repartidor
- **Password**: Any password

### Negocio (Business Owner)
- **Email**: maria@negocio.com
- **Phone**: 9999999999
- **Type**: negocio
- **Password**: Any password

---

## 🧪 5-Minute Testing Checklist

### 1. Portal Login (2 min)
```
✅ Open http://localhost:3000/portal/
✅ Try login with "juan@test.com" + password
✅ Should redirect to /cliente/
✅ See "👋 Juan Pérez" in header
```

### 2. Email/Phone Login (1 min)
```
✅ Go back to portal
✅ Try login with phone "5555555555" + password
✅ Should redirect to /repartidor/
✅ See "Repartidor" in header
```

### 3. Dashboard Features (2 min)
```
Cliente Dashboard:
  ✅ Click "Buscar Productos" tab
  ✅ See 6 product categories
  ✅ Click "Agregar" on any product
  ✅ See cart badge show "1"
  ✅ See "✅ Producto agregado" alert

Repartidor Dashboard:
  ✅ See "Entregas Disponibles" tab
  ✅ See mock delivery cards
  ✅ See "Aceptar" button
  ✅ See earnings stats in header

Negocio Dashboard:
  ✅ See "Órdenes Pendientes" tab
  ✅ Click "Agregar Producto" button
  ✅ See form to add new product
  ✅ Fill and save product
```

---

## 📊 Files Overview

### Backend
- **server_jwt.py** - Contains `/api/user-type` endpoint for auto-detection

### Frontend Portals
- **portal/index.html** - Unified login for all user types (221 lines)
- **cliente/index.html** - Customer dashboard with cart and orders (1,200+ lines)
- **repartidor/index.html** - Delivery person dashboard (1,300+ lines)
- **negocio/index.html** - Business owner dashboard with catalog (1,400+ lines)

### Shared Assets
- **js/shared.js** - Authentication & utility functions (450+ lines)
- **js/popups.js** - Pop-up advertising system (550+ lines)
- **css/portals.css** - Shared styling for all portals (550+ lines)

---

## 🔐 Authentication Flow

```
User enters email/phone + password
        ↓
POST /api/user-type
        ↓
System detects user type (cliente/repartidor/negocio)
        ↓
POST /api/login with detected email
        ↓
System generates JWT token
        ↓
Store in localStorage: yesswera_session
        ↓
Auto-redirect:
├─ /cliente/ (for customers)
├─ /repartidor/ (for delivery)
└─ /negocio/ (for business)
```

---

## 🎨 Color Scheme

| Role | Color | Hex | Usage |
|------|-------|-----|-------|
| Cliente | Green | #4CAF50 | Buttons, accents, header |
| Repartidor | Blue | #2196F3 | Buttons, accents, header |
| Negocio | Orange | #FF9800 | Buttons, accents, header |

---

## 🚨 Troubleshooting

### "User not found" error
- Check user exists in users.json
- Verify email or phone is exact match
- Test with juan@test.com

### Redirect to wrong portal
- Clear localStorage: DevTools → Application → Clear All
- Refresh page with Ctrl+F5
- Check browser console (F12) for errors

### Session expires immediately
- Normal - 30-minute timeout with 25-min warning
- Click anywhere on page to reset timer
- Check localStorage for yesswera_last_activity

### Pop-ups not showing
- Normal - frequency capped (max per day)
- Try fresh browser/incognito mode
- Check DevTools → Console for errors

---

## 📱 Mobile Testing

All dashboards are fully responsive. Test on:
- ✅ iPhone (portrait/landscape)
- ✅ Android phones
- ✅ Tablets
- ✅ Chrome DevTools mobile emulation

**To test mobile emulation**:
1. Press F12 (DevTools)
2. Click device icon (top-left)
3. Select device from list
4. Test navigation and features

---

## 🔗 Key Features to Test

### Portal Login
- [ ] Email login
- [ ] Phone number login
- [ ] Correct auto-redirect per role
- [ ] Error messages for invalid input
- [ ] Session storage in localStorage

### Cliente Dashboard
- [ ] Add products to cart
- [ ] Remove from cart
- [ ] Search functionality
- [ ] View order history
- [ ] Edit profile
- [ ] Session timeout (30 min)
- [ ] Logout button

### Repartidor Dashboard
- [ ] View available deliveries
- [ ] Accept delivery
- [ ] View active delivery
- [ ] See earnings stats
- [ ] View vehicle info
- [ ] Check delivery history

### Negocio Dashboard
- [ ] View pending orders
- [ ] Confirm order
- [ ] Mark order as ready
- [ ] Add product to catalog
- [ ] Edit/delete products
- [ ] View revenue stats
- [ ] Manage deliveries

### Pop-ups
- [ ] Welcome pop-up on first load
- [ ] Pop-ups don't spam (5-min minimum)
- [ ] Daily limits enforced
- [ ] Auto-close with timer
- [ ] Manual close button
- [ ] Code copy functionality (WELCOME20)
- [ ] Button actions work

---

## 💾 Local Storage Keys

Used by the system:

```javascript
// Session management
localStorage.yesswera_session = {
  token: "JWT_TOKEN",
  user: { id, nombre, email, tipo },
  tipo: "cliente|repartidor|negocio",
  saved_at: "ISO_TIMESTAMP"
}

// Activity tracking
localStorage.yesswera_last_activity = "TIMESTAMP_MS"

// Cart (cliente only)
localStorage.yesswera_cart = [ { id, name, price, quantity } ]

// Active delivery (repartidor only)
localStorage.activeDelivery = { id, startTime }

// Products (negocio only)
localStorage.negocio_products = [ { id, name, price, stock } ]

// Pop-up tracking
localStorage.yesswera_popups_shown = { "DATE_POPUP_ID": count }
localStorage.yesswera_last_popup_time = "TIMESTAMP_MS"

// Idempotency tokens
localStorage.yesswera_idempotency = { "TOKEN": { data, timestamp } }
```

---

## 🧪 API Endpoints to Test

### User Type Detection
```bash
curl -X POST http://localhost:3000/api/user-type \
  -H "Content-Type: application/json" \
  -d '{"emailOrPhone":"juan@test.com"}'

# Response:
{
  "success": true,
  "email": "juan@test.com",
  "tipo": "cliente",
  "nombre": "Juan Pérez"
}
```

### Test with Phone
```bash
curl -X POST http://localhost:3000/api/user-type \
  -H "Content-Type: application/json" \
  -d '{"emailOrPhone":"5555555555"}'

# Response:
{
  "success": true,
  "email": "carlos@delivery.com",
  "tipo": "repartidor",
  "nombre": "Carlos López"
}
```

### Server Ping
```bash
curl http://localhost:3000/api/ping

# Response:
{
  "status": "online",
  "timestamp": "2025-11-12T..."
}
```

---

## 📋 Deployment Checklist

Before going live:

- [ ] Update test accounts with real data in users.json
- [ ] Change JWT_SECRET in server_jwt.py
- [ ] Change ADMIN_PASSWORD in server_jwt.py
- [ ] Enable HTTPS/SSL
- [ ] Test all three portals on remote server
- [ ] Test login with sample accounts
- [ ] Verify pop-ups display correctly
- [ ] Test mobile responsiveness
- [ ] Load test with multiple concurrent users
- [ ] Check browser console for errors
- [ ] Verify offline detection works
- [ ] Test session timeout
- [ ] Set up monitoring/logging
- [ ] Document for support team

---

## 🎓 Documentation Files

- **MULTI_PORTAL_IMPLEMENTATION_GUIDE.md** - Complete implementation specs
- **MULTI_PORTAL_IMPLEMENTATION_SUMMARY.md** - Detailed summary with all features
- **MULTI_PORTAL_QUICK_START.md** - This file

---

## 💡 Tips & Tricks

### Quick Debug
```javascript
// In browser console (F12):
JSON.parse(localStorage.yesswera_session) // View session
popupManager.showById('welcome') // Show specific popup
logout() // Force logout
getUserType() // Check user type
getToken() // View token
```

### Clear Session
```javascript
localStorage.clear()
location.reload()
```

### Test Offline Mode
1. F12 → Network tab
2. Throttling → Offline
3. Try actions (should show "Desconectado")
4. Throttling → Online (should recover)

### Inspect Network Requests
1. F12 → Network tab
2. Perform action
3. See API calls
4. Check request headers for Authorization
5. See response data

---

## 🎯 What's Working

✅ Portal login with email/phone
✅ Auto-detection of user type
✅ JWT authentication
✅ Auto-redirect to correct dashboard
✅ Cliente dashboard with cart and products
✅ Repartidor dashboard with deliveries
✅ Negocio dashboard with catalog
✅ Session timeout with warning
✅ Online/offline detection
✅ Pop-up advertising system
✅ Responsive mobile design
✅ Shared utilities module
✅ localStorage persistence
✅ Error handling and notifications

---

## 🚀 Next Steps

1. **Deploy to Remote Server**
   - Upload files to 192.168.100.3
   - Restart yesswera-web service
   - Test all endpoints

2. **QA Testing**
   - Comprehensive manual testing
   - Cross-browser testing (Chrome, Firefox, Safari, Edge)
   - Mobile device testing
   - Load testing

3. **User Training**
   - Create user guides for each role
   - Record training videos
   - Document support procedures

4. **Go Live**
   - Soft launch with beta users
   - Monitor for issues
   - Full public release

---

**Ready to test? Start with the 5-minute checklist above!** ✅

For detailed information, see: **MULTI_PORTAL_IMPLEMENTATION_SUMMARY.md**
