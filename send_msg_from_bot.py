import asyncio
from bot_instance import bot


async def send_text(ids: list[int]) -> None:
    text = (
        "Привет!\nБот недавно помог вам найти ИИН. "
        "Теперь вы можете помочь боту своим "
        "<a href='https://pay.cloudtips.ru/p/9d2b07f7'>пожертвованием</a>"
    )
    for tg_id in ids:
        await bot.send_animation(
            chat_id=tg_id,
            animation="CgACAgIAAxkBAAIfmGbBMa7x0K4rG-GIu66Vvh04m7nZAAIaUgACFQgRSt0QJMcbESvRNQQ",
            caption=text,
        )
        await asyncio.sleep(5)


if __name__ == "__main__":
    tg_user_ids = []
    asyncio.run(send_text(ids=tg_user_ids))
