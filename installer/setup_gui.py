"""
LopixAI Kurulum Sihirbazı (Product Rules #1, #16)
LopixAI-Setup.exe
Kullanıcıdan hiçbir teknik bilgi, Python veya model kurulumu istemez.
Seçilen program klasörüne dosyaları kurar, masaüstü kısayolu ve başlangıç ayarlarını yapar.
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QProgressBar,
    QFileDialog, QFrame, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QCursor

# Kurulum Sabitleri
APP_NAME = "LopixAI"
DEFAULT_INSTALL_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Programs" / "LopixAI"


def create_windows_shortcut(target_exe: Path, shortcut_path: Path, description: str = "LopixAI Kişisel Yapay Zeka Asistanı"):
    """PowerShell / WScript.Shell kullanarak Windows .lnk kısayolu oluşturur."""
    target_str = str(target_exe).replace("'", "''")
    shortcut_str = str(shortcut_path).replace("'", "''")
    working_dir = str(target_exe.parent).replace("'", "''")

    ps_script = f"""
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('{shortcut_str}')
    $Shortcut.TargetPath = '{target_str}'
    $Shortcut.WorkingDirectory = '{working_dir}'
    $Shortcut.Description = '{description}'
    $Shortcut.Save()
    """
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=True,
            timeout=10
        )
    except Exception as e:
        print(f"Kısayol oluşturma hatası: {e}", file=sys.stderr)


class InstallWorker(QThread):
    """Dosya kopyalama ve kurulum işlemlerini yürüten thread."""
    progress_updated = pyqtSignal(int, str)
    install_completed = pyqtSignal(bool, str)

    def __init__(self, target_dir: Path, make_desktop_shortcut: bool, run_on_startup: bool):
        super().__init__()
        self.target_dir = target_dir
        self.make_desktop_shortcut = make_desktop_shortcut
        self.run_on_startup = run_on_startup

    def run(self):
        try:
            self.progress_updated.emit(10, "Hedef klasör hazırlanıyor...")
            self.target_dir.mkdir(parents=True, exist_ok=True)

            # Kaynak dosyalar (Uygulama kök dizini)
            source_dir = Path(__file__).resolve().parent.parent
            self.progress_updated.emit(25, "Uygulama ve bileşenler kopyalanıyor...")

            items_to_copy = ["app", "main.py", "run.bat", "requirements.txt", "README.md"]
            total_items = len(items_to_copy)

            for idx, item_name in enumerate(items_to_copy, 1):
                src_item = source_dir / item_name
                dst_item = self.target_dir / item_name
                if src_item.exists():
                    if src_item.is_dir():
                        if dst_item.exists():
                            shutil.rmtree(dst_item)
                        shutil.copytree(src_item, dst_item)
                    else:
                        shutil.copy2(src_item, dst_item)
                pct = 25 + int((idx / total_items) * 45)
                self.progress_updated.emit(pct, f"Kopyalanıyor: {item_name}")
                self.msleep(60)

            # Hedef çalıştırılabilir dosya
            target_exe = self.target_dir / "LopixAI.exe"
            if not target_exe.exists():
                # Geliştirme/kaynak modunda run.bat kısayol hedeflenir
                target_exe = self.target_dir / "run.bat"

            # Masaüstü Kısayolu
            if self.make_desktop_shortcut:
                self.progress_updated.emit(78, "Masaüstü kısayolu oluşturuluyor...")
                desktop_dir = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
                shortcut_file = desktop_dir / "LopixAI.lnk"
                create_windows_shortcut(target_exe, shortcut_file)

            # Başlangıçta Çalıştır
            if self.run_on_startup:
                self.progress_updated.emit(90, "Başlangıç ayarları yapılandırılıyor...")
                startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
                if startup_dir.exists():
                    startup_shortcut = startup_dir / "LopixAI.lnk"
                    create_windows_shortcut(target_exe, startup_shortcut)

            self.progress_updated.emit(100, "Kurulum tamamlandı!")
            self.install_completed.emit(True, "Kurulum başarıyla tamamlandı.")

        except Exception as e:
            self.install_completed.emit(False, f"Kurulum sırasında hata oluştu:\n{e}")


class LopixAISetupDialog(QWidget):
    """
    LopixAI Modern Kurulum Ekranı (Product Rule #16).
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LopixAI Setup")
        self.setFixedSize(560, 440)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.MSWindowsFixedSizeDialogHint)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        # 1. Başlık
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        
        lbl_title = QLabel("✦ LopixAI Setup")
        lbl_title.setStyleSheet("font-size: 22px; font-weight: 800; color: #ffffff;")
        
        lbl_desc = QLabel("LopixAI kişisel yapay zeka asistanı bilgisayarınıza kurulacak.")
        lbl_desc.setStyleSheet("font-size: 13px; color: #9ca3af;")
        
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_desc)
        layout.addLayout(title_box)

        # Ayırıcı
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #262832;")
        layout.addWidget(sep)

        # 2. Kurulum Konumu
        loc_box = QVBoxLayout()
        loc_box.setSpacing(6)
        
        lbl_loc = QLabel("Kurulum konumu:")
        lbl_loc.setStyleSheet("font-size: 12px; font-weight: 600; color: #e5e7eb;")
        loc_box.addWidget(lbl_loc)

        dir_box = QHBoxLayout()
        self.input_dir = QLineEdit(str(DEFAULT_INSTALL_DIR))
        self.input_dir.setStyleSheet("""
            QLineEdit {
                background-color: #1e2026;
                border: 1px solid #32353f;
                border-radius: 8px;
                padding: 8px 12px;
                color: #ffffff;
                font-size: 12px;
            }
        """)
        
        self.btn_browse = QPushButton("Gözat...")
        self.btn_browse.setStyleSheet("""
            QPushButton {
                background-color: #2a2d36;
                color: #e5e7eb;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #353844;
            }
        """)
        self.btn_browse.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_browse.clicked.connect(self._browse_dir)

        dir_box.addWidget(self.input_dir)
        dir_box.addWidget(self.btn_browse)
        loc_box.addLayout(dir_box)

        lbl_data_note = QLabel("ℹ️ <i>Kullanıcı verileri (sohbetler, hafıza) ayrı olarak %APPDATA%\\.lopixai\\ altında korunacaktır.</i>")
        lbl_data_note.setStyleSheet("font-size: 11px; color: #6b7280;")
        loc_box.addWidget(lbl_data_note)

        layout.addLayout(loc_box)

        # 3. Seçenekler
        opt_box = QVBoxLayout()
        opt_box.setSpacing(8)

        self.chk_desktop = QCheckBox("Masaüstü kısayolu oluştur")
        self.chk_desktop.setChecked(True)
        self.chk_desktop.setStyleSheet("color: #d1d5db; font-size: 13px;")

        self.chk_startup = QCheckBox("Windows başlangıcında çalıştır")
        self.chk_startup.setChecked(False)
        self.chk_startup.setStyleSheet("color: #d1d5db; font-size: 13px;")

        opt_box.addWidget(self.chk_desktop)
        opt_box.addWidget(self.chk_startup)
        layout.addLayout(opt_box)

        # 4. İlerleme Çubuğu ve Durum
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #1e2026;
                border-radius: 6px;
                height: 12px;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #06b6d4);
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("font-size: 11px; color: #38bdf8;")
        self.lbl_status.setVisible(False)
        layout.addWidget(self.lbl_status)

        layout.addStretch()

        # 5. Alt Butonlar
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #262830;
                color: #d1d5db;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2f323c;
            }
        """)
        self.btn_cancel.clicked.connect(self.close)

        self.btn_install = QPushButton("  Kur  ")
        self.btn_install.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #6366f1);
                color: #ffffff;
                font-weight: 700;
                border-radius: 8px;
                padding: 10px 28px;
                font-size: 13px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:1 #4f46e5);
            }
        """)
        self.btn_install.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_install.clicked.connect(self._start_install)

        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_install)
        layout.addLayout(btn_box)

        # Stil
        self.setStyleSheet("""
            QWidget {
                background-color: #121316;
                color: #e5e7eb;
                font-family: "Segoe UI", sans-serif;
            }
        """)

    def _browse_dir(self):
        chosen = QFileDialog.getExistingDirectory(self, "Kurulum Klasörünü Seçin", self.input_dir.text())
        if chosen:
            self.input_dir.setText(str(Path(chosen) / "LopixAI"))

    def _start_install(self):
        target_path = Path(self.input_dir.text().strip())
        if not target_path:
            QMessageBox.warning(self, "Uyarı", "Lütfen geçerli bir kurulum dizini belirleyin.")
            return

        self.btn_install.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.btn_browse.setEnabled(False)
        self.input_dir.setEnabled(False)
        self.chk_desktop.setEnabled(False)
        self.chk_startup.setEnabled(False)

        self.progress_bar.setVisible(True)
        self.lbl_status.setVisible(True)

        self.worker = InstallWorker(
            target_dir=target_path,
            make_desktop_shortcut=self.chk_desktop.isChecked(),
            run_on_startup=self.chk_startup.isChecked()
        )
        self.worker.progress_updated.connect(self._on_progress)
        self.worker.install_completed.connect(self._on_completed)
        self.worker.start()

    def _on_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(msg)

    def _on_completed(self, success: bool, message: str):
        if success:
            self.btn_install.setText("Bitir ve Başlat")
            self.btn_install.setEnabled(True)
            self.btn_install.clicked.disconnect()
            self.btn_install.clicked.connect(self._launch_and_exit)

            self.btn_cancel.setText("Kapat")
            self.btn_cancel.setEnabled(True)

            self.lbl_status.setText("✓ Kurulum tamamlandı! LopixAI kullanıma hazır.")
            self.lbl_status.setStyleSheet("font-size: 12px; color: #10b981; font-weight: bold;")
        else:
            QMessageBox.critical(self, "Kurulum Hatası", message)
            self.btn_cancel.setEnabled(True)
            self.btn_install.setEnabled(True)

    def _launch_and_exit(self):
        target_path = Path(self.input_dir.text().strip())
        target_exe = target_path / "LopixAI.exe"
        if not target_exe.exists():
            target_exe = target_path / "run.bat"

        try:
            if target_exe.exists():
                subprocess.Popen([str(target_exe)], cwd=str(target_path), shell=True)
        except Exception as e:
            print(f"Başlatma hatası: {e}", file=sys.stderr)

        self.close()


def main():
    app = QApplication(sys.argv)
    wizard = LopixAISetupDialog()
    wizard.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
