from datetime import datetime
from pathlib import Path
import asyncio
import aiosqlite
from app import constants


async def add_log_search(tg_user: dict, search: dict, search_type: int) -> int:
    db_file = Path("app", "data", constants.SEARCH_LOG_DB_FILE)
    date_time = f"{datetime.now():%Y-%m-%d %H:%M:%S}"
    async with aiosqlite.connect(db_file) as db_connection:
        cursor = await db_connection.cursor()
        await cursor.execute(
            """CREATE TABLE IF NOT EXISTS searches (
            date_time TEXT NOT NULL,
            tg_id INTEGER NOT NULL,
            tg_nick TEXT,
            tg_name TEXT,
            search_date TEXT NOT NULL,
            search_name TEXT NOT NULL,
            search_type INTEGER NOT NULL,
            found_count INTEGER
            )"""
        )
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


