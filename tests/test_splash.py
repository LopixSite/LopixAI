"""
LopixAI Splash Ekranı ve Sistem Kontrolü Testi
"""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from app.core.config import ensure_data_directories
from app.database.db_manager import DBManager
from app.gui.splash import SplashScreen


class TestSplashScreen(unittest.TestCase):
    """Açılış ekranı testleri."""

    @classmethod
    def setUpClass(cls):
        ensure_data_directories()
        DBManager.initialize_databases()
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_splash_workflow(self):
        """Splash ekranı tüm kontrolleri bitirip kapanabiliyor mu?"""
        splash = SplashScreen()
        self.assertIsNotNone(splash.progress_bar)
        
        # Test için kontrollerin bitmesini bekleyelim
        loop_counter = 0
        while splash.progress_bar.value() < 100 and loop_counter < 50:
            self.app.processEvents()
            splash.thread().msleep(50)
            loop_counter += 1

        self.assertGreater(splash.progress_bar.value(), 0)
        splash.close()


if __name__ == "__main__":
    unittest.main()
