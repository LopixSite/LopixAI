"""
LopixAI Loglama Sistemi
Hatalar ve genel işlemler .lopixai/logs/ altında lopixai.log ve errors.log dosyalarına yazılır.
Kullanıcıya karmaşık traceback göstermek yerine anlaşılır mesajlar verilir.
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from app.core.config import LOG_FILE, ERROR_LOG_FILE, ensure_data_directories

_logger_initialized = False

def setup_logger() -> logging.Logger:
    """Uygulama loglama altyapısını başlatır ve yapılandırır."""
    global _logger_initialized
    logger = logging.getLogger("LopixAI")
    
    if _logger_initialized:
        return logger

    ensure_data_directories()
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Log formatı
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] (%(name)s - %(filename)s:%(lineno)d): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Genel Log Dosyası (lopixai.log) - 5 MB rotasyon, 3 yedek
    try:
        general_handler = RotatingFileHandler(
            filename=str(LOG_FILE),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        general_handler.setLevel(logging.INFO)
        general_handler.setFormatter(formatter)
        logger.addHandler(general_handler)
    except Exception as e:
        print(f"[LopixAI Log Init Error] General handler failed: {e}", file=sys.stderr)

    # 2. Hata Log Dosyası (errors.log) - Sadece ERROR ve CRITICAL
    try:
        error_handler = RotatingFileHandler(
            filename=str(ERROR_LOG_FILE),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
    except Exception as e:
        print(f"[LopixAI Log Init Error] Error handler failed: {e}", file=sys.stderr)

    # 3. Konsol Çıktısı (Geliştirme ve teşhis için)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_formatter = logging.Formatter(
        fmt="[%(levelname)s] %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    _logger_initialized = True
    logger.info("LopixAI loglama sistemi başarıyla başlatıldı.")
    return logger

def get_logger(name: str = "LopixAI") -> logging.Logger:
    """Belirtilen alt modül için logger döner."""
    if not _logger_initialized:
        setup_logger()
    return logging.getLogger(f"LopixAI.{name}")
