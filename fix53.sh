#!/bin/bash
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa"
MASTER_URI="wss://server.auralink.link:443+sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV+allowUntrustedCertificate"

echo "=== Fix 10.10.1.53 (reset to master key) ==="
sshpass -p "Auralink2021" ssh $SSH_OPTS ubnt@10.10.1.53 << 'REMOTE'
grep -v 'unms.uri' /tmp/system.cfg > /tmp/system.cfg.new
echo "unms.uri=wss://server.auralink.link:443+sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV+allowUntrustedCertificate" >> /tmp/system.cfg.new
cp /tmp/system.cfg.new /tmp/system.cfg
rm /tmp/system.cfg.new
cfgmtd -w -p /etc/
sleep 1
echo "URI now:"
grep unms.uri /tmp/system.cfg
PID=$(ps | grep "udapi-bridge" | grep -v grep | grep -v supervise | tail -1 | awk '{print $1}')
if [ -n "$PID" ]; then
    kill -9 $PID
    echo "killed $PID"
fi
REMOTE

echo ""
echo "=== Fix 10.10.1.219 (Magda Mora) - retry with AURALINK ==="
sshpass -p "Auralink2021" ssh $SSH_OPTS AURALINK@10.10.1.219 << 'REMOTE2'
rm -f /tmp/running.cfg
PID=$(ps | grep "udapi-bridge" | grep -v grep | grep -v supervise | tail -1 | awk '{print $1}')
if [ -n "$PID" ]; then
    kill -9 $PID
    echo "killed $PID"
else
    echo "no udapi-bridge found"
fi
REMOTE2

if [ $? -ne 0 ]; then
    echo "AURALINK failed, trying ubnt..."
    sshpass -p "Auralink2021" ssh $SSH_OPTS ubnt@10.10.1.219 << 'REMOTE3'
rm -f /tmp/running.cfg
PID=$(ps | grep "udapi-bridge" | grep -v grep | grep -v supervise | tail -1 | awk '{print $1}')
if [ -n "$PID" ]; then
    kill -9 $PID
    echo "killed $PID"
else
    echo "no udapi-bridge found"
fi
REMOTE3
fi

echo ""
echo "=== Done ==="
