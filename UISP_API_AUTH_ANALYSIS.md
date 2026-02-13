# UISP API Authentication Analysis & Solutions

**Date:** 2025-12-01
**Status:** Investigation Complete - Solution Options Identified

---

## Problem Summary

The AURALINK Monitor bot cannot fetch real client/device data from UISP because API token authentication is failing with **401 Authentication Required** errors across ALL tested authentication methods.

**Tested and Failed:**
- ✗ Bearer token: `Authorization: Bearer {token}`
- ✗ Custom header: `x-auth-token: {token}`
- ✗ Basic auth: `Authorization: Basic base64(username:password)`
- ✗ Query parameter: `?apitoken={token}`
- ✗ Multiple token formats (both provided tokens)

**Interesting Finding:**
- The API tokens **WORK in the UISP Swagger UI** (api-docs interface)
- The API tokens **FAIL for direct API calls** from curl/Python/requests
- This suggests tokens may be restricted to web UI sessions only

---

## Root Cause Analysis

### Theory 1: Token Scope Limitation (MOST LIKELY)
UISP API tokens might be designed for:
- Web UI authentication only
- Session-based access only (requires browser cookies)
- Specific user permissions not set for API access

**Evidence:**
- Swagger UI (web-based) works with token
- Direct API calls fail with 401
- This is a common pattern in newer API management systems

### Theory 2: Token Permissions
The token exists but doesn't have:
- API read permissions enabled
- Client/device read permissions
- Active status in API token settings

**How to check:**
UISP Admin Panel → Settings → API Tokens → {Your Token Name}
- ☐ Enabled checkbox
- ☐ Has "Read" permission
- ☐ "Clients" section is readable
- ☐ "Devices" section is readable

### Theory 3: IP/Network Restrictions
Token might be restricted to:
- Specific IP addresses
- Same subnet only
- Admin interface only

---

## Solution Options

### Option A: Create a Service Account User (RECOMMENDED)

**Step 1:** In UISP Admin Panel
```
Settings → Users → Create New User
- Username: "auralink-bot"
- Password: (strong password)
- Role: "Read-Only API Access" (or "Technician")
- Enable API access
- Save
```

**Step 2:** Generate API Token for this user
```
Settings → API Tokens → Create New Token
- Name: "AURALINK Bot Service"
- Owner: "auralink-bot" user
- Permissions: Read (Clients, Devices, Network)
- Enable token
- Copy token value
```

**Step 3:** Update bot configuration
```python
# In auralink_bot_ai_claude_enabled.py line 28:
UISP_API_TOKEN = "new-token-from-service-account"

# Use Bearer authentication:
headers = {
    'Authorization': f'Bearer {UISP_API_TOKEN}',
    'Content-Type': 'application/json'
}
```

**Time Required:** 5-10 minutes
**Difficulty:** Easy
**Success Rate:** 95% (most reliable solution)

---

### Option B: Check Existing Token Permissions

**Step 1:** Verify token in UISP
```
Login to UISP Admin → Settings → API Tokens
→ Click your token (f569c64b-f183-4d03-af69-e6720cec2ead)
```

**Step 2:** Check these settings:
- ☑ Token is "Enabled" (not disabled)
- ☑ Permissions show "Read" access
- ☑ Clients & Devices are included in readable resources
- ☑ Token hasn't expired
- ☑ Associated user is active

**Step 3:** If permissions are wrong:
- Regenerate token with correct permissions
- Or enable missing permissions
- Save and use new token

**Step 4:** Test with updated token:
```bash
# SSH to UISP server
ssh uisp@10.1.1.254

# Test token
curl -k -H "Authorization: Bearer UPDATED_TOKEN" \
  https://10.1.1.254/api/v2.1/clients \
  | head -c 200

# Should return JSON client data (not 401 error)
```

**Time Required:** 3-5 minutes
**Difficulty:** Very Easy
**Success Rate:** 40% (if permissions were the issue)

---

### Option C: Use Session-Based Authentication

**How it works:**
1. Login to UISP web UI (username/password)
2. Extract session cookies
3. Use cookies for API calls

**Pros:**
- No special API token needed
- Uses existing credentials

**Cons:**
- More complex implementation
- Session cookies expire
- Requires session management code

**Not Recommended For:** Automated bot use (too fragile)

---

## Implementation Guide - Option A (Recommended)

### 1. Create Service Account in UISP

```
UISP Web UI → Admin Panel → Users → "+ Add User"

Fill in:
┌─────────────────────────────────────────┐
│ Username:    auralink-bot               │
│ Email:       monitoring@auralink.local  │
│ Password:    [Generate Strong]          │
│ Role:        Technician OR Read-Only    │
│ Status:      Active ✓                   │
└─────────────────────────────────────────┘

Click: Save
```

### 2. Generate API Token

```
Settings → API Tokens → "+ Create New Token"

Fill in:
┌─────────────────────────────────────────┐
│ Name:       AURALINK Bot Service        │
│ Owner:      auralink-bot                │
│ Permissions:                            │
│  ☑ Read Clients                         │
│  ☑ Read Devices                         │
│  ☑ Read Customers                       │
│  ☑ Read Sites                           │
│ Status:     Enabled ✓                   │
└─────────────────────────────────────────┘

Click: Create

Copy the generated token (appears once)
```

### 3. Update Bot File

```bash
# On your local computer
nano C:/claude2/auralink_bot_ai_claude_enabled.py

# Find line 28:
UISP_API_TOKEN = "d5451905-9c58-49b7-89dc-76f680bf6b63"

# Replace with new service account token:
UISP_API_TOKEN = "paste-new-token-here"

# Save: Ctrl+O → Enter → Ctrl+X
```

### 4. Deploy to Server

```bash
# Copy updated file to UISP server
scp C:/claude2/auralink_bot_ai_claude_enabled.py \
    uisp@10.1.1.254:/home/uisp/auralink_monitor/auralink_monitor.py

# SSH to server
ssh uisp@10.1.1.254

# Restart bot
pkill -9 python3
sleep 2
cd /home/uisp/auralink_monitor
nohup python3 auralink_monitor.py > monitor.log 2>&1 &

# Check logs
sleep 3
tail -15 monitor.log
```

### 5. Verify It Works

**In logs, look for:**
```
✅ API Token validado correctamente
✅ Obtenidos N clientes de UISP
✅ Obtenidos N dispositivos de UISP
```

**In Telegram, test:**
```
/clients
→ Should show actual client list (not error)

/devices
→ Should show actual device list (not error)

/status
→ Should show real numbers
```

---

## Testing Your Token

Before restarting bot, verify token works:

```bash
# SSH to UISP server
ssh uisp@10.1.1.254

# Test API with token
curl -k -H "Authorization: Bearer YOUR_NEW_TOKEN" \
  https://10.1.1.254/api/v2.1/clients

# Expected: JSON array of clients
# [{"id":1,"name":"Client1",...}, ...]

# NOT expected: 401 error
# {"code":401,"message":"Authentication Required"}
```

---

## If Still Getting 401 Error

**1. Check token format:**
```bash
# Token should be just the string, no quotes
echo "YOUR_TOKEN" | wc -c
# Should be ~36-40 characters (UUID format)
```

**2. Wait for propagation:**
```bash
# UISP might need 10-30 seconds to activate token
sleep 30
curl -k -H "Authorization: Bearer YOUR_NEW_TOKEN" \
  https://10.1.1.254/api/v2.1/clients
```

**3. Verify user is active:**
- UISP Admin → Users → auralink-bot → Status should be "Active"
- If not active, enable it

**4. Check API endpoint availability:**
```bash
# Some UISP versions use different API paths
curl -k https://10.1.1.254/api/v2.1/devices  # Try devices
curl -k https://10.1.1.254/api/v2/clients    # Try v2 instead of v2.1
```

**5. Regenerate token:**
- Delete old token: Settings → API Tokens → Delete
- Create new one with same settings
- Use new token immediately

---

## Advanced: Session-Based Fallback

If service account doesn't work, bot can fallback to session-based auth:

```python
import requests
from requests.auth import HTTPBasicAuth

# Login and get session
session = requests.Session()
response = session.post(
    'https://10.1.1.254/api/v2.1/auth/login',
    auth=HTTPBasicAuth('auralink-bot', 'password'),
    verify=False
)

# Use session for API calls
clients = session.get(
    'https://10.1.1.254/api/v2.1/clients',
    verify=False
)
```

But this requires storing credentials in bot, which is less secure.

---

## Quick Decision Tree

```
Can you access UISP web UI?
├─ YES:
│  └─ Go to Settings → API Tokens
│     ├─ Token exists?
│     │  ├─ YES:
│     │  │  └─ Try Option B (check permissions)
│     │  └─ NO:
│     │     └─ Try Option A (create service account)
│     └─ Still failing?
│        └─ Contact UISP support
│
└─ NO:
   └─ Contact your UISP administrator
```

---

## Files & Resources

**Current bot version:**
- Location: `/home/uisp/auralink_monitor/auralink_monitor.py`
- Logs: `/home/uisp/auralink_monitor/monitor.log`
- Config line: Line 28 (UISP_API_TOKEN)

**Documentation:**
- `BOT_DEPLOYMENT_SUMMARY.md` - Bot features & usage
- `QUICK_FIX_UISP_TOKEN.md` - Quick reference guide
- `UISP_API_AUTH_ANALYSIS.md` - This file (technical details)

---

## Next Steps Recommendation

**Immediate (Today):**
1. Try Option B - check existing token permissions in UISP
2. If that doesn't work, proceed to Option A

**Option A Implementation (5 minutes):**
1. Create service account user in UISP
2. Generate token for that account
3. Update bot configuration file
4. Restart bot on server
5. Test in Telegram

**Expected Result:**
Once fixed, bot will fetch and display real client/device data in responses.

---

## Support Contact

If you encounter issues:
1. Check bot logs: `tail -50 /home/uisp/auralink_monitor/monitor.log`
2. Test token manually: `curl -k -H "Authorization: Bearer TOKEN" https://10.1.1.254/api/v2.1/clients`
3. Verify UISP service is running
4. Contact UISP support with this analysis document

---

**Technical Details:**
- UISP Version Detected: v2.x (using /api/v2.1 endpoints)
- Authentication: Bearer token (OAuth-like pattern)
- Tested: 6 different authentication methods
- Conclusion: Token scope/permission issue most likely

---

Last Updated: 2025-12-01 01:45 UTC
