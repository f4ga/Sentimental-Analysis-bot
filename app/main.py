"""
FastAPI сервис для анализа тональности текста.

Предоставляет REST API для анализа эмоциональной окраски текста
с использованием машинного обучения. Включает функциональность
для отслеживания статистики и ограничения частоты запросов.
"""

from contextlib import asynccontextmanager
from datetime import datetime
import logging
import json
import os
from typing import Dict, Any
from functools import wraps
import time
from collections import defaultdict

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


# Хранилище для пользовательской статистики
user_stats: Dict[int, Dict[str, Any]] = defaultdict(
    lambda: {
        "total": 0,
        "positive": 0,
        "negative": 0,
        "neutral": 0,
        "start_time": datetime.now().isoformat(),
    }
)


# Загрузка статистики из файла
def load_stats():
    """Загружает статистику из файла при запуске."""
    global user_stats
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

                # Загрузка пользовательской статистики
                if "users" in data:
                    for user_id, user_data in data["users"].items():
                        user_stats[int(user_id)] = {
                            "total": user_data.get("total", 0),
                            "positive": user_data.get("positive", 0),
                            "negative": user_data.get("negative", 0),
                            "neutral": user_data.get("neutral", 0),
                            "start_time": user_data.get(
                                "start_time", datetime.now().isoformat()
                            ),
                        }

            logger.info("Статистика загружена из файла")
    except Exception as e:
        logger.error(f"Ошибка загрузки статистики: {e}")


# Сохранение статистики в файл
def save_stats():
    """Сохраняет статистику в файл при завершении работы."""
    try:
        # Подготовка данных для сохранения (только пользовательская статистика)
        data = {"users": {}}

        # Добавляем пользовательскую статистику
        for user_id, user_data in user_stats.items():
            data["users"][str(user_id)] = {
                "total": user_data["total"],
                "positive": user_data["positive"],
                "negative": user_data["negative"],
                "neutral": user_data["neutral"],
                "start_time": user_data["start_time"],
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
    """Запрос на анализ тональности текста.

    Модель данных для запроса анализа тональности, включает
    текст для анализа и идентификатор пользователя.
    """

    text: str = Field(..., min_length=1, max_length=5000)
    user_id: int | None = Field(None, alias="userId")


class SentimentResponse(BaseModel):
    """Ответ с результатом анализа тональности.

    Модель данных для ответа с результатами анализа тональности текста.
    """

    text: str
    sentiment: str  # 'positive' | 'negative' | 'neutral'
    confidence: float
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


# Управление жизненным циклом
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управляет жизненным циклом приложения.

    Выполняет инициализацию при запуске и финализацию при остановке
    приложения. Включает загрузку статистики и инициализацию ML-модели.
    """
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
    """Корневой эндпоинт с информацией о сервисе.

    Возвращает базовую информацию о сервисе, включая версию,
    используемую модель и доступные эндпоинты.

    Returns:
        dict: Информация о сервисе.
    """
    analyzer = get_analyzer()

    return {
        "service": "Sentiment Analysis API",
        "version": "2.0.0",
        "model": analyzer.model_name,
        "endpoints": {
            "POST /predict": "Анализ тональности",
            "GET /health": "Проверка здоровья",
            "GET /stats/{user_id}": "Статистика пользователя",
        },
    }


@app.post("/predict", response_model=SentimentResponse)
@rate_limit(max_requests=30, window=60)  # 30 запросов в минуту
async def predict(request: SentimentRequest) -> SentimentResponse:
    """Анализирует тональность текста.

    Принимает текст для анализа тональности и возвращает результат
    с оценкой точности. Включает ограничение частоты запросов.

    Args:
        request (SentimentRequest): Запрос с текстом для анализа.

    Returns:
        SentimentResponse: Результат анализа с оценкой точности.

    Raises:
        HTTPException: При ошибке анализа текста.
    """
    try:
        analyzer = get_analyzer()
        result = analyzer.analyze(request.text)

        # Обновляем пользовательскую статистику, если указан user_id
        if request.user_id is not None:
            user_stats[request.user_id]["total"] += 1
            match result["sentiment"]:
                case "positive":
                    user_stats[request.user_id]["positive"] += 1
                case "negative":
                    user_stats[request.user_id]["negative"] += 1
                case "neutral":
                    user_stats[request.user_id]["neutral"] += 1

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
    """Проверяет работоспособность сервиса.

    Возвращает статус сервиса и временную метку для мониторинга.

    Returns:
        dict: Статус сервиса и временная метка.
    """
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/stats/{user_id}")
async def get_user_stats(user_id: int) -> dict:
    """Возвращает статистику использования для конкретного пользователя.

    Собирает и возвращает статистику использования сервиса
    для указанного пользователя, включая количество запросов
    и распределение по тональностям.

    Args:
        user_id (int): Идентификатор пользователя.

    Returns:
        dict: Статистика использования для пользователя.
    """
    user_stat = user_stats.get(
        user_id,
        {
            "total": 0,
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "start_time": datetime.now().isoformat(),
        },
    )

    # Вычисляем uptime
    start_time = datetime.fromisoformat(user_stat["start_time"])
    uptime = datetime.now() - start_time

    return {
        "total_requests": user_stat["total"],
        "positive": user_stat["positive"],
        "negative": user_stat["negative"],
        "neutral": user_stat["neutral"],
        "uptime_seconds": uptime.total_seconds(),
    }


@app.exception_handler(Exception)
async def handle_exceptions(request, exc):
    """Обрабатывает все необработанные исключения.

    Перехватывает все необработанные исключения и возвращает
    стандартный ответ об ошибке.

    Args:
        request: Объект запроса.
        exc: Объект исключения.

    Returns:
        JSONResponse: Стандартный ответ об ошибке.
    """
    logger.error(f"Необработанная ошибка: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Внутренняя ошибка сервера"},
    )


@app.exception_handler(429)
async def rate_limit_exception_handler(request, exc):
    """Обработчик ошибок rate limiting.

    Перехватывает ошибки превышения лимита запросов и возвращает
    соответствующий ответ.

    Args:
        request: Объект запроса.
        exc: Объект исключения.

    Returns:
        JSONResponse: Ответ о превышении лимита запросов.
    """
    return JSONResponse(
        status_code=429,
        content={"detail": "Превышен лимит запросов. Попробуйте позже."},
    )
