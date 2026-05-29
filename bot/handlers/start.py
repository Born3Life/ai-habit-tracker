from __future__ import annotations

import logging
from datetime import datetime

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.markdown import hbold

from bot.keyboards.menu import main_keyboard
from bot.services.storage import register_user, user_info

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def handle_start(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    created = await register_user(user.id, user.username, user.full_name)

    if created:
        text = (
            f"Привет, {hbold(user.full_name)}! 🌟\n\n"
            "Я — твой AI-коуч. Каждый вечер я буду напоминать, "
            "а ты будешь писать, что сделал за день.\n\n"
            "Я похвалю, дам совет и раз в неделю — саммари прогресса.\n"
            "7 дней бесплатно, дальше 590₽/мес.\n\n"
            "Готов? Напиши, что сделал сегодня:"
        )
    else:
        info = await user_info(user.id)
        trial_end = ""
        if info:
            trial_end = info.get("trial_end", "")[:10]

        text = (
            f"С возвращением, {hbold(user.full_name)}! 🌟\n\n"
            f"Пробный период до {trial_end}.\n"
            "Напиши, что сделал сегодня:"
        )

    await message.answer(text, reply_markup=main_keyboard())


@router.message(lambda msg: msg.text in ("ℹ️ О статусе", "📊 Мой прогресс"))
async def handle_status(message: types.Message) -> None:
    user = message.from_user
    if user is None:
        return

    info = await user_info(user.id)
    if not info:
        await message.answer("Ты не зарегистрирован. Напиши /start")
        return

    trial_end = datetime.fromisoformat(info["trial_end"])
    now = datetime.utcnow()
    days_left = (trial_end - now).days

    status = "✅ Активен" if info["is_active"] else "❌ Неактивен"
    paid = "💎 Премиум" if info["is_paid"] else "🆓 Бесплатный"
    trial = f"{days_left} дн." if days_left > 0 else "❌ Закончился"

    lines = [
        "📊 **Мой статус**",
        f"Тариф: {paid}",
        f"Пробный: {trial}",
        f"Статус: {status}",
    ]
    if not info["is_paid"] and days_left <= 0:
        lines.append("\nПробный период закончился.\n590₽/мес — продли доступ.")

    await message.answer("\n".join(lines))
