from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import types

from catalog import CATEGORIES


def main_menu() -> types.ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    for label in CATEGORIES.values():
        kb.button(text=label)
    kb.button(text="🛒 Кошик")
    kb.button(text="📦 Мої замовлення")
    kb.button(text="ℹ️ Інформація")
    kb.adjust(2, 1, 2, 1)
    return kb.as_markup(resize_keyboard=True)


def quantity_keyboard(item_id: str) -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✏️ Ввести кількість", callback_data=f"manualqty_{item_id}")
    kb.adjust(1)
    return kb.as_markup()


def cancel_manual_qty_keyboard() -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Скасувати", callback_data="cancel_manual_qty")
    return kb.as_markup()


def cart_keyboard(cart: dict, catalog: dict) -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item_id, qty in cart.items():
        name = catalog[item_id]["name"]
        short = name if len(name) <= 22 else name[:22] + "…"
        kb.button(text="➖", callback_data=f"dec_{item_id}")
        kb.button(text=f"{short} × {qty}", callback_data="noop")
        kb.button(text="➕", callback_data=f"inc_{item_id}")
    kb.adjust(*([3] * len(cart)))
    kb.row(types.InlineKeyboardButton(text="✅ Оформити замовлення", callback_data="checkout"))
    kb.row(types.InlineKeyboardButton(text="🗑 Очистити кошик", callback_data="clear_cart"))
    return kb.as_markup()


def exchange_keyboard() -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Так, є тара на обмін", callback_data="exchange_yes")
    kb.button(text="Ні, потрібен новий бутель (+застава)", callback_data="exchange_no")
    kb.adjust(1)
    return kb.as_markup()


def phone_request_keyboard() -> types.ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="📲 Надіслати контакт", request_contact=True)
    kb.button(text="❌ Скасувати замовлення")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True, one_time_keyboard=True)


def payment_keyboard() -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💵 Готівкою", callback_data="pay_cash")
    kb.button(text="💳 Карткою (переказ)", callback_data="pay_card")
    kb.adjust(1)
    return kb.as_markup()


def confirm_keyboard() -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Підтвердити", callback_data="confirm_order")
    kb.button(text="❌ Скасувати", callback_data="cancel_order")
    kb.adjust(1)
    return kb.as_markup()


def admin_menu() -> types.ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="📥 Нові замовлення")
    kb.button(text="📊 Статистика")
    kb.button(text="📣 Розсилка")
    kb.button(text="⬅️ Вийти з адмінки")
    kb.adjust(2, 1, 1)
    return kb.as_markup(resize_keyboard=True)


def order_done_keyboard(order_id: int) -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Позначити виконаним", callback_data=f"done_{order_id}")
    return kb.as_markup()
