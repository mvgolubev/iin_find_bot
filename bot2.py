import asyncio
from datetime import date
from os import getenv, path

from dotenv import load_dotenv
from telebot import TeleBot
from telebot.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReactionTypeEmoji,
)

from app import constants, utils

if path.isfile(".env"):
    load_dotenv()
    bot = TeleBot(token=getenv("API_TOKEN"), parse_mode="HTML")
else:
    print(
        "Файл .env не найден!\n"
        '1. Создайте файл с именем ".env" рядом с файлом "bot2.py"\n'
        '2. В файл ".env" добавьте строку:\n'
        'API_TOKEN = "telegram_bot_token"\n'
        "где telegram_bot_token - это токен для вашего телеграм-бота, полученный от @BotFather"
    )


@bot.message_handler(commands=["start"])
def start_handler(message: Message) -> None:
    bot.send_message(
        message.chat.id, text=f"🔎 <b>Поиск ИИН</b>\n\n{constants.DATE_REQUEST}"
    )
    bot.register_next_step_handler(message, date_handler)


@bot.message_handler()
def default_handler(message: Message) -> None:
    bot.set_message_reaction(
        message.chat.id, message.id, reaction=[ReactionTypeEmoji("🤷‍♂️")]
    )
    bot.send_message(message.chat.id, text="Чтобы начать, отправьте: /start")


def date_handler(message: Message) -> None:
    if message.content_type == "text":
        try:
            birth_date = date.fromisoformat(message.text)
        except ValueError as date_error:
            bot.set_message_reaction(
                message.chat.id, message.id, reaction=[ReactionTypeEmoji("👎")]
            )
            bot.reply_to(message, text=f"⚠️ Дата указана некорректно\n({date_error})")
            start_handler(message)
        else:
            bot.set_message_reaction(
                message.chat.id, message.id, reaction=[ReactionTypeEmoji("✍")]
            )
            bot.send_chat_action(message.chat.id, action="typing")
            iins_possible = utils.generate_iins(
                birth_date, start_suffix=5001, quantity=300
            )
            bot.send_chat_action(message.chat.id, action="typing")
            iins_postkz = asyncio.run(utils.mass_upd_iins_postkz(iins_possible))
            text = "Отправьте имя и первую букву фамилии.\nНапример: <i>Александр Д</i>"
            bot.send_message(message.chat.id, text=text)
            bot.register_next_step_handler(message, name_handler, iins_postkz)
    else:
        bot.set_message_reaction(
            message.chat.id, message.id, reaction=[ReactionTypeEmoji("👎")]
        )
        bot.reply_to(message, text="⚠️ Это не текстовое сообщение!")
        start_handler(message)


def name_handler(message: Message, iins_postkz: list[dict]) -> None:
    if message.content_type == "text":
        bot.set_message_reaction(
            message.chat.id, message.id, reaction=[ReactionTypeEmoji("✍")]
        )
        bot.send_chat_action(message.chat.id, action="typing")
        input_name = message.text.strip(" .").casefold()
        iins_matched_postkz = utils.match_name_postkz(input_name, iins_postkz)
        iins_empty_postkz = utils.empty_name_postkz(iins_postkz)
        iins_possible_postkz = iins_matched_postkz + iins_empty_postkz
        iins_nca = asyncio.run(utils.mass_upd_iins_nca(iins_possible_postkz))
        iins_matched_nca = utils.match_name_nca(input_name, iins_nca)
        if len(iins_matched_nca) == 0:
            text = (
                "❌ <b>Подходящий ИИН не найден!</b>\n\n"
                "Убедитесь, что вы верно ввели данные для поиска. "
                "Если данные указаны верно, тогда повторите поиск позже."
            )
        else:
            text = f"✅ <b>Найдено: {len(iins_matched_nca)} ИИН</b>\n"
            if len(iins_matched_nca) > 1:
                text += "Ваш ИИН только один из них (который с вашими ФИО).\n"
            text += "\n"
            for iin in iins_matched_nca:
                text += f"<b>ИИН:</b> <code>{iin['iin']}</code>\n"
                if not iin["middle_name"]:
                    iin["middle_name"] = ""
                if not iin["last_name"]:
                    iin["last_name"] = ""
                full_name = f"{iin['last_name']} {iin['first_name']} {iin['middle_name']}".strip().title()
                text += f"<b>ФИО:</b> {full_name}\n"
                text += "Добавлен в базу налоговой: "
                if iin["kgd_date"]:
                    text += f"{iin['kgd_date']}\n\n"
                else:
                    text += '(нет) - см. "Info"\n\n'
            text += (
                "<i>(ткните в значение ИИН, чтобы скопировать его в буфер)</i>\n\n"
                'Сказать спасибо можно по кнопке <b>"Donate"</b>'
            )
        bot.send_message(message.chat.id, text=text, reply_markup=inline_keyboard(0))
    else:
        bot.set_message_reaction(
            message.chat.id, message.id, reaction=[ReactionTypeEmoji("👎")]
        )
        text = "⚠️ Это не текстовое сообщение!\nОтправьте имя и первую букву фамилии."
        bot.reply_to(message, text=text)
        bot.register_next_step_handler(message, name_handler, iins_postkz)


def inline_keyboard(num: int) -> InlineKeyboardMarkup:
    info_button = InlineKeyboardButton(text="ℹ️ Info", callback_data="cb_info")
    donate_button = InlineKeyboardButton(text="💳 Donate", callback_data="cb_donate")
    search_button = InlineKeyboardButton(
        text="🔎 Новый поиск ИИН", callback_data="cb_start"
    )
    if num == 0:
        markup = InlineKeyboardMarkup(
            keyboard=[[info_button, donate_button], [search_button]]
        )
    elif num == 1:
        markup = InlineKeyboardMarkup(keyboard=[[donate_button, search_button]])
    elif num == 2:
        markup = InlineKeyboardMarkup(keyboard=[[info_button, search_button]])
    return markup


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "cb_start":
        bot.answer_callback_query(call.id, text="")
        start_handler(call.message)
    elif call.data == "cb_info":
        bot.answer_callback_query(call.id, text="")
        text = (
            f"ℹ️ <b>Info</b>\n\n"
            f"Для открытия карт/счетов в банках Kaspi и Freedom Bank достаточно, чтобы ИИН просто "
            f"был присвоен человеку (существовал в базе ГБД ФЛ). Для этих двух банков добавление ИИН "
            f"в базу налоговой не требуется.\nА для открытия карт/счетов во многих других банках "
            f"Казахстана нужно, чтобы ИИН обязательно загрузился в налоговую базу.\n\n"
            f"ИИН сразу после присвоения человеку попадает в базу <a href='{constants.GBDFL_URL}'>ГБД ФЛ</a>.\n"
            f"Вы можете самостоятельно проверить свой ИИН в ГБД ФЛ, например, через "
            f"<a href='{constants.NCA_URL}'>сайт НУЦ РК</a> (Национального Удостоверяющего Центра Республики "
            f"Казахстан).\n\nЧерез 1-3 рабочих дня после присвоения ИИН должен автоматически пройти налоговую "
            f"регистрацию, в результате чего он автоматически должен попасть в налоговую базу КГД МФ РК "
            f"(налоговая служба Казахстана).\n"
            f"Вы можете самостоятельно проверить свой ИИН в налоговой базе, например, на "
            f"<a href='{constants.FAFA_URL}'>этом сайте</a> или через <a href='{constants.POSTKZ_URL}'>сайт "
            f'Казпочты</a> (там нужно ввести свой ИИН в поле "ИИН/ЖСН" и, если автоматически отобразится ваше '
            f"имя и первая буква фамилии, значит ИИН есть в налоговой базе).\n\n"
            f"Если после присвоения ИИН прошло более недели, а ИИН так и не появился в налоговой базе, "
            f"значит автоматическая синхронизация ИИН в налоговую базу по каким-то причинам не произошла "
            f"(такое иногда случается). В этом случае, чтобы ИИН всё же появился в налоговой базе, "        
            f"вам нужно обратиться в налоговое управление КГД МФ РК, сообщить об этой проблеме "
            f"и попросить обновить ваш ИИН в налоговой базе."
        )
        bot.send_message(
            call.message.chat.id,
            text=text,
            disable_web_page_preview=True,
            reply_markup=inline_keyboard(1),
        )
    elif call.data == "cb_donate":
        bot.answer_callback_query(call.id, text="")
        text = (
            "💳 <b>Donate</b>\n\n"
            "Данный бот - это некоммерческий проект.\n"
            "Если бот вам помог, вы можете отблагодарить разработчика "
            f"<a href='{constants.DONATE_URL}'>пожертвованием</a>"
        )
        bot.send_message(
            call.message.chat.id,
            text=text,
            disable_web_page_preview=True,
            reply_markup=inline_keyboard(2),
        )


if __name__ == "__main__":
    bot.delete_webhook(drop_pending_updates=True)
    bot.infinity_polling()
