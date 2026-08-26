"""
Допоміжний скрипт: надішліть фото своєму боту в Telegram, потім запустіть
цей файл — він виведе file_id, який можна вставити у catalog.py.

Використання:
    python get_file_id.py
Потім у Telegram надішліть фото боту протягом ~30 секунд.
"""
import asyncio
from aiogram import Bot, Dispatcher, F, types
from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(F.photo)
async def get_id(message: types.Message):
    file_id = message.photo[-1].file_id  # найбільший розмір
    print(f"\n✅ file_id для цього фото:\n{file_id}\n")
    print("Скопіюйте цей рядок у catalog.py, наприклад:")
    print(f'    "photo": "{file_id}",\n')


async def main():
    print("Надішліть фото боту в Telegram зараз (Ctrl+C щоб зупинити)...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
