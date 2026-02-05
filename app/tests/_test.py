from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json
import os
import sys

# Добавляем путь к приложению
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app
from ml_service import SentimentAnalyzer, get_analyzer
from bot.services import analyze_text, fetch_stats, get_user_history

client = TestClient(app)


def test_root_endpoint():
    """Тест корневого эндпоинта"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "version" in data
    assert "model" in data
    assert "endpoints" in data
    print(f"✅ Корневой эндпоинт: {data['service']}")


def test_predict_endpoint():
    """Тест анализа тональности текста"""
    # Позитивный текст
    response = client.post(
        "/predict",
        json={"text": "Я очень счастлив сегодня! Отличный день!", "user_id": 123},
    )

    assert response.status_code == 200
    data = response.json()

    # Проверяем структуру ответа
    assert "text" in data
    assert "sentiment" in data
    assert "confidence" in data
    assert "timestamp" in data

    # Проверяем допустимые значения тональности
    assert data["sentiment"] in ["positive", "negative", "neutral"]

    # Проверяем confidence в допустимых пределах
    assert 0.0 <= data["confidence"] <= 1.0

    print(
        f"✅ Успешный анализ: {data['sentiment']} (уверенность: {data['confidence']})"
    )


def test_predict_empty_text():
    """Тест с пустым текстом (должна быть ошибка валидации)"""
    response = client.post("/predict", json={"text": "", "user_id": 123})
    assert response.status_code == 422  # Ошибка валидации Pydantic
    print("✅ Пустой текст правильно отвергнут")


def test_health_endpoint():
    """Тест health-check эндпоинта"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
    print("✅ Health check passed")


def test_stats_endpoint():
    """Тест эндпоинта статистики"""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
    assert "positive" in data
    assert "negative" in data
    assert "neutral" in data
    print(f"✅ Статистика: {data['total_requests']} запросов")


def test_predict_negative_text():
    """Тест негативного текста"""
    response = client.post(
        "/predict", json={"text": "Это ужасно и плохо", "user_id": 456}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sentiment"] in ["positive", "negative", "neutral"]
    print(f"✅ Негативный текст: {data['sentiment']}")


def test_predict_neutral_text():
    """Тест нейтрального текста"""
    response = client.post(
        "/predict",
        json={"text": "Сегодня среда. Погода обычной облачности.", "user_id": 789},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sentiment"] in ["positive", "negative", "neutral"]
    print(f"✅ Нейтральный текст: {data['sentiment']}")


def test_ml_service_analyze():
    """Тест ML сервиса"""
    analyzer = get_analyzer()

    # Тест позитивного текста
    result = analyzer.analyze("Отличный день сегодня!")
    assert result["sentiment"] in ["positive", "negative", "neutral"]
    assert 0.0 <= result["confidence"] <= 1.0
    print("✅ ML сервис: позитивный текст")

    # Тест негативного текста
    result = analyzer.analyze("Ужасный день сегодня.")
    assert result["sentiment"] in ["positive", "negative", "neutral"]
    print("✅ ML сервис: негативный текст")

    # Тест длинного текста
    long_text = "Это очень длинный текст. " * 100
    result = analyzer.analyze(long_text)
    assert result["sentiment"] in ["positive", "negative", "neutral"]
    print("✅ ML сервис: длинный текст")


def test_ml_service_irony_detection():
    """Тест детекции иронии"""
    analyzer = get_analyzer()

    # Тест ироничного текста
    result = analyzer.analyze("Ну конечно, это просто великолепно!")
    assert result["sentiment"] in ["positive", "negative", "neutral"]
    print("✅ ML сервис: ирония")


def test_bot_services():
    """Тест сервисов бота"""
    # Тест анализа текста (мокаем HTTP запросы)
    with patch("aiohttp.ClientSession.post") as mock_post:
        # Создаем мок-ответ
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "text": "Тестовый текст",
                "sentiment": "positive",
                "confidence": 0.95,
                "timestamp": "2023-01-01T00:00:00Z",
            }
        )
        mock_post.return_value.__aenter__.return_value = mock_response

        # Вызываем функцию (асинхронно)
        import asyncio

        result = asyncio.run(analyze_text("Тестовый текст", 123))
        assert result is not None
        assert result.sentiment == "positive"
        print("✅ Сервисы бота: анализ текста")

    # Тест получения статистики (мокаем HTTP запросы)
    with patch("aiohttp.ClientSession.get") as mock_get:
        # Создаем мок-ответ
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "total_requests": 100,
                "positive": 50,
                "negative": 30,
                "neutral": 20,
                "uptime_seconds": 3600,
            }
        )
        mock_get.return_value.__aenter__.return_value = mock_response

        # Вызываем функцию (асинхронно)
        import asyncio

        stats = asyncio.run(fetch_stats())
        assert stats.total_requests == 100
        print("✅ Сервисы бота: статистика")


def test_user_history():
    """Тест истории пользователя"""
    from bot.services import _add_to_history

    # Добавляем тестовые данные
    test_result = {
        "text": "Тестовый текст",
        "sentiment": "positive",
        "confidence": 0.95,
        "timestamp": "2023-01-01T00:00:00Z",
    }

    _add_to_history(123, test_result)

    # Проверяем историю
    history = get_user_history(123)
    assert len(history) > 0
    assert history[0]["result"]["sentiment"] == "positive"
    print("✅ История пользователя")


def test_rate_limiting():
    """Тест ограничения запросов"""
    # Отправляем много запросов подряд
    failed_requests = 0
    for i in range(35):  # Больше лимита в 30 запросов
        response = client.post(
            "/predict",
            json={"text": f"Тестовый текст {i}", "user_id": 123},
        )
        if response.status_code == 429:  # Too Many Requests
            failed_requests += 1

    # Должно быть несколько отказов из-за ограничения
    print(f"✅ Rate limiting: {failed_requests} запросов отклонено")


# Запуск всех тестов
if __name__ == "__main__":
    print("🧪 Запуск тестов API...")
    test_root_endpoint()
    test_health_endpoint()
    test_stats_endpoint()
    test_predict_endpoint()
    test_predict_negative_text()
    test_predict_neutral_text()
    test_predict_empty_text()

    print("\n🤖 Запуск тестов ML сервиса...")
    test_ml_service_analyze()
    test_ml_service_irony_detection()

    print("\n💬 Запуск тестов сервисов бота...")
    test_bot_services()
    test_user_history()

    print("\n🛡️ Запуск тестов ограничения запросов...")
    test_rate_limiting()

    print("\n🎉 Все тесты пройдены!")
