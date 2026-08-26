"""
Допоміжний скрипт: після того, як бота додано в групу (і зроблено адміном),
запустіть цей файл, а потім напишіть БУДЬ-ЯКЕ повідомлення в тій групі.
Скрипт виведе ID групи і додатково запише його у файл chat_id.txt —
про всяк випадок, якщо консоль щось обріже або не покаже емодзі.

Використання:
    python get_chat_id.py
Потім напишіть щось у потрібній групі протягом ~30 секунд.
"""
import asyncio
from aiogram import Bot, Dispatcher, F, types
from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(F.chat.type.in_({"group", "supergroup"}))
async def get_id(message: types.Message):
    chat_id = message.chat.id
    title = message.chat.title or "(без назви)"

    line1 = f"Знайдено групу: {title}"
    line2 = f"ID групи: {chat_id}"

    print("\n" + line1)
    print(line2)
    print("Скопіюйте це число (разом з мінусом, якщо він є) у .env як ADMIN_CHAT_ID\n")

    with open("chat_id.txt", "w", encoding="utf-8") as f:
        f.write(f"{line1}\n{line2}\n")
    print("Це саме значення також збережено у файл chat_id.txt поруч з ботом.\n")


async def main():
    print("Очікую повідомлення в групі... Напишіть щось у потрібному чаті зараз.")
    print("(Ctrl+C щоб зупинити)\n")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
