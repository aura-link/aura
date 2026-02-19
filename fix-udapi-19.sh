#!/bin/bash
# Fix udapi-bridge on 19 antennas with key desync issues
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=8 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa -o BatchMode=no"

IPS="10.10.1.95 10.10.1.67 10.10.1.249 10.10.1.98 10.10.1.88 10.10.1.216 10.10.1.160 10.10.1.86 10.10.1.159 10.10.1.149 10.10.1.245 10.10.1.194 10.10.1.162 10.10.1.169 10.10.1.112 10.10.1.226 10.10.1.62 10.10.1.124 10.10.1.241"

FIXED=0; ALREADY=0; FAILED=0; TOTAL=0

for IP in $IPS; do
    TOTAL=$((TOTAL + 1))
    DONE=0
    for CRED in "ubnt:Auralink2021" "AURALINK:Auralink2021" "ubnt:Casimposible*7719Varce*1010"; do
        USER="${CRED%%:*}"
        PASS="${CRED#*:}"

        RESULT=$(sshpass -p "$PASS" ssh $SSH_OPTS ${USER}@${IP} 'rm -f /tmp/running.cfg; CHILD=$(ps | grep "udapi-bridge" | grep -v grep | grep -v supervise | awk "{print \$1}" | head -1); if [ -n "$CHILD" ]; then kill -9 $CHILD 2>/dev/null; echo "FIXED"; else echo "NOPROC"; fi' 2>/dev/null)

        if echo "$RESULT" | grep -q "FIXED"; then
            FIXED=$((FIXED+1))
            echo "[$TOTAL] $IP: FIXED (running.cfg removed + udapi-bridge killed)"
            DONE=1
            break
        elif echo "$RESULT" | grep -q "NOPROC"; then
            ALREADY=$((ALREADY+1))
            echo "[$TOTAL] $IP: PARTIAL (running.cfg removed, no udapi-bridge proc found)"
            DONE=1
            break
        fi
    done
    [ "$DONE" -eq 0 ] && { FAILED=$((FAILED+1)); echo "[$TOTAL] $IP: FAIL (SSH failed)"; }
done

echo ""
echo "=== RESULTADO: Total=$TOTAL Fixed=$FIXED Partial=$ALREADY Failed=$FAILED ==="
