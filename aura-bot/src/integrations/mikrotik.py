"""Cliente MikroTik via librouteros (RouterOS API, puerto 8728)."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import librouteros
from librouteros.query import Key
from src.utils.logger import log
from src import config

_executor = ThreadPoolExecutor(max_workers=2)


class MikroTikClient:
    def __init__(self):
        self.host = config.MIKROTIK_HOST
        self.port = config.MIKROTIK_PORT
        self.user = config.MIKROTIK_USER
        self.password = config.MIKROTIK_PASSWORD

    def _connect(self) -> librouteros.Api:
        return librouteros.connect(
            host=self.host,
            username=self.user,
            password=self.password,
            port=self.port,
        )

    async def _run(self, func):
        """Ejecuta operacion sincrona de librouteros en thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, func)

    async def get_active_sessions(self) -> list[dict]:
        """Lista sesiones PPPoE activas."""
        def _fetch():
            api = self._connect()
            try:
                result = list(api.path("/ppp/active"))
                return [dict(r) for r in result]
            finally:
                api.close()

        return await self._run(_fetch)

    async def find_session_by_ip(self, ip: str) -> dict | None:
        """Busca sesion PPPoE por IP asignada."""
        sessions = await self.get_active_sessions()
        for s in sessions:
            if s.get("address") == ip:
                return s
        return None

    async def find_session_by_name(self, name: str) -> dict | None:
        """Busca sesion PPPoE por nombre de usuario."""
        sessions = await self.get_active_sessions()
        name_lower = name.lower()
        for s in sessions:
            if (s.get("name") or "").lower() == name_lower:
                return s
        return None

    async def ping(self, address: str, count: int = 4) -> dict:
        """Hace ping a una IP desde el MikroTik."""
        def _ping():
            api = self._connect()
            try:
                params = {
                    "address": address,
                    "count": str(count),
                }
                results = list(api.path("/ping", **params))

                if not results:
                    return {"success": False, "sent": count, "received": 0, "lost": count}

                # librouteros returns intermediate results + summary
                # The last entry usually has the summary
                received = 0
                total_rtt = 0
                rtt_count = 0

                for r in results:
                    r = dict(r)
                    if "time" in r:
                        received += 1
                        try:
                            # time can be like "1ms" or just a number
                            t = str(r["time"]).replace("ms", "").strip()
                            total_rtt += int(t)
                            rtt_count += 1
                        except (ValueError, TypeError):
                            pass

                avg_rtt = round(total_rtt / rtt_count) if rtt_count > 0 else None

                return {
                    "success": received > 0,
                    "sent": count,
                    "received": received,
                    "lost": count - received,
                    "avg_rtt": avg_rtt,
                }
            finally:
                api.close()

        return await self._run(_ping)

    async def get_ppp_secrets(self) -> list[dict]:
        """Lista secrets PPP configurados."""
        def _fetch():
            api = self._connect()
            try:
                result = list(api.path("/ppp/secret"))
                return [dict(r) for r in result]
            finally:
                api.close()

        return await self._run(_fetch)

    async def create_ppp_secret(
        self, name: str, password: str, profile: str, service: str = "pppoe"
    ) -> dict:
        """Crea un secret PPPoE en el MikroTik."""
        def _create():
            api = self._connect()
            try:
                path = api.path("/ppp/secret")
                result = path.add(
                    name=name,
                    password=password,
                    profile=profile,
                    service=service,
                )
                return {"success": True, "id": str(result)}
            finally:
                api.close()

        return await self._run(_create)

    async def update_ppp_secret(self, secret_id: str, **kwargs) -> dict:
        """Actualiza campos de un secret PPPoE (profile, password, etc)."""
        def _update():
            api = self._connect()
            try:
                path = api.path("/ppp/secret")
                params = {".id": secret_id, **kwargs}
                path.update(**params)
                return {"success": True}
            finally:
                api.close()

        return await self._run(_update)

    async def get_ppp_profiles(self) -> list[dict]:
        """Lista perfiles PPP disponibles."""
        def _fetch():
            api = self._connect()
            try:
                result = list(api.path("/ppp/profile"))
                return [dict(r) for r in result]
            finally:
                api.close()

        return await self._run(_fetch)

    async def get_neighbors(self) -> list[dict]:
        """Lista neighbors detectados via CDP/LLDP."""
        def _fetch():
            api = self._connect()
            try:
                result = list(api.path("/ip/neighbor"))
                return [dict(r) for r in result]
            finally:
                api.close()

        return await self._run(_fetch)

    async def find_secret_by_name(self, name: str) -> dict | None:
        """Busca secret PPPoE por nombre (exacto, luego parcial)."""
        secrets = await self.get_ppp_secrets()
        name_lower = name.lower()
        # Exacto
        for s in secrets:
            if (s.get("name") or "").lower() == name_lower:
                return s
        # Parcial
        for s in secrets:
            if name_lower in (s.get("name") or "").lower():
                return s
        return None

    async def suspend_client(self, secret_name: str) -> str | None:
        """Cambia perfil PPPoE a 'Morosos'. Retorna perfil anterior o None si falla."""
        secret = await self.find_secret_by_name(secret_name)
        if not secret:
            return None
        previous_profile = secret.get("profile", "default")
        if previous_profile == "Morosos":
            return previous_profile  # ya suspendido
        secret_id = secret.get(".id")
        if not secret_id:
            return None
        result = await self.update_ppp_secret(secret_id, profile="Morosos")
        if result.get("success"):
            return previous_profile
        return None

    async def unsuspend_client(self, secret_name: str, profile: str = "default") -> bool:
        """Restaura perfil PPPoE original."""
        secret = await self.find_secret_by_name(secret_name)
        if not secret:
            return False
        secret_id = secret.get(".id")
        if not secret_id:
            return False
        result = await self.update_ppp_secret(secret_id, profile=profile)
        return result.get("success", False)

    async def test_connection(self) -> bool:
        """Prueba la conexion al MikroTik."""
        try:
            def _test():
                api = self._connect()
                api.close()
                return True
            return await self._run(_test)
        except Exception as e:
            log.error("MikroTik connection test failed: %s", e)
            return False
