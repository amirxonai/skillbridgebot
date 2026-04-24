"""
run_all.py — Entry point to start both bot and web server simultaneously.
This is the file Render.com runs via: python run_all.py
"""

import asyncio
import logging
import sys
import os
import socket
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

# Ensure project root is in Python path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from skillbridge_bot.config import BOT_TOKEN, REDIS_URL
from skillbridge_bot.handlers import start, profile, search, rating, invite, admin, mentors, skills
from skillbridge_bot.services.queue_service import start_queue_worker, start_followup_worker
from skillbridge_bot.data.database import init_db
from skillbridge_site.backend.main import app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Try to import Redis storage, but don't fail if redis is not available
try:
    from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_free_port(start_port: int, max_port: int = 8100) -> int:
    port = start_port
    while port <= max_port:
        if not is_port_in_use(port):
            return port
        port += 1
    return -1


async def run_bot(bot: Bot, dp: Dispatcher) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("SkillBridge Bot is starting...")
    await asyncio.gather(
        dp.start_polling(bot),
        start_queue_worker(bot, interval_seconds=15),
        start_followup_worker(bot, interval_seconds=3600)
    )

async def run_web(bot: Bot) -> None:
    # Pass the bot instance to the FastAPI app state
    app.state.bot = bot

    host = os.getenv("HOST", os.getenv("WEB_HOST", "0.0.0.0"))
    # Render provides PORT environment variable. Fallback to WEB_PORT or 8000.
    requested_port = int(os.getenv("PORT", os.getenv("WEB_PORT", "8000")))
    
    # In cloud environments, we MUST bind exactly to the provided port to pass health checks.
    if os.getenv("PORT") or os.getenv("RENDER"):
        port = requested_port
    else:
        port = find_free_port(requested_port)
        if port == -1:
             logger.error(f"Could not find a free port starting from {requested_port}")
             sys.exit(1)
             
        if port != requested_port:
             logger.warning(f"Port {requested_port} is busy. Falling back to port {port}")

    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    logger.info(f"SkillBridge Web is starting on http://{host}:{port}...")
    await server.serve()

async def main() -> None:
    # Initialize the database
    init_db()
    
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("BOT_TOKEN is not set in .env file!")
        sys.exit(1)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Choose FSM storage
    if REDIS_URL and REDIS_AVAILABLE:
        storage = RedisStorage.from_url(REDIS_URL, key_builder=DefaultKeyBuilder(with_bot_id=True))
        logger.info("FSM Storage: Redis")
    else:
        storage = MemoryStorage()
        logger.info("FSM Storage: Memory (not recommended for production)")
        
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

    try:
        await asyncio.gather(
            run_bot(bot, dp),
            run_web(bot)
        )
    except (asyncio.CancelledError, KeyboardInterrupt):
        logger.info("Shutdown signal received")
    finally:
        await bot.session.close()
        logger.info("All services stopped.")

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
