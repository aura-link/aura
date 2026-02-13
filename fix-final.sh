#!/bin/bash
# FINAL FIX: Remove running.cfg + kill udapi-bridge child + kill infctld
# This forces both services to restart and read from system.cfg

SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=5 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa -o BatchMode=no"
IPFILE="${1:-/tmp/ubnt_ppp_ips.txt}"
FIXED=0; OK=0; FAILED=0; TOTAL=0

cat > /tmp/fix_antenna_final.sh << 'REMOTESCRIPT'
#!/bin/sh
# Check if already connected to correct UISP
if netstat -tn 2>/dev/null | grep -q "217.216.85.65:443.*ESTABLISHED"; then
    echo "OK"
    exit 0
fi
# Remove running.cfg
rm -f /tmp/running.cfg
# Kill udapi-bridge child (the {exe} one that connects to UISP)
for PID in $(ps w | grep '{exe}.*udapi-bridge' | grep -v grep | awk '{print $1}'); do
    kill -9 $PID 2>/dev/null
done
# Also kill infctld
for PID in $(ps w | grep 'infctld' | grep -v grep | awk '{print $1}'); do
    kill -9 $PID 2>/dev/null
done
sleep 1
# Verify new connection
if netstat -tn 2>/dev/null | grep -q "217.216.85.65:443"; then
    echo "FIXED_OK"
else
    echo "FIXED_PENDING"
fi
REMOTESCRIPT

while IFS= read -r IP; do
    IP=$(echo "$IP" | tr -d '\r\n ')
    [ -z "$IP" ] && continue
    TOTAL=$((TOTAL + 1))

    DONE=0
    for CRED in "ubnt:Auralink2021" "AURALINK:Auralink2021" "ubnt:Casimposible*7719Varce*1010"; do
        USER="${CRED%%:*}"
        PASS="${CRED#*:}"
        RESULT=$(sshpass -p "$PASS" ssh $SSH_OPTS ${USER}@${IP} 'sh -s' < /tmp/fix_antenna_final.sh 2>/dev/null)
        if [ -n "$RESULT" ]; then
            DONE=1
            case "$RESULT" in
                *OK*) OK=$((OK+1)); echo "[$TOTAL] $IP: OK" ;;
                *FIXED*) FIXED=$((FIXED+1)); echo "[$TOTAL] $IP: FIXED" ;;
                *) echo "[$TOTAL] $IP: ?($RESULT)" ;;
            esac
            break
        fi
    done
    [ "$DONE" -eq 0 ] && { FAILED=$((FAILED+1)); echo "[$TOTAL] $IP: FAIL"; }
done < "$IPFILE"

echo ""
echo "=== DONE: Total=$TOTAL Fixed=$FIXED OK=$OK Failed=$FAILED ==="
