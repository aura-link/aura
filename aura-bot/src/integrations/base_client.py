"""Base HTTP client con aiohttp, retry y timeout."""

import asyncio
import ssl
import aiohttp
from src.utils.logger import log
from src import config

_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}
_MAX_RETRIES = 3


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
        return await self._request_with_retry("GET", path, params=params)

    async def post(self, path: str, json: dict | None = None) -> dict | list | None:
        return await self._request_with_retry("POST", path, json=json)

    async def patch(self, path: str, json: dict | None = None) -> dict | list | None:
        return await self._request_with_retry("PATCH", path, json=json)

    async def delete(self, path: str, params: dict | None = None) -> bool:
        return await self._request_with_retry("DELETE", path, params=params)

    async def _request_with_retry(self, method: str, path: str, **kwargs):
        session = await self._get_session()
        url = f"{self.base_url}{path}"
        is_delete = method == "DELETE"
        ok_statuses = (200, 204) if is_delete else (200, 201)
        fail_return = False if is_delete else None

        for attempt in range(_MAX_RETRIES):
            try:
                async with session.request(method, url, **kwargs) as resp:
                    if resp.status in ok_statuses:
                        if is_delete:
                            return True
                        return await resp.json()
                    if resp.status in _RETRYABLE_STATUSES and attempt < _MAX_RETRIES - 1:
                        delay = 2 ** attempt  # 1s, 2s
                        log.warning("%s %s -> %d, retrying in %ds", method, path, resp.status, delay)
                        await asyncio.sleep(delay)
                        continue
                    log.warning("%s %s -> %d", method, path, resp.status)
                    return fail_return
            except Exception as e:
                if attempt < _MAX_RETRIES - 1:
                    delay = 2 ** attempt
                    log.warning("%s %s attempt %d error: %s, retrying in %ds", method, path, attempt + 1, e, delay)
                    await asyncio.sleep(delay)
                    continue
                log.error("%s %s error: %s", method, path, e)
                return fail_return
        return fail_return

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
