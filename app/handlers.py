from datetime import date
from pathlib import Path
from random import randint

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    Message,
    ReactionTypeEmoji,
    CallbackQuery,
    FSInputFile,
    BufferedInputFile,
)

from app import constants, utils, pdf_generator, databases as db, keyboards as kb


class BotStatus(StatesGroup):
    input_birth_date = State()
    input_name = State()
    search_result = State()
    config_auto_search = State()
    choose_iin = State()
    country_request = State()
    input_country = State()
    input_region = State()
    send_pdf = State()


router = Router()


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    user_role = await db.access_level(message.from_user.id)
    if user_role == "default":
        searches_count, next_possible_time_msk = await db.get_log_by_tgid(message.chat.id)
        if searches_count >= 10:
            text = (
                "⛔ <b>Поиск временно ограничен</b>\n\nВы достигли лимита: "
                "10 поисковых запросов за последние 7 дней.\nСледующий поиск "
                f"будет возможен после <b>{next_possible_time_msk} (MSK)</b>"
            )
            await message.answer(text=text)
            return None
        if searches_count in [7, 8, 9]:
            text = (
                "⚠️ <b>Вы близки к достижению лимита</b>\n\nЗа последние 7 дней "
                f"вы сделали <b>{searches_count}</b> поисковых запросов (лимит: "
                "10 запросов за последние 7 дней).\n\nПо возможности используйте "
                'авто-поиск по кнопке <b>"Настроить Авто-поиск"</b> в результатах '
                "ручного поиска.\nАвто-поиск не расходует лимит на количество "
                "ручных поисковых запросов."
            )
            await message.answer(text=text)
    await message.answer(text=f"🔎 <b>Поиск ИИН</b>\n\n{constants.DATE_REQUEST}")
    await state.set_state(BotStatus.input_birth_date)


@router.message(F.text, BotStatus.input_birth_date)
async def date_handler(message: Message, state: FSMContext) -> None:
    try:
        birth_date = date.fromisoformat(message.text)
    except ValueError as date_error:
        await message.react([ReactionTypeEmoji(emoji="👎")])
        text = f"⚠️ Дата указана некорректно\n({date_error})\n{constants.DATE_REQUEST}"
        await message.reply(text=text)
    else:
        await message.react([ReactionTypeEmoji(emoji="✍")])
        await message.chat.do(action="typing")
        await state.update_data(birth_date=birth_date)
        text = "Отправьте имя и первую букву фамилии.\nНапример: <i>Александр Б</i>"
        await message.answer(text=text, reply_markup=kb.remove)
        await state.set_state(BotStatus.input_name)


@router.message(F.text, BotStatus.input_name)
async def name_handler(message: Message, state: FSMContext) -> None:
    await message.react([ReactionTypeEmoji(emoji="✍")])
    await message.chat.do(action="typing")
    name = message.text.strip(" .").casefold()
    if len(name) == 0 or not all(char.isalpha() or char.isspace() for char in name):
        await message.react([ReactionTypeEmoji(emoji="👎")])
        text = "⚠️ Некорректное значение!\nПовторите ввод имени и первой буквы фамилии."
        await message.reply(text=text)
        return None
    await state.update_data(name=name)
    data = await state.get_data()
    text = (
        "🤖🔎 Начал поиск ИИН со следующими параметрами:\n\n"
        f"<b>◦ ИИН:</b> {data['birth_date']:%y%m%d}05xxxx\n"
        f"<b>◦ Имя:</b> {str.title(data['name'])}\n"
        f"<b>◦ Дата рождения:</b> {data['birth_date']}\n\n"
        "Ждите завершения поиска (несколько секунд)... ⏱️"
    )
    await message.answer(text=text)
    await message.chat.do(action="typing")
    tg_first_name = message.from_user.first_name
    tg_last_name = message.from_user.last_name
    tg_user = {
        "id": message.from_user.id,
        "nick": message.from_user.username,
        "name": f"{tg_first_name}{' '+tg_last_name if tg_last_name else ''}",
    }
    search = {
        "date": f"{data["birth_date"]:%Y-%m-%d}",
        "name": data["name"].title(),
        "digit_8th": 5,
        "auto": 0,
    }
    log_row_num = await db.add_log_record(tg_user, search)
    cache_used, iins_found, iins_auto_search = await utils.find_iin(
        birth_date=data["birth_date"], name=data["name"], digit_8th=5
    )
    await db.update_log_record(
        rowid=log_row_num, cache_used=cache_used, iins_found=iins_found
    )
    await state.update_data(iins_found=iins_found, iins_auto_search=iins_auto_search)
    if len(iins_found) == 0:
        text = f"{constants.NOT_FOUND_TEXT}{constants.DEEP_SEARCH_TEXT}"
    else:
        text = f"✅ <b>Найдено: {len(iins_found)} ИИН</b>"
        if cache_used > 0:
            text += " (из кэша)"
        text += "\n"
        if len(iins_found) > 1:
            text += "Ваш ИИН только один из них (который с вашими ФИО).\n"
        text += "\n"
        for iin in iins_found:
            text += f"<b>ИИН:</b> <code>{iin['iin']}</code>\n"
            full_name = utils.get_full_name(iin)
            text += f"<b>ФИО:</b> {full_name}\n"
            text += "Добавлен в базу налоговой: "
            if iin.get("kgd_date"):
                text += f"{iin['kgd_date']}\n\n"
            else:
                text += '(нет) - см. "Info"\n\n'
        text += (
            "<i>(ткните в значение ИИН, чтобы скопировать его в буфер)</i>\n\n"
            'Сказать спасибо можно по кнопке <b>"Donate"</b>\n\n'
            "🤷‍♂️ <b>Среди найденных ИИН нет вашего?</b>\n"
            f"{constants.DEEP_SEARCH_TEXT}"
        )
    tasks_count = len(await db.get_tasks_by_tgid(message.from_user.id))
    await message.answer(
        text=text,
        reply_markup=kb.search_result(deep_search=False, auto_tasks=tasks_count),
    )
    await state.set_state(BotStatus.search_result)


@router.callback_query(F.data == "cb_standard_search")
async def callback_standard_search(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer(text="")
    await start_handler(callback.message, state)


@router.callback_query(F.data == "cb_deep_search")
async def callback_deep_search(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer(text="")
    data = await state.get_data()
    if not data.get("name"):
        await default_handler(callback.message)
    else:
        text = (
            "🤖🔎 Дополнительно ищу (среди более старых ИИН):\n\n"
            f"<b>◦ ИИН:</b> {data['birth_date']:%y%m%d}00xxxx\n"
            f"<b>◦ Имя:</b> {str.title(data['name'])}\n"
            f"<b>◦ Дата рождения</b>: {data['birth_date']}\n\n"
            "Ждите завершения поиска (несколько секунд)... ⏱️"
        )
        await callback.message.answer(text=text)
        await callback.message.chat.do(action="typing")
        tg_first_name = callback.from_user.first_name
        tg_last_name = callback.from_user.last_name
        tg_user = {
            "id": callback.from_user.id,
            "nick": callback.from_user.username,
            "name": f"{tg_first_name}{' '+tg_last_name if tg_last_name else ''}",
        }
        search = {
            "date": f"{data["birth_date"]:%Y-%m-%d}",
            "name": data["name"].title(),
            "digit_8th": 0,
            "auto": 0,
        }
        row_num = await db.add_log_record(tg_user, search)
        cache_used, iins_found, _ = await utils.find_iin(
            birth_date=data["birth_date"], name=data["name"], digit_8th=0
        )
        await db.update_log_record(
            rowid=row_num, cache_used=cache_used, iins_found=iins_found
        )
        await state.update_data(iins_found=iins_found)
        if len(iins_found) == 0:
            text = f"{constants.NOT_FOUND_TEXT}"
        else:
            text = f"✅ <b>Найдено: {len(iins_found)} ИИН</b>"
            if cache_used == 2:
                text += " (из кэша)"
            if len(iins_found) > 1:
                text += "Ваш ИИН только один из них (который с вашими ФИО).\n"
            text += "\n"
            for iin in iins_found:
                text += f"<b>ИИН:</b> <code>{iin['iin']}</code>\n"
                full_name = utils.get_full_name(iin)
                text += f"<b>ФИО:</b> {full_name}\n"
                text += "Добавлен в базу налоговой: "
                if iin.get("kgd_date"):
                    text += f"{iin['kgd_date']}\n\n"
                else:
                    text += '(нет) - см. "Info"\n\n'
            text += (
                "<i>(ткните в значение ИИН, чтобы скопировать его в буфер)</i>\n\n"
                'Сказать спасибо можно по кнопке <b>"Donate"</b>'
            )
        tasks_count = len(await db.get_tasks_by_tgid(callback.from_user.id))
        await callback.message.answer(
            text=text,
            reply_markup=kb.search_result(deep_search=True, auto_tasks=tasks_count),
        )
        await state.set_state(BotStatus.search_result)


@router.callback_query(F.data == "cb_auto_search", BotStatus.search_result)
@router.callback_query(F.data == "cb_start_task", BotStatus.config_auto_search)
@router.callback_query(F.data == "cb_stop_task", BotStatus.config_auto_search)
async def callback_auto_search(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer(text="")
    if callback.data == "cb_auto_search":
        text, reply_markup = await set_auto_search_msg(callback.from_user.id, state)
        await callback.message.answer(text=text, reply_markup=reply_markup)
        await state.set_state(BotStatus.config_auto_search)
    elif callback.data == "cb_start_task":
        tg_first_name = callback.from_user.first_name
        tg_last_name = callback.from_user.last_name
        tg_user = {
            "id": callback.from_user.id,
            "nick": callback.from_user.username,
            "name": f"{tg_first_name}{' '+tg_last_name if tg_last_name else ''}",
        }
        data = await state.get_data()
        search = {
            "date": data["birth_date"],
            "name": data["name"],
            "iins_auto_search": data["iins_auto_search"],
        }
        await db.add_auto_search_task(tg_user=tg_user, search=search)
        text, reply_markup = await set_auto_search_msg(callback.from_user.id, state)
        await callback.message.edit_text(text=text, reply_markup=reply_markup)
    elif callback.data == "cb_stop_task":
        await db.remove_user_search_tasks(callback.from_user.id)
        text, reply_markup = await set_auto_search_msg(callback.from_user.id, state)
        await callback.message.edit_text(text=text, reply_markup=reply_markup)


async def set_auto_search_msg(tg_user_id: int, state: FSMContext):
    user_tasks = await db.get_tasks_by_tgid(tg_user_id)
    data = await state.get_data()
    text = "🔁 <b>Авто-поиск:</b> "
    if len(user_tasks) == 0:
        text += (
            "⚪ <b>(отключен)</b>\n\nМожно включить авто-поиск с параметрами "
            "последнего ручного поиска:\n\n"
            f"<b>◦ Дата рождения:</b> {data['birth_date']:%Y-%m-%d}\n"
            f"<b>◦ Имя:</b> {data['name'].title()}"
        )
        if data["iins_found"]:
            text += (
                "\n\n<blockquote>⚠️ ВАЖНО: ИИН, найденные при ручном поиске, "
                "будут исключены из результатов авто-поиска!</blockquote>"
            )
        reply_markup = kb.auto_search_is_off
    if len(user_tasks) == 1:
        text += (
            "🟢 <b>(включен)</b>\n\nАвто-поиск ИИН включен со следующими параметрами:\n\n"
            f"<b>◦ Дата рождения:</b> {user_tasks[0]['search_date']}\n"
            f"<b>◦ Имя:</b> {user_tasks[0]['search_name'].title()}\n"
            f"<b>◦ Включен:</b> {utils.utc_to_msk(user_tasks[0]['when_created'])}\n"
        )
        if user_tasks[0]["when_changed"] != user_tasks[0]["when_created"]:
            text += f"<b>◦ Пред. поиск:</b> {utils.utc_to_msk(user_tasks[0]['when_changed'])}\n"
        text += (
            "\n⏰ Ждите... Когда новый ИИН с этими параметрами будет автоматически "
            "найден, бот пришлёт вам сообщение.\n\n<i>Пока авто-поиск работает в фоновом"
            "режиме, вы можете параллельно вручную делать другие поисковые запросы.</i>"
        )
        reply_markup = kb.auto_search_is_on
    return text, reply_markup


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
        text=text, disable_web_page_preview=True, reply_markup=kb.info
    )


@router.callback_query(F.data == "cb_donate")
async def callback_donate(callback: CallbackQuery) -> None:
    await callback.answer(text="")
    await callback.message.answer(
        text=(
            "💳 <b>Donate</b>\n\n"
            "Данный бот - это некоммерческий проект.\n"
            "Если бот вам помог, вы можете отблагодарить разработчика "
            f"<a href='{constants.DONATE_URL}'>пожертвованием</a>"
        ),
        disable_web_page_preview=True,
        reply_markup=kb.donate,
    )


@router.callback_query(F.data == "cb_print")
async def callback_print(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer(text="")
    text = (
        "🖨️ <b>Распечатать ИИН</b>\n\n"
        "Для удалённого оформления карты Freedom Bank по приглашению "
        "распечатывать ИИН на бумаге не требуется (там нужно просто "
        "ввести при регистрации свой ИИН в соответствующее поле, а также "
        "во время видео-верификации продиктовать все цифры своего ИИН)."
        "\n\nРаспечатка свидетельства о регистрации ИИН на бумаге нужна, "
        "если вы пойдёте в отделения банков в Казахстане лично "
        "оформлять карты/счета.\n\n"
        "Для получения ИИН на бумаге вы можете зайти в любой ЦОН на "
        "территории Казахстана и попросить распечатать там ваш ИИН. "
        "Или можете заранее скачать здесь и распечатать на бумаге "
        "свидетельство о регистрации ИИН, чтобы не тратить время на "
        "посещение ЦОН в Казахстане."
    )
    data = await state.get_data()
    if data.get("iins_found") and len(data["iins_found"]) > 0:
        await callback.message.answer(text=text, reply_markup=kb.print_iin(pdf=True))
    else:
        await callback.message.answer(text=text, reply_markup=kb.print_iin(pdf=False))


@router.callback_query(F.data == "cb_rtf")
async def callback_rtf(callback: CallbackQuery) -> None:
    await callback.answer(text="")
    file_path = Path("app", "doc_templates", f"iin_template_{randint(1,3)}.rtf")
    caption = (
        f"📝 Скачайте и отредактируйте этот RTF-документ.\n{constants.RTF_DOCX_CAPTION}"
    )
    await callback.message.answer_document(
        document=FSInputFile(path=file_path), caption=caption, reply_markup=kb.info
    )


@router.callback_query(F.data == "cb_docx")
async def callback_docx(callback: CallbackQuery) -> None:
    await callback.answer(text="")
    file_path = Path("app", "doc_templates", f"iin_template_{randint(1,3)}.docx")
    caption = f"📝 Скачайте и отредактируйте этот DOCX-документ.\n{constants.RTF_DOCX_CAPTION}"
    await callback.message.answer_document(
        document=FSInputFile(path=file_path), caption=caption, reply_markup=kb.info
    )


@router.callback_query(F.data == "cb_pdf_start")
async def callback_pdf_start(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer(text="")
    data = await state.get_data()
    if not data.get("iins_found"):
        await default_handler(callback.message)
    elif len(data["iins_found"]) == 1:
        await state.update_data(index=0)
        await state.set_state(BotStatus.country_request)
        await country_request(callback, state)
    elif len(data["iins_found"]) > 1:
        text = "<b>Какой из найденных ИИН ваш?</b>\n\n"
        for n, iin in enumerate(data["iins_found"], start=1):
            text += f"{n}:\n"
            text += f"<b>ИИН:</b> {iin['iin']}\n"
            text += f"<b>ФИО:</b> {utils.get_full_name(iin)}\n\n"
        await callback.message.answer(
            text=text, reply_markup=kb.choose_iin(len(data["iins_found"]))
        )
        await state.set_state(BotStatus.choose_iin)


@router.callback_query(F.data.startswith("pdf:"), BotStatus.choose_iin)
async def callback_choose_iin(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer(text="")
    await state.update_data(index=int(callback.data.removeprefix("pdf:")))
    await state.set_state(BotStatus.country_request)
    await country_request(callback, state)


@router.callback_query(BotStatus.country_request)
async def country_request(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    iin = data["iins_found"][data["index"]]
    text = (
        f"<b>◦ ИИН:</b> {iin["iin"]}\n"
        f"<b>◦ ФИО:</b> {utils.get_full_name(iin)}\n\n"
        "🌎 <b>Страна рождения</b>\n\n"
        "Укажите страну рождения по-русски в соответствии с загран. "
        "паспортом, на который оформлялся ИИН.\n"
        'Если в паспорте указано "USSR", тогда укажите современное '
        "название соответствующей страны.\n"
        "Например: <i>Россия</i> или <i>Украина</i> или <i>Молдова</i> "
        "или <i>Грузия</i> или <i>Латвия</i>"
    )
    await callback.message.answer(text=text, reply_markup=kb.country)
    await state.set_state(BotStatus.input_country)


@router.message(F.text, BotStatus.input_country)
async def country_handler(message: Message, state: FSMContext) -> None:
    await state.update_data(country=message.text)
    text = (
        "🌎 <b>Регион (или город) рождения</b>\n\n"
        "Укажите регион (или город) рождения по-русски в соответствии "
        "с загран. паспортом, на который оформлялся ИИН.\n"
        'Обозначения "ОБЛ.", "ГОР.", "Г." не указывайте, только '
        "основная часть названия региона/города.\n"
        "Например: <i>Москва</i> или <i>Московская</i> или <i>Горьковская</i>\n\n"
        "Если кроме современного названия страны подробнее регион в паспорте "
        'не указан (например, в паспорте "УКРАИНСКАЯ ССР / USSR"), тогда '
        "на этом шаге отправьте одну точку"
    )
    await message.answer(text=text, reply_markup=kb.remove)
    await state.set_state(BotStatus.send_pdf)


@router.message(F.text, BotStatus.send_pdf)
async def send_pdf(message: Message, state: FSMContext) -> None:
    await state.update_data(region=message.text)
    data = await state.get_data()
    index = data["index"]
    iin_data = data["iins_found"][index]
    birth_date = data["birth_date"]
    if data["region"] == ".":
        birth_location = data["country"].title()
    else:
        birth_location = f"{data["country"].title()}   {data["region"].upper()}"
    file_name = f"iin_{iin_data["iin"]}.pdf"
    pdf_data = pdf_generator.generate_pdf(
        iin_data=iin_data, birth_date=birth_date, birth_location=birth_location
    )
    caption = (
        "🖨️ Распечатайте этот PDF-документ на одной стороне листа А4 "
        "с альбомной (горизонтальной) ориентацией страницы."
    )
    await message.answer_document(
        document=BufferedInputFile(file=pdf_data, filename=file_name),
        caption=caption,
        reply_markup=kb.info,
    )
    await state.clear()


@router.message()
async def default_handler(message: Message) -> None:
    await message.react([ReactionTypeEmoji(emoji="🤷‍♂️")])
    text = (
        "⚠️ Сообщение не распознано.\nПовторите ввод.\n\n"
        "Чтобы начать новый поиск ИИН, отправьте: /start"
    )
    await message.answer(text=text)
