"""
FastAPI сервис для анализа тональности.
"""

from contextlib import asynccontextmanager
from datetime import datetime
import logging

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ConfigDict

from ml_service import get_analyzer

logger = logging.getLogger(__name__)


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


# Инициализация
stats = Stats()


# Управление жизненным циклом
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управляет жизненным циклом приложения."""
    # Startup
    logger.info("Запуск Sentiment Analysis API...")
    try:
        analyzer = get_analyzer()
        logger.info(f"Готов к работе: {analyzer.model_name}")
    except Exception as e:
        logger.error(f"Ошибка инициализации ML: {e}")

    yield

    # Shutdown
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
async def predict(request: SentimentRequest) -> SentimentResponse:
    """Анализирует тональность текста.

    Returns:
        Результат анализа с оценкой уверенности.
    """
    try:
        # Анализ текста
        analyzer = get_analyzer()
        result = analyzer.analyze(request.text)

        # Обновление статистики
        stats.update(result["sentiment"])

        # Логирование
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
    uptime = datetime.now() - stats.start_time

    return {
        "total_requests": stats.total,
        "positive": stats.positive,
        "negative": stats.negative,
        "neutral": stats.neutral,
        "uptime_seconds": uptime.total_seconds(),
    }


# Глобальный обработчик ошибок
@app.exception_handler(Exception)
async def handle_exceptions(request, exc):
    """Обрабатывает все необработанные исключения."""
    logger.error(f"Необработанная ошибка: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Внутренняя ошибка сервера"},
    )
