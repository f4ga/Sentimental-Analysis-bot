"""
сервис анализа тональности на основе RuBERT.
"""

from dataclasses import dataclass, asdict
from typing import Literal, Dict, List
import logging
from functools import lru_cache
import hashlib
import json

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

        self.classifier = None
        logger.info(f"Загрузка модели: {self.model_name}")

    def _init_model(self) -> None:
        """Ленивая инициализация пайплайна модели."""
        if self.classifier is not None:
            return

        try:
            logger.info(f"Загрузка модели: {self.model_name}")
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

        # Проверяем кэш
        cache_key = self._get_cache_key(text)
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            logger.info("Результат найден в кэше")
            return cached_result

        # Детекция иронии (делаем до анализа)
        irony_detected = self._detect_irony(text)

        try:
            # Анализ моделью
            result = self._analyze_with_model(text, irony_detected)
            result_dict = result.as_dict()

            # Сохраняем в кэш
            self._save_to_cache(cache_key, result_dict)

            return result_dict
        except Exception as e:
            logger.error(f"Ошибка анализа: {e}")
            raise RuntimeError("Ошибка анализа тональности") from e

    def _analyze_with_model(self, text: str, irony_detected: bool) -> SentimentResult:
        """Основной анализ с помощью модели."""
        # Ленивая инициализация модели
        self._init_model()

        # Для очень длинных текстов разбиваем на части
        if len(text) > 2000:
            return self._analyze_long_text(text, irony_detected)

        # Получаем предсказание
        prediction = self.classifier(text)[0]

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

    def _analyze_long_text(self, text: str, irony_detected: bool) -> SentimentResult:
        """Анализ длинных текстов путем разбиения на части."""
        # Разбиваем текст на части по предложениям
        sentences = self._split_sentences(text)

        # Анализируем каждую часть
        results = []
        for sentence in sentences:
            if len(sentence.strip()) > 0:
                try:
                    prediction = self.classifier(sentence[:1000])[0]
                    results.append(
                        {"label": prediction["label"], "score": prediction["score"]}
                    )
                except Exception as e:
                    logger.warning(f"Ошибка анализа части текста: {e}")
                    continue

        if not results:
            return SentimentResult(
                text=text,
                sentiment="neutral",
                confidence=0.5,
                irony_detected=irony_detected,
                model_used=self.model_name,
            )

        # Агрегируем результаты
        total_score = sum(r["score"] for r in results)
        avg_confidence = total_score / len(results)

        # Определяем доминирующую тональность
        positive_count = sum(1 for r in results if "POSITIVE" in r["label"].upper())
        negative_count = sum(1 for r in results if "NEGATIVE" in r["label"].upper())
        neutral_count = len(results) - positive_count - negative_count

        if positive_count > negative_count and positive_count > neutral_count:
            sentiment = "positive"
        elif negative_count > positive_count and negative_count > neutral_count:
            sentiment = "negative"
        else:
            sentiment = "neutral"

        return SentimentResult(
            text=text,
            sentiment=sentiment,
            confidence=avg_confidence,
            irony_detected=irony_detected,
            model_used=self.model_name,
        )

    def _split_sentences(self, text: str) -> List[str]:
        """Простое разбиение текста на предложения."""
        # Разбиваем по точкам, восклицательным и вопросительным знакам
        sentences = []
        current_sentence = ""

        for char in text:
            current_sentence += char
            if char in ".!?":
                sentences.append(current_sentence.strip())
                current_sentence = ""

        # Добавляем остаток
        if current_sentence.strip():
            sentences.append(current_sentence.strip())

        return sentences

    def _detect_irony(self, text: str) -> bool:
        """Обнаруживает иронию в тексте."""
        text_lower = text.lower()

        # Быстрая проверка по ключевым фразам
        return any(phrase in text_lower for phrase in self._IRONY_PHRASES)

    def _get_cache_key(self, text: str) -> str:
        """Генерирует ключ для кэширования."""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _get_from_cache(self, key: str) -> dict | None:
        """Получает результат из кэша."""
        # В реальной реализации здесь будет кэш
        return None

    def _save_to_cache(self, key: str, result: dict) -> None:
        """Сохраняет результат в кэш."""
        # В реальной реализации здесь будет кэш
        pass


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
