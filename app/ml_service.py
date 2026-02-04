"""
сервис анализа тональности на основе RuBERT.
"""

from dataclasses import dataclass, asdict
from typing import Literal
import logging
from transformers import pipeline

logger = logging.getLogger(__name__)
from core.config import get_ml_model


@dataclass
class SentimentResult:

    text: str
    sentiment: Literal["positive", "negative", "neutral"]
    confidence: float
    irony_detected: bool = False
    model_used: str = ""

    def as_dict(self) -> dict[str, object]:
        """Конвертирует результат в словарь для API."""
        return {
            "text": self.text,
            "sentiment": self.sentiment,
            "confidence": self.confidence,
            "irony_detected": self.irony_detected,
            "model_used": self.model_used,
        }


class SentimentAnalyzer:
    """Анализ тональности с поддержкой иронии."""

    # модель возвращает: POSITIVE, NEGATIVE, NEUTRAL
    _LABEL_MAP = {
        "POSITIVE": "positive",
        "NEGATIVE": "negative",
        "NEUTRAL": "neutral",
        "positive": "positive",
        "negative": "negative",
        "neutral": "neutral",
    }

    # Ключевые фразы для детекции иронии
    _IRONY_PHRASES = {
        "ну конечно",
        "ещё бы",
        "как же",
        "вот именно",
        "просто блестяще",
        "просто прекрасно",
        "само собой",
        "разумеется",
        "естественно",
        "что может быть лучше",
        "просто замечательно",
        "как хорошо",
    }

    def __init__(self, model_name: str | None = None):
        """Инициализация анализатора."""
        if model_name:
            self.model_name = model_name
        else:
            self.model_name = get_ml_model()

        logger.info(f"Загрузка модели: {self.model_name}")
        self._init_model()

    def _init_model(self) -> None:
        """Инициализирует пайплайн модели."""

        try:
            # Используем упрощённую инициализацию
            self.classifier = pipeline(
                task="sentiment-analysis",
                model=self.model_name,
                device=-1,  # CPU
                truncation=True,
                max_length=512,
            )
            logger.info(f"Модель {self.model_name} загружена")

        except Exception as e:
            logger.error(f" Критическая ошибка загрузки модели: {e}")
            raise RuntimeError(f"Не удалось загрузить модель {self.model_name}") from e

    def analyze(self, text: str) -> dict[str, object]:
        """Анализирует тональность текста.

        Args:
            text: Текст для анализа.

        Returns:
            Словарь с результатами анализа (для обратной совместимости).

        Raises:
            ValueError: Если текст пустой.
            RuntimeError: Если произошла ошибка анализа.
        """
        if not text or not text.strip():
            raise ValueError("Текст не может быть пустым")

        # Детекция иронии (делаем до анализа)
        irony_detected = self._detect_irony(text)

        try:
            # Анализ моделью
            result = self._analyze_with_model(text, irony_detected)
            return result.as_dict()

        except Exception as e:
            logger.error(f"Ошибка анализа: {e}")
            raise RuntimeError("Ошибка анализа тональности") from e

    def _analyze_with_model(self, text: str, irony_detected: bool) -> SentimentResult:
        """Основной анализ с помощью модели."""
        # Ограничиваем длину для эффективности
        truncated_text = text[:1000]

        # Получаем предсказание
        prediction = self.classifier(truncated_text)[0]

        # Нормализуем метку
        raw_label = prediction["label"].upper()
        sentiment = self._LABEL_MAP.get(raw_label, "neutral")
        confidence = float(prediction["score"])

        # Корректируем для иронии
        if irony_detected and sentiment == "positive":
            sentiment = "negative"
            confidence = max(0.1, confidence * 0.5)  # Сильно снижаем уверенность

        return SentimentResult(
            text=text,
            sentiment=sentiment,
            confidence=confidence,
            irony_detected=irony_detected,
            model_used=self.model_name,
        )

    def _detect_irony(self, text: str) -> bool:
        """Обнаруживает иронию в тексте."""
        text_lower = text.lower()

        # Быстрая проверка по ключевым фразам
        return any(phrase in text_lower for phrase in self._IRONY_PHRASES)


# Современный синглтон с типизацией
_analyzer: SentimentAnalyzer | None = None


def get_analyzer() -> SentimentAnalyzer:
    """Возвращает или создаёт экземпляр анализатора."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer


def set_analyzer(model_name: str) -> SentimentAnalyzer:
    """Устанавливает новую модель анализатора.

    Returns:
        Новый экземпляр анализатора.
    """
    global _analyzer
    _analyzer = SentimentAnalyzer(model_name)
    return _analyzer


# Новая асинхронная версия с типизацией
async def analyze_async_result(text: str) -> SentimentResult:
    """Асинхронный анализ тональности с возвратом типизированного результата."""
    analyzer = get_analyzer()
    return analyzer._analyze_with_model(text, analyzer._detect_irony(text))
