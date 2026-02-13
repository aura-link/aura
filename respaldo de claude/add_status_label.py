#!/usr/bin/env python3
"""Add handed_to_driver status to status label/color functions"""

with open("/home/yesswera/yesswera-app-mobile/app/driver/active-order.tsx", "r") as f:
    content = f.read()

# 1. Add to status labels
old_labels = '''const labels: Record<string, string> = {
    pending: 'Pendiente',
    assigned: 'Asignada',
    accepted: 'Aceptada',
    confirmed: 'Confirmada',
    preparing: 'Preparando',
    ready: 'Lista',
    driver_verified: 'Verificado por Negocio',
    picked_up: 'En Camino',
    in_transit: 'En Camino al Cliente',
    delivered: 'Entregada',
    cancelled: 'Cancelada',
  };'''

new_labels = '''const labels: Record<string, string> = {
    pending: 'Pendiente',
    assigned: 'Asignada',
    accepted: 'Aceptada',
    confirmed: 'Confirmada',
    preparing: 'Preparando',
    ready: 'Lista',
    driver_verified: 'Verificado por Negocio',
    handed_to_driver: 'Orden Entregada',
    picked_up: 'En Camino',
    in_transit: 'En Camino al Cliente',
    delivered: 'Entregada',
    cancelled: 'Cancelada',
  };'''

content = content.replace(old_labels, new_labels)

# 2. Add to status colors
old_colors = '''if (status === 'driver_verified') return '#4CAF50';'''

new_colors = '''if (status === 'driver_verified' || status === 'handed_to_driver') return '#4CAF50';'''

content = content.replace(old_colors, new_colors)

with open("/home/yesswera/yesswera-app-mobile/app/driver/active-order.tsx", "w") as f:
    f.write(content)

print("Status labels updated with handed_to_driver")
