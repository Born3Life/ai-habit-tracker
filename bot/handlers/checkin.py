from __future__ import annotations

import logging
from datetime import datetime, timedelta

from aiogram import Router, types

from bot.services.ai_service import checkin_reply, weekly_summary
from bot.services.storage import (
    add_checkin,
    get_recent_checkins,
    get_week_checkins,
    mark_summary_sent,
    user_info,
)

logger = logging.getLogger(__name__)

router = Router()


@router.message()
async def handle_checkin(message: types.Message) -> None:
    user = message.from_user
    if user is None or not message.text:
        return

    info = await user_info(user.id)
    if not info:
        await message.answer("Напиши /start, чтобы начать")
        return

    # Skip command/keyboard messages
    text = message.text.strip()
    if text in ("📝 Написать отчёт", "📊 Мой прогресс", "ℹ️ О статусе", "/start"):
        return

    # Check trial
    trial_end = datetime.fromisoformat(info["trial_end"])
    if not info["is_paid"] and datetime.utcnow() > trial_end:
        await message.answer(
            "🤷 Бесплатный период закончился.\n"
            "Для продолжения — 590₽/мес.\n"
            "Напиши /start, чтобы узнать детали.",
        )
        return

    sent = await message.answer("💭 Анализирую...")

    history = await get_recent_checkins(user.id)
    reply = await checkin_reply(text, history)
    await add_checkin(user.id, text, reply)

    await sent.edit_text(reply)

    # Weekly summary (once per week)
    week_checkins = await get_week_checkins(user.id)
    last_summary = info.get("last_summary_sent")
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    should_send = len(week_checkins) >= 6 and (
        last_summary is None or last_summary < week_ago
    )
    if should_send:
        summary = await weekly_summary(week_checkins)
        await message.answer(
            f"📊 **Твой еженедельный отчёт**\n\n{summary}",
        )
        await mark_summary_sent(user.id)
