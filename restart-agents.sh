#!/bin/bash
# Script para reiniciar el agente UISP (infctld) en todas las antenas
SSH_OPTS="-o StrictHostKeyChecking=no -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa -o ConnectTimeout=5"

OK=0
FAIL=0

restart_agent() {
    local IP=$1
    local USERS=("ubnt" "AURALINK")
    local PASS="Auralink2021"

    for USER in "${USERS[@]}"; do
        RESULT=$(sshpass -p "$PASS" ssh $SSH_OPTS "$USER@$IP" "killall infctld 2>/dev/null; echo RESTART_OK" 2>/dev/null < /dev/null)
        if echo "$RESULT" | grep -q "RESTART_OK"; then
            echo "  [$IP] OK - Agente reiniciado ($USER)"
            OK=$((OK+1))
            return 0
        fi
    done

    FAIL=$((FAIL+1))
    return 1
}

echo "Reiniciando agente UISP en antenas..."
echo ""

TOTAL=$(wc -l < /tmp/antenna_ips.txt)
COUNT=0
while read -r IP; do
    [ -z "$IP" ] && continue
    COUNT=$((COUNT+1))
    printf "\r[$COUNT/$TOTAL] $IP...          "
    restart_agent "$IP"
done < /tmp/antenna_ips.txt

echo ""
echo ""
echo "============================================"
echo "  RESUMEN"
echo "============================================"
echo "  Reiniciados: $OK"
echo "  Sin acceso:  $FAIL"
echo "============================================"
