# Quick Fix: UISP API Token Issue

## The Problem
Bot says "No hay clientes registrados" → Token authentication is failing (401 error)

## The Solution (5 minutes)

### Step 1: Verify Token in UISP
```bash
# Open browser and go to:
https://10.1.1.254

# Login → Settings → API Tokens
# Look for: d5451905-9c58-49b7-89dc-76f680bf6b63
```

### Step 2: Check If Token Is Valid

The token should be:
- ✅ **Enabled** (toggle ON)
- ✅ **Has read permissions** for clients/devices
- ✅ **Not expired**
- ✅ **Assigned to active user**

### Step 3: If Token Is Invalid

Generate a new token:

```
UISP Admin → Settings → API Tokens → Create New Token
- Name: "AURALINK Bot API"
- Permissions: Read (Clients, Devices)
- Click: Create
- Copy: The new token value
```

### Step 4: Update Bot with New Token

**Option A: Direct SSH Update**
```bash
ssh uisp@10.1.1.254

# Edit the bot file
nano /home/uisp/auralink_monitor/auralink_monitor.py

# Find line 27:
UISP_API_TOKEN = "d5451905-9c58-49b7-89dc-76f680bf6b63"

# Replace with new token:
UISP_API_TOKEN = "YOUR_NEW_TOKEN_HERE"

# Save: Ctrl+O → Enter → Ctrl+X
```

**Option B: Update Local & Deploy**
```bash
# Edit on your computer:
nano C:/claude2/auralink_bot_ai_final.py

# Find line 27, replace token, save

# Deploy:
bash C:/claude2/QUICK_START_DEPLOYMENT.sh
```

### Step 5: Test Token

Before restarting bot, test the token:
```bash
# From any computer
curl -k -H "Authorization: Bearer YOUR_NEW_TOKEN" \
  https://10.1.1.254/api/v2.1/clients | head -20

# Should return: list of clients (not 401 error)
```

### Step 6: Restart Bot

```bash
# SSH to UISP server
ssh uisp@10.1.1.254

# Restart bot
pkill -f auralink_monitor
cd /home/uisp/auralink_monitor && source bin/activate && \
  nohup python3 auralink_monitor.py > monitor.log 2>&1 &

# Check logs
tail -20 monitor.log
```

### Step 7: Test in Telegram

Open Telegram and test:
```
@auralinkmonitor_bot
/start → Should show welcome

/clients → Should show client list (not error message)

/status → Should show real numbers (not all zeros)
```

---

## Troubleshooting

### Issue: Still getting 401 after token update

1. **Wait 10 seconds** - Token might need time to activate
2. **Check token format** - Copy full token exactly
3. **Verify token in UISP** - Make sure it's enabled
4. **Check file was saved** - Verify token in actual bot file:
   ```bash
   grep "UISP_API_TOKEN" /home/uisp/auralink_monitor/auralink_monitor.py
   ```

### Issue: Bot won't start after update

```bash
# Check for syntax errors
python3 -m py_compile /home/uisp/auralink_monitor/auralink_monitor.py

# View error details
python3 /home/uisp/auralink_monitor/auralink_monitor.py

# Check logs
tail -50 /home/uisp/auralink_monitor/monitor.log
```

---

## Current Status

**Bot Process:** ✅ Running
**Bot Response:** ✅ Working
**API Access:** ❌ Blocked (Invalid token)
**Time to Fix:** 5-10 minutes

---

## Key Commands Reference

| Task | Command |
|------|---------|
| View current token | `grep UISP_API_TOKEN /home/uisp/auralink_monitor/auralink_monitor.py` |
| Test token works | `curl -k -H "Authorization: Bearer TOKEN" https://10.1.1.254/api/v2.1/clients` |
| Check bot status | `ps aux \| grep auralink` |
| View logs | `tail -50 /home/uisp/auralink_monitor/monitor.log` |
| Restart bot | `pkill -f auralink_monitor && sleep 2 && cd /home/uisp/auralink_monitor && source bin/activate && nohup python3 auralink_monitor.py > monitor.log 2>&1 &` |
| Check bot is running | `curl https://api.telegram.org/bot8318058273:AAEiKpg6L8gG9DSb4zLrtnPUS1Z6urYe_UI/getMe` |

---

## What NOT to Do

- ❌ Don't delete the old token until new one works
- ❌ Don't use wrong token format (no "Bearer " prefix in the token value itself)
- ❌ Don't disable the bot while troubleshooting
- ❌ Don't forget to restart bot after token change

---

## Success Indicators

After fixing the token, you should see in logs:

```
✅ API Token validado correctamente
✅ Obtenidos N clientes de UISP
✅ Obtenidos N dispositivos de UISP
```

And in Telegram, `/clients` will show actual client data instead of error message.

---

**Need Help?** Check `API_TOKEN_DIAGNOSTIC_REPORT.md` for detailed analysis.
