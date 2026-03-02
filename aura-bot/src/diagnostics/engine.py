"""Motor de diagnostico unificado: CRM + UISP + MikroTik + Ping en un solo paso."""

import asyncio
from dataclasses import dataclass, field
from src.utils.logger import log


@dataclass
class DiagnosticResult:
    client_name: str = ""
    client_id: str = ""
    # CRM service
    service_plan: str = ""
    service_status: str = ""  # "active" / "suspended" / "ended"
    # UISP device
    device_found: bool = False
    device_name: str = ""
    device_model: str = ""
    device_status: str = ""  # "active" / "disconnected"
    device_ip: str = ""
    signal_dbm: int | None = None
    firmware: str = ""
    # PPPoE MikroTik
    pppoe_active: bool = False
    pppoe_username: str = ""
    pppoe_uptime: str = ""
    pppoe_profile: str = ""
    pppoe_mac: str = ""
    # Ping
    ping_success: bool = False
    ping_avg_ms: int | None = None
    ping_received: int = 0
    ping_sent: int = 0
    # Zone
    zone_incident: bool = False
    zone_maintenance: bool = False
    zone_name: str = ""
    # Result
    issues: list[str] = field(default_factory=list)
    severity: str = "none"  # none / low / medium / high / critical
    error: str = ""


class DiagnosticEngine:
    def __init__(self, nms, crm, mk, db):
        self.nms = nms
        self.crm = crm
        self.mk = mk
        self.db = db

    async def diagnose(self, crm_client_id: str, client_name: str = "") -> DiagnosticResult:
        """Ejecuta diagnostico completo: CRM → UISP → PPPoE + Ping → Clasificacion."""
        result = DiagnosticResult(client_name=client_name, client_id=crm_client_id)

        try:
            # Step 1: CRM service info
            await self._check_crm(result)

            # Step 2: UISP device info
            await self._check_uisp(result)

            # Step 3+4: PPPoE + Ping in parallel (if we have an IP)
            if result.device_ip and self.mk:
                pppoe_task = self._check_pppoe(result)
                ping_task = self._check_ping(result)
                await asyncio.gather(pppoe_task, ping_task, return_exceptions=True)

            # Step 5: Zone incidents
            await self._check_zone(result)

            # Step 6: Classify
            self._classify(result)

        except Exception as e:
            log.error("DiagnosticEngine error for client %s: %s", crm_client_id, e)
            result.error = str(e)
            result.severity = "none"  # fallback to Claude

        return result

    async def _check_crm(self, r: DiagnosticResult):
        """Obtiene plan y status del servicio CRM."""
        services = await self.crm.get_client_services(r.client_id)
        for svc in services:
            status_code = svc.get("status")
            r.service_plan = svc.get("servicePlanName") or "Sin plan"
            r.service_status = _svc_status(status_code)
            # Get the unmsClientSiteId for UISP lookup
            svc_detail = await self.crm.get_service(str(svc.get("id", "")))
            if svc_detail:
                r._unms_site_id = svc_detail.get("unmsClientSiteId")
            break  # first service

    async def _check_uisp(self, r: DiagnosticResult):
        """Obtiene estado de la antena desde UISP NMS."""
        site_id = getattr(r, "_unms_site_id", None)
        if not site_id:
            return

        device = await self.nms.find_device_by_site_id(site_id)
        if not device:
            return

        r.device_found = True
        overview = device.get("overview", {}) or {}
        ident = device.get("identification", {}) or {}

        r.device_name = ident.get("name", "")
        r.device_model = ident.get("model", "")
        r.device_status = (overview.get("status") or "unknown").lower()
        r.firmware = ident.get("firmwareVersion") or ""

        signal = overview.get("signal")
        if signal is not None:
            try:
                r.signal_dbm = int(signal)
            except (ValueError, TypeError):
                pass

        ip = (device.get("ipAddress") or "").split("/")[0]
        r.device_ip = ip

    async def _check_pppoe(self, r: DiagnosticResult):
        """Busca sesion PPPoE activa por IP."""
        try:
            session = await self.mk.find_session_by_ip(r.device_ip)
            if session:
                r.pppoe_active = True
                r.pppoe_username = session.get("name", "")
                r.pppoe_uptime = session.get("uptime", "")
                r.pppoe_profile = session.get("service", "")
                r.pppoe_mac = session.get("caller-id", "")
        except Exception as e:
            log.warning("PPPoE check error for %s: %s", r.device_ip, e)

    async def _check_ping(self, r: DiagnosticResult):
        """Hace ping desde MikroTik a la antena."""
        try:
            ping = await self.mk.ping(r.device_ip, count=3)
            r.ping_success = ping.get("success", False)
            r.ping_avg_ms = ping.get("avg_rtt")
            r.ping_received = ping.get("received", 0)
            r.ping_sent = ping.get("sent", 3)
        except Exception as e:
            log.warning("Ping check error for %s: %s", r.device_ip, e)

    async def _check_zone(self, r: DiagnosticResult):
        """Checa incidentes/mantenimiento activos en la zona del cliente."""
        if not self.db:
            return
        try:
            incident = await self.db.get_active_incident_for_client(r.client_id)
            if incident:
                r.zone_incident = True
                r.zone_name = incident.get("site_name", "")

            maint = await self.db.get_maintenance_for_client(r.client_id)
            if maint:
                r.zone_maintenance = True
                if not r.zone_name:
                    r.zone_name = maint.get("site_name", "")
        except Exception as e:
            log.warning("Zone check error for client %s: %s", r.client_id, e)

    def _classify(self, r: DiagnosticResult):
        """Clasifica severidad segun arbol de decision."""
        issues = []

        # Critical: zone incident/maintenance
        if r.zone_incident:
            issues.append("Interrupcion activa en tu zona")
            r.issues = issues
            r.severity = "critical"
            return
        if r.zone_maintenance:
            issues.append("Mantenimiento en curso en tu zona")
            r.issues = issues
            r.severity = "critical"
            return

        # Critical: suspended
        if r.service_status == "suspended":
            issues.append("Servicio suspendido por falta de pago")
            r.issues = issues
            r.severity = "critical"
            return

        # High: device offline + no PPPoE
        if r.device_found and r.device_status != "active" and not r.pppoe_active:
            issues.append("Antena desconectada")
            issues.append("Sin sesion PPPoE")
            r.issues = issues
            r.severity = "high"
            return

        # High: device online but no PPPoE
        if r.device_found and r.device_status == "active" and not r.pppoe_active:
            issues.append("Antena encendida pero sin conexion PPPoE")
            r.issues = issues
            r.severity = "high"
            return

        # High: PPPoE active but ping fails
        if r.pppoe_active and not r.ping_success:
            issues.append("Conexion activa pero sin respuesta a ping")
            r.issues = issues
            r.severity = "high"
            return

        # Medium: weak signal
        if r.signal_dbm is not None and r.signal_dbm < -80:
            issues.append(f"Senal debil: {r.signal_dbm} dBm")

        # Medium: high latency
        if r.ping_avg_ms is not None and r.ping_avg_ms > 100:
            issues.append(f"Latencia alta: {r.ping_avg_ms} ms")

        # Medium: packet loss
        if r.ping_sent > 0 and r.ping_received < r.ping_sent:
            loss_pct = round((1 - r.ping_received / r.ping_sent) * 100)
            issues.append(f"Perdida de paquetes: {loss_pct}%")

        r.issues = issues
        if issues:
            r.severity = "medium"
        else:
            r.severity = "none"


def _svc_status(code: int | None) -> str:
    mapping = {0: "prepared", 1: "active", 2: "ended", 3: "suspended",
               4: "prepared_blocked", 5: "obsolete", 6: "deferred", 7: "quoted"}
    return mapping.get(code or 0, "unknown")
