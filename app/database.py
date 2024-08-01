from datetime import datetime
from pathlib import Path
import aiosqlite
import ujson

Path("app", "data").mkdir(exist_ok=True)
cache_db_file = Path("app", "data", "cache.db")
search_log_db_file = Path("app", "data", "search_log.db")
access_db_file = Path("app", "data", "access.db")


async def create_databases() -> None:
    if not cache_db_file.exists():
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
                iins_matched_postkz TEXT,
                iins_empty_postkz TEXT
                )"""
            )
    if not search_log_db_file.exists():
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
                found_count INTEGER
                )"""
            )
    if not access_db_file.exists():
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
    when_created = f"{datetime.now():%Y-%m-%d %H:%M:%S}"
    print("--- Write cache ---")
    print(f"{cache_level=}\n{cache_data=}")
    if cache_level == 1:
        async with aiosqlite.connect(cache_db_file) as db_connection:
            cursor = await db_connection.cursor()
            await cursor.execute(
                """INSERT INTO level_1 (
                    when_created, search_date, digit_8th, iins_postkz
                ) VALUES (?, ?, ?, ?)""",
                (
                    when_created,
                    f"{cache_data["search_date"]:%Y-%m-%d}",
                    cache_data["digit_8th"],
                    ujson.dumps(cache_data["iins_postkz"], ensure_ascii=False),
                ),
            )
            await db_connection.commit()
    elif cache_level == 2:
        async with aiosqlite.connect(cache_db_file) as db_connection:
            cursor = await db_connection.cursor()
            await cursor.execute(
                """INSERT INTO level_2 (
                    when_created,
                    search_date,
                    search_name,
                    digit_8th,
                    iins_matched_postkz,
                    iins_empty_postkz
                ) VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    when_created,
                    f"{cache_data["search_date"]:%Y-%m-%d}",
                    cache_data["search_name"],
                    cache_data["digit_8th"],
                    ujson.dumps(cache_data["iins_matched_postkz"], ensure_ascii=False),
                    ujson.dumps(cache_data["iins_empty_postkz"]),
                ),
            )
            await db_connection.commit()


async def read_cache(search_date: str, search_name: str, digit_8th: int):
    cache_used = 0
    cached_data = None
    async with aiosqlite.connect(cache_db_file) as db_connection:
        cursor = await db_connection.cursor()
        await cursor.execute(
            """SELECT iins_matched_postkz, iins_empty_postkz FROM level_2
                WHERE search_date == ?
                AND search_name == ?
                AND digit_8th == ?
            """,
            (search_date, search_name, digit_8th),
        )
        db_data = await cursor.fetchone()
        if db_data:
            cache_used = 2
            cached_data = [ujson.loads(db_data[0]), ujson.loads(db_data[1])]
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
    print("--- Read cache ---")
    print(f"{digit_8th=}\n{cache_used=}\n{cached_data=}")
    return cache_used, cached_data


async def add_log_record(tg_user: dict, search: dict) -> int:
    date_time = f"{datetime.now():%Y-%m-%d %H:%M:%S}"
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                date_time,
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


async def update_log_record(rowid: int, cache_used: int, found_count: int) -> None:
    async with aiosqlite.connect(search_log_db_file) as db_connection:
        cursor = await db_connection.cursor()
        await cursor.execute(
            """UPDATE searches SET cache_used = ?, found_count = ?
            WHERE rowid == ?""",
            (cache_used, found_count, rowid),
        )
        await db_connection.commit()
