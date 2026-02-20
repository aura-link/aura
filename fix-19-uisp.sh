#!/bin/bash
# Configure UISP connection string on antennas without UISP entry
# These are CRM clients with PPPoE but no NMS endpoint
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=8 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa"
URI="wss://server.auralink.link:443+sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV+allowUntrustedCertificate"

CREDS=("AURALINK:Auralink2021" "ubnt:Auralink2021" "ubnt:Casimposible*7719Varce*1010")

IPS=(10.10.1.119 10.10.1.84 10.10.1.143 10.10.1.124)
NAMES=("novedadestomatlan" "mariacristinamoralesc" "uriellarat" "grupomorant")

FIXED=0; ALREADY=0; FAILED=0; TOTAL=${#IPS[@]}

echo "Configure UISP on $TOTAL antennas (CRM clients without NMS endpoint)"
echo "======================================================================"

for IDX in "${!IPS[@]}"; do
    IP="${IPS[$IDX]}"
    NAME="${NAMES[$IDX]}"
    echo -n "[$IP] ($NAME) "
    CONNECTED=0
    for CRED in "${CREDS[@]}"; do
        USER="${CRED%%:*}"; PASS="${CRED#*:}"

        RESULT=$(sshpass -p "$PASS" ssh $SSH_OPTS "$USER@$IP" '
            CURRENT=$(grep "^unms.uri=" /tmp/system.cfg 2>/dev/null | head -1 | cut -d= -f2-)
            if [ -z "$CURRENT" ]; then
                echo "STATUS=missing"
            elif echo "$CURRENT" | grep -q "server.auralink.link.*allowUntrustedCertificate"; then
                echo "STATUS=ok"
            else
                echo "STATUS=wrong"
            fi
        ' 2>/dev/null)

        if [ $? -eq 0 ] && [ -n "$RESULT" ]; then
            CONNECTED=1
            STATUS=$(echo "$RESULT" | grep -o 'STATUS=[^ ]*' | cut -d= -f2)

            if [ "$STATUS" = "ok" ]; then
                # Already configured, just restart udapi-bridge
                sshpass -p "$PASS" ssh $SSH_OPTS "$USER@$IP" '
                    rm -f /tmp/running.cfg
                    cp /tmp/system.cfg /tmp/running.cfg
                    killall -9 udapi-bridge 2>/dev/null
                ' 2>/dev/null
                ALREADY=$((ALREADY + 1))
                echo "already configured, restarted udapi (user=$USER)"
            else
                # Configure URI
                sshpass -p "$PASS" ssh $SSH_OPTS "$USER@$IP" "
                    grep -v '^unms\.' /tmp/system.cfg > /tmp/system.cfg.new
                    echo 'unms.uri=$URI' >> /tmp/system.cfg.new
                    echo 'unms.status=enabled' >> /tmp/system.cfg.new
                    cp /tmp/system.cfg.new /tmp/system.cfg
                    rm /tmp/system.cfg.new
                    cfgmtd -w -p /etc/
                    rm -f /tmp/running.cfg
                    cp /tmp/system.cfg /tmp/running.cfg
                    killall -9 udapi-bridge 2>/dev/null
                " 2>/dev/null
                FIXED=$((FIXED + 1))
                echo "CONFIGURED (was: $STATUS, user=$USER)"
            fi
            break
        fi
    done

    [ $CONNECTED -eq 0 ] && { FAILED=$((FAILED + 1)); echo "FAILED (unreachable)"; }
    sleep 0.5
done

echo ""
echo "======================================================================"
echo "RESULTS:"
echo "  Configured:      $FIXED"
echo "  Already OK:      $ALREADY"
echo "  Failed:          $FAILED"
echo "  Total:           $TOTAL"
echo "======================================================================"
