"""
bot.py — SkillBridge Bot entry point.

Starts the polling loop AND the background queue matcher service.
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from skillbridge_bot.config import BOT_TOKEN
from skillbridge_bot.handlers import start, profile, search, rating, invite, admin, mentors, skills
from skillbridge_bot.services.queue_service import start_queue_worker, start_followup_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ BOT_TOKEN is not set in config.py or environment env!")
        sys.exit(1)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register all handlers
    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(search.router)
    dp.include_router(rating.router)
    dp.include_router(invite.router)
    dp.include_router(admin.router)
    dp.include_router(mentors.router)
    dp.include_router(skills.router)

    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("SkillBridge Bot is starting...")

    try:
        # Start both the aiogram polling AND our background worker as concurrent tasks
        await asyncio.gather(
            dp.start_polling(bot),
            start_queue_worker(bot, interval_seconds=15),
            start_followup_worker(bot, interval_seconds=3600)
        )
    except (asyncio.CancelledError, KeyboardInterrupt):
        pass
    finally:
        await bot.session.close()
        logger.info("👋 SkillBridge Bot has stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
