import asyncio
from bot_instance import bot


async def send_text(ids: list[int]) -> None:
    text = (
        "Привет!\n🤖 Бот недавно помог вам найти ИИН. "
        "Теперь вы можете помочь боту своим "
        "<a href='https://pay.cloudtips.ru/p/9d2b07f7'>пожертвованием</a>\n"
        "🥹 Спасибо за поддержку!"
    )
    for tg_id in ids:
        print(tg_id)
        try:
            async with bot:
                await bot.send_message(
                    chat_id=tg_id,
                    text=text,
                    disable_web_page_preview=True,
                )
        except Exception as err:
            print(err)
        await asyncio.sleep(2)


if __name__ == "__main__":
    tg_user_ids = []
    asyncio.run(send_text(ids=tg_user_ids))
