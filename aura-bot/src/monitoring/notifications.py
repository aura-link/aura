"""Notificaciones Telegram con anti-spam."""

from telegram import Bot
from src import config
from src.utils.logger import log


# Templates de mensajes
TEMPLATES = {
    "outage_client": (
        "⚠️ *Interrupcion detectada*\n\n"
        "Detectamos una interrupcion en la zona *{zone_name}*.\n"
        "Nuestro equipo ya esta trabajando para restablecer el servicio.\n\n"
        "Te avisaremos cuando se resuelva."
    ),
    "recovery_client": (
        "✅ *Servicio restaurado*\n\n"
        "La zona *{zone_name}* ha sido restaurada.\n"
        "Si aun tienes problemas, usa /miconexion para diagnosticar "
        "o /soporte para hablar con un tecnico."
    ),
    "outage_admin": (
        "🚨 *Caida de infraestructura*\n\n"
        "📡 Dispositivo: *{device_name}*\n"
        "📍 Zona: *{zone_name}*\n"
        "👥 Clientes afectados: *{affected_count}*\n"
        "🕐 Detectado: {timestamp}"
    ),
    "recovery_admin": (
        "✅ *Infraestructura restaurada*\n\n"
        "📡 Dispositivo: *{device_name}*\n"
        "📍 Zona: *{zone_name}*\n"
        "⏱ Duracion: {duration}"
    ),
    "maintenance_client": (
        "🔧 *Mantenimiento programado*\n\n"
        "Se realizara mantenimiento en la zona *{zone_name}*.\n"
        "📅 Inicio: {start_time}\n"
        "📅 Fin estimado: {end_time}\n\n"
        "📝 {description}\n\n"
        "Durante este periodo tu servicio podria verse interrumpido."
    ),
    "maintenance_admin": (
        "🔧 *Mantenimiento iniciado*\n\n"
        "📍 Zona: *{zone_name}*\n"
        "📅 {start_time} - {end_time}\n"
        "📝 {description}\n"
        "👥 Clientes notificados: {notified_count}"
    ),
    # -- Billing / Cobranza --
    "billing_invoice_ready": (
        "📄 *Factura disponible*\n\n"
        "Tu factura de *{month}* por *${amount} MXN* esta lista.\n"
        "Fecha limite de pago: *dia 7* de este mes.\n\n"
        "Puedes pagar por transferencia o OXXO y enviarme "
        "una foto del comprobante para registrar tu pago."
    ),
    "billing_reminder": (
        "⏰ *Recordatorio de pago*\n\n"
        "Tu factura de *{month}* por *${amount} MXN* sigue pendiente.\n"
        "Quedan *4 dias* para pagar (limite: dia 7).\n\n"
        "💳 *Datos para deposito/transferencia:*\n"
        "Banco: *BBVA Bancomer*\n"
        "Titular: Carlos Eduardo Valenzuela Rios\n"
        "Cuenta: `285 958 9260`\n"
        "Tarjeta: `4152 3144 8622 9639`\n"
        "CLABE: `012 400 02859589260 7`\n\n"
        "Una vez que pagues, envia foto de tu comprobante "
        "aqui para registrar tu pago automaticamente."
    ),
    "billing_warning": (
        "🚨 *Ultimo dia para pagar*\n\n"
        "Hoy es el *ultimo dia* para pagar tu factura de *{month}* "
        "por *${amount} MXN*.\n\n"
        "Si no pagas hoy, manana tu servicio sera suspendido "
        "y se cobrara *${reconnection_fee} MXN de reconexion*.\n\n"
        "💳 *Datos para deposito/transferencia:*\n"
        "Banco: *BBVA Bancomer*\n"
        "Titular: Carlos Eduardo Valenzuela Rios\n"
        "Cuenta: `285 958 9260`\n"
        "Tarjeta: `4152 3144 8622 9639`\n"
        "CLABE: `012 400 02859589260 7`\n\n"
        "Envia foto de tu comprobante para registrar tu pago."
    ),
    "billing_suspended": (
        "🔴 *Servicio suspendido*\n\n"
        "Tu servicio ha sido suspendido por falta de pago.\n"
        "Deuda pendiente: *${amount} MXN*\n"
        "Cargo de reconexion: *${reconnection_fee} MXN*\n"
        "Total para reactivar: *${total_reactivation} MXN*\n\n"
        "💳 *Datos para deposito/transferencia:*\n"
        "Banco: *BBVA Bancomer*\n"
        "Titular: Carlos Eduardo Valenzuela Rios\n"
        "Cuenta: `285 958 9260`\n"
        "Tarjeta: `4152 3144 8622 9639`\n"
        "CLABE: `012 400 02859589260 7`\n\n"
        "Realiza el pago y envia foto del comprobante "
        "para reactivar tu servicio."
    ),
    "billing_suspended_admin": (
        "🔴 *Cliente suspendido*\n\n"
        "👤 {client_name}\n"
        "💰 Deuda: ${amount} MXN\n"
        "📡 Secret: {secret_name}\n"
        "Perfil anterior: {previous_profile}"
    ),
    "payment_approved": (
        "✅ *Pago registrado*\n\n"
        "Tu pago de *${amount} MXN* ha sido registrado exitosamente.\n"
        "Tu saldo esta al corriente.\n\n"
        "Gracias por tu pago! Tu proximo corte es el dia 1 de {next_month}."
    ),
    "payment_pending_admin": (
        "💵 *Reporte de pago (efectivo)*\n\n"
        "👤 {client_name}\n"
        "💰 Monto: ${amount} MXN\n"
        "📋 Reporte #{report_id}\n\n"
        "Usa los botones para aprobar o rechazar."
    ),
    "payment_pending_client": (
        "📋 *Reporte enviado*\n\n"
        "Tu reporte de pago en efectivo por *${amount} MXN* "
        "ha sido enviado al administrador.\n"
        "Te avisare cuando sea aprobado."
    ),
    "payment_rejected": (
        "❌ *Reporte no verificado*\n\n"
        "Tu reporte de pago no pudo ser verificado.\n"
        "Por favor envia una foto clara del comprobante de pago."
    ),
    "payment_approved_admin": (
        "✅ *Pago auto-registrado*\n\n"
        "👤 {client_name}\n"
        "💰 ${amount} MXN ({method})\n"
        "📋 Reporte #{report_id}\n"
        "Factura(s): {invoice_ids}"
    ),
    "fraud_warning_1": (
        "⚠️ *Advertencia*\n\n"
        "Tu reporte de pago no pudo ser verificado.\n"
        "Asegurate de enviar una foto clara y legible del comprobante.\n\n"
        "Si tienes dudas, contacta a soporte con /soporte."
    ),
    "fraud_warning_2": (
        "🚨 *Segunda advertencia*\n\n"
        "Este es tu segundo reporte que no pudo ser verificado.\n"
        "Un reporte mas sin verificar causara la *suspension automatica* "
        "de tu servicio.\n\n"
        "Si necesitas ayuda, contacta a soporte con /soporte."
    ),
    "fraud_suspended": (
        "🔴 *Servicio suspendido por reportes falsos*\n\n"
        "Tu servicio ha sido suspendido debido a multiples "
        "reportes de pago no verificables.\n\n"
        "Contacta al administrador para resolver esta situacion."
    ),
    "service_reactivated": (
        "✅ *Servicio reactivado*\n\n"
        "Tu servicio de internet ha sido reactivado.\n"
        "Gracias por tu pago!"
    ),
}


class NotificationSender:
    def __init__(self, bot: Bot, db):
        self.bot = bot
        self.db = db

    async def notify_client(self, telegram_user_id: int, template: str,
                             reference_id: str, **kwargs):
        """Envia notificacion a un cliente con anti-spam."""
        if not telegram_user_id:
            return False

        # Check cooldown
        already = await self.db.was_notified_recently(
            telegram_user_id, template, reference_id,
            config.NOTIFICATION_COOLDOWN,
        )
        if already:
            return False

        text = TEMPLATES.get(template, "").format(**kwargs)
        if not text:
            log.warning("Template no encontrado: %s", template)
            return False

        try:
            await self.bot.send_message(
                chat_id=telegram_user_id,
                text=text,
                parse_mode="Markdown",
            )
            await self.db.log_notification(telegram_user_id, template, reference_id)
            return True
        except Exception as e:
            log.warning("No se pudo notificar a %d: %s", telegram_user_id, e)
            return False

    async def notify_admins(self, template: str, reference_id: str, **kwargs):
        """Envia notificacion a todos los admins."""
        text = TEMPLATES.get(template, "").format(**kwargs)
        if not text:
            return

        for admin_id in config.TELEGRAM_ADMIN_IDS:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    parse_mode="Markdown",
                )
                await self.db.log_notification(admin_id, template, reference_id)
            except Exception as e:
                log.warning("No se pudo notificar admin %d: %s", admin_id, e)

    async def notify_affected_clients(self, clients: list[dict], template: str,
                                       reference_id: str, **kwargs) -> int:
        """Notifica a todos los clientes con Telegram vinculado. Retorna cuantos."""
        sent = 0
        for c in clients:
            uid = c.get("telegram_user_id")
            if uid:
                ok = await self.notify_client(uid, template, reference_id, **kwargs)
                if ok:
                    sent += 1
        return sent
