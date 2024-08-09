import asyncio
from aiogram import Dispatcher

from bot_instance import bot
from app.handlers import router
from app import databases as db, auto_search


async def run_dispatcher() -> None:
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def main():
    await db.create_databases()
    async_tasks = [
        asyncio.create_task(run_dispatcher()),
        asyncio.create_task(db.cleanup_log_db(repeat_minutes=60)),
        asyncio.create_task(db.cleanup_auto_search_db(repeat_minutes=60)),
        asyncio.create_task(db.cleanup_cache_level1(repeat_minutes=10)),
        asyncio.create_task(db.cleanup_cache_level2(repeat_minutes=1)),
        asyncio.create_task(auto_search.search_cycle(repeat_minutes=1)),
    ]
    return await asyncio.gather(*async_tasks)


if __name__ == "__main__":
    asyncio.run(main())
