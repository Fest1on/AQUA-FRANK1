import asyncio
import html
import logging

from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from config import ADMIN_USER_IDS
from states import AdminProcess

router = Router(name="admin")
logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS


@router.message(Command("admin"))
async def admin_entry(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🔑 Адмін-панель Aqua Frank", reply_markup=kb.admin_menu())


@router.message(F.text == "⬅️ Вийти з адмінки")
async def admin_exit(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Вихід з адмінки.", reply_markup=kb.main_menu())


@router.message(F.text == "📥 Нові замовлення")
async def pending_orders(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    orders = await db.get_pending_orders()
    if not orders:
        await message.answer("Немає нових замовлень 🎉")
        return

    for order_id, user_id, username, full_name, phone, address, payment_method, items_text, total_sum, created_at in orders:
        text = (
            f"🔔 <b>Замовлення №{order_id}</b> ({created_at})\n\n"
            f"👤 {html.escape(full_name)} (@{html.escape(username) if username else 'немає'})\n"
            f"📞 {html.escape(phone)}\n"
            f"📍 {html.escape(address)}\n"
            f"💳 {payment_method}\n\n"
            f"{items_text}\n💵 <b>{total_sum} грн</b>"
        )
        await message.answer(text, reply_markup=kb.order_done_keyboard(order_id))
        await asyncio.sleep(0.1)


@router.callback_query(F.data.startswith("done_"))
async def mark_order_done(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Немає доступу", show_alert=True)
        return
    order_id = int(callback.data.split("_", 1)[1])
    await db.update_order_status(order_id, "done")
    await callback.answer("Позначено виконаним ✅")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass


@router.message(F.text == "📊 Статистика")
async def stats(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    data = await db.get_stats()
    text = (
        "📊 <b>Статистика Aqua Frank</b>\n\n"
        f"👥 Користувачів: {data['users']}\n"
        f"📦 Всього замовлень: {data['orders']}\n"
        f"🕓 Очікують обробки: {data['pending']}\n"
        f"💰 Загальна виручка: {data['revenue']} грн"
    )
    await message.answer(text)


@router.message(F.text == "📣 Розсилка")
async def broadcast_start(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "Введіть текст повідомлення для розсилки всім користувачам бота "
        "(або надішліть /cancel, щоб скасувати):"
    )
    await state.set_state(AdminProcess.waiting_for_broadcast)


@router.message(Command("cancel"), AdminProcess.waiting_for_broadcast)
async def broadcast_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Розсилку скасовано.", reply_markup=kb.admin_menu())


@router.message(AdminProcess.waiting_for_broadcast)
async def broadcast_send(message: types.Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    text = message.text or ""
    user_ids = await db.list_all_user_ids()

    sent, failed = 0, 0
    for user_id in user_ids:
        try:
            await bot.send_message(chat_id=user_id, text=text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # обережно з лімітами Telegram

    await message.answer(f"📣 Розсилку завершено.\n✅ Надіслано: {sent}\n❌ Не вдалося: {failed}", reply_markup=kb.admin_menu())
