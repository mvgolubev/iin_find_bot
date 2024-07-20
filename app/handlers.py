from datetime import date

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    Message,
    ReactionTypeEmoji,
    CallbackQuery,
)

from app import constants, utils, keyboards as kb


class IinInfo(StatesGroup):
    birth_date = State()
    name = State()
    standard_search_complete = State()


router = Router()


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    text = f"🔎 <b>Поиск ИИН</b>\n\n{constants.DATE_REQUEST}"
    await message.answer(text=text)
    await state.set_state(IinInfo.birth_date)


@router.message(IinInfo.birth_date)
async def date_handler(message: Message, state: FSMContext) -> None:
    if message.content_type == "text":
        try:
            birth_date = date.fromisoformat(message.text)
        except ValueError as date_error:
            await message.react([ReactionTypeEmoji(emoji="👎")])
            await message.reply(
                text=f"⚠️ Дата указана некорректно\n({date_error})\n{constants.DATE_REQUEST}"
            )
        else:
            await message.react([ReactionTypeEmoji(emoji="✍")])
            await message.chat.do(action="typing")
            await state.update_data(birth_date=birth_date)
            await message.answer(
                text="Отправьте имя и первую букву фамилии.\nНапример: <i>Александр Б</i>"
            )
            await state.set_state(IinInfo.name)
    else:
        await message.react([ReactionTypeEmoji(emoji="👎")])
        await message.reply(
            text=f"⚠️ Это не текстовое сообщение!\n{constants.DATE_REQUEST}"
        )


@router.message(IinInfo.name)
async def name_handler(message: Message, state: FSMContext) -> None:
    if message.content_type == "text":
        await message.react([ReactionTypeEmoji(emoji="✍")])
        await message.chat.do(action="typing")
        name = message.text.strip(" .").casefold()
        await state.update_data(name=name)
        data = await state.get_data()
        text = (
            "🤖🔎 Начал искать ИИН. Ждите...\n\n"
            f"* Дата рождения: {data['birth_date']}\n"
            f"* Имя: {str.title(data['name'])}\n"
            f"* ИИН: {data['birth_date']:%y%m%d}05xxxx"
        )
        await message.answer(text=text)
        await message.chat.do(action="typing")
        iins_found = await utils.find_iin(
            birth_date=data["birth_date"], name=data["name"], digit_8th=5
        )
        if len(iins_found) == 0:
            text = f"{constants.NOT_FOUND_TEXT}{constants.DEEP_SEARCH_TEXT}"
            await message.answer(text=text, reply_markup=kb.not_found_standard())
            await state.set_state(IinInfo.standard_search_complete)
        else:
            text = f"✅ <b>Найдено: {len(iins_found)} ИИН</b>\n"
            if len(iins_found) > 1:
                text += "Ваш ИИН только один из них (который с вашими ФИО).\n"
            text += "\n"
            for iin in iins_found:
                text += f"<b>ИИН:</b> <code>{iin['iin']}</code>\n"
                if not iin["first_name"]:
                    iin["first_name"] = ""
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
                'Сказать спасибо можно по кнопке <b>"Donate"</b>\n\n'
                "🤷‍♂️ <b>Среди найденных ИИН нет вашего?</b>\n"
                f"{constants.DEEP_SEARCH_TEXT}"
            )
            await message.answer(text=text, reply_markup=kb.found_standard())
            await state.set_state(IinInfo.standard_search_complete)
    else:
        await message.react([ReactionTypeEmoji(emoji="👎")])
        await message.reply(
            text="⚠️ Это не текстовое сообщение!\nОтправьте имя и первую букву фамилии."
        )


@router.message()
async def default_handler(message: Message) -> None:
    await message.react([ReactionTypeEmoji(emoji="🤷‍♂️")])
    await message.answer(text="Чтобы начать, отправьте: /start")


@router.callback_query(F.data == "cb_standard_search")
async def callback_standard_search(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer(text="")
    await start_handler(callback.message, state)


@router.callback_query(F.data == "cb_deep_search", IinInfo.standard_search_complete)
async def callback_deep_search(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer(text="")
    data = await state.get_data()
    text = (
        "🤖🔎 Дополнительно ищу среди более старых ИИН. Ждите...\n\n"
        f"* Дата рождения: {data['birth_date']}\n"
        f"* Имя: {str.title(data['name'])}\n"
        f"* ИИН: {data['birth_date']:%y%m%d}00xxxx"
    )
    await callback.message.answer(text=text)
    await callback.message.chat.do(action="typing")
    iins_found = await utils.find_iin(
        birth_date=data["birth_date"], name=data["name"], digit_8th=0
    )
    if len(iins_found) == 0:
        text = f"{constants.NOT_FOUND_TEXT}"
        await callback.message.answer(text=text, reply_markup=kb.not_found_deep())
    else:
        text = f"✅ <b>Найдено: {len(iins_found)} ИИН</b>\n"
        if len(iins_found) > 1:
            text += "Ваш ИИН только один из них (который с вашими ФИО).\n"
        text += "\n"
        for iin in iins_found:
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
        await callback.message.answer(text=text, reply_markup=kb.found_deep())


@router.callback_query(F.data == "cb_info")
async def callback_info(callback: CallbackQuery) -> None:
    await callback.answer(text="")
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
    await callback.message.answer(
        text=text, disable_web_page_preview=True, reply_markup=kb.info()
    )


@router.callback_query(F.data == "cb_donate")
async def callback_donate(callback: CallbackQuery) -> None:
    await callback.answer(text="")
    text = (
        "💳 <b>Donate</b>\n\n"
        "Данный бот - это некоммерческий проект.\n"
        "Если бот вам помог, вы можете отблагодарить разработчика "
        f"<a href='{constants.DONATE_URL}'>пожертвованием</a>"
    )
    await callback.message.answer(
        text=text, disable_web_page_preview=True, reply_markup=kb.donate()
    )
