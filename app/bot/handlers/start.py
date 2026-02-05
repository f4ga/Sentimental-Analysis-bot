from venv import logger
from aiogram import Router, types
from aiogram.filters import Command
from bot.keyboards import get_main_keyboard
import sys
import os

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

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
    "3. Покажу результат с точностью по моим метрикам!\n\n"
    "<b>Используйте кнопки</b> для быстрого доступа.\n\n"
    "<i>Примеры текста:</i>\n"
    "• <code>Сегодня отличная погода!</code>\n"
    "• <code>Я себя чувствую плохо весь день.</code>\n"
    "• <code>В принципе всё могло быть и лучше</code>\n\n"
    "<b>🚨 Помощь по командам:</b>\n\n"
    "<b>Основные команды:</b>\n"
    "• /start - начать работу с ботом\n"
    "• /help - показать эту справку\n"
    "• /stats - статистика тональности запросов\n"
    "• /history - последние 10 запросов\n"
    "• /about - автор \n"
    "<b>Анализ текста:</b>\n"
    "Пришли мне текст, отрывок из книги, отзыв или личное сообщение и я определю его тональность:\n"
    "☀️ Позитивная\n"
    "⛈️ Негативная\n"
    "☁️ Нейтральная\n\n"
    "Ответ с уровенем точности от 30-65% может показаться неправильным, бот отличает ироничные или противоречащие выражения и высчитывает с их учетом\n\n"
    "‼️В данный момент ваша история и статистика могут в любой момент исчезнуть и потом снова появится, прошу не беспокоится \n\n"
    "<b>P.s:</b> Разработчик очень старается, чтобы решить эту проблему(добавить потом бд) и скоро будут кнопочки верно или неверно :) ⚡️\n"
)


@router.message(Command("start"))
async def cmd_start(message: types.Message) -> None:

    # Проверяем админа
    is_admin = message.from_user.id in ADMIN_IDS if ADMIN_IDS else False

    greeting = f"Добро пожаловать, {message.from_user.first_name or 'друг'}! Я бот для анализа тональности текста."

    if is_admin:
        greeting += "\n\nВы администратор!"

    await message.answer(greeting, reply_markup=get_main_keyboard(), parse_mode="HTML")

    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: types.Message) -> None:
    await message.answer(help_text, parse_mode="HTML")


@router.message(Command("history"))
async def cmd_history(message: types.Message) -> None:
    """Команда для получения истории запросов пользователя."""
    from bot.services import get_user_history

    user_id = message.from_user.id

    try:
        # Получаем историю пользователя
        history = get_user_history(user_id)

        if not history:
            await message.answer(
                "📋 <b>История запросов</b>\n\n"
                "У вас пока нет истории запросов.\n"
                "Отправьте текст для анализа, чтобы начать.",
                parse_mode="HTML",
            )
            return

        # Форматируем историю
        history_text = "📋 <b>История ваших запросов:</b>\n\n"

        # Отображаем последние 10 запросов
        for i, record in enumerate(reversed(history[-10:]), 1):
            result = record["result"]
            timestamp = record["timestamp"][:19].replace("T", " ")

            # Определяем эмодзи для тональности
            sentiment_emojis = {
                "positive": "☀️",
                "negative": "⛈️",
                "neutral": "☁️",
            }
            emoji = sentiment_emojis.get(result["sentiment"], "⚪")

            # Сокращаем текст для отображения
            display_text = (
                result["text"][:50] + "..."
                if len(result["text"]) > 50
                else result["text"]
            )

            history_text += f"{i}. {emoji} {display_text}\n"
            history_text += (
                f"   Уверенность: {result['confidence']:.1%} | {timestamp}\n\n"
            )

        history_text += "<i>Показаны последние 10 запросов</i>"

        await message.answer(history_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка при получении истории: {e}")
        await message.answer(
            " <b>Не удалось загрузить историю запросов</b>\n" "Попробуйте позже.",
            parse_mode="HTML",
        )


@router.message(Command("stats"))
async def cmd_stats(message: types.Message) -> None:
    """Команда для получения статистики использования."""
    from bot.services import fetch_stats

    try:
        stats = await fetch_stats()

        # Форматирование статистики
        stats_template = """
📊 <b>Статистика использования:</b>

• Всего запросов: {total}
• Успешных: {successful}
• Ошибок: {errors}

<b>Тональности запросов:</b>
☀️ Позитивных: {positive} ({positive_percent:.1%})
⛈️ Негативных: {negative} ({negative_percent:.1%})
☁️ Нейтральных: {neutral} ({neutral_percent:.1%})

<i>Данные обновляются в реальном времени.</i>
"""
        total = stats.total_requests
        successful = stats.positive + stats.negative + stats.neutral
        errors = total - successful if total >= successful else 0

        # Избегаем деления на ноль
        total_nonzero = total if total > 0 else 1

        response_text = stats_template.format(
            total=total,
            successful=successful,
            errors=errors,
            positive=stats.positive,
            positive_percent=stats.positive / total_nonzero,
            negative=stats.negative,
            negative_percent=stats.negative / total_nonzero,
            neutral=stats.neutral,
            neutral_percent=stats.neutral / total_nonzero,
        )

        await message.answer(response_text, parse_mode="HTML")

    except Exception as e:
        from logging import getLogger

        logger = getLogger(__name__)
        logger.error(f"Ошибка при получении статистики: {e}")
        await message.answer(
            " <b>Не удалось загрузить статистику</b>\n"
            "API статистики временно недоступен.",
            parse_mode="HTML",
        )


@router.message(Command("about"))
async def cmd_about(message: types.Message) -> None:
    await message.answer("Этот бот создан @ebbsy")
