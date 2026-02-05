import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field

# Ищем .env в корне проекта
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()


class Settings(BaseSettings):
    """Конфигурация приложения с валидацией."""

    # Токен Telegram бота
    bot_token: str = Field(..., validation_alias="BOT_TOKEN")

    # ID администратора
    admin_id: int | None = Field(None, validation_alias="ADMIN_ID")

    # Название ML модели
    ml_model_name: str = Field(
        "cointegrated/rubert-tiny-sentiment-balanced", validation_alias="ML_MODEL_NAME"
    )

    # Настройки API
    api_host: str = Field("localhost", validation_alias="API_HOST")
    api_port: int = Field(8000, validation_alias="API_PORT")
    api_reload: bool = Field(False, validation_alias="API_RELOAD")

    # Уровень логирования
    log_level: str = Field("INFO", validation_alias="LOG_LEVEL")

    # Окружение
    environment: str = Field("production", validation_alias="ENVIRONMENT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Игнорировать дополнительные поля


# Создаем экземпляр настроек
try:
    settings = Settings()
except Exception as e:
    print(f"Ошибка загрузки конфигурации: {e}")

    # Создаем настройки с минимальными параметрами
    class FallbackSettings:
        def __init__(self):
            self.bot_token = os.getenv("BOT_TOKEN", "dummy_token")
            self.admin_id = (
                int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else None
            )
            self.ml_model_name = os.getenv(
                "ML_MODEL_NAME", "cointegrated/rubert-tiny-sentiment-balanced"
            )
            self.api_host = os.getenv("API_HOST", "localhost")
            self.api_port = int(os.getenv("API_PORT", "8000"))
            self.api_reload = os.getenv("API_RELOAD", "false").lower() == "true"
            self.log_level = os.getenv("LOG_LEVEL", "INFO")
            self.environment = os.getenv("ENVIRONMENT", "production")

    settings = FallbackSettings()


def get_bot_token() -> str:
    """Получить токен бота из .env"""
    return settings.bot_token


def get_admin_id() -> int | None:
    """Получить ID администратора из .env"""
    return settings.admin_id


def get_ml_model() -> str:
    """Получить название ML модели из .env"""
    return settings.ml_model_name


def get_api_host() -> str:
    """Получить хост API"""
    return settings.api_host


def get_api_port() -> int:
    """Получить порт API"""
    return settings.api_port


def get_api_reload() -> bool:
    """Нужна ли автоперезагрузка API"""
    return settings.api_reload


def get_log_level() -> str:
    """Получить уровень логирования"""
    return settings.log_level


def get_environment() -> str:
    """Получить окружение (development/production)"""
    return settings.environment


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
