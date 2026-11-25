"""
LopixAI Güvenli Veri ve Anahtar Yönetimi (Windows DPAPI)
Gemini API Key, Telegram Bot Token gibi hassas veriler düz metin olarak saklanmaz.
Windows Data Protection API (DPAPI) ile şifrelenerek secrets.dat dosyasında tutulur.
"""

import os
import sys
import json
import base64
import ctypes
from ctypes import wintypes
from pathlib import Path
from typing import Optional, Dict, Any

from app.core.config import SECRETS_PATH, ensure_data_directories
from app.core.logger import get_logger

logger = get_logger("Secrets")

# DPAPI Veri Yapıları
class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte))
    ]

def _win32_encrypt(data_bytes: bytes) -> bytes:
    """Windows CryptProtectData ile veriyi şifreler."""
    if sys.platform != "win32":
        # Windows dışı test ortamları için base64 simülasyonu
        return base64.b64encode(data_bytes)

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    in_blob = DATA_BLOB()
    in_blob.cbData = len(data_bytes)
    in_blob.pbData = ctypes.cast(ctypes.create_string_buffer(data_bytes), ctypes.POINTER(ctypes.c_byte))

    out_blob = DATA_BLOB()

    # CRYPTPROTECT_UI_FORBIDDEN = 0x1
    res = crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        "LopixAI Secret",
        None,
        None,
        None,
        0x1,
        ctypes.byref(out_blob)
    )

    if not res:
        raise OSError("Windows DPAPI şifreleme hatası (CryptProtectData başarısız).")

    encrypted_bytes = ctypes.string_at(out_blob.pbData, out_blob.cbData)
    kernel32.LocalFree(out_blob.pbData)
    return encrypted_bytes

def _win32_decrypt(encrypted_bytes: bytes) -> bytes:
    """Windows CryptUnprotectData ile şifrelenmiş veriyi çözer."""
    if sys.platform != "win32":
        return base64.b64decode(encrypted_bytes)

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    in_blob = DATA_BLOB()
    in_blob.cbData = len(encrypted_bytes)
    in_blob.pbData = ctypes.cast(ctypes.create_string_buffer(encrypted_bytes), ctypes.POINTER(ctypes.c_byte))

    out_blob = DATA_BLOB()

    res = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0x1,
        ctypes.byref(out_blob)
    )

    if not res:
        raise OSError("Windows DPAPI şifre çözme hatası (CryptUnprotectData başarısız).")

    decrypted_bytes = ctypes.string_at(out_blob.pbData, out_blob.cbData)
    kernel32.LocalFree(out_blob.pbData)
    return decrypted_bytes


class SecretsManager:
    """
    secrets.dat dosyasında DPAPI ile şifrelenmiş anahtarları yöneten sınıf.
    """
    _cache: Dict[str, str] = {}
    _loaded: bool = False

    @classmethod
    def _load(cls) -> None:
        if cls._loaded:
            return

        ensure_data_directories()
        if not SECRETS_PATH.exists():
            cls._cache = {}
            cls._loaded = True
            return

        try:
            raw_data = SECRETS_PATH.read_bytes()
            if not raw_data:
                cls._cache = {}
                cls._loaded = True
                return

            decrypted = _win32_decrypt(raw_data)
            cls._cache = json.loads(decrypted.decode("utf-8"))
            cls._loaded = True
        except Exception as e:
            logger.error(f"Secrets dosyası okunamadı veya şifre çözülemedi: {e}")
            cls._cache = {}
            cls._loaded = True

    @classmethod
    def _save(cls) -> None:
        try:
            ensure_data_directories()
            json_bytes = json.dumps(cls._cache, ensure_ascii=False).encode("utf-8")
            encrypted = _win32_encrypt(json_bytes)
            SECRETS_PATH.write_bytes(encrypted)
            logger.debug("Secrets başarıyla DPAPI ile kaydedildi.")
        except Exception as e:
            logger.error(f"Secrets kaydedilirken hata oluştu: {e}")

    @classmethod
    def get_secret(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        """Güvenli anahtar değerini döner."""
        cls._load()
        return cls._cache.get(key, default)

    @classmethod
    def set_secret(cls, key: str, value: str) -> None:
        """Hassas veriyi şifreli olarak kaydeder."""
        cls._load()
        cls._cache[key] = value
        cls._save()

    @classmethod
    def delete_secret(cls, key: str) -> None:
        """Kayıtlı anahtarı siler."""
        cls._load()
        if key in cls._cache:
            del cls._cache[key]
            cls._save()

    @classmethod
    def has_secret(cls, key: str) -> bool:
        """Belirtilen anahtarın varlığını kontrol eder."""
        cls._load()
        val = cls._cache.get(key)
        return bool(val and val.strip())

    @classmethod
    def get_gemini_api_key(cls) -> Optional[str]:
        """Gemini API Key döner."""
        return cls.get_secret("gemini_api_key")

    @classmethod
    def set_gemini_api_key(cls, api_key: str) -> None:
        """Gemini API Key kaydeder."""
        cls.set_secret("gemini_api_key", api_key.strip())

    @classmethod
    def get_telegram_token(cls) -> Optional[str]:
        """Telegram Bot Token döner."""
        return cls.get_secret("telegram_bot_token")

    @classmethod
    def set_telegram_token(cls, token: str) -> None:
        """Telegram Bot Token kaydeder."""
        cls.set_secret("telegram_bot_token", token.strip())
