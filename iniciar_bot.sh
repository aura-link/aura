#!/bin/bash
# Script para iniciar el bot AURALINK Monitor
# Ejecutar: bash iniciar_bot.sh

set -e

echo "=========================================="
echo "Iniciando AURALINK Monitor Bot"
echo "=========================================="

cd /home/uisp/auralink_monitor

# Activar virtual environment
source /home/uisp/auralink_monitor/bin/activate

# Ejecutar el bot
echo "✓ Bot iniciado"
echo "✓ Esperando mensajes en Telegram..."
echo ""
echo "Para detener: Ctrl+C"
echo "=========================================="
echo ""

python3 /home/uisp/auralink_monitor/auralink_monitor.py
