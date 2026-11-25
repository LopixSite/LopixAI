"""
LopixAI SQLite Veritabanı Yöneticisi
Thread güvenliği, WAL modu ve otomatik şema migrasyonu sağlar.
"""

import sqlite3
import threading
from pathlib import Path
from typing import Optional
from app.core.config import CHATS_DB_PATH, MEMORY_DB_PATH, ensure_data_directories
from app.core.logger import get_logger

logger = get_logger("DBManager")

_local = threading.local()

CHATS_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    is_pinned INTEGER DEFAULT 0,
    is_deleted INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp REAL NOT NULL,
    metadata TEXT,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_pinned ON conversations(is_pinned DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_deleted ON conversations(is_deleted);
CREATE INDEX IF NOT EXISTS idx_messages_conv_time ON messages(conversation_id, timestamp ASC);

-- Kalıcı Sohbet Kasası (Silinen Sohbetleri de Saklar)
CREATE TABLE IF NOT EXISTS chat_vault (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp REAL NOT NULL,
    conv_title TEXT,
    is_deleted_conv INTEGER DEFAULT 0
);

-- Otonom Öğrenilen Bilgiler Veritabanı
CREATE TABLE IF NOT EXISTS learned_knowledge (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    url TEXT,
    content TEXT NOT NULL,
    summary TEXT,
    keywords TEXT,
    learned_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chat_vault_conv ON chat_vault(conversation_id);
CREATE INDEX IF NOT EXISTS idx_chat_vault_time ON chat_vault(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_learned_topic ON learned_knowledge(topic);
CREATE INDEX IF NOT EXISTS idx_learned_time ON learned_knowledge(learned_at DESC);
"""

MEMORY_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(key);
CREATE INDEX IF NOT EXISTS idx_memories_cat ON memories(category);
"""

class DBManager:
    """SQLite veritabanı bağlantı ve migrasyon yöneticisi."""

    @staticmethod
    def get_connection(db_path: Path) -> sqlite3.Connection:
        """
        Thread-local SQLite bağlantısı döner.
        WAL modu ve PRAGMA ayarları uygulanır.
        """
        ensure_data_directories()
        conn = sqlite3.connect(
            str(db_path),
            timeout=10.0,
            check_same_thread=False
        )
        conn.row_factory = sqlite3.Row
        # Performans ve güvenilirlik PRAGMA'ları
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    @classmethod
    def get_chats_conn(cls) -> sqlite3.Connection:
        """chats.db bağlantısı döner."""
        return cls.get_connection(CHATS_DB_PATH)

    @classmethod
    def get_memory_conn(cls) -> sqlite3.Connection:
        """memory.db bağlantısı döner."""
        return cls.get_connection(MEMORY_DB_PATH)

    @classmethod
    def initialize_databases(cls) -> None:
        """Her iki veritabanının şemalarını ve migrasyonlarını uygular."""
        cls._init_chats_db()
        cls._init_memory_db()
        logger.info("SQLite veritabanları (chats.db, memory.db) başarıyla hazırlandı.")

    @classmethod
    def _init_chats_db(cls) -> None:
        conn = cls.get_chats_conn()
        try:
            with conn:
                conn.executescript(CHATS_SCHEMA_V1)
                # Versiyon kontrolü
                cur = conn.execute("SELECT version FROM schema_version LIMIT 1;")
                row = cur.fetchone()
                if not row:
                    conn.execute("INSERT INTO schema_version (version) VALUES (1);")
        except Exception as e:
            logger.error(f"chats.db başlatılırken hata: {e}")
            raise
        finally:
            conn.close()

    @classmethod
    def _init_memory_db(cls) -> None:
        conn = cls.get_memory_conn()
        try:
            with conn:
                conn.executescript(MEMORY_SCHEMA_V1)
                cur = conn.execute("SELECT version FROM schema_version LIMIT 1;")
                row = cur.fetchone()
                if not row:
                    conn.execute("INSERT INTO schema_version (version) VALUES (1);")
        except Exception as e:
            logger.error(f"memory.db başlatılırken hata: {e}")
            raise
        finally:
            conn.close()
