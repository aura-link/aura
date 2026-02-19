#!/bin/bash
# Configure UISP connection string on 27 Ubiquiti antennas that have PPPoE but no UISP entry
# These antennas either never had the connection string or had it wrong
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=8 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa"
URI="wss://server.auralink.link:443+sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV+allowUntrustedCertificate"

CREDS=("AURALINK:Auralink2021" "ubnt:Auralink2021" "ubnt:Casimposible*7719Varce*1010")

IPS=(
    10.10.1.101 10.10.1.119 10.10.1.124 10.10.1.131 10.10.1.133
    10.10.1.134 10.10.1.143 10.10.1.147 10.10.1.154 10.10.1.159
    10.10.1.161 10.10.1.184 10.10.1.191 10.10.1.217 10.10.1.218
    10.10.1.222 10.10.1.226 10.10.1.247 10.10.1.252 10.10.1.52
    10.10.1.54  10.10.1.55  10.10.1.60  10.10.1.75  10.10.1.84
    10.10.1.86  10.10.1.96
)

FIXED=0; ALREADY=0; FAILED=0; TOTAL=${#IPS[@]}

echo "Configure UISP on $TOTAL Ubiquiti antennas"
echo "============================================"

for IP in "${IPS[@]}"; do
    echo -n "[$IP] "
    CONNECTED=0
    for CRED in "${CREDS[@]}"; do
        USER="${CRED%%:*}"; PASS="${CRED#*:}"

        RESULT=$(sshpass -p "$PASS" ssh $SSH_OPTS "$USER@$IP" '
            # Check current URI
            CURRENT=$(grep "^unms.uri=" /tmp/system.cfg 2>/dev/null | head -1 | cut -d= -f2-)
            if [ -z "$CURRENT" ]; then
                echo "STATUS=missing"
            elif echo "$CURRENT" | grep -q "server.auralink.link.*allowUntrustedCertificate"; then
                echo "STATUS=ok"
            else
                echo "STATUS=wrong CURRENT=$CURRENT"
            fi
        ' 2>/dev/null)

        if [ $? -eq 0 ] && [ -n "$RESULT" ]; then
            CONNECTED=1
            STATUS=$(echo "$RESULT" | grep -o 'STATUS=[^ ]*' | cut -d= -f2)

            if [ "$STATUS" = "ok" ]; then
                # Already has correct URI, just restart udapi-bridge
                sshpass -p "$PASS" ssh $SSH_OPTS "$USER@$IP" '
                    rm -f /tmp/running.cfg
                    PID=$(ps | grep "udapi-bridge" | grep -v grep | grep -v supervise | tail -1 | awk "{print \$1}")
                    [ -n "$PID" ] && kill -9 $PID
                ' 2>/dev/null
                ALREADY=$((ALREADY + 1))
                echo "already configured, restarted udapi (user=$USER)"
            else
                # Need to configure URI
                sshpass -p "$PASS" ssh $SSH_OPTS "$USER@$IP" "
                    # Remove old unms lines
                    grep -v '^unms\.' /tmp/system.cfg > /tmp/system.cfg.new
                    echo 'unms.uri=$URI' >> /tmp/system.cfg.new
                    echo 'unms.status=enabled' >> /tmp/system.cfg.new
                    cp /tmp/system.cfg.new /tmp/system.cfg
                    rm /tmp/system.cfg.new
                    # Save to flash
                    cfgmtd -w -p /etc/
                    # Restart udapi-bridge
                    PID=\$(ps | grep 'udapi-bridge' | grep -v grep | grep -v supervise | tail -1 | awk '{print \$1}')
                    [ -n \"\$PID\" ] && kill -9 \$PID
                " 2>/dev/null
                FIXED=$((FIXED + 1))
                echo "CONFIGURED (was: $STATUS, user=$USER)"
            fi
            break
        fi
    done

    [ $CONNECTED -eq 0 ] && { FAILED=$((FAILED + 1)); echo "FAILED (unreachable)"; }
    sleep 0.3
done

echo ""
echo "============================================"
echo "RESULTS:"
echo "  Configured:      $FIXED"
echo "  Already OK:      $ALREADY"
echo "  Failed:          $FAILED"
echo "  Total:           $TOTAL"
echo "============================================"
