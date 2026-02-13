# AURALINK Monitor Bot v3 - Deployment Guide

## Status: READY FOR DEPLOYMENT

The v3 bot has been created with improvements to handle the asyncio event loop issues that were crashing v1.

### Key Improvements in v3:
- ✅ Better asyncio event loop handling
- ✅ Proper signal handlers for clean shutdown
- ✅ Simplified code structure to avoid event loop conflicts
- ✅ Same core functionality as v2 but more robust

---

## Quick Deployment Steps

### Step 1: Stop any running bot process
```bash
ssh uisp@10.1.1.254 "pkill -f 'python3.*auralink_monitor' || true; sleep 2"
```

### Step 2: Upload v3 script to server
```bash
scp -o StrictHostKeyChecking=no C:/claude2/auralink_telegram_monitor_v3.py uisp@10.1.1.254:/home/uisp/auralink_monitor/auralink_monitor.py
```

### Step 3: Start bot in background (no timeout)
```bash
ssh -o StrictHostKeyChecking=no uisp@10.1.1.254 "cd /home/uisp/auralink_monitor && source bin/activate && nohup python3 auralink_monitor.py > monitor.log 2>&1 &"
```

### Step 4: Verify it's running
```bash
ssh -o StrictHostKeyChecking=no uisp@10.1.1.254 "sleep 2 && ps aux | grep 'python3.*auralink_monitor' | grep -v grep"
```

### Step 5: Check logs
```bash
ssh -o StrictHostKeyChecking=no uisp@10.1.1.254 "tail -20 /home/uisp/auralink_monitor/monitor.log"
```

---

## Testing in Telegram

1. Open Telegram and search for **@auralinkmonitor_bot**
2. Send `/start` - should get welcome message
3. Send `/status` - should get system statistics
4. Send `/clients` - should list clients from UISP
5. Send `/help` - should get help message

**Expected response time:** 1-3 seconds

---

## Troubleshooting

### If bot doesn't respond:
1. Check if process is running:
   ```bash
   ssh uisp@10.1.1.254 "ps aux | grep auralink"
   ```

2. Check logs for errors:
   ```bash
   ssh uisp@10.1.1.254 "tail -50 /home/uisp/auralink_monitor/monitor.log"
   ```

3. Restart bot:
   ```bash
   ssh uisp@10.1.1.254 "pkill -f auralink_monitor; sleep 1; source /home/uisp/auralink_monitor/bin/activate && nohup python3 /home/uisp/auralink_monitor/auralink_monitor.py > /home/uisp/auralink_monitor/monitor.log 2>&1 &"
   ```

### Common Issues:

| Issue | Solution |
|-------|----------|
| "Cannot close a running event loop" | Caused by timeout in v1. v3 fixes this. |
| Bot doesn't respond to commands | Check if process is running with `ps aux` |
| UISP connection 404 | Normal - bot continues without token, still works |
| Telegram timeout | Bot may be busy - wait and retry |

---

## System Service Setup (Optional - for 24/7 operation)

If you want the bot to auto-start and restart on failure, create a systemd service:

```bash
sudo bash -c 'cat > /etc/systemd/system/auralink-monitor.service << EOF
[Unit]
Description=AURALINK Monitor Bot v3
After=network.target

[Service]
Type=simple
User=uisp
WorkingDirectory=/home/uisp/auralink_monitor
ExecStart=/home/uisp/auralink_monitor/bin/python3 /home/uisp/auralink_monitor/auralink_monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF'

sudo systemctl daemon-reload
sudo systemctl enable auralink-monitor.service
sudo systemctl start auralink-monitor.service
```

Check status:
```bash
sudo systemctl status auralink-monitor.service
```

View logs:
```bash
sudo journalctl -u auralink-monitor -f
```

---

## Files Location

- **Bot script:** `/home/uisp/auralink_monitor/auralink_monitor.py` (v3)
- **Virtual environment:** `/home/uisp/auralink_monitor/bin/`
- **Logs:** `/home/uisp/auralink_monitor/monitor.log`
- **Dependencies:** python-telegram-bot, requests, matplotlib, pandas, plotly

---

## Next Phase Features (v4+)

- [ ] Claude AI integration for smart responses
- [ ] Real-time graphs of bandwidth consumption
- [ ] Automatic alerts for high CPU/RAM
- [ ] Daily/weekly reports
- [ ] Client-specific statistics
- [ ] Device management commands

---

## Notes

- The bot is stateless - no database needed
- All data is fetched live from UISP
- Logs are preserved in monitor.log
- Bot will run continuously until stopped
- SSH key authentication is configured to skip host checking
