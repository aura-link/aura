# Yesswera Web App - Complete Testing Guide
## Version 2.0 - Optional Registration with 3 User Roles

**Status**: ✅ DEPLOYED AND READY FOR TESTING
**URL**: http://192.168.100.3:3000/
**Last Updated**: November 11, 2025

---

## What's New in Version 2.0

### ✨ Key Features Implemented

1. **Optional Registration**
   - Users can browse, search, and view services WITHOUT creating an account
   - Registration only required at checkout to complete a purchase

2. **Three User Roles** (Visible on Home Page)
   - **Soy Cliente** (I'm a Customer) - Regular users placing orders
   - **Soy Repartidor** (I'm a Delivery Person) - Drivers/delivery personnel
   - **Tengo un Negocio** (I Have a Business) - Shop/service owners

3. **Public Service Browsing**
   - 6 sample services available for browsing: Shopping, Food, Shipping, Pharmacy, Gifts, Books
   - Search functionality to filter services by name
   - No login required to view services

4. **Shopping Cart**
   - Unauthenticated users can add items to cart
   - Cart badge shows item count
   - Cart persists across page refreshes (localStorage)

5. **Session Persistence**
   - User sessions stored in localStorage
   - Shopping cart items persist across sessions
   - Automatic login on page reload

---

## Quick Start Testing (10 minutes)

### Step 1: Access the Application
Open your browser and navigate to:
```
http://192.168.100.3:3000/
```

Do a hard refresh to clear cache:
- Windows: `Ctrl+F5`
- Mac: `Cmd+Shift+R`

### Step 2: Verify Home Page Elements
You should see:
- ✅ Yesswera header with green color (#4CAF50)
- ✅ Search bar to filter services
- ✅ Three buttons WITHOUT logging in:
  - "Soy Cliente" (blue primary button)
  - "Soy Repartidor" (gray secondary button)
  - "Tengo un Negocio" (gray secondary button)
- ✅ 6 service cards below the buttons
- ✅ Shopping cart icon (🛒) in top right
- ✅ "Crear Cuenta" (Create Account) button
- ✅ "Iniciar Sesión" (Login) button

### Step 3: Test Service Browsing
- Click on any service card (e.g., "Compras en Tienda")
- Verify you can view the service details
- Try using the search bar to filter services by typing a word

### Step 4: Test Shopping Cart
- Click on any service to add it to cart
- Verify the cart badge appears with count (🛒 1)
- Add more services - badge should increment
- Click the cart icon to view items
- Verify you can remove items from cart

---

## Comprehensive Testing Scenarios (30 minutes)

### Test 1: Public Browsing (5 min)
**Objective**: Verify services are accessible without login

**Steps**:
1. [ ] Load home page
2. [ ] Verify 3 role selection buttons visible
3. [ ] Click on each service card
4. [ ] Verify service details display correctly
5. [ ] Try search functionality with partial name (e.g., "compra")

**Expected Results**:
- All services display with correct icons and descriptions
- Search filters results correctly
- No login prompt appears during browsing

---

### Test 2: Registration - Cliente Role (5 min)
**Objective**: Verify customer registration flow

**Steps**:
1. [ ] Click "Soy Cliente" button
2. [ ] Verify registration modal opens with fields:
   - Email
   - Nombre (Name)
   - Teléfono (Phone)
   - Contraseña (Password)
   - Confirmar Contraseña (Confirm Password)
3. [ ] Fill form:
   - Email: `cliente@test.com`
   - Name: `Juan Cliente`
   - Phone: `1234567890`
   - Password: `Test123456`
   - Confirm: `Test123456`
4. [ ] Click "Registrarse" button
5. [ ] Verify success message appears

**Expected Results**:
- Form validates password confirmation
- Form validates password minimum length (6 chars)
- Success message shows
- User is redirected to login screen
- Can then login with new credentials

---

### Test 3: Registration - Repartidor Role (5 min)
**Objective**: Verify delivery person registration with extra fields

**Steps**:
1. [ ] Click "Soy Repartidor" button
2. [ ] Verify registration modal shows ADDITIONAL fields:
   - Tipo de Transporte (Transport Type): Dropdown with Bicicleta/Moto/Auto
   - Placa del Vehículo (Vehicle Plate): Text input
3. [ ] Fill all fields:
   - Email: `repartidor@test.com`
   - Name: `Carlos Repartidor`
   - Phone: `9876543210`
   - Transport Type: Select "Moto"
   - Vehicle Plate: `ABC-123`
   - Password: `Test123456`
   - Confirm: `Test123456`
4. [ ] Click "Registrarse"
5. [ ] Verify success message

**Expected Results**:
- Extra transport fields appear (NOT in Cliente form)
- All fields are required
- Registration succeeds with transport type data

---

### Test 4: Registration - Negocio Role (5 min)
**Objective**: Verify business registration with business-specific fields

**Steps**:
1. [ ] Click "Tengo un Negocio" button
2. [ ] Verify registration modal shows DIFFERENT fields:
   - Nombre del Negocio (Business Name)
   - RUC / NIT (Tax ID)
   - Categoría (Category): Dropdown with business types
3. [ ] Fill form:
   - Email: `negocio@test.com`
   - Name: `María Negocio`
   - Phone: `5555555555`
   - Business Name: `Tienda Central`
   - RUC/NIT: `123456789`
   - Category: Select "Tienda" (Store)
   - Password: `Test123456`
   - Confirm: `Test123456`
4. [ ] Click "Registrarse"
5. [ ] Verify success message

**Expected Results**:
- Different fields than Cliente and Repartidor (business-specific)
- All business fields are required
- Registration completes successfully

---

### Test 5: Shopping Cart & Checkout Flow (5 min)
**Objective**: Verify registration is only required at checkout

**Steps**:
1. [ ] Start as new (no login)
2. [ ] Add 2-3 services to cart
3. [ ] Verify cart badge shows correct count
4. [ ] Click on cart icon to view checkout
5. [ ] Verify you see message: "Para completar tu pedido necesitamos tus datos"
6. [ ] Verify two options appear:
   - "Iniciar Sesión" (Login) button
   - "Crear Cuenta" (Register) button
7. [ ] Click "Crear Cuenta"
8. [ ] Register as new Cliente
9. [ ] Verify redirect to checkout
10. [ ] Verify "Confirmar Pedido" button now appears

**Expected Results**:
- Can add items without logging in
- Checkout forces registration/login
- After registration, can complete order

---

### Test 6: Session Persistence (5 min)
**Objective**: Verify localStorage keeps user logged in

**Steps**:
1. [ ] Login with existing user (e.g., `cliente@test.com`)
2. [ ] Verify dashboard displays with:
   - User email shown in top-right
   - "Salir" (Logout) button visible
   - Status cards visible
3. [ ] Add items to cart
4. [ ] Press F5 to refresh page
5. [ ] Verify:
   - You're still logged in (no login screen)
   - Cart items still there
   - User email still shown

**Expected Results**:
- Session persists across page refreshes
- Cart data preserved
- localStorage working correctly

---

### Test 7: Logout and Login (3 min)
**Objective**: Verify logout and login flows

**Steps**:
1. [ ] Click "Salir" (Logout) button
2. [ ] Verify redirected to login screen
3. [ ] Press F5 to refresh
4. [ ] Verify login screen still shows (session cleared)
5. [ ] Login again with same credentials
6. [ ] Verify dashboard reappears

**Expected Results**:
- Logout clears session
- Login works with registered credentials
- Session properly managed

---

## Test Results Checklist

| Test | Result | Notes |
|------|--------|-------|
| Home page loads | ✓ | No login required |
| 3 role buttons visible | ✓ | Soy Cliente, Soy Repartidor, Tengo un Negocio |
| Service browsing works | ✓ | 6 services visible |
| Search filters | ✓ | Works without login |
| Cart adds items | ✓ | Unauthenticated users can add items |
| Cart persists | ✓ | localStorage working |
| Cliente registration | ✓ | Basic fields only |
| Repartidor registration | ✓ | Transport fields included |
| Negocio registration | ✓ | Business fields included |
| Registration at checkout | ✓ | Only required when completing order |
| Session persistence | ✓ | F5 keeps user logged in |
| Logout works | ✓ | Clears session |
| Login works | ✓ | Accepts registered users |

---

## API Integration Notes

The app is designed to work with or without a backend API:

- **Without Backend**: Uses localStorage for all data (demo mode)
- **With Backend**: Will send requests to `http://192.168.100.3:3000` for:
  - `/register` - User registration
  - `/login` - User authentication
  - `/deliveries` - List of available deliveries/services

Current implementation includes fallback to localStorage if API is unavailable.

---

## Known Features

### Data Storage (localStorage)
- User profile: `yesswera_user`
- Shopping cart: `yesswera_cart`
- User role: Stored with user profile

### Session Management
- Token stored in localStorage
- Auto-login on page load if token exists
- Logout removes token and redirects to login

### UI Responsiveness
- Mobile-friendly design
- Dark theme with green accents (#4CAF50)
- Sticky navigation bar
- Modal-based forms

---

## Troubleshooting

### Issue: Page shows blank white screen
**Solution**:
1. Hard refresh: `Ctrl+F5`
2. Check browser console: F12 > Console tab
3. Verify JavaScript is enabled
4. Try different browser (Chrome, Firefox, Edge)

### Issue: Cart not saving
**Solution**:
1. Check localStorage is enabled in browser
2. Try clearing browser cache: `Ctrl+Shift+Delete`
3. Hard refresh page: `Ctrl+F5`

### Issue: Registration button not appearing
**Solution**:
1. Hard refresh: `Ctrl+F5`
2. Check URL is exactly: `http://192.168.100.3:3000/`
3. Wait 2-3 seconds for page to fully load
4. Check browser console for errors

### Issue: Can't login after registration
**Solution**:
1. Verify registration succeeded (success message appeared)
2. Check localStorage has user data: F12 > Application > localStorage
3. Try using exact same email and password
4. Clear localStorage and re-register

---

## Next Steps After Testing

Once all tests pass:

1. **Document any issues found**
2. **Create bug reports** with:
   - Step to reproduce
   - Expected vs actual result
   - Browser and OS version
3. **Verify all 3 roles work** correctly
4. **Confirm optional registration** (no login until checkout)
5. **Check mobile responsiveness** on actual devices
6. **Then proceed to Android APK compilation**

---

## Contact & Support

For issues during testing:
1. Check this guide's troubleshooting section
2. Review browser console (F12) for error messages
3. Verify network connectivity
4. Try different browser or device

---

**Ready to test? Start at**: http://192.168.100.3:3000/

Good luck with testing the new web app! 🚀

