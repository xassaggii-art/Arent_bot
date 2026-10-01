import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot_handlers import router
from app.config import settings
from app.middleware import DatabaseMiddleware
from app.monitor import MonitorService
from app.storage import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    db_path = Path(settings.database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db = Database(str(db_path))
    await db.connect()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.update.middleware(DatabaseMiddleware(db))
    dp.include_router(router)

    monitor = MonitorService(db, bot)
    monitor.start()

    try:
        logger.info("Bot started (poll every %ss)", settings.poll_interval_sec)
        await dp.start_polling(bot, db=db)
    finally:
        await monitor.stop()
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    if not os.getenv("BOT_TOKEN") and not settings.bot_token:
        raise SystemExit("Set BOT_TOKEN in .env")
    asyncio.run(main())
