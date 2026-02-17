"""Scheduler de cobranza: loop diario que envia avisos y suspende morosos."""

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
        self._last_action_day: int | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._daily_loop())
        log.info("BillingScheduler started (invoice=%d, reminder=%d, warning=%d, suspend=%d)",
                 config.BILLING_DAY_INVOICE, config.BILLING_DAY_REMINDER,
                 config.BILLING_DAY_WARNING, config.BILLING_DAY_SUSPEND)

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
        """Check every hour; act once per day based on day of month."""
        await asyncio.sleep(10)  # let bot finish init
        while self._running:
            try:
                now = datetime.now(TZ)
                today = now.day

                # Only act once per calendar day
                if today != self._last_action_day:
                    await self._check_day(today, now)
                    self._last_action_day = today
            except Exception as e:
                log.error("BillingScheduler error: %s", e)

            # Check every hour
            await asyncio.sleep(3600)

    async def _check_day(self, day: int, now: datetime):
        """Execute billing action for the current day of month."""
        billing_month = now.strftime("%Y-%m")
        month_name = MONTH_NAMES.get(now.month, str(now.month))

        if day == config.BILLING_DAY_INVOICE:
            await self._send_notifications(billing_month, month_name, "invoice_ready")
        elif day == config.BILLING_DAY_REMINDER:
            await self._send_notifications(billing_month, month_name, "reminder")
        elif day == config.BILLING_DAY_WARNING:
            await self._send_notifications(billing_month, month_name, "warning")
        elif day == config.BILLING_DAY_SUSPEND:
            await self._suspend_delinquents(billing_month, month_name)

    async def _send_notifications(self, billing_month: str, month_name: str,
                                   notification_type: str):
        """Send billing notifications to all linked clients with unpaid invoices."""
        log.info("Billing: sending '%s' notifications for %s", notification_type, billing_month)

        links = await self.db.get_all_customer_links()
        sent = 0
        skipped = 0

        for link in links:
            client_id = link["crm_client_id"]
            telegram_user_id = link["telegram_user_id"]

            # Check if client has a billable plan
            if not await self._has_billable_plan(client_id):
                skipped += 1
                continue

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

            # Send
            ok = await self.notifier.notify_client(
                telegram_user_id, template,
                f"billing_{billing_month}_{notification_type}",
                **kwargs,
            )

            if ok:
                await self.db.log_billing_notification(
                    client_id, telegram_user_id, notification_type,
                    None, billing_month,
                )
                sent += 1

            # Rate limit: 200ms between clients
            await asyncio.sleep(0.2)

        log.info("Billing '%s': sent=%d, skipped=%d, total_links=%d",
                 notification_type, sent, skipped, len(links))

    async def _suspend_delinquents(self, billing_month: str, month_name: str):
        """Suspend all clients with unpaid invoices on suspension day."""
        log.info("Billing: running suspension for %s", billing_month)

        links = await self.db.get_all_customer_links()
        suspended_count = 0

        for link in links:
            client_id = link["crm_client_id"]
            telegram_user_id = link["telegram_user_id"]

            # Check if client has a billable plan
            if not await self._has_billable_plan(client_id):
                continue

            # Check if already suspended
            existing = await self.db.get_suspension_for_client(client_id)
            if existing:
                continue

            # Get unpaid invoices
            invoices = await self.crm.get_unpaid_invoices(client_id)
            if not invoices:
                continue

            total_unpaid = sum(inv.get("total", 0) for inv in invoices)
            if total_unpaid <= 0:
                continue

            # Get client info
            client = await self.crm.get_client(client_id)
            if not client:
                continue
            client_name = self.crm.get_client_name(client)

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

            # Log suspension
            await self.db.log_suspension(
                client_id,
                secret_name=client_name,
                service_id=str(service_id) if service_id else None,
                previous_profile=previous_profile,
                reason="nonpayment",
                suspended_by="scheduler",
            )

            # Notify client
            await self.notifier.notify_client(
                telegram_user_id, "billing_suspended",
                f"suspended_{billing_month}_{client_id}",
                amount=f"{total_unpaid:.0f}",
                reconnection_fee=f"{config.RECONNECTION_FEE:.0f}",
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

        log.info("Billing suspension: %d clients suspended for %s",
                 suspended_count, billing_month)

    async def _has_billable_plan(self, client_id: str) -> bool:
        """Check if client has one of the 4 standard billable plans."""
        services = await self.crm.get_client_services(client_id)
        for svc in services:
            if svc.get("status") not in (0, 1):  # only prepared/active
                continue
            plan_name = (svc.get("servicePlanName") or "").lower()
            for keyword in BILLABLE_PLANS:
                if keyword in plan_name:
                    return True
        return False
