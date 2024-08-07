import asyncio
from os import getenv, path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

from app.handlers import router
from app import databases as db

if path.isfile(".env"):
    load_dotenv()
    default_properties = DefaultBotProperties(parse_mode="HTML")
    bot = Bot(token=getenv("API_TOKEN"), default=default_properties)
else:
    print(
        "Файл .env не найден!\n"
        '1. Создайте файл с именем ".env" рядом с файлом "bot.py"\n'
        '2. В файл ".env" добавьте строку:\n'
        'API_TOKEN = "telegram_bot_token"\n'
        "где telegram_bot_token - это токен для вашего телеграм-бота, полученный от @BotFather"
    )


async def run_dispatcher() -> None:
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def send_auto_search_result() -> None:
    await bot.send_message(chat_id=144651841, text="auto search result")


async def main():
    await send_auto_search_result()
    await db.create_databases()
    async_tasks = [
        asyncio.create_task(run_dispatcher()),
        asyncio.create_task(db.cleanup_log_db()),
        asyncio.create_task(db.cleanup_cache_level1()),
        asyncio.create_task(db.cleanup_cache_level2()),
        asyncio.create_task(db.cleanup_auto_search_db()),
        asyncio.create_task(db.auto_search_cycle()),
    ]
    return await asyncio.gather(*async_tasks)


if __name__ == "__main__":
    asyncio.run(main())
