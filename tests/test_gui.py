"""
LopixAI PyQt6 Arayüz Testi (Headless & Widget Doğrulama)
Arayüz bileşenlerinin hatasız oluşturulabildiğini ve sinyal/slot bağlantılarını test eder.
"""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer

from app.core.config import ensure_data_directories
from app.database.db_manager import DBManager
from app.database.chat_repo import ChatRepository
from app.gui.theme import DARK_THEME_QSS
from app.gui.main_window import MainWindow
from app.gui.sidebar import SidebarWidget
from app.gui.chat_view import ChatViewWidget
from app.gui.dialogs import RenameDialog, DeleteConfirmDialog, SettingsDialog


class TestLopixAIGUI(unittest.TestCase):
    """PyQt6 GUI Testleri."""

    @classmethod
    def setUpClass(cls):
        ensure_data_directories()
        DBManager.initialize_databases()
        cls.app = QApplication.instance() or QApplication(sys.argv)
        cls.app.setStyleSheet(DARK_THEME_QSS)

    def test_01_main_window_lifecycle(self):
        """MainWindow oluşturuluyor, gösteriliyor ve kapanabiliyor mu?"""
        win = MainWindow()
        self.assertIsNotNone(win)
        self.assertIsNotNone(win.sidebar)
        self.assertIsNotNone(win.chat_view)

        # Yeni sohbet sinyali
        initial_count = len(ChatRepository.get_all_conversations())
        win.sidebar.btn_new_chat.click()
        new_count = len(ChatRepository.get_all_conversations())
        self.assertEqual(new_count, initial_count + 1)

        win.close()

    def test_02_dialogs_instantiation(self):
        """Diyaloglar hatasız açılabiliyor mu?"""
        conv = ChatRepository.create_conversation("Diyalog Testi")
        
        del_dlg = DeleteConfirmDialog(conv.title)
        self.assertEqual(del_dlg.btn_delete.text(), "Sil")
        del_dlg.close()

        ren_dlg = RenameDialog(conv.title)
        self.assertEqual(ren_dlg.get_new_title(), "Diyalog Testi")
        ren_dlg.close()

        set_dlg = SettingsDialog()
        self.assertIsNotNone(set_dlg.input_api_key)
        set_dlg.close()

        ChatRepository.delete_conversation(conv.id)


if __name__ == "__main__":
    unittest.main()
