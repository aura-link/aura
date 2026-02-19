#!/bin/bash
# Fix remaining 19 antennas (batch 2)
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=8 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa"

IPS=(
    10.10.1.85  10.10.1.81  10.10.1.225 10.10.1.145
    10.10.1.213 10.10.1.175 10.10.1.169 10.10.1.227 10.10.1.237
    10.10.1.215 10.10.1.197 10.10.1.220 10.10.1.53  10.10.1.92
    10.10.1.254 10.10.1.219 10.10.1.232 10.10.1.172 10.10.1.116
)

CREDS=("AURALINK:Auralink2021" "ubnt:Auralink2021" "ubnt:Casimposible*7719Varce*1010")
FIXED=0; FAILED=0; TOTAL=${#IPS[@]}

echo "Fix remaining $TOTAL antennas"
echo "=============================="

for IP in "${IPS[@]}"; do
    echo -n "[$IP] "
    CONNECTED=0
    for CRED in "${CREDS[@]}"; do
        USER="${CRED%%:*}"; PASS="${CRED#*:}"
        RESULT=$(sshpass -p "$PASS" ssh $SSH_OPTS "$USER@$IP" 'rm -f /tmp/running.cfg; PID=$(ps | grep "udapi-bridge" | grep -v grep | grep -v supervise | awk "{print \$1}" | tail -1); if [ -n "$PID" ]; then kill -9 $PID; echo "killed=$PID"; else echo "killed=none"; fi' 2>/dev/null)
        if [ $? -eq 0 ] && [ -n "$RESULT" ]; then
            CONNECTED=1
            FIXED=$((FIXED + 1))
            echo "FIXED (user=$USER) $RESULT"
            break
        fi
    done
    [ $CONNECTED -eq 0 ] && { FAILED=$((FAILED + 1)); echo "FAILED"; }
    sleep 0.5
done

echo ""
echo "=============================="
echo "RESULTS: Fixed=$FIXED Failed=$FAILED Total=$TOTAL"
echo "=============================="
