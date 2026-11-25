"""
LopixAI Sistem Kontrol Ekranı (Product Rule #15)
İlk açılışta runtime, ses, kamera, ağ ve veritabanı kontrollerini görsel olarak gösterir.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QWidget, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon

from app.core.system_check import SystemChecker, CheckResult
from app.core.logger import get_logger

logger = get_logger("SplashScreen")

class SystemCheckWorker(QThread):
    """Sistem kontrollerini arka planda yürüten thread."""
    progress_updated = pyqtSignal(int, object)  # (percent, CheckResult)
    finished_checks = pyqtSignal(list)

    def run(self):
        results = []
        def callback(pct, res):
            results.append(res)
            self.progress_updated.emit(pct, res)
            self.msleep(140)  # Akıcı görsel geçiş için hafif bekleme

        SystemChecker.run_all_checks(progress_callback=callback)
        self.finished_checks.emit(results)


class SplashScreen(QDialog):
    """Sistem Teşhis ve Açılış Ekranı."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LopixAI - Başlatılıyor")
        self.setFixedSize(480, 520)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self._init_ui()
        self._start_checks()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        # Üst Başlık
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        
        self.lbl_logo = QLabel("✦ LOPIXAI")
        self.lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_logo.setStyleSheet("font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: 2px;")
        
        self.lbl_sub = QLabel("Sistem kontrol ediliyor...")
        self.lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_sub.setStyleSheet("font-size: 13px; color: #9ca3af; font-weight: 500;")

        title_box.addWidget(self.lbl_logo)
        title_box.addWidget(self.lbl_sub)
        layout.addLayout(title_box)

        # İlerleme Çubuğu
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)

        # Kontrol Listesi Kartı
        list_frame = QFrame()
        list_frame.setStyleSheet("""
            QFrame {
                background-color: #17181c;
                border: 1px solid #23252b;
                border-radius: 10px;
            }
        """)
        self.list_layout = QVBoxLayout(list_frame)
        self.list_layout.setContentsMargins(16, 16, 16, 16)
        self.list_layout.setSpacing(10)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Scroll Alanı
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(list_frame)
        layout.addWidget(scroll)

        # Alt Bilgi
        self.lbl_status = QLabel("Bileşenler taranıyor...")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("font-size: 11px; color: #6b7280;")
        layout.addWidget(self.lbl_status)

    def _start_checks(self):
        self.worker = SystemCheckWorker()
        self.worker.progress_updated.connect(self._on_check_item)
        self.worker.finished_checks.connect(self._on_all_finished)
        self.worker.start()

    def _on_check_item(self, pct: int, res: CheckResult):
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(f"{res.title}: {res.message}")

        # Liste elemanı ekle
        row = QHBoxLayout()
        row.setSpacing(10)

        # Durum ikonu
        if res.status == "OK":
            icon_lbl = QLabel("✓")
            icon_lbl.setStyleSheet("color: #10b981; font-weight: bold; font-size: 14px;")
        elif res.status == "WARN":
            icon_lbl = QLabel("⚠")
            icon_lbl.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 14px;")
        elif res.status == "INFO":
            icon_lbl = QLabel("ℹ")
            icon_lbl.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 14px;")
        else:
            icon_lbl = QLabel("✕")
            icon_lbl.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 14px;")

        icon_lbl.setFixedWidth(20)

        name_lbl = QLabel(res.title)
        name_lbl.setStyleSheet("color: #f3f4f6; font-weight: 600; font-size: 12px;")

        msg_lbl = QLabel(res.message)
        msg_lbl.setStyleSheet("color: #9ca3af; font-size: 11px;")
        msg_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        row.addWidget(icon_lbl)
        row.addWidget(name_lbl)
        row.addStretch()
        row.addWidget(msg_lbl)

        self.list_layout.addLayout(row)

    def _on_all_finished(self, results):
        self.progress_bar.setValue(100)
        self.lbl_sub.setText("Sistem hazır. Başlatılıyor...")
        self.lbl_sub.setStyleSheet("font-size: 13px; color: #10b981; font-weight: 600;")
        # 500 ms sonra pencereyi kapat ve ana ekrana geç
        QTimer.singleShot(600, self.accept)
