"""SQLite async database manager."""

import aiosqlite
from pathlib import Path
from src.utils.logger import log


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._create_tables()
        log.info("Base de datos conectada: %s", self.db_path)

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None
            log.info("Base de datos cerrada")

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Database not connected")
        return self._db

    async def _create_tables(self):
        await self.db.executescript("""
            CREATE TABLE IF NOT EXISTS customer_links (
                telegram_user_id INTEGER PRIMARY KEY,
                telegram_username TEXT,
                crm_client_id TEXT NOT NULL,
                crm_client_name TEXT,
                linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_conv_user
                ON conversation_history(telegram_user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS escalations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                telegram_username TEXT,
                crm_client_id TEXT,
                issue TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            );
        """)
        await self.db.commit()

    # -- customer_links --

    async def link_customer(
        self, telegram_user_id: int, telegram_username: str | None,
        crm_client_id: str, crm_client_name: str
    ):
        await self.db.execute(
            """INSERT OR REPLACE INTO customer_links
               (telegram_user_id, telegram_username, crm_client_id, crm_client_name)
               VALUES (?, ?, ?, ?)""",
            (telegram_user_id, telegram_username, crm_client_id, crm_client_name),
        )
        await self.db.commit()

    async def get_customer_link(self, telegram_user_id: int) -> dict | None:
        cursor = await self.db.execute(
            "SELECT * FROM customer_links WHERE telegram_user_id = ?",
            (telegram_user_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    # -- conversation_history --

    async def add_message(self, telegram_user_id: int, role: str, content: str):
        await self.db.execute(
            """INSERT INTO conversation_history (telegram_user_id, role, content)
               VALUES (?, ?, ?)""",
            (telegram_user_id, role, content),
        )
        await self.db.commit()

    async def get_history(self, telegram_user_id: int, limit: int = 20) -> list[dict]:
        cursor = await self.db.execute(
            """SELECT role, content FROM conversation_history
               WHERE telegram_user_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (telegram_user_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in reversed(rows)]

    async def clear_history(self, telegram_user_id: int):
        await self.db.execute(
            "DELETE FROM conversation_history WHERE telegram_user_id = ?",
            (telegram_user_id,),
        )
        await self.db.commit()

    # -- escalations --

    async def create_escalation(
        self, telegram_user_id: int, telegram_username: str | None,
        crm_client_id: str | None, issue: str
    ) -> int:
        cursor = await self.db.execute(
            """INSERT INTO escalations
               (telegram_user_id, telegram_username, crm_client_id, issue)
               VALUES (?, ?, ?, ?)""",
            (telegram_user_id, telegram_username, crm_client_id, issue),
        )
        await self.db.commit()
        return cursor.lastrowid  # type: ignore

    async def get_open_escalations(self) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM escalations WHERE status = 'open' ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def resolve_escalation(self, escalation_id: int):
        await self.db.execute(
            """UPDATE escalations SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (escalation_id,),
        )
        await self.db.commit()

    # -- rate limiting --

    async def get_ai_usage_today(self, telegram_user_id: int) -> int:
        """Cuenta cuantas consultas AI hizo el usuario hoy."""
        cursor = await self.db.execute(
            """SELECT COUNT(*) FROM conversation_history
               WHERE telegram_user_id = ? AND role = 'user'
               AND date(created_at) = date('now')""",
            (telegram_user_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0
