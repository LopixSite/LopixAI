"""
LopixAI Faz 0 Kapsamlı Otomatik Birim ve Entegrasyon Testleri
Tüm çekirdek fonksiyonları, DPAPI şifrelemeyi, SQLite işlemlerini ve offline motoru test eder.
"""

import sys
import unittest
import time
from pathlib import Path

# Proje dizinini ekle
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import (
    DATA_DIR, CHATS_DB_PATH, MEMORY_DB_PATH, SETTINGS_PATH, SECRETS_PATH,
    ensure_data_directories
)
from app.core.secrets import SecretsManager
from app.core.settings import SettingsManager
from app.core.system_check import SystemChecker
from app.database.db_manager import DBManager
from app.database.chat_repo import ChatRepository
from app.database.memory_repo import MemoryRepository
from app.ai.offline_service import OfflineService
from app.ai.gemini_service import GeminiService


class TestLopixAICore(unittest.TestCase):
    """LopixAI Faz 0 Çekirdek Sistem Testleri."""

    @classmethod
    def setUpClass(cls):
        """Test öncesi ortamı hazırla."""
        ensure_data_directories()
        DBManager.initialize_databases()

    def test_01_directories_created(self):
        """%APPDATA%\\.lopixai klasör hiyerarşisi oluşturuluyor mu?"""
        self.assertTrue(DATA_DIR.exists(), "DATA_DIR oluşturulmadı!")
        self.assertTrue((DATA_DIR / "logs").exists(), "logs/ oluşturulmadı!")
        self.assertTrue((DATA_DIR / "voice").exists(), "voice/ oluşturulmadı!")
        self.assertTrue((DATA_DIR / "security" / "events").exists(), "security/events/ oluşturulmadı!")
        self.assertTrue((DATA_DIR / "agent" / "workspace").exists(), "agent/workspace/ oluşturulmadı!")

    def test_02_secrets_dpapi_encryption(self):
        """Windows DPAPI şifreleme ve çözme düz metin sızıntısı olmadan çalışıyor mu?"""
        original_gemini = SecretsManager.get_gemini_api_key()
        try:
            test_key = "AIzaSy_TEST_DPAPI_SECRET_KEY_123456"
            SecretsManager.set_gemini_api_key(test_key)

            # Şifreli dosyayı doğrudan oku; düz metin OLMAMALI
            raw_bytes = SECRETS_PATH.read_bytes()
            self.assertNotIn(test_key.encode("utf-8"), raw_bytes, "HATA: API Key secrets.dat içinde düz metin olarak bulundu!")

            # DPAPI ile geri çöz ve doğrula
            retrieved_key = SecretsManager.get_gemini_api_key()
            self.assertEqual(retrieved_key, test_key, "DPAPI çözülen anahtar orijinali ile eşleşmiyor!")
        finally:
            if original_gemini and original_gemini != "AIzaSy_TEST_DPAPI_SECRET_KEY_123456":
                SecretsManager.set_gemini_api_key(original_gemini)
            else:
                SecretsManager.delete_secret("gemini_api_key")

    def test_03_settings_manager(self):
        """settings.json okuma, yazma ve varsayılan tamamlama çalışıyor mu?"""
        SettingsManager.set("telegram_enabled", True)
        self.assertTrue(SettingsManager.get("telegram_enabled"))
        SettingsManager.set("telegram_enabled", False)

        # Dosyanın gerçekten var olduğunu doğrula
        self.assertTrue(SETTINGS_PATH.exists())

    def test_04_chat_repository_crud(self):
        """chats.db üzerinde konuşma ve mesaj CRUD işlemleri doğru çalışıyor mu?"""
        # 1. Konuşma oluştur
        conv = ChatRepository.create_conversation("Test Sohbeti")
        self.assertIsNotNone(conv.id)
        self.assertEqual(conv.title, "Test Sohbeti")

        # 2. Mesaj ekle
        msg1 = ChatRepository.add_message(conv.id, "user", "Merhaba dünya!")
        msg2 = ChatRepository.add_message(conv.id, "assistant", "Merhaba, ben LopixAI!")
        self.assertEqual(msg1.content, "Merhaba dünya!")
        self.assertEqual(msg2.role, "assistant")

        # 3. Mesajları getir
        messages = ChatRepository.get_messages(conv.id)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].content, "Merhaba dünya!")
        self.assertEqual(messages[1].content, "Merhaba, ben LopixAI!")

        # 4. Yeniden adlandır
        renamed = ChatRepository.rename_conversation(conv.id, "Python Kursu")
        self.assertTrue(renamed)
        updated_conv = ChatRepository.get_conversation(conv.id)
        self.assertEqual(updated_conv.title, "Python Kursu")

        # 5. Sabitle (Pin)
        ChatRepository.set_pinned(conv.id, True)
        updated_conv = ChatRepository.get_conversation(conv.id)
        self.assertTrue(updated_conv.is_pinned)

        # 6. Arama (Search)
        search_res = ChatRepository.search_conversations("Python")
        self.assertTrue(any(c.id == conv.id for c in search_res))

        # Mesaj içeriğinde arama
        search_res_msg = ChatRepository.search_conversations("dünya")
        self.assertTrue(any(c.id == conv.id for c in search_res_msg))

        # 7. Silme (Soft Delete)
        deleted = ChatRepository.delete_conversation(conv.id)
        self.assertTrue(deleted)
        # Aktif listede görünmemeli
        active_convs = ChatRepository.get_all_conversations(include_deleted=False)
        self.assertFalse(any(c.id == conv.id for c in active_convs))

    def test_05_memory_repository(self):
        """memory.db kullanıcı tercih ve bilgi saklama çalışıyor mu?"""
        MemoryRepository.set_memory("kullanici_adi", "FALCON", category="profile")
        val = MemoryRepository.get_memory("kullanici_adi")
        self.assertEqual(val, "FALCON")

        all_mem = MemoryRepository.get_all_memories()
        self.assertTrue(any(m.key == "kullanici_adi" for m in all_mem))

        MemoryRepository.delete_memory("kullanici_adi")
        self.assertIsNone(MemoryRepository.get_memory("kullanici_adi"))

    def test_06_offline_service(self):
        """Çevrimdışı mod komutları (/durum, /saat, /yardim) yanıt üretiyor mu?"""
        reply_help = OfflineService.generate_response("/yardim", "conv_test")
        self.assertIn("Komutları", reply_help)

        reply_status = OfflineService.generate_response("/durum", "conv_test")
        self.assertIn("Sistem Durumu", reply_status)

        reply_time = OfflineService.generate_response("saat kaç", "conv_test")
        self.assertIn("saat", reply_time)

        reply_remember = OfflineService.generate_response("/hatirla sehir Istanbul", "conv_test")
        self.assertIn("Hafızaya kaydedildi", reply_remember)

        saved_city = MemoryRepository.get_memory("sehir")
        self.assertEqual(saved_city, "Istanbul")

    def test_07_gemini_auto_title_generation(self):
        """İlk kullanıcı mesajından otomatik başlık türetme çalışıyor mu?"""
        t1 = GeminiService.generate_title_from_prompt("Python'da class nedir?")
        self.assertIn("Python", t1)

        t2 = GeminiService.generate_title_from_prompt("bana yapay zeka mimarisi hakkında bilgi ver")
        self.assertTrue(len(t2) <= 40)
        self.assertTrue(t2[0].isupper())

    def test_08_system_checks(self):
        """Açılış sistem kontrol modülü çökmeksizin tüm testleri tamamlıyor mu?"""
        results = SystemChecker.run_all_checks()
        self.assertGreaterEqual(len(results), 8)
        # Runtime ve Filesystem kesinlikle OK olmalı
        runtime_res = next((r for r in results if r.key == "runtime"), None)
        self.assertIsNotNone(runtime_res)
        self.assertEqual(runtime_res.status, "OK")

    def test_09_gemini_automatic_model(self):
        """Gemini modeli kullanıcıya sorulmadan otomatik yönetiliyor mu?"""
        model = GeminiService.get_model_name()
        self.assertEqual(model, "gemini-3.6-flash")
        self.assertIn("gemini-flash-latest", GeminiService.CANDIDATE_MODELS)

    def test_10_telegram_bridge_and_token_validation(self):
        """Telegram köprüsü /newchat, /listchats ve geçersiz token koruması çalışıyor mu?"""
        from app.telegram.bridge import TelegramAPI, TelegramBridge
        
        # Boş token kontrolü
        ok, msg, _ = TelegramAPI.test_token("")
        self.assertFalse(ok)
        self.assertIn("boş", msg.lower())

        # /newchat komutu
        new_res = TelegramBridge.handle_command_newchat("Telegram Test Sohbeti")
        self.assertIn("Telegram Test Sohbeti", new_res)

        # /listchats komutu
        list_res = TelegramBridge.handle_command_listchats()
        self.assertIn("Mevcut Sohbetler", list_res)


if __name__ == "__main__":
    unittest.main()
