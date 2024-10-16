import asyncio
from datetime import date, datetime, timedelta, timezone

import aiohttp
from bs4 import BeautifulSoup

from app import constants, captcha, databases as db


def generate_iins(
    birth_date: date, digit_8th: int = 5, quantity: int = 300
) -> list[str]:
    iins_possible = []
    for suffix in range(1, quantity):
        iin_11 = f"{birth_date:%y%m%d}0{digit_8th}{str(suffix).zfill(3)}"
        if checksum(iin_11) < 10:
            iins_possible.append(f"{iin_11}{checksum(iin_11)}")
    return iins_possible


def checksum(iin_11: str) -> int:
    check_nums = (
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11),
        (3, 4, 5, 6, 7, 8, 9, 10, 11, 1, 2),
    )
    check_digit = sum([int(x) * y for (x, y) in zip(iin_11, check_nums[0])]) % 11
    if check_digit == 10:
        check_digit = sum([int(x) * y for (x, y) in zip(iin_11, check_nums[1])]) % 11
    return check_digit


async def mass_upd_iins_postkz(
    session: aiohttp.ClientSession, iins: list[str]
) -> list[dict]:
    tasks = []
    for iin in iins:
        task = asyncio.create_task(update_iin_postkz(session, iin))
        tasks.append(task)
    return await asyncio.gather(*tasks)


async def update_iin_postkz(session: aiohttp.ClientSession, iin: str) -> dict:
    iin_data = {
        "iin": iin,
        "name": None,
        "kgd_date": None,
    }
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "User-Agent": constants.USER_AGENT,
        "Origin": "https://post.kz",
        "Referer": constants.POSTKZ_URL,
    }
    json = {"iinBin": iin}
    try:
        async with session.post(
            url=constants.POSTKZ_API_URL, headers=headers, json=json
        ) as response:
            if response.status == 202:
                response_json = await response.json()
                iin_data["name"] = response_json["fio"]
                iin_data["kgd_date"] = response_json["correctDt"].split()[0]
    except aiohttp.ClientConnectionError as err:
        print(f"*** ERROR: update_iin_postkz - {err}")
    return iin_data


def match_name_postkz(input_name: str, iins_postkz: list[dict]) -> list[dict]:
    iins_matched_postkz = []
    for iin in iins_postkz:
        if iin["name"] and iin["name"].casefold() == input_name:
            iins_matched_postkz.append(iin)
    return iins_matched_postkz


def empty_name_postkz(iins_postkz: list[dict]) -> list[dict]:
    names_list = [iin["name"] for iin in iins_postkz]
    if names_list.count(None) == len(names_list):
        last_est_index = 4
    else:
        last_name_value = [name for name in names_list if name][-1]
        names_list.reverse()
        last_est_index = min(
            len(iins_postkz), len(iins_postkz) - names_list.index(last_name_value) + 4
        )
    iins_empty_postkz = []
    for i in range(last_est_index):
        if not iins_postkz[i]["name"]:
            empty_iin = {"iin": iins_postkz[i]["iin"]}
            iins_empty_postkz.append(empty_iin)
    return iins_empty_postkz


async def mass_upd_iins_nca(
    session: aiohttp.ClientSession, iins: list[dict]
) -> list[dict]:
    tasks = []
    for iin in iins:
        img_data, viewstate = await get_captcha(session, constants.NCA_URL)
        if img_data:
            captcha_answer = captcha.resolve_captcha(img_data)
            task = asyncio.create_task(
                update_iin_nca(session, iin, captcha_answer, viewstate)
            )
            tasks.append(task)
    return await asyncio.gather(*tasks)


async def get_captcha(session: aiohttp.ClientSession, url: str) -> tuple[str, str]:
    headers = {
        "User-Agent": constants.USER_AGENT,
    }
    try:
        async with session.get(url=url, headers=headers) as response:
            page = await response.text()
    except aiohttp.ClientConnectionError as err:
        print(f"*** ERROR: get_captcha - {err}")
        return None, None
    else:
        soup = BeautifulSoup(markup=page, features="html.parser")
        img_src = soup.find(name="span", id="captchaImage").find("img")["src"]
        img_data = img_src.removeprefix("data:image/png;base64,")
        viewstate = soup.find(name="input", id="j_id1:javax.faces.ViewState:0")["value"]
        return img_data, viewstate
    

async def update_iin_nca(
    session: aiohttp.ClientSession, iin: dict, captcha_answer: str, viewstate: str
) -> dict:
    headers = {
        "User-Agent": constants.USER_AGENT,
        "Accept": "application/xml, text/xml, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Faces-Request": "partial/ajax",
        "X-Requested-With": "XMLHttpRequest",
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
        "javax.faces.ViewState": viewstate,
    }
    try:
        async with session.post(
            url=constants.NCA_URL, headers=headers, data=data
        ) as response:
            xml = await response.text()
    except aiohttp.ClientConnectionError as err:
        print(f"*** ERROR: update_iin_nca - {err}")
        iin["last_name"] = iin["first_name"] = iin["middle_name"] = None
    else:
        xml_soup = BeautifulSoup(xml, "xml")
        html = xml_soup.find("update", id="indexForm").string
        html_soup = BeautifulSoup(html, "html.parser")
        alert = html_soup.find("li", role="alert")
        if alert:
            iin["last_name"] = iin["first_name"] = iin["middle_name"] = None
        else:
            iin["last_name"] = html_soup.find("span", class_="lastname").string
            iin["first_name"] = html_soup.find("span", class_="firstname").string
            iin["middle_name"] = html_soup.find("span", class_="middlename").string
    return iin


def match_name_nca(input_name: str, nca_updated_iins: list[dict]) -> list[dict]:
    iins_matched_nca = []
    for iin in nca_updated_iins:
        iin_name = ""
        # ИИН 991223050176 - has first name only (КАДЖАЛ)
        # ИИН 000101051361 - has last name only (САЖВАЛ)
        if iin["first_name"]:
            if iin["last_name"]:  # has first_name AND last_name
                iin_name = (iin["first_name"] + " " + iin["last_name"][0]).casefold()
            else:  # has first_name only
                iin_name = iin["first_name"].casefold()
        elif iin["last_name"]:  # has last_name only
            iin_name = iin["last_name"].casefold()
        if iin_name == input_name:
            iins_matched_nca.append(iin)
    return iins_matched_nca


def get_full_name(iin_data: dict) -> str:
    first = iin_data["first_name"] or ""
    middle = iin_data["middle_name"] or ""
    last = iin_data["last_name"] or ""
    return f"{last} {first} {middle}".strip().title()


async def find_iin(
    birth_date: date, name: str, digit_8th: int = 5
) -> tuple[int, list[dict], list[dict]]:
    cache_used, cached_data = await db.read_cache(birth_date, name, digit_8th)
    async with aiohttp.ClientSession() as session:
        if cache_used == 2:
            return cache_used, cached_data[0], cached_data[1]
        elif cache_used == 1:
            iins_postkz = cached_data
        elif cache_used == 0:
            iins_possible = generate_iins(birth_date, digit_8th=digit_8th, quantity=300)
            iins_postkz = await mass_upd_iins_postkz(session, iins_possible)
            data_to_cache = {
                "search_date": birth_date,
                "digit_8th": digit_8th,
                "iins_postkz": iins_postkz,
            }
            await db.write_cache(cache_level=1, cache_data=data_to_cache)
        iins_matched_postkz = match_name_postkz(name, iins_postkz)
        iins_empty_postkz = empty_name_postkz(iins_postkz)
        iins_possible_postkz = iins_matched_postkz + iins_empty_postkz
        iins_nca = await mass_upd_iins_nca(session, iins_possible_postkz)
        iins_found = match_name_nca(name, iins_nca)
        iins_auto_search = [
            {"iin": iin["iin"]}
            for iin in iins_empty_postkz
            if iin["iin"] not in [iin["iin"] for iin in iins_found]
        ]
        data_to_cache = {
            "search_date": birth_date,
            "search_name": name,
            "digit_8th": digit_8th,
            "iins_found": iins_found,
            "iins_auto_search": iins_auto_search,
        }
        await db.write_cache(cache_level=2, cache_data=data_to_cache)
    return cache_used, iins_found, iins_auto_search


async def find_iin_auto(iins_auto_search: list[dict], name: str) -> list[dict]:
    async with aiohttp.ClientSession() as session:
        iins_nca = await mass_upd_iins_nca(session, iins_auto_search)
        return match_name_nca(name, iins_nca)


def utc_to_msk(utc_datetime: str) -> str:
    msk_datetime = datetime.fromisoformat(utc_datetime) + timedelta(hours=3)
    return f"{msk_datetime:%Y-%m-%d %H:%M} (MSK)"


def is_time_to_search() -> bool:
    now_utc = datetime.now(timezone.utc)
    if now_utc.weekday() > 4:
        return False
    if now_utc.hour < 4 or now_utc.hour > 16:
        return False
    return True