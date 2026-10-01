import aiosqlite

from app.models import FeedKey


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._migrate()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if not self._conn:
            raise RuntimeError("Database is not connected")
        return self._conn

    async def _migrate(self) -> None:
        await self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS subscribers (
                chat_id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                chat_id INTEGER NOT NULL,
                feed_key TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (chat_id, feed_key),
                FOREIGN KEY (chat_id) REFERENCES subscribers(chat_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS seen_listings (
                dedupe_key TEXT PRIMARY KEY,
                first_seen_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        await self.conn.commit()

    async def ensure_subscriber(self, chat_id: int) -> None:
        await self.conn.execute(
            "INSERT OR IGNORE INTO subscribers (chat_id) VALUES (?)",
            (chat_id,),
        )
        await self.conn.commit()

    async def set_subscriber_enabled(self, chat_id: int, enabled: bool) -> None:
        await self.ensure_subscriber(chat_id)
        await self.conn.execute(
            "UPDATE subscribers SET enabled = ? WHERE chat_id = ?",
            (1 if enabled else 0, chat_id),
        )
        await self.conn.commit()

    async def is_subscriber_enabled(self, chat_id: int) -> bool:
        cursor = await self.conn.execute(
            "SELECT enabled FROM subscribers WHERE chat_id = ?",
            (chat_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return True
        return bool(row["enabled"])

    async def set_feed(self, chat_id: int, feed_key: FeedKey, enabled: bool) -> None:
        await self.ensure_subscriber(chat_id)
        if enabled:
            await self.conn.execute(
                """
                INSERT INTO subscriptions (chat_id, feed_key, enabled)
                VALUES (?, ?, 1)
                ON CONFLICT(chat_id, feed_key) DO UPDATE SET enabled = 1
                """,
                (chat_id, feed_key.value),
            )
        else:
            await self.conn.execute(
                "DELETE FROM subscriptions WHERE chat_id = ? AND feed_key = ?",
                (chat_id, feed_key.value),
            )
        await self.conn.commit()

    async def is_feed_enabled(self, chat_id: int, feed_key: FeedKey) -> bool:
        cursor = await self.conn.execute(
            """
            SELECT 1 FROM subscriptions
            WHERE chat_id = ? AND feed_key = ? AND enabled = 1
            """,
            (chat_id, feed_key.value),
        )
        return await cursor.fetchone() is not None

    async def list_enabled_feeds(self, chat_id: int) -> list[FeedKey]:
        cursor = await self.conn.execute(
            """
            SELECT feed_key FROM subscriptions
            WHERE chat_id = ? AND enabled = 1
            ORDER BY feed_key
            """,
            (chat_id,),
        )
        rows = await cursor.fetchall()
        return [FeedKey(row["feed_key"]) for row in rows]

    async def subscribers_for_feed(self, feed_key: FeedKey) -> list[int]:
        cursor = await self.conn.execute(
            """
            SELECT s.chat_id
            FROM subscriptions s
            JOIN subscribers u ON u.chat_id = s.chat_id
            WHERE s.feed_key = ? AND s.enabled = 1 AND u.enabled = 1
            """,
            (feed_key.value,),
        )
        rows = await cursor.fetchall()
        return [int(row["chat_id"]) for row in rows]

    async def mark_seen_if_new(self, dedupe_key: str) -> bool:
        cursor = await self.conn.execute(
            "SELECT 1 FROM seen_listings WHERE dedupe_key = ?",
            (dedupe_key,),
        )
        if await cursor.fetchone():
            return False
        await self.conn.execute(
            "INSERT INTO seen_listings (dedupe_key) VALUES (?)",
            (dedupe_key,),
        )
        await self.conn.commit()
        return True
