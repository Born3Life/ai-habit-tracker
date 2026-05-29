from __future__ import annotations

import asyncio
import logging
from os import getenv
from typing import Any

import urllib3
from requests import Session

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

OPENROUTER_BASE = "https://openrouter.ai/api/v1/chat/completions"

CHECKIN_PROMPT = (
    "Ты — дружелюбный коуч. Пользователь написал, что сделал за день. "
    "Похвали, дай 1 микро-совет (1–2 предложения). На русском. "
    "Если он ничего не делал — мягко подбодри."
)

WEEKLY_PROMPT = (
    "Ты — коуч. Вот записи пользователя за неделю. "
    "Напиши краткое саммари (3–4 предложения), похвали прогресс, "
    "дай 1 совет на следующую неделю. На русском."
)


def _api_key() -> str | None:
    return getenv("OPENROUTER_API_KEY")


def _model() -> str:
    return getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")


def _proxy() -> str | None:
    return getenv("TELEGRAM_PROXY")


def _call(messages: list[dict]) -> str:
    key = _api_key()
    if not key:
        return "API-ключ не настроен."

    session = Session()
    session.verify = False
    proxy = _proxy()
    if proxy:
        session.proxies.update({"http": proxy, "https": proxy})
    session.headers.update({"Authorization": f"Bearer {key}"})

    payload: dict[str, Any] = {
        "model": _model(),
        "messages": messages,
        "max_tokens": 300,
    }

    try:
        resp = session.post(OPENROUTER_BASE, json=payload, timeout=30)
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        logger.exception("OpenRouter request failed")
        return "Не удалось получить ответ. Попробуй ещё раз."
    finally:
        session.close()


async def checkin_reply(user_text: str, history: list[dict]) -> str:
    messages = [{"role": "system", "content": CHECKIN_PROMPT}]
    for h in history[-6:]:
        messages.append({"role": "user", "content": h["text"]})
        if h.get("ai_response"):
            messages.append({"role": "assistant", "content": h["ai_response"]})
    messages.append({"role": "user", "content": user_text})

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _call, messages)


async def weekly_summary(checkins: list[dict]) -> str:
    entries = "\n".join(f"- {c['created_at'][:10]}: {c['text']}" for c in checkins)
    text = f"Записи за неделю:\n{entries}"
    messages = [
        {"role": "system", "content": WEEKLY_PROMPT},
        {"role": "user", "content": text},
    ]

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _call, messages)
