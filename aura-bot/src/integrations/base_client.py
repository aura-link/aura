"""Base HTTP client con aiohttp, retry y timeout."""

import ssl
import aiohttp
from src.utils.logger import log
from src import config


class BaseClient:
    def __init__(self, base_url: str, headers: dict | None = None, verify_ssl: bool = True):
        self.base_url = base_url.rstrip("/")
        self._headers = headers or {}
        self._verify_ssl = verify_ssl
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            ssl_ctx = None if self._verify_ssl else False
            connector = aiohttp.TCPConnector(ssl=ssl_ctx)
            timeout = aiohttp.ClientTimeout(total=config.API_TIMEOUT)
            self._session = aiohttp.ClientSession(
                connector=connector, timeout=timeout, headers=self._headers
            )
        return self._session

    async def get(self, path: str, params: dict | None = None) -> dict | list | None:
        session = await self._get_session()
        url = f"{self.base_url}{path}"
        try:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                log.warning("GET %s -> %d", path, resp.status)
                return None
        except Exception as e:
            log.error("GET %s error: %s", path, e)
            return None

    async def post(self, path: str, json: dict | None = None) -> dict | list | None:
        session = await self._get_session()
        url = f"{self.base_url}{path}"
        try:
            async with session.post(url, json=json) as resp:
                if resp.status in (200, 201):
                    return await resp.json()
                log.warning("POST %s -> %d", path, resp.status)
                return None
        except Exception as e:
            log.error("POST %s error: %s", path, e)
            return None

    async def patch(self, path: str, json: dict | None = None) -> dict | list | None:
        session = await self._get_session()
        url = f"{self.base_url}{path}"
        try:
            async with session.patch(url, json=json) as resp:
                if resp.status in (200, 201):
                    return await resp.json()
                log.warning("PATCH %s -> %d", path, resp.status)
                return None
        except Exception as e:
            log.error("PATCH %s error: %s", path, e)
            return None

    async def delete(self, path: str, params: dict | None = None) -> bool:
        session = await self._get_session()
        url = f"{self.base_url}{path}"
        try:
            async with session.delete(url, params=params) as resp:
                if resp.status in (200, 204):
                    return True
                log.warning("DELETE %s -> %d", path, resp.status)
                return False
        except Exception as e:
            log.error("DELETE %s error: %s", path, e)
            return False

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
