"""Cliente UISP CRM: clientes, servicios, facturas."""

from src.integrations.base_client import BaseClient
from src.utils.cache import TTLCache
from src.utils.logger import log
from src import config


class UispCrmClient(BaseClient):
    def __init__(self):
        super().__init__(
            base_url=f"{config.UISP_BASE_URL}/crm/api/v1.0",
            headers={"x-auth-token": config.UISP_NMS_TOKEN},
            verify_ssl=config.UISP_VERIFY_SSL,
        )
        self._cache = TTLCache(ttl=config.CACHE_TTL)

    # -- Clients --

    async def get_clients(self) -> list[dict]:
        cached = self._cache.get("clients")
        if cached is not None:
            return cached
        data = await self.get("/clients")
        result = data if isinstance(data, list) else []
        self._cache.set("clients", result)
        return result

    async def get_client(self, client_id: str) -> dict | None:
        return await self.get(f"/clients/{client_id}")

    async def search_clients(self, query: str) -> list[dict]:
        """Busca clientes por nombre usando la API de UISP."""
        clients = await self.get_clients()
        query_lower = query.lower()
        results = []
        for c in clients:
            first = (c.get("firstName") or "").lower()
            last = (c.get("lastName") or "").lower()
            company = (c.get("companyName") or "").lower()
            full_name = f"{first} {last}".strip()
            if query_lower in full_name or query_lower in company:
                results.append(c)
        return results

    def get_client_name(self, client: dict) -> str:
        first = client.get("firstName") or ""
        last = client.get("lastName") or ""
        company = client.get("companyName") or ""
        name = f"{first} {last}".strip()
        return name or company or "Sin nombre"

    async def create_client(
        self, first_name: str, last_name: str, is_active: bool = True
    ) -> dict | None:
        """Crea un nuevo cliente en el CRM. Retorna el cliente creado o None."""
        payload = {
            "firstName": first_name,
            "lastName": last_name,
            "isLead": False,
            "isActive": is_active,
        }
        result = await self.post("/clients", json=payload)
        if result:
            self._cache.invalidate("clients")
        return result

    # -- Services --

    async def get_client_services(self, client_id: str) -> list[dict]:
        data = await self.get(f"/clients/services", params={"clientId": client_id})
        return data if isinstance(data, list) else []

    async def get_service(self, service_id: str) -> dict | None:
        return await self.get(f"/clients/services/{service_id}")

    # -- Invoices --

    async def get_client_invoices(self, client_id: str) -> list[dict]:
        data = await self.get(f"/invoices", params={"clientId": client_id})
        return data if isinstance(data, list) else []

    # -- Balance / Saldo --

    async def get_client_balance(self, client_id: str) -> dict:
        """Obtiene saldo del cliente: balance, ultimo pago, facturas pendientes."""
        client = await self.get_client(client_id)
        if not client:
            return {"error": "Cliente no encontrado"}

        balance = client.get("accountBalance", 0) or 0
        invoices = await self.get_client_invoices(client_id)

        unpaid = [
            inv for inv in invoices
            if inv.get("status") in (1, 2)  # 1=draft, 2=unpaid
        ]
        total_unpaid = sum(inv.get("total", 0) for inv in unpaid)

        return {
            "client_name": self.get_client_name(client),
            "balance": balance,
            "total_unpaid": total_unpaid,
            "unpaid_count": len(unpaid),
            "currency": "MXN",
        }

    async def update_client_ident(self, client_id: str, user_ident: str) -> bool:
        """Escribe el userIdent del cliente via PATCH. Retorna True si exitoso."""
        result = await self.patch(f"/clients/{client_id}", json={"userIdent": user_ident})
        if result:
            self._cache.invalidate("clients")
            return True
        return False

    async def get_service_zone(self, client_id: str) -> str | None:
        """Obtiene la zona (city) del primer servicio activo del cliente."""
        services = await self.get_client_services(client_id)
        for svc in services:
            if svc.get("status") in (0, 1):  # prepared or active
                city = (svc.get("street") or "").strip()
                if not city:
                    city = (svc.get("city") or "").strip()
                if city:
                    return city
        # Fallback: any service with city
        for svc in services:
            city = (svc.get("city") or "").strip()
            if city:
                return city
        return None

    async def get_client_service_details(self, client_id: str) -> list[dict]:
        """Retorna detalles de servicios de un cliente."""
        services = await self.get_client_services(client_id)
        results = []
        for svc in services:
            results.append({
                "id": svc.get("id"),
                "name": svc.get("name", "Sin nombre"),
                "status": _svc_status(svc.get("status")),
                "plan": (svc.get("servicePlanName") or "Sin plan"),
                "download": svc.get("downloadSpeed"),
                "upload": svc.get("uploadSpeed"),
                "active_from": svc.get("activeFrom"),
                "active_to": svc.get("activeTo"),
                "address": svc.get("street") or "",
            })
        return results

    async def get_clients_overview(self) -> dict:
        clients = await self.get_clients()
        active = sum(1 for c in clients if c.get("isActive"))
        with_balance = sum(1 for c in clients if (c.get("accountBalance") or 0) > 0)
        return {
            "total": len(clients),
            "active": active,
            "inactive": len(clients) - active,
            "with_balance": with_balance,
        }


    # -- Billing / Payments --

    async def get_unpaid_invoices(self, client_id: str | None = None) -> list[dict]:
        """Facturas impagas (status 1=unpaid, 2=overdue)."""
        params = {"statuses[]": [1, 2]}
        if client_id:
            params["clientId"] = client_id
        data = await self.get("/invoices", params=params)
        return data if isinstance(data, list) else []

    async def get_overdue_invoices(self) -> list[dict]:
        """Facturas vencidas (status 2=overdue)."""
        data = await self.get("/invoices", params={"statuses[]": [2]})
        return data if isinstance(data, list) else []

    async def create_payment(
        self, client_id: int, amount: float, method_id: str,
        invoice_ids: list[int] | None = None, note: str = ""
    ) -> dict | None:
        """Registra un pago en el CRM."""
        payload = {
            "clientId": client_id,
            "amount": amount,
            "methodId": method_id,
        }
        if note:
            payload["note"] = note
        if invoice_ids:
            payload["invoiceIds"] = invoice_ids
        result = await self.post("/payments", json=payload)
        if result:
            self._cache.invalidate("clients")
        return result

    async def delete_payment(self, payment_id: int) -> bool:
        """Reversa un pago."""
        return await self.delete(f"/payments/{payment_id}")

    async def suspend_service(self, service_id: int) -> dict | None:
        """Suspende un servicio (status=3)."""
        return await self.patch(f"/clients/services/{service_id}", json={"status": 3})

    async def activate_service(self, service_id: int) -> dict | None:
        """Activa un servicio (status=1)."""
        return await self.patch(f"/clients/services/{service_id}", json={"status": 1})

    async def get_payment_methods(self) -> list[dict]:
        """Lista metodos de pago configurados."""
        data = await self.get("/payment-methods")
        return data if isinstance(data, list) else []


def _svc_status(code: int | None) -> str:
    mapping = {0: "prepared", 1: "active", 2: "ended", 3: "suspended", 4: "prepared_blocked",
               5: "obsolete", 6: "deferred", 7: "quoted"}
    return mapping.get(code or 0, "unknown")
