"""
LopixAI Çevrimdışı Yapay Zeka ve Ajan Servisi (Product Rule #4)
Gemini API yokken veya internet kesildiğinde çalışır.
Yerel komutlar, hafıza yönetimi, sistem bilgisi ve hazır yanıtları yönetir.
"""

import os
import time
import datetime
import platform
import psutil
from typing import Dict, Any, Optional
from app.database.memory_repo import MemoryRepository
from app.core.logger import get_logger

logger = get_logger("OfflineService")

class OfflineService:
    """Çevrimdışı mod yanıt üreticisi ve yerel komut motoru."""

    @classmethod
    def generate_response(cls, user_message: str, conversation_id: str) -> str:
        """Kullanıcı mesajını yerel olarak değerlendirir ve yanıt üretir."""
        msg = user_message.strip()
        lower_msg = msg.lower()

        # 1. Doğrudan Komut Kontrolleri
        if lower_msg in ("/yardim", "/help", "yardım", "komutlar"):
            return cls._cmd_help()

        if lower_msg in ("/durum", "/status", "sistem durumu", "durum"):
            return cls._cmd_status()

        if any(w in lower_msg for w in ["saat kaç", "şu an saat", "/saat", "/time"]):
            return cls._cmd_time()

        if any(w in lower_msg for w in ["tarih ne", "bugün ayın kaçı", "hangi gündeyiz", "/tarih", "/date"]):
            return cls._cmd_date()

        if lower_msg.startswith("/hatirla ") or lower_msg.startswith("/remember "):
            return cls._cmd_remember(msg)

        if lower_msg in ("/hatirlananlar", "/memories", "hafıza", "neler biliyorsun"):
            return cls._cmd_list_memories()

        if lower_msg.startswith("/unut ") or lower_msg.startswith("/forget "):
            return cls._cmd_forget(msg)

        # 2. Tanıtım ve Sohbet Kalıpları
        if any(w in lower_msg for w in ["sen kimsin", "kimsin", "lopixai nedir", "kendini tanıt"]):
            return (
                "✦ **Ben LopixAI**\n\n"
                "Windows 10/11 için tasarlanmış, kullanıcıdan teknik model kurulumu veya "
                "özel GPU gerektirmeyen kişisel yapay zeka asistanınızım.\n\n"
                "Şu anda **Çevrimdışı Mod**'dayım. Genel bilgi soruları ve derinlemesine sohbet için "
                "sol üstteki Ayarlar menüsünden Gemini API anahtarınızı tanımlayabilirsiniz."
            )

        if any(w in lower_msg for w in ["merhaba", "selam", "günaydın", "iyi akşamlar", "hey"]):
            return (
                "Merhaba! Size nasıl yardımcı olabilirim?\n\n"
                "*(Not: Şu anda çevrimdışı mod aktif. Bilgisayar kontrol komutları veya hafıza "
                "özelliklerini kullanabilir, komut listesi için `/yardim` yazabilirsiniz.)*"
            )

        # 3. 100+ Site Kapsamlı Derin Web Arama Motoru (Reddit, Wiki, StackOverflow, Quora vb.)
        try:
            from app.ai.deep_search_engine import DeepSearchEngine
            deep_res = DeepSearchEngine.search_and_synthesize(msg)
            if deep_res:
                return deep_res
        except Exception as e:
            logger.warning(f"Derin arama servisinde hata: {e}")

        # 4. İnternet yoksa veya arama başarısızsa yerel bilgilendirme
        return (
            "ℹ️ **LopixAI Çevrimdışı Mod**\n\n"
            f"Sorunuzu aldım: *\"{msg}\"*\n\n"
            "Şu anda geçerli bir **Gemini API anahtarı** bulunamadığı ve internet bağlantısına erişilemediği "
            "için yerel mod devrededir.\n\n"
            "**Neler yapabilirsiniz?**\n"
            "• **Ayarlar** (sol alttaki dişli çark) üzerinden Gemini API anahtarınızı girerek sınırsız yapay zekaya geçebilirsiniz.\n"
            "• Yerel hafızaya bilgi eklemek için: `/hatirla <anahtar> <bilgi>`\n"
            "• Sistem durumunu görmek için: `/durum`\n"
            "• Tüm komutlar için: `/yardim`"
        )

    @staticmethod
    def _cmd_help() -> str:
        return (
            "🛠️ **LopixAI Çevrimdışı Komutları**\n\n"
            "• `/durum` - Bilgisayar donanım, RAM ve CPU durumunu gösterir\n"
            "• `/saat` - Güncel saat bilgisini verir\n"
            "• `/tarih` - Güncel tarih bilgisini verir\n"
            "• `/hatirla <anahtar> <bilgi>` - Yerel hafızaya (`memory.db`) kalıcı bilgi kaydeder\n"
            "• `/hatirlananlar` - Kayıtlı tüm hafıza bilgilerini listeler\n"
            "• `/unut <anahtar>` - Kayıtlı bir hafıza bilgisini siler\n"
            "• `/yardim` - Bu menüyü gösterir\n\n"
            "*Tam yapay zeka sohbeti için lütfen Gemini API anahtarınızı ekleyin.*"
        )

    @staticmethod
    def _cmd_status() -> str:
        try:
            cpu_pct = psutil.cpu_percent(interval=0.2)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage(os.getenv("SystemDrive", "C:") + "\\")
            ram_used_gb = round((ram.total - ram.available) / (1024**3), 2)
            ram_total_gb = round(ram.total / (1024**3), 2)
            disk_free_gb = round(disk.free / (1024**3), 2)

            return (
                "💻 **Sistem Durumu (Windows x64)**\n\n"
                f"• **İşletim Sistemi:** {platform.system()} {platform.release()} ({platform.version()})\n"
                f"• **İşlemci (CPU) Kullanımı:** %{cpu_pct}\n"
                f"• **Bellek (RAM):** {ram_used_gb} GB / {ram_total_gb} GB (%{ram.percent})\n"
                f"• **Sistem Diski Boş Alan:** {disk_free_gb} GB\n"
                "• **LopixAI Modu:** Çevrimdışı / Yerel Motor Hazır ✓"
            )
        except Exception as e:
            return f"Sistem durumu alınırken hata oluştu: {e}"

    @staticmethod
    def _cmd_time() -> str:
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        return f"🕒 Şu an saat: **{now_str}**"

    @staticmethod
    def _cmd_date() -> str:
        now_str = datetime.datetime.now().strftime("%d.%m.%Y (%A)")
        return f"📅 Bugünün tarihi: **{now_str}**"

    @staticmethod
    def _cmd_remember(msg: str) -> str:
        parts = msg.split(maxsplit=2)
        if len(parts) < 3:
            return "Kullanım: `/hatirla <anahtar> <bilgi>`\nÖrnek: `/hatirla adim Ahmet`"
        key = parts[1]
        val = parts[2]
        MemoryRepository.set_memory(key, val)
        return f"✓ **Hafızaya kaydedildi:** `{key}` = \"{val}\""

    @staticmethod
    def _cmd_list_memories() -> str:
        items = MemoryRepository.get_all_memories()
        if not items:
            return "Hafızada kayıtlı herhangi bir bilgi bulunmuyor."
        lines = ["🧠 **LopixAI Yerel Hafızası (`memory.db`)**\n"]
        for it in items:
            lines.append(f"• **{it.key}**: {it.value} *(Kategori: {it.category})*")
        return "\n".join(lines)

    @staticmethod
    def _cmd_forget(msg: str) -> str:
        parts = msg.split(maxsplit=1)
        if len(parts) < 2:
            return "Kullanım: `/unut <anahtar>`\nÖrnek: `/unut adim`"
        key = parts[1]
        if MemoryRepository.delete_memory(key):
            return f"✓ `{key}` hafızadan silindi."
        return f"`{key}` hafızada bulunamadı."
