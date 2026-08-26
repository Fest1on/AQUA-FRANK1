import asyncio
import html
import os
import logging

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from catalog import CATALOG, CATEGORIES, get_items_by_category, NEW_CUSTOMER_PROMO, promo_savings
from states import OrderProcess

router = Router(name="catalog")
logger = logging.getLogger(__name__)


async def show_category_items(message: types.Message, category_code: str):
    items = get_items_by_category(category_code)
    if not items:
        await message.answer("Наразі товарів у цій категорії немає.")
        return

    is_new_customer = not await db.has_previous_orders(message.from_user.id)
    promo = NEW_CUSTOMER_PROMO

    for item_id, data in items.items():
        caption = f"🛍 <b>{html.escape(data['name'])}</b>\n💰 Ціна: {data['price']} грн"
        if is_new_customer and item_id == promo["item_id"]:
            caption += (
                f"\n\n🎁 <b>Акція для нових клієнтів:</b> {promo['required_qty']} шт за "
                f"{promo['promo_total']} грн (звичайна ціна — "
                f"{data['price'] * promo['required_qty']} грн, знижка {promo_savings()} грн)!\n"
                f"Діє тільки на перше замовлення рівно {promo['required_qty']} шт."
            )
        photo = data["photo"]
        try:
            if os.path.exists(photo):
                # Локальний файл на диску (перевіряємо реальну наявність,
                # а не довжину рядка — абсолютні шляхи легко довші за 50 символів).
                file = types.FSInputFile(photo)
                await message.answer_photo(
                    photo=file, caption=caption, reply_markup=kb.quantity_keyboard(item_id)
                )
            else:
                # Посилання (http...) або вже завантажений Telegram file_id.
                await message.answer_photo(
                    photo=photo, caption=caption, reply_markup=kb.quantity_keyboard(item_id)
                )
        except Exception:
            logger.exception("Не вдалося надіслати фото для товару %s (шлях: %s)", item_id, photo)
            await message.answer(
                f"{caption}\n<i>(🖼 Фото тимчасово недоступне)</i>",
                reply_markup=kb.quantity_keyboard(item_id),
            )
        await asyncio.sleep(0.2)


for code, label in CATEGORIES.items():

    def _make_handler(cat_code):
        async def _handler(message: types.Message):
            await show_category_items(message, cat_code)

        return _handler

    router.message.register(_make_handler(code), F.text == label)


@router.callback_query(F.data.startswith("manualqty_"))
async def manual_qty_start(callback: types.CallbackQuery, state: FSMContext):
    item_id = callback.data.split("_", 1)[1]
    await state.update_data(manual_item_id=item_id)
    await state.set_state(OrderProcess.waiting_for_manual_qty)
    await callback.answer()
    await callback.message.answer(
        f"Введіть потрібну кількість для «{CATALOG[item_id]['name']}» (число від 1 до 99):",
        reply_markup=kb.cancel_manual_qty_keyboard(),
    )


@router.callback_query(F.data == "cancel_manual_qty", OrderProcess.waiting_for_manual_qty)
async def manual_qty_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Скасовано")
    await callback.message.answer("Гаразд, кількість не змінено.")


@router.message(OrderProcess.waiting_for_manual_qty)
async def manual_qty_receive(message: types.Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text.isdigit() or not (1 <= int(text) <= 99):
        await message.answer(
            "Будь ласка, введіть ціле число від 1 до 99.",
            reply_markup=kb.cancel_manual_qty_keyboard(),
        )
        return

    data = await state.get_data()
    item_id = data.get("manual_item_id")
    quantity = int(text)
    await db.add_to_cart(message.from_user.id, item_id, quantity)
    await state.clear()
    await message.answer(f"✅ Додано {quantity} шт. — {CATALOG[item_id]['name']}")
