import html

from aiogram import Router, F, types

import database as db
import keyboards as kb
from catalog import CATALOG, item_line, NEW_CUSTOMER_PROMO, promo_savings

router = Router(name="cart")


async def build_cart_text(user_id: int, cart: dict) -> tuple[str, int]:
    is_new_customer = not await db.has_previous_orders(user_id)

    text = "🛒 <b>Ваш кошик:</b>\n\n"
    total = 0
    for item_id, qty in cart.items():
        item = CATALOG[item_id]
        item_sum, note = item_line(item_id, qty, is_new_customer)
        total += item_sum
        text += f"• {html.escape(item['name'])} × {qty} = {item_sum} грн{note}\n"

    text += f"\n💰 <b>Попередня сума:</b> {total} грн"

    if "water_189" in cart:
        text += "\n\n<i>ℹ️ Вартість бутлів уточниться при оформленні залежно від наявності тари на обмін.</i>"

    promo = NEW_CUSTOMER_PROMO
    water_qty = cart.get(promo["item_id"], 0)
    if is_new_customer and water_qty != promo["required_qty"]:
        text += (
            f"\n\n🎁 <b>Акція для нових клієнтів:</b> {promo['required_qty']} бутлі води 18,9л "
            f"за {promo['promo_total']} грн замість {CATALOG['water_189']['price'] * promo['required_qty']} грн "
            f"(знижка {promo_savings()} грн)! Діє тільки на перше замовлення."
        )

    return text, total


@router.message(F.text == "🛒 Кошик")
async def view_cart(message: types.Message):
    cart = await db.get_cart(message.from_user.id)
    if not cart:
        await message.answer("🛒 Ваш кошик порожній.")
        return
    text, _ = await build_cart_text(message.from_user.id, cart)
    await message.answer(text, reply_markup=kb.cart_keyboard(cart, CATALOG))


async def _refresh_cart_message(callback: types.CallbackQuery):
    cart = await db.get_cart(callback.from_user.id)
    if not cart:
        await callback.message.edit_text("🛒 Ваш кошик порожній.")
        return
    text, _ = await build_cart_text(callback.from_user.id, cart)
    await callback.message.edit_text(text, reply_markup=kb.cart_keyboard(cart, CATALOG))


@router.callback_query(F.data.startswith("inc_"))
async def increment_item(callback: types.CallbackQuery):
    item_id = callback.data.split("_", 1)[1]
    await db.add_to_cart(callback.from_user.id, item_id, 1)
    await callback.answer()
    await _refresh_cart_message(callback)


@router.callback_query(F.data.startswith("dec_"))
async def decrement_item(callback: types.CallbackQuery):
    item_id = callback.data.split("_", 1)[1]
    await db.decrement_cart_item(callback.from_user.id, item_id)
    await callback.answer()
    await _refresh_cart_message(callback)


@router.callback_query(F.data == "noop")
async def noop(callback: types.CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "clear_cart")
async def clear_cart(callback: types.CallbackQuery):
    await db.clear_cart(callback.from_user.id)
    await callback.answer("Кошик очищено")
    await callback.message.edit_text("🛒 Ваш кошик порожній.")
