from aiogram import Router, F, types
from bot.services import fetch_stats
from bot.keyboards import get_main_keyboard
import logging
from .start import help_text

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "stats")
async def show_stats(callback: types.CallbackQuery) -> None:
    """Показать статистику использования."""

    await callback.answer("⏳ Загружаю статистику...")

    try:
        stats = await fetch_stats()

        # Форматирование статистики
        stats_template = """
📊 <b>Статистика использования:</b>

• Всего запросов: {total}
• Успешных: {successful}
• Ошибок: {errors}

<b>тональности запросов:</b>
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
    """Показать историю запросов (заглушка)."""

    # В реальном проекте здесь была бы работа с БД
    await callback.message.answer(
        "📋 <b>История запросов</b>\n\n"
        "В этой версии истории запросов нет. \n"
        "Скоро разработчик добавит базу данных!\n\n"
        "Используйте команду для статистики /stats , \n"
        "(пока работает только в текущей сессии).",
        parse_mode="HTML",
    )
    await callback.answer()


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
