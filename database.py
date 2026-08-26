"""
Персистентне сховище на SQLite (через aiosqlite).

Раніше кошик жив тільки в MemoryStorage і зникав при перезапуску бота.
Тепер кошик, користувачі та замовлення зберігаються на диску.
"""
import aiosqlite
from datetime import datetime

_DB_PATH = "aquafrank.db"


async def init_db(path: str = "aquafrank.db") -> None:
    global _DB_PATH
    _DB_PATH = path
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                first_seen TEXT,
                last_seen TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cart_items (
                user_id INTEGER NOT NULL,
                item_id TEXT NOT NULL,
                qty INTEGER NOT NULL,
                PRIMARY KEY (user_id, item_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                order_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT,
                phone TEXT,
                address TEXT,
                payment_method TEXT,
                items_text TEXT,
                total_sum INTEGER,
                status TEXT DEFAULT 'new',
                created_at TEXT
            )
        """)
        await db.commit()


async def register_user(user_id: int, username: str | None, full_name: str) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (user_id, username, full_name, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                full_name=excluded.full_name,
                last_seen=excluded.last_seen
            """,
            (user_id, username, full_name, now, now),
        )
        await db.commit()


async def get_cart(user_id: int) -> dict:
    async with aiosqlite.connect(_DB_PATH) as db:
        cursor = await db.execute("SELECT item_id, qty FROM cart_items WHERE user_id=?", (user_id,))
        rows = await cursor.fetchall()
        return {item_id: qty for item_id, qty in rows}


async def add_to_cart(user_id: int, item_id: str, qty: int) -> None:
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO cart_items (user_id, item_id, qty) VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_id) DO UPDATE SET qty = qty + excluded.qty
            """,
            (user_id, item_id, qty),
        )
        await db.commit()


async def set_cart_qty(user_id: int, item_id: str, qty: int) -> None:
    async with aiosqlite.connect(_DB_PATH) as db:
        if qty <= 0:
            await db.execute("DELETE FROM cart_items WHERE user_id=? AND item_id=?", (user_id, item_id))
        else:
            await db.execute(
                """
                INSERT INTO cart_items (user_id, item_id, qty) VALUES (?, ?, ?)
                ON CONFLICT(user_id, item_id) DO UPDATE SET qty = excluded.qty
                """,
                (user_id, item_id, qty),
            )
        await db.commit()


async def decrement_cart_item(user_id: int, item_id: str) -> None:
    async with aiosqlite.connect(_DB_PATH) as db:
        cursor = await db.execute("SELECT qty FROM cart_items WHERE user_id=? AND item_id=?", (user_id, item_id))
        row = await cursor.fetchone()
        if not row:
            return
        qty = row[0] - 1
        if qty <= 0:
            await db.execute("DELETE FROM cart_items WHERE user_id=? AND item_id=?", (user_id, item_id))
        else:
            await db.execute("UPDATE cart_items SET qty=? WHERE user_id=? AND item_id=?", (qty, user_id, item_id))
        await db.commit()


async def clear_cart(user_id: int) -> None:
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute("DELETE FROM cart_items WHERE user_id=?", (user_id,))
        await db.commit()


async def save_order(
    user_id: int,
    username: str | None,
    full_name: str,
    phone: str,
    address: str,
    payment_method: str,
    items_text: str,
    total_sum: int,
) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    async with aiosqlite.connect(_DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO orders
                (user_id, username, full_name, phone, address, payment_method, items_text, total_sum, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'new', ?)
            """,
            (user_id, username, full_name, phone, address, payment_method, items_text, total_sum, now),
        )
        await db.commit()
        return cursor.lastrowid


async def get_user_orders(user_id: int, limit: int = 10) -> list:
    async with aiosqlite.connect(_DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT order_id, items_text, total_sum, status, created_at
            FROM orders WHERE user_id=? ORDER BY order_id DESC LIMIT ?
            """,
            (user_id, limit),
        )
        return await cursor.fetchall()


async def has_previous_orders(user_id: int) -> bool:
    """Чи є в користувача хоча б одне попереднє замовлення (для акції для нових клієнтів)."""
    async with aiosqlite.connect(_DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM orders WHERE user_id=? LIMIT 1", (user_id,))
        row = await cursor.fetchone()
        return row is not None


async def get_pending_orders(limit: int = 20) -> list:
    async with aiosqlite.connect(_DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT order_id, user_id, username, full_name, phone, address, payment_method,
                   items_text, total_sum, created_at
            FROM orders WHERE status='new' ORDER BY order_id ASC LIMIT ?
            """,
            (limit,),
        )
        return await cursor.fetchall()


async def update_order_status(order_id: int, status: str) -> None:
    async with aiosqlite.connect(_DB_PATH) as db:
        await db.execute("UPDATE orders SET status=? WHERE order_id=?", (status, order_id))
        await db.commit()


async def get_stats() -> dict:
    async with aiosqlite.connect(_DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*), COALESCE(SUM(total_sum),0) FROM orders WHERE status != 'cancelled'")
        total_orders, total_revenue = await cursor.fetchone()
        cursor = await db.execute("SELECT COUNT(*) FROM orders WHERE status='new'")
        pending = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        return {
            "orders": total_orders,
            "revenue": total_revenue,
            "pending": pending,
            "users": total_users,
        }


async def list_all_user_ids() -> list:
    async with aiosqlite.connect(_DB_PATH) as db:
        cursor = await db.execute("SELECT user_id FROM users")
        rows = await cursor.fetchall()
        return [r[0] for r in rows]
