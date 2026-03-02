"""Respuestas automaticas para problemas claros (severidad high/critical)."""

from src.diagnostics.engine import DiagnosticResult


def auto_respond(diag: DiagnosticResult) -> str | None:
    """Genera respuesta automatica si el problema es claro. Retorna None si debe pasar a Claude."""
    if diag.error:
        return None  # engine failed, let Claude handle it

    if diag.severity == "critical":
        return _critical_response(diag)

    if diag.severity == "high":
        return _high_response(diag)

    # medium/low/none → pass to Claude with context
    return None


def _critical_response(diag: DiagnosticResult) -> str:
    if diag.zone_incident:
        zone = diag.zone_name or "tu zona"
        return (
            f"*Interrupcion detectada en zona {zone}*\n\n"
            "Ya estamos trabajando para restablecer el servicio. "
            "Te notificaremos cuando se resuelva.\n\n"
            "Si necesitas mas ayuda, usa /soporte."
        )

    if diag.zone_maintenance:
        zone = diag.zone_name or "tu zona"
        return (
            f"*Mantenimiento en curso en zona {zone}*\n\n"
            "Tu servicio se restablecera al terminar el mantenimiento.\n\n"
            "Si el problema persiste despues, usa /miconexion."
        )

    if diag.service_status == "suspended":
        return (
            "Tu servicio esta *suspendido* por falta de pago.\n\n"
            "Usa /misaldo para ver tu adeudo y reporta tu pago "
            "enviando una foto de tu comprobante.\n\n"
            "Una vez confirmado, tu servicio se reactiva automaticamente."
        )

    return None


def _high_response(diag: DiagnosticResult) -> str | None:
    # Device offline + no PPPoE
    if diag.device_found and diag.device_status != "active" and not diag.pppoe_active:
        return (
            "Tu antena esta *desconectada*.\n\n"
            "Intenta lo siguiente:\n"
            "1. Verifica que el cable de corriente este bien conectado\n"
            "2. Desconecta la antena de la corriente por 30 segundos\n"
            "3. Vuelve a conectar y espera 2 minutos\n\n"
            "Si el problema persiste, usa /soporte para reportar la falla."
        )

    # Device online but no PPPoE
    if diag.device_found and diag.device_status == "active" and not diag.pppoe_active:
        return (
            "Tu antena esta encendida pero *sin conexion a internet*.\n\n"
            "Esto puede ser un problema de configuracion. "
            "Ya se notifico al equipo tecnico.\n\n"
            "Intenta reiniciar tu antena (desconectar 30 seg) y si no se resuelve, "
            "usa /soporte."
        )

    # PPPoE active but ping fails
    if diag.pppoe_active and not diag.ping_success:
        return (
            "Tu conexion esta activa pero presenta *problemas de comunicacion*.\n\n"
            "Intenta lo siguiente:\n"
            "1. Desconecta la antena de la corriente por 30 segundos\n"
            "2. Vuelve a conectar y espera 2 minutos\n\n"
            "Si el problema continua, usa /soporte."
        )

    return None


def format_diagnostic_context(diag: DiagnosticResult) -> str:
    """Formatea el diagnostico para inyectar en el system prompt de Claude."""
    lines = [
        "--- DIAGNOSTICO PRE-EJECUTADO ---",
        f"Cliente: {diag.client_name} (ID: {diag.client_id})",
        f"Plan: {diag.service_plan} | Estado: {diag.service_status}",
    ]

    if diag.device_found:
        signal_str = f"{diag.signal_dbm} dBm" if diag.signal_dbm is not None else "N/A"
        lines.append(
            f"Antena: {diag.device_name} ({diag.device_model})\n"
            f"  Estado UISP: {diag.device_status} | Senal: {signal_str}"
        )
    else:
        lines.append("Antena: No encontrada en UISP")

    if diag.pppoe_active:
        lines.append(
            f"PPPoE: Activo (user: {diag.pppoe_username}, "
            f"uptime: {diag.pppoe_uptime}, perfil: {diag.pppoe_profile})"
        )
    else:
        lines.append("PPPoE: Sin sesion activa")

    if diag.ping_sent > 0:
        if diag.ping_success:
            lines.append(
                f"Ping: {diag.ping_received}/{diag.ping_sent} OK"
                + (f" avg={diag.ping_avg_ms}ms" if diag.ping_avg_ms is not None else "")
            )
        else:
            lines.append(f"Ping: Sin respuesta ({diag.ping_received}/{diag.ping_sent})")

    if diag.issues:
        lines.append(f"Problemas detectados: {', '.join(diag.issues)}")

    lines.append("")
    lines.append(
        "IMPORTANTE: Estos datos ya fueron recopilados. NO uses las herramientas "
        "diagnosticar_conexion_cliente, consultar_sesion_pppoe ni ping_dispositivo. "
        "Analiza los datos y responde al cliente."
    )
    lines.append("---")

    return "\n".join(lines)
