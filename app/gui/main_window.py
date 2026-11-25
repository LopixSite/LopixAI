"""
LopixAI Ana Penceresi (Product Rules #6, #7, #21)
Sol sidebar ve sağ chat görünümünü entegre eder, tüm durum geçişlerini yönetir.
"""

from typing import Optional
from PyQt6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QSplitter
from PyQt6.QtCore import Qt

from app.core.config import APP_TITLE, APP_VERSION
from app.core.settings import SettingsManager
from app.database.chat_repo import ChatRepository, Conversation
from app.gui.sidebar import SidebarWidget
from app.gui.chat_view import ChatViewWidget
from app.telegram.bridge import TelegramBridge
from app.core.logger import get_logger

logger = get_logger("MainWindow")

class MainWindow(QMainWindow):
    """LopixAI Ana Uygulama Penceresi."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} - Kişisel Yapay Zeka Asistanı")
        self.resize(1150, 780)
        self.setMinimumSize(850, 550)

        self._init_ui()
        self._load_initial_state()
        self._init_telegram_service()
        self._init_knowledge_learner()

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # QSplitter ile kullanıcı boyutlandırabilir arayüz
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #23252b;
            }
        """)

        # Sol Panel (Sidebar)
        self.sidebar = SidebarWidget()
        self.splitter.addWidget(self.sidebar)

        # Sağ Panel (Sohbet Görünümü)
        self.chat_view = ChatViewWidget()
        self.splitter.addWidget(self.chat_view)

        # Başlangıç boyut oranları: Sol 280px, Sağ kalan alan
        self.splitter.setSizes([280, 870])
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)

        main_layout.addWidget(self.splitter)

        # Sinyal Bağlantıları
        self.sidebar.chat_selected.connect(self._on_chat_selected)
        self.sidebar.new_chat_requested.connect(self._on_new_chat_requested)
        self.sidebar.chat_deleted.connect(self._on_chat_deleted)
        self.sidebar.settings_changed.connect(self._on_settings_changed)
        self.chat_view.title_updated.connect(self._on_title_updated)

    def _init_telegram_service(self):
        """Telegram arka plan dinleyicisini başlatır (Eğer ayarlardan etkinse)."""
        if SettingsManager.get("telegram_enabled", False):
            TelegramBridge.start_polling(on_sync_callback=self._on_telegram_sync)

    def _on_telegram_sync(self, conv_id: str):
        """Telegram'dan yeni mesaj geldiğinde arayüzü canlı yenile."""
        self.sidebar.refresh_chat_list()
        if self.chat_view.conversation and self.chat_view.conversation.id == conv_id:
            self.chat_view.load_conversation(conv_id)

    def _load_initial_state(self):
        """Uygulama açılışında son sohbeti yükler veya yeni oluşturur."""
        conversations = ChatRepository.get_all_conversations()
        if conversations:
            active_conv = conversations[0]
        else:
            active_conv = ChatRepository.create_conversation("Yeni sohbet")

        self.sidebar.set_active_conversation(active_conv.id)
        self.chat_view.load_conversation(active_conv.id)
        logger.info(f"Başlangıç sohbeti yüklendi: {active_conv.id} - '{active_conv.title}'")

    def _on_chat_selected(self, conv_id: str):
        """Kullanıcı sol listeden bir sohbete tıkladığında."""
        self.chat_view.load_conversation(conv_id)

    def _on_new_chat_requested(self):
        """＋ Yeni sohbet butonuna tıklandığında (Product Rule #7)."""
        new_conv = ChatRepository.create_conversation("Yeni sohbet")
        self.sidebar.set_active_conversation(new_conv.id)
        self.chat_view.load_conversation(new_conv.id)

    def _on_chat_deleted(self, deleted_conv_id: str):
        """Aktif sohbet silindiyse başka bir sohbete geç (Product Rule #10)."""
        if self.chat_view.conversation and self.chat_view.conversation.id == deleted_conv_id:
            remaining = ChatRepository.get_all_conversations()
            if remaining:
                next_conv = remaining[0]
            else:
                next_conv = ChatRepository.create_conversation("Yeni sohbet")

            self.sidebar.set_active_conversation(next_conv.id)
            self.chat_view.load_conversation(next_conv.id)

    def _on_title_updated(self, conv_id: str, new_title: str):
        """İlk mesajla veya yeniden adlandırmayla başlık güncellendiğinde."""
        self.sidebar.refresh_chat_list()

    def _on_settings_changed(self):
        """Ayarlar değiştiğinde göstergeleri ve temayı güncelle."""
        self.chat_view.update_status_indicator()
        self.chat_view.apply_theme()

    def _init_knowledge_learner(self):
        """Her 1 dakikada bir kullanıcının tüm sohbetlerine göre otonom bilgi öğrenen servis."""
        try:
            from app.ai.knowledge_learner import KnowledgeLearner
            self.learner = KnowledgeLearner(interval_seconds=60, parent=self)
            self.learner.knowledge_learned.connect(self._on_knowledge_learned)
            self.learner.start()
        except Exception as e:
            logger.error(f"KnowledgeLearner başlatılamadı: {e}")

    def _on_knowledge_learned(self, topic: str, title: str):
        logger.info(f"[Otonom Öğrenme] Yerel hafıza genişletildi: {topic} -> {title}")

    def closeEvent(self, event):
        """Uygulama kapanırken arka plan servislerini durdur."""
        if hasattr(self, 'learner') and self.learner:
            self.learner.stop()
            self.learner.wait(1500)
        super().closeEvent(event)
