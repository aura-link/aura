#!/bin/bash

# Script para suspender clientes PPPoE dinámicamente
# Funciona incluso si la IP cambia

ROUTER="10.147.17.11"
USER="admin"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

show_help() {
    cat << 'HELP'
Gestor de Suspensiones PPPoE para MikroTik

Uso: ./suspension_pppoe.sh [comando] [usuario_pppoe] [acción]

Comandos:
  add     - Agregar cliente a suspensión
  remove  - Remover cliente de suspensión
  list    - Listar clientes suspendidos
  help    - Mostrar esta ayuda

Ejemplos:
  ./suspension_pppoe.sh add cliente_juan
  ./suspension_pppoe.sh remove cliente_juan
  ./suspension_pppoe.sh list

HELP
}

add_suspended_pppoe() {
    local pppoe_user=$1

    echo -e "${YELLOW}=== Suspendiendo cliente PPPoE ===${NC}"
    echo "Usuario: $pppoe_user"
    echo ""

    # Paso 1: Obtener la IP actual del usuario PPPoE
    echo -e "${YELLOW}[1/3]${NC} Obteniendo IP actual del usuario PPPoE..."
    local current_ip=$(ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o PubkeyAuthentication=no "$USER@$ROUTER" \
        "/ppp active print where name=$pppoe_user" 2>&1 | grep -i address | awk '{print $NF}')

    if [ -z "$current_ip" ]; then
        echo -e "${RED}✗ Error: Usuario PPPoE '$pppoe_user' no encontrado o no está conectado${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ IP encontrada: $current_ip${NC}"
    echo ""

    # Paso 2: Crear mangle rule basada en el usuario PPPoE
    echo -e "${YELLOW}[2/3]${NC} Creando regla de suspensión..."

    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o PubkeyAuthentication=no "$USER@$ROUTER" \
        "/ip firewall mangle add chain=prerouting src-address=$current_ip action=mark-packet new-packet-mark=suspended_traffic comment=\"PPPoE: $pppoe_user\"" \
        2>&1 | grep -v "WARNING"

    echo -e "${GREEN}✓ Regla mangle creada${NC}"
    echo ""

    # Paso 3: Verificar que todo está bien
    echo -e "${YELLOW}[3/3]${NC} Verificando configuración..."
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o PubkeyAuthentication=no "$USER@$ROUTER" \
        "/ip firewall mangle print where comment~\"$pppoe_user\"" 2>&1 | grep -v "WARNING" | head -5

    echo ""
    echo -e "${BLUE}═════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ Cliente suspendido exitosamente${NC}"
    echo -e "${BLUE}═════════════════════════════════════${NC}"
    echo ""
    echo "Usuario PPPoE: $pppoe_user"
    echo "IP Actual: $current_ip"
    echo "Estado: SUSPENDIDO"
    echo ""
    echo -e "${YELLOW}Nota:${NC} Si el cliente se desconecta y reconecta con nueva IP,"
    echo "      deberá ejecutar nuevamente este script para actualizar la regla."
    echo ""
}

remove_suspended_pppoe() {
    local pppoe_user=$1

    echo -e "${YELLOW}=== Removiendo suspensión de cliente PPPoE ===${NC}"
    echo "Usuario: $pppoe_user"
    echo ""

    # Buscar y remover la regla
    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o PubkeyAuthentication=no "$USER@$ROUTER" \
        "/ip firewall mangle remove [find comment~\"$pppoe_user\"]" 2>&1 | grep -v "WARNING"

    echo -e "${GREEN}✓ Regla removida${NC}"
    echo ""
    echo -e "${BLUE}═════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ Cliente reactivado${NC}"
    echo -e "${BLUE}═════════════════════════════════════${NC}"
    echo ""
}

list_suspended_pppoe() {
    echo -e "${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Clientes PPPoE Suspendidos                       ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════╝${NC}"
    echo ""

    ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o PubkeyAuthentication=no "$USER@$ROUTER" \
        "/ip firewall mangle print where chain=prerouting comment~\"PPPoE:\"" 2>&1 | grep -v "WARNING"

    echo ""
}

# Main
if [ $# -lt 1 ]; then
    show_help
    exit 1
fi

case "$1" in
    add)
        if [ -z "$2" ]; then
            echo "Error: Debes especificar el usuario PPPoE"
            echo "Uso: $0 add [usuario_pppoe]"
            exit 1
        fi
        add_suspended_pppoe "$2"
        ;;
    remove)
        if [ -z "$2" ]; then
            echo "Error: Debes especificar el usuario PPPoE"
            echo "Uso: $0 remove [usuario_pppoe]"
            exit 1
        fi
        remove_suspended_pppoe "$2"
        ;;
    list)
        list_suspended_pppoe
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Comando no reconocido: $1"
        show_help
        exit 1
        ;;
esac
