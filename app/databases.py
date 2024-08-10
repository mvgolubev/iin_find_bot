# from bot_instance import bot

import asyncio
from pathlib import Path
import aiosqlite
import ujson
import zipfile

Path("app", "data").mkdir(exist_ok=True)
cache_db_file = Path("app", "data", "cache.db")
search_log_db_file = Path("app", "data", "search_log.db")
auto_search_db_file = Path("app", "data", "auto_search.db")
access_db_file = Path("app", "data", "access.db")


async def create_databases() -> None:
    if not cache_db_file.exists():  # cache database
        async with aiosqlite.connect(cache_db_file) as db_connection:
            cursor = await db_connection.cursor()
            await cursor.execute(
                """CREATE TABLE IF NOT EXISTS level_1 (
                    when_created TEXT NOT NULL,
                    search_date TEXT NOT NULL,
                    digit_8th INTEGER NOT NULL,
                    iins_postkz TEXT
                )"""
            )
            await cursor.execute(
                """CREATE TABLE IF NOT EXISTS level_2 (
                    when_created TEXT NOT NULL,
                    search_date TEXT NOT NULL,
                    search_name TEXT NOT NULL,
                    digit_8th INTEGER NOT NULL,
                    iins_found TEXT,
                    iins_auto_search TEXT
                )"""
            )
    if not search_log_db_file.exists():  # search log database
        async with aiosqlite.connect(search_log_db_file) as db_connection:
            cursor = await db_connection.cursor()
            await cursor.execute(
                """CREATE TABLE IF NOT EXISTS searches (
                    date_time TEXT NOT NULL,
                    tg_id INTEGER NOT NULL,
                    tg_nick TEXT,
                    tg_name TEXT,
                    search_date TEXT NOT NULL,
                    search_name TEXT NOT NULL,
                    digit_8th INTEGER NOT NULL,
                    auto_search INTEGER NOT NULL,
                    cache_used INTEGER,
                    found_count INTEGER,
                    found_iins TEXT
                )"""
            )
    if not auto_search_db_file.exists():  # auto search database
        async with aiosqlite.connect(auto_search_db_file) as db_connection:
            cursor = await db_connection.cursor()
            await cursor.execute(
                """CREATE TABLE IF NOT EXISTS search_tasks (
                    when_created TEXT NOT NULL,
                    tg_id INTEGER NOT NULL,
                    tg_nick TEXT,
                    tg_name TEXT,
                    search_date TEXT NOT NULL,
                    search_name TEXT NOT NULL,
                    iins_auto_search TEXT,
                    when_changed TEXT
                )"""
            )
    if not access_db_file.exists():  # access database
        async with aiosqlite.connect(access_db_file) as db_connection:
            cursor = await db_connection.cursor()
            await cursor.execute(
                """CREATE TABLE IF NOT EXISTS white_list (
                    when_changed TEXT NOT NULL,
                    tg_id INTEGER NOT NULL,
                    tg_nick TEXT,
                    tg_name TEXT,
                    expires TEXT NOT NULL,
                    admin_tg_id INTEGER NOT NULL,
                    admin_tg_nick TEXT,
                    admin_tg_name TEXT,
                    admin_comment TEXT
                )"""
            )
            await cursor.execute(
                """CREATE TABLE IF NOT EXISTS black_list (
                    when_changed TEXT NOT NULL,
                    tg_id INTEGER NOT NULL,
                    tg_nick TEXT,
                    tg_name TEXT,
                    expires TEXT NOT NULL,
                    admin_tg_id INTEGER NOT NULL,
                    admin_tg_nick TEXT,
                    admin_tg_name TEXT,
                    admin_comment TEXT
                )"""
            )


async def write_cache(cache_level: int, cache_data: dict) -> None:
    async with aiosqlite.connect(cache_db_file) as db_connection:
        cursor = await db_connection.cursor()
        if cache_level == 1:
            await cursor.execute(
                "INSERT INTO level_1 VALUES (datetime('now'), ?, ?, ?)",
                (
                    f"{cache_data["search_date"]:%Y-%m-%d}",
                    cache_data["digit_8th"],
                    ujson.dumps(cache_data["iins_postkz"], ensure_ascii=False),
                ),
            )
            await db_connection.commit()
        elif cache_level == 2:
            await cursor.execute(
                "INSERT INTO level_2 VALUES (datetime('now'), ?, ?, ?, ?, ?)",
                (
                    f"{cache_data["search_date"]:%Y-%m-%d}",
                    cache_data["search_name"],
                    cache_data["digit_8th"],
                    ujson.dumps(cache_data["iins_found"], ensure_ascii=False),
                    ujson.dumps(cache_data["iins_auto_search"], ensure_ascii=False),
                ),
            )
            await db_connection.commit()


async def read_cache(search_date: str, search_name: str, digit_8th: int):
    cache_used = 0
    cached_data = None
    async with aiosqlite.connect(cache_db_file) as db_connection:
        cursor = await db_connection.cursor()
        await cursor.execute(
            """SELECT iins_found, iins_auto_search FROM level_2
                WHERE search_date == ?
                AND search_name == ?
                AND digit_8th == ?
            """,
            (search_date, search_name, digit_8th),
        )
        db_data = await cursor.fetchone()
        if db_data:
            cache_used = 2
            cached_data = ujson.loads(db_data[0]), ujson.loads(db_data[1])
        else:
            await cursor.execute(
                """SELECT iins_postkz FROM level_1
                    WHERE search_date == ?
                    AND digit_8th == ?
                """,
                (search_date, digit_8th),
            )
            db_data = await cursor.fetchone()
            if db_data:
                cache_used = 1
                cached_data = ujson.loads(db_data[0])
    return cache_used, cached_data


async def add_log_record(tg_user: dict, search: dict) -> int:
    async with aiosqlite.connect(search_log_db_file) as db_connection:
        cursor = await db_connection.cursor()
        await cursor.execute(
            """INSERT INTO searches (
                date_time,
                tg_id,
                tg_nick,
                tg_name,
                search_date,
                search_name,
                digit_8th,
                auto_search
            ) VALUES (datetime("now"), ?, ?, ?, ?, ?, ?, ?)""",
            (
                tg_user["id"],
                tg_user["nick"],
                tg_user["name"],
                search["date"],
                search["name"],
                search["digit_8th"],
                search["auto"],
            ),
        )
        await db_connection.commit()
        return cursor.lastrowid


async def update_log_record(
    rowid: int, cache_used: int, iins_found: list[dict]
) -> None:
    async with aiosqlite.connect(search_log_db_file) as db_connection:
        cursor = await db_connection.cursor()
        await cursor.execute(
            """UPDATE searches SET cache_used = ?, found_count = ?, found_iins = ?
                WHERE rowid == ?""",
            (
                cache_used,
                len(iins_found),
                ujson.dumps(iins_found, ensure_ascii=False),
                rowid,
            ),
        )
        await db_connection.commit()


async def cleanup_log_db(repeat_minutes: int) -> None:
    while True:
        async with aiosqlite.connect(search_log_db_file) as db_connection:
            cursor = await db_connection.cursor()
            await cursor.execute(
                "DELETE FROM searches WHERE date_time < datetime('now', '-90 days')"
            )
            await db_connection.commit()
        await asyncio.sleep(repeat_minutes * 60)


async def cleanup_cache_level1(repeat_minutes: int) -> None:
    while True:
        async with aiosqlite.connect(cache_db_file) as db_connection:
            cursor = await db_connection.cursor()
            await cursor.execute(
                "DELETE FROM level_1 WHERE when_created < datetime('now', '-1 day')"
            )
            await db_connection.commit()
        await asyncio.sleep(repeat_minutes * 60)


async def cleanup_cache_level2(repeat_minutes: int) -> None:
    while True:
        async with aiosqlite.connect(cache_db_file) as db_connection:
            cursor = await db_connection.cursor()
            await cursor.execute(
                "DELETE FROM level_2 WHERE when_created < datetime('now', '-1 hour')"
            )
            await db_connection.commit()
        await asyncio.sleep(repeat_minutes * 60)


async def cleanup_auto_search_db(repeat_minutes: int) -> None:
    while True:
        async with aiosqlite.connect(auto_search_db_file) as db_connection:
            cursor = await db_connection.cursor()
            await cursor.execute(
                "DELETE FROM search_tasks WHERE when_created < datetime('now', '-30 days')"
            )
            await db_connection.commit()
        await asyncio.sleep(repeat_minutes * 60)


async def get_log_by_tgid(tg_id: int) -> int:
    async with aiosqlite.connect(search_log_db_file) as db_connection:
        cursor = await db_connection.cursor()
        await cursor.execute(
            """SELECT COUNT(*), datetime(date_time, '+7 days', '+3 hours')
                FROM searches
                WHERE date_time > datetime('now', '-7 days')
                AND tg_id == ?
                AND digit_8th == 5
                AND auto_search == 0
                AND cache_used < 2
                AND found_count NOT NULL
            """,
            (tg_id,),
        )
        return await cursor.fetchone()


async def add_auto_search_task(tg_user: dict, search: dict) -> None:
    async with aiosqlite.connect(auto_search_db_file) as db_connection:
        cursor = await db_connection.cursor()
        await cursor.execute(
            """INSERT INTO search_tasks (
                when_created,
                tg_id,
                tg_nick,
                tg_name,
                search_date,
                search_name,
                iins_auto_search,
                when_changed
            ) VALUES (datetime("now"), ?, ?, ?, ?, ?, ?, datetime("now"))""",
            (
                tg_user["id"],
                tg_user["nick"],
                tg_user["name"],
                f"{search["date"]:%Y-%m-%d}",
                search["name"],
                ujson.dumps(search["iins_auto_search"], ensure_ascii=False),
            ),
        )
        await db_connection.commit()


async def update_auto_search_task(rowid: int) -> None:
    async with aiosqlite.connect(auto_search_db_file) as db_connection:
        cursor = await db_connection.cursor()
        await cursor.execute(
            """UPDATE search_tasks SET when_changed == datetime('now')
                WHERE rowid == ?""",
            (rowid,),
        )
        await db_connection.commit()


async def remove_search_task_by_rowid(rowid: int) -> None:
    async with aiosqlite.connect(auto_search_db_file) as db_connection:
        cursor = await db_connection.cursor()
        await cursor.execute("DELETE FROM search_tasks WHERE rowid == ?", (rowid,))
        await db_connection.commit()


async def remove_user_search_tasks(tg_id: int) -> None:
    async with aiosqlite.connect(auto_search_db_file) as db_connection:
        cursor = await db_connection.cursor()
        await cursor.execute("DELETE FROM search_tasks WHERE tg_id == ?", (tg_id,))
        await db_connection.commit()


async def get_tasks_by_tgid(tg_id: int) -> list[dict]:
    async with aiosqlite.connect(auto_search_db_file) as db_connection:
        cursor = await db_connection.cursor()
        await cursor.execute(
            """SELECT when_created, tg_id, search_date, search_name, when_changed
                FROM search_tasks WHERE tg_id == ?""",
            (tg_id,),
        )
        matching_rows = await cursor.fetchall()
        keys = (
            "when_created",
            "tg_id",
            "search_date",
            "search_name",
            "when_changed",
        )
        return [dict(zip(keys, row)) for row in matching_rows]


async def get_tasks_by_time() -> list[dict]:
    async with aiosqlite.connect(auto_search_db_file) as db_connection:
        cursor = await db_connection.cursor()
        await cursor.execute(
            """SELECT rowid, tg_id, tg_nick, tg_name, search_date, search_name, iins_auto_search
                FROM search_tasks WHERE when_changed < datetime('now', '-4 hours')
            """
        )
        matching_rows = await cursor.fetchmany(3)
        auto_search_tasks = [
            {
                "rowid": row[0],
                "tg_id": row[1],
                "tg_nick": row[2],
                "tg_name": row[3],
                "search_date": row[4],
                "search_name": row[5],
                "iins_auto_search": ujson.loads(row[6]),
            }
            for row in matching_rows
        ]
        return auto_search_tasks


def archive_db_files():
    with zipfile.ZipFile(
        file="app/data/db_archive.zip",
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as zf:
        zf.write(filename="app/data/access.db", arcname="access.db")
        zf.write(filename="app/data/auto_search.db", arcname="auto_search.db")
        zf.write(filename="app/data/search_log.db", arcname="search_log.db")


if __name__ == "__main__":
    archive_db_files()
