from aiogram import Router, F, types
from bot.services import fetch_user_stats, get_user_history
import logging
from .start import help_text

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "stats")
async def show_stats(callback: types.CallbackQuery) -> None:
    """Показать статистику использования."""

    await callback.answer("⏳ Загружаю статистику...")

    user_id = callback.from_user.id

    try:
        stats = await fetch_user_stats(user_id)

        # Форматирование статистики
        stats_template = """
📊 <b>Ваша статистика использования:</b>

• Всего запросов: {total}
• Успешных: {successful}
• Ошибок: {errors}

<b>Тональности ваших запросов:</b>
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
            positive_percent=stats.positive / total_nonzero if total_nonzero > 0 else 0,
            negative=stats.negative,
            negative_percent=stats.negative / total_nonzero if total_nonzero > 0 else 0,
            neutral=stats.neutral,
            neutral_percent=stats.neutral / total_nonzero if total_nonzero > 0 else 0,
        )

        await callback.message.answer(response_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await callback.message.answer(
            " <b>Не удалось загрузить статистику</b>\n"
            "API статистики временно недоступен.",
            parse_mode="HTML",
        )


@router.callback_query(F.data == "help")
async def show_help(callback: types.CallbackQuery) -> None:
    """Показать справку."""

    await callback.message.answer(help_text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "more_analysis")
async def more_analysis(callback: types.CallbackQuery) -> None:
    """Запрос нового анализа."""

    await callback.message.answer(
        "📝 <b>Отправьте следующий текст для анализа</b>\n\n"
        "<i>Можно анализировать:</i>\n"
        "• Отрывки из книг\n"
        "• Отзывы \n"
        "• Новостные заголовки\n"
        "• Личные сообщения",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "history")
async def show_history(callback: types.CallbackQuery) -> None:
    """Показать историю запросов пользователя."""

    user_id = callback.from_user.id
    await callback.answer("⏳ Загружаю историю запросов...")

    try:
        # Получаем историю пользователя
        history = get_user_history(user_id)

        if not history:
            await callback.message.answer(
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

        await callback.message.answer(history_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Ошибка при получении истории: {e}")
        await callback.message.answer(
            "❌ <b>Не удалось загрузить историю запросов</b>\n" "Попробуйте позже.",
            parse_mode="HTML",
        )


@router.callback_query(F.data == "settings")
async def show_settings(callback: types.CallbackQuery) -> None:
    """Настройки бота."""
    await callback.answer("Настройки пока не реализованы")


@router.callback_query(F.data == "yes")
async def confirm_analysis(callback: types.CallbackQuery) -> None:
    """Подтверждение анализа."""

    await callback.message.answer("Отправьте текст для анализа.", parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "no")
async def cancel_analysis(callback: types.CallbackQuery) -> None:
    """Отмена анализа."""

    await callback.message.answer(
        "❌ <b>Анализ отменен.</b>\n" "Вы можете начать новый анализ в любое время.",
        parse_mode="HTML",
    )
    await callback.answer()
