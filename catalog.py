"""
Каталог товарів. Винесено в окремий модуль, щоб легко редагувати
асортимент, не чіпаючи логіку бота.
"""
import os

# Абсолютний шлях до папки з фото. Використовуємо розташування ЦЬОГО файлу,
# а не поточну робочу директорію — тоді фото знаходяться незалежно від того,
# звідки саме запущено `python bot.py` (ярлик, IDE, планувальник задач тощо).
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_PHOTOS_DIR = os.path.join(_BASE_DIR, "photos")


def _photo(filename: str) -> str:
    return os.path.join(_PHOTOS_DIR, filename)


CATEGORIES = {
    "water": "💧 Вода Aqua Frank 18.9л",
    "morsh": "⛰ Вода Моршинська",
    "accessory": "🔌 Помпи та Аксесуари",
}

CATALOG = {
    # Вода 18.9 л (основна позиція)
    "water_189": {"name": "Вода Aqua Frank 18,9л", "price": 140, "category": "water", "photo": _photo("water_189.jpg")},

    # Помпи та супутні товари
    "pump_el": {"name": "Помпа електрична PRIMO", "price": 270, "category": "accessory", "photo": _photo("p_el.jpg")},
    "pump_mech": {"name": "Помпа механічна Lilu", "price": 200, "category": "accessory", "photo": _photo("p_mech.jpg")},
    "handle": {"name": "Ручка для перенесення VIAPLAST", "price": 90, "category": "accessory", "photo": _photo("rucha.jpg")},
    "cups": {"name": "Стакан паперовий 250мл (50 шт)", "price": 65, "category": "accessory", "photo": _photo("stakan.jpg")},

    # Моршинська
    "msh_1_5_sg": {"name": "Моршинська слабогаз 1,5л × 6", "price": 200, "category": "morsh", "photo": _photo("m15_sl.jpg")},
    "msh_1_5_g": {"name": "Моршинська сильногаз 1,5л × 6", "price": 200, "category": "morsh", "photo": _photo("m15_sil.jpg")},
    "msh_1_5_ng": {"name": "Моршинська негаз 1,5л × 6", "price": 200, "category": "morsh", "photo": _photo("m15_neg.jpg")},
    "msh_0_75_ng": {"name": "Моршинська негаз 0,75л × 12", "price": 300, "category": "morsh", "photo": _photo("m075_neg.jpg")},
    "msh_0_75_sg": {"name": "Моршинська слабогаз 0,75л × 12", "price": 300, "category": "morsh", "photo": _photo("m075_sl.jpg")},
    "msh_0_75_sport": {"name": "Моршинська Sport 0,75л × 12", "price": 365, "category": "morsh", "photo": _photo("m_sport.jpg")},
    "msh_0_5_sg": {"name": "Моршинська слабогаз 0,5л × 12", "price": 275, "category": "morsh", "photo": _photo("m05_sl.jpg")},
    "msh_0_5_ng": {"name": "Моршинська негаз 0,5л × 12", "price": 275, "category": "morsh", "photo": _photo("m05_neg.jpg")},
    "msh_6_ng": {"name": "Моршинська негаз 6л × 2 шт", "price": 210, "category": "morsh", "photo": _photo("m6.jpg")},
}

# Проста система знижок при оптовому замовленні: item_id -> {поріг кількості: знижка за од., грн}
BULK_DISCOUNTS = {
    "water_189": {5: 5, 10: 15},   # 5+ бутлів -5грн/шт, 10+ бутлів -15грн/шт
}

BOTTLE_DEPOSIT = 400  # застава за новий бутель, якщо немає тари на обмін
BOTTLE_EXCHANGE_PRICE = 0  # додаткова доплата не потрібна, якщо є тара на обмін

# Акція для НОВИХ клієнтів: рівно 2 бутлі води 18,9 л за фіксовану суму.
# Діє тільки при першому замовленні (перевіряється в database.has_previous_orders)
# і тільки якщо в кошику РІВНО стільки бутлів, скільки вказано в required_qty.
NEW_CUSTOMER_PROMO = {
    "item_id": "water_189",
    "required_qty": 2,
    "promo_total": 200,  # разом за 2 шт (замість 140 × 2 = 280 грн)
}


def get_items_by_category(category_code: str) -> dict:
    return {k: v for k, v in CATALOG.items() if v["category"] == category_code}


def unit_price(item_id: str, qty: int) -> int:
    """Повертає ціну за одиницю товару з урахуванням оптової знижки."""
    base = CATALOG[item_id]["price"]
    discount = 0
    for threshold, disc in BULK_DISCOUNTS.get(item_id, {}).items():
        if qty >= threshold and disc > discount:
            discount = disc
    return max(base - discount, 0)


def line_total(item_id: str, qty: int) -> int:
    return unit_price(item_id, qty) * qty


def promo_applies(item_id: str, qty: int, is_new_customer: bool) -> bool:
    """Чи застосовується акція для нових клієнтів до цієї позиції кошика."""
    promo = NEW_CUSTOMER_PROMO
    return is_new_customer and item_id == promo["item_id"] and qty == promo["required_qty"]


def promo_savings() -> int:
    promo = NEW_CUSTOMER_PROMO
    regular = CATALOG[promo["item_id"]]["price"] * promo["required_qty"]
    return regular - promo["promo_total"]


def item_line(item_id: str, qty: int, is_new_customer: bool) -> tuple[int, str]:
    """
    Повертає (сума за позицію, приписка для чека) з урахуванням акції для нових
    клієнтів (має пріоритет над оптовою знижкою, якщо застосовується).
    """
    if promo_applies(item_id, qty, is_new_customer):
        promo = NEW_CUSTOMER_PROMO
        note = f" 🎉 Акція для нових клієнтів (знижка {promo_savings()} грн)"
        return promo["promo_total"], note

    total = line_total(item_id, qty)
    note = ""
    if unit_price(item_id, qty) != CATALOG[item_id]["price"]:
        note = f" (знижка: {unit_price(item_id, qty)} грн/шт)"
    return total, note
