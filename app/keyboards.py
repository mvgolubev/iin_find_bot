from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

info_button = InlineKeyboardButton(text="ℹ️ Info", callback_data="cb_info")
donate_button = InlineKeyboardButton(text="💳 Donate", callback_data="cb_donate")
new_search_button = InlineKeyboardButton(
    text="🔎 Новый поиск ИИН", callback_data="cb_new_search"
)
old_search_button = InlineKeyboardButton(
    text="⌛ Искать среди более старых ИИН", callback_data="cb_old_search"
)


def found_new() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [old_search_button],
            [info_button, donate_button],
            [new_search_button],
        ]
    )


def not_found_new() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [old_search_button],
            [info_button, donate_button],
            [new_search_button],
        ]
    )


def found_old() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [info_button, donate_button],
            [new_search_button],
        ]
    )


def not_found_old() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [info_button, donate_button],
            [new_search_button],
        ]
    )


def info() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[donate_button, new_search_button]])


def donate() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[info_button, new_search_button]])
