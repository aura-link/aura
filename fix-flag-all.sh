#!/bin/bash
# Fix all 17 antennas: change allowSelfSignedCertificate to allowUntrustedCertificate
# and save to flash (NO kill of udapi-bridge - let it reconnect naturally)
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa -o BatchMode=no"

IPS="10.10.1.67 10.10.1.249 10.10.1.98 10.10.1.88 10.10.1.216 10.10.1.160 10.10.1.86 10.10.1.159 10.10.1.149 10.10.1.245 10.10.1.194 10.10.1.162 10.10.1.169 10.10.1.112 10.10.1.226 10.10.1.62 10.10.1.124"

FIXED=0; ALREADY=0; FAILED=0; TOTAL=0

for IP in $IPS; do
    TOTAL=$((TOTAL + 1))
    DONE=0
    for CRED in "AURALINK:Auralink2021" "ubnt:Auralink2021" "ubnt:Casimposible*7719Varce*1010"; do
        USER="${CRED%%:*}"
        PASS="${CRED#*:}"

        RESULT=$(sshpass -p "$PASS" ssh $SSH_OPTS ${USER}@${IP} '
            CURRENT=$(grep "unms.uri" /tmp/system.cfg 2>/dev/null)
            if echo "$CURRENT" | grep -q "allowUntrustedCertificate"; then
                echo "ALREADY_OK"
            elif echo "$CURRENT" | grep -q "allowSelfSignedCertificate"; then
                sed -i "s/allowSelfSignedCertificate/allowUntrustedCertificate/" /tmp/system.cfg
                rm -f /tmp/running.cfg
                cfgmtd -w -p /etc/ 2>/dev/null
                echo "CHANGED"
            elif echo "$CURRENT" | grep -q "unms.uri="; then
                # Has URI but no flag - add allowUntrustedCertificate
                sed -i "s|unms.uri=\(.*\)|unms.uri=\1+allowUntrustedCertificate|" /tmp/system.cfg
                rm -f /tmp/running.cfg
                cfgmtd -w -p /etc/ 2>/dev/null
                echo "ADDED_FLAG"
            else
                echo "NO_UNMS_URI"
            fi
        ' 2>/dev/null)

        if echo "$RESULT" | grep -q "CHANGED"; then
            FIXED=$((FIXED+1))
            echo "[$TOTAL] $IP: CHANGED flag ($USER)"
            DONE=1
            break
        elif echo "$RESULT" | grep -q "ADDED_FLAG"; then
            FIXED=$((FIXED+1))
            echo "[$TOTAL] $IP: ADDED flag ($USER)"
            DONE=1
            break
        elif echo "$RESULT" | grep -q "ALREADY_OK"; then
            ALREADY=$((ALREADY+1))
            echo "[$TOTAL] $IP: ALREADY OK ($USER)"
            DONE=1
            break
        elif echo "$RESULT" | grep -q "NO_UNMS_URI"; then
            echo "[$TOTAL] $IP: NO UNMS URI FOUND ($USER)"
            DONE=1
            break
        fi
    done
    [ "$DONE" -eq 0 ] && { FAILED=$((FAILED+1)); echo "[$TOTAL] $IP: FAIL (SSH failed all creds)"; }
done

echo ""
echo "=== RESULTADO: Total=$TOTAL Changed=$FIXED Already=$ALREADY Failed=$FAILED ==="
