"""
LopixAI Dizin ve Yapılandırma Yöneticisi
Tüm kullanıcı verileri %APPDATA%\\.lopixai\\ altında tutulur.
"""

import os
import sys
from pathlib import Path

# Uygulama Temel Bilgileri
APP_NAME = "LopixAI"
APP_VERSION = "0.1.0"
APP_TITLE = "✦ LopixAI"

# %APPDATA% veya sistem uyumlu kullanıcı veri klasörü
def get_app_data_dir() -> Path:
    """Windows %APPDATA%\\.lopixai klasör yolunu döner."""
    appdata = os.getenv("APPDATA")
    if appdata:
        base_dir = Path(appdata)
    else:
        # Fallback (geliştirme veya farklı ortamlar için)
        base_dir = Path.home() / "AppData" / "Roaming"
    
    lopixai_dir = base_dir / ".lopixai"
    return lopixai_dir

# Temel Yollar
DATA_DIR = get_app_data_dir()

# Veritabanları ve Dosyalar
CHATS_DB_PATH = DATA_DIR / "chats.db"
MEMORY_DB_PATH = DATA_DIR / "memory.db"
SETTINGS_PATH = DATA_DIR / "settings.json"
SECRETS_PATH = DATA_DIR / "secrets.dat"

# Alt Klasörler
LOGS_DIR = DATA_DIR / "logs"
CACHE_DIR = DATA_DIR / "cache"
VOICE_DIR = DATA_DIR / "voice"
VOICE_CACHE_DIR = VOICE_DIR / "cache"
VOICE_SETTINGS_PATH = VOICE_DIR / "settings.json"

SECURITY_DIR = DATA_DIR / "security"
SECURITY_EVENTS_DIR = SECURITY_DIR / "events"
SECURITY_SETTINGS_PATH = SECURITY_DIR / "settings.json"

AGENT_DIR = DATA_DIR / "agent"
AGENT_WORKSPACE_DIR = AGENT_DIR / "workspace"
AGENT_HISTORY_DIR = AGENT_DIR / "history"

# Log Dosyaları
LOG_FILE = LOGS_DIR / "lopixai.log"
ERROR_LOG_FILE = LOGS_DIR / "errors.log"

def ensure_data_directories() -> None:
    """
    Kullanıcının %APPDATA%\\.lopixai klasör hiyerarşisini
    güvenli ve eksiksiz bir şekilde oluşturur.
    Program güncellendiğinde veya yeniden kurulduğunda mevcut veriler silinmez.
    """
    directories = [
        DATA_DIR,
        LOGS_DIR,
        CACHE_DIR,
        VOICE_DIR,
        VOICE_CACHE_DIR,
        SECURITY_DIR,
        SECURITY_EVENTS_DIR,
        AGENT_DIR,
        AGENT_WORKSPACE_DIR,
        AGENT_HISTORY_DIR,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    # Varsayılan ayar dosyaları yoksa boş JSON olarak oluştur
    if not VOICE_SETTINGS_PATH.exists():
        try:
            VOICE_SETTINGS_PATH.write_text("{}", encoding="utf-8")
        except Exception:
            pass

    if not SECURITY_SETTINGS_PATH.exists():
        try:
            SECURITY_SETTINGS_PATH.write_text("{}", encoding="utf-8")
        except Exception:
            pass
