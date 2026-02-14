"""Entry point de Aura Bot."""

import asyncio
from src.bot.app import create_application
from src.utils.logger import log


def main():
    log.info("Iniciando Aura Bot...")
    app = create_application()
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
