"""
LopixAI Telegram Köprüsü ve Canlı Bot Servisi (Product Rule #13)
Telegram botu ve masaüstü arayüzü aynı chats.db veritabanını paylaşır.
/newchat, /listchats ve mesaj senkronizasyonu canlı polling ile sağlanır.
"""

import time
import requests
from typing import Optional, List, Tuple, Dict, Any
from PyQt6.QtCore import QThread, pyqtSignal

from app.core.secrets import SecretsManager
from app.core.logger import get_logger
from app.database.chat_repo import ChatRepository, Conversation
from app.ai.gemini_service import GeminiService

logger = get_logger("TelegramBridge")

class TelegramAPI:
    """Telegram Bot HTTP REST API istemcisi."""

    @staticmethod
    def test_token(token: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Token'ı Telegram API ile test eder.
        Döner: (başarılı_mı, mesaj, bot_bilgisi)
        """
        token = token.strip()
        if not token:
            return False, "Token boş olamaz.", None

        url = f"https://api.telegram.org/bot{token}/getMe"
        try:
            resp = requests.get(url, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    bot_info = data.get("result", {})
                    username = bot_info.get("username", "Bilinmiyor")
                    first_name = bot_info.get("first_name", "LopixAI Bot")
                    return True, f"Bağlandı: @{username} ({first_name})", bot_info
                else:
                    return False, f"Telegram hatası: {data.get('description')}", None
            elif resp.status_code == 401 or resp.status_code == 404:
                return False, "Geçersiz Bot Token! Lütfen token'ı kontrol edin.", None
            else:
                return False, f"HTTP {resp.status_code} Hatası", None
        except requests.exceptions.RequestException as e:
            return False, f"Ağ bağlantı hatası: {e}", None
        except Exception as e:
            return False, f"Beklenmeyen hata: {e}", None

    @staticmethod
    def send_message(token: str, chat_id: int, text: str) -> bool:
        """Telegram sohbetine mesaj gönderir."""
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            resp = requests.post(url, json=payload, timeout=10.0)
            if resp.status_code != 200:
                # Markdown parse hatası olursa düz metin olarak tekrar dene
                payload.pop("parse_mode")
                resp = requests.post(url, json=payload, timeout=10.0)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Telegram mesaj gönderme hatası ({chat_id}): {e}")
            return False

    @staticmethod
    def get_updates(token: str, offset: Optional[int] = None, timeout: int = 15) -> List[Dict[str, Any]]:
        """Telegram sunucusundan yeni güncellemeleri çeker."""
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        params = {"timeout": timeout}
        if offset is not None:
            params["offset"] = offset

        try:
            resp = requests.get(url, params=params, timeout=timeout + 5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    return data.get("result", [])
        except Exception as e:
            logger.debug(f"Telegram polling geçici bağlantı durumu: {e}")
        return []


class TelegramPollingWorker(QThread):
    """
    Arka planda Telegram getUpdates polling döngüsünü yürüten QThread.
    Masaüstü arayüzünü kilitlemez.
    """
    message_synced = pyqtSignal(str)  # conversation_id
    status_changed = pyqtSignal(str)  # durum mesajı

    def __init__(self, token: str):
        super().__init__()
        self.token = token
        self._running = True
        self.offset = None

    def stop(self):
        """Thread'i güvenli şekilde sonlandırır."""
        self._running = False

    def run(self):
        logger.info("Telegram polling thread'i başlatıldı.")
        self.status_changed.emit("Çalışıyor")

        while self._running:
            try:
                updates = TelegramAPI.get_updates(self.token, offset=self.offset, timeout=10)
                for update in updates:
                    if not self._running:
                        break

                    update_id = update.get("update_id")
                    self.offset = update_id + 1

                    message = update.get("message")
                    if not message:
                        continue

                    chat_id = message.get("chat", {}).get("id")
                    text = message.get("text", "").strip()
                    if not text or not chat_id:
                        continue

                    self._handle_telegram_message(chat_id, text)

            except Exception as e:
                logger.error(f"Telegram worker döngü hatası: {e}")
                self.msleep(2000)

        logger.info("Telegram polling thread'i durduruldu.")
        self.status_changed.emit("Durduruldu")

    def _handle_telegram_message(self, chat_id: int, text: str):
        """Telegram'dan gelen mesajı veya komutu işler."""
        logger.info(f"Telegram mesajı alındı ({chat_id}): '{text}'")

        # 1. /start veya /help
        if text.startswith("/start") or text.startswith("/help"):
            welcome = (
                "✦ **LopixAI Telegram Asistanı**\n\n"
                "Masaüstü LopixAI ile aynı veritabanını paylaşıyorsunuz.\n\n"
                "• `/newchat` - Yeni sohbet başlatır\n"
                "• `/listchats` - Mevcut sohbetleri listeler\n"
                "• Doğrudan bir mesaj yazarak aktif sohbette konuşabilirsiniz."
            )
            TelegramAPI.send_message(self.token, chat_id, welcome)
            return

        # 2. /newchat komutu (Product Rule #13)
        if text.startswith("/newchat"):
            title = text.replace("/newchat", "").strip() or "Telegram Sohbeti"
            conv = ChatRepository.create_conversation(title)
            TelegramBridge.set_active_conversation(conv.id)
            reply = f"✓ Yeni sohbet oluşturuldu: **{conv.title}**"
            TelegramAPI.send_message(self.token, chat_id, reply)
            self.message_synced.emit(conv.id)
            return

        # 3. /listchats komutu (Product Rule #13)
        if text.startswith("/listchats"):
            reply = TelegramBridge.handle_command_listchats()
            TelegramAPI.send_message(self.token, chat_id, reply)
            return

        # 4. Normal Mesaj -> Aktif sohbete ekle ve yanıtla
        conv_id = TelegramBridge.get_active_conversation_id()
        
        # Kullanıcı mesajını chats.db'ye ekle
        ChatRepository.add_message(conv_id, "user", text, metadata={"source": "telegram", "chat_id": chat_id})
        self.message_synced.emit(conv_id)

        # İlk mesajsa otomatik başlık türet
        conv = ChatRepository.get_conversation(conv_id)
        if conv and conv.title in ("Yeni sohbet", "Telegram Sohbeti"):
            auto_title = GeminiService.generate_title_from_prompt(text)
            ChatRepository.rename_conversation(conv_id, auto_title)

        # Yapay zeka yanıtı üret
        reply_text, is_offline = GeminiService.send_message(conv_id, text)

        # Yanıtı chats.db'ye ekle
        ChatRepository.add_message(conv_id, "assistant", reply_text, metadata={"source": "telegram", "is_offline": is_offline})
        self.message_synced.emit(conv_id)

        # Yanıtı Telegram kullanıcısına gönder
        TelegramAPI.send_message(self.token, chat_id, reply_text)


class TelegramBridge:
    """Telegram modüler köprü yöneticisi."""

    _active_conversation_id: Optional[str] = None
    _worker: Optional[TelegramPollingWorker] = None

    @classmethod
    def is_configured(cls) -> bool:
        """Token tanımlı mı?"""
        token = SecretsManager.get_telegram_token()
        return bool(token and token.strip())

    @classmethod
    def test_connection(cls, token: Optional[str] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Token'ı test eder."""
        tok = token or SecretsManager.get_telegram_token() or ""
        return TelegramAPI.test_token(tok)

    @classmethod
    def get_active_conversation_id(cls) -> str:
        """Aktif sohbet ID'sini döner."""
        if not cls._active_conversation_id:
            convs = ChatRepository.get_all_conversations()
            if convs:
                cls._active_conversation_id = convs[0].id
            else:
                new_conv = ChatRepository.create_conversation("Telegram Sohbeti")
                cls._active_conversation_id = new_conv.id
        return cls._active_conversation_id

    @classmethod
    def set_active_conversation(cls, conv_id: str) -> None:
        cls._active_conversation_id = conv_id

    @classmethod
    def handle_command_newchat(cls, title: str = "Telegram Sohbeti") -> str:
        """/newchat komutunu işler ve aktif sohbeti günceller."""
        conv = ChatRepository.create_conversation(title)
        cls.set_active_conversation(conv.id)
        return f"✓ Yeni sohbet oluşturuldu: **{conv.title}**"

    @classmethod
    def handle_command_listchats(cls) -> str:
        convs = ChatRepository.get_all_conversations()
        if not convs:
            return "Henüz hiç sohbet geçmişi bulunmuyor."

        lines = ["📋 **Mevcut Sohbetler:**\n"]
        for idx, c in enumerate(convs[:15], 1):
            pin = "📌 " if c.is_pinned else ""
            active = " 🟢 *(Aktif)*" if c.id == cls.get_active_conversation_id() else ""
            lines.append(f"{idx}. {pin}**{c.title}**{active}")
        return "\n".join(lines)

    @classmethod
    def start_polling(cls, on_sync_callback=None) -> bool:
        """Telegram arka plan bot dinleme servisini başlatır."""
        token = SecretsManager.get_telegram_token()
        if not token or not token.strip():
            logger.info("Telegram token bulunamadı, polling başlatılamadı.")
            return False

        cls.stop_polling()

        cls._worker = TelegramPollingWorker(token)
        if on_sync_callback:
            cls._worker.message_synced.connect(on_sync_callback)
        cls._worker.start()
        logger.info("Telegram bot servisi arka planda başlatıldı.")
        return True

    @classmethod
    def stop_polling(cls) -> None:
        """Telegram bot dinleme servisini durdurur."""
        if cls._worker and cls._worker.isRunning():
            cls._worker.stop()
            cls._worker.wait(2000)
            cls._worker = None
            logger.info("Telegram bot servisi durduruldu.")

    @classmethod
    def is_running(cls) -> bool:
        return bool(cls._worker and cls._worker.isRunning())
