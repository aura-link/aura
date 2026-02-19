#!/bin/bash
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=8 -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa"

echo "=== Fix 10.10.1.219 (Magda Mora) ==="
sshpass -p "Auralink2021" ssh $SSH_OPTS ubnt@10.10.1.219 'rm -f /tmp/running.cfg; PIDS=$(ps | grep udapi-bridge | grep -v grep | grep -v supervise); echo "$PIDS"; PID=$(echo "$PIDS" | tail -1 | awk "{print \$1}"); if [ -n "$PID" ]; then kill -9 $PID; echo "killed $PID"; else echo "no pid"; fi'

echo ""
echo "=== Fix 10.10.1.227 (Ana Esther) ==="
sshpass -p "Auralink2021" ssh $SSH_OPTS ubnt@10.10.1.227 'rm -f /tmp/running.cfg; PIDS=$(ps | grep udapi-bridge | grep -v grep | grep -v supervise); echo "$PIDS"; PID=$(echo "$PIDS" | tail -1 | awk "{print \$1}"); if [ -n "$PID" ]; then kill -9 $PID; echo "killed $PID"; else echo "no pid"; fi'

echo ""
echo "=== Fix 10.10.1.53 (Jose Nicolas) - needs DB cleanup first ==="
# Delete stale device entry so it re-registers
docker exec unms-postgres psql -U postgres -d unms -c "DELETE FROM unms.device WHERE device_id = 'f9cc0f51-e0e0-4041-b998-3e16cefae741';" 2>&1
echo "DB entry deleted"
sleep 2
sshpass -p "Auralink2021" ssh $SSH_OPTS ubnt@10.10.1.53 'rm -f /tmp/running.cfg; grep "unms.uri=" /tmp/system.cfg; PIDS=$(ps | grep udapi-bridge | grep -v grep | grep -v supervise); echo "$PIDS"; PID=$(echo "$PIDS" | tail -1 | awk "{print \$1}"); if [ -n "$PID" ]; then kill -9 $PID; echo "killed $PID"; else echo "no pid"; fi'

echo ""
echo "=== Done ==="
