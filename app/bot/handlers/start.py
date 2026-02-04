"""
Обработчики команд бота.
"""

from aiogram import Router, types
from aiogram.filters import Command
from bot.keyboards import get_main_keyboard
import sys
import os

# Добавляем путь для импорта из core
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# Импортируем настройки
try:
    from core.config import get_admin_id, get_api_host, get_api_port

    ADMIN_ID = get_admin_id()
    ADMIN_IDS = [ADMIN_ID] if ADMIN_ID else []
    API_HOST = get_api_host()
    API_PORT = get_api_port()
    API_BASE = f"http://{API_HOST}:{API_PORT}"
except ImportError:
    ADMIN_IDS = []
    API_BASE = "http://127.0.0.1:8000"

router = Router()

help_text = (
    "<b>📋 Инструкция:</b>\n\n"
    "1. Отправь мне текст от 3 до 1000 символов\n"
    "2. Я проанализирую его тональность\n"
    "3. Покажу результат с точночстью по моим метрикам!\n\n"
    "<i>Примеры текста:</i>\n"
    "• <code>Сегодня отличная погода!</code>\n"
    "• <code>Я себя чувствую плохо весь день.</code>\n"
    "• <code>В принципе всё могло быть и лучше</code>\n\n"
    "<b>🆘 Помощь по командам:</b>\n\n"
    "<b>Основные команды:</b>\n"
    "• /start - начать работу с ботом\n"
    "• /help - показать эту справку\n"
    "• /stats - статистика тональности запросов\n"
    "<b>Анализ текста:</b>\n"
    "Пришли мне текст, отрывок из книги, отзыв или личное сообщение и я определю его тональность:\n"
    "☀️ Позитивная\n"
    "⛈️ Негативная\n"
    "☁️ Нейтральная\n\n"
    "‼️В данный момент статистика запросов появляется только для одной сессии в боте\n"
    "<b>P.s:</b> Если вы удалите историю то статистика обнулится, \n"
    "разработчик потом добавит базу данных!⚡️\n"
    "<b>Используйте кнопки</b> для быстрого доступа."
)


@router.message(Command("start"))
async def cmd_start(message: types.Message) -> None:
    """Обработчик команды /start."""

    # Проверяем админа
    is_admin = message.from_user.id in ADMIN_IDS if ADMIN_IDS else False

    # Приветствие с учетом прав
    greeting = f"Добро пожаловать, {message.from_user.first_name or 'друг'}! Я бот для анализа тональности текста."

    if is_admin:
        greeting += "\n\nВы администратор!"

    await message.answer(greeting, reply_markup=get_main_keyboard(), parse_mode="HTML")

    # Дополнительное сообщение с инструкцией

    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    """Обработчик команды /help."""
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("about"))
async def cmd_about(message: types.Message):
    await message.answer("Этот бот создан f4lga для портфолио!")
