#!/bin/bash
# Fix ALL antennas: force master key + correct flag in system.cfg
# This replaces any old device-specific key with the current master key
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa -o BatchMode=no"

CORRECT_URI="wss://server.auralink.link:443+sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV+allowUntrustedCertificate"

IPS="10.10.1.95 10.10.1.67 10.10.1.249 10.10.1.98 10.10.1.88 10.10.1.216 10.10.1.160 10.10.1.86 10.10.1.159 10.10.1.149 10.10.1.245 10.10.1.194 10.10.1.162 10.10.1.169 10.10.1.112 10.10.1.226 10.10.1.62 10.10.1.124"

FIXED=0; ALREADY=0; FAILED=0; TOTAL=0

for IP in $IPS; do
    TOTAL=$((TOTAL + 1))
    DONE=0
    for CRED in "AURALINK:Auralink2021" "ubnt:Auralink2021" "ubnt:Casimposible*7719Varce*1010"; do
        USER="${CRED%%:*}"
        PASS="${CRED#*:}"

        RESULT=$(sshpass -p "$PASS" ssh $SSH_OPTS ${USER}@${IP} "
            CURRENT=\$(grep 'unms.uri=' /tmp/system.cfg 2>/dev/null)
            TARGET='unms.uri=$CORRECT_URI'
            if [ \"\$CURRENT\" = \"\$TARGET\" ]; then
                echo ALREADY_OK
            else
                sed -i 's|unms.uri=.*|unms.uri=$CORRECT_URI|' /tmp/system.cfg
                rm -f /tmp/running.cfg
                cfgmtd -w -p /etc/ 2>/dev/null
                NEW=\$(grep 'unms.uri=' /tmp/system.cfg 2>/dev/null)
                if echo \"\$NEW\" | grep -q 'sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV'; then
                    echo FIXED
                else
                    echo VERIFY_FAIL
                fi
            fi
        " 2>/dev/null)

        if echo "$RESULT" | grep -q "FIXED"; then
            FIXED=$((FIXED+1))
            echo "[$TOTAL] $IP: FIXED - master key set ($USER)"
            DONE=1
            break
        elif echo "$RESULT" | grep -q "ALREADY_OK"; then
            ALREADY=$((ALREADY+1))
            echo "[$TOTAL] $IP: ALREADY OK ($USER)"
            DONE=1
            break
        elif echo "$RESULT" | grep -q "VERIFY_FAIL"; then
            echo "[$TOTAL] $IP: VERIFY FAILED ($USER)"
            DONE=1
            break
        fi
    done
    [ "$DONE" -eq 0 ] && { FAILED=$((FAILED+1)); echo "[$TOTAL] $IP: FAIL (SSH failed)"; }
done

echo ""
echo "=== RESULTADO: Total=$TOTAL Fixed=$FIXED Already=$ALREADY Failed=$FAILED ==="
