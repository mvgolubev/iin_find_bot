from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

info_button = InlineKeyboardButton(text="ℹ️ Info", callback_data="cb_info")
donate_button = InlineKeyboardButton(text="💳 Donate", callback_data="cb_donate")
standard_search_button = InlineKeyboardButton(
    text="🔎 Новый поиск ИИН", callback_data="cb_standard_search"
)
deep_search_button = InlineKeyboardButton(
    text="⌛ Искать среди более старых ИИН", callback_data="cb_deep_search"
)
print_button = InlineKeyboardButton(text="🖨️ Распечатать ИИН", callback_data="cb_print")
pdf_begin_button = InlineKeyboardButton(
    text="📄 Найденный ИИН в PDF", callback_data="cb_pdf_start"
)
rtf_button = InlineKeyboardButton(text="📄 RTF-шаблон", callback_data="cb_rtf")
docx_button = InlineKeyboardButton(text="📄 DOCX-шаблон", callback_data="cb_docx")


def standard_search_result() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [deep_search_button],
            [info_button, print_button],
            [donate_button, standard_search_button],
        ]
    )


def deep_search_result() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [info_button, print_button],
            [donate_button, standard_search_button],
        ]
    )


def info() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[donate_button, standard_search_button]]
    )


def donate() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[info_button, standard_search_button]])


def print_iin(found_quantity: int) -> InlineKeyboardMarkup:
    if found_quantity == 0:
        return InlineKeyboardMarkup(
            inline_keyboard=[[rtf_button, docx_button], [standard_search_button]]
        )
    else:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [pdf_begin_button],
                [rtf_button, docx_button],
                [standard_search_button],
            ]
        )


def choose_iin(found_quantity: int) -> ReplyKeyboardMarkup:
    keyboard_line = [KeyboardButton(text=str(n + 1)) for n in range(found_quantity)]
    return ReplyKeyboardMarkup(
        keyboard=[keyboard_line],
        resize_keyboard=True,
        one_time_keyboard=True,
        is_persistent=True,
    )


def country() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Россия")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
