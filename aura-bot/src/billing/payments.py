"""Procesador de pagos: analisis IA de comprobantes, registro CRM, fraude."""

import asyncio
import base64
import json
import anthropic
from src import config
from src.utils.logger import log
from src.billing.receipt_storage import ReceiptStorage

VISION_CAPABLE_MODELS = {
    "claude-sonnet-4-20250514",
    "claude-sonnet-4-5-20250929",
    "claude-haiku-4-5-20250929",
}
VISION_FALLBACK_MODEL = "claude-sonnet-4-20250514"


class PaymentProcessor:
    def __init__(self, crm, mk, db, notifier, receipt_storage: ReceiptStorage):
        self.crm = crm
        self.mk = mk
        self.db = db
        self.notifier = notifier
        self.receipt_storage = receipt_storage
        self._anthropic: anthropic.AsyncAnthropic | None = None
        self._register_lock = asyncio.Lock()

    @property
    def _client(self) -> anthropic.AsyncAnthropic:
        if self._anthropic is None:
            self._anthropic = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)
        return self._anthropic

    async def analyze_receipt(self, image_bytes: bytes) -> dict:
        """Analiza comprobante con Claude Vision. Retorna dict con datos extraidos."""
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        # Detect media type from magic bytes
        media_type = "image/jpeg"
        if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            media_type = "image/png"
        elif image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
            media_type = "image/webp"

        vision_model = config.CLAUDE_MODEL if config.CLAUDE_MODEL in VISION_CAPABLE_MODELS else VISION_FALLBACK_MODEL

        try:
            response = await self._client.messages.create(
                model=vision_model,
                max_tokens=512,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Analiza esta imagen de un comprobante de pago. "
                                "Extrae la siguiente informacion en formato JSON:\n"
                                '- "valid": true si es un comprobante de pago real, false si no\n'
                                '- "amount": monto numerico (sin simbolo de moneda)\n'
                                '- "date": fecha en formato YYYY-MM-DD\n'
                                '- "reference": numero de referencia o folio\n'
                                '- "bank": nombre del banco o institucion\n'
                                '- "method": "transferencia" o "oxxo" o "deposito" o "otro"\n'
                                '- "confidence": "high", "medium" o "low"\n\n'
                                "Si NO es un comprobante de pago valido, responde:\n"
                                '{"valid": false, "reason": "descripcion breve"}\n\n'
                                "Responde SOLO con el JSON, sin texto adicional."
                            ),
                        },
                    ],
                }],
            )

            text = response.content[0].text.strip()
            # Clean markdown code blocks if present
            if text.startswith("```"):
                text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            return json.loads(text)
        except json.JSONDecodeError:
            log.warning("Claude Vision returned non-JSON: %s", text[:200])
            return {"valid": False, "reason": "No se pudo analizar la respuesta"}
        except Exception as e:
            log.error("Receipt analysis error: %s", e)
            return {"valid": False, "reason": f"Error de analisis: {e}"}

    async def check_duplicate_receipt(self, client_id: str, reference: str,
                                      amount: float) -> dict | None:
        """Check if this receipt was already submitted. Returns existing report or None."""
        if not self.db:
            return None
        # Check by reference number (strongest match)
        if reference:
            existing = await self.db.find_payment_report_by_reference(client_id, reference)
            if existing:
                return existing
        # Check by same amount in last 24h from same client
        recent = await self.db.find_recent_payment_report(client_id, amount, hours=24)
        return recent

    def calculate_reactivation_amount(self, unpaid_total: float) -> float:
        """Calculate total needed to reactivate: unpaid + reconnection fee."""
        return unpaid_total + config.RECONNECTION_FEE

    async def match_invoices(self, client_id: str, amount: float,
                              tolerance: float = 5.0) -> list[dict]:
        """Busca facturas impagas que coincidan con el monto.

        For suspended clients, also accepts amount = invoices + reconnection fee.
        """
        invoices = await self.crm.get_unpaid_invoices(client_id)
        matches = []
        for inv in invoices:
            inv_total = inv.get("total", 0)
            if abs(inv_total - amount) <= tolerance:
                matches.append(inv)
        # If no exact match, try sum of all unpaid
        if not matches and invoices:
            total_unpaid = sum(inv.get("total", 0) for inv in invoices)
            if abs(total_unpaid - amount) <= tolerance:
                matches = invoices
            # Also try: total + reconnection fee (for suspended clients)
            elif self.db:
                suspension = await self.db.get_suspension_for_client(client_id)
                if suspension:
                    total_with_fee = total_unpaid + config.RECONNECTION_FEE
                    if abs(total_with_fee - amount) <= tolerance:
                        matches = invoices
        return matches

    async def register_payment(self, client_id: str, amount: float,
                                method: str, invoice_ids: list[int] | None = None,
                                note: str = "") -> dict | None:
        """Registra pago en CRM. Uses lock to prevent double-registration."""
        async with self._register_lock:
            # Check for recent duplicate before registering
            if self.db:
                recent = await self.db.find_recent_payment_report(client_id, amount, hours=1)
                if recent and recent.get("status") in ("approved", "pending"):
                    log.warning("Duplicate payment blocked: client=%s amount=%.0f", client_id, amount)
                    return recent

            # Map method to CRM method ID (from UISP CRM payment-methods API)
            method_map = {
                "transferencia": "4145b5f5-3bbc-45e3-8fc5-9cda970c62fb",
                "oxxo": "4145b5f5-3bbc-45e3-8fc5-9cda970c62fb",  # same as transfer
                "deposito": "4145b5f5-3bbc-45e3-8fc5-9cda970c62fb",
                "efectivo": "6efe0fa8-36b2-4dd1-b049-427bffc7d369",
            }
            method_id = method_map.get(method, method_map["transferencia"])
            return await self.crm.create_payment(
                client_id=int(client_id), amount=amount,
                method_id=method_id, invoice_ids=invoice_ids, note=note,
            )

    async def check_fraud(self, client_id: str, telegram_user_id: int,
                           report_id: int, reason: str = "Comprobante no verificable"
                           ) -> dict:
        """Incrementa strikes y retorna accion a tomar."""
        strike_num = await self.db.add_fraud_strike(
            client_id, telegram_user_id, report_id, reason
        )

        if strike_num >= 3:
            # Suspension automatica
            await self._suspend_for_fraud(client_id, telegram_user_id)
            return {"action": "suspended", "strike": strike_num}
        elif strike_num == 2:
            return {"action": "warning_2", "strike": strike_num}
        else:
            return {"action": "warning_1", "strike": strike_num}

    async def _suspend_for_fraud(self, client_id: str, telegram_user_id: int):
        """Suspende cliente por fraude reiterado."""
        # Get client info for MikroTik
        client = await self.crm.get_client(client_id)
        if not client:
            return
        client_name = self.crm.get_client_name(client)

        # Suspend in MikroTik
        previous_profile = None
        if self.mk:
            previous_profile = await self.mk.suspend_client(client_name)
            if previous_profile is None:
                log.warning("PPPoE secret not found for fraud suspension: '%s' (ID %s)",
                            client_name, client_id)

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
            client_id, client_name, str(service_id) if service_id else None,
            previous_profile, reason="fraud", suspended_by="fraud_system",
        )

        # Notify client
        await self.notifier.notify_client(
            telegram_user_id, "fraud_suspended",
            f"fraud_{client_id}",
        )

        # Notify admins
        await self.notifier.notify_admins(
            "billing_suspended_admin", f"fraud_{client_id}",
            client_name=client_name, amount="N/A",
            secret_name=client_name, previous_profile=previous_profile or "N/A",
        )

    async def reactivate_client(self, client_id: str, admin_user_id: int) -> dict:
        """Reactivate suspended client: MikroTik + CRM + notify."""
        client = await self.crm.get_client(client_id)
        if not client:
            return {"success": False, "error": "Cliente no encontrado"}

        client_name = self.crm.get_client_name(client)
        suspension = await self.db.get_suspension_for_client(client_id)

        # Restore MikroTik profile
        mk_ok = False
        if self.mk and suspension:
            prev_profile = suspension.get("previous_profile", "default")
            secret_name = suspension.get("secret_name", client_name)
            mk_ok = await self.mk.unsuspend_client(secret_name, prev_profile)

        # Activate CRM service
        crm_ok = False
        services = await self.crm.get_client_services(client_id)
        for svc in services:
            if svc.get("status") == 3:  # suspended
                await self.crm.activate_service(svc.get("id"))
                crm_ok = True
                break

        # Log unsuspension
        await self.db.log_unsuspension(client_id)

        # Reset fraud strikes
        await self.db.reset_fraud_strikes(client_id)

        # Notify client if linked
        link = None
        links = await self.db.get_all_customer_links()
        for l in links:
            if l.get("crm_client_id") == client_id:
                link = l
                break
        if link:
            await self.notifier.notify_client(
                link["telegram_user_id"], "service_reactivated",
                f"reactivated_{client_id}",
            )

        return {
            "success": True,
            "client_name": client_name,
            "mikrotik": mk_ok,
            "crm": crm_ok,
        }
