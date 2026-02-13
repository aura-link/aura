# AURALINK Monitor - Guía de Despliegue Paso a Paso

## ✅ QUÉ YA ESTÁ HECHO

- ✓ Virtual environment creado en `/home/uisp/auralink_monitor`
- ✓ Todas las dependencias Python instaladas
- ✓ Script `auralink_monitor.py` listo y copiado al servidor
- ✓ Archivo de servicio `auralink-monitor.service` preparado
- ✓ Credenciales UISP y Telegram configuradas

---

## 🚀 PASOS PARA INICIAR EL BOT

### OPCIÓN A: Inicio manual (para testing)

```bash
# 1. Conectarse al servidor UISP
ssh uisp@10.1.1.254

# 2. Activar el virtual environment
source /home/uisp/auralink_monitor/bin/activate

# 3. Ejecutar el script
python3 /home/uisp/auralink_monitor/auralink_monitor.py
```

**Resultado esperado:**
```
🚀 Iniciando AURALINK Monitor Bot...
✓ Bot iniciado correctamente
✓ Esperando mensajes en Telegram...
```

El bot ahora está esperando mensajes en Telegram.

---

### OPCIÓN B: Instalación como servicio systemd (recomendado - 24/7)

**Ejecutar SOLO UNA VEZ:**

```bash
# 1. Conectarse al servidor con sudo
ssh uisp@10.1.1.254

# 2. Instalar el servicio (necesita sudo)
sudo cp /home/uisp/auralink-monitor.service /etc/systemd/system/

# 3. Recargar systemd
sudo systemctl daemon-reload

# 4. Habilitar el servicio (autostart)
sudo systemctl enable auralink-monitor.service

# 5. Iniciar el servicio
sudo systemctl start auralink-monitor.service

# 6. Verificar que está corriendo
sudo systemctl status auralink-monitor.service
```

**Resultado esperado:**
```
● auralink-monitor.service - AURALINK Monitor - Telegram Bot para UISP
     Loaded: loaded (/etc/systemd/system/auralink-monitor.service; enabled; preset: enabled)
     Active: active (running) since ...
     ...
```

---

## 📱 PRUEBAS EN TELEGRAM

### 1. Abrir Telegram

Busca **@auralinkmonitor_bot** o accede directamente:
https://t.me/auralinkmonitor_bot

### 2. Enviar /start

```
Tú: /start

Bot: 🌐 AURALINK Monitor
     Monitoreo inteligente de UISP vía Telegram + IA
     ...
```

### 3. Probar comandos

```
Tú: /status

Bot: ✅ Estado AURALINK Monitor
     📊 Estadísticas:
     • Clientes activos: XX/XX
     • Dispositivos: XX
     • Servidor UISP: 🟢 Online
```

### 4. Probar búsqueda de cliente

```
Tú: ¿Cuál es la IP del cliente Zuri?

Bot: ✅ Cliente Encontrado
     Nombre: Zuri
     ID: ...
     Estado: 🟢 Activo
     Ubicación: La Gloria
```

---

## 🔍 MONITOREO Y LOGS

### Ver logs en tiempo real:

```bash
sudo journalctl -u auralink-monitor -f
```

### Ver últimas líneas de logs:

```bash
sudo journalctl -u auralink-monitor -n 50
```

### Ver logs guardados en archivo:

```bash
tail -f /home/uisp/auralink_monitor/monitor.log
```

---

## 🛠️ COMANDOS DE MANTENIMIENTO

### Detener el bot:
```bash
sudo systemctl stop auralink-monitor.service
```

### Reiniciar el bot:
```bash
sudo systemctl restart auralink-monitor.service
```

### Ver estado actual:
```bash
sudo systemctl status auralink-monitor.service
```

### Ver si se inició correctamente:
```bash
sudo systemctl is-active auralink-monitor.service
```

---

## ⚠️ TROUBLESHOOTING

### El bot no responde en Telegram

1. **Verificar que el servicio está corriendo:**
```bash
sudo systemctl status auralink-monitor
```

2. **Verificar logs:**
```bash
sudo journalctl -u auralink-monitor -n 100
```

3. **Comprobar conectividad a UISP:**
```bash
ping 10.1.1.254
curl -k https://10.1.1.254/api/v2.1/user/login
```

4. **Reiniciar manualmente:**
```bash
sudo systemctl restart auralink-monitor
```

### Error "UISP API not responding"

```bash
# Verificar credenciales y conectividad
ssh uisp@10.1.1.254
curl -k -X POST https://10.1.1.254/api/v2.1/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"AURALINK","password":"1234"}'
```

### Bot autoriza pero no entiende comandos

- Verificar que el usuario está en `AUTHORIZED_USERS`
- El primer usuario que envía `/start` se autoriza automáticamente
- Para más usuarios, editar el script

---

## 📋 CHECKLIST DE INSTALACIÓN

- [ ] SSH al servidor UISP funciona (`ssh uisp@10.1.1.254`)
- [ ] Virtual environment existe en `/home/uisp/auralink_monitor`
- [ ] Dependencias Python instaladas (`pip3 list | grep telegram`)
- [ ] Script `auralink_monitor.py` copiado y ejecutable
- [ ] Archivo de servicio en `/home/uisp/auralink-monitor.service`
- [ ] Servicio registrado en systemd
- [ ] Servicio está corriendo (`systemctl status`)
- [ ] Bot responde en Telegram (`/start`)
- [ ] Comandos funcionan (`/status`, `/clients`)
- [ ] Búsqueda de clientes funciona

---

## 🎯 PRÓXIMOS PASOS

Una vez el bot esté funcionando:

1. **Probar todos los comandos** en Telegram
2. **Verificar logs** para errores
3. **Agregar más usuarios** si es necesario
4. **Configurar alertas automáticas** (próxima versión)
5. **Implementar gráficas** de consumo
6. **Integrar IA** para consultas más complejas

---

## 📞 SOPORTE RÁPIDO

| Problema | Solución |
|----------|----------|
| Bot no inicia | `sudo journalctl -u auralink-monitor -n 50` |
| No conecta a UISP | Verificar credenciales y ping a 10.1.1.254 |
| Usuario no autorizado | Enviar `/start` al bot primero |
| Servicio no inicia | Verificar permisos: `ls -la /home/uisp/auralink_monitor/` |

---

**Documento creado:** 2025-11-30
**Versión:** 1.0
**Estado:** ✅ LISTO PARA DESPLEGAR

