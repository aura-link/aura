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
        await self._migrate()
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
                service_id TEXT,
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

            CREATE TABLE IF NOT EXISTS device_state (
                device_id TEXT PRIMARY KEY,
                device_name TEXT,
                device_ip TEXT,
                site_id TEXT,
                status TEXT NOT NULL,
                role TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS zone_mapping (
                endpoint_site_id TEXT PRIMARY KEY,
                endpoint_site_name TEXT,
                infra_site_id TEXT NOT NULL,
                infra_site_name TEXT,
                crm_client_id TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_zone_infra ON zone_mapping(infra_site_id);
            CREATE INDEX IF NOT EXISTS idx_zone_crm ON zone_mapping(crm_client_id);

            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                device_name TEXT,
                site_id TEXT,
                site_name TEXT,
                status TEXT DEFAULT 'active',
                affected_clients INTEGER DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_incident_status ON incidents(status);

            CREATE TABLE IF NOT EXISTS maintenance_windows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site_id TEXT,
                site_name TEXT,
                description TEXT,
                starts_at TIMESTAMP NOT NULL,
                ends_at TIMESTAMP NOT NULL,
                created_by INTEGER,
                notified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                reference_id TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_notif_user ON notification_log(telegram_user_id, notification_type, sent_at DESC);

            CREATE TABLE IF NOT EXISTS payment_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT NOT NULL,
                telegram_user_id INTEGER NOT NULL,
                amount REAL,
                method TEXT,
                receipt_path TEXT,
                ai_analysis TEXT,
                matched_invoice_ids TEXT,
                crm_payment_id INTEGER,
                status TEXT DEFAULT 'pending',
                admin_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_payment_reports_status ON payment_reports(status);
            CREATE INDEX IF NOT EXISTS idx_payment_reports_client ON payment_reports(client_id);

            CREATE TABLE IF NOT EXISTS billing_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT NOT NULL,
                telegram_user_id INTEGER,
                notification_type TEXT NOT NULL,
                invoice_id TEXT,
                billing_month TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_billing_notif ON billing_notifications(client_id, notification_type, billing_month);

            CREATE TABLE IF NOT EXISTS fraud_strikes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT NOT NULL,
                telegram_user_id INTEGER NOT NULL,
                report_id INTEGER,
                strike_number INTEGER NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_fraud_client ON fraud_strikes(client_id);

            CREATE TABLE IF NOT EXISTS suspension_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id TEXT NOT NULL,
                secret_name TEXT,
                service_id TEXT,
                previous_profile TEXT,
                suspended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                unsuspended_at TIMESTAMP,
                reason TEXT DEFAULT 'nonpayment',
                suspended_by TEXT DEFAULT 'scheduler'
            );
            CREATE INDEX IF NOT EXISTS idx_suspension_client ON suspension_log(client_id);
        """)
        await self.db.commit()

    async def _migrate(self):
        """Migraciones incrementales para tablas existentes."""
        # Add service_id column if missing (for existing DBs)
        cursor = await self.db.execute("PRAGMA table_info(customer_links)")
        cols = [row[1] for row in await cursor.fetchall()]
        if "service_id" not in cols:
            await self.db.execute("ALTER TABLE customer_links ADD COLUMN service_id TEXT")
            await self.db.commit()
            log.info("Migración: columna service_id agregada a customer_links")

    # -- customer_links --

    async def link_customer(
        self, telegram_user_id: int, telegram_username: str | None,
        crm_client_id: str, crm_client_name: str, service_id: str | None = None
    ):
        await self.db.execute(
            """INSERT OR REPLACE INTO customer_links
               (telegram_user_id, telegram_username, crm_client_id, crm_client_name, service_id)
               VALUES (?, ?, ?, ?, ?)""",
            (telegram_user_id, telegram_username, crm_client_id, crm_client_name, service_id),
        )
        await self.db.commit()

    async def get_all_customer_links(self) -> list[dict]:
        cursor = await self.db.execute("SELECT * FROM customer_links")
        return [dict(row) for row in await cursor.fetchall()]

    async def get_link_by_service_id(self, service_id: str) -> dict | None:
        cursor = await self.db.execute(
            "SELECT * FROM customer_links WHERE service_id = ?",
            (service_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

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

    # -- device_state --

    async def upsert_device_state(self, device_id: str, device_name: str,
                                   device_ip: str, site_id: str | None,
                                   status: str, role: str | None):
        await self.db.execute(
            """INSERT INTO device_state (device_id, device_name, device_ip, site_id, status, role, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(device_id) DO UPDATE SET
               device_name=excluded.device_name, device_ip=excluded.device_ip,
               site_id=excluded.site_id, status=excluded.status, role=excluded.role,
               updated_at=CURRENT_TIMESTAMP""",
            (device_id, device_name, device_ip, site_id, status, role),
        )

    async def get_device_state(self, device_id: str) -> dict | None:
        cursor = await self.db.execute(
            "SELECT * FROM device_state WHERE device_id = ?", (device_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_all_device_states(self) -> list[dict]:
        cursor = await self.db.execute("SELECT * FROM device_state")
        return [dict(r) for r in await cursor.fetchall()]

    async def commit(self):
        await self.db.commit()

    # -- zone_mapping --

    async def rebuild_zone_mapping(self, mappings: list[dict]):
        await self.db.execute("DELETE FROM zone_mapping")
        for m in mappings:
            await self.db.execute(
                """INSERT INTO zone_mapping
                   (endpoint_site_id, endpoint_site_name, infra_site_id, infra_site_name, crm_client_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (m["endpoint_site_id"], m.get("endpoint_site_name"),
                 m["infra_site_id"], m.get("infra_site_name"),
                 m.get("crm_client_id")),
            )
        await self.db.commit()

    async def get_clients_for_infra_site(self, infra_site_id: str) -> list[dict]:
        cursor = await self.db.execute(
            """SELECT zm.crm_client_id, cl.telegram_user_id
               FROM zone_mapping zm
               LEFT JOIN customer_links cl ON zm.crm_client_id = cl.crm_client_id
               WHERE zm.infra_site_id = ? AND zm.crm_client_id IS NOT NULL""",
            (infra_site_id,),
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def get_zone_summary(self) -> list[dict]:
        cursor = await self.db.execute(
            """SELECT infra_site_id, infra_site_name,
                      COUNT(*) as total_endpoints,
                      COUNT(crm_client_id) as total_clients
               FROM zone_mapping
               GROUP BY infra_site_id
               ORDER BY total_clients DESC""",
        )
        return [dict(r) for r in await cursor.fetchall()]

    # -- incidents --

    async def create_incident(self, device_id: str, device_name: str,
                               site_id: str | None, site_name: str | None,
                               affected_clients: int) -> int:
        cursor = await self.db.execute(
            """INSERT INTO incidents (device_id, device_name, site_id, site_name, affected_clients)
               VALUES (?, ?, ?, ?, ?)""",
            (device_id, device_name, site_id, site_name, affected_clients),
        )
        await self.db.commit()
        return cursor.lastrowid  # type: ignore

    async def resolve_incident(self, incident_id: int):
        await self.db.execute(
            """UPDATE incidents SET status = 'resolved', resolved_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (incident_id,),
        )
        await self.db.commit()

    async def get_active_incidents(self) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM incidents WHERE status = 'active' ORDER BY started_at DESC"
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def get_incident_by_device(self, device_id: str) -> dict | None:
        cursor = await self.db.execute(
            "SELECT * FROM incidents WHERE device_id = ? AND status = 'active'",
            (device_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_recent_incidents(self, limit: int = 10) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM incidents ORDER BY started_at DESC LIMIT ?", (limit,)
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def get_active_incident_for_client(self, crm_client_id: str) -> dict | None:
        """Busca incidente activo que afecte al cliente via zone_mapping."""
        cursor = await self.db.execute(
            """SELECT i.* FROM incidents i
               JOIN zone_mapping zm ON i.site_id = zm.infra_site_id
               WHERE zm.crm_client_id = ? AND i.status = 'active'
               LIMIT 1""",
            (crm_client_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    # -- maintenance_windows --

    async def create_maintenance(self, site_id: str | None, site_name: str | None,
                                  description: str, starts_at: str, ends_at: str,
                                  created_by: int) -> int:
        cursor = await self.db.execute(
            """INSERT INTO maintenance_windows
               (site_id, site_name, description, starts_at, ends_at, created_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (site_id, site_name, description, starts_at, ends_at, created_by),
        )
        await self.db.commit()
        return cursor.lastrowid  # type: ignore

    async def get_active_maintenance(self) -> list[dict]:
        cursor = await self.db.execute(
            """SELECT * FROM maintenance_windows
               WHERE ends_at > datetime('now')
               ORDER BY starts_at ASC"""
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def get_maintenance_for_client(self, crm_client_id: str) -> dict | None:
        """Busca mantenimiento activo que afecte al cliente."""
        cursor = await self.db.execute(
            """SELECT mw.* FROM maintenance_windows mw
               JOIN zone_mapping zm ON mw.site_id = zm.infra_site_id
               WHERE zm.crm_client_id = ?
               AND mw.starts_at <= datetime('now')
               AND mw.ends_at > datetime('now')
               LIMIT 1""",
            (crm_client_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_pending_maintenance(self) -> list[dict]:
        """Mantenimientos no notificados que ya van a comenzar (dentro de 30 min)."""
        cursor = await self.db.execute(
            """SELECT * FROM maintenance_windows
               WHERE notified = 0
               AND starts_at <= datetime('now', '+30 minutes')
               AND ends_at > datetime('now')"""
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def mark_maintenance_notified(self, maintenance_id: int):
        await self.db.execute(
            "UPDATE maintenance_windows SET notified = 1 WHERE id = ?",
            (maintenance_id,),
        )
        await self.db.commit()

    async def cancel_maintenance(self, maintenance_id: int):
        await self.db.execute(
            "DELETE FROM maintenance_windows WHERE id = ?",
            (maintenance_id,),
        )
        await self.db.commit()

    # -- notification_log --

    async def log_notification(self, telegram_user_id: int, notification_type: str,
                                reference_id: str):
        await self.db.execute(
            """INSERT INTO notification_log (telegram_user_id, notification_type, reference_id)
               VALUES (?, ?, ?)""",
            (telegram_user_id, notification_type, reference_id),
        )
        await self.db.commit()

    async def was_notified_recently(self, telegram_user_id: int, notification_type: str,
                                     reference_id: str, cooldown_seconds: int) -> bool:
        cursor = await self.db.execute(
            """SELECT 1 FROM notification_log
               WHERE telegram_user_id = ? AND notification_type = ? AND reference_id = ?
               AND sent_at > datetime('now', ? || ' seconds')
               LIMIT 1""",
            (telegram_user_id, notification_type, reference_id, f"-{cooldown_seconds}"),
        )
        return await cursor.fetchone() is not None

    # -- payment_reports --

    async def create_payment_report(
        self, client_id: str, telegram_user_id: int, amount: float | None,
        method: str | None, receipt_path: str | None, ai_analysis: str | None,
        matched_invoice_ids: str | None, status: str = "pending"
    ) -> int:
        cursor = await self.db.execute(
            """INSERT INTO payment_reports
               (client_id, telegram_user_id, amount, method, receipt_path,
                ai_analysis, matched_invoice_ids, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (client_id, telegram_user_id, amount, method, receipt_path,
             ai_analysis, matched_invoice_ids, status),
        )
        await self.db.commit()
        return cursor.lastrowid  # type: ignore

    async def get_pending_payment_reports(self) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM payment_reports WHERE status = 'pending' ORDER BY created_at DESC"
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def update_payment_report(self, report_id: int, **kwargs):
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [report_id]
        await self.db.execute(
            f"UPDATE payment_reports SET {sets} WHERE id = ?", vals
        )
        await self.db.commit()

    async def find_payment_report_by_reference(self, client_id: str, reference: str) -> dict | None:
        """Find existing payment report with same reference number."""
        cursor = await self.db.execute(
            """SELECT * FROM payment_reports
               WHERE client_id = ? AND ai_analysis LIKE ?
               AND status IN ('approved', 'pending')
               ORDER BY created_at DESC LIMIT 1""",
            (client_id, f'%"reference": "{reference}"%'),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def find_recent_payment_report(self, client_id: str, amount: float,
                                          hours: int = 24) -> dict | None:
        """Find recent payment report with same amount from same client."""
        cursor = await self.db.execute(
            """SELECT * FROM payment_reports
               WHERE client_id = ? AND amount = ?
               AND status IN ('approved', 'pending')
               AND created_at > datetime('now', ? || ' hours')
               ORDER BY created_at DESC LIMIT 1""",
            (client_id, amount, f"-{hours}"),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_payment_report(self, report_id: int) -> dict | None:
        cursor = await self.db.execute(
            "SELECT * FROM payment_reports WHERE id = ?", (report_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    # -- billing_notifications --

    async def was_billing_notified(self, client_id: str, notification_type: str,
                                    billing_month: str) -> bool:
        cursor = await self.db.execute(
            """SELECT 1 FROM billing_notifications
               WHERE client_id = ? AND notification_type = ? AND billing_month = ?
               LIMIT 1""",
            (client_id, notification_type, billing_month),
        )
        return await cursor.fetchone() is not None

    async def log_billing_notification(self, client_id: str, telegram_user_id: int | None,
                                        notification_type: str, invoice_id: str | None,
                                        billing_month: str):
        await self.db.execute(
            """INSERT INTO billing_notifications
               (client_id, telegram_user_id, notification_type, invoice_id, billing_month)
               VALUES (?, ?, ?, ?, ?)""",
            (client_id, telegram_user_id, notification_type, invoice_id, billing_month),
        )
        await self.db.commit()

    # -- fraud_strikes --

    async def get_fraud_strike_count(self, client_id: str) -> int:
        cursor = await self.db.execute(
            "SELECT COUNT(*) FROM fraud_strikes WHERE client_id = ?",
            (client_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def add_fraud_strike(self, client_id: str, telegram_user_id: int,
                                report_id: int, reason: str) -> int:
        count = await self.get_fraud_strike_count(client_id)
        strike_number = count + 1
        await self.db.execute(
            """INSERT INTO fraud_strikes
               (client_id, telegram_user_id, report_id, strike_number, reason)
               VALUES (?, ?, ?, ?, ?)""",
            (client_id, telegram_user_id, report_id, strike_number, reason),
        )
        await self.db.commit()
        return strike_number

    async def reset_fraud_strikes(self, client_id: str):
        await self.db.execute(
            "DELETE FROM fraud_strikes WHERE client_id = ?", (client_id,)
        )
        await self.db.commit()

    # -- suspension_log --

    async def log_suspension(
        self, client_id: str, secret_name: str | None, service_id: str | None,
        previous_profile: str | None, reason: str = "nonpayment",
        suspended_by: str = "scheduler"
    ) -> int:
        cursor = await self.db.execute(
            """INSERT INTO suspension_log
               (client_id, secret_name, service_id, previous_profile, reason, suspended_by)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (client_id, secret_name, service_id, previous_profile, reason, suspended_by),
        )
        await self.db.commit()
        return cursor.lastrowid  # type: ignore

    async def log_unsuspension(self, client_id: str):
        await self.db.execute(
            """UPDATE suspension_log SET unsuspended_at = CURRENT_TIMESTAMP
               WHERE client_id = ? AND unsuspended_at IS NULL""",
            (client_id,),
        )
        await self.db.commit()

    async def get_active_suspensions(self) -> list[dict]:
        cursor = await self.db.execute(
            """SELECT * FROM suspension_log
               WHERE unsuspended_at IS NULL
               ORDER BY suspended_at DESC"""
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def get_suspension_for_client(self, client_id: str) -> dict | None:
        cursor = await self.db.execute(
            """SELECT * FROM suspension_log
               WHERE client_id = ? AND unsuspended_at IS NULL
               ORDER BY suspended_at DESC LIMIT 1""",
            (client_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

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
