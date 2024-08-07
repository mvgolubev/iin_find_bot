import asyncio
from bot import bot

async def msg_send():
    while True:
        asyncio.sleep(10)
        await bot.send_auto_search_result()
