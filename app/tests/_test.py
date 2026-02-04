from fastapi.testclient import TestClient
from main import app
import json

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


# Запуск всех тестов
if __name__ == "__main__":
    print("🧪 Запуск тестов API...")
    test_root_endpoint()
    test_health_endpoint()
    test_stats_endpoint()
    test_predict_endpoint()
    test_predict_negative_text()
    test_predict_empty_text()
    print("\n🎉 Все тесты пройдены!")
