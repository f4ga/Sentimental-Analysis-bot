"""
Сервис бота для работы с API.
"""

import aiohttp
import os
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)

# Конфигурация API
API_HOST = os.getenv("API_HOST", "localhost")
API_PORT = os.getenv("API_PORT", "8000")
API_BASE = f"http://{API_HOST}:{API_PORT}"

# Кэш для результатов анализа
result_cache: Dict[str, dict] = {}
cache_limit = 100  # Максимальное количество записей в кэше

# История запросов пользователя
user_histories: Dict[int, List[dict]] = {}
history_limit = 50  # Максимальное количество записей в истории пользователя


@dataclass(frozen=True)
class SentimentResult:
    """Результат анализа тональности."""

    text: str
    sentiment: str
    confidence: float
    timestamp: datetime


@dataclass(frozen=True)
class APIStats:
    """Статистика API."""

    total_requests: int
    positive: int
    negative: int
    neutral: int
    uptime_seconds: float = 0.0


def _add_to_cache(text: str, result: dict) -> None:
    """Добавляет результат в кэш."""
    if len(result_cache) >= cache_limit:
        # Удаляем самую старую запись
        oldest_key = next(iter(result_cache))
        del result_cache[oldest_key]

    result_cache[text] = result


def _get_from_cache(text: str) -> Optional[dict]:
    """Получает результат из кэша."""
    return result_cache.get(text)


def _add_to_history(user_id: int, result: dict) -> None:
    """Добавляет результат в историю пользователя."""
    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append(
        {"timestamp": datetime.now().isoformat(), "result": result}
    )

    # Ограничиваем размер истории
    if len(user_histories[user_id]) > history_limit:
        user_histories[user_id].pop(0)


def get_user_history(user_id: int) -> List[dict]:
    """Получает историю запросов пользователя."""
    return user_histories.get(user_id, [])


async def analyze_text(text: str, user_id: int | None = None) -> SentimentResult | None:
    """Анализирует текст через API.

    Returns:
        SentimentResult или None при ошибке.
    """
    # Проверяем кэш
    cached_result = _get_from_cache(text)
    if cached_result:
        logger.info(f"Результат найден в кэше для user_id={user_id}")
        return SentimentResult(
            text=cached_result["text"],
            sentiment=cached_result["sentiment"],
            confidence=float(cached_result["confidence"]),
            timestamp=datetime.fromisoformat(
                cached_result["timestamp"].replace("Z", "+00:00")
            ),
        )

    logger.info(f"Анализ для user_id={user_id}: {text[:50]}...")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{API_BASE}/predict",
                json={"text": text, "userId": user_id},
                timeout=10,
            ) as response:

                if response.status == 200:
                    data = await response.json()

                    # Сохраняем в кэш
                    _add_to_cache(text, data)

                    # Сохраняем в историю пользователя
                    if user_id:
                        _add_to_history(user_id, data)

                    return SentimentResult(
                        text=data["text"],
                        sentiment=data["sentiment"],
                        confidence=float(data["confidence"]),
                        timestamp=datetime.fromisoformat(
                            data["timestamp"].replace("Z", "+00:00")
                        ),
                    )
                else:
                    logger.error(f"Ошибка API: {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Ошибка запроса: {e}")
            return None


async def fetch_stats() -> APIStats:
    """Получает статистику с API."""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{API_BASE}/stats", timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    return APIStats(
                        total_requests=data.get("total_requests", 0),
                        positive=data.get("positive", 0),
                        negative=data.get("negative", 0),
                        neutral=data.get("neutral", 0),
                        uptime_seconds=data.get("uptime_seconds", 0.0),
                    )
                else:
                    logger.error(f"Ошибка получения статистики: {response.status}")
                    return APIStats(0, 0, 0, 0)
        except Exception as e:
            logger.error(f"Ошибка запроса статистики: {e}")
            return APIStats(0, 0, 0, 0)
