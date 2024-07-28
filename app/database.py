import sqlite3
from datetime import datetime
from pathlib import Path


def add_log_search(tg_user: dict, search: dict) -> int:
    db_file = Path("app", "data", "search_log.db")
    date_time = f"{datetime.now():%Y-%m-%d %H:%M:%S}"
    with sqlite3.connect(db_file) as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS searches (
            date_time TEXT NOT NULL,
            tg_id INTEGER NOT NULL,
            tg_nick TEXT,
            tg_name TEXT,
            search_date TEXT NOT NULL,
            search_name TEXT NOT NULL,
            found_count INTEGER
            )"""
        )
        cursor.execute(
            """INSERT INTO searches
            (date_time, tg_id, tg_nick, tg_name, search_date, search_name)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                date_time,
                tg_user["id"],
                tg_user["nick"],
                tg_user["name"],
                search["date"],
                search["name"],
            ),
        )
        return cursor.lastrowid


def add_log_count(rowid: int, found_count: int) -> None:
    db_file = Path("app", "data", "search_log.db")
    with sqlite3.connect(db_file) as db_connection:
        cursor = db_connection.cursor()
        cursor.execute(
            "UPDATE searches SET found_count = ? WHERE rowid == ?",
            (found_count, rowid)
        )


if __name__ == "__main__":
    tg_user = {
        "id": 123456789,
        "nick": "mr_dick",
        "name": "Jack White",
    }
    search = {
        "date": "1998-09-28",
        "name": "Александр Д",
    }
    search_num = add_log_search(tg_user, search)
    add_log_count(search_num, 2)