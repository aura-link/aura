#!/bin/bash
# Restart udapi-bridge on all fixed antennas + fix remaining 2
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa -o BatchMode=no"
CORRECT_URI="wss://server.auralink.link:443+sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV+allowUntrustedCertificate"

IPS="10.10.1.95 10.10.1.67 10.10.1.249 10.10.1.98 10.10.1.88 10.10.1.216 10.10.1.160 10.10.1.86 10.10.1.159 10.10.1.149 10.10.1.245 10.10.1.194 10.10.1.162 10.10.1.169 10.10.1.112 10.10.1.226 10.10.1.62 10.10.1.124"

FIXED=0; FAILED=0; TOTAL=0

for IP in $IPS; do
    TOTAL=$((TOTAL + 1))
    DONE=0
    for CRED in "AURALINK:Auralink2021" "ubnt:Auralink2021" "ubnt:Casimposible*7719Varce*1010"; do
        USER="${CRED%%:*}"
        PASS="${CRED#*:}"

        RESULT=$(sshpass -p "$PASS" ssh $SSH_OPTS ${USER}@${IP} "
            # Ensure correct URI
            CURRENT=\$(grep 'unms.uri=' /tmp/system.cfg 2>/dev/null)
            if ! echo \"\$CURRENT\" | grep -q 'sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV.*allowUntrustedCertificate'; then
                sed -i 's|unms.uri=.*|unms.uri=$CORRECT_URI|' /tmp/system.cfg
                cfgmtd -w -p /etc/ 2>/dev/null
            fi
            rm -f /tmp/running.cfg
            # Kill udapi-bridge child to force re-read
            CHILD=\$(ps | grep 'udapi-bridge' | grep -v grep | grep -v supervise | awk '{print \$1}' | head -1)
            if [ -n \"\$CHILD\" ]; then
                kill -9 \$CHILD 2>/dev/null
                echo RESTARTED
            else
                echo NO_PROC
            fi
        " 2>/dev/null)

        if echo "$RESULT" | grep -q "RESTARTED\|NO_PROC"; then
            FIXED=$((FIXED+1))
            echo "[$TOTAL] $IP: $RESULT ($USER)"
            DONE=1
            break
        fi
    done
    [ "$DONE" -eq 0 ] && { FAILED=$((FAILED+1)); echo "[$TOTAL] $IP: FAIL"; }
done

echo ""
echo "=== RESULTADO: Total=$TOTAL OK=$FIXED Failed=$FAILED ==="
