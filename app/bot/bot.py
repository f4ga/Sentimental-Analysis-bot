import asyncio
import os
import sys
import logging
import ssl

# Исправление SSL для Python 3.14
ssl._create_default_https_context = ssl._create_unverified_context
# Настройка логирования ДО всех импортов
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Добавляем путь для импорта из core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем настройки из нашего конфига
try:
    from core.config import get_bot_token, get_admin_id, get_log_level

    BOT_TOKEN = get_bot_token()
    ADMIN_ID = get_admin_id()
    ADMIN_IDS = [ADMIN_ID] if ADMIN_ID else []

    # Устанавливаем уровень логирования из конфига
    log_level = getattr(logging, get_log_level().upper(), logging.INFO)
    logging.getLogger().setLevel(log_level)

    logger.info(f"Конфиг загружен. Админы: {ADMIN_IDS}")

except ImportError as e:
    logger.error(f"Ошибка импорта конфига: {e}")
    sys.exit(1)
except ValueError as e:
    logger.error(f"Ошибка конфигурации: {e}")
    sys.exit(1)


async def main():
    """Основная функция запуска бота."""
    from aiogram import Bot, Dispatcher
    from aiogram.fsm.storage.memory import MemoryStorage
    from bot.handlers import router  # Главный роутер

    # ПРОСТО СОЗДАЕМ БОТА - aiogram сам разберется с SSL
    bot = Bot(token=BOT_TOKEN)

    # Создаем диспетчер и подключаем роутер
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    try:
        # Удаляем вебхук и запускаем поллинг
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Бот успешно запущен и готов к работе!")

        # Проверяем соединение с Telegram API
        me = await bot.get_me()
        logger.info(f"Бот авторизован как: @{me.username} (ID: {me.id})")

        # Запускаем поллинг
        await dp.start_polling(bot)

    except Exception as e:
        logger.exception(f"Критическая ошибка при работе бота: {e}")

    finally:
        # Корректно закрываем сессию
        try:
            await bot.session.close()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        # Запускаем асинхронную главную функцию
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при запуске бота: {e}")
