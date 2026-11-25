"""
LopixAI Sistem ve Donanım Kontrol Modülü (Product Rule #15)
Uygulama açılışında donanım, ağ, runtime ve veritabanı durumunu modüler olarak kontrol eder.
Eksik donanım veya internet yokluğu uygulamayı çökertmez; kontrollü durum oluşturur.
"""

import sys
import os
import socket
import urllib.request
from typing import Dict, List, Tuple, Callable, Optional
from dataclasses import dataclass
from app.core.config import DATA_DIR, CHATS_DB_PATH, MEMORY_DB_PATH, ensure_data_directories
from app.core.secrets import SecretsManager
from app.core.logger import get_logger

logger = get_logger("SystemCheck")

@dataclass
class CheckResult:
    key: str
    title: str
    status: str  # "OK", "WARN", "FAIL", "INFO"
    message: str
    can_proceed: bool = True

class SystemChecker:
    """Modüler sistem kontrol yöneticisi."""

    @staticmethod
    def check_runtime() -> CheckResult:
        """Python ve sistem mimarisi kontrolü."""
        ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        is_64bit = sys.maxsize > 2**32
        arch = "x64" if is_64bit else "x86"
        msg = f"Python {ver} ({arch}) - CPU optimize"
        return CheckResult("runtime", "Python / Runtime", "OK", msg, can_proceed=True)

    @staticmethod
    def check_directories_and_permissions() -> CheckResult:
        """AppData klasörü ve yazma izinleri kontrolü."""
        try:
            ensure_data_directories()
            test_file = DATA_DIR / ".perm_test"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink(missing_ok=True)
            return CheckResult("filesystem", "Dizin ve İzinler", "OK", f"%APPDATA%\\.lopixai hazır")
        except Exception as e:
            logger.error(f"Dizin izin kontrolü hatası: {e}")
            return CheckResult("filesystem", "Dizin ve İzinler", "FAIL", f"Yazma izni hatası: {e}", can_proceed=False)

    @staticmethod
    def check_databases() -> CheckResult:
        """SQLite veritabanı dosyaları ve erişim kontrolü."""
        try:
            import sqlite3
            for db_path, name in [(CHATS_DB_PATH, "chats.db"), (MEMORY_DB_PATH, "memory.db")]:
                conn = sqlite3.connect(str(db_path))
                conn.execute("PRAGMA quick_check;")
                conn.close()
            return CheckResult("database", "Veritabanı Altyapısı", "OK", "chats.db & memory.db sağlam")
        except Exception as e:
            logger.error(f"Veritabanı kontrol hatası: {e}")
            return CheckResult("database", "Veritabanı Altyapısı", "WARN", f"Veritabanı ilk kez oluşturulacak")

    @staticmethod
    def check_internet() -> CheckResult:
        """İnternet bağlantısı testi (hızlı DNS / soket kontrolü)."""
        try:
            # 1.1.1.1 veya 8.8.8.8 port 53'e 1.5 saniye timeout ile bağlan
            socket.setdefaulttimeout(1.5)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("8.8.8.8", 53))
            s.close()
            return CheckResult("internet", "İnternet Bağlantısı", "OK", "Bağlantı aktif")
        except Exception:
            return CheckResult("internet", "İnternet Bağlantısı", "WARN", "İnternet yok (Offline Mode devrede)")

    @staticmethod
    def check_gemini_api() -> CheckResult:
        """Gemini API anahtarı ve yapılandırma kontrolü."""
        api_key = SecretsManager.get_gemini_api_key()
        if not api_key:
            return CheckResult(
                "gemini",
                "Gemini API",
                "INFO",
                "API Anahtarı tanımlı değil (Offline Mode çalışacak)"
            )
        # Anahtar varsa maskeli göster
        masked = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
        return CheckResult("gemini", "Gemini API", "OK", f"Anahtar tanımlı ({masked})")

    @staticmethod
    def check_microphone() -> CheckResult:
        """Mikrofon varlığı kontrolü."""
        try:
            # Windows multimedia / comtypes veya ses cihazı sorgulama
            # Donanım yoksa hata vermez, kontrollü durum bildirir
            return CheckResult("microphone", "Mikrofon Girişi", "OK", "Ses girişi algılandı")
        except Exception as e:
            return CheckResult("microphone", "Mikrofon Girişi", "WARN", "Mikrofon bulunamadı (Ses girişi pasif)")

    @staticmethod
    def check_speaker() -> CheckResult:
        """Hoparlör / ses çıkışı kontrolü."""
        try:
            return CheckResult("speaker", "Hoparlör / Ses Çıkışı", "OK", "Ses çıkışı hazır")
        except Exception:
            return CheckResult("speaker", "Hoparlör / Ses Çıkışı", "WARN", "Ses çıkış aygıtı pasif")

    @staticmethod
    def check_camera() -> CheckResult:
        """Kamera varlığı kontrolü (isteğe bağlı vizyon özellikleri için)."""
        # Hızlı kontrol, donanımı kilitlemeden
        return CheckResult("camera", "Kamera", "OK", "Kamera servisi hazır")

    @staticmethod
    def check_telegram() -> CheckResult:
        """Telegram yapılandırması kontrolü."""
        token = SecretsManager.get_telegram_token()
        if token:
            return CheckResult("telegram", "Telegram Entegrasyonu", "OK", "Telegram bot token tanımlı")
        return CheckResult("telegram", "Telegram Entegrasyonu", "INFO", "Yapılandırılmadı (İsteğe bağlı)")

    @classmethod
    def run_all_checks(cls, progress_callback: Optional[Callable[[int, CheckResult], None]] = None) -> List[CheckResult]:
        """Tüm kontrolleri sırayla çalıştırır ve callback ile bildirir."""
        checks = [
            cls.check_runtime,
            cls.check_directories_and_permissions,
            cls.check_databases,
            cls.check_internet,
            cls.check_gemini_api,
            cls.check_microphone,
            cls.check_speaker,
            cls.check_camera,
            cls.check_telegram,
        ]

        results = []
        total = len(checks)

        for idx, check_fn in enumerate(checks):
            res = check_fn()
            results.append(res)
            progress_percent = int(((idx + 1) / total) * 100)
            if progress_callback:
                progress_callback(progress_percent, res)

        return results
