"""Monitor de red: poll UISP cada N segundos, detecta cambios, dispara eventos."""

import asyncio
import time
from datetime import datetime, timezone
from src import config
from src.utils.logger import log
from src.monitoring.zones import ZoneMapper
from src.monitoring.notifications import NotificationSender


def _device_status(device: dict) -> str:
    overview = device.get("overview", {}) or {}
    return (overview.get("status") or device.get("status") or "unknown").lower()


def _device_role(device: dict) -> str:
    ident = device.get("identification", {}) or {}
    return (ident.get("role") or "").lower()


def _device_name(device: dict) -> str:
    ident = device.get("identification", {}) or {}
    return ident.get("name") or ident.get("hostname") or "sin nombre"


def _device_ip(device: dict) -> str:
    return (device.get("ipAddress") or "").split("/")[0]


def _device_site_id(device: dict) -> str | None:
    ident = device.get("identification", {}) or {}
    site = ident.get("site")
    if isinstance(site, dict):
        return site.get("id")
    return site


def _format_duration(seconds: float) -> str:
    mins = int(seconds // 60)
    if mins < 60:
        return f"{mins} min"
    hours = mins // 60
    mins = mins % 60
    return f"{hours}h {mins}m"


class NetworkMonitor:
    """Monitor de red que detecta caidas de infraestructura con anti-flap."""

    # Solo monitorear dispositivos con estos roles (infraestructura)
    INFRA_ROLES = {"ap", "router", "switch", "gateway", "wireless"}

    def __init__(self, nms, db, zone_mapper: ZoneMapper, notifier: NotificationSender):
        self.nms = nms
        self.db = db
        self.zone_mapper = zone_mapper
        self.notifier = notifier
        self._running = False
        self._task: asyncio.Task | None = None
        self._pending_downs: dict[str, float] = {}  # device_id -> timestamp del primer down
        self._last_zone_rebuild = 0.0
        self.last_poll_time: float | None = None
        self.tracked_devices = 0

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self):
        if self._running:
            return
        self._running = True
        # Rebuild zonas al arrancar
        await self.zone_mapper.rebuild()
        self._last_zone_rebuild = time.time()
        self._task = asyncio.create_task(self._poll_loop())
        log.info("Network monitor started (interval=%ds)", config.MONITOR_INTERVAL)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        log.info("Network monitor stopped")

    async def _poll_loop(self):
        """Loop principal: poll cada MONITOR_INTERVAL segundos."""
        # Esperar un poco para que el bot termine de inicializarse
        await asyncio.sleep(5)
        while self._running:
            try:
                await self._poll()
            except Exception as e:
                log.error("Monitor poll error: %s", e)
            await asyncio.sleep(config.MONITOR_INTERVAL)

    async def _poll(self):
        """Un ciclo de polling: obtiene dispositivos y compara con estado previo."""
        now = time.time()

        # Rebuild zonas periodicamente
        if now - self._last_zone_rebuild > config.ZONE_REFRESH_INTERVAL:
            await self.zone_mapper.rebuild()
            self._last_zone_rebuild = now

        # Obtener dispositivos frescos
        devices = await self.nms.get_devices_fresh()
        if not devices:
            log.warning("Monitor: no se obtuvieron dispositivos")
            return

        self.last_poll_time = now

        # Filtrar solo infraestructura
        infra_devices = [
            d for d in devices
            if _device_role(d) in self.INFRA_ROLES
        ]
        self.tracked_devices = len(infra_devices)

        for device in infra_devices:
            dev_id = device.get("id", "")
            if not dev_id:
                continue

            current_status = _device_status(device)
            name = _device_name(device)
            ip = _device_ip(device)
            site_id = _device_site_id(device)
            role = _device_role(device)

            # Obtener estado previo
            prev = await self.db.get_device_state(dev_id)
            prev_status = prev["status"] if prev else None

            # Actualizar estado en DB
            await self.db.upsert_device_state(dev_id, name, ip, site_id, current_status, role)

            if prev_status is None:
                # Primera vez que vemos este dispositivo, solo registrar
                continue

            # Detectar cambio
            was_up = prev_status == "active"
            is_up = current_status == "active"

            if was_up and not is_up:
                # Transicion a down → anti-flap: marcar como pending
                if dev_id not in self._pending_downs:
                    self._pending_downs[dev_id] = now
                    log.info("Monitor: %s (%s) down - pending confirmation", name, ip)

            elif not was_up and is_up:
                # Transicion a up → recovery
                if dev_id in self._pending_downs:
                    # Era pending, se recupero → flap, descartar
                    del self._pending_downs[dev_id]
                    log.info("Monitor: %s (%s) recovered (flap descartado)", name, ip)
                else:
                    # Era un incidente confirmado → resolver
                    await self._handle_recovery(dev_id, name, site_id)

        # Confirmar pending downs que persisten
        confirmed = []
        for dev_id, ts in list(self._pending_downs.items()):
            if now - ts >= config.MONITOR_INTERVAL:
                confirmed.append(dev_id)

        for dev_id in confirmed:
            del self._pending_downs[dev_id]
            state = await self.db.get_device_state(dev_id)
            if state and state["status"] != "active":
                await self._handle_outage(
                    dev_id, state["device_name"],
                    state["site_id"], state["device_ip"],
                )

        # Commit de estados en batch
        await self.db.commit()

        # Check mantenimientos pendientes de notificar
        await self._check_maintenance_notifications()

    async def _handle_outage(self, device_id: str, device_name: str,
                              site_id: str | None, device_ip: str):
        """Maneja confirmacion de caida de infraestructura."""
        # Verificar que no haya incidente activo ya
        existing = await self.db.get_incident_by_device(device_id)
        if existing:
            return

        # Obtener clientes afectados
        affected = []
        site_name = ""
        if site_id:
            affected = await self.zone_mapper.get_affected_clients(site_id)
            # Obtener nombre del sitio
            states = await self.db.get_zone_summary()
            for z in states:
                if z["infra_site_id"] == site_id:
                    site_name = z.get("infra_site_name", "")
                    break

        if not site_name:
            site_name = device_name

        # Crear incidente
        incident_id = await self.db.create_incident(
            device_id, device_name, site_id, site_name, len(affected),
        )
        ref_id = str(incident_id)

        log.warning("INCIDENTE #%d: %s (%s) en zona %s, %d clientes afectados",
                     incident_id, device_name, device_ip, site_name, len(affected))

        # Notificar admins
        ts = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
        await self.notifier.notify_admins(
            "outage_admin", ref_id,
            device_name=device_name, zone_name=site_name,
            affected_count=len(affected), timestamp=ts,
        )

        # Notificar clientes afectados
        if affected:
            sent = await self.notifier.notify_affected_clients(
                affected, "outage_client", ref_id, zone_name=site_name,
            )
            log.info("Notificados %d/%d clientes del incidente #%d",
                     sent, len(affected), incident_id)

    async def _handle_recovery(self, device_id: str, device_name: str,
                                site_id: str | None):
        """Maneja recuperacion de un dispositivo."""
        incident = await self.db.get_incident_by_device(device_id)
        if not incident:
            return

        incident_id = incident["id"]
        site_name = incident.get("site_name", device_name)

        # Calcular duracion
        started = incident.get("started_at", "")
        duration_str = ""
        if started:
            try:
                start_dt = datetime.fromisoformat(started)
                duration_secs = (datetime.now() - start_dt).total_seconds()
                duration_str = _format_duration(duration_secs)
            except (ValueError, TypeError):
                duration_str = "desconocida"

        # Resolver incidente
        await self.db.resolve_incident(incident_id)
        ref_id = str(incident_id)

        log.info("RECUPERADO incidente #%d: %s, duracion: %s",
                 incident_id, device_name, duration_str)

        # Notificar admins
        await self.notifier.notify_admins(
            "recovery_admin", f"recovery_{ref_id}",
            device_name=device_name, zone_name=site_name,
            duration=duration_str or "N/A",
        )

        # Notificar clientes
        if site_id:
            clients = await self.zone_mapper.get_affected_clients(site_id)
            if clients:
                await self.notifier.notify_affected_clients(
                    clients, "recovery_client", f"recovery_{ref_id}",
                    zone_name=site_name,
                )

    async def _check_maintenance_notifications(self):
        """Notifica mantenimientos proximos que aun no se notificaron."""
        pending = await self.db.get_pending_maintenance()
        for mw in pending:
            site_id = mw.get("site_id")
            site_name = mw.get("site_name", "")
            description = mw.get("description", "Mantenimiento de red")
            start_time = mw.get("starts_at", "")
            end_time = mw.get("ends_at", "")
            mw_id = mw["id"]

            # Formato de fechas
            try:
                st = datetime.fromisoformat(start_time)
                start_fmt = st.strftime("%d/%m/%Y %H:%M")
            except (ValueError, TypeError):
                start_fmt = start_time
            try:
                et = datetime.fromisoformat(end_time)
                end_fmt = et.strftime("%d/%m/%Y %H:%M")
            except (ValueError, TypeError):
                end_fmt = end_time

            # Notificar admins
            notified_count = 0
            if site_id:
                clients = await self.zone_mapper.get_affected_clients(site_id)
                notified_count = await self.notifier.notify_affected_clients(
                    clients, "maintenance_client", f"maint_{mw_id}",
                    zone_name=site_name, start_time=start_fmt,
                    end_time=end_fmt, description=description,
                )

            await self.notifier.notify_admins(
                "maintenance_admin", f"maint_{mw_id}",
                zone_name=site_name or "General",
                start_time=start_fmt, end_time=end_fmt,
                description=description, notified_count=notified_count,
            )

            await self.db.mark_maintenance_notified(mw_id)
            log.info("Mantenimiento #%d notificado (%d clientes)", mw_id, notified_count)
