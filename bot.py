import asyncio
import logging
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import database as db
from config import BOT_TOKEN, DB_PATH, ADMIN_CHAT_ID
from handlers import common, catalog, cart, checkout, admin


def setup_logging():
    handler = RotatingFileHandler("bot.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[handler, logging.StreamHandler()],
    )


async def check_admin_chat(bot: Bot, logger: logging.Logger):
    """Перевіряє при старті, чи бот може писати в адмін-чат — щоб не чекати
    реального замовлення, аби дізнатись, що ADMIN_CHAT_ID або права налаштовані невірно."""
    if not ADMIN_CHAT_ID:
        logger.warning("ADMIN_CHAT_ID не заданий у .env — сповіщення про замовлення надсилатись не будуть.")
        return
    try:
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text="✅ Бот запущено. Сповіщення про замовлення будуть приходити сюди.")
        logger.info("Перевірка адмін-чату успішна: повідомлення надіслано в %s", ADMIN_CHAT_ID)
    except Exception as e:
        logger.error(
            "НЕ ВДАЛОСЯ надіслати повідомлення в ADMIN_CHAT_ID=%s. "
            "Перевірте: 1) чи бот доданий у групу, 2) чи він там адміністратор, "
            "3) чи правильний ID (має бути число типу -1001234567890). Помилка: %s",
            ADMIN_CHAT_ID, e,
        )


async def main():
    setup_logging()
    logger = logging.getLogger(__name__)

    await db.init_db(DB_PATH)
    logger.info("База даних ініціалізована: %s", DB_PATH)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Порядок важливий: admin і checkout мають стани FSM, які мають опрацьовуватись
    # раніше за загальні текстові хендлери в catalog/common.
    dp.include_router(admin.router)
    dp.include_router(checkout.router)
    dp.include_router(cart.router)
    dp.include_router(catalog.router)
    dp.include_router(common.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await check_admin_chat(bot, logger)
    logger.info("Бот запускається (polling)...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
