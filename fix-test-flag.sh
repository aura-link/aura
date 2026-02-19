#!/bin/bash
# Test: change allowSelfSignedCertificate to allowUntrustedCertificate on 10.10.1.95
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa -o BatchMode=no"
IP="10.10.1.95"
USER="AURALINK"
PASS="Auralink2021"

echo "=== Testing connection string flag change on $IP ==="

echo "[1] Current config:"
sshpass -p "$PASS" ssh $SSH_OPTS ${USER}@${IP} 'grep unms /tmp/system.cfg' 2>/dev/null

echo "[2] Changing allowSelfSignedCertificate to allowUntrustedCertificate..."
sshpass -p "$PASS" ssh $SSH_OPTS ${USER}@${IP} '
    sed -i "s/allowSelfSignedCertificate/allowUntrustedCertificate/" /tmp/system.cfg
    rm -f /tmp/running.cfg
    cfgmtd -w -p /etc/ 2>/dev/null
    CHILD=$(ps | grep "udapi-bridge" | grep -v grep | grep -v supervise | awk "{print \$1}" | head -1)
    [ -n "$CHILD" ] && kill -9 $CHILD 2>/dev/null
    echo "DONE"
' 2>/dev/null

echo "[3] Waiting 15 seconds..."
sleep 15

echo "[4] New config:"
sshpass -p "$PASS" ssh $SSH_OPTS ${USER}@${IP} 'grep unms /tmp/system.cfg' 2>/dev/null

echo "[5] Log:"
sshpass -p "$PASS" ssh $SSH_OPTS ${USER}@${IP} 'tail -10 /var/log/unms.log 2>/dev/null' 2>/dev/null

echo "=== Done ==="
