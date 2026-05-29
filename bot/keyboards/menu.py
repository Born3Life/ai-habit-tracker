from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Написать отчёт")],
            [
                KeyboardButton(text="📊 Мой прогресс"),
                KeyboardButton(text="ℹ️ О статусе"),
            ],
        ],
        resize_keyboard=True,
    )
