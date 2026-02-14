"""Ejecuta tool calls de Claude despachando a las integraciones correctas."""

import json
from src.utils.formatting import format_mxn, format_signal, format_speed, status_emoji
from src.utils.logger import log


class ToolExecutor:
    def __init__(self, uisp_nms, uisp_crm, mikrotik, db):
        self.nms = uisp_nms
        self.crm = uisp_crm
        self.mk = mikrotik
        self.db = db

    async def execute(self, tool_name: str, tool_input: dict, user_context: dict | None = None) -> str:
        """Ejecuta una herramienta y retorna resultado como string."""
        try:
            handler = getattr(self, f"_handle_{tool_name}", None)
            if handler is None:
                return f"Herramienta desconocida: {tool_name}"
            return await handler(tool_input, user_context or {})
        except Exception as e:
            log.error("Tool execution error [%s]: %s", tool_name, e)
            return f"Error al ejecutar {tool_name}: {str(e)}"

    async def _handle_consultar_saldo_cliente(self, inp: dict, ctx: dict) -> str:
        client_id = inp.get("client_id") or ctx.get("client_id")
        if not client_id:
            return "No se especifico client_id"

        balance = await self.crm.get_client_balance(client_id)
        if "error" in balance:
            return balance["error"]

        return json.dumps({
            "cliente": balance["client_name"],
            "saldo": balance["balance"],
            "saldo_formato": format_mxn(balance["balance"]),
            "facturas_pendientes": balance["unpaid_count"],
            "total_pendiente": format_mxn(balance["total_unpaid"]),
        }, ensure_ascii=False)

    async def _handle_consultar_servicio_cliente(self, inp: dict, ctx: dict) -> str:
        client_id = inp.get("client_id") or ctx.get("client_id")
        if not client_id:
            return "No se especifico client_id"

        services = await self.crm.get_client_service_details(client_id)
        if not services:
            return "No se encontraron servicios para este cliente."

        results = []
        for svc in services:
            results.append({
                "nombre": svc["name"],
                "plan": svc["plan"],
                "estado": svc["status"],
                "descarga": format_speed(svc["download"]) if svc["download"] else "N/A",
                "subida": format_speed(svc["upload"]) if svc["upload"] else "N/A",
            })
        return json.dumps(results, ensure_ascii=False)

    async def _handle_diagnosticar_conexion_cliente(self, inp: dict, ctx: dict) -> str:
        client_id = inp.get("client_id") or ctx.get("client_id")
        if not client_id:
            return "No se especifico client_id"

        result = {"diagnostico": []}

        services = await self.crm.get_client_services(client_id)
        for svc in services:
            svc_detail = await self.crm.get_service(str(svc.get("id", "")))
            if not svc_detail:
                continue

            unms_device_id = svc_detail.get("unmsClientSiteId")
            if not unms_device_id:
                continue

            device = await self.nms.get_device(unms_device_id)
            if not device:
                continue

            overview = device.get("overview", {}) or {}
            ident = device.get("identification", {}) or {}
            diag = {
                "antena": ident.get("name", "N/A"),
                "modelo": ident.get("model", "N/A"),
                "estado": overview.get("status", "unknown"),
                "señal": format_signal(overview.get("signal")),
            }

            ip = (device.get("ipAddress") or "").split("/")[0]
            diag["ip"] = ip

            if ip and self.mk:
                session = await self.mk.find_session_by_ip(ip)
                if session:
                    diag["pppoe"] = {
                        "usuario": session.get("name", "N/A"),
                        "uptime": session.get("uptime", "N/A"),
                        "activo": True,
                    }
                else:
                    diag["pppoe"] = {"activo": False}

                try:
                    ping = await self.mk.ping(ip, count=3)
                    diag["ping"] = {
                        "responde": ping.get("success", False),
                        "promedio_ms": ping.get("avg_rtt"),
                        "paquetes": f"{ping.get('received', 0)}/{ping.get('sent', 0)}",
                    }
                except Exception:
                    diag["ping"] = {"responde": False}

            result["diagnostico"].append(diag)

        if not result["diagnostico"]:
            return "No se encontro dispositivo asociado al cliente."

        return json.dumps(result, ensure_ascii=False)

    async def _handle_consultar_estado_red(self, inp: dict, ctx: dict) -> str:
        devices_ov = await self.nms.get_devices_overview()
        clients_ov = await self.crm.get_clients_overview()

        result = {
            "dispositivos": devices_ov,
            "clientes_crm": clients_ov,
        }

        if self.mk:
            try:
                sessions = await self.mk.get_active_sessions()
                result["pppoe_activos"] = len(sessions)
            except Exception:
                result["pppoe_activos"] = "error al consultar"

        return json.dumps(result, ensure_ascii=False)

    async def _handle_buscar_cliente_por_nombre(self, inp: dict, ctx: dict) -> str:
        nombre = inp.get("nombre", "")
        if not nombre:
            return "No se especifico nombre"

        clients = await self.crm.search_clients(nombre)
        if not clients:
            return f"No se encontraron clientes con '{nombre}'"

        results = []
        for c in clients[:5]:
            results.append({
                "id": c.get("id"),
                "nombre": self.crm.get_client_name(c),
                "activo": c.get("isActive", False),
                "saldo": format_mxn(c.get("accountBalance", 0)),
            })
        return json.dumps(results, ensure_ascii=False)

    async def _handle_listar_dispositivos_offline(self, inp: dict, ctx: dict) -> str:
        offline = await self.nms.get_offline_devices()
        if not offline:
            return "Todos los dispositivos estan online."

        results = []
        for d in offline[:15]:
            ident = d.get("identification", {}) or {}
            results.append({
                "nombre": ident.get("name") or d.get("name", "Sin nombre"),
                "modelo": ident.get("model", ""),
                "ip": (d.get("ipAddress") or "sin IP").split("/")[0],
            })

        return json.dumps({"offline_count": len(offline), "dispositivos": results}, ensure_ascii=False)

    async def _handle_consultar_sesion_pppoe(self, inp: dict, ctx: dict) -> str:
        if not self.mk:
            return "MikroTik no configurado"

        ip = inp.get("ip")
        nombre = inp.get("nombre")

        if ip:
            session = await self.mk.find_session_by_ip(ip)
        elif nombre:
            session = await self.mk.find_session_by_name(nombre)
        else:
            return "Especifica ip o nombre"

        if not session:
            return "No se encontro sesion PPPoE activa"

        return json.dumps({
            "usuario": session.get("name", "N/A"),
            "ip": session.get("address", "N/A"),
            "uptime": session.get("uptime", "N/A"),
            "mac": session.get("caller-id", "N/A"),
            "servicio": session.get("service", "N/A"),
        }, ensure_ascii=False)

    async def _handle_ping_dispositivo(self, inp: dict, ctx: dict) -> str:
        if not self.mk:
            return "MikroTik no configurado"

        ip = inp.get("ip", "")
        if not ip:
            return "No se especifico IP"

        result = await self.mk.ping(ip)
        return json.dumps({
            "ip": ip,
            "responde": result.get("success", False),
            "enviados": result.get("sent", 0),
            "recibidos": result.get("received", 0),
            "perdidos": result.get("lost", 0),
            "promedio_ms": result.get("avg_rtt"),
        }, ensure_ascii=False)

    async def _handle_escalar_a_soporte(self, inp: dict, ctx: dict) -> str:
        motivo = inp.get("motivo", "Sin motivo especificado")
        user_id = ctx.get("telegram_user_id")
        username = ctx.get("telegram_username")
        client_id = ctx.get("client_id")

        if user_id and self.db:
            ticket_id = await self.db.create_escalation(
                telegram_user_id=user_id,
                telegram_username=username,
                crm_client_id=client_id,
                issue=motivo,
            )
            return json.dumps({
                "ticket_id": ticket_id,
                "estado": "creado",
                "mensaje": f"Ticket #{ticket_id} creado. Un tecnico se comunicara pronto.",
            }, ensure_ascii=False)

        return "No se pudo crear el ticket de soporte."
