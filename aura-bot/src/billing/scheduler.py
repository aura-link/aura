"""Scheduler de cobranza: loop diario que envia avisos y suspende morosos.

Funciona con TODOS los clientes del CRM (no solo los vinculados a Telegram).
Incluye auto-recuperacion si el bot estuvo caido en un dia de accion.
"""

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from src import config
from src.utils.logger import log

TZ = ZoneInfo("America/Mexico_City")

MONTH_NAMES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
    5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
    9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre",
}

# Solo estos planes reciben notificaciones automaticas de cobranza
BILLABLE_PLANS = {"basico", "residencial", "profesional", "empresarial"}


class BillingScheduler:
    def __init__(self, crm, mk, db, notifier):
        self.crm = crm
        self.mk = mk
        self.db = db
        self.notifier = notifier
        self._running = False
        self._task: asyncio.Task | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._daily_loop())
        log.info("BillingScheduler started (invoice=%d, reminder=%d, warning=%d, suspend=%d, start=%s)",
                 config.BILLING_DAY_INVOICE, config.BILLING_DAY_REMINDER,
                 config.BILLING_DAY_WARNING, config.BILLING_DAY_SUSPEND,
                 config.BILLING_START_MONTH)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        log.info("BillingScheduler stopped")

    async def _daily_loop(self):
        """Check every hour. On each check, run any pending actions for this month."""
        await asyncio.sleep(15)  # let bot finish init
        while self._running:
            try:
                await self._check_and_recover()
            except Exception as e:
                log.error("BillingScheduler error: %s", e)
            # Check every hour
            await asyncio.sleep(3600)

    async def _check_and_recover(self):
        """Self-recovery: run ALL pending actions for current month.

        If bot was down on day 1 and restarts on day 3, it will:
        1. Send invoice notifications (day 1 action, not yet done)
        2. Send reminder notifications (day 3 action)

        This ensures no billing action is ever missed.
        """
        now = datetime.now(TZ)
        billing_month = now.strftime("%Y-%m")
        month_name = MONTH_NAMES.get(now.month, str(now.month))
        today = now.day

        # Don't bill before the start month
        if billing_month < config.BILLING_START_MONTH:
            return

        # Check each action in order: only run if today >= action day
        actions = [
            (config.BILLING_DAY_INVOICE, "invoice_ready"),
            (config.BILLING_DAY_REMINDER, "reminder"),
            (config.BILLING_DAY_WARNING, "warning"),
        ]

        for action_day, notification_type in actions:
            if today >= action_day:
                await self._send_notifications(billing_month, month_name, notification_type)

        # Suspension: only on or after suspend day
        if today >= config.BILLING_DAY_SUSPEND:
            await self._suspend_delinquents(billing_month, month_name)

    async def _get_billable_clients(self) -> list[dict]:
        """Get ALL CRM clients with billable plans + their Telegram link if any."""
        all_clients = await self.crm.get_clients()
        links = await self.db.get_all_customer_links()
        link_map = {l["crm_client_id"]: l for l in links}

        result = []
        for client in all_clients:
            client_id = str(client.get("id", ""))
            if not client_id or not client.get("isActive"):
                continue

            # Check if billable plan
            services = await self.crm.get_client_services(client_id)
            is_billable = False
            for svc in services:
                if svc.get("status") not in (0, 1):
                    continue
                plan_name = (svc.get("servicePlanName") or "").lower()
                for keyword in BILLABLE_PLANS:
                    if keyword in plan_name:
                        is_billable = True
                        break
                if is_billable:
                    break

            if not is_billable:
                continue

            link = link_map.get(client_id)
            result.append({
                "client_id": client_id,
                "client_name": self.crm.get_client_name(client),
                "telegram_user_id": link["telegram_user_id"] if link else None,
            })

            # Rate limit API calls
            await asyncio.sleep(0.1)

        return result

    async def _send_notifications(self, billing_month: str, month_name: str,
                                   notification_type: str):
        """Send billing notifications to all billable clients with unpaid invoices."""
        clients = await self._get_billable_clients()
        sent = 0
        skipped = 0

        for client_info in clients:
            client_id = client_info["client_id"]
            telegram_user_id = client_info["telegram_user_id"]

            # Check if already notified this month for this type
            already = await self.db.was_billing_notified(
                client_id, notification_type, billing_month
            )
            if already:
                skipped += 1
                continue

            # Get unpaid invoices
            invoices = await self.crm.get_unpaid_invoices(client_id)
            if not invoices:
                continue

            total_unpaid = sum(inv.get("total", 0) for inv in invoices)
            if total_unpaid <= 0:
                continue

            # Select template
            template_map = {
                "invoice_ready": "billing_invoice_ready",
                "reminder": "billing_reminder",
                "warning": "billing_warning",
            }
            template = template_map.get(notification_type)
            if not template:
                continue

            # Build kwargs
            kwargs = {
                "month": month_name,
                "amount": f"{total_unpaid:.0f}",
            }
            if notification_type == "warning":
                kwargs["reconnection_fee"] = f"{config.RECONNECTION_FEE:.0f}"

            # Send to Telegram if linked
            ok = False
            if telegram_user_id:
                ok = await self.notifier.notify_client(
                    telegram_user_id, template,
                    f"billing_{billing_month}_{notification_type}",
                    **kwargs,
                )

            # Always log notification (even for unlinked clients, to avoid re-processing)
            await self.db.log_billing_notification(
                client_id, telegram_user_id, notification_type,
                None, billing_month,
            )
            if ok:
                sent += 1

            await asyncio.sleep(0.2)

        log.info("Billing '%s' for %s: sent=%d, skipped=%d, total=%d",
                 notification_type, billing_month, sent, skipped, len(clients))

    async def _suspend_delinquents(self, billing_month: str, month_name: str):
        """Suspend all billable clients with unpaid invoices."""
        clients = await self._get_billable_clients()
        suspended_count = 0

        for client_info in clients:
            client_id = client_info["client_id"]
            client_name = client_info["client_name"]
            telegram_user_id = client_info["telegram_user_id"]

            # Check if already suspended
            existing = await self.db.get_suspension_for_client(client_id)
            if existing:
                continue

            # Check if already processed this month
            already = await self.db.was_billing_notified(
                client_id, "suspended", billing_month
            )
            if already:
                continue

            # Get unpaid invoices
            invoices = await self.crm.get_unpaid_invoices(client_id)
            if not invoices:
                continue

            total_unpaid = sum(inv.get("total", 0) for inv in invoices)
            if total_unpaid <= 0:
                continue

            # Suspend in MikroTik
            previous_profile = None
            if self.mk:
                previous_profile = await self.mk.suspend_client(client_name)

            # Suspend in CRM
            services = await self.crm.get_client_services(client_id)
            service_id = None
            for svc in services:
                if svc.get("status") == 1:  # active
                    service_id = svc.get("id")
                    await self.crm.suspend_service(service_id)
                    break

            # Log suspension with reconnection fee
            await self.db.log_suspension(
                client_id,
                secret_name=client_name,
                service_id=str(service_id) if service_id else None,
                previous_profile=previous_profile,
                reason="nonpayment",
                suspended_by="scheduler",
            )

            # Log to avoid re-processing
            await self.db.log_billing_notification(
                client_id, telegram_user_id, "suspended",
                None, billing_month,
            )

            # Notify client (if linked)
            if telegram_user_id:
                total_with_fee = total_unpaid + config.RECONNECTION_FEE
                await self.notifier.notify_client(
                    telegram_user_id, "billing_suspended",
                    f"suspended_{billing_month}_{client_id}",
                    amount=f"{total_unpaid:.0f}",
                    reconnection_fee=f"{config.RECONNECTION_FEE:.0f}",
                    total_reactivation=f"{total_with_fee:.0f}",
                )

            # Notify admins
            await self.notifier.notify_admins(
                "billing_suspended_admin",
                f"suspended_{billing_month}_{client_id}",
                client_name=client_name,
                amount=f"{total_unpaid:.0f}",
                secret_name=client_name,
                previous_profile=previous_profile or "N/A",
            )

            suspended_count += 1
            await asyncio.sleep(0.2)

        log.info("Billing suspension for %s: %d clients suspended",
                 billing_month, suspended_count)

    async def run_manual(self, action: str) -> str:
        """Manual trigger for admin. Returns summary string."""
        now = datetime.now(TZ)
        billing_month = now.strftime("%Y-%m")
        month_name = MONTH_NAMES.get(now.month, str(now.month))

        if action == "invoice":
            await self._send_notifications(billing_month, month_name, "invoice_ready")
            return f"Avisos de factura enviados para {month_name}"
        elif action == "reminder":
            await self._send_notifications(billing_month, month_name, "reminder")
            return f"Recordatorios enviados para {month_name}"
        elif action == "warning":
            await self._send_notifications(billing_month, month_name, "warning")
            return f"Advertencias enviadas para {month_name}"
        elif action == "suspend":
            await self._suspend_delinquents(billing_month, month_name)
            return f"Suspension ejecutada para {month_name}"
        else:
            return f"Accion no reconocida: {action}"
