import asyncio
from datetime import date

import aiohttp
from bs4 import BeautifulSoup

from app import constants, captcha


def generate_iins(birth_date: date, start_suffix: int, quantity: int) -> list[str]:
    iins_possible = []
    for suffix in range(start_suffix, start_suffix + quantity):
        iin_11 = birth_date.strftime("%y%m%d") + "0" + str(suffix)
        if checksum(iin_11) < 10:
            iins_possible.append(iin_11 + str(checksum(iin_11)))
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


async def mass_upd_iins_postkz(iins: list[str]) -> list[dict]:
    async with aiohttp.ClientSession() as session:
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
    async with session.post(
        url=constants.POSTKZ_API_URL, headers=headers, json=json
    ) as response:
        if response.status == 202:
            response_json = await response.json()
            iin_data["name"] = response_json["fio"]
            iin_data["kgd_date"] = response_json["correctDt"].split()[0]
    return iin_data


def match_name_postkz(input_name: str, iins_postkz: list[dict]) -> list[dict]:
    iins_matched_postkz = []
    for iin in iins_postkz:
        if iin["name"] and iin["name"].casefold() == input_name:
            iins_matched_postkz.append(iin)
    return iins_matched_postkz


def empty_name_postkz(iins_postkz: list[dict]) -> list[dict]:
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
                "kgd_date": None,
            }
            iins_empty_postkz.append(empty_iin)
    return iins_empty_postkz


async def mass_upd_iins_nca(iins: list[dict]) -> list[dict]:
    async with aiohttp.ClientSession() as session:
        tasks = []
        for iin in iins:
            img_data, viewstate = await get_captcha(session, constants.NCA_URL)
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
    async with session.get(url=url, headers=headers) as response:
        page = await response.text()
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
    async with session.post(
        url=constants.NCA_URL, headers=headers, data=data
    ) as response:
        xml = await response.text()
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
        if iin["first_name"]:
            # из-за существования людей без фамилии типа ИИН 991223050176 (КАДЖАЛ)
            if iin["last_name"]:
                iin_name = (iin["first_name"] + " " + iin["last_name"][0]).casefold()
            else:
                iin_name = iin["first_name"].casefold()
            if iin_name == input_name:
                iins_matched_nca.append(iin)
    return iins_matched_nca
