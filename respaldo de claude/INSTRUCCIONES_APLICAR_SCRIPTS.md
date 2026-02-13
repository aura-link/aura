# Instrucciones para Aplicar Scripts en MikroTik

## 📋 PASOS A SEGUIR

### PASO 1: Conectarte por SSH al router

```bash
ssh admin@10.147.17.11
# Contraseña: 1234
```

---

### PASO 2: Aplicar SCRIPT 2 (Routing Marks)

**Abre el archivo**: `SCRIPT_2_ROUTING_MARKS.txt`

**Copia TODOS los comandos** (desde `/ip route add...` hasta `/ip route print...`)

**Pégalos en la terminal SSH del MikroTik**:

```
[admin@Balanceador] > /ip route add dst-address=0.0.0.0/0 gateway=192.168.40.1 routing-mark=to_isp1
[admin@Balanceador] > /ip route add dst-address=0.0.0.0/0 gateway=192.169.1.1 routing-mark=to_isp2
... (continúa con los demás)
[admin@Balanceador] > /ip route print where routing-mark!=main
```

**Esperado**: Deberías ver 9 rutas con routing-mark (to_isp1 hasta to_isp9)

---

### PASO 3: Aplicar SCRIPT 3 (Failover Health Check)

**Abre el archivo**: `SCRIPT_3_FAILOVER_HEALTH_CHECK.txt`

**Copia TODOS los comandos** (desde `/tool netwatch add...` hasta `/tool netwatch print`)

**Pégalos en la terminal SSH del MikroTik**:

```
[admin@Balanceador] > /tool netwatch add host=192.168.40.1 comment="WAN3-Presidencia" interval=10s timeout=3s down-script=...
[admin@Balanceador] > /tool netwatch add host=192.169.1.1 comment="WAN4-Presidencia" interval=10s timeout=3s down-script=...
... (continúa con los demás)
[admin@Balanceador] > /tool netwatch print
```

**Esperado**: Deberías ver 9 health checks (uno para cada ISP)

---

### PASO 4: Verificar que todo funciona

Ejecuta esto en la terminal SSH:

```
/ip route print where routing-mark!=main
/tool netwatch print
```

**Deberías ver**:
- 9 rutas con routing-mark (to_isp1 a to_isp9)
- 9 health checks (uno por cada gateway)

---

## 🎯 QUÉ HACE CADA SCRIPT

### SCRIPT 2: Routing Marks
- Crea rutas para cada ISP con su routing-mark específico
- Permite que el tráfico marcado en mangle vaya al ISP correcto
- **Resultado**: Balanceo real entre 9 ISPs

### SCRIPT 3: Failover Automático
- Monitorea cada gateway con ping cada 10 segundos
- Si un gateway no responde en 3 segundos, desactiva las rutas
- Cuando vuelve a responder, reactiva las rutas automáticamente
- **Resultado**: Failover automático sin intervención manual

---

## ⚠️ IMPORTANTE

### Antes de aplicar:

1. **Haz un backup:**
   ```
   /system backup save name=backup_antes_cambios_$(date)
   ```

2. **Verifica que todos los gateways responden:**
   ```
   /ping 192.168.40.1
   /ping 192.169.1.1
   /ping 192.168.4.1
   # ... etc para todos
   ```

3. **No copies líneas vacías** - MikroTik puede dar errores

---

## 🔍 CÓMO TESTEAR DESPUÉS

1. **Prueba que el balanceo funciona:**
   - Abre múltiples navegadores desde diferentes clientes
   - Cada uno debería ir a un ISP diferente

2. **Prueba failover:**
   - Desconecta WAN3 (o un ISP)
   - Espera 10 segundos
   - La ruta debería desactivarse automáticamente
   - El tráfico debería ir a otro ISP

3. **Verifica logs:**
   ```
   /log print where message~"netwatch"
   ```

---

## 📞 SI ALGO FALLA

1. **Error en routing:** Verifica que los gateways existen
   ```
   /ip address print
   ```

2. **Netwatch no funciona:** Verifica que los hosts responden
   ```
   /ping 192.168.40.1
   ```

3. **Necesitas revertir:** Restaura el backup
   ```
   /system backup restore name=backup_antes_cambios
   ```

---

## 📂 ARCHIVOS INCLUIDOS

- `SCRIPT_2_ROUTING_MARKS.txt` - Crear rutas con routing-mark
- `SCRIPT_3_FAILOVER_HEALTH_CHECK.txt` - Configurar failover automático
- `INSTRUCCIONES_APLICAR_SCRIPTS.md` - Este archivo

---

**¿Necesitas ayuda con algo específico?**

Cuando hayas ejecutado los scripts, avísame y verificamos que todo funcione correctamente.
