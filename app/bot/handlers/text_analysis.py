from aiogram import Router, F, types
from bot.services import analyze_text
from bot.keyboards import get_sentiment_keyboard
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text)
async def handle_text(message: types.Message) -> None:
    """Обработка текстовых сообщений для анализа тональности."""

    text = message.text.strip()

    # Проверка на пустой текст
    if not text:
        await message.answer("📝 Пожалуйста, отправьте текст для анализа.")
        return

    # Проверка длины текста
    if len(text) < 3:
        await message.answer(
            "📏 Слишком короткий текст. Отправьте не менее 3 символов."
        )
        return

    if len(text) > 1000:
        await message.answer("📏 Текст слишком длинный. Максимум 1000 символов.")
        return

    try:
        status_msg = await message.answer(
            "🔍 Анализирую текст..."
        )  # Статусное сообщение, потом удаляем

        # Анализ текста
        result = await analyze_text(text, message.from_user.id)

        # ответ
        sentiment_emojis = {
            "positive": "☀️ Позитивная",
            "negative": "⛈️ Негативная",
            "neutral": "☁️ Нейтральная",
        }

        sentiment_display = sentiment_emojis.get(
            result.sentiment, f"⚪ {result.sentiment.title()}"
        )

        response = (
            f"🎭 <b>Результат анализа:</b>\n\n"
            f"💬 <b>Ваш текст:</b>\n<code>{text[:100]}{'...' if len(text) > 200 else ''}</code>\n\n"
            f"📊 <b>Тональность:</b> {sentiment_display}\n"
            f"🎯 <b>Точность:</b> {result.confidence:.1%}\n\n"
        )

        # Статусное сообщение удаляется и отправляем ответ
        await status_msg.delete()
        await message.answer(
            response, reply_markup=get_sentiment_keyboard(), parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при анализе текста: {e}", exc_info=True)

        # статусное сообщение удаляется при ошибке
        if "status_msg" in locals():
            try:
                await status_msg.delete()
            except:
                pass

        await message.answer(
            "❌ <b>Произошла ошибка при анализе текста</b>\n\n"
            "Возможные причины:\n"
            "• Сервис временно недоступен\n"
            "• Проблемы с сетью\n"
            "• Технические работы\n\n"
            "Попробуйте еще раз через несколько минут.",
            parse_mode="HTML",
        )
