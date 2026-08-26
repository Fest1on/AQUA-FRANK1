from aiogram import Router, F, types
from aiogram.filters import CommandStart

import database as db
import keyboards as kb

router = Router(name="common")


@router.message(CommandStart())
async def start_cmd(message: types.Message):
    await db.register_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    welcome_text = (
        "💧 <b>Aqua Frank — доставка питної води 18,9 л</b>\n\n"
        "🚚 Безкоштовна доставка по Івано-Франківську\n"
        "💧 Якісна вода для дому та офісу\n"
        "📦 Зручне замовлення через бот\n\n"
        "👇 <b>Обирайте категорію товарів:</b>"
    )
    await message.answer(welcome_text, reply_markup=kb.main_menu())


@router.message(F.text == "ℹ️ Інформація")
async def info_cmd(message: types.Message):
    info_text = (
        "💧 <b>Інформація про воду Aqua Frank</b>\n\n"
        "Aqua Frank — питна вода у бутлях 18,9 л, очищена та підготовлена для щоденного вживання.\n\n"
        "🔹 Багатоступенева система очищення\n"
        "🔹 Контроль якості\n"
        "🔹 Безкоштовна доставка по Івано-Франківську та околицях\n\n"
        "📞 <b>Менеджер:</b> 0969724183, 0995462910\n\n"
        '📸 <a href="https://www.instagram.com/aquafrank.if/">Наш Інстаграм</a>'
    )
    await message.answer(info_text, disable_web_page_preview=True)


@router.message(F.text == "📦 Мої замовлення")
async def my_orders(message: types.Message):
    orders = await db.get_user_orders(message.from_user.id)
    if not orders:
        await message.answer("У вас ще немає замовлень.")
        return

    status_labels = {"new": "🕓 в обробці", "done": "✅ виконано", "cancelled": "❌ скасовано"}
    lines = ["📦 <b>Ваші останні замовлення:</b>\n"]
    for order_id, items_text, total_sum, status, created_at in orders:
        label = status_labels.get(status, status)
        lines.append(f"<b>№{order_id}</b> від {created_at} — {label}\n{items_text}Сума: {total_sum} грн\n")
    await message.answer("\n".join(lines))
