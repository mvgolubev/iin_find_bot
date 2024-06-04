import asyncio
from os import getenv, path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from app.handlers import router


async def main() -> None:
    if path.isfile(".env"):
        load_dotenv()
        bot = Bot(token=getenv("API_TOKEN"), default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()
        dp.include_router(router)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    else:
        print("Файл .env не найден!\n"
              "1. Создайте файл с именем \".env\" рядом с файлом \"bot.py\"\n"
              "2. В файл \".env\" добавьте строку:\n"
              "API_TOKEN = \"telegram_bot_token\"\n"
              "где telegram_bot_token - это токен для вашего телеграм-бота, полученный от @BotFather")


if __name__ == "__main__":
    asyncio.run(main())
