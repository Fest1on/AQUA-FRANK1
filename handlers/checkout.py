import html
import re
import logging
from datetime import datetime

from aiogram import Router, F, types, Bot
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from catalog import CATALOG, item_line, BOTTLE_DEPOSIT
from states import OrderProcess
from config import ADMIN_CHAT_ID
from sheets import safe_append_row

router = Router(name="checkout")
logger = logging.getLogger(__name__)

PHONE_RE = re.compile(r"^\+?3?8?0\d{9}$|^\+?\d{9,15}$")


async def build_order_lines(user_id: int, cart: dict, has_exchange: bool) -> tuple[str, int]:
    is_new_customer = not await db.has_previous_orders(user_id)

    total_sum = 0
    lines = ""
    for item_id, qty in cart.items():
        item = CATALOG[item_id]
        item_total, note = item_line(item_id, qty, is_new_customer)
        total_sum += item_total
        lines += f"• {html.escape(item['name'])} × {qty} = {item_total} грн{note}\n"

    if "water_189" in cart and not has_exchange:
        bottle_qty = cart["water_189"]
        bottle_cost = bottle_qty * BOTTLE_DEPOSIT
        total_sum += bottle_cost
        lines += f"• Застава за новий бутель 18,9 л × {bottle_qty} = {bottle_cost} грн\n"

    return lines, total_sum


@router.callback_query(F.data == "checkout")
async def start_checkout(callback: types.CallbackQuery, state: FSMContext):
    cart = await db.get_cart(callback.from_user.id)
    if not cart:
        await callback.answer("Кошик порожній!")
        return

    await callback.answer()
    await callback.message.answer("Як до вас звертатись? Введіть, будь ласка, ваше ім'я:")
    await state.set_state(OrderProcess.waiting_for_name)


@router.message(OrderProcess.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Будь ласка, вкажіть ім'я (мінімум 2 символи).")
        return

    await state.update_data(customer_name=name)
    cart = await db.get_cart(message.from_user.id)

    if "water_189" in cart:
        await message.answer(
            "💧 Ви замовляєте бутлі 18,9 л.\nЧи маєте ви пусту тару на обмін?",
            reply_markup=kb.exchange_keyboard(),
        )
        await state.set_state(OrderProcess.waiting_for_bottle_exchange)
    else:
        await state.update_data(has_exchange=True)
        await ask_phone(message, state)


@router.callback_query(OrderProcess.waiting_for_bottle_exchange)
async def process_exchange(callback: types.CallbackQuery, state: FSMContext):
    has_exchange = callback.data == "exchange_yes"
    await state.update_data(has_exchange=has_exchange)
    await callback.answer()
    await ask_phone(callback.message, state)


async def ask_phone(message: types.Message, state: FSMContext):
    await message.answer(
        "Надішліть ваш номер телефону кнопкою нижче або введіть його вручну "
        "(наприклад, +380971234567):",
        reply_markup=kb.phone_request_keyboard(),
    )
    await state.set_state(OrderProcess.waiting_for_phone)


@router.message(F.text == "❌ Скасувати замовлення")
async def cancel_anywhere(message: types.Message, state: FSMContext):
    current = await state.get_state()
    if current is None:
        return
    await state.clear()
    await message.answer("❌ Оформлення замовлення скасовано.", reply_markup=kb.main_menu())


@router.message(OrderProcess.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else (message.text or "").strip()
    cleaned = phone.replace(" ", "").replace("-", "")
    if not PHONE_RE.match(cleaned):
        await message.answer(
            "Схоже, номер введено некоректно. Спробуйте ще раз, наприклад: +380971234567",
            reply_markup=kb.phone_request_keyboard(),
        )
        return

    await state.update_data(phone=cleaned)
    await message.answer(
        "Введіть адресу доставки (вулиця, будинок, квартира/офіс):",
        reply_markup=types.ReplyKeyboardRemove(),
    )
    await state.set_state(OrderProcess.waiting_for_address)


@router.message(OrderProcess.waiting_for_address)
async def process_address(message: types.Message, state: FSMContext):
    address = (message.text or "").strip()
    if len(address) < 5:
        await message.answer("Адреса виглядає закороткою. Вкажіть, будь ласка, вулицю та номер будинку.")
        return

    await state.update_data(address=address)
    await message.answer("Оберіть спосіб оплати:", reply_markup=kb.payment_keyboard())
    await state.set_state(OrderProcess.waiting_for_payment)


@router.callback_query(OrderProcess.waiting_for_payment)
async def process_payment(callback: types.CallbackQuery, state: FSMContext):
    payment_method = "Готівка" if callback.data == "pay_cash" else "Переказ на картку"
    await state.update_data(payment_method=payment_method)

    data = await state.get_data()
    cart = await db.get_cart(callback.from_user.id)
    has_exchange = data.get("has_exchange", True)
    order_items_text, total_sum = await build_order_lines(callback.from_user.id, cart, has_exchange)

    confirm_text = (
        "🧾 <b>Фінальний чек:</b>\n\n"
        f"👤 <b>Ім'я:</b> {html.escape(data['customer_name'])}\n"
        f"📱 <b>Телефон:</b> {html.escape(data['phone'])}\n"
        f"📍 <b>Адреса:</b> {html.escape(data['address'])}\n"
        f"💳 <b>Оплата:</b> {payment_method}\n\n"
        f"🛍 <b>Склад замовлення:</b>\n{order_items_text}\n"
        f"💰 <b>Разом до сплати:</b> {total_sum} грн"
    )

    await state.update_data(total_sum=total_sum, order_items_text=order_items_text)
    await state.set_state(OrderProcess.waiting_for_confirmation)
    await callback.answer()
    await callback.message.edit_text(confirm_text, reply_markup=kb.confirm_keyboard())


@router.callback_query(F.data == "confirm_order", OrderProcess.waiting_for_confirmation)
async def finish_order(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user = callback.from_user

    order_id = await db.save_order(
        user_id=user.id,
        username=user.username,
        full_name=data["customer_name"],
        phone=data["phone"],
        address=data["address"],
        payment_method=data["payment_method"],
        items_text=data["order_items_text"],
        total_sum=data["total_sum"],
    )
    await db.clear_cart(user.id)

    admin_card = (
        f"🔔 <b>НОВЕ ЗАМОВЛЕННЯ №{order_id}!</b>\n\n"
        f"👤 <b>Клієнт:</b> {html.escape(data['customer_name'])} "
        f"(@{html.escape(user.username) if user.username else 'немає'})\n"
        f"📞 <b>Телефон:</b> {html.escape(data['phone'])}\n"
        f"📍 <b>Адреса:</b> {html.escape(data['address'])}\n"
        f"💳 <b>Оплата:</b> {data['payment_method']}\n\n"
        f"📦 <b>Замовлення:</b>\n{data['order_items_text']}\n"
        f"💵 <b>СУМА:</b> {data['total_sum']} грн"
    )

    if ADMIN_CHAT_ID:
        try:
            await bot.send_message(
                chat_id=ADMIN_CHAT_ID, text=admin_card, reply_markup=kb.order_done_keyboard(order_id)
            )
        except Exception:
            logger.exception("Не вдалося надіслати повідомлення в адмін-чат")

    safe_append_row(
        [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            str(order_id),
            str(user.id),
            data["phone"],
            data["address"],
            data["order_items_text"].replace("\n", " | "),
            data["total_sum"],
            data["payment_method"],
        ]
    )

    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        f"🎉 <b>Дякуємо! Замовлення №{order_id} прийнято.</b>\nНаш менеджер зв'яжеться з вами найближчим часом."
    )
    await callback.message.answer("Обирайте товари в меню:", reply_markup=kb.main_menu())


@router.callback_query(F.data == "cancel_order", OrderProcess.waiting_for_confirmation)
async def cancel_order(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.edit_text("❌ Замовлення скасовано.")
    await callback.message.answer("Обирайте товари в меню:", reply_markup=kb.main_menu())
