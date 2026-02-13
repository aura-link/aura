#!/bin/bash
# Script para actualizar UISP key en antenas Ubiquiti
NEW_KEY="wss://server.auralink.link:443+sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV+allowSelfSignedCertificate"
SSH_OPTS="-o StrictHostKeyChecking=no -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa -o ConnectTimeout=5"

OK=0
FAIL=0
SKIP=0
NOSSH=0

update_antenna() {
    local IP=$1

    # Intentar con cada credencial
    local USERS=("ubnt" "AURALINK" "ubnt")
    local PASSES=("Auralink2021" "Auralink2021" "Casimposible*7719Varce*1010")

    for i in 0 1 2; do
        USER="${USERS[$i]}"
        PASS="${PASSES[$i]}"

        RESULT=$(sshpass -p "$PASS" ssh $SSH_OPTS "$USER@$IP" "grep unms.uri /tmp/system.cfg 2>/dev/null; echo EXIT_OK" 2>/dev/null < /dev/null)

        if echo "$RESULT" | grep -q "EXIT_OK"; then
            # SSH exitoso
            CURRENT_URI=$(echo "$RESULT" | grep "unms.uri=" | head -1)

            if echo "$CURRENT_URI" | grep -q "sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV"; then
                echo "  [$IP] SKIP - Ya tiene la key correcta ($USER)"
                SKIP=$((SKIP+1))
                return 0
            fi

            # Actualizar key via script remoto
            sshpass -p "$PASS" ssh $SSH_OPTS "$USER@$IP" "sed -i 's|unms.uri=.*|unms.uri=$NEW_KEY|' /tmp/system.cfg; grep -q 'unms.uri=' /tmp/system.cfg || echo 'unms.uri=$NEW_KEY' >> /tmp/system.cfg; grep -q 'unms.status=enabled' /tmp/system.cfg || echo 'unms.status=enabled' >> /tmp/system.cfg; cfgmtd -w -p /etc/ 2>/dev/null; echo UPDATED_OK" 2>/dev/null < /dev/null | grep -q "UPDATED_OK"

            if [ $? -eq 0 ]; then
                echo "  [$IP] OK - Key actualizada ($USER) [anterior: $CURRENT_URI]"
                OK=$((OK+1))
            else
                echo "  [$IP] FAIL - Error al guardar ($USER)"
                FAIL=$((FAIL+1))
            fi
            return 0
        fi
    done

    NOSSH=$((NOSSH+1))
    return 1
}

echo "============================================"
echo "  UISP Key Update - Antenas Ubiquiti"
echo "============================================"
echo ""

if [ ! -f /tmp/antenna_ips.txt ]; then
    echo "ERROR: No se encontro /tmp/antenna_ips.txt"
    exit 1
fi

TOTAL=$(wc -l < /tmp/antenna_ips.txt)
echo "Procesando $TOTAL antenas..."
echo ""
COUNT=0
while read -r IP; do
    [ -z "$IP" ] && continue
    COUNT=$((COUNT+1))
    echo "[$COUNT/$TOTAL] Procesando $IP..."
    update_antenna "$IP"
done < /tmp/antenna_ips.txt

echo ""
echo "============================================"
echo "  RESUMEN"
echo "============================================"
echo "  Actualizadas: $OK"
echo "  Ya correctas: $SKIP"
echo "  Sin acceso SSH: $NOSSH"
echo "  Fallidas:     $FAIL"
echo "============================================"
