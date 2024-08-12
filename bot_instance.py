from os import getenv, path
from dotenv import load_dotenv
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties


if path.isfile(".env"):
    load_dotenv()
    default_properties = DefaultBotProperties(parse_mode="HTML")
    bot = Bot(token=getenv("BOT_API_TOKEN"), default=default_properties)
else:
    print(
        "Файл .env не найден!\n"
        '1. Создайте файл с именем ".env" рядом с файлом "bot_instance.py"\n'
        '2. В файл ".env" добавьте строку:\n'
        'BOT_API_TOKEN = "telegram_bot_token"\n'
        "где telegram_bot_token - это токен для вашего телеграм-бота, "
        'полученный от @BotFather\n3. В файл ".env" добавьте строку:\n'
        'BOT_ADMIN_ID = 1234567890\n'
        "где 1234567890 - это ID телеграм-аккаунта администратора бота."
    )