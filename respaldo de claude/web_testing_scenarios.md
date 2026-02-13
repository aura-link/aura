# Yesswera Web App - Real-World Testing Scenarios

**Testing Date:** 2025-11-10
**Target:** http://192.168.100.3:3000/
**Backend API:** http://192.168.100.3:3000

---

## Testing Overview

This document outlines comprehensive real-world scenario testing for the Yesswera web application. All tests focus on user workflows and edge cases that might occur in production.

---

## Scenario 1: Initial Load & Login Screen

### Objective
Verify the app loads correctly and displays the login form with proper styling.

### Steps
1. Open browser to http://192.168.100.3:3000/
2. Observe the login screen

### Expected Results
- ✅ Page loads with HTTP 200
- ✅ Black background with green accent (#4CAF50)
- ✅ "Yesswera" title visible
- ✅ Email input field present
- ✅ Password input field present
- ✅ "Iniciar Sesión" button visible and clickable
- ✅ API status shows "🔗 API: 192.168.100.3:3000"

### Pass/Fail
- [ ] PASS
- [ ] FAIL - Details: ___________

---

## Scenario 2: Valid Login with Correct Credentials

### Objective
Test that valid email/password combination authenticates successfully.

### Prerequisites
- Backend must have user credentials registered
- User email and password available

### Steps
1. Enter valid email in email field (e.g., test@example.com)
2. Enter correct password in password field
3. Click "Iniciar Sesión" button
4. Observe response

### Expected Results
- ✅ Button shows "Iniciando sesión..." while processing
- ✅ API request to `/login` is made with POST method
- ✅ Token is received and stored in localStorage
- ✅ Dashboard view appears with:
  - User email displayed in header
  - "✅ App Funcionando" status card
  - "🔗 Backend conectado" status card with IP address
  - "🌐 Ethernet activo" status card
  - "Entregas" section with deliveries list (or "No hay entregas disponibles")
- ✅ Logout button visible in top-right

### Pass/Fail
- [ ] PASS
- [ ] FAIL - Details: ___________

---

## Scenario 3: Invalid Login - Wrong Password

### Objective
Test that incorrect password is rejected with appropriate error message.

### Steps
1. Return to login page (clear localStorage if needed)
2. Enter valid email
3. Enter intentionally WRONG password
4. Click "Iniciar Sesión" button
5. Observe error handling

### Expected Results
- ✅ Button shows "Iniciando sesión..." during processing
- ✅ API request is made to `/login`
- ✅ Error message appears (e.g., "Error: No se pudo iniciar sesión")
- ✅ User remains on login page
- ✅ Email field retains entered value (or is cleared per design choice)
- ✅ Password field is cleared
- ✅ Button returns to normal "Iniciar Sesión" state

### Pass/Fail
- [ ] PASS
- [ ] FAIL - Details: ___________

---

## Scenario 4: Invalid Login - Non-existent Email

### Objective
Test that non-existent email addresses are handled correctly.

### Steps
1. Return to login page
2. Enter email that doesn't exist (e.g., nonexistent@neverused.com)
3. Enter any password
4. Click "Iniciar Sesión" button
5. Observe response

### Expected Results
- ✅ Button shows loading state
- ✅ Error message displayed to user
- ✅ Remains on login page
- ✅ No unexpected JavaScript errors in console

### Pass/Fail
- [ ] PASS
- [ ] FAIL - Details: ___________

---

## Scenario 5: Empty Fields Validation

### Objective
Test form validation when fields are empty.

### Steps
1. On login page, leave email field empty
2. Click "Iniciar Sesión" button
3. Verify browser HTML5 validation stops submission
4. Repeat with password field empty

### Expected Results
- ✅ HTML5 validation prevents form submission
- ✅ Browser shows native validation message on empty required field
- ✅ No API call is made for empty fields

### Pass/Fail
- [ ] PASS
- [ ] FAIL - Details: ___________

---

## Scenario 6: Session Persistence Across Page Refresh

### Objective
Verify token is stored correctly and survives page reload.

### Prerequisites
- Successfully logged in with valid credentials
- Token stored in localStorage

### Steps
1. Login successfully to dashboard
2. Open browser DevTools (F12) → Application/Storage → localStorage
3. Verify "token" key exists with a value
4. Refresh page (Ctrl+R or F5)
5. Observe dashboard loads without showing login screen

### Expected Results
- ✅ localStorage contains "token" key with JWT value
- ✅ Page refresh shows dashboard immediately
- ✅ No redirect to login screen
- ✅ User email still displayed in header
- ✅ Deliveries load without needing to re-login

### Pass/Fail
- [ ] PASS
- [ ] FAIL - Details: ___________

---

## Scenario 7: Dashboard Deliveries List Load

### Objective
Test that deliveries are fetched from backend and displayed correctly.

### Prerequisites
- Backend has deliveries in database
- Logged in successfully

### Steps
1. Login successfully
2. Observe "Entregas" section
3. Wait for deliveries to load (may show "Cargando entregas..." briefly)

### Expected Results
- ✅ Deliveries section displays loading state initially
- ✅ Deliveries are fetched from `/deliveries` endpoint with Bearer token
- ✅ Each delivery card shows:
  - Title (or "Entrega" if missing)
  - Status badge with green background (#4CAF50)
  - Description
- ✅ If no deliveries exist, shows "No hay entregas disponibles"
- ✅ Delivery cards are displayed in responsive grid

### Pass/Fail
- [ ] PASS
- [ ] FAIL - Details: ___________

---

## Scenario 8: Logout Functionality

### Objective
Test that logout properly clears session and returns to login.

### Prerequisites
- Logged in on dashboard

### Steps
1. Click "Salir" (logout) button in top-right
2. Observe page transition
3. Check browser DevTools localStorage for "token" key

### Expected Results
- ✅ Token is removed from localStorage
- ✅ Page redirects to login screen
- ✅ All dashboard content disappears
- ✅ Login form is displayed with empty fields
- ✅ currentUser variable is reset to null

### Pass/Fail
- [ ] PASS
- [ ] FAIL - Details: ___________

---

## Scenario 9: Network Timeout - Slow Connection

### Objective
Test app behavior when API responds slowly.

### Steps
1. Open DevTools → Network tab
2. Set network throttling to "Slow 3G" or "Offline"
3. Attempt login
4. Observe timeout handling

### Expected Results
- ✅ If connection is very slow, appropriate error message appears
- ✅ User can see loading state
- ✅ No crashes or frozen UI
- ✅ Can still interact with form

### Pass/Fail
- [ ] PASS
- [ ] FAIL - Details: ___________

---

## Scenario 10: API Connection Failure

### Objective
Test graceful handling when backend API is unavailable.

### Steps
1. Stop or block the backend API (192.168.100.3:3000)
2. Attempt login
3. Observe error message

### Expected Results
- ✅ Error message: "Error de conexión: [network error details]"
- ✅ No server-related JavaScript errors
- ✅ User can see what went wrong
- ✅ Can retry login once API is available

### Pass/Fail
- [ ] PASS
- [ ] FAIL - Details: ___________

---

## Scenario 11: Token Expiration (If Implemented)

### Objective
Test behavior when JWT token expires.

### Prerequisites
- Backend has token expiration implemented
- Valid session with token

### Steps
1. Login successfully
2. Wait for token to expire (or manually set old token in localStorage)
3. Try to load deliveries or perform any authenticated action
4. Observe behavior

### Expected Results
- ✅ If 401 Unauthorized response: Show login screen
- ✅ Clear localStorage token
- ✅ Redirect user to login
- ✅ User can log in again

### Note
This test only applies if token expiration is implemented on backend.

### Pass/Fail
- [ ] PASS
- [ ] FAIL - Details: ___________

---

## Scenario 12: Multiple Concurrent Logins

### Objective
Test simultaneous login attempts from different browser tabs.

### Steps
1. Open app in two browser tabs
2. In Tab 1: Start login process (but don't wait)
3. In Tab 2: Try to login at same time
4. Observe results

### Expected Results
- ✅ Both requests are processed independently
- ✅ No race conditions
- ✅ Last login's token overwrite previous (or per design)
- ✅ No duplicate tokens in localStorage

### Pass/Fail
- [ ] PASS
- [ ] FAIL - Details: ___________

---

## Scenario 13: Browser Back Button After Login

### Objective
Test navigation with browser back button.

### Prerequisites
- Logged in on dashboard

### Steps
1. On dashboard, click browser back button
2. Observe behavior

### Expected Results
- ✅ Back button should NOT take user to login page (if token still valid)
- ✅ May reload dashboard from cache
- ✅ Or if implemented, show history navigation only on same app page

### Pass/Fail
- [ ] PASS
- [ ] FAIL - Details: ___________

---

## Scenario 14: Responsive Design - Mobile Viewport

### Objective
Test app layout on mobile device sizes.

### Steps
1. Open DevTools → Toggle device toolbar (Ctrl+Shift+M)
2. Set viewport to iPhone 12 (390x844)
3. Test login and dashboard views
4. Verify all elements are visible and clickable

### Expected Results
- ✅ Login form is centered and responsive
- ✅ Buttons are large enough to tap
- ✅ Input fields are properly sized
- ✅ Dashboard is readable
- ✅ Status cards stack vertically
- ✅ Deliveries list is scrollable

### Pass/Fail
- [ ] PASS
- [ ] FAIL - Details: ___________

---

## Scenario 15: Rapid Login/Logout Cycles

### Objective
Test stability through repeated authentication cycles.

### Steps
1. Login with valid credentials
2. Logout immediately
3. Login again
4. Repeat 5 times

### Expected Results
- ✅ Each cycle completes successfully
- ✅ No memory leaks or performance degradation
- ✅ localStorage stays consistent
- ✅ No JavaScript errors in console

### Pass/Fail
- [ ] PASS
- [ ] FAIL - Details: ___________

---

## Test Summary

| Scenario | Status | Notes |
|----------|--------|-------|
| 1. Initial Load | [ ] | |
| 2. Valid Login | [ ] | |
| 3. Wrong Password | [ ] | |
| 4. Non-existent Email | [ ] | |
| 5. Empty Fields | [ ] | |
| 6. Session Persistence | [ ] | |
| 7. Deliveries Load | [ ] | |
| 8. Logout | [ ] | |
| 9. Slow Network | [ ] | |
| 10. API Failure | [ ] | |
| 11. Token Expiration | [ ] | |
| 12. Concurrent Logins | [ ] | |
| 13. Back Button | [ ] | |
| 14. Mobile Responsive | [ ] | |
| 15. Rapid Cycles | [ ] | |

---

## Overall Result

- **Total Tests:** 15
- **Passed:** [ ]
- **Failed:** [ ]
- **Pass Rate:** [ ]%

---

## Issues Found

(List any bugs, improvements, or issues discovered during testing)

1. _______________________________________________________________
2. _______________________________________________________________
3. _______________________________________________________________

---

## Recommendations

(List recommended improvements based on testing results)

1. _______________________________________________________________
2. _______________________________________________________________
3. _______________________________________________________________

---

## Sign-Off

**Tested By:** ________________
**Date:** ___________________
**Status:** ✅ PASSED / ❌ FAILED / ⚠️ CONDITIONAL

---

## Next Steps

Once all scenarios pass:

1. **Implement backend mock user credentials** if not already done
2. **Test with real user data** from production or staging database
3. **Proceed to mobile APK compilation** using EAS (Recommended approach)
4. **Deploy to testing environment** with real users
5. **Gather user feedback** on web app experience before finalizing mobile versions

---

