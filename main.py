"""
LopixAI - Kişisel Yapay Zeka Asistanı
Ana Başlatıcı (Main Entry Point)
Windows 10/11 x64, Sıfır Teknik Kurulum, %APPDATA%\\.lopixai\\ Veri Yönetimi
"""

import sys
import os
from pathlib import Path

# Proje kök dizinini sys.path'e ekle ve çalışma dizinini ayarla
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Herhangi bir konumdan çalışabilmek için çalışma dizinini script'in dizinine ayarla
os.chdir(ROOT_DIR)

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from app.core.config import ensure_data_directories, APP_TITLE
from app.core.logger import setup_logger, get_logger
from app.core.settings import SettingsManager
from app.database.db_manager import DBManager
from app.gui.theme import DARK_THEME_QSS
from app.gui.splash import SplashScreen
from app.gui.main_window import MainWindow

def main():
    """LopixAI ana başlatma döngüsü."""
    # 1. Loglama ve Çekirdek Dizinler
    logger = setup_logger()
    logger.info("LopixAI başlatılıyor...")

    try:
        ensure_data_directories()
        DBManager.initialize_databases()
        SettingsManager.load()
    except Exception as e:
        logger.critical(f"Çekirdek başlatma hatası: {e}", exc_info=True)
        print(f"Kritik Başlatma Hatası: {e}", file=sys.stderr)
        return 1

    # 2. PyQt6 Uygulaması
    app = QApplication(sys.argv)
    app.setApplicationName("LopixAI")
    app.setApplicationDisplayName(APP_TITLE)
    
    # Uygulama Simgesi (LopixAI Logo)
    icon_path = ROOT_DIR / "app" / "assets" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
        
    app.setStyleSheet(DARK_THEME_QSS)

    # 3. Sistem Kontrolü Açılış Ekranı (Product Rule #15)
    show_splash = SettingsManager.get("system_check_on_startup", True)
    if show_splash:
        splash = SplashScreen()
        splash.exec()

    # 4. Ana Pencere
    try:
        window = MainWindow()
        window.show()
    except Exception as e:
        logger.critical(f"Ana pencere oluşturulamadı: {e}", exc_info=True)
        QMessageBox.critical(
            None,
            "LopixAI - Hata",
            f"Uygulama arayüzü başlatılırken bir hata oluştu:\n{e}\n\nDetaylar için logs/errors.log dosyasını inceleyebilirsiniz."
        )
        return 1

    logger.info("LopixAI arayüzü başarıyla açıldı.")
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
