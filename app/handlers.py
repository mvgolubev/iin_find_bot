from datetime import date

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReactionTypeEmoji, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from app import constants, utils


class IinInfo(StatesGroup):
    birth_date = State()
    name = State()


router = Router()


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    text = (f"🔎 <b>Поиск ИИН</b>\n\n{constants.DATE_REQUEST}")
    await message.answer(text=text)
    await state.set_state(IinInfo.birth_date)


@router.message(IinInfo.birth_date)
async def date_handler(message: Message, state: FSMContext) -> None:
    if message.content_type == "text":
        try:
            birth_date = date.fromisoformat(message.text)
        except ValueError as date_error:
            await message.react([ReactionTypeEmoji(emoji="👎")])
            await message.reply(text=f"⚠️ Дата указана некорректно\n({date_error})\n{constants.DATE_REQUEST}")
        else:
            await message.react([ReactionTypeEmoji(emoji="✍")])
            await message.chat.do(action="typing")
            iins_possible = utils.generate_iins(birth_date, start_suffix=5001, quantity=300)
            await message.chat.do(action="typing")
            iins_postkz = await utils.mass_upd_iins_postkz(iins_possible)
            await state.update_data(iins=iins_postkz)
            await message.answer(text="Отправьте имя и первую букву фамилии.\nНапример: <i>Александр Б</i>")
            await state.set_state(IinInfo.name)
    else:
        await message.react([ReactionTypeEmoji(emoji="👎")])
        await message.reply(text=f"⚠️ Это не текстовое сообщение!\n{date_req}")


@router.message(IinInfo.name)
async def name_handler(message: Message, state: FSMContext) -> None:
    if message.content_type == "text":
        await message.react([ReactionTypeEmoji(emoji="✍")])
        await message.chat.do(action="typing")
        input_name = message.text.strip(" .").casefold()
        iins_postkz = (await state.get_data())["iins"]
        iins_matched_postkz = utils.match_name_postkz(input_name, iins_postkz)
        iins_empty_postkz = utils.empty_name_postkz(iins_postkz)
        iins_possible_postkz = iins_matched_postkz + iins_empty_postkz
        iins_nca = await utils.mass_upd_iins_nca(iins_possible_postkz)
        iins_matched_nca = utils.match_name_nca(input_name, iins_nca)
        if len(iins_matched_nca) == 0:
            text = ("❌ <b>Подходящий ИИН не найден!</b>\n\n"
                    "Убедитесь, что вы верно ввели данные для поиска. "
                    "Если данные указаны верно, тогда повторите поиск позже.")
        else:
            text = f"✅ <b>Найдено: {len(iins_matched_nca)} ИИН</b>\n"
            if len(iins_matched_nca) > 1:
                text += "Ваш ИИН только один из них (который с вашими ФИО).\n"
            text += "\n"
            for iin in iins_matched_nca:
                text += f"<b>ИИН:</b> <code>{iin["iin"]}</code>\n"
                if not iin["middle_name"]:
                    iin["middle_name"] = ""
                if not iin["last_name"]:
                    iin["last_name"] = ""
                full_name = f"{iin["last_name"]} {iin["first_name"]} {iin["middle_name"]}".strip().title()
                text += f"<b>ФИО:</b> {full_name}\n"
                text += f"Добавлен в базу налоговой: {iin["kgd_date"]}\n\n"
            text += ("<i>(ткните в значение ИИН, чтобы скопировать его в буфер)</i>\n\n"
                     "Для дополнительной информации нажмите <b>\"Info\"</b>\n"
                     "Сказать спасибо можно по кнопке <b>\"Donate\"</b>")
        await message.answer(text=text, reply_markup=inline_keyboard(0))
    else:
        await message.react([ReactionTypeEmoji(emoji="👎")])
        await message.reply(text="⚠️ Это не текстовое сообщение!\nОтправьте имя и первую букву фамилии.")


@router.message()
async def default_handler(message: Message) -> None:
    await message.react([ReactionTypeEmoji(emoji="🤷‍♂️")])
    await message.answer(text="Чтобы начать, отправьте: /start")


def inline_keyboard(num: int) -> InlineKeyboardMarkup:
    info_button = InlineKeyboardButton(text="ℹ️ Info", callback_data="cb_info")
    donate_button = InlineKeyboardButton(text="💳 Donate", callback_data="cb_donate")
    search_button = InlineKeyboardButton(text="🔎 Новый поиск ИИН", callback_data="cb_search")
    if num == 0:
        markup = InlineKeyboardMarkup(inline_keyboard=[[info_button, donate_button], [search_button]])
    elif num == 1:
        markup = InlineKeyboardMarkup(inline_keyboard=[[donate_button, search_button]])
    elif num == 2:
        markup = InlineKeyboardMarkup(inline_keyboard=[[info_button, search_button]])
    return markup


@router.callback_query(F.data == "cb_search")
async def callback_search(callback: CallbackQuery, state: FSMContext) -> None:
    await start_handler(callback.message, state)
    await callback.answer(text="")


@router.callback_query(F.data == "cb_info")
async def callback_info(callback: CallbackQuery) -> None:
    text = (f"ℹ️ <b>Info</b>\n\n"
            f"ИИН сразу после присвоения человеку попадает в базу <a href='{constants.GBDFL_URL}'>ГБД ФЛ</a>.\n"
            f"Вы можете самостоятельно проверить свой ИИН в ГБД ФЛ, например, через "
            f"<a href='{constants.NCA_URL}'>сайт НУЦ РК</a> (Национального Удостоверяющего Центра Республики "
            f"Казахстан).\n\nЧерез 1-3 рабочих дня после присвоения ИИН должен автоматически пройти налоговую "
            f"регистрацию, в результате чего он автоматически должен попасть в налоговую базу КГД МФ РК "
            f"(налоговая служба Казахстана).\n"
            f"Вы можете самостоятельно проверить свой ИИН в налоговой базе, например, на "
            f"<a href='{constants.FAFA_URL}'>этом сайте</a> или через <a href='{constants.POSTKZ_URL}'>сайт "
            f"Казпочты</a> (там нужно ввести свой ИИН в поле \"ИИН/ЖСН\" и, если автоматически отобразится ваше "
            f"имя и первая буква фамилии, значит ИИН есть в налоговой базе).\n\n"
            f"Если после присвоения ИИН прошло более недели, а он так и не появился в налоговой базе, "
            f"значит вам нужно обратиться в налоговое управление КГД МФ РК, сообщить об этой проблеме "
            f"и попросить обновить ваш ИИН в налоговой базе.\n\n"
            f"Для открытия счетов/карт в банках Kaspi и Freedom Bank достаточно, чтобы ИИН просто "
            f"существовал (был в базе ГБД ФЛ). А для открытия счетов/карт во многих других банках "
            f"Казахстана нужно, чтобы ИИН обязательно загрузился в налоговую базу.")
    await callback.message.answer(text=text, disable_web_page_preview=True, reply_markup=inline_keyboard(1))
    await callback.answer(text="")


@router.callback_query(F.data == "cb_donate")
async def callback_donate(callback: CallbackQuery) -> None:
    text = ("💳 <b>Donate</b>\n\n"
            "Данный бот - это некоммерческий проект.\n"
            "Если бот вам помог, вы можете отблагодарить разработчика "
            f"<a href='{constants.DONATE_URL}'>пожертвованием</a>")
    await callback.message.answer(text=text, disable_web_page_preview=True, reply_markup=inline_keyboard(2))
    await callback.answer(text="")
