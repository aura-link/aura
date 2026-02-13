#!/bin/bash

# ════════════════════════════════════════════════════════════════════════════════
# GESTOR DE SUSPENSIONES PPPoE - MikroTik RB5009
# Sistema rápido para suspender/reactivar clientes
# ════════════════════════════════════════════════════════════════════════════════

# Colores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuración
ROUTER="10.147.17.11"
USER_ADMIN="admin"
WISP_DIR="C:/claude/WISP"
SUSPENSION_SCRIPT="${WISP_DIR}/scripts/suspension_manager.sh"
SUSPENDED_FILE="${WISP_DIR}/config/suspended_clients.txt"

# ════════════════════════════════════════════════════════════════════════════════
# FUNCIONES
# ════════════════════════════════════════════════════════════════════════════════

show_menu() {
    clear
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}                                                        ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}        ${CYAN}GESTOR DE SUSPENSIONES PPPoE${NC}                  ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}                                                        ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${CYAN}1${NC}) ${YELLOW}Suspender cliente${NC}"
    echo -e "  ${CYAN}2${NC}) ${GREEN}Reactivar cliente${NC}"
    echo -e "  ${CYAN}3${NC}) ${BLUE}Ver clientes suspendidos${NC}"
    echo -e "  ${CYAN}4${NC}) Salir"
    echo ""
}

suspender_cliente() {
    local search_name="$1"

    if [ -z "$search_name" ]; then
        echo ""
        read -p "Ingresa nombre del cliente a suspender: " search_name
    fi

    if [ -z "$search_name" ]; then
        echo -e "${RED}❌ Nombre vacío${NC}"
        return 1
    fi

    echo ""
    echo -e "${YELLOW}🔍 Buscando clientes con nombre: $search_name${NC}"
    echo ""

    # Obtener lista de usuarios PPPoE que coincidan
    # Captura toda la línea de salida y parsea correctamente
    local users_array=()
    local ssh_output=$(ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
        -o PubkeyAuthentication=no "$USER_ADMIN@$ROUTER" "/ppp active print" 2>&1)

    # Debug: mostrar salida SSH si no hay coincidencias
    if [ -z "$(echo "$ssh_output" | grep -i "$search_name")" ]; then
        echo -e "${RED}❌ No se encontraron usuarios con '$search_name'${NC}"
        echo ""
        echo -e "${CYAN}Clientes disponibles:${NC}"
        echo "$ssh_output" | head -15
        echo ""
        read -p "Presiona Enter para continuar..."
        return 1
    fi

    # Parsear correctamente: awk extrae el nombre del usuario (segundo campo típicamente)
    while IFS= read -r line; do
        local usuario=$(echo "$line" | awk '{print $2}' | grep -v '^$')
        if [ -n "$usuario" ]; then
            users_array+=("$usuario")
        fi
    done < <(echo "$ssh_output" | grep -i "$search_name")

    # Contar resultados
    local count=${#users_array[@]}

    if [ "$count" -eq 0 ]; then
        echo -e "${RED}❌ No se pudieron extraer usuarios de los resultados${NC}"
        echo ""
        read -p "Presiona Enter para continuar..."
        return 1
    elif [ "$count" -eq 1 ]; then
        # Si solo hay un resultado, suspender directamente
        echo -e "${GREEN}✓ Cliente encontrado: ${users_array[0]}${NC}"
        echo ""
        read -p "¿Suspender? (s/n): " confirm
        if [ "$confirm" = "s" ] || [ "$confirm" = "S" ]; then
            echo ""
            echo -e "${YELLOW}⏳ Procesando...${NC}"
            echo ""
            sudo "$SUSPENSION_SCRIPT" add "${users_array[0]}"
            echo ""
            echo -e "${GREEN}✓ Listo${NC}"
        else
            echo -e "${RED}❌ Operación cancelada${NC}"
        fi
    else
        # Si hay múltiples, mostrar opciones con números
        echo -e "${YELLOW}Se encontraron $count clientes:${NC}"
        echo ""

        select usuario in "${users_array[@]}" "Cancelar"; do
            if [ "$usuario" = "Cancelar" ]; then
                echo -e "${RED}❌ Cancelado${NC}"
                break
            elif [ -n "$usuario" ]; then
                echo ""
                echo -e "${CYAN}Cliente seleccionado: $usuario${NC}"
                echo ""
                read -p "¿Suspender a $usuario? (s/n): " confirm
                if [ "$confirm" = "s" ] || [ "$confirm" = "S" ]; then
                    echo ""
                    echo -e "${YELLOW}⏳ Procesando...${NC}"
                    echo ""
                    sudo "$SUSPENSION_SCRIPT" add "$usuario"
                    echo ""
                    echo -e "${GREEN}✓ Listo${NC}"
                else
                    echo -e "${RED}❌ Operación cancelada${NC}"
                fi
                break
            fi
        done
    fi

    echo ""
    read -p "Presiona Enter para continuar..."
}

reactivar_cliente() {
    local search_name="$1"

    if [ -z "$search_name" ]; then
        echo ""
        read -p "Ingresa nombre del cliente a reactivar: " search_name
    fi

    if [ -z "$search_name" ]; then
        echo -e "${RED}❌ Nombre vacío${NC}"
        return 1
    fi

    echo ""
    echo -e "${YELLOW}🔍 Buscando clientes suspendidos con nombre: $search_name${NC}"
    echo ""

    # Verificar que el archivo de suspendidos existe
    if [ ! -f "$SUSPENDED_FILE" ]; then
        echo -e "${RED}❌ No hay archivo de suspendidos${NC}"
        echo ""
        read -p "Presiona Enter para continuar..."
        return 1
    fi

    # Obtener lista de suspendidos que coincidan
    local users_array=()
    local suspended_list=$(grep -i "$search_name" "$SUSPENDED_FILE" 2>/dev/null)

    if [ -z "$suspended_list" ]; then
        echo -e "${RED}❌ No hay suspendidos con ese nombre${NC}"
        echo ""
        echo -e "${CYAN}Clientes actualmente suspendidos:${NC}"
        cat "$SUSPENDED_FILE" 2>/dev/null | head -20
        echo ""
        read -p "Presiona Enter para continuar..."
        return 1
    fi

    # Parsear lista correctamente en array
    while IFS= read -r usuario; do
        if [ -n "$usuario" ]; then
            users_array+=("$usuario")
        fi
    done < <(echo "$suspended_list")

    # Contar resultados
    local count=${#users_array[@]}

    if [ "$count" -eq 0 ]; then
        echo -e "${RED}❌ No se pudieron extraer usuarios de los resultados${NC}"
        echo ""
        read -p "Presiona Enter para continuar..."
        return 1
    elif [ "$count" -eq 1 ]; then
        # Si solo hay un resultado, reactivar directamente
        echo -e "${GREEN}✓ Cliente encontrado: ${users_array[0]}${NC}"
        echo ""
        read -p "¿Reactivar? (s/n): " confirm
        if [ "$confirm" = "s" ] || [ "$confirm" = "S" ]; then
            echo ""
            echo -e "${YELLOW}⏳ Procesando...${NC}"
            echo ""
            sudo "$SUSPENSION_SCRIPT" remove "${users_array[0]}"
            echo ""
            echo -e "${GREEN}✓ Listo${NC}"
        else
            echo -e "${RED}❌ Operación cancelada${NC}"
        fi
    else
        # Si hay múltiples, mostrar opciones con números
        echo -e "${YELLOW}Se encontraron $count clientes suspendidos:${NC}"
        echo ""

        select usuario in "${users_array[@]}" "Cancelar"; do
            if [ "$usuario" = "Cancelar" ]; then
                echo -e "${RED}❌ Cancelado${NC}"
                break
            elif [ -n "$usuario" ]; then
                echo ""
                echo -e "${CYAN}Cliente seleccionado: $usuario${NC}"
                echo ""
                read -p "¿Reactivar a $usuario? (s/n): " confirm
                if [ "$confirm" = "s" ] || [ "$confirm" = "S" ]; then
                    echo ""
                    echo -e "${YELLOW}⏳ Procesando...${NC}"
                    echo ""
                    sudo "$SUSPENSION_SCRIPT" remove "$usuario"
                    echo ""
                    echo -e "${GREEN}✓ Listo${NC}"
                else
                    echo -e "${RED}❌ Operación cancelada${NC}"
                fi
                break
            fi
        done
    fi

    echo ""
    read -p "Presiona Enter para continuar..."
}

ver_suspendidos() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}           ${CYAN}CLIENTES ACTUALMENTE SUSPENDIDOS${NC}           ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""

    sudo "$SUSPENSION_SCRIPT" list

    echo ""
    read -p "Presiona Enter para continuar..."
}

# ════════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════════

# Verificar si se ejecutó desde línea de comandos
if [ $# -gt 0 ]; then
    case "$1" in
        add)
            suspender_cliente "$2"
            ;;
        remove)
            reactivar_cliente "$2"
            ;;
        list)
            ver_suspendidos
            ;;
        *)
            echo "Uso: $0 [add|remove|list] [nombre_cliente]"
            echo ""
            echo "Ejemplos:"
            echo "  $0 add juan           - Suspender cliente con nombre 'juan'"
            echo "  $0 remove maria       - Reactivar cliente con nombre 'maria'"
            echo "  $0 list               - Ver todos los suspendidos"
            echo ""
            echo "Sin argumentos abre menú interactivo:"
            echo "  $0"
            ;;
    esac
else
    # Menú interactivo
    while true; do
        show_menu
        read -p "Selecciona opción (1-4): " option
        echo ""

        case $option in
            1)
                suspender_cliente
                ;;
            2)
                reactivar_cliente
                ;;
            3)
                ver_suspendidos
                ;;
            4)
                echo -e "${CYAN}Hasta luego! 👋${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Opción inválida${NC}"
                echo ""
                read -p "Presiona Enter para continuar..."
                ;;
        esac
    done
fi
