"""Almacenamiento de comprobantes de pago en disco."""

import time
from pathlib import Path
from src.utils.logger import log


class ReceiptStorage:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, client_id: str, image_bytes: bytes) -> str:
        """Guarda imagen y retorna ruta relativa."""
        client_dir = self.base_path / str(client_id)
        client_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{int(time.time())}.jpg"
        filepath = client_dir / filename
        filepath.write_bytes(image_bytes)
        log.info("Comprobante guardado: %s", filepath)
        return str(filepath)
