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
