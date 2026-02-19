#!/bin/bash
# Nuclear fix for 10.10.1.53 (Jose Nicolas Mariscal)
# Clean ALL UISP config from system.cfg and start fresh
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa"

echo "=== Step 1: Delete stale DB entries ==="
docker exec unms-postgres psql -U postgres -d unms -c "DELETE FROM unms.device WHERE mac = '0c:ea:14:a8:c6:55';"

echo ""
echo "=== Step 2: Clean antenna system.cfg ==="
sshpass -p "Auralink2021" ssh $SSH_OPTS ubnt@10.10.1.53 << 'REMOTE'
echo "Before:"
grep -c unms /tmp/system.cfg
grep unms /tmp/system.cfg

# Remove ALL unms.* lines
grep -v '^unms\.' /tmp/system.cfg > /tmp/system.cfg.clean

# Add only the master key URI
echo "unms.uri=wss://server.auralink.link:443+sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV+allowUntrustedCertificate" >> /tmp/system.cfg.clean
echo "unms.status=enabled" >> /tmp/system.cfg.clean

# Replace
cp /tmp/system.cfg.clean /tmp/system.cfg
rm /tmp/system.cfg.clean

# Delete running.cfg
rm -f /tmp/running.cfg

# Save to flash
cfgmtd -w -p /etc/

echo ""
echo "After:"
grep unms /tmp/system.cfg

# Kill ALL udapi-bridge processes
echo ""
echo "Killing udapi-bridge..."
killall -9 udapi-bridge 2>/dev/null
sleep 2
echo "Processes after kill:"
ps | grep udapi
REMOTE

echo ""
echo "=== Step 3: Wait and check logs ==="
sleep 30
echo "Checking logs..."
for i in 1 2 3 4 5; do
    LOGS=$(docker logs app-device-ws-$i --since 30s 2>&1 | grep 'a8:c6:55')
    if [ -n "$LOGS" ]; then
        echo "ws-$i: $LOGS"
    fi
done

echo ""
echo "=== Step 4: DB check ==="
docker exec unms-postgres psql -U postgres -d unms -t -A -c "SELECT device_id, name, mac, ip, connected, authorized, key_exchange_status, failed_decryption FROM unms.device WHERE mac = '0c:ea:14:a8:c6:55';"

echo "=== Done ==="
