"""
Конфігурація бота. Всі секрети беруться зі змінних середовища (.env),
а не хардкодяться в коді — це дозволяє безпечно тримати код у git.
"""
import os
import sys
from dotenv import load_dotenv

# На Windows консоль часто не вміє виводити emoji (⚠️, ✅ тощо) в стандартній
# кодовій сторінці — через це print() може падати з помилкою або обривати
# скрипт. Примусово перемикаємо stdout/stderr на UTF-8 з заміною символів,
# яких немає в шрифті консолі, замість краху.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

load_dotenv()


def _get_admin_ids(raw: str) -> list[int]:
    ids = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() or (part.startswith("-") and part[1:].isdigit()):
            ids.append(int(part))
    return ids


BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()
ADMIN_USER_IDS = _get_admin_ids(os.getenv("ADMIN_USER_IDS", ""))

GOOGLE_SHEETS_JSON = os.getenv("GOOGLE_SHEETS_JSON", "credentials.json").strip()
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME", "Aqua Frank Orders").strip()

DB_PATH = os.getenv("DB_PATH", "aquafrank.db").strip()

if not BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не заданий. Скопіюйте .env.example у .env і впишіть токен бота від @BotFather."
    )

if not ADMIN_CHAT_ID:
    print("⚠️ ADMIN_CHAT_ID не заданий — сповіщення про нові замовлення надсилатись не будуть.")

if not ADMIN_USER_IDS:
    print("⚠️ ADMIN_USER_IDS не заданий — команда /admin буде недоступна нікому.")
