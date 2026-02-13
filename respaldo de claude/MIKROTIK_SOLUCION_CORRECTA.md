# MikroTik RouterOS 7.19.2 - Solución Correcta para SSH

## 🔍 PROBLEMA IDENTIFICADO

Tu router es:
- **Versión**: RouterOS 7.19.2 (stable)
- **Hardware**: RB5009UG+S+
- **SSH**: Activo pero con limitaciones en terminal interactiva

## ✅ SOLUCIÓN CORRECTA

MikroTik **NO permite heredoc con múltiples comandos interactivos por SSH**.

**Las opciones que SÍ funcionan:**

### OPCIÓN 1: Ejecutar comandos uno por uno (RECOMENDADO)

En tu terminal SSH, ejecuta **cada comando por separado**:

```bash
# Paso 1: Crear rutas con routing-mark

ssh admin@10.147.17.11 "/ip route add dst-address=0.0.0.0/0 gateway=192.168.40.1 routing-mark=to_isp1"
ssh admin@10.147.17.11 "/ip route add dst-address=0.0.0.0/0 gateway=192.169.1.1 routing-mark=to_isp2"
ssh admin@10.147.17.11 "/ip route add dst-address=0.0.0.0/0 gateway=192.168.4.1 routing-mark=to_isp3"
ssh admin@10.147.17.11 "/ip route add dst-address=0.0.0.0/0 gateway=192.168.1.1 routing-mark=to_isp4"
ssh admin@10.147.17.11 "/ip route add dst-address=0.0.0.0/0 gateway=192.168.2.1 routing-mark=to_isp5"
ssh admin@10.147.17.11 "/ip route add dst-address=0.0.0.0/0 gateway=192.168.201.1 routing-mark=to_isp6"
ssh admin@10.147.17.11 "/ip route add dst-address=0.0.0.0/0 gateway=100.64.0.1 routing-mark=to_isp7"
ssh admin@10.147.17.11 "/ip route add dst-address=0.0.0.0/0 gateway=192.168.5.1 routing-mark=to_isp8"
ssh admin@10.147.17.11 "/ip route add dst-address=0.0.0.0/0 gateway=192.168.101.1 routing-mark=to_isp9"

# Verificar
ssh admin@10.147.17.11 "/ip route print where routing-mark!=main"
```

**Te pedirá la contraseña (1234) para cada comando.**

---

### OPCIÓN 2: Usar archivo script .rsc en el router (MEJOR)

1. **Conecta por SSH interactivo:**
   ```bash
   ssh admin@10.147.17.11
   # Contraseña: 1234
   ```

2. **En la terminal SSH, crea un script con el editor built-in:**
   ```
   /file
   add name=routes.rsc contents="/ip route add dst-address=0.0.0.0/0 gateway=192.168.40.1 routing-mark=to_isp1\n/ip route add dst-address=0.0.0.0/0 gateway=192.169.1.1 routing-mark=to_isp2\n..."
   ```

3. **O simplemente pega en la terminal (LÍNEA POR LÍNEA):**
   ```
   [admin@Balanceador] > /ip route add dst-address=0.0.0.0/0 gateway=192.168.40.1 routing-mark=to_isp1
   [admin@Balanceador] > /ip route add dst-address=0.0.0.0/0 gateway=192.169.1.1 routing-mark=to_isp2
   [admin@Balanceador] > /ip route add dst-address=0.0.0.0/0 gateway=192.168.4.1 routing-mark=to_isp3
   [admin@Balanceador] > /ip route add dst-address=0.0.0.0/0 gateway=192.168.1.1 routing-mark=to_isp4
   [admin@Balanceador] > /ip route add dst-address=0.0.0.0/0 gateway=192.168.2.1 routing-mark=to_isp5
   [admin@Balanceador] > /ip route add dst-address=0.0.0.0/0 gateway=192.168.201.1 routing-mark=to_isp6
   [admin@Balanceador] > /ip route add dst-address=0.0.0.0/0 gateway=100.64.0.1 routing-mark=to_isp7
   [admin@Balanceador] > /ip route add dst-address=0.0.0.0/0 gateway=192.168.5.1 routing-mark=to_isp8
   [admin@Balanceador] > /ip route add dst-address=0.0.0.0/0 gateway=192.168.101.1 routing-mark=to_isp9
   ```

---

### OPCIÓN 3: Usar WinBox (RECOMENDADO para no técnicos)

1. Descarga WinBox desde https://mikrotik.com/download
2. Conéctate a 10.147.17.11
3. Ve a IP → Routes
4. Agrega 9 rutas con click en "+"
5. Rellena los datos y aplica

---

## 🎯 YO PUEDO HACERLO - OPCIÓN 4

Dame permisos y yo lo hago ejecutando cada comando uno por uno via SSH automáticamente.

¿Prefieres que lo haga así?

---

## 📝 RESUMEN FINAL

Para tu **RouterOS 7.19.2**:

✅ **MEJOR OPCIÓN**: Pega línea por línea en terminal SSH interactiva
✅ **ALTERNATIVA**: Usa WinBox (interfaz gráfica)
✅ **AUTOMATIZADO**: Yo lo ejecuto via SSH comando por comando

¿Cuál prefieres?
