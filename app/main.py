"""
FastAPI сервис для анализа тональности.
"""

from contextlib import asynccontextmanager
from datetime import datetime
import logging
import json
import os
from typing import Dict, Any
from functools import wraps
import time

from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict

from ml_service import get_analyzer

logger = logging.getLogger(__name__)

# Файл для сохранения статистики
STATS_FILE = "stats.json"

# Хранилище для rate limiting
request_counts: Dict[str, int] = {}
last_reset = time.time()


# Загрузка статистики из файла
def load_stats():
    """Загружает статистику из файла при запуске."""
    global stats
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                stats.total = data.get("total", 0)
                stats.positive = data.get("positive", 0)
                stats.negative = data.get("negative", 0)
                stats.neutral = data.get("neutral", 0)
                stats.start_time = datetime.fromisoformat(
                    data.get("start_time", datetime.now().isoformat())
                )
            logger.info("Статистика загружена из файла")
    except Exception as e:
        logger.error(f"Ошибка загрузки статистики: {e}")


# Сохранение статистики в файл
def save_stats():
    """Сохраняет статистику в файл при завершении работы."""
    try:
        data = {
            "total": stats.total,
            "positive": stats.positive,
            "negative": stats.negative,
            "neutral": stats.neutral,
            "start_time": stats.start_time.isoformat(),
        }
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Статистика сохранена в файл")
    except Exception as e:
        logger.error(f"Ошибка сохранения статистики: {e}")


# Декоратор для rate limiting
def rate_limit(max_requests: int = 100, window: int = 60):
    """Декоратор для ограничения количества запросов."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            global last_reset
            current_time = time.time()

            # Сброс счетчиков каждые window секунд
            if current_time - last_reset > window:
                request_counts.clear()
                last_reset = current_time

            # Получаем IP клиента
            request = next((arg for arg in args if isinstance(arg, Request)), None)
            if request:
                client_ip = request.client.host
                current_count = request_counts.get(client_ip, 0)

                if current_count >= max_requests:
                    raise HTTPException(
                        status_code=429,
                        detail=f"Превышен лимит запросов. Максимум {max_requests} запросов в {window} секунд.",
                    )

                request_counts[client_ip] = current_count + 1

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Типы запросов/ответов
class SentimentRequest(BaseModel):
    """Запрос на анализ тональности."""

    text: str = Field(..., min_length=1, max_length=5000)
    user_id: int | None = Field(None, alias="userId")


class SentimentResponse(BaseModel):
    """Ответ с результатом анализа."""

    text: str
    sentiment: str  # 'positive' | 'negative' | 'neutral'
    confidence: float
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# Статистика сервиса
class Stats:
    """Трекер статистики запросов."""

    def __init__(self):
        self.total = 0
        self.positive = 0
        self.negative = 0
        self.neutral = 0
        self.start_time = datetime.now()

    def update(self, sentiment: str) -> None:
        """Обновляет статистику по результату."""
        self.total += 1

        match sentiment:
            case "positive":
                self.positive += 1
            case "negative":
                self.negative += 1
            case "neutral":
                self.neutral += 1

    def to_dict(self) -> Dict[str, Any]:
        """Преобразует статистику в словарь."""
        uptime = datetime.now() - self.start_time
        return {
            "total_requests": self.total,
            "positive": self.positive,
            "negative": self.negative,
            "neutral": self.neutral,
            "uptime_seconds": uptime.total_seconds(),
        }


stats = Stats()


# Управление жизненным циклом
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управляет жизненным циклом приложения."""
    logger.info("Запуск Sentiment Analysis API...")

    # Загружаем статистику из файла
    load_stats()

    try:
        analyzer = get_analyzer()
        logger.info(f"Готов к работе: {analyzer.model_name}")
    except Exception as e:
        logger.error(f"Ошибка инициализации ML: {e}")

    yield

    # Сохраняем статистику в файл
    save_stats()
    logger.info("Остановка API...")


# Создание приложения
app = FastAPI(title="Sentiment Analysis API", version="2.0.0", lifespan=lifespan)


# Эндпоинты
@app.get("/")
async def root() -> dict:
    """Корневой эндпоинт с информацией о сервисе."""
    analyzer = get_analyzer()

    return {
        "service": "Sentiment Analysis API",
        "version": "2.0.0",
        "model": analyzer.model_name,
        "endpoints": {
            "POST /predict": "Анализ тональности",
            "GET /health": "Проверка здоровья",
            "GET /stats": "Статистика",
        },
    }


@app.post("/predict", response_model=SentimentResponse)
@rate_limit(max_requests=30, window=60)  # 30 запросов в минуту
async def predict(request: SentimentRequest) -> SentimentResponse:
    """Анализирует тональность текста.

    Returns:
        Результат анализа с оценкой точности.
    """
    try:
        analyzer = get_analyzer()
        result = analyzer.analyze(request.text)

        stats.update(result["sentiment"])

        logger.info(f"Анализ для user_id={request.user_id}: {result['sentiment']}")

        return SentimentResponse(
            text=result["text"],
            sentiment=result["sentiment"],
            confidence=result["confidence"],
            timestamp=datetime.now(),
        )

    except Exception as e:
        logger.error(f"Ошибка анализа: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при анализе текста",
        )


@app.get("/health")
async def health() -> dict:
    """Проверяет работоспособность сервиса."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/stats")
async def get_stats() -> dict:
    """Возвращает статистику использования."""
    return stats.to_dict()


@app.exception_handler(Exception)
async def handle_exceptions(request, exc):
    """Обрабатывает все необработанные исключения."""
    logger.error(f"Необработанная ошибка: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Внутренняя ошибка сервера"},
    )


@app.exception_handler(429)
async def rate_limit_exception_handler(request, exc):
    """Обработчик ошибок rate limiting."""
    return JSONResponse(
        status_code=429,
        content={"detail": "Превышен лимит запросов. Попробуйте позже."},
    )
