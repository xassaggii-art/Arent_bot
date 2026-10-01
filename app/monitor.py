import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError

from app.config import settings
from app.fetcher import FetchError
from app.formatters import format_listing_message
from app.models import (
    FACEBOOK_FEED_URLS,
    LIST_AM_FEED_URLS,
    FeedKey,
    Listing,
)
from app.scrapers.facebook import scrape_facebook
from app.scrapers.list_am import scrape_list_am
from app.storage import Database

logger = logging.getLogger(__name__)


class MonitorService:
    def __init__(self, db: Database, bot: Bot) -> None:
        self.db = db
        self.bot = bot
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run_loop(), name="monitor-loop")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task

    async def _run_loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self.run_once()
            except Exception:
                logger.exception("Monitor cycle failed")
                await self._notify_admin("⚠️ Ошибка цикла мониторинга — см. логи.")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=settings.poll_interval_sec)
            except asyncio.TimeoutError:
                pass

    async def run_once(self) -> None:
        for feed_key, url in LIST_AM_FEED_URLS.items():
            await self._process_feed(feed_key, url, source="list_am")

        if settings.facebook_enabled:
            for feed_key, url in FACEBOOK_FEED_URLS.items():
                await self._process_feed(
                    feed_key,
                    url,
                    source="facebook",
                )

    async def _process_feed(self, feed_key: FeedKey, url: str, *, source: str) -> None:
        subscribers = await self.db.subscribers_for_feed(feed_key)
        if not subscribers:
            return

        try:
            if source == "list_am":
                listings = await scrape_list_am(url, feed_key)
            else:
                listings = await scrape_facebook(
                    url,
                    feed_key,
                    cookie_header=settings.facebook_cookie,
                )
        except FetchError as exc:
            logger.warning("Fetch failed for %s: %s", feed_key.value, exc)
            return

        for item in listings:
            if not await self.db.mark_seen_if_new(item.dedupe_key):
                continue
            await self._broadcast(item, subscribers)

    async def _broadcast(self, item: Listing, chat_ids: list[int]) -> None:
        text = format_listing_message(item)
        for chat_id in chat_ids:
            try:
                if item.image_url:
                    await self.bot.send_photo(
                        chat_id,
                        item.image_url,
                        caption=text,
                        parse_mode="HTML",
                    )
                else:
                    await self.bot.send_message(chat_id, text, parse_mode="HTML", disable_web_page_preview=False)
            except TelegramForbiddenError:
                logger.info("User %s blocked the bot — disabling", chat_id)
                await self.db.set_subscriber_enabled(chat_id, False)
            except Exception:
                logger.exception("Failed to notify chat_id=%s", chat_id)

    async def _notify_admin(self, text: str) -> None:
        if not settings.admin_chat_id:
            return
        try:
            await self.bot.send_message(settings.admin_chat_id, text)
        except Exception:
            logger.exception("Failed to notify admin")
