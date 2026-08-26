"""
Обгортка над Google Sheets. Якщо бібліотеки не встановлені, файл credentials.json
відсутній, або немає доступу до таблиці — бот просто пише попередження в лог
і продовжує працювати далі. Замовлення НІКОЛИ не губиться через Sheets:
воно вже збережене в SQLite (database.py) до виклику цієї функції.
"""
import logging

from config import GOOGLE_SHEETS_JSON, SPREADSHEET_NAME

logger = logging.getLogger(__name__)

_sheet = None
_sheets_checked = False


def _get_sheet():
    global _sheet, _sheets_checked
    if _sheets_checked:
        return _sheet
    _sheets_checked = True

    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
    except ImportError:
        logger.warning("gspread/oauth2client не встановлені — запис у Google Таблиці вимкнено.")
        return None

    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEETS_JSON, scope)
        client = gspread.authorize(creds)
        _sheet = client.open(SPREADSHEET_NAME).sheet1
        logger.info("Підключення до Google Sheets успішне.")
    except Exception:
        logger.exception("Не вдалося підключитись до Google Sheets (перевірте credentials.json і доступ).")
        _sheet = None

    return _sheet


def safe_append_row(row: list) -> None:
    sheet = _get_sheet()
    if not sheet:
        return
    try:
        sheet.append_row(row)
    except Exception:
        logger.exception("Не вдалося записати рядок у Google Таблицю.")
