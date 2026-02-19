#!/bin/bash
# Fix 35 antennas: PPPoE active but UISP disconnected
# Deletes /tmp/running.cfg and restarts udapi-bridge
# Also verifies system.cfg has correct UISP connection string

CORRECT_URI="wss://server.auralink.link:443+sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV+allowUntrustedCertificate"
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=8 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa"

# Credentials to try in order
CREDS=(
    "AURALINK:Auralink2021"
    "ubnt:Auralink2021"
    "ubnt:Casimposible*7719Varce*1010"
)

IPS=(
    10.10.1.221 10.10.1.135 10.10.1.132 10.10.1.158 10.10.1.153
    10.10.1.88  10.10.1.180 10.10.1.144 10.10.1.242 10.10.1.108
    10.10.1.236 10.10.1.253 10.10.1.149 10.10.1.102 10.10.1.168
    10.10.1.216 10.10.1.85  10.10.1.81  10.10.1.225 10.10.1.145
    10.10.1.213 10.10.1.175 10.10.1.169 10.10.1.227 10.10.1.237
    10.10.1.215 10.10.1.197 10.10.1.220 10.10.1.53  10.10.1.92
    10.10.1.254 10.10.1.219 10.10.1.232 10.10.1.172 10.10.1.116
)

FIXED=0
ALREADY_OK=0
URI_FIXED=0
FAILED=0
TOTAL=${#IPS[@]}

echo "=========================================="
echo "Fix 35 UISP-disconnected antennas"
echo "=========================================="
echo "Total: $TOTAL antennas"
echo ""

for IP in "${IPS[@]}"; do
    echo -n "[$IP] "

    # Try each credential
    CONNECTED=0
    for CRED in "${CREDS[@]}"; do
        USER="${CRED%%:*}"
        PASS="${CRED#*:}"

        # Test connection and run fix in one shot
        RESULT=$(sshpass -p "$PASS" ssh $SSH_OPTS "$USER@$IP" '
            # Check if running.cfg exists
            HAD_RUNNING="no"
            if [ -f /tmp/running.cfg ]; then
                HAD_RUNNING="yes"
                rm -f /tmp/running.cfg
            fi

            # Check system.cfg for correct URI
            URI_STATUS="ok"
            if grep -q "unms.uri=" /tmp/system.cfg 2>/dev/null; then
                CURRENT=$(grep "unms.uri=" /tmp/system.cfg | head -1 | cut -d= -f2-)
                if echo "$CURRENT" | grep -q "allowSelfSignedCertificate"; then
                    URI_STATUS="wrong_flag"
                elif ! echo "$CURRENT" | grep -q "server.auralink.link"; then
                    URI_STATUS="wrong_server"
                fi
            else
                URI_STATUS="missing"
            fi

            # Find and kill udapi-bridge child process
            BRIDGE_PID=$(ps | grep "{exe} /bin/udapi-bridge" | grep -v grep | awk "{print \$1}" | head -1)
            if [ -z "$BRIDGE_PID" ]; then
                BRIDGE_PID=$(ps | grep "udapi-bridge" | grep -v grep | grep -v "supervise" | awk "{print \$1}" | tail -1)
            fi

            KILLED="no"
            if [ -n "$BRIDGE_PID" ]; then
                kill -9 $BRIDGE_PID 2>/dev/null
                KILLED="yes"
            fi

            echo "running=$HAD_RUNNING uri=$URI_STATUS killed=$KILLED pid=$BRIDGE_PID"
        ' 2>/dev/null)

        if [ $? -eq 0 ] && [ -n "$RESULT" ]; then
            CONNECTED=1

            HAD_RUNNING=$(echo "$RESULT" | grep -o 'running=[^ ]*' | cut -d= -f2)
            URI_STATUS=$(echo "$RESULT" | grep -o 'uri=[^ ]*' | cut -d= -f2)
            KILLED=$(echo "$RESULT" | grep -o 'killed=[^ ]*' | cut -d= -f2)

            # Fix URI if needed
            if [ "$URI_STATUS" != "ok" ]; then
                echo -n "(fixing URI: $URI_STATUS) "
                sshpass -p "$PASS" ssh $SSH_OPTS "$USER@$IP" "
                    # Remove old unms.uri line and add correct one
                    grep -v 'unms.uri=' /tmp/system.cfg > /tmp/system.cfg.tmp
                    echo 'unms.uri=$CORRECT_URI' >> /tmp/system.cfg.tmp
                    mv /tmp/system.cfg.tmp /tmp/system.cfg
                    # Save to flash
                    cfgmtd -w -p /etc/
                    # Kill udapi-bridge again to pick up new config
                    BRIDGE_PID=\$(ps | grep 'udapi-bridge' | grep -v grep | grep -v 'supervise' | awk '{print \$1}' | tail -1)
                    [ -n \"\$BRIDGE_PID\" ] && kill -9 \$BRIDGE_PID 2>/dev/null
                " 2>/dev/null
                URI_FIXED=$((URI_FIXED + 1))
            fi

            if [ "$HAD_RUNNING" = "yes" ] || [ "$KILLED" = "yes" ]; then
                FIXED=$((FIXED + 1))
                echo "FIXED (user=$USER, running.cfg=$HAD_RUNNING, killed=$KILLED, uri=$URI_STATUS)"
            else
                ALREADY_OK=$((ALREADY_OK + 1))
                echo "no running.cfg, no bridge found (user=$USER, uri=$URI_STATUS)"
            fi
            break
        fi
    done

    if [ $CONNECTED -eq 0 ]; then
        FAILED=$((FAILED + 1))
        echo "FAILED (all credentials failed or unreachable)"
    fi

    sleep 0.3
done

echo ""
echo "=========================================="
echo "RESULTS"
echo "=========================================="
echo "Total:        $TOTAL"
echo "Fixed:        $FIXED"
echo "URI updated:  $URI_FIXED"
echo "Already OK:   $ALREADY_OK"
echo "Failed:       $FAILED"
echo "=========================================="
