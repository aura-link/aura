#!/bin/bash
# Test encryption reset on single antenna 10.10.1.95 (veronicagonzalest)
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa -o BatchMode=no"
IP="10.10.1.95"
USER="AURALINK"
PASS="Auralink2021"

echo "=== Testing encryption reset on $IP ==="

echo "[1] Current UISP config:"
sshpass -p "$PASS" ssh $SSH_OPTS ${USER}@${IP} 'grep unms /tmp/system.cfg' 2>/dev/null

echo "[2] Disabling UISP..."
sshpass -p "$PASS" ssh $SSH_OPTS ${USER}@${IP} '
    sed -i "s/unms.status=enabled/unms.status=disabled/" /tmp/system.cfg
    cfgmtd -w -p /etc/ 2>/dev/null
    CHILD=$(ps | grep "udapi-bridge" | grep -v grep | grep -v supervise | awk "{print \$1}" | head -1)
    [ -n "$CHILD" ] && kill -9 $CHILD 2>/dev/null
    echo "Done"
' 2>/dev/null

echo "[3] Waiting 5 seconds..."
sleep 5

echo "[4] Re-enabling UISP..."
sshpass -p "$PASS" ssh $SSH_OPTS ${USER}@${IP} '
    rm -f /tmp/running.cfg
    sed -i "s/unms.status=disabled/unms.status=enabled/" /tmp/system.cfg
    cfgmtd -w -p /etc/ 2>/dev/null
    CHILD=$(ps | grep "udapi-bridge" | grep -v grep | grep -v supervise | awk "{print \$1}" | head -1)
    [ -n "$CHILD" ] && kill -9 $CHILD 2>/dev/null
    echo "Done"
' 2>/dev/null

echo "[5] Waiting 10 seconds for reconnection..."
sleep 10

echo "[6] Checking UISP config after reset:"
sshpass -p "$PASS" ssh $SSH_OPTS ${USER}@${IP} 'grep unms /tmp/system.cfg' 2>/dev/null

echo "[7] Checking udapi-bridge log:"
sshpass -p "$PASS" ssh $SSH_OPTS ${USER}@${IP} 'tail -10 /var/log/unms.log 2>/dev/null' 2>/dev/null

echo "=== Test complete ==="
