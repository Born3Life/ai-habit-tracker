from __future__ import annotations

import asyncio
import logging
import os
import sys
from os import getenv
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web
from dotenv import load_dotenv

from bot.handlers import routers
from bot.services.scheduler import reminder_loop
from bot.services.storage import init_db

load_dotenv(Path(__file__).parent.parent / ".env")

BOT_TOKEN = getenv("BOT_TOKEN")
TELEGRAM_PROXY = getenv("TELEGRAM_PROXY")

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


async def _health_handler(_request: web.Request) -> web.Response:
    return web.Response(text="ok")


async def _health_server(port: int) -> None:
    """Minimal HTTP server so Render doesn't kill the process."""
    app = web.Application()
    app.router.add_get("/health", _health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("health server listening on port %d", port)
    await asyncio.Event().wait()


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN not set")

    port = getenv("PORT")
    if port:
        asyncio.create_task(_health_server(int(port)))

    if TELEGRAM_PROXY:
        os.environ["HTTP_PROXY"] = TELEGRAM_PROXY
        os.environ["HTTPS_PROXY"] = TELEGRAM_PROXY

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    for router in routers:
        dp.include_router(router)

    await init_db()

    asyncio.create_task(reminder_loop(bot))

    logger.info("habit tracker started")
    await dp.start_polling(bot, polling_timeout=1)


if __name__ == "__main__":
    asyncio.run(main())
