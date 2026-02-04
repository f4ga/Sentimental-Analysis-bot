"""
Сервис бота для работы с API.
"""

import aiohttp
import os
import logging
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Конфигурация API
API_HOST = os.getenv("API_HOST", "localhost")
API_PORT = os.getenv("API_PORT", "8000")
API_BASE = f"http://{API_HOST}:{API_PORT}"


@dataclass(frozen=True)
class SentimentResult:
    """Результат анализа тональности."""

    text: str
    sentiment: str
    confidence: float
    timestamp: datetime


@dataclass(frozen=True)
class APIStats:
    """Статистика API для удобного доступа."""

    total_requests: int
    positive: int
    negative: int
    neutral: int


async def analyze_text(text: str, user_id: int | None = None) -> SentimentResult | None:
    """Анализирует текст через API.

    Returns:
        SentimentResult или None при ошибке.
    """
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
                    )
                else:
                    logger.error(f"Ошибка получения статистики: {response.status}")
                    return APIStats(0, 0, 0, 0)
        except Exception as e:
            logger.error(f"Ошибка запроса статистики: {e}")
            return APIStats(0, 0, 0, 0)
