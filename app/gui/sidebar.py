"""
LopixAI Sol Kenar Çubuğu (Product Rules #6, #7, #10, #11)
ChatGPT benzeri sol panel: Yeni Sohbet, Arama, Sohbet Listesi ve ⋮ Menüsü.
"""

import time
import datetime
from typing import Optional, List, Dict
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QLabel, QScrollArea, QFrame, QMenu, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QAction, QCursor

from app.core.config import APP_TITLE, APP_VERSION
from app.database.chat_repo import ChatRepository, Conversation
from app.gui.dialogs import DeleteConfirmDialog, RenameDialog, SettingsDialog
from app.core.logger import get_logger

logger = get_logger("Sidebar")

class ChatItemWidget(QFrame):
    """Sohbet listesindeki tek bir satır öğesi."""

    def __init__(self, conversation: Conversation, is_active: bool = False, parent=None):
        super().__init__(parent)
        self.conversation = conversation
        self.is_active = is_active
        self._init_ui()

    def _init_ui(self):
        self.setFixedHeight(40)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(6)

        # Pin İkonu
        if self.conversation.is_pinned:
            lbl_pin = QLabel("📌")
            lbl_pin.setStyleSheet("font-size: 11px; background: transparent;")
            layout.addWidget(lbl_pin)

        # Sohbet Başlık Butonu
        title_text = self.conversation.title
        self.btn_select = QPushButton(title_text)
        self.btn_select.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.btn_select.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # Aktif/Pasif Stil
        active_class = "chat-item-btn-active" if self.is_active else "chat-item-btn"
        self.btn_select.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                text-align: left;
                color: {'#ffffff' if self.is_active else '#d1d5db'};
                font-weight: {'600' if self.is_active else 'normal'};
                font-size: 13px;
                padding-left: 4px;
            }}
            QPushButton:hover {{
                color: #ffffff;
            }}
        """)
        layout.addWidget(self.btn_select)

        # Üç Nokta Menü Butonu (⋮)
        self.btn_menu = QPushButton("⋮")
        self.btn_menu.setFixedSize(26, 26)
        self.btn_menu.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_menu.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #9ca3af;
                font-size: 15px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2b2e38;
                color: #ffffff;
            }
        """)
        layout.addWidget(self.btn_menu)

        # QFrame Arka Planı
        bg_color = "#252833" if self.is_active else "transparent"
        border_css = "border-left: 3px solid #6366f1;" if self.is_active else "border: none;"
        self.setStyleSheet(f"""
            ChatItemWidget {{
                background-color: {bg_color};
                border-radius: 6px;
                {border_css}
            }}
            ChatItemWidget:hover {{
                background-color: {'#2a2d38' if self.is_active else '#1e2027'};
            }}
        """)


class SidebarWidget(QWidget):
    """Sol Sohbet Yönetim Paneli."""

    chat_selected = pyqtSignal(str)       # conv_id
    new_chat_requested = pyqtSignal()
    chat_deleted = pyqtSignal(str)        # conv_id
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebarWidget")
        self.setFixedWidth(280)
        self.active_conv_id: Optional[str] = None
        self._item_widgets: Dict[str, ChatItemWidget] = {}

        self._init_ui()
        self.refresh_chat_list()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(12)

        # 1. Başlık & Logo
        header_box = QHBoxLayout()
        lbl_logo = QLabel(APP_TITLE)
        lbl_logo.setObjectName("logoLabel")
        lbl_logo.setStyleSheet("font-size: 17px; font-weight: 800; color: #ffffff;")

        badge = QLabel(f"v{APP_VERSION}")
        badge.setObjectName("versionBadge")
        badge.setStyleSheet("font-size: 10px; background-color: #262832; color: #a5b4fc; border-radius: 4px; padding: 2px 6px;")

        header_box.addWidget(lbl_logo)
        header_box.addWidget(badge)
        header_box.addStretch()

        layout.addLayout(header_box)

        # 2. Yeni Sohbet Butonu (＋ Yeni sohbet)
        self.btn_new_chat = QPushButton("＋  Yeni sohbet")
        self.btn_new_chat.setObjectName("btnNewChat")
        self.btn_new_chat.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_new_chat.clicked.connect(self._on_new_chat_clicked)
        layout.addWidget(self.btn_new_chat)

        # 3. Sohbetlerde Ara (🔍 Sohbetlerde ara)
        self.search_input = QLineEdit()
        self.search_input.setObjectName("searchBar")
        self.search_input.setPlaceholderText("🔍  Sohbetlerde ara...")
        self.search_input.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.search_input)

        # 4. Sohbet Listesi Kaydırma Alanı
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.list_container = QWidget()
        self.list_container.setObjectName("chatListContainer")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 4, 0, 4)
        self.list_layout.setSpacing(4)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.list_container)
        layout.addWidget(self.scroll_area)

        # 5. Alt Ayarlar Butonu
        bottom_box = QHBoxLayout()
        self.btn_settings = QPushButton("⚙️  Ayarlar")
        self.btn_settings.setProperty("class", "secondary-btn")
        self.btn_settings.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_settings.clicked.connect(self._open_settings)

        bottom_box.addWidget(self.btn_settings)
        layout.addLayout(bottom_box)

    def _on_new_chat_clicked(self):
        self.new_chat_requested.emit()

    def _on_search_changed(self, text: str):
        self.refresh_chat_list(query=text.strip())

    def refresh_chat_list(self, query: str = ""):
        """Sohbet listesini SQLite'tan yeniden yükler."""
        # Eski öğeleri temizle
        while self.list_layout.count():
            child = self.list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self._item_widgets.clear()

        # Veritabanından sohbetleri al
        if query:
            conversations = ChatRepository.search_conversations(query)
        else:
            conversations = ChatRepository.get_all_conversations()

        if not conversations:
            lbl_empty = QLabel("Henüz sohbet yok" if not query else "Sonuç bulunamadı")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_empty.setStyleSheet("color: #6b7280; font-size: 12px; padding: 24px 0;")
            self.list_layout.addWidget(lbl_empty)
            return

        # Zaman bazlı gruplandırma veya listeleme
        # Pinned önce, sonra Bugün, Dün, Önceki Günler
        now = time.time()
        today_start = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        yesterday_start = today_start - 86400

        current_group = ""

        for conv in conversations:
            # Grup belirle
            if conv.is_pinned:
                group_name = "📌 Sabitlenenler"
            elif conv.updated_at >= today_start:
                group_name = "Bugün"
            elif conv.updated_at >= yesterday_start:
                group_name = "Dün"
            else:
                group_name = "Daha Eski"

            if group_name != current_group:
                current_group = group_name
                lbl_group = QLabel(current_group)
                lbl_group.setStyleSheet("font-size: 11px; font-weight: 700; color: #6b7280; padding: 10px 4px 4px 4px;")
                self.list_layout.addWidget(lbl_group)

            is_active = (conv.id == self.active_conv_id)
            item_widget = ChatItemWidget(conv, is_active=is_active)
            
            # Tıklama bağla
            item_widget.btn_select.clicked.connect(lambda _, cid=conv.id: self._on_chat_selected(cid))
            # Menü bağla
            item_widget.btn_menu.clicked.connect(lambda _, c=conv, w=item_widget: self._show_chat_menu(c, w))

            self._item_widgets[conv.id] = item_widget
            self.list_layout.addWidget(item_widget)

    def _on_chat_selected(self, conv_id: str):
        self.active_conv_id = conv_id
        self.chat_selected.emit(conv_id)
        self.refresh_chat_list(query=self.search_input.text().strip())

    def set_active_conversation(self, conv_id: str):
        """Dışarıdan aktif sohbeti ayarlar."""
        self.active_conv_id = conv_id
        self.refresh_chat_list(query=self.search_input.text().strip())

    def _show_chat_menu(self, conv: Conversation, item_widget: ChatItemWidget):
        """Üç nokta (⋮) tıklandığında menüyü açar."""
        menu = QMenu(self)

        # 1. ✏️ Yeniden adlandır
        act_rename = QAction("✏️  Yeniden adlandır", self)
        act_rename.triggered.connect(lambda: self._action_rename(conv))
        menu.addAction(act_rename)

        # 2. 📌 Sabitle / Sabitlemeyi Kaldır
        pin_label = "📌  Sabitlemeyi Kaldır" if conv.is_pinned else "📌  Sabitle"
        act_pin = QAction(pin_label, self)
        act_pin.triggered.connect(lambda: self._action_toggle_pin(conv))
        menu.addAction(act_pin)

        menu.addSeparator()

        # 3. 🗑️ Sil
        act_delete = QAction("🗑️  Sil", self)
        act_delete.triggered.connect(lambda: self._action_delete(conv))
        menu.addAction(act_delete)

        menu.exec(QCursor.pos())

    def _action_rename(self, conv: Conversation):
        dialog = RenameDialog(conv.title, self)
        if dialog.exec():
            new_title = dialog.get_new_title()
            if new_title and new_title != conv.title:
                ChatRepository.rename_conversation(conv.id, new_title)
                self.refresh_chat_list(query=self.search_input.text().strip())

    def _action_toggle_pin(self, conv: Conversation):
        ChatRepository.set_pinned(conv.id, not conv.is_pinned)
        self.refresh_chat_list(query=self.search_input.text().strip())

    def _action_delete(self, conv: Conversation):
        dialog = DeleteConfirmDialog(conv.title, self)
        if dialog.exec():
            ChatRepository.delete_conversation(conv.id)
            self.chat_deleted.emit(conv.id)
            self.refresh_chat_list(query=self.search_input.text().strip())

    def _open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            self.settings_changed.emit()
