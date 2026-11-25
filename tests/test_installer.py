"""
LopixAI Kurulum Sihirbazı Arayüz Testi (Setup GUI)
"""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from PyQt6.QtWidgets import QApplication
from installer.setup_gui import LopixAISetupDialog, DEFAULT_INSTALL_DIR

class TestInstallerGUI(unittest.TestCase):
    """Kurulum sihirbazı testleri."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def test_installer_instantiation(self):
        """Setup penceresi doğru bileşenlerle açılıyor mu?"""
        wizard = LopixAISetupDialog()
        self.assertIsNotNone(wizard.input_dir)
        self.assertEqual(wizard.input_dir.text(), str(DEFAULT_INSTALL_DIR))
        self.assertTrue(wizard.chk_desktop.isChecked())
        self.assertFalse(wizard.chk_startup.isChecked())
        self.assertIn("Kur", wizard.btn_install.text())
        wizard.close()

if __name__ == "__main__":
    unittest.main()
