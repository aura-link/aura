"""CRUD de ventanas de mantenimiento."""

from datetime import datetime
from src.utils.logger import log


class MaintenanceManager:
    def __init__(self, db):
        self.db = db

    async def create(self, site_id: str | None, site_name: str | None,
                     description: str, starts_at: str, ends_at: str,
                     created_by: int) -> int:
        """Crea ventana de mantenimiento. starts_at/ends_at en formato ISO."""
        mw_id = await self.db.create_maintenance(
            site_id, site_name, description, starts_at, ends_at, created_by,
        )
        log.info("Mantenimiento #%d creado por %d: %s (%s - %s)",
                 mw_id, created_by, site_name or "General", starts_at, ends_at)
        return mw_id

    async def list_active(self) -> list[dict]:
        return await self.db.get_active_maintenance()

    async def cancel(self, maintenance_id: int):
        await self.db.cancel_maintenance(maintenance_id)
        log.info("Mantenimiento #%d cancelado", maintenance_id)

    async def get_for_client(self, crm_client_id: str) -> dict | None:
        return await self.db.get_maintenance_for_client(crm_client_id)
