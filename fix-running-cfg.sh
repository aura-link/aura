#!/bin/bash
# Fix running.cfg on all Ubiquiti antennas
# Usage: bash fix-running-cfg.sh /path/to/ip_list.txt

NEW_URI="wss://server.auralink.link:443+sBRaeWB1kiH4cxBIWmBTEyuxIIeULvidfT3s7UXpR2ZbapIV+allowSelfSignedCertificate"
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=5 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa -o BatchMode=no"
PASSWORDS=("Auralink2021" "Casimposible*7719Varce*1010")
USERS=("ubnt" "AURALINK")

IPFILE="${1:-/tmp/ubnt_ppp_ips.txt}"

FIXED=0
ALREADY_OK=0
NO_RUNNING_CFG=0
FAILED=0
TOTAL=0

while IFS= read -r IP; do
    IP=$(echo "$IP" | tr -d '\r\n ')
    [ -z "$IP" ] && continue
    TOTAL=$((TOTAL + 1))

    DONE=0
    for USER in "${USERS[@]}"; do
        [ "$DONE" -eq 1 ] && break
        for PASS in "${PASSWORDS[@]}"; do
            RESULT=$(sshpass -p "$PASS" ssh -n $SSH_OPTS ${USER}@${IP} "
                if [ ! -f /tmp/running.cfg ]; then
                    echo NO_RUNNING_CFG
                    exit 0
                fi

                CURRENT=\$(grep '^unms.uri=' /tmp/running.cfg 2>/dev/null)
                if echo \"\$CURRENT\" | grep -q 'server.auralink.link'; then
                    echo ALREADY_OK
                    exit 0
                fi

                if grep -q '^unms.uri=' /tmp/running.cfg; then
                    sed -i 's|^unms.uri=.*|unms.uri=${NEW_URI}|' /tmp/running.cfg
                else
                    echo 'unms.uri=${NEW_URI}' >> /tmp/running.cfg
                fi

                if ! grep -q '^unms.status=enabled' /tmp/running.cfg; then
                    if grep -q '^unms.status=' /tmp/running.cfg; then
                        sed -i 's|^unms.status=.*|unms.status=enabled|' /tmp/running.cfg
                    else
                        echo 'unms.status=enabled' >> /tmp/running.cfg
                    fi
                fi

                if ! grep -q 'server.auralink.link' /tmp/system.cfg 2>/dev/null; then
                    if grep -q '^unms.uri=' /tmp/system.cfg; then
                        sed -i 's|^unms.uri=.*|unms.uri=${NEW_URI}|' /tmp/system.cfg
                    fi
                    cfgmtd -w -p /etc/ 2>/dev/null
                fi

                PID=\$(ps w | grep infctld | grep -v grep | awk '{print \$1}')
                [ -n \"\$PID\" ] && kill \$PID 2>/dev/null
                echo FIXED
            " 2>/dev/null)

            if [ -n "$RESULT" ]; then
                DONE=1
                case "$RESULT" in
                    *FIXED*)
                        FIXED=$((FIXED + 1))
                        echo "[$TOTAL] $IP: FIXED"
                        ;;
                    *ALREADY_OK*)
                        ALREADY_OK=$((ALREADY_OK + 1))
                        echo "[$TOTAL] $IP: OK"
                        ;;
                    *NO_RUNNING_CFG*)
                        NO_RUNNING_CFG=$((NO_RUNNING_CFG + 1))
                        echo "[$TOTAL] $IP: NO_RCFG"
                        ;;
                    *)
                        echo "[$TOTAL] $IP: ?($RESULT)"
                        ;;
                esac
                break
            fi
        done
    done

    if [ "$DONE" -eq 0 ]; then
        FAILED=$((FAILED + 1))
        echo "[$TOTAL] $IP: FAIL"
    fi
done < "$IPFILE"

echo ""
echo "=== SUMMARY ==="
echo "Total: $TOTAL"
echo "Fixed: $FIXED"
echo "Already OK: $ALREADY_OK"
echo "No running.cfg: $NO_RUNNING_CFG"
echo "Failed: $FAILED"
