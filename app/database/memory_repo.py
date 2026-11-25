"""
LopixAI Yerel Hafıza Deposu (memory.db)
Sohbetlerden tamamen ayrı tutulan kalıcı kullanıcı hafızası.
Kullanıcı tercihleri, öğrendiği gerçekler ve profili saklar.
"""

import time
import uuid
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from app.database.db_manager import DBManager
from app.core.logger import get_logger

logger = get_logger("MemoryRepo")

@dataclass
class MemoryItem:
    id: str
    key: str
    value: str
    category: str
    created_at: float
    updated_at: float

    @classmethod
    def from_row(cls, row) -> "MemoryItem":
        return cls(
            id=row["id"],
            key=row["key"],
            value=row["value"],
            category=row["category"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

class MemoryRepository:
    """memory.db tablosunu yöneten repo sınıfı."""

    @staticmethod
    def set_memory(key: str, value: str, category: str = "general") -> MemoryItem:
        """Hafızaya bilgi ekler veya mevcut bilgiyi günceller."""
        key = key.strip()
        value = value.strip()
        now = time.time()
        conn = DBManager.get_memory_conn()
        try:
            with conn:
                # Önce var mı bak
                cur = conn.execute("SELECT id FROM memories WHERE key = ? LIMIT 1;", (key,))
                row = cur.fetchone()
                if row:
                    item_id = row["id"]
                    conn.execute(
                        """
                        UPDATE memories
                        SET value = ?, category = ?, updated_at = ?
                        WHERE id = ?;
                        """,
                        (value, category, now, item_id)
                    )
                else:
                    item_id = str(uuid.uuid4())
                    conn.execute(
                        """
                        INSERT INTO memories (id, key, value, category, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?);
                        """,
                        (item_id, key, value, category, now, now)
                    )
            logger.info(f"Hafıza güncellendi: '{key}' -> '{value}' [{category}]")
            return MemoryItem(
                id=item_id,
                key=key,
                value=value,
                category=category,
                created_at=now,
                updated_at=now
            )
        finally:
            conn.close()

    @staticmethod
    def get_memory(key: str) -> Optional[str]:
        """Key'e karşılık gelen hafıza değerini döner."""
        conn = DBManager.get_memory_conn()
        try:
            cur = conn.execute("SELECT value FROM memories WHERE key = ? LIMIT 1;", (key.strip(),))
            row = cur.fetchone()
            return row["value"] if row else None
        finally:
            conn.close()

    @staticmethod
    def get_all_memories(category: Optional[str] = None) -> List[MemoryItem]:
        """Tüm hafıza kayıtlarını döner."""
        conn = DBManager.get_memory_conn()
        try:
            if category:
                cur = conn.execute(
                    "SELECT * FROM memories WHERE category = ? ORDER BY updated_at DESC;",
                    (category,)
                )
            else:
                cur = conn.execute("SELECT * FROM memories ORDER BY updated_at DESC;")
            return [MemoryItem.from_row(r) for r in cur.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def delete_memory(key: str) -> bool:
        """Belirtilen anahtara ait hafızayı siler."""
        conn = DBManager.get_memory_conn()
        try:
            with conn:
                cur = conn.execute("DELETE FROM memories WHERE key = ?;", (key.strip(),))
                return cur.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def clear_all() -> None:
        """Tüm hafızayı sıfırlar."""
        conn = DBManager.get_memory_conn()
        try:
            with conn:
                conn.execute("DELETE FROM memories;")
            logger.info("Tüm hafıza verisi temizlendi.")
        finally:
            conn.close()
