#!/bin/bash

# Script de Auto-Actualización PPPoE Suspension
# Ejecutar cada 5 minutos via cron para actualizar IPs dinámicas

ROUTER="10.147.17.11"
USER="admin"
LOG_FILE="/var/log/pppoe_suspension.log"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Crear log si no existe
touch "$LOG_FILE" 2>/dev/null || LOG_FILE="/tmp/pppoe_suspension.log"

log_message() {
    local msg="$1"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $msg" >> "$LOG_FILE"
}

update_suspended_pppoe_users() {
    log_message "=== Iniciando actualización de suspensiones PPPoE ==="

    # Obtener lista de usuarios PPPoE con comentario "PPPoE:"
    local suspended_users=$(ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o PubkeyAuthentication=no "$USER@$ROUTER" \
        "/ip firewall mangle print where comment~\"PPPoE:\" comment" 2>&1 | \
        grep -oP '(?<=PPPoE: )\S+' | sort -u)

    if [ -z "$suspended_users" ]; then
        log_message "No hay usuarios PPPoE suspendidos"
        return 0
    fi

    log_message "Encontrados usuarios suspendidos: $suspended_users"

    # Procesar cada usuario
    while IFS= read -r pppoe_user; do
        if [ -z "$pppoe_user" ]; then
            continue
        fi

        log_message "Procesando usuario: $pppoe_user"

        # Obtener IP actual del usuario PPPoE
        local current_ip=$(ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
            -o PubkeyAuthentication=no "$USER@$ROUTER" \
            "/ppp active print where name=$pppoe_user" 2>&1 | \
            grep -i address | awk '{print $NF}')

        if [ -z "$current_ip" ]; then
            log_message "  ⚠️  Usuario $pppoe_user no está conectado"
            # Opcionalmente, aquí podrías remover la regla si el usuario está offline
            # ssh -o StrictHostKeyChecking=no "$USER@$ROUTER" \
            #     "/ip firewall mangle remove [find comment~\"$pppoe_user\"]"
            continue
        fi

        log_message "  ✓ IP actual: $current_ip"

        # Obtener IP de la regla existente
        local rule_ip=$(ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
            -o PubkeyAuthentication=no "$USER@$ROUTER" \
            "/ip firewall mangle print where comment~\"$pppoe_user\"" 2>&1 | \
            grep -oP 'src-address=\K[^ ]+' | head -1)

        if [ "$current_ip" = "$rule_ip" ]; then
            log_message "  ✓ IP sin cambios, regla actualizada"
        else
            log_message "  ! Cambio detectado: $rule_ip → $current_ip"

            # Remover regla antigua
            ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
                -o PubkeyAuthentication=no "$USER@$ROUTER" \
                "/ip firewall mangle remove [find comment~\"$pppoe_user\"]" 2>&1 | \
                grep -v "WARNING" > /dev/null

            log_message "  - Regla antigua removida"

            # Crear regla nueva con IP actual
            ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
                -o PubkeyAuthentication=no "$USER@$ROUTER" \
                "/ip firewall mangle add chain=prerouting src-address=$current_ip action=mark-packet new-packet-mark=suspended_traffic comment=\"PPPoE: $pppoe_user\"" 2>&1 | \
                grep -v "WARNING" > /dev/null

            log_message "  + Regla nueva creada con IP $current_ip"
        fi

    done <<< "$suspended_users"

    log_message "=== Finalización de actualización ==="
}

# Ejecutar actualización
update_suspended_pppoe_users
