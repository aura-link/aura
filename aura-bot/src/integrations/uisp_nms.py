"""Cliente UISP NMS: dispositivos, sitios, outages."""

from src.integrations.base_client import BaseClient
from src.utils.cache import TTLCache
from src.utils.logger import log
from src import config


class UispNmsClient(BaseClient):
    def __init__(self):
        super().__init__(
            base_url=f"{config.UISP_BASE_URL}/nms/api/v2.1",
            headers={"x-auth-token": config.UISP_NMS_TOKEN},
            verify_ssl=config.UISP_VERIFY_SSL,
        )
        self._cache = TTLCache(ttl=config.CACHE_TTL)

    # -- Devices --

    async def get_devices(self) -> list[dict]:
        cached = self._cache.get("devices")
        if cached is not None:
            return cached
        data = await self.get("/devices")
        result = data if isinstance(data, list) else []
        self._cache.set("devices", result)
        return result

    async def get_device(self, device_id: str) -> dict | None:
        return await self.get(f"/devices/{device_id}")

    async def get_devices_overview(self) -> dict:
        devices = await self.get_devices()
        online = sum(1 for d in devices if _status(d) == "active")
        offline = sum(1 for d in devices if _status(d) in ("disconnected", "inactive"))
        unknown = sum(1 for d in devices if _status(d) not in ("active", "disconnected", "inactive"))
        return {
            "total": len(devices),
            "online": online,
            "offline": offline,
            "unknown": unknown,
        }

    async def get_offline_devices(self) -> list[dict]:
        devices = await self.get_devices()
        return [
            d for d in devices
            if _status(d) in ("disconnected", "inactive")
        ]

    async def find_device_by_ip(self, ip: str) -> dict | None:
        devices = await self.get_devices()
        for d in devices:
            dev_ip = (d.get("ipAddress") or "").split("/")[0]
            if dev_ip == ip:
                return d
        return None

    # -- Sites --

    async def get_sites(self) -> list[dict]:
        cached = self._cache.get("sites")
        if cached is not None:
            return cached
        data = await self.get("/sites")
        result = data if isinstance(data, list) else []
        self._cache.set("sites", result)
        return result

    # -- Outages --

    async def get_outages(self, count: int = 20) -> list[dict]:
        data = await self.get("/outages", params={"count": count, "page": 1})
        return data if isinstance(data, list) else []

    async def get_active_outages(self) -> list[dict]:
        outages = await self.get_outages(count=50)
        return [o for o in outages if not o.get("endTimestamp")]


def _status(device: dict) -> str:
    """Extrae el status de un dispositivo UISP."""
    overview = device.get("overview", {}) or {}
    return (overview.get("status") or device.get("status") or "unknown").lower()
