import sqlite3
from typing import List, Optional
from datetime import datetime
import logging
from datetime import timedelta
from models import Lot

logger = logging.getLogger(__name__)

DB_PATH = "base.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Створити таблицю, якщо її ще немає
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS skins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skin_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            price REAL,
            last_updated TEXT,
            icon_url TEXT
        )
    """
    )
    # table set token
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """
    )
    # Перевірити, чи таблиця порожня
    cursor.execute("SELECT COUNT(*) FROM skins")
    count = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    if count == 0:
        return True


# set token
def set_token(token: str):
    logger.info("Setting new token.")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
        ("mrkt_token", token),
    )
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
    cursor.execute(
        """
        INSERT OR REPLACE INTO skins (skin_id, name, price, last_updated, icon_url)
        VALUES (?, ?, ?, ?, ?)
    """,
        (skin_id, name, price, datetime.now().isoformat(), icon_url),
    )
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
    cursor.execute(
        """
        SELECT skin_id, name, price, last_updated, icon_url
        FROM skins
        ORDER BY last_updated ASC
        LIMIT 1
    """
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "skin_id": row[0],
            "name": row[1],
            "price": row[2],
            "last_updated": row[3],
            "icon_url": row[4],
        }
    return None


def mark_skin_checked(skin_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE skins SET last_updated = ?
        WHERE skin_id = ?
    """,
        (datetime.now().isoformat(), skin_id),
    )

    conn.commit()
    conn.close()


def get_skin(skin_id: str) -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT skin_id, name, price, last_updated, icon_url FROM skins WHERE skin_id = ?",
        (skin_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "skin_id": row[0],
            "name": row[1],
            "price": row[2],
            "last_updated": row[3],
            "icon_url": row[4],
        }
    return None

def get_oldest_skins(delta: timedelta) -> List[dict]:
    threshold_time = (datetime.now() - delta).isoformat()

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT skin_id, name, price, last_updated, icon_url
        FROM skins
        WHERE last_updated < ?
        ORDER BY last_updated ASC
    """, (threshold_time,))
    rows = cursor.fetchall()
    conn.close()

    skins = []
    for row in rows:
        skins.append({
            "skin_id": row[0],
            "name": row[1],
            "price": row[2],
            "last_updated": row[3],
            "icon_url": row[4],
        })
    return skins
        
def get_all_skins() -> List[dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT skin_id, name, price, last_updated, icon_url FROM skins")
    rows = cursor.fetchall()
    conn.close()

    skins = []
    for row in rows:
        skins.append(
            {
                "skin_id": row[0],
                "name": row[1],
                "price": row[2],
                "last_updated": row[3],
                "icon_url": row[4],
            }
        )
    return skins


def update_lots(skin_id: str, lots: list[dict]):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM lots WHERE skin_id = ?", (skin_id,))

    for lot in lots:
        cursor.execute(
            """
            INSERT OR REPLACE INTO lots (lot_id, skin_id, price, serial)
            VALUES (?, ?, ?, ?)
        """,
            (lot["id"], skin_id, lot["salePrice"], lot["serial"]),
        )

    conn.commit()
    conn.close()


def get_top_lots(skin_id: str) -> list[Lot]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lots WHERE skin_id = ? ORDER BY price", (skin_id,))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return []

    column_names = [desc[0] for desc in cursor.description]
    return [Lot(**dict(zip(column_names, row))) for row in rows]


def set_feed_cursor(feed_cursor: str):
    logger.info(f"Setting new cursor: {feed_cursor}.")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
        ("mrkt_cursor", feed_cursor),
    )
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


from alembic.config import Config
from alembic import command


def run_migrations():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
