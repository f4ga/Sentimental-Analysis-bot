"""
Конфигурация через os.getenv()
Все значения берутся из .env файла
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ЗАГРУЗКА .env ПЕРЕД ВСЕМИ ФУНКЦИЯМИ
# Ищем .env в корне проекта (на уровень выше app/)
project_root = Path(__file__).parent.parent  # core -> app -> easy-bot
env_path = project_root / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Попробуем текущую директорию
    load_dotenv()


def get_bot_token() -> str:
    """Получить токен бота из .env"""
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN не найден в .env файле!")
    return token


def get_admin_id() -> int | None:
    """Получить ID администратора из .env"""
    admin_str = os.getenv("ADMIN_ID")
    if admin_str and admin_str.strip():
        return int(admin_str.strip())
    return None


def get_ml_model() -> str:
    """Получить название ML модели из .env"""
    model_name = os.getenv("ML_MODEL_NAME")

    # ДЕБАГ: посмотрим что получаем

    if not model_name:
        # Значение по умолчанию если не указано
        return "cointegrated/rubert-tiny-sentiment-balanced"
    return model_name


def get_api_host() -> str:
    """Получить хост API"""
    return os.getenv("API_HOST", "0.0.0.0")


def get_api_port() -> int:
    """Получить порт API"""
    return int(os.getenv("API_PORT", "8000"))


def get_api_reload() -> bool:
    """Нужна ли автоперезагрузка API"""
    return os.getenv("API_RELOAD", "false").lower() == "true"


def get_log_level() -> str:
    """Получить уровень логирования"""
    return os.getenv("LOG_LEVEL", "INFO")


def get_environment() -> str:
    """Получить окружение (development/production)"""
    return os.getenv("ENVIRONMENT", "development")


# Экспортируем функции
__all__ = [
    "get_bot_token",
    "get_admin_id",
    "get_ml_model",
    "get_api_host",
    "get_api_port",
    "get_api_reload",
    "get_log_level",
    "get_environment",
]
