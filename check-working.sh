#!/bin/bash
# Check UISP config on working antennas for comparison
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=5 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa -o BatchMode=no"
for IP in 10.10.1.91 10.10.1.60 10.10.1.68; do
    for CRED in "ubnt:Auralink2021" "AURALINK:Auralink2021"; do
        USER="${CRED%%:*}"
        PASS="${CRED#*:}"
        R=$(sshpass -p "$PASS" ssh $SSH_OPTS ${USER}@${IP} 'grep unms /tmp/system.cfg' 2>/dev/null)
        if [ -n "$R" ]; then
            echo "$IP ($USER): $R"
            break
        fi
    done
done
