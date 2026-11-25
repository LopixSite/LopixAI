"""
LopixAI Modalları ve İletişim Pencereleri (Product Rules #10, #13, #14)
Sohbet silme onayı, yeniden adlandırma ve güvenli Ayarlar/API anahtarı/Telegram yönetimi.
Gemini modeli tam otomatik yönetilir; kullanıcıdan sürüm seçimi istenmez.
"""

import re
from typing import Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QFrame, QMessageBox, QWidget,
    QTabWidget, QComboBox, QColorDialog, QGridLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QCursor, QColor

from app.core.secrets import SecretsManager
from app.core.settings import SettingsManager
from app.telegram.bridge import TelegramAPI, TelegramBridge
from app.gui.theme import THEME_PRESETS, get_current_theme_colors
from app.core.logger import get_logger

logger = get_logger("Dialogs")

class DeleteConfirmDialog(QDialog):
    """Sohbet Silme Onay Modalı (Product Rule #10)."""
    def __init__(self, chat_title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sohbeti Sil")
        self.setFixedSize(400, 180)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        lbl_msg = QLabel(f"“<b>{chat_title}</b>” sohbeti silinsin mi?")
        lbl_msg.setWordWrap(True)
        lbl_msg.setStyleSheet("font-size: 14px; color: #f3f4f6;")
        layout.addWidget(lbl_msg)

        lbl_sub = QLabel("Bu işlem geri alınamaz. Sohbet ve mesaj geçmişi kaldırılacaktır.")
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet("font-size: 12px; color: #9ca3af;")
        layout.addWidget(lbl_sub)

        layout.addStretch()

        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        btn_box.addStretch()

        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setProperty("class", "secondary-btn")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_delete = QPushButton("Sil")
        self.btn_delete.setProperty("class", "danger-btn")
        self.btn_delete.clicked.connect(self.accept)

        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_delete)
        layout.addLayout(btn_box)


class RenameDialog(QDialog):
    """Sohbet Yeniden Adlandırma Modalı (Product Rule #10)."""
    def __init__(self, current_title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sohbeti Yeniden Adlandır")
        self.setFixedSize(420, 190)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        lbl = QLabel("Sohbet Başlığı:")
        lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #f3f4f6;")
        layout.addWidget(lbl)

        self.input_title = QLineEdit()
        self.input_title.setText(current_title)
        self.input_title.setProperty("class", "dialog-input")
        self.input_title.selectAll()
        layout.addWidget(self.input_title)

        layout.addStretch()

        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        btn_box.addStretch()

        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setProperty("class", "secondary-btn")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Kaydet")
        self.btn_save.setProperty("class", "primary-btn")
        self.btn_save.clicked.connect(self._on_save)

        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_save)
        layout.addLayout(btn_box)

    def _on_save(self):
        new_title = self.input_title.text().strip()
        if new_title:
            self.accept()
        else:
            self.input_title.setFocus()

    def get_new_title(self) -> str:
        return self.input_title.text().strip()


class GeminiTestWorker(QThread):
    """Gemini API anahtarını arka planda test eden thread."""
    test_completed = pyqtSignal(bool, str)

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key

    def run(self):
        from app.ai.gemini_service import GeminiService
        success, msg = GeminiService.test_connection(self.api_key)
        self.test_completed.emit(success, msg)


class TelegramTestWorker(QThread):
    """Telegram token testini arka planda yürüten thread."""
    test_completed = pyqtSignal(bool, str)

    def __init__(self, token: str):
        super().__init__()
        self.token = token

    def run(self):
        success, msg, _ = TelegramAPI.test_token(self.token)
        self.test_completed.emit(success, msg)


class SettingsDialog(QDialog):
    """
    LopixAI Ayarlar Modalı (Product Rules #13, #14).
    Renk ve tema özelleştirmeleri, Gemini API Key ve Telegram Bot Token yönetimi.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LopixAI - Ayarlar ve Görünüm")
        self.setFixedSize(580, 640)
        self.setModal(True)

        # Aktif renk durumları
        self.current_theme = SettingsManager.get("chat_theme_preset", "neon_cyan")
        self.color_user_bubble = SettingsManager.get("user_bubble_color", "#0891b2")
        self.color_ai_bubble = SettingsManager.get("ai_bubble_color", "#111622")
        self.color_chat_bg = SettingsManager.get("chat_bg_color", "#090b10")
        self.color_accent = SettingsManager.get("accent_color", "#06b6d4")

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 18)
        main_layout.setSpacing(14)

        # Başlık Çubuğu
        header_box = QHBoxLayout()
        title_lbl = QLabel("⚙️  LopixAI Ayarları")
        title_lbl.setStyleSheet("font-size: 17px; font-weight: 800; color: #ffffff;")
        header_box.addWidget(title_lbl)
        header_box.addStretch()
        main_layout.addLayout(header_box)

        # QTabWidget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #282a36;
                background-color: #16171d;
                border-radius: 8px;
                padding: 12px;
            }
            QTabBar::tab {
                background-color: #1a1b22;
                color: #9ca3af;
                padding: 8px 18px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 600;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background-color: #242735;
                color: #38bdf8;
                border-bottom: 2px solid #06b6d4;
            }
            QTabBar::tab:hover {
                color: #ffffff;
            }
        """)

        # 1. SEKME: 🎨 Sohbet Görünümü & Renkler
        tab_theme = QWidget()
        self._setup_theme_tab(tab_theme)
        self.tabs.addTab(tab_theme, "🎨 Sohbet Renkleri")

        # 2. SEKME: 🤖 Yapay Zeka (Gemini)
        tab_ai = QWidget()
        self._setup_ai_tab(tab_ai)
        self.tabs.addTab(tab_ai, "🤖 Yapay Zeka")

        # 3. SEKME: ✈️ Telegram & Sistem
        tab_system = QWidget()
        self._setup_system_tab(tab_system)
        self.tabs.addTab(tab_system, "✈️ Telegram & Sistem")

        main_layout.addWidget(self.tabs)

        # Alt Butonlar
        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        btn_box.addStretch()

        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.setProperty("class", "secondary-btn")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Kaydet ve Uygula")
        self.btn_save.setProperty("class", "primary-btn")
        self.btn_save.clicked.connect(self._save_settings)

        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_save)
        main_layout.addLayout(btn_box)

    def _setup_theme_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        # Açıklama
        lbl_info = QLabel("Sohbet alanının ve mesaj baloncuklarının renklerini zevkinize göre özelleştirin.")
        lbl_info.setStyleSheet("font-size: 12px; color: #9ca3af;")
        layout.addWidget(lbl_info)

        # Hazır Tema Seçimi
        preset_box = QHBoxLayout()
        lbl_preset = QLabel("🎨 Hazır Renk Teması:")
        lbl_preset.setStyleSheet("font-size: 13px; font-weight: 700; color: #f3f4f6;")
        
        self.combo_theme = QComboBox()
        self.combo_theme.setStyleSheet("""
            QComboBox {
                background-color: #21242f;
                border: 1px solid #33384a;
                border-radius: 8px;
                padding: 6px 12px;
                color: #ffffff;
                font-size: 12px;
                min-width: 260px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #1a1c24;
                color: #ffffff;
                selection-background-color: #0891b2;
                border: 1px solid #33384a;
            }
        """)
        for key, p in THEME_PRESETS.items():
            self.combo_theme.addItem(p["name"], key)
        
        self.combo_theme.currentIndexChanged.connect(self._on_theme_preset_changed)
        preset_box.addWidget(lbl_preset)
        preset_box.addWidget(self.combo_theme)
        preset_box.addStretch()
        layout.addLayout(preset_box)

        # Renk Butonları Izgarası (Grid)
        grid = QGridLayout()
        grid.setSpacing(10)

        # 1. Kullanıcı Baloncuğu Rengi
        lbl_user_color = QLabel("Kullanıcı Mesajı:")
        lbl_user_color.setStyleSheet("color: #d1d5db; font-weight: 600; font-size: 12px;")
        self.btn_user_color = QPushButton()
        self.btn_user_color.setFixedHeight(30)
        self.btn_user_color.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_user_color.clicked.connect(lambda: self._pick_color("user"))
        grid.addWidget(lbl_user_color, 0, 0)
        grid.addWidget(self.btn_user_color, 0, 1)

        # 2. LopixAI Yanıt Baloncuğu Rengi
        lbl_ai_color = QLabel("LopixAI Mesajı:")
        lbl_ai_color.setStyleSheet("color: #d1d5db; font-weight: 600; font-size: 12px;")
        self.btn_ai_color = QPushButton()
        self.btn_ai_color.setFixedHeight(30)
        self.btn_ai_color.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_ai_color.clicked.connect(lambda: self._pick_color("ai"))
        grid.addWidget(lbl_ai_color, 0, 2)
        grid.addWidget(self.btn_ai_color, 0, 3)

        # 3. Sohbet Arka Plan Rengi
        lbl_bg_color = QLabel("Sohbet Arka Planı:")
        lbl_bg_color.setStyleSheet("color: #d1d5db; font-weight: 600; font-size: 12px;")
        self.btn_bg_color = QPushButton()
        self.btn_bg_color.setFixedHeight(30)
        self.btn_bg_color.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_bg_color.clicked.connect(lambda: self._pick_color("bg"))
        grid.addWidget(lbl_bg_color, 1, 0)
        grid.addWidget(self.btn_bg_color, 1, 1)

        # 4. Vurgu / Aksan Rengi
        lbl_acc_color = QLabel("Vurgu & İkon Rengi:")
        lbl_acc_color.setStyleSheet("color: #d1d5db; font-weight: 600; font-size: 12px;")
        self.btn_acc_color = QPushButton()
        self.btn_acc_color.setFixedHeight(30)
        self.btn_acc_color.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_acc_color.clicked.connect(lambda: self._pick_color("accent"))
        grid.addWidget(lbl_acc_color, 1, 2)
        grid.addWidget(self.btn_acc_color, 1, 3)

        layout.addLayout(grid)

        # Canlı Önizleme Alanı
        lbl_preview_title = QLabel("Canlı Görünüm Önizlemesi:")
        lbl_preview_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #a5b4fc; margin-top: 6px;")
        layout.addWidget(lbl_preview_title)

        self.preview_frame = QFrame()
        self.preview_frame.setFixedHeight(150)
        self.preview_frame.setStyleSheet("border-radius: 10px; padding: 8px;")
        prev_layout = QVBoxLayout(self.preview_frame)
        prev_layout.setContentsMargins(12, 10, 12, 10)
        prev_layout.setSpacing(8)

        # Örnek Kullanıcı Balonu
        self.prev_user_card = QFrame()
        self.prev_user_card.setMaximumWidth(320)
        user_c_layout = QVBoxLayout(self.prev_user_card)
        user_c_layout.setContentsMargins(12, 6, 12, 6)
        self.prev_user_lbl = QLabel("Siz: Merhaba LopixAI, bugün nasılsın?")
        self.prev_user_lbl.setStyleSheet("font-size: 12px; color: #ffffff;")
        user_c_layout.addWidget(self.prev_user_lbl)
        
        user_box = QHBoxLayout()
        user_box.addStretch()
        user_box.addWidget(self.prev_user_card)
        prev_layout.addLayout(user_box)

        # Örnek LopixAI Balonu
        self.prev_ai_card = QFrame()
        self.prev_ai_card.setMaximumWidth(360)
        ai_c_layout = QVBoxLayout(self.prev_ai_card)
        ai_c_layout.setContentsMargins(12, 6, 12, 6)
        self.prev_ai_lbl = QLabel("✦ LopixAI: Harikayım! 100+ siteden bilgi toplamaya ve size yardımcı olmaya hazırım.")
        self.prev_ai_lbl.setWordWrap(True)
        self.prev_ai_lbl.setStyleSheet("font-size: 12px; color: #f3f4f6;")
        ai_c_layout.addWidget(self.prev_ai_lbl)

        ai_box = QHBoxLayout()
        ai_box.addWidget(self.prev_ai_card)
        ai_box.addStretch()
        prev_layout.addLayout(ai_box)

        layout.addWidget(self.preview_frame)
        layout.addStretch()

    def _setup_ai_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(14)

        lbl_gemini_title = QLabel("✦ Gemini API Yapılandırması (Otomatik Model)")
        lbl_gemini_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #a5b4fc;")
        layout.addWidget(lbl_gemini_title)

        lbl_key = QLabel("Gemini API Anahtarı:")
        lbl_key.setStyleSheet("font-size: 12px; font-weight: 600; color: #e5e7eb;")
        layout.addWidget(lbl_key)

        key_input_box = QHBoxLayout()
        self.input_api_key = QLineEdit()
        self.input_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_api_key.setPlaceholderText("AIzaSy...")
        self.input_api_key.setProperty("class", "dialog-input")

        self.btn_toggle_key = QPushButton("👁")
        self.btn_toggle_key.setFixedWidth(38)
        self.btn_toggle_key.setProperty("class", "secondary-btn")
        self.btn_toggle_key.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_toggle_key.clicked.connect(self._toggle_key_visibility)

        self.btn_test_gemini = QPushButton("Bağlan / Test Et")
        self.btn_test_gemini.setProperty("class", "primary-btn")
        self.btn_test_gemini.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_test_gemini.clicked.connect(self._test_gemini_connection)

        key_input_box.addWidget(self.input_api_key)
        key_input_box.addWidget(self.btn_toggle_key)
        key_input_box.addWidget(self.btn_test_gemini)
        layout.addLayout(key_input_box)

        self.lbl_gemini_status = QLabel("⚪ Bağlantı durumu: Bekleniyor")
        self.lbl_gemini_status.setStyleSheet("font-size: 11px; color: #9ca3af;")
        layout.addWidget(self.lbl_gemini_status)

        lbl_fallback_info = QLabel(
            "🌐 <b>API Anahtarı Olmadığında Ne Olur?</b><br>"
            "LopixAI otomatik olarak <b>Derin Web Arama Motoru</b>'na geçer. Reddit, Wikipedia, "
            "StackOverflow, Quora, GitHub ve 100+ popüler siteden soru ve sorunlarınızı tamamen "
            "inceleyerek Türkçe kapsamlı yanıt derler."
        )
        lbl_fallback_info.setWordWrap(True)
        lbl_fallback_info.setStyleSheet("font-size: 11px; color: #38bdf8; background-color: #121e29; border: 1px solid #1f3b52; border-radius: 8px; padding: 10px;")
        layout.addWidget(lbl_fallback_info)

        layout.addStretch()

    def _setup_system_tab(self, parent: QWidget):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(14)

        lbl_tg_title = QLabel("✈️ Telegram Bot Bağlantısı")
        lbl_tg_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #38bdf8;")
        layout.addWidget(lbl_tg_title)

        lbl_tg_desc = QLabel("Masaüstü sohbetlerinizle senkronize çalışacak Telegram Bot Token:")
        lbl_tg_desc.setStyleSheet("font-size: 12px; color: #9ca3af;")
        layout.addWidget(lbl_tg_desc)

        tg_input_box = QHBoxLayout()
        self.input_tg_token = QLineEdit()
        self.input_tg_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_tg_token.setPlaceholderText("123456789:ABCdefGHIjklmn...")
        self.input_tg_token.setProperty("class", "dialog-input")

        self.btn_toggle_tg = QPushButton("👁")
        self.btn_toggle_tg.setFixedWidth(38)
        self.btn_toggle_tg.setProperty("class", "secondary-btn")
        self.btn_toggle_tg.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_toggle_tg.clicked.connect(self._toggle_tg_visibility)

        self.btn_test_tg = QPushButton("Bağlan / Test Et")
        self.btn_test_tg.setProperty("class", "primary-btn")
        self.btn_test_tg.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_test_tg.clicked.connect(self._test_telegram_connection)

        tg_input_box.addWidget(self.input_tg_token)
        tg_input_box.addWidget(self.btn_toggle_tg)
        tg_input_box.addWidget(self.btn_test_tg)
        layout.addLayout(tg_input_box)

        self.lbl_tg_status = QLabel("⚪ Bağlantı durumu: Bekleniyor")
        self.lbl_tg_status.setStyleSheet("font-size: 11px; color: #9ca3af;")
        layout.addWidget(self.lbl_tg_status)

        self.chk_tg_enabled = QCheckBox("Telegram Botunu arka planda sürekli dinle")
        self.chk_tg_enabled.setStyleSheet("color: #d1d5db; font-size: 12px;")
        layout.addWidget(self.chk_tg_enabled)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #262832;")
        layout.addWidget(sep)

        lbl_gen_title = QLabel("⚙️ Genel Seçenekler")
        lbl_gen_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #f3f4f6;")
        layout.addWidget(lbl_gen_title)

        self.chk_auto_title = QCheckBox("İlk kullanıcı mesajından otomatik sohbet başlığı üret")
        self.chk_auto_title.setChecked(True)
        self.chk_auto_title.setStyleSheet("color: #d1d5db; font-size: 12px;")
        layout.addWidget(self.chk_auto_title)

        self.chk_system_check = QCheckBox("Uygulama açılışında sistem kontrolü ekranını göster")
        self.chk_system_check.setChecked(True)
        self.chk_system_check.setStyleSheet("color: #d1d5db; font-size: 12px;")
        layout.addWidget(self.chk_system_check)

        lbl_learner_info = QLabel("🧠 <i>Otonom Öğrenme Motoru aktif: Kullanıcının sohbet ilgi alanlarına göre her 1 dk'de bir arka planda bilgi hafızaya alınır.</i>")
        lbl_learner_info.setStyleSheet("font-size: 11px; color: #10b981; padding-top: 4px;")
        layout.addWidget(lbl_learner_info)

        layout.addStretch()

    def _on_theme_preset_changed(self, idx: int):
        preset_key = self.combo_theme.currentData()
        if preset_key and preset_key in THEME_PRESETS and preset_key != "custom":
            p = THEME_PRESETS[preset_key]
            self.color_user_bubble = p["user_bubble"]
            self.color_ai_bubble = p["ai_bubble"]
            self.color_chat_bg = p["chat_bg"]
            self.color_accent = p["accent"]
            self._update_color_buttons_and_preview()

    def _pick_color(self, target: str):
        current_hex = {
            "user": self.color_user_bubble,
            "ai": self.color_ai_bubble,
            "bg": self.color_chat_bg,
            "accent": self.color_accent
        }.get(target, "#ffffff")

        color = QColorDialog.getColor(QColor(current_hex), self, "Renk Seç")
        if color.isValid():
            new_hex = color.name()
            if target == "user":
                self.color_user_bubble = new_hex
            elif target == "ai":
                self.color_ai_bubble = new_hex
            elif target == "bg":
                self.color_chat_bg = new_hex
            elif target == "accent":
                self.color_accent = new_hex

            # Custom presetine geçir
            custom_idx = self.combo_theme.findData("custom")
            if custom_idx >= 0:
                self.combo_theme.blockSignals(True)
                self.combo_theme.setCurrentIndex(custom_idx)
                self.combo_theme.blockSignals(False)

            self._update_color_buttons_and_preview()

    def _update_color_buttons_and_preview(self):
        # Buton stillerini güncelle
        def btn_style(hex_color):
            return f"background-color: {hex_color}; color: #ffffff; border: 1px solid #475569; border-radius: 6px; font-weight: 700; font-size: 11px; text-align: center;"

        self.btn_user_color.setStyleSheet(btn_style(self.color_user_bubble))
        self.btn_user_color.setText(self.color_user_bubble)

        self.btn_ai_color.setStyleSheet(btn_style(self.color_ai_bubble))
        self.btn_ai_color.setText(self.color_ai_bubble)

        self.btn_bg_color.setStyleSheet(btn_style(self.color_chat_bg))
        self.btn_bg_color.setText(self.color_chat_bg)

        self.btn_acc_color.setStyleSheet(btn_style(self.color_accent))
        self.btn_acc_color.setText(self.color_accent)

        # Canlı Önizlemeyi güncelle
        self.preview_frame.setStyleSheet(f"background-color: {self.color_chat_bg}; border: 1px solid #282a38; border-radius: 10px;")
        self.prev_user_card.setStyleSheet(f"background-color: {self.color_user_bubble}; border-radius: 12px; border-top-right-radius: 3px;")
        self.prev_ai_card.setStyleSheet(f"background-color: {self.color_ai_bubble}; border: 1px solid #282a38; border-radius: 12px; border-top-left-radius: 3px;")

    def _load_data(self):
        # Tema ve renkleri yükle
        preset_key = SettingsManager.get("chat_theme_preset", "neon_cyan")
        idx = self.combo_theme.findData(preset_key)
        if idx >= 0:
            self.combo_theme.setCurrentIndex(idx)
        self.color_user_bubble = SettingsManager.get("user_bubble_color", "#0891b2")
        self.color_ai_bubble = SettingsManager.get("ai_bubble_color", "#111622")
        self.color_chat_bg = SettingsManager.get("chat_bg_color", "#090b10")
        self.color_accent = SettingsManager.get("accent_color", "#06b6d4")
        self._update_color_buttons_and_preview()
        # API anahtarını yükle
        current_key = SecretsManager.get_gemini_api_key() or ""
        self.input_api_key.setText(current_key)
        if current_key:
            self.lbl_gemini_status.setText("🟢 Anahtar kayıtlı (Test etmek için butona basın)")
            self.lbl_gemini_status.setStyleSheet("color: #10b981; font-size: 11px;")

        # Telegram token'ını yükle
        current_tg = SecretsManager.get_telegram_token() or ""
        self.input_tg_token.setText(current_tg)
        if current_tg:
            self.lbl_tg_status.setText("🟡 Token kayıtlı (Test etmek için butona basın)")
            self.lbl_tg_status.setStyleSheet("color: #f59e0b; font-size: 11px;")

        self.chk_tg_enabled.setChecked(SettingsManager.get("telegram_enabled", False))
        self.chk_auto_title.setChecked(SettingsManager.get("auto_title", True))
        self.chk_system_check.setChecked(SettingsManager.get("system_check_on_startup", True))

    @staticmethod
    def _clean_key(raw: str) -> str:
        """API anahtarı ve tokenları tırnak, boşluk ve gizli karakterlerden arındırır."""
        k = raw.strip().strip("'\"").strip()
        k = re.sub(r"[\r\n\t\u200b\u200c\u200d\ufeff ]+", "", k)
        return k

    def _test_gemini_connection(self):
        key = self._clean_key(self.input_api_key.text())
        if not key:
            self.lbl_gemini_status.setText("⚠️ Lütfen önce bir Gemini API anahtarı girin.")
            self.lbl_gemini_status.setStyleSheet("color: #f59e0b; font-size: 11px;")
            return

        self.lbl_gemini_status.setText("⏳ Gemini API ile bağlantı test ediliyor...")
        self.lbl_gemini_status.setStyleSheet("color: #38bdf8; font-size: 11px;")
        self.btn_test_gemini.setEnabled(False)

        self.gemini_test_worker = GeminiTestWorker(key)
        self.gemini_test_worker.test_completed.connect(self._on_gemini_test_result)
        self.gemini_test_worker.start()

    def _on_gemini_test_result(self, success: bool, message: str):
        self.btn_test_gemini.setEnabled(True)
        if success:
            self.lbl_gemini_status.setText(f"✓ {message}")
            self.lbl_gemini_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        else:
            self.lbl_gemini_status.setText(f"✕ {message}")
            self.lbl_gemini_status.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 11px;")

    def _toggle_key_visibility(self):
        if self.input_api_key.echoMode() == QLineEdit.EchoMode.Password:
            self.input_api_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_key.setText("🔒")
        else:
            self.input_api_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_key.setText("👁")

    def _toggle_tg_visibility(self):
        if self.input_tg_token.echoMode() == QLineEdit.EchoMode.Password:
            self.input_tg_token.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_tg.setText("🔒")
        else:
            self.input_tg_token.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_tg.setText("👁")

    def _test_telegram_connection(self):
        token = self.input_tg_token.text().strip()
        if not token:
            self.lbl_tg_status.setText("⚠️ Lütfen önce bir bot token girin.")
            self.lbl_tg_status.setStyleSheet("color: #f59e0b; font-size: 11px;")
            return

        self.lbl_tg_status.setText("⏳ Telegram API ile bağlantı test ediliyor...")
        self.lbl_tg_status.setStyleSheet("color: #38bdf8; font-size: 11px;")
        self.btn_test_tg.setEnabled(False)

        self.test_worker = TelegramTestWorker(token)
        self.test_worker.test_completed.connect(self._on_tg_test_result)
        self.test_worker.start()

    def _on_tg_test_result(self, success: bool, message: str):
        self.btn_test_tg.setEnabled(True)
        if success:
            self.lbl_tg_status.setText(f"✓ {message}")
            self.lbl_tg_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        else:
            self.lbl_tg_status.setText(f"✕ {message}")
            self.lbl_tg_status.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 11px;")

    def _save_settings(self):
        # Gemini API Key kaydet
        new_key = self._clean_key(self.input_api_key.text())
        if new_key:
            SecretsManager.set_gemini_api_key(new_key)
        else:
            SecretsManager.delete_secret("gemini_api_key")

        # Telegram Token kaydet
        new_tg = self._clean_key(self.input_tg_token.text())
        if new_tg:
            SecretsManager.set_telegram_token(new_tg)
        else:
            SecretsManager.delete_secret("telegram_bot_token")

        # Ayarları kaydet
        tg_enabled = self.chk_tg_enabled.isChecked()
        SettingsManager.set("telegram_enabled", tg_enabled)
        SettingsManager.set("auto_title", self.chk_auto_title.isChecked())
        SettingsManager.set("system_check_on_startup", self.chk_system_check.isChecked())

        # Tema ve renk ayarlarını kaydet
        selected_theme = self.combo_theme.currentData() or "neon_cyan"
        SettingsManager.set("chat_theme_preset", selected_theme)
        SettingsManager.set("user_bubble_color", self.color_user_bubble)
        SettingsManager.set("ai_bubble_color", self.color_ai_bubble)
        SettingsManager.set("chat_bg_color", self.color_chat_bg)
        SettingsManager.set("accent_color", self.color_accent)

        # Telegram bot servisini başlat / durdur
        if tg_enabled and new_tg:
            TelegramBridge.start_polling()
        else:
            TelegramBridge.stop_polling()

        self.accept()
