# Sistema de Suspensión PPPoE para MikroTik

## Problema Identificado
Las IPs de PPPoE son dinámicas. Cuando creas una regla mangle estática, y el cliente se desconecta, su IP cambia la próxima conexión y la regla se vuelve inútil.

---

## Soluciones Disponibles

### OPCIÓN 1: Script Manual PPPoE
**Archivo:** `suspension_pppoe.sh`

**Uso:**
```bash
./suspension_pppoe.sh add cliente_juan       # Suspender
./suspension_pppoe.sh remove cliente_juan    # Reactivar
./suspension_pppoe.sh list                    # Ver suspendidos
```

**Ventajas:**
- Fácil de usar
- Automático (obtiene IP actual)
- Sin dependencias

**Desventaja:**
- Si el cliente se desconecta/reconecta, necesitas ejecutar de nuevo

**Cuándo usar:** Clientes pequeños (<10), suspensiones cortas

---

### OPCIÓN 2: Script con Auto-Actualización (RECOMENDADA)
**Archivo:** `update_pppoe_suspension.sh`

**Instalación:**
```bash
# 1. Copiar script
sudo cp update_pppoe_suspension.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/update_pppoe_suspension.sh

# 2. Agregar a cron (ejecutar cada 5 minutos)
sudo crontab -e
```

**Agregar línea:**
```
*/5 * * * * /usr/local/bin/update_pppoe_suspension.sh
```

**Funciona así:**
1. Se ejecuta cada 5 minutos automáticamente
2. Busca usuarios con "PPPoE:" en el comentario de mangle rules
3. Obtiene su IP actual
4. Si cambió, actualiza la regla automáticamente
5. Registra todo en `/tmp/pppoe_suspension.log`

**Ventajas:**
- Totalmente automático
- Confiable y profesional
- Mantiene logs
- Escalable

**Cuándo usar:** Clientes medianos (10-50), suspensiones largas (días)

---

### OPCIÓN 3: Sistema Hotspot
**Para sistemas con muchos clientes (>50)**

No depende de IPs, funciona por usuario PPPoE nativo. Más complejo de configurar pero muy robusto.

---

## MI RECOMENDACIÓN: Opción 2

✓ Automático
✓ Confiable
✓ Mantiene sistema actual funcionando
✓ Fácil de mantener
✓ Escalable hasta 50+ clientes

---

## Pasos de Implementación (Opción 2)

### Paso 1: Preparar script
```bash
sudo cp update_pppoe_suspension.sh /usr/local/bin/
sudo chmod +x /usr/local/bin/update_pppoe_suspension.sh
```

### Paso 2: Instalar en cron
```bash
sudo crontab -e
```
Agregar:
```
*/5 * * * * /usr/local/bin/update_pppoe_suspension.sh
```

### Paso 3: Suspender cliente
```bash
# Con script manual
./suspension_pppoe.sh add usuario_juan

# O manualmente
ssh -o StrictHostKeyChecking=no admin@10.147.17.11 \
  "/ip firewall mangle add chain=prerouting src-address=192.168.x.x action=mark-packet new-packet-mark=suspended_traffic comment=\"PPPoE: usuario_juan\""
```

### Paso 4: Verificar logs
```bash
tail -f /tmp/pppoe_suspension.log
```

### Paso 5: Reactivar cliente
```bash
./suspension_pppoe.sh remove usuario_juan

# O manualmente
ssh -o StrictHostKeyChecking=no admin@10.147.17.11 \
  "/ip firewall mangle remove [find comment~\"usuario_juan\"]"
```

---

## Verificación

**Ver clientes suspendidos:**
```bash
ssh -o StrictHostKeyChecking=no admin@10.147.17.11 \
  "/ip firewall mangle print where comment~\"PPPoE:\""
```

**Ver logs:**
```bash
tail -f /tmp/pppoe_suspension.log
```

---

## Componentes del Sistema

### 1. Página HTML de Suspensión ✓
- Ubicación: MikroTik `/file/suspension.html`
- Tamaño: 2,483 bytes
- Estado: Activa

### 2. Servicio HTTP en Puerto 80 ✓
- Puerto: 80 (habilitado)
- Estado: Activo

### 3. Regla Mangle (Dinámico)
- Marca tráfico de clientes suspendidos
- Actualizado automáticamente cada 5 minutos

### 4. Regla NAT Redirect ✓
- Redirige HTTP a página de suspensión
- Estado: Activo

---

## Archivos Incluidos

1. **suspension_pppoe.sh** - Script manual para suspender/reactivar clientes
2. **update_pppoe_suspension.sh** - Script de auto-actualización (Cron)
3. **PPPOE_SUSPENSION_README.md** - Este archivo
4. **PPPOE_SOLUTION_SUMMARY.md** - Comparativa de soluciones

---

## Ejemplo de Uso Real

```bash
# Usuario en WISP: "cliente_juan" (usuario PPPoE)
# IP actual: 192.168.1.150 (dinámica)

# Suspender
./suspension_pppoe.sh add cliente_juan

# Output:
# === Suspendiendo cliente PPPoE ===
# Usuario: cliente_juan
# [1/3] Obteniendo IP actual del usuario PPPoE...
# ✓ IP encontrada: 192.168.1.150
# [2/3] Creando regla de suspensión...
# ✓ Regla mangle creada
# [3/3] Verificando configuración...
#
# ═══════════════════════════════════
# ✓ Cliente suspendido exitosamente
# ═══════════════════════════════════
#
# Usuario PPPoE: cliente_juan
# IP Actual: 192.168.1.150
# Estado: SUSPENDIDO

# Si se desconecta y se reconecta con nueva IP (192.168.1.200)
# El script de cron actualiza automáticamente:
# [2025-11-14 15:00:00] Procesando usuario: cliente_juan
# [2025-11-14 15:00:00] ✓ IP actual: 192.168.1.200
# [2025-11-14 15:00:00] ! Cambio detectado: 192.168.1.150 → 192.168.1.200
# [2025-11-14 15:00:00] - Regla antigua removida
# [2025-11-14 15:00:00] + Regla nueva creada con IP 192.168.1.200

# Reactivar
./suspension_pppoe.sh remove cliente_juan
```

---

## Notas Importantes

1. **El cliente debe estar conectado** cuando ejecutas el script
2. **Con cron, se actualiza cada 5 minutos** - puedes cambiar el tiempo
3. **Los logs se guardan en** `/tmp/pppoe_suspension.log`
4. **Sistema totalmente compatible** con la página de suspensión existente

---

## Troubleshooting

**Problema:** Script no funciona
```bash
# Verificar permisos
chmod +x suspension_pppoe.sh

# Verificar conexión SSH
ssh -o StrictHostKeyChecking=no admin@10.147.17.11 "id"
```

**Problema:** Cron no se ejecuta
```bash
# Verificar cron
sudo crontab -l

# Ver logs de cron
sudo tail -f /var/log/syslog | grep CRON
```

**Problema:** Cliente no ve la página
```bash
# Verificar regla
ssh -o StrictHostKeyChecking=no admin@10.147.17.11 \
  "/ip firewall mangle print where comment~\"PPPoE:\""

# Verificar NAT
ssh -o StrictHostKeyChecking=no admin@10.147.17.11 \
  "/ip firewall nat print where action=redirect"
```

---

## Próximos Pasos

1. ✓ Sistema de suspensión está funcionando
2. ✓ Página HTML lista
3. ✓ Reglas MikroTik configuradas
4. **Próximo:** Implementar Opción 2 (Cron) para auto-actualización
5. **Futuro:** Integrar con sistema de facturación

---

**Estado del Sistema:** ✓ OPERATIVO

Creado: 2025-11-14
Última actualización: 2025-11-14
Versión: 1.0
