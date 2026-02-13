#!/bin/bash
# Script para instalar el servicio AURALINK Monitor en systemd
# Ejecutar con: sudo bash INSTALAR_SERVICIO.sh

set -e

echo "=========================================="
echo "Instalando AURALINK Monitor como servicio"
echo "=========================================="

# Copiar archivo de servicio
sudo cp /home/uisp/auralink-monitor.service /etc/systemd/system/auralink-monitor.service
echo "✓ Archivo de servicio copiado"

# Recargar systemd
sudo systemctl daemon-reload
echo "✓ Systemd reloaded"

# Habilitar servicio
sudo systemctl enable auralink-monitor.service
echo "✓ Servicio habilitado (iniciará al arrancar)"

# Iniciar servicio
sudo systemctl start auralink-monitor.service
echo "✓ Servicio iniciado"

# Verificar estado
echo ""
echo "Estado del servicio:"
sudo systemctl status auralink-monitor.service --no-pager

echo ""
echo "=========================================="
echo "✓ Instalación completada exitosamente"
echo "=========================================="
echo ""
echo "Comandos útiles:"
echo "  Ver logs:       sudo journalctl -u auralink-monitor -f"
echo "  Detener:        sudo systemctl stop auralink-monitor"
echo "  Reiniciar:      sudo systemctl restart auralink-monitor"
echo "  Estado:         sudo systemctl status auralink-monitor"
echo ""
