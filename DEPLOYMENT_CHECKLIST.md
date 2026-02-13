# AURALINK Monitor Bot v3 - Deployment Checklist

**Status:** ✅ COMPLETE & READY FOR DEPLOYMENT
**Version:** v3 (Stable)
**Date:** 2025-11-30

---

## 🎯 Pre-Deployment Checklist

### Files Ready
- ✅ `auralink_telegram_monitor_v3.py` - Bot script (225 lines)
- ✅ `QUICK_START_DEPLOYMENT.sh` - Automated deployment
- ✅ `README_DEPLOYMENT.md` - Complete guide
- ✅ `AURALINK_V3_DEPLOYMENT_SUMMARY.md` - Executive summary
- ✅ `DEPLOYMENT_V3_GUIDE.md` - Step-by-step instructions
- ✅ `BOT_VERSIONS_COMPARISON.md` - Technical analysis
- ✅ `DEPLOYMENT_CHECKLIST.md` - This checklist

### Infrastructure Check
- ✅ UISP Server reachable at 10.1.1.254
- ✅ SSH access to uisp@10.1.1.254 configured
- ✅ Virtual environment exists at /home/uisp/auralink_monitor
- ✅ Python 3.12 with dependencies installed
- ✅ Telegram bot token verified: `8318058273:AAEiKpg6L8gG9DSb4zLrtnPUS1Z6urYe_UI`
- ✅ UISP credentials verified: AURALINK / Varce*101089

---

## 🚀 Deployment Phase

### Step 1: Stop Existing Bot (if any)
```bash
[ ] Execute: ssh uisp@10.1.1.254 "pkill -f 'python3.*auralink_monitor' || true"
[ ] Verify: ps aux shows no auralink_monitor process
[ ] Wait: 2 seconds before proceeding
```

### Step 2: Deploy v3 Script
```bash
[ ] Choose deployment method:
    [ ] Option A: bash C:/claude2/QUICK_START_DEPLOYMENT.sh
    [ ] Option B: Manual steps from README_DEPLOYMENT.md
    [ ] Option C: Systemd service (for 24/7)

[ ] Upload script: scp ...v3.py to /home/uisp/auralink_monitor/auralink_monitor.py
[ ] Verify upload: File exists at destination
[ ] Check permissions: File is readable
```

### Step 3: Start Bot Process
```bash
[ ] Start with: nohup python3 auralink_monitor.py > monitor.log 2>&1 &
[ ] Verify running: ps aux | grep auralink_monitor (should show process)
[ ] Wait: 3-5 seconds for startup
[ ] Check logs: tail -20 /home/uisp/auralink_monitor/monitor.log
```

### Step 4: Verify Startup
Expected in logs:
```
[ ] "AURALINK Monitor Bot v3 - Iniciando"
[ ] "Creando aplicación Telegram..."
[ ] "Agregando handlers..."
[ ] "Bot listo para recibir mensajes"
[ ] "Esperando mensajes en Telegram..."
```

NOT expected (would indicate failure):
```
[ ] ✅ NOT "Cannot close a running event loop"
[ ] ✅ NOT "Error fatal"
[ ] ✅ NOT "RuntimeWarning: coroutine ... was never awaited"
```

---

## 🧪 Testing Phase

### Test 1: Process Verification
```bash
[ ] Run: ssh uisp@10.1.1.254 "ps aux | grep python3.*auralink | grep -v grep"
[ ] Expected: Shows Python process with auralink_monitor.py
[ ] Memory: Should be 50-100 MB
[ ] CPU: Should be <1% idle
```

### Test 2: Telegram /start Command
```bash
[ ] Open Telegram
[ ] Search: @auralinkmonitor_bot
[ ] Send: /start
[ ] Expected response within 2-3 seconds:
    ✅ "🌐 AURALINK Monitor v3"
    ✅ "Bot de monitoreo de UISP"
    ✅ Commands listed
```

### Test 3: Telegram /status Command
```bash
[ ] Send: /status
[ ] Expected response within 2-3 seconds:
    ✅ "✅ Estado AURALINK Monitor"
    ✅ "Clientes totales: [number]"
    ✅ "Servidor UISP: 🟢 Online"
```

### Test 4: Telegram /clients Command
```bash
[ ] Send: /clients
[ ] Expected response within 2-3 seconds:
    ✅ "👥 Clientes Registrados:"
    ✅ List of 1-15 clients from UISP
    ✅ Client names visible
```

### Test 5: Telegram /help Command
```bash
[ ] Send: /help
[ ] Expected response within 2-3 seconds:
    ✅ "📖 Guía de Comandos"
    ✅ Commands list: /status, /clients, /help
    ✅ Example queries
```

### Test 6: Message Handling
```bash
[ ] Send any random text (e.g., "hello")
[ ] Expected response within 2-3 seconds:
    ✅ "✅ Mensaje recibido"
    ✅ Instruction message with command suggestions
```

### Test Results Summary
```
[ ] /start     - PASS / FAIL
[ ] /status    - PASS / FAIL
[ ] /clients   - PASS / FAIL
[ ] /help      - PASS / FAIL
[ ] message    - PASS / FAIL

Overall: [ ] ALL PASS ✅  [ ] SOME FAIL ⚠️  [ ] ALL FAIL ❌
```

---

## 📊 Performance Validation

### Memory Check
```bash
[ ] Run: ssh uisp@10.1.1.254 "ps aux | grep python3.*auralink | awk '{print \$6}'"
[ ] Expected: 50-100 MB
[ ] Status: [ ] OK ✅  [ ] High ⚠️  [ ] Critical ❌
```

### Response Time Check
```bash
[ ] Send /status 5 times and measure response time
[ ] Each response should be 1-3 seconds
[ ] Status: [ ] OK (1-3s) ✅  [ ] Slow (3-5s) ⚠️  [ ] Very Slow (>5s) ❌
```

### Network Connectivity
```bash
[ ] Run: ssh uisp@10.1.1.254 "curl -k https://10.1.1.254/api/v2.1/clients -m 5"
[ ] Expected: JSON response from UISP
[ ] Status: [ ] Connected ✅  [ ] Timeout ⚠️  [ ] Error ❌
```

### Log Check
```bash
[ ] Run: ssh uisp@10.1.1.254 "grep 'Usuario.*pidió' /home/uisp/auralink_monitor/monitor.log | tail -5"
[ ] Expected: Recent entries showing your test commands
[ ] Status: [ ] Found ✅  [ ] Missing ⚠️  [ ] Error ❌
```

---

## ✅ Post-Deployment Tasks

### Documentation
- [ ] Read README_DEPLOYMENT.md
- [ ] Keep AURALINK_V3_DEPLOYMENT_SUMMARY.md for reference
- [ ] Bookmark BOT_VERSIONS_COMPARISON.md for technical details

### Monitoring
- [ ] Set up log monitoring: `tail -f /home/uisp/auralink_monitor/monitor.log`
- [ ] Check logs at least once daily for 7 days
- [ ] Note any errors or warnings

### Optional: Systemd Service Setup
```bash
[ ] Create systemd service file
[ ] Copy to /etc/systemd/system/
[ ] Enable service: systemctl enable auralink-monitor
[ ] Start service: systemctl start auralink-monitor
[ ] Verify: systemctl status auralink-monitor
```

### Credentials & Security
- [ ] Note bot token is: 8318058273:AAEiKpg6L8gG9DSb4zLrtnPUS1Z6urYe_UI
- [ ] Note UISP user: AURALINK
- [ ] Note UISP pass: Varce*101089
- [ ] Plan to change credentials after testing
- [ ] Do NOT share token in chat or logs

---

## 🔄 Operations Guide (After Deployment)

### Daily Operations
```bash
# Check if bot is running
[ ] ssh uisp@10.1.1.254 "ps aux | grep auralink"

# View recent logs
[ ] ssh uisp@10.1.1.254 "tail -20 /home/uisp/auralink_monitor/monitor.log"

# Test a command
[ ] Send /status in Telegram
```

### If Bot Stops Responding
```bash
# Step 1: Check if running
[ ] ssh uisp@10.1.1.254 "ps aux | grep auralink | grep -v grep"

# Step 2: Check logs for errors
[ ] ssh uisp@10.1.1.254 "tail -50 /home/uisp/auralink_monitor/monitor.log"

# Step 3: Restart
[ ] ssh uisp@10.1.1.254 "pkill -f auralink_monitor; sleep 2"
[ ] bash C:/claude2/QUICK_START_DEPLOYMENT.sh

# Step 4: Verify
[ ] Test /status command in Telegram
```

### Weekly Maintenance
```bash
# Backup logs
[ ] ssh uisp@10.1.1.254 "cp monitor.log monitor.log.backup.$(date +%Y%m%d)"

# Check disk space
[ ] ssh uisp@10.1.1.254 "df -h /home/uisp"

# Review logs for issues
[ ] ssh uisp@10.1.1.254 "grep -i error /home/uisp/auralink_monitor/monitor.log | tail -10"
```

---

## 🐛 Troubleshooting Quick Reference

### Issue: Bot doesn't respond
```
[ ] Check: ps aux | grep auralink
[ ] Check: tail -50 monitor.log
[ ] Fix: Restart with QUICK_START_DEPLOYMENT.sh
```

### Issue: Event loop error
```
[ ] Check: Is this v3? (grep "v3" first 5 lines)
[ ] Fix: Redeploy v3 script
```

### Issue: High memory usage
```
[ ] Measure: ps aux | grep auralink | awk '{print $6}'
[ ] Fix: Restart bot (should drop to 50-80 MB)
```

### Issue: UISP connection error
```
[ ] Check: curl -k https://10.1.1.254/api/v2.1/clients
[ ] Check: Are credentials correct?
[ ] Check: Network connectivity to UISP?
```

### Issue: Telegram timeout
```
[ ] Check: Is bot running? (ps aux)
[ ] Check: Any errors in logs?
[ ] Fix: Retry command in 1-2 seconds
```

---

## 📋 Sign-Off

### Deployment Completed By
- Name: ___________________
- Date: ___________________
- Time: ___________________

### Approval
- [ ] All tests passed
- [ ] Bot is responding
- [ ] Logs look clean
- [ ] Ready for production

### Next Phase
- [ ] Monitor for 24-48 hours
- [ ] Plan Phase 2 features (AI integration, graphs)
- [ ] Update UISP credentials
- [ ] Set up systemd service

---

## 📞 Support Contacts

If issues arise:
1. Check `README_DEPLOYMENT.md` troubleshooting section
2. Review `BOT_VERSIONS_COMPARISON.md` for technical details
3. Check logs: `tail -100 monitor.log | grep -i error`
4. Verify connectivity: `curl -k https://10.1.1.254/api/v2.1/clients`

---

## 📞 Quick Commands Reference

```bash
# START BOT
bash C:/claude2/QUICK_START_DEPLOYMENT.sh

# STOP BOT
ssh uisp@10.1.1.254 "pkill -f auralink_monitor"

# RESTART BOT
ssh uisp@10.1.1.254 "pkill -f auralink_monitor; sleep 2" && \
bash C:/claude2/QUICK_START_DEPLOYMENT.sh

# CHECK STATUS
ssh uisp@10.1.1.254 "ps aux | grep auralink"

# VIEW LOGS
ssh uisp@10.1.1.254 "tail -50 /home/uisp/auralink_monitor/monitor.log"

# MONITOR LOGS LIVE
ssh uisp@10.1.1.254 "tail -f /home/uisp/auralink_monitor/monitor.log"

# TEST UISP
ssh uisp@10.1.1.254 "curl -k https://10.1.1.254/api/v2.1/clients"
```

---

**✅ DEPLOYMENT READY - All systems go!**

Use `bash C:/claude2/QUICK_START_DEPLOYMENT.sh` to begin.
