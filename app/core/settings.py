"""
LopixAI Ayarlar Yöneticisi
Kullanıcı tercihleri .lopixai/settings.json dosyasında tutulur.
Hassas veriler (API key, token) burada ASLA tutulmaz, secrets.dat'ta saklanır.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import SETTINGS_PATH, ensure_data_directories
from app.core.logger import get_logger

logger = get_logger("Settings")

DEFAULT_SETTINGS: Dict[str, Any] = {
    "version": "1.0",
    "theme": "dark",
    "auto_title": True,
    "auto_scroll": True,
    "voice_enabled": False,
    "system_check_on_startup": True,
    "telegram_enabled": False,
    "max_context_messages": 20,
    "offline_fallback_enabled": True,
    # Sohbet Görünümü ve Renk Temaları
    "chat_theme_preset": "neon_cyan",  # neon_cyan, indigo, emerald, amethyst, oled, custom
    "user_bubble_color": "#0e7490",
    "ai_bubble_color": "#151922",
    "chat_bg_color": "#0d0f15",
    "accent_color": "#06b6d4"
}

class SettingsManager:
    """settings.json yönetim sınıfı."""
    _settings: Dict[str, Any] = {}
    _loaded: bool = False

    @classmethod
    def load(cls) -> Dict[str, Any]:
        """Ayarları yükler, eksik anahtarları varsayılanlarla tamamlar."""
        ensure_data_directories()
        if not SETTINGS_PATH.exists():
            cls._settings = DEFAULT_SETTINGS.copy()
            cls.save()
            cls._loaded = True
            return cls._settings

        try:
            content = SETTINGS_PATH.read_text(encoding="utf-8")
            data = json.loads(content)
            # Eksik varsayılanları ekle
            for key, val in DEFAULT_SETTINGS.items():
                if key not in data:
                    data[key] = val
            cls._settings = data
            cls._loaded = True
        except Exception as e:
            logger.error(f"Ayarlar dosyası yüklenemedi, varsayılanlar kullanılacak: {e}")
            cls._settings = DEFAULT_SETTINGS.copy()
            cls._loaded = True

        return cls._settings

    @classmethod
    def save(cls) -> None:
        """Ayarları diske kaydeder."""
        try:
            ensure_data_directories()
            json_str = json.dumps(cls._settings, indent=4, ensure_ascii=False)
            SETTINGS_PATH.write_text(json_str, encoding="utf-8")
            logger.debug("Ayarlar kaydedildi.")
        except Exception as e:
            logger.error(f"Ayarlar kaydedilirken hata oluştu: {e}")

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """Belirtilen ayar değerini döner."""
        if not cls._loaded:
            cls.load()
        return cls._settings.get(key, default)

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        """Ayar değerini günceller ve kaydeder."""
        if not cls._loaded:
            cls.load()
        cls._settings[key] = value
        cls.save()

    @classmethod
    def reset_defaults(cls) -> None:
        """Ayarları varsayılanlara sıfırlar."""
        cls._settings = DEFAULT_SETTINGS.copy()
        cls.save()
