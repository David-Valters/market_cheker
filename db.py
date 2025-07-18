import sqlite3
from typing import List, Optional
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

DB_PATH = "base.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Створити таблицю, якщо її ще немає
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skin_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            price REAL,
            last_updated TEXT,
            icon_url TEXT
        )
    """)
    #table set token
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS top_lots (
            skin_id TEXT PRIMARY KEY,
            lot_ids TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    # Перевірити, чи таблиця порожня
    cursor.execute("SELECT COUNT(*) FROM skins")
    count = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    
    if count == 0:
        return True

#set token
def set_token(token: str):
    logger.info(f"Setting new token.")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ("mrkt_token", token))
    conn.commit()
    conn.close()

def get_token() -> Optional[str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = ?", ("mrkt_token",))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return None

def add_skin(skin_id: str, name: str, price: float, icon_url: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO skins (skin_id, name, price, last_updated, icon_url)
        VALUES (?, ?, ?, ?, ?)
    """, (skin_id, name, price, datetime.now().isoformat(), icon_url))
    conn.commit()
    conn.close()

def remove_skin(skin_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM skins WHERE skin_id = ?", (skin_id,))
    conn.commit()
    conn.close()

def get_next_skin_to_check() -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT skin_id, name, price, last_updated, icon_url
        FROM skins
        ORDER BY last_updated ASC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "skin_id": row[0],
            "name": row[1],
            "price": row[2],
            "last_updated": row[3],
            "icon_url": row[4]
        }
    return None

def mark_skin_checked(skin_id: str, new_price: Optional[float] = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if new_price is not None:
        cursor.execute("""
            UPDATE skins SET price = ?, last_updated = ?
            WHERE skin_id = ?
        """, (new_price, datetime.now().isoformat(), skin_id))
    else:
        cursor.execute("""
            UPDATE skins SET last_updated = ?
            WHERE skin_id = ?
        """, (datetime.now().isoformat(), skin_id))

    conn.commit()
    conn.close()

def get_skin(skin_id: str) -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT skin_id, name, price, last_updated, icon_url FROM skins WHERE skin_id = ?", (skin_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "skin_id": row[0],
            "name": row[1],
            "price": row[2],
            "last_updated": row[3],
            "icon_url": row[4]
        }
    return None

def save_top_lots(skin_id: str, lot_ids: list[str]):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    lot_ids_json = json.dumps(lot_ids)
    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT OR REPLACE INTO top_lots (skin_id, lot_ids, updated_at)
        VALUES (?, ?, ?)
    """, (skin_id, lot_ids_json, now))

    conn.commit()
    conn.close()

def get_top_lots(skin_id: str) -> list[str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT lot_ids FROM top_lots WHERE skin_id = ?", (skin_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        return json.loads(row[0])
    return []


def set_feed_cursor(feed_cursor: str):
    logger.info(f"Setting new cursor: {feed_cursor}.")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", ("mrkt_cursor", feed_cursor))
    conn.commit()
    conn.close()

def get_feed_cursor() -> Optional[str]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM config WHERE key = ?", ("mrkt_cursor",))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0]
    return None