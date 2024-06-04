import asyncio
import base64
from datetime import date

import aiohttp
import cv2
import numpy as np
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReactionTypeEmoji

load_dotenv()
bot = TeleBot(token=getenv("API_TOKEN"), parse_mode="HTML")


@bot.message_handler(commands=["start"])
def start_handler(message):
    text = ("🔎 <b>Поиск ИИН</b>\n\n"
            "Отправьте текстом дату рождения\n(в формате ГГГГ-ММ-ДД)\n"
            "Например: <i>1997-08-25</i>")
    bot.send_message(message.chat.id, text=text)
    bot.register_next_step_handler(message, date_handler)


@bot.message_handler()
def default_handler(message):
    bot.set_message_reaction(message.chat.id, message.id, [ReactionTypeEmoji("🤷‍♂️")])
    bot.send_message(message.chat.id, text="Чтобы начать, отправьте: /start")


def date_handler(message):
    if message.content_type == "text":
        try:
            birth_date = date.fromisoformat(message.text)
        except ValueError as date_error:
            text = f"⚠️ Дата указана некорректно\n({date_error})"
            bot.reply_to(message, text=text)
            bot.set_message_reaction(message.chat.id, message.id, [ReactionTypeEmoji("👎")])
            start_handler(message)
        else:
            bot.set_message_reaction(message.chat.id, message.id, [ReactionTypeEmoji("✍")])
            bot.send_chat_action(message.chat.id, "typing", 5)
            iins_possible = generate_iins(birth_date, 5001, 300)
            iins_postkz = asyncio.run(mass_upd_iins_postkz(iins_possible))
            text = "Отправьте имя и первую букву фамилии.\nНапример: <i>Александр Б</i>"
            bot.send_message(message.chat.id, text=text)
            bot.register_next_step_handler(message, name_handler, iins_postkz)
    else:
        bot.reply_to(message, text="⚠️ Это не текстовое сообщение!")
        bot.set_message_reaction(message.chat.id, message.id, [ReactionTypeEmoji("👎")])
        start_handler(message)


def name_handler(message, iins_postkz):
    if message.content_type == "text":
        bot.set_message_reaction(message.chat.id, message.id, [ReactionTypeEmoji("✍")])
        bot.send_chat_action(message.chat.id, "typing", 5)
        iins_matched_postkz = match_name_postkz(message, iins_postkz)
        iins_empty_postkz = empty_name_postkz(iins_postkz)
        iins_possible_postkz = iins_matched_postkz + iins_empty_postkz
        iins_nca = asyncio.run(mass_upd_iins_nca(iins_possible_postkz))
        iins_matched_nca = match_name_nca(message, iins_nca)
        if len(iins_matched_nca) == 0:
            text = ("❌ <b>Подходящий ИИН не найден!</b>\n\n"
                    "Убедитесь, что вы верно ввели данные для поиска. "
                    "Если данные указаны верно, тогда повторите поиск позже.")
        else:
            text = f"✅ <b>Найдено: {len(iins_matched_nca)} ИИН</b>\n\n"
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
                     'Для дополнительной информации нажмите <b>"Info"</b>\n'
                     'Сказать спасибо можно по кнопке <b>"Donate"</b>\n')
        bot.send_message(message.chat.id, text=text, reply_markup=inline_keyboard(0))
    else:
        text = ("⚠️ Это не текстовое сообщение!\n"
                "Отправьте имя и первую букву фамилии.")
        bot.reply_to(message, text=text)
        bot.set_message_reaction(message.chat.id, message.id, [ReactionTypeEmoji("👎")])
        bot.register_next_step_handler(message, name_handler, iins_postkz)


def inline_keyboard(num: int) -> InlineKeyboardMarkup:
    info_button = InlineKeyboardButton(text="ℹ️ Info", callback_data="cb_info")
    donate_button = InlineKeyboardButton(text="💳 Donate", callback_data="cb_donate")
    search_button = InlineKeyboardButton(text="🔎 Новый поиск ИИН", callback_data="cb_start")
    if num == 0:
        markup = InlineKeyboardMarkup(keyboard=[[info_button, donate_button], [search_button]])
    elif num == 1:
        markup = InlineKeyboardMarkup(keyboard=[[donate_button, search_button]])
    elif num == 2:
        markup = InlineKeyboardMarkup(keyboard=[[info_button, search_button]])
    return markup


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "cb_start":
        start_handler(call.message)
    elif call.data == "cb_info":
        gbdfl_url = "https://www.nitec.kz/ru/proekty/gosudarstvennaya-baza-dannykh-fizicheskie-lica"
        nca_url = "https://nca.pki.gov.kz/service/pkiorder/create.xhtml?lang=ru&certtemplateAlias=individ"
        fafa_url = "https://fa-fa.kz/company_info/"
        postkz_url = "https://post.kz/register"
        text = (f"ℹ️ <b>Info</b>\n\n"
                f"ИИН сразу после присвоения человеку попадает в базу <a href='{gbdfl_url}'>ГБД ФЛ</a>.\n"
                f"Вы можете самостоятельно проверить свой ИИН в ГБД ФЛ, например, через "
                f"<a href='{nca_url}'>сайт НУЦ РК</a> (Национального Удостоверяющего Центра Республики Казахстан)."
                f"\n\nЧерез 1-3 рабочих дня после присвоения ИИН должен автоматически пройти налоговую "
                f"регистрацию, в результате чего он автоматически должен попасть в налоговую базу КГД МФ РК "
                f"(налоговая служба Казахстана).\n"
                f"Вы можете самостоятельно проверить свой ИИН в налоговой базе, например, на "
                f"<a href='{fafa_url}'>этом сайте</a> или через <a href='{postkz_url}'>сайт Казпочты</a> "
                f"(там нужно ввести свой ИИН в поле 'ИИН/ЖСН' и, "
                f"если автоматически отобразится ваше имя и первая буква фамилии, значит ИИН есть в "
                f"налоговой базе).\n\n"
                f"Если после присвоения ИИН прошло более недели, а он так и не появился в налоговой базе, "
                f"значит вам нужно обратиться в налоговое управление КГД МФ РК, сообщить об этой проблеме "
                f"и попросить обновить ваш ИИН в налоговой базе.\n\n"
                f"Для открытия счетов/карт в банках Kaspi и Freedom Bank достаточно, чтобы ИИН просто "
                f"существовал (был в базе ГБД ФЛ). А для открытия счетов/карт во многих других банках "
                f"Казахстана нужно, чтобы ИИН обязательно загрузился в налоговую базу.")
        bot.send_message(call.message.chat.id, text=text, disable_web_page_preview=True,
                         reply_markup=inline_keyboard(1))
    elif call.data == "cb_donate":
        donate_url = "https://pay.cloudtips.ru/p/9d2b07f7"
        text = ("💳 <b>Donate</b>\n\n"
                "Данный бот - это некоммерческий проект.\n"
                "Если бот вам помог, вы можете отблагодарить разработчика "
                f"<a href='{donate_url}'>пожертвованием</a>")
        bot.send_message(call.message.chat.id, text=text, disable_web_page_preview=True,
                         reply_markup=inline_keyboard(2))


def checksum(iin_11):
    check_nums = (
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11),
        (3, 4, 5, 6, 7, 8, 9, 10, 11, 1, 2)
    )
    check_digit = sum([int(x) * y for (x, y) in zip(iin_11, check_nums[0])]) % 11
    if check_digit == 10:
        check_digit = sum([int(x) * y for (x, y) in zip(iin_11, check_nums[1])]) % 11
    return check_digit


def generate_iins(birth_date, start_suffix, quantity):
    iins_possible = []
    for suffix in range(start_suffix, start_suffix + quantity):
        iin_11 = birth_date.strftime("%y%m%d") + "0" + str(suffix)
        if checksum(iin_11) < 10:
            iins_possible.append(iin_11 + str(checksum(iin_11)))
    return iins_possible


async def update_iin_postkz(session, iin):
    url = "https://post.kz/mail-app/api/checkIinBin"
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://post.kz",
        "Referer": "https://post.kz/register"
    }
    json = {"iinBin": iin}
    name = None
    kgd_date = "(нет)"
    async with session.post(url=url, headers=headers, json=json) as response:
        if response.status == 202:
            response_json = await response.json()
            name = response_json["fio"]
            kgd_date = response_json["correctDt"].split()[0]
    return {"iin": iin,
            "name": name,
            "kgd_date": kgd_date,
            "first_name": None,
            "middle_name": None,
            "last_name": None}


async def mass_upd_iins_postkz(iins):
    async with aiohttp.ClientSession() as session:
        tasks = []
        for iin in iins:
            task = asyncio.create_task(update_iin_postkz(session, iin))
            tasks.append(task)
        return await asyncio.gather(*tasks)


def match_name_postkz(message, iins_postkz):
    iins_matched_postkz = []
    for iin in iins_postkz:
        if iin["name"]:
            if iin["name"].casefold() == message.text.strip(" .").casefold():
                iins_matched_postkz.append(iin)
    return iins_matched_postkz


def empty_name_postkz(iins_postkz):
    names_list = [iin["name"] for iin in iins_postkz]
    last_name_value = [name for name in names_list if name][-1]
    names_list.reverse()
    last_est_index = len(iins_postkz) - names_list.index(last_name_value) + 4
    iins_empty_postkz = []
    for i in range(last_est_index):
        if not iins_postkz[i]["name"]:
            empty_iin = {
                "iin": iins_postkz[i]["iin"],
                "name": None,
                "kgd_date": "(нет)",
                "first_name": None,
                "middle_name": None,
                "last_name": None}
            iins_empty_postkz.append(empty_iin)
    return iins_empty_postkz


async def get_captcha(session, url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    }
    async with session.get(url=url, headers=headers) as response:
        page = await response.text()
    soup = BeautifulSoup(page, "html.parser")
    img_src = soup.find("span", id="captchaImage").find("img")["src"]
    img_data = img_src.removeprefix("data:image/png;base64,")
    viewstate = soup.find("input", id="j_id1:javax.faces.ViewState:0")["value"]
    return img_data, viewstate


def b64_to_array(img_b64):
    img_bytes = base64.b64decode(img_b64)
    img_buffer = np.frombuffer(img_bytes, dtype=np.uint8)
    return cv2.imdecode(img_buffer, cv2.IMREAD_UNCHANGED)


def gray(img_array):
    img_crop = img_array[5:][:][:]
    img_bwa = cv2.threshold(img_crop, 254, 255, cv2.THRESH_BINARY)[1]
    alpha_mask = img_bwa[:, :, 3] < 255
    img_bwa[alpha_mask] = [255, 255, 255, 255]
    return cv2.cvtColor(img_bwa, cv2.COLOR_BGRA2GRAY)


def load_all_templates():
    templates_dir = "img/templates"
    all_templates = {}
    for digit in range(10):
        for font in ("b", "i"):
            char_name = str(digit) + font
            template_file = f"{templates_dir}/{char_name}.png"
            template_array = cv2.imread(template_file, -1)
            all_templates[char_name] = template_array
    return all_templates


def match_digit(digit_templates, gray_img_array, method, threshhold):
    digit_coordinates = []
    for template in digit_templates:
        match_array = cv2.matchTemplate(gray_img_array, template, method)
        if method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
            char_positions = np.where(match_array <= 1 - threshhold)[1]
        else:
            char_positions = np.where(match_array >= threshhold)[1]
        digit_coordinates.extend(char_positions)
    return digit_coordinates


def digits_positions(img_array, all_templates, method, threshhold):
    digit_coordinates = {}
    for digit in range(10):
        digit_templates = (all_templates[f"{digit}b"], all_templates[f"{digit}i"])
        coordinates = match_digit(digit_templates, gray(img_array), method, threshhold)
        for x_coord in coordinates:
            digit_coordinates[x_coord] = str(digit)
    return digit_coordinates


def resolve_captcha(img_array, all_templates):
    # try_methods = [cv2.TM_SQDIFF_NORMED, cv2.TM_CCORR_NORMED, cv2.TM_CCOEFF_NORMED]
    method = cv2.TM_CCORR_NORMED
    threshhold = 0.99
    digit_coordinates = digits_positions(img_array, all_templates, method, threshhold)
    captcha_txt = ""
    for position, char in sorted(digit_coordinates.items()):
        captcha_txt += char
    return captcha_txt


async def update_iin_nca(session, nca_url, iin, captcha_answer, viewstate):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "application/xml, text/xml, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Faces-Request": "partial/ajax",
        "X-Requested-With": "XMLHttpRequest"
    }
    data = {
        "javax.faces.partial.ajax": "true",
        "javax.faces.source": "rcfield:0:checkPersonButton",
        "javax.faces.partial.execute": "indexForm",
        "javax.faces.partial.render": "indexForm",
        "rcfield:0:checkPersonButton": "rcfield:0:checkPersonButton",
        "indexForm": "indexForm",
        "captcha": captcha_answer,
        "rcfield:0:inputValue": iin["iin"],
        "connectionpoint": "",
        "userAgreementCheckHidden": "true",
        "certrequestStr": "",
        "keyidStr": "",
        "javax.faces.ViewState": viewstate
    }
    async with session.post(url=nca_url, headers=headers, data=data) as response:
        xml = await response.text()
    xml_soup = BeautifulSoup(xml, "xml")
    html = xml_soup.find("update", id="indexForm").string
    html_soup = BeautifulSoup(html, "html.parser")
    alert = html_soup.find("li", role="alert")
    if alert:
        last_name = first_name = middle_name = None
    else:
        last_name = html_soup.find("span", class_="lastname").string
        first_name = html_soup.find("span", class_="firstname").string
        middle_name = html_soup.find("span", class_="middlename").string
    return {"iin": iin["iin"],
            "name": iin["name"],
            "kgd_date": iin["kgd_date"],
            "last_name": last_name,
            "first_name": first_name,
            "middle_name": middle_name}


async def mass_upd_iins_nca(iins):
    nca_url = "https://nca.pki.gov.kz/service/pkiorder/create.xhtml?lang=ru&certtemplateAlias=individ"
    all_templates = load_all_templates()
    async with aiohttp.ClientSession() as session:
        tasks = []
        for iin in iins:
            img_data, viewstate = await get_captcha(session, nca_url)
            captcha_answer = resolve_captcha(b64_to_array(img_data), all_templates)
            task = asyncio.create_task(update_iin_nca(session, nca_url, iin, captcha_answer, viewstate))
            tasks.append(task)
        return await asyncio.gather(*tasks)


def match_name_nca(message, nca_updated_iins):
    msg_name = message.text.strip(" .").casefold()
    iins_matched_nca = []
    for iin in nca_updated_iins:
        if iin["first_name"]:
            # из-за существования людей без фамилии типа ИИН 991223050176 (КАДЖАЛ)
            if iin["last_name"]:
                iin_name = (iin["first_name"] + " " + iin["last_name"][0]).casefold()
            else:
                iin_name = iin["first_name"].casefold()
            if iin_name == msg_name:
                iins_matched_nca.append(iin)
    return iins_matched_nca


if __name__ == "__main__":
    bot.delete_webhook(drop_pending_updates=True)
    bot.infinity_polling()
