from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

info_button = InlineKeyboardButton(text="ℹ️ Info", callback_data="cb_info")
donate_button = InlineKeyboardButton(text="💳 Donate", callback_data="cb_donate")
standard_search_button = InlineKeyboardButton(
    text="🔎 Новый поиск ИИН", callback_data="cb_standard_search"
)
deep_search_button = InlineKeyboardButton(
    text="⌛ Искать среди более старых ИИН", callback_data="cb_deep_search"
)


def found_standard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [deep_search_button],
            [info_button, donate_button],
            [standard_search_button],
        ]
    )


def not_found_standard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [deep_search_button],
            [info_button, donate_button],
            [standard_search_button],
        ]
    )


def found_deep() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [info_button, donate_button],
            [standard_search_button],
        ]
    )


def not_found_deep() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [info_button, donate_button],
            [standard_search_button],
        ]
    )


def info() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[donate_button, standard_search_button]])


def donate() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[info_button, standard_search_button]])
