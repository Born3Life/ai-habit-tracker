from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time

from aiogram import Bot

from bot.services.storage import get_reminder_candidates

logger = logging.getLogger(__name__)

REMINDER_HOUR = 21
REMINDER_MINUTE = 0
CHECK_INTERVAL = 60


async def _send_reminder(bot: Bot, user_id: int) -> None:
    try:
        await bot.send_message(
            user_id,
            "🌙 Что ты сделал сегодня для своих целей?\n"
            "Напиши пару предложений — я похвалю и дам совет.",
        )
    except Exception:
        logger.warning("reminder fail for %d", user_id)


async def reminder_loop(bot: Bot) -> None:
    """Check every minute if it's reminder time and notify candidates."""
    last_remind_date: date | None = None

    while True:
        now = datetime.now()
        remind_time = time(REMINDER_HOUR, REMINDER_MINUTE)
        today = now.date()

        if now.time() >= remind_time and last_remind_date != today:
            candidates = await get_reminder_candidates()
            for uid in candidates:
                await _send_reminder(bot, uid)
            last_remind_date = today
            logger.info("reminded %d users", len(candidates))

        await asyncio.sleep(CHECK_INTERVAL)
