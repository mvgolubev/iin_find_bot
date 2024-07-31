from datetime import datetime
from pathlib import Path
import aiosqlite
from app import constants


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
                cache_level INTEGER,
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

async def add_log_search(tg_user: dict, search: dict, search_type: int) -> int:
    db_file = Path("app", "data", constants.SEARCH_LOG_DB_FILE)
    date_time = f"{datetime.now():%Y-%m-%d %H:%M:%S}"
    async with aiosqlite.connect(db_file) as db_connection:
        cursor = await db_connection.cursor()
        await cursor.execute(
            """INSERT INTO searches
            (date_time, tg_id, tg_nick, tg_name, search_date, search_name, search_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                date_time,
                tg_user["id"],
                tg_user["nick"],
                tg_user["name"],
                search["date"],
                search["name"],
                search_type,
            ),
        )
        await db_connection.commit()
        return cursor.lastrowid


async def add_log_count(rowid: int, found_count: int) -> None:
    db_file = Path("app", "data", constants.SEARCH_LOG_DB_FILE)
    async with aiosqlite.connect(db_file) as db_connection:
        cursor = await db_connection.cursor()
        await cursor.execute(
            "UPDATE searches SET found_count = ? WHERE rowid == ?", (found_count, rowid)
        )
        await db_connection.commit()
