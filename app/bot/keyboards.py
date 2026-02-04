from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Основная клавиатура для главного меню."""

    buttons = [
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="🚨 Помощь", callback_data="help"),
        ],
        [
            InlineKeyboardButton(text="🔍 Анализ", callback_data="more_analysis"),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_sentiment_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после анализа текста."""

    buttons = [
        [
            InlineKeyboardButton(text="🔍 Анализ", callback_data="more_analysis"),
            InlineKeyboardButton(text="📋 История", callback_data="history"),
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_yes_no_keyboard() -> InlineKeyboardMarkup:
    """Простая клавиатура Да/Нет."""

    buttons = [
        [
            InlineKeyboardButton(text="Да", callback_data="yes"),
            InlineKeyboardButton(text="Нет", callback_data="no"),
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_reply_keyboard() -> ReplyKeyboardMarkup:
    """Reply-клавиатура для быстрого доступа."""

    buttons = [
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="🚨 Помощь")],
        [
            KeyboardButton(text="🔍 Анализ"),
        ],
    ]

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=False,
    )


# # Клавиатура для выбора языка (пример использования t-строк)
# def get_language_keyboard() -> InlineKeyboardMarkup:
#     """Клавиатура для выбора языка анализа."""

#     # В реальном проекте здесь можно использовать t-строки для локализации
#     buttons = [
#         [
#             InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
#             InlineKeyboardButton(text="🇺🇸 English", callback_data="lang_en"),
#         ],
#         [
#             InlineKeyboardButton(text="🇩🇪 Deutsch", callback_data="lang_de"),
#             InlineKeyboardButton(text="🇫🇷 Français", callback_data="lang_fr"),
#         ],
#     ]

#     return InlineKeyboardMarkup(inline_keyboard=buttons)
