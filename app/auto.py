from os import getenv
import asyncio
from aiogram.types import FSInputFile

from bot_instance import bot
from app import databases as db, keyboards as kb, utils


async def search(repeat_minutes: int) -> None:
    while True:
        auto_search_tasks = await db.get_tasks_by_time()
        for task in auto_search_tasks:
            tg_user = {
                "id": task["tg_id"],
                "nick": task["tg_nick"],
                "name": task["tg_name"],
            }
            search = {
                "date": task["search_date"],
                "name": task["search_name"].title(),
                "digit_8th": 5,
                "auto": 1,
            }
            log_row_num = await db.add_log_record(tg_user, search)
            iins_found = await utils.find_iin_auto(
                iins_auto_search=task["iins_auto_search"], name=task["search_name"]
            )
            await db.update_log_record(
                rowid=log_row_num, cache_used=0, iins_found=iins_found
            )
            if iins_found:
                await bot.send_sticker(
                    chat_id=task["tg_id"],
                    sticker="CAACAgIAAxkBAAIdWWa1K79rFVg3jNUczO4Cdg0Ug9LkAAJHAgACRxVoCeT3B7UIQsMeNQQ",
                )
                text = "🎉 <b>Авто-поиск нашёл ИИН:</b>\n\n"
                for iin in iins_found:
                    text += f"<b>ИИН:</b> <code>{iin['iin']}</code>\n"
                    full_name = utils.get_full_name(iin)
                    text += f"<b>ФИО:</b> {full_name}\n\n"
                text += (
                    "<i>(ткните в значение ИИН, чтобы скопировать его в буфер)</i>\n\n"
                    'Сказать спасибо можно по кнопке <b>"Donate"</b>'
                )
                await bot.send_message(
                    chat_id=task["tg_id"], text=text, reply_markup=kb.info
                )
                await db.remove_search_task_by_rowid(rowid=task["rowid"])
            else:
                await db.update_auto_search_task(rowid=task["rowid"])
        await asyncio.sleep(repeat_minutes * 60)


async def send_db_archive(repeat_minutes: int) -> None:
    while True:
        db.archive_db_files()
        await bot.send_document(
            chat_id=getenv("BOT_ADMIN_ID"),
            document=FSInputFile(path="app/data/db_archive.zip"),
        )
        await asyncio.sleep(repeat_minutes * 60)
