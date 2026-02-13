# Yesswera Web App - Quick Start Testing Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Open the Application
```
Open your browser to: http://192.168.100.3:3000/
```

**Important:** Do a HARD REFRESH first!
- **Windows:** Press `Ctrl+F5`
- **Mac:** Press `Cmd+Shift+R`
- **Firefox:** `Ctrl+Shift+R`

---

## 📝 Test 1: Verify Registration Button (2 min)

**What to do:**
1. Look at the login screen
2. Scroll down if needed
3. You should see TWO buttons:
   - Green button: "Iniciar Sesión"
   - Gray button: "Crear Cuenta"

**Expected result:** ✅ Gray "Crear Cuenta" button is visible
**If fails:** Hard refresh again (Ctrl+F5)

---

## 📝 Test 2: Create New Account (3 min)

**What to do:**
1. Click the gray "Crear Cuenta" button
2. Enter email: `testuser@example.com`
3. Enter password: `TestPassword123`
4. Confirm password: `TestPassword123`
5. Click "Registrarse" button

**Expected results:**
- ✅ Green message: "✅ Cuenta creada exitosamente"
- ✅ Auto-redirects back to login (after ~1.5 seconds)
- ✅ See login form again

**Common issues:**
- Password doesn't match: Error message appears
- Password too short: Error message appears

---

## 📝 Test 3: Login with New Account (2 min)

**What to do:**
1. Email: `testuser@example.com`
2. Password: `TestPassword123`
3. Click "Iniciar Sesión" button

**Expected results:**
- ✅ Button shows "Iniciando sesión..." during loading
- ✅ Dashboard appears
- ✅ Top-right shows: `testuser@example.com`
- ✅ See three status cards:
  - ✅ App Funcionando
  - 🔗 Backend conectado (192.168.100.3:3000)
  - 🌐 Ethernet activo
- ✅ See "Entregas" section

---

## 📝 Test 4: Session Persistence (1 min)

**What to do:**
1. You're on the dashboard (from Test 3)
2. Press `F5` to refresh the page
3. Wait for page to reload

**Expected results:**
- ✅ Dashboard loads IMMEDIATELY
- ✅ NO login form appears
- ✅ User email still shown in top-right
- ✅ All content preserved

---

## 📝 Test 5: Logout (1 min)

**What to do:**
1. On dashboard, locate top-right corner
2. Click red "Salir" button

**Expected results:**
- ✅ Returns to login screen
- ✅ All form fields empty
- ✅ Page is fresh (no cached data)

**Verify:**
1. Press `F5` again
2. Should still show login (not dashboard)
3. This proves logout worked

---

## 🎯 Summary Checklist

After completing all 5 tests above, check:

- [ ] Test 1: Registration button visible
- [ ] Test 2: Can create new account
- [ ] Test 3: Can login with new account
- [ ] Test 4: Session persists across refresh
- [ ] Test 5: Logout clears session

**If ALL checked:** ✅ **BASIC TESTING PASSED**

---

## 🔍 Advanced Testing (Optional)

Once basic tests pass, you can optionally try:

1. **Wrong password:** Try logging in with wrong password
   - Expected: Error message appears

2. **Empty fields:** Try logging in without email
   - Expected: Browser validation message

3. **Duplicate email:** Register with same email twice
   - Expected: Error "Este email ya está registrado"

4. **Mobile view:** Press `Ctrl+Shift+M` in DevTools
   - Expected: Layout adjusts for mobile

For complete advanced testing, see: `C:\claude\web_testing_scenarios.md`

---

## 📱 What Each Screen Shows

### Login Screen
```
┌─────────────────────────────────┐
│                                 │
│           Yesswera              │
│    Plataforma de Entregas       │
│                                 │
│  [Email input field]            │
│  [Password input field]         │
│  [Error message box if needed]  │
│                                 │
│  [Iniciar Sesión button]        │
│  [Crear Cuenta button]          │
│                                 │
│  🔗 API: 192.168.100.3:3000     │
└─────────────────────────────────┘
```

### Registration Screen
```
┌─────────────────────────────────┐
│           Yesswera              │
│     Crear Nueva Cuenta          │
│                                 │
│  [Email input field]            │
│  [Password input field]         │
│  [Confirm Password field]       │
│  [Error/Success message box]    │
│                                 │
│  [Registrarse button]           │
│  [Volver al Login button]       │
│                                 │
│  🔗 API: 192.168.100.3:3000     │
└─────────────────────────────────┘
```

### Dashboard Screen
```
┌──────────────────────────────────────┐
│ Yesswera           testuser@example  │
│                            [Salir]   │
├──────────────────────────────────────┤
│                                      │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│ │ ✅ App  │ │ 🔗 Back │ │ 🌐 Ether│ │
│ │Funciona │ │ conecta │ │ activo  │ │
│ └─────────┘ └─────────┘ └─────────┘ │
│                                      │
│ Entregas                             │
│                                      │
│ [Loading or delivery list here]      │
│                                      │
└──────────────────────────────────────┘
```

---

## 🛠️ Troubleshooting Quick Guide

| Problem | Solution |
|---------|----------|
| Page not loading | Hard refresh: Ctrl+F5 |
| Registration button not showing | Hard refresh: Ctrl+F5 |
| Can't login after registration | Check password length (min 6) |
| Password error | Passwords must match exactly |
| Logout button not working | Try refreshing, should show login |
| Dashboard empty | Wait a moment, may be loading |
| Server error | Check if http://192.168.100.3:3000 is accessible |

---

## 📚 Full Documentation

For complete testing details with all 15 scenarios, see:
- **Main testing guide:** `C:\claude\web_testing_scenarios.md`
- **Status report:** `C:\claude\WEB_APP_TESTING_STATUS.md`
- **Application code:** `C:\claude\YessweraWeb\index.html`

---

## ✅ After Testing

Once you complete all 5 basic tests above, proceed to:
1. Run the automated test script (optional): `C:\claude\test_web_api.sh`
2. Try the advanced test scenarios (optional)
3. Report results to proceed to Android APK compilation

**Your next steps:** Complete these 5 tests and let us know the results!

---

**Test Duration:** ~10-15 minutes total
**Required:** Web browser, internet connection to 192.168.100.3:3000
**No installation needed:** Fully web-based!
