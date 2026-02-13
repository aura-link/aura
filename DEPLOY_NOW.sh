#!/bin/bash
#
# AURALINK Monitor Bot v3 - DEPLOYMENT INMEDIATO
# Ejecuta esto en tu máquina con acceso SSH a UISP
#
# Uso: bash DEPLOY_NOW.sh
#

set -e

echo ""
echo "============================================================"
echo "  AURALINK MONITOR BOT v3 - DEPLOYMENT INMEDIATO"
echo "============================================================"
echo ""
echo "Este script:"
echo "  1. Detiene el bot anterior (si existe)"
echo "  2. Copia el script v3 al servidor"
echo "  3. Inicia el bot en background"
echo "  4. Verifica que está corriendo"
echo ""
echo "============================================================"
echo ""

# Configuración
UISP_USER="uisp"
UISP_HOST="10.1.1.254"
UISP_SERVER="${UISP_USER}@${UISP_HOST}"
BOT_DIR="/home/uisp/auralink_monitor"
BOT_SCRIPT="auralink_monitor.py"
LOCAL_SCRIPT="C:/claude2/auralink_telegram_monitor_v3.py"

# Verificar que el script local existe
if [ ! -f "$LOCAL_SCRIPT" ]; then
    echo "❌ ERROR: No se encontró $LOCAL_SCRIPT"
    exit 1
fi

echo "[PASO 1] Deteniendo bot anterior..."
echo "ssh $UISP_SERVER \"pkill -f auralink_monitor 2>/dev/null || true\""
ssh -o StrictHostKeyChecking=no "$UISP_SERVER" "pkill -f auralink_monitor 2>/dev/null || true; sleep 1" || true
echo "✓ Hecho"
echo ""

echo "[PASO 2] Respaldando logs anterior..."
ssh -o StrictHostKeyChecking=no "$UISP_SERVER" "test -f $BOT_DIR/monitor.log && cp $BOT_DIR/monitor.log $BOT_DIR/monitor.log.backup.\$(date +%Y%m%d_%H%M%S) || true" || true
echo "✓ Respaldo completado"
echo ""

echo "[PASO 3] Subiendo script v3..."
echo "scp $LOCAL_SCRIPT $UISP_SERVER:$BOT_DIR/$BOT_SCRIPT"
scp -o StrictHostKeyChecking=no "$LOCAL_SCRIPT" "$UISP_SERVER:$BOT_DIR/$BOT_SCRIPT"
echo "✓ Script subido"
echo ""

echo "[PASO 4] Iniciando bot en background..."
echo "ssh $UISP_SERVER \"cd $BOT_DIR && source bin/activate && nohup python3 $BOT_SCRIPT > monitor.log 2>&1 &\""
ssh -o StrictHostKeyChecking=no "$UISP_SERVER" "cd $BOT_DIR && source bin/activate && nohup python3 $BOT_SCRIPT > monitor.log 2>&1 &"
echo "✓ Bot iniciado"
echo ""

# Esperar a que el bot se inicie
echo "[PASO 5] Esperando 3 segundos para que el bot arranque..."
sleep 3
echo "✓ Hecho"
echo ""

echo "[PASO 6] Verificando que el bot está ejecutándose..."
RUNNING=$(ssh -o StrictHostKeyChecking=no "$UISP_SERVER" "ps aux | grep 'python3.*auralink_monitor' | grep -v grep | wc -l")

if [ "$RUNNING" -gt 0 ]; then
    echo "✓ Bot está ejecutándose ✅"
    echo ""
    echo "============================================================"
    echo "  ✅ DEPLOYMENT EXITOSO"
    echo "============================================================"
    echo ""
    echo "Bot Details:"
    echo "  - Servidor: $UISP_HOST"
    echo "  - Directorio: $BOT_DIR"
    echo "  - Script: $BOT_SCRIPT"
    echo ""

    echo "[PASO 7] Mostrando últimas 15 líneas del log..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ssh -o StrictHostKeyChecking=no "$UISP_SERVER" "tail -15 $BOT_DIR/monitor.log"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    echo "PRÓXIMOS PASOS:"
    echo ""
    echo "1. PROBAR EN TELEGRAM:"
    echo "   - Abre Telegram"
    echo "   - Busca: @auralinkmonitor_bot"
    echo "   - Envía: /start"
    echo "   - Deberías recibir un mensaje de bienvenida"
    echo ""

    echo "2. PROBAR COMANDOS:"
    echo "   - /status   → Muestra estadísticas"
    echo "   - /clients  → Lista de clientes"
    echo "   - /help     → Ayuda"
    echo ""

    echo "3. MONITOREAR LOGS EN TIEMPO REAL:"
    echo "   ssh uisp@10.1.1.254 'tail -f /home/uisp/auralink_monitor/monitor.log'"
    echo ""

    echo "4. SI ALGO FALLA:"
    echo "   ssh uisp@10.1.1.254 'tail -50 /home/uisp/auralink_monitor/monitor.log'"
    echo ""

    echo "============================================================"
    echo ""
else
    echo "❌ Bot NO está ejecutándose"
    echo ""
    echo "Mostrando últimas líneas del log para diagnóstico:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ssh -o StrictHostKeyChecking=no "$UISP_SERVER" "tail -30 $BOT_DIR/monitor.log" || echo "No se pudo leer el log"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    echo "DIAGNÓSTICO:"
    echo "1. Verifica la salida anterior buscando 'Error' o 'Exception'"
    echo "2. Prueba estas comandos:"
    echo "   ssh uisp@10.1.1.254 'ps aux | grep python'"
    echo "   ssh uisp@10.1.1.254 'ls -la /home/uisp/auralink_monitor/'"
    echo "   ssh uisp@10.1.1.254 'head -5 /home/uisp/auralink_monitor/auralink_monitor.py'"
    echo ""

    exit 1
fi
