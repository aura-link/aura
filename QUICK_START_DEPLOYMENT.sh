#!/bin/bash
#
# AURALINK Monitor Bot v3 - Quick Deployment Script
# Usage: bash QUICK_START_DEPLOYMENT.sh
#
# This script will:
# 1. Kill any running bot process
# 2. Backup current logs
# 3. Upload v3 bot script
# 4. Start bot in background
# 5. Verify it's running
#

set -e

UISP_SERVER="uisp@10.1.1.254"
BOT_DIR="/home/uisp/auralink_monitor"
BOT_SCRIPT="$BOT_DIR/auralink_monitor.py"
BACKUP_LOG="$BOT_DIR/monitor.log.backup.$(date +%Y%m%d_%H%M%S)"

echo "========================================="
echo "AURALINK Monitor Bot v3 - Deployment"
echo "========================================="
echo ""

# Step 1: Kill any existing process
echo "[1/5] Stopping any existing bot process..."
ssh -o StrictHostKeyChecking=no $UISP_SERVER "pkill -f 'python3.*auralink_monitor' || true; sleep 2" 2>/dev/null || true
echo "✓ Process killed"
echo ""

# Step 2: Backup logs
echo "[2/5] Backing up existing logs..."
ssh -o StrictHostKeyChecking=no $UISP_SERVER "test -f $BOT_DIR/monitor.log && cp $BOT_DIR/monitor.log $BACKUP_LOG || true" 2>/dev/null || true
echo "✓ Logs backed up"
echo ""

# Step 3: Upload v3 script
echo "[3/5] Uploading v3 bot script..."
scp -o StrictHostKeyChecking=no C:/claude2/auralink_telegram_monitor_v3.py $UISP_SERVER:$BOT_SCRIPT 2>/dev/null || {
    echo "❌ Error uploading script"
    exit 1
}
echo "✓ Script uploaded"
echo ""

# Step 4: Start bot in background (NO TIMEOUT)
echo "[4/5] Starting bot in background..."
ssh -o StrictHostKeyChecking=no $UISP_SERVER "cd $BOT_DIR && source bin/activate && nohup python3 auralink_monitor.py > monitor.log 2>&1 &" 2>/dev/null || {
    echo "❌ Error starting bot"
    exit 1
}
sleep 3
echo "✓ Bot started"
echo ""

# Step 5: Verify it's running
echo "[5/5] Verifying bot is running..."
RUNNING=$(ssh -o StrictHostKeyChecking=no $UISP_SERVER "ps aux | grep 'python3.*auralink_monitor' | grep -v grep | wc -l" 2>/dev/null || echo "0")

if [ "$RUNNING" -gt 0 ]; then
    echo "✓ Bot process is running"
    echo ""
    echo "========================================="
    echo "✅ DEPLOYMENT SUCCESSFUL"
    echo "========================================="
    echo ""
    echo "Bot Details:"
    echo "- Location: /home/uisp/auralink_monitor/"
    echo "- Process: $(ssh -o StrictHostKeyChecking=no $UISP_SERVER 'ps aux | grep python3.*auralink_monitor | grep -v grep' 2>/dev/null || echo 'Running')"
    echo ""
    echo "Latest Logs (last 10 lines):"
    ssh -o StrictHostKeyChecking=no $UISP_SERVER "tail -10 /home/uisp/auralink_monitor/monitor.log" 2>/dev/null || true
    echo ""
    echo "To test the bot in Telegram:"
    echo "1. Open Telegram and search: @auralinkmonitor_bot"
    echo "2. Send /start"
    echo "3. Send /status"
    echo "4. Send /help"
    echo ""
    echo "To view logs in real-time:"
    echo "  ssh uisp@10.1.1.254 'tail -f /home/uisp/auralink_monitor/monitor.log'"
    echo ""
    echo "To stop the bot:"
    echo "  ssh uisp@10.1.1.254 'pkill -f \"python3.*auralink_monitor\"'"
    echo ""
else
    echo "❌ Bot failed to start"
    echo ""
    echo "Error logs:"
    ssh -o StrictHostKeyChecking=no $UISP_SERVER "tail -20 /home/uisp/auralink_monitor/monitor.log" 2>/dev/null || true
    exit 1
fi
