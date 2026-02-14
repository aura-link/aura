"""Sistema de roles: GUEST, CUSTOMER, ADMIN."""

from enum import Enum
from src import config


class Role(Enum):
    GUEST = "guest"
    CUSTOMER = "customer"
    ADMIN = "admin"


def get_role(telegram_user_id: int, is_linked: bool = False) -> Role:
    if telegram_user_id in config.TELEGRAM_ADMIN_IDS:
        return Role.ADMIN
    if is_linked:
        return Role.CUSTOMER
    return Role.GUEST


def is_admin(telegram_user_id: int) -> bool:
    return telegram_user_id in config.TELEGRAM_ADMIN_IDS
