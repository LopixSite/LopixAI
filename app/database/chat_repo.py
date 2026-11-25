"""
LopixAI Sohbet Veritabanı Deposu (chats.db)
Sohbet oluşturma, mesaj kaydetme, arama, sabitleme, yeniden adlandırma ve silme.
"""

import time
import uuid
import json
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
from app.database.db_manager import DBManager
from app.core.logger import get_logger

logger = get_logger("ChatRepo")

@dataclass
class Message:
    id: str
    conversation_id: str
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_row(cls, row) -> "Message":
        meta = None
        if row["metadata"]:
            try:
                meta = json.loads(row["metadata"])
            except Exception:
                meta = None
        return cls(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            timestamp=row["timestamp"],
            metadata=meta
        )

@dataclass
class Conversation:
    id: str
    title: str
    created_at: float
    updated_at: float
    is_pinned: bool = False
    is_deleted: bool = False

    @classmethod
    def from_row(cls, row) -> "Conversation":
        return cls(
            id=row["id"],
            title=row["title"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            is_pinned=bool(row["is_pinned"]),
            is_deleted=bool(row["is_deleted"])
        )

class ChatRepository:
    """chats.db veritabanı işlemlerini yöneten depo sınıfı."""

    @staticmethod
    def create_conversation(title: str = "Yeni sohbet") -> Conversation:
        """Yeni bir konuşma oluşturur ve döner."""
        conv_id = str(uuid.uuid4())
        now = time.time()
        conn = DBManager.get_chats_conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO conversations (id, title, created_at, updated_at, is_pinned, is_deleted)
                    VALUES (?, ?, ?, ?, 0, 0)
                    """,
                    (conv_id, title, now, now)
                )
            logger.info(f"Yeni sohbet oluşturuldu: {conv_id} - '{title}'")
            return Conversation(
                id=conv_id,
                title=title,
                created_at=now,
                updated_at=now,
                is_pinned=False,
                is_deleted=False
            )
        finally:
            conn.close()

    @staticmethod
    def get_conversation(conv_id: str) -> Optional[Conversation]:
        """ID'ye göre sohbeti döner."""
        conn = DBManager.get_chats_conn()
        try:
            cur = conn.execute(
                "SELECT * FROM conversations WHERE id = ? AND is_deleted = 0 LIMIT 1;",
                (conv_id,)
            )
            row = cur.fetchone()
            return Conversation.from_row(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_all_conversations(include_deleted: bool = False) -> List[Conversation]:
        """Tüm sohbetleri önce sabitlenme, sonra güncelleme tarihine göre sıralı döner."""
        conn = DBManager.get_chats_conn()
        try:
            sql = "SELECT * FROM conversations "
            if not include_deleted:
                sql += "WHERE is_deleted = 0 "
            sql += "ORDER BY is_pinned DESC, updated_at DESC;"
            cur = conn.execute(sql)
            return [Conversation.from_row(r) for r in cur.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def rename_conversation(conv_id: str, new_title: str) -> bool:
        """Sohbet başlığını günceller."""
        new_title = new_title.strip()
        if not new_title:
            return False

        conn = DBManager.get_chats_conn()
        try:
            with conn:
                cur = conn.execute(
                    "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?;",
                    (new_title, time.time(), conv_id)
                )
                success = cur.rowcount > 0
                if success:
                    logger.info(f"Sohbet yeniden adlandırıldı ({conv_id}): '{new_title}'")
                return success
        finally:
            conn.close()

    @staticmethod
    def set_pinned(conv_id: str, is_pinned: bool) -> bool:
        """Sohbetin sabitlenme durumunu günceller."""
        conn = DBManager.get_chats_conn()
        try:
            with conn:
                cur = conn.execute(
                    "UPDATE conversations SET is_pinned = ?, updated_at = ? WHERE id = ?;",
                    (1 if is_pinned else 0, time.time(), conv_id)
                )
                return cur.rowcount > 0
        finally:
            conn.close()

    @staticmethod
    def delete_conversation(conv_id: str, soft_delete: bool = True) -> bool:
        """Sohbeti siler (varsayılan: soft delete)."""
        conn = DBManager.get_chats_conn()
        try:
            with conn:
                if soft_delete:
                    cur = conn.execute(
                        "UPDATE conversations SET is_deleted = 1, updated_at = ? WHERE id = ?;",
                        (time.time(), conv_id)
                    )
                else:
                    cur = conn.execute("DELETE FROM conversations WHERE id = ?;", (conv_id,))
                
                # Kalıcı kasada silindi olarak işaretle ama veriyi ASLA silme
                try:
                    conn.execute("UPDATE chat_vault SET is_deleted_conv = 1 WHERE conversation_id = ?;", (conv_id,))
                except Exception:
                    pass

                success = cur.rowcount > 0
                if success:
                    logger.info(f"Sohbet silindi ({conv_id}, soft_delete={soft_delete})")
                return success
        finally:
            conn.close()

    @staticmethod
    def add_message(conv_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """Sohbete yeni bir mesaj ekler ve sohbetin güncellenme tarihini tazeler."""
        msg_id = str(uuid.uuid4())
        now = time.time()
        meta_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

        conn = DBManager.get_chats_conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO messages (id, conversation_id, role, content, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?, ?);
                    """,
                    (msg_id, conv_id, role, content, now, meta_json)
                )
                conn.execute(
                    "UPDATE conversations SET updated_at = ? WHERE id = ?;",
                    (now, conv_id)
                )

                # Kalıcı Kasaya (Shadow Vault) kaydet
                try:
                    c_cur = conn.execute("SELECT title FROM conversations WHERE id = ?;", (conv_id,))
                    c_row = c_cur.fetchone()
                    c_title = c_row["title"] if c_row else "Sohbet"
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO chat_vault (id, conversation_id, role, content, timestamp, conv_title, is_deleted_conv)
                        VALUES (?, ?, ?, ?, ?, ?, 0);
                        """,
                        (msg_id, conv_id, role, content, now, c_title)
                    )
                except Exception as ex_v:
                    logger.warning(f"Kasa kaydı sırasında uyarı: {ex_v}")
            return Message(
                id=msg_id,
                conversation_id=conv_id,
                role=role,
                content=content,
                timestamp=now,
                metadata=metadata
            )
        finally:
            conn.close()

    @staticmethod
    def get_messages(conv_id: str, limit: Optional[int] = None) -> List[Message]:
        """Sohbete ait mesajları kronolojik sırayla döner."""
        conn = DBManager.get_chats_conn()
        try:
            sql = "SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC"
            if limit:
                sql += f" LIMIT {int(limit)}"
            cur = conn.execute(sql, (conv_id,))
            return [Message.from_row(r) for r in cur.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def search_conversations(query_str: str) -> List[Conversation]:
        """
        Sohbet başlıklarında ve mesaj içeriklerinde arama yapar.
        Arama sonuçlarını en güncelden eskiye sıralar.
        """
        query_str = query_str.strip()
        if not query_str:
            return ChatRepository.get_all_conversations()

        pattern = f"%{query_str}%"
        conn = DBManager.get_chats_conn()
        try:
            cur = conn.execute(
                """
                SELECT DISTINCT c.*
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.is_deleted = 0
                  AND (c.title LIKE ? OR m.content LIKE ?)
                ORDER BY c.is_pinned DESC, c.updated_at DESC;
                """,
                (pattern, pattern)
            )
            return [Conversation.from_row(r) for r in cur.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_message_count(conv_id: str) -> int:
        """Sohbetteki toplam mesaj sayısını döner."""
        conn = DBManager.get_chats_conn()
        try:
            cur = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE conversation_id = ?;",
                (conv_id,)
            )
            return cur.fetchone()[0]
        finally:
            conn.close()

    # ==========================================
    # Kalıcı Kasa (Chat Vault) & Otonom Öğrenme
    # ==========================================

    @staticmethod
    def get_all_user_queries(include_deleted: bool = True, limit: int = 200) -> List[str]:
        """
        Kullanıcının geçmişte sorduğu tüm soruları ve mesajları döner.
        Silinen sohbetler de kasadan (chat_vault) taranır.
        """
        conn = DBManager.get_chats_conn()
        try:
            sql = "SELECT content FROM chat_vault WHERE role = 'user' "
            if not include_deleted:
                sql += "AND is_deleted_conv = 0 "
            sql += "ORDER BY timestamp DESC LIMIT ?;"
            cur = conn.execute(sql, (limit,))
            queries = [row["content"].strip() for row in cur.fetchall() if row["content"].strip()]
            
            # Eğer chat_vault henüz boşsa doğrudan messages tablosundan al
            if not queries:
                cur2 = conn.execute(
                    "SELECT content FROM messages WHERE role = 'user' ORDER BY timestamp DESC LIMIT ?;",
                    (limit,)
                )
                queries = [r["content"].strip() for r in cur2.fetchall() if r["content"].strip()]
            return queries
        except Exception as e:
            logger.error(f"Kullanıcı geçmişi alınırken hata: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def save_learned_knowledge(
        topic: str, title: str, source: str, url: str, content: str, summary: str, keywords: str
    ) -> bool:
        """Otonom öğrenilen bir bilgiyi SQLite veritabanına kaydeder."""
        knowledge_id = str(uuid.uuid4())
        now = time.time()
        conn = DBManager.get_chats_conn()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO learned_knowledge (id, topic, title, source, url, content, summary, keywords, learned_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (knowledge_id, topic, title, source, url, content, summary, keywords, now)
                )
            logger.info(f"[Hafıza] Yeni bilgi kaydedildi: {topic} - '{title}' ({source})")
            return True
        except Exception as e:
            logger.error(f"Öğrenilen bilgi kaydedilemedi: {e}")
            return False
        finally:
            conn.close()

    @staticmethod
    def search_learned_knowledge(query_str: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Kullanıcının sorusuyla eşleşen daha önce öğrenilmiş yerel bilgileri döner."""
        words = [w for w in query_str.lower().split() if len(w) > 2]
        if not words:
            return []

        conn = DBManager.get_chats_conn()
        try:
            results = []
            for w in words[:4]:
                pattern = f"%{w}%"
                cur = conn.execute(
                    """
                    SELECT * FROM learned_knowledge
                    WHERE topic LIKE ? OR title LIKE ? OR keywords LIKE ? OR content LIKE ?
                    ORDER BY learned_at DESC LIMIT ?;
                    """,
                    (pattern, pattern, pattern, pattern, limit)
                )
                for r in cur.fetchall():
                    item = dict(r)
                    if item not in results:
                        results.append(item)
                    if len(results) >= limit:
                        break
                if len(results) >= limit:
                    break
            return results
        except Exception as e:
            logger.error(f"Öğrenilen bilgiler aranırken hata: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def get_learned_knowledge_count() -> int:
        """Hafızada kayıtlı toplam otonom bilgi sayısını döner."""
        conn = DBManager.get_chats_conn()
        try:
            cur = conn.execute("SELECT COUNT(*) FROM learned_knowledge;")
            row = cur.fetchone()
            return row[0] if row else 0
        except Exception:
            return 0
        finally:
            conn.close()
