"""Zone mapper: construye mapeo infraestructura -> clientes desde sitios UISP."""

import asyncio
from src.utils.logger import log


class ZoneMapper:
    def __init__(self, nms, crm, db):
        self.nms = nms
        self.crm = crm
        self.db = db
        self._last_rebuild = 0

    async def rebuild(self):
        """Reconstruye zone_mapping desde la API de sitios UISP."""
        try:
            sites = await self.nms.get_sites_fresh()
        except Exception as e:
            log.error("Error obteniendo sitios para zone mapping: %s", e)
            return

        # Separar sitios por tipo
        infra_sites = {}  # id -> site (type=site)
        endpoint_sites = []  # type=endpoint

        for s in sites:
            sid = s.get("id", "")
            stype = (s.get("identification", {}) or {}).get("type", "")
            if stype == "site":
                infra_sites[sid] = s
            elif stype == "endpoint":
                endpoint_sites.append(s)

        # Construir mappings: endpoint -> parent (infra) -> crm client
        mappings = []
        for ep in endpoint_sites:
            ep_id = ep.get("id", "")
            ep_ident = ep.get("identification", {}) or {}
            ep_name = ep_ident.get("name", "")

            # parent puede ser {"id": "..."} o un string
            parent_raw = ep_ident.get("parent")
            if isinstance(parent_raw, dict):
                parent_id = parent_raw.get("id", "")
            else:
                parent_id = parent_raw or ""

            if not parent_id or parent_id not in infra_sites:
                continue

            parent = infra_sites[parent_id]
            parent_name = (parent.get("identification", {}) or {}).get("name", "")

            # Obtener CRM client ID del endpoint
            crm_id = None
            ucrm = ep.get("ucrm", {}) or {}
            if ucrm.get("client"):
                cid = ucrm["client"].get("id", "")
                if cid:
                    crm_id = str(cid)

            mappings.append({
                "endpoint_site_id": ep_id,
                "endpoint_site_name": ep_name,
                "infra_site_id": parent_id,
                "infra_site_name": parent_name,
                "crm_client_id": crm_id,
            })

        await self.db.rebuild_zone_mapping(mappings)
        log.info("Zone mapping rebuilt: %d endpoints, %d infra sites",
                 len(mappings), len(infra_sites))

    async def get_affected_clients(self, site_id: str) -> list[dict]:
        """Obtiene clientes afectados por una caida en un sitio de infraestructura."""
        return await self.db.get_clients_for_infra_site(site_id)

    async def get_zone_summary(self) -> list[dict]:
        """Resumen de zonas para comando /zonas."""
        return await self.db.get_zone_summary()
