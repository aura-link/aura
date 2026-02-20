#!/bin/bash
# Fix 7 antennas causing decryption errors in UISP
# These have UISP connection string but with old/wrong keys
# Solution: reset to master key, save, restart udapi-bridge
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=8 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa"
URI="wss://server.auralink.link:443+sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV+allowUntrustedCertificate"

CREDS=("ubnt:Auralink2021" "AURALINK:Auralink2021" "ubnt:Casimposible*7719Varce*1010")

# MAC -> PPPoE name -> current IP
IPS=(10.10.1.55 10.10.1.54 10.10.1.222 10.10.1.184 10.10.1.161 10.10.1.86 10.10.1.75)
NAMES=("hugomanzot" "veronicatenoriot" "dianacornejoc" "diftomatlan" "veronicachavarinc" "landinc" "danielayonc")

FIXED=0; ALREADY=0; FAILED=0; TOTAL=${#IPS[@]}

echo "Fix decryption errors on $TOTAL antennas (reset to master key)"
echo "================================================================"

for IDX in "${!IPS[@]}"; do
    IP="${IPS[$IDX]}"
    NAME="${NAMES[$IDX]}"

    # Clear known_hosts first
    ssh-keygen -f /root/.ssh/known_hosts -R "$IP" 2>/dev/null

    echo -n "[$IP] ($NAME) "
    CONNECTED=0
    for CRED in "${CREDS[@]}"; do
        USER="${CRED%%:*}"; PASS="${CRED#*:}"

        RESULT=$(sshpass -p "$PASS" ssh $SSH_OPTS "$USER@$IP" 'grep "^unms.uri=" /tmp/system.cfg 2>/dev/null | head -1' 2>/dev/null)

        if [ $? -eq 0 ]; then
            CONNECTED=1
            STATUS="$RESULT"

            # Always reset to master key and restart
            sshpass -p "$PASS" ssh $SSH_OPTS "$USER@$IP" "
                # Remove ALL unms.* lines
                grep -v '^unms\.' /tmp/system.cfg > /tmp/system.cfg.new
                echo 'unms.uri=$URI' >> /tmp/system.cfg.new
                echo 'unms.status=enabled' >> /tmp/system.cfg.new
                cp /tmp/system.cfg.new /tmp/system.cfg
                rm /tmp/system.cfg.new
                # Save to flash
                cfgmtd -w -p /etc/
                # Recreate running.cfg for key exchange
                rm -f /tmp/running.cfg
                cp /tmp/system.cfg /tmp/running.cfg
                # Restart udapi-bridge
                killall -9 udapi-bridge 2>/dev/null
            " 2>/dev/null
            FIXED=$((FIXED + 1))
            echo "RESET to master key (user=$USER, was: $STATUS)"
            break
        fi
    done

    [ $CONNECTED -eq 0 ] && { FAILED=$((FAILED + 1)); echo "FAILED (unreachable)"; }
    sleep 0.5
done

echo ""
echo "================================================================"
echo "RESULTS:"
echo "  Reset:           $FIXED"
echo "  Failed:          $FAILED"
echo "  Total:           $TOTAL"
echo "================================================================"
