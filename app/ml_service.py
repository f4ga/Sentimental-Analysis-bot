"""
Сервис анализа тональности текста на основе RuBERT.

Данный модуль предоставляет функциональность для анализа эмоциональной
окраски текста с использованием предобученной модели RuBERT. Включает
в себя поддержку определения иронии и кэширования результатов.
"""

from dataclasses import dataclass
from typing import Literal, List
import logging
import hashlib
import threading

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
    """Анализатор тональности текста с поддержкой определения иронии.

    Использует предобученную модель RuBERT для анализа эмоциональной
    окраски текста. Включает функциональность для определения иронии
    и кэширования результатов анализа.
    """

    # модель возвращает: POSITIVE, NEGATIVE, NEUTRAL
    _LABEL_MAP = {
        "POSITIVE": "positive",
        "NEGATIVE": "negative",
        "NEUTRAL": "neutral",
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
        "ну ты и молодец",
        "спасибо, конечно",
        "ну да, ну да",
        "",
    }

    def __init__(self, model_name: str | None = None):
        """Инициализирует анализатор тональности.

        Args:
            model_name (str, optional): Название модели для анализа тональности.
                                         Если не указано, используется модель по умолчанию.
        """
        if model_name:
            self.model_name = model_name
        else:
            self.model_name = get_ml_model()

        self.classifier = None
        logger.info(f"Загрузка модели: {self.model_name}")

        # Инициализация кэша
        self._cache = {}
        self._cache_lock = threading.Lock()

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

        Выполняет анализ эмоциональной окраски текста с использованием
        предобученной модели. Включает определение иронии и кэширование
        результатов для повышения производительности.

        Args:
            text (str): Текст для анализа тональности. Не должен быть пустым.

        Returns:
            dict[str, object]: Словарь с результатами анализа, содержащий:
                - text (str): Исходный текст
                - sentiment (str): Тональность ("positive", "negative", "neutral")
                - confidence (float): Уверенность в результате (0.0 - 1.0)
                - irony_detected (bool): Была ли обнаружена ирония
                - model_used (str): Использованная модель

        Raises:
            ValueError: Если текст пустой или состоит только из пробелов.
            RuntimeError: Если произошла ошибка во время анализа модели.
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
        """Основной анализ текста с помощью модели.

        Выполняет анализ тональности текста с использованием предобученной
        модели. Для длинных текстов (>2000 символов) использует специальный
        метод анализа частями.

        Args:
            text (str): Текст для анализа.
            irony_detected (bool): Флаг обнаруженной иронии.

        Returns:
            SentimentResult: Результат анализа тональности.
        """
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
        """Анализ длинных текстов путем разбиения на части.

        Для текстов длиннее 2000 символов разбивает текст на предложения
        и анализирует каждую часть отдельно, затем агрегирует результаты.

        Args:
            text (str): Длинный текст для анализа.
            irony_detected (bool): Флаг обнаруженной иронии.

        Returns:
            SentimentResult: Агрегированный результат анализа.
        """
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
        """Простое разбиение текста на предложения.

        Разбивает текст на предложения по точкам, восклицательным
        и вопросительным знакам.

        Args:
            text (str): Текст для разбиения.

        Returns:
            List[str]: Список предложений.
        """
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
        return any(phrase in text_lower for phrase in self._IRONY_PHRASES)

    def _get_cache_key(self, text: str) -> str:
        """Генерирует ключ для кэширования.

        Использует MD5 хэш от текста для создания уникального ключа.

        Args:
            text (str): Текст для генерации ключа.

        Returns:
            str: Уникальный ключ для кэширования.
        """
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _get_from_cache(self, cache_key: str) -> dict | None:
        """Получает результат из кэша по ключу."""
        with self._cache_lock:
            return self._cache.get(cache_key)

    def _save_to_cache(self, cache_key: str, result: dict) -> None:
        """Сохраняет результат в кэш."""
        with self._cache_lock:
            # Ограничиваем размер кэша
            if len(self._cache) >= 1000:
                # Удаляем самый старый элемент
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
            self._cache[cache_key] = result


_analyzer: SentimentAnalyzer | None = None


def get_analyzer() -> SentimentAnalyzer:
    """Возвращает или создаёт экземпляр анализатора.

    Использует singleton паттерн для обеспечения единственного
    экземпляра анализатора во всем приложении.

    Returns:
        SentimentAnalyzer: Экземпляр анализатора тональности.
    """
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer


def set_analyzer(model_name: str) -> SentimentAnalyzer:
    """Устанавливает новую модель анализатора.

    Создает новый экземпляр анализатора с указанной моделью
    и заменяет текущий singleton экземпляр.

    Args:
        model_name (str): Название новой модели для анализа тональности.

    Returns:
        SentimentAnalyzer: Новый экземпляр анализатора.
    """
    global _analyzer
    _analyzer = SentimentAnalyzer(model_name)
    return _analyzer


async def analyze_async_result(text: str) -> SentimentResult:
    """Анализ тональности с возвратом типизированного результата.

    Асинхронная функция для анализа тональности текста с возвратом
    результата в виде типизированного объекта SentimentResult.

    Args:
        text (str): Текст для анализа тональности.

    Returns:
        SentimentResult: Результат анализа тональности.
    """
    analyzer = get_analyzer()
    return analyzer._analyze_with_model(text, analyzer._detect_irony(text))
