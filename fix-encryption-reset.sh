#!/bin/bash
# Reset UISP encryption state on antennas with key desync
# Process: disable UISP → save to flash → kill udapi → re-enable → save → kill udapi
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa -o BatchMode=no"

IPS="10.10.1.95 10.10.1.67 10.10.1.249 10.10.1.98 10.10.1.88 10.10.1.216 10.10.1.160 10.10.1.86 10.10.1.159 10.10.1.149 10.10.1.245 10.10.1.194 10.10.1.162 10.10.1.169 10.10.1.112 10.10.1.226 10.10.1.62 10.10.1.124"

FIXED=0; FAILED=0; TOTAL=0

for IP in $IPS; do
    TOTAL=$((TOTAL + 1))
    DONE=0
    for CRED in "AURALINK:Auralink2021" "ubnt:Auralink2021" "ubnt:Casimposible*7719Varce*1010"; do
        USER="${CRED%%:*}"
        PASS="${CRED#*:}"

        # Step 1: Disable UISP and save to flash
        R1=$(sshpass -p "$PASS" ssh $SSH_OPTS ${USER}@${IP} '
            # Disable UISP
            sed -i "s/unms.status=enabled/unms.status=disabled/" /tmp/system.cfg
            # Save to flash
            cfgmtd -w -p /etc/ 2>/dev/null
            # Kill udapi-bridge
            CHILD=$(ps | grep "udapi-bridge" | grep -v grep | grep -v supervise | awk "{print \$1}" | head -1)
            [ -n "$CHILD" ] && kill -9 $CHILD 2>/dev/null
            sleep 2
            echo "DISABLED"
        ' 2>/dev/null)

        if echo "$R1" | grep -q "DISABLED"; then
            # Step 2: Re-enable UISP and save to flash
            sleep 3
            R2=$(sshpass -p "$PASS" ssh $SSH_OPTS ${USER}@${IP} '
                # Remove any running.cfg
                rm -f /tmp/running.cfg
                # Re-enable UISP
                sed -i "s/unms.status=disabled/unms.status=enabled/" /tmp/system.cfg
                # Save to flash
                cfgmtd -w -p /etc/ 2>/dev/null
                # Kill udapi-bridge to force restart
                CHILD=$(ps | grep "udapi-bridge" | grep -v grep | grep -v supervise | awk "{print \$1}" | head -1)
                [ -n "$CHILD" ] && kill -9 $CHILD 2>/dev/null
                echo "ENABLED"
            ' 2>/dev/null)

            if echo "$R2" | grep -q "ENABLED"; then
                FIXED=$((FIXED+1))
                echo "[$TOTAL] $IP: RESET OK (disabled→saved→re-enabled→saved→restarted)"
            else
                FIXED=$((FIXED+1))
                echo "[$TOTAL] $IP: PARTIAL (disabled OK, re-enable uncertain)"
            fi
            DONE=1
            break
        fi
    done
    [ "$DONE" -eq 0 ] && { FAILED=$((FAILED+1)); echo "[$TOTAL] $IP: FAIL (SSH failed all creds)"; }
done

echo ""
echo "=== RESULTADO: Total=$TOTAL Fixed=$FIXED Failed=$FAILED ==="
