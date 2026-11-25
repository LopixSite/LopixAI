"""
LopixAI Modern Sohbet Arayüzü ve Yazı Animasyonu (Product Rules #3, #6, #8, #9, #21)
ChatGPT / Claude benzeri modern merkezlenmiş tasarım, daktilo (streaming) yazı animasyonu,
hoş geldiniz başlangıç kartları, kopyalama butonu ve akıcı kaydırma.
"""

import time
import datetime
from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QScrollArea, QFrame, QSizePolicy, QApplication, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont, QTextCursor, QCursor, QClipboard

from app.database.chat_repo import ChatRepository, Conversation, Message
from app.ai.gemini_service import GeminiService
from app.core.settings import SettingsManager
from app.gui.theme import get_current_theme_colors
from app.core.logger import get_logger

logger = get_logger("ChatView")


class AIWorker(QThread):
    """Gemini API veya Offline yanıtını arka planda üreten thread."""
    finished = pyqtSignal(str, bool)  # (reply_text, is_offline)

    def __init__(self, conversation_id: str, prompt: str):
        super().__init__()
        self.conversation_id = conversation_id
        self.prompt = prompt

    def run(self):
        try:
            reply, is_offline = GeminiService.send_message(self.conversation_id, self.prompt)
            self.finished.emit(reply, is_offline)
        except Exception as e:
            logger.error(f"AI Worker hatası: {e}")
            self.finished.emit(f"Hata oluştu: {e}", True)


class MessageBubble(QFrame):
    """Modern ve kompakt mesaj kartı (Kullanıcı veya LopixAI)."""

    def __init__(self, message: Message, parent=None):
        super().__init__(parent)
        self.message = message
        self.raw_content = message.content
        self.content_card: Optional[QFrame] = None
        self.lbl_avatar: Optional[QLabel] = None
        self._init_ui()

    def _init_ui(self):
        is_user = (self.message.role == "user")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 2, 0, 4)
        main_layout.setSpacing(3)

        # Mesaj Konteyneri (Ortalanmış ve Maksimum Genişlikli)
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(10)

        if is_user:
            row_layout.addStretch(1)

        # Asistan Avatarı (Kompakt 28x28)
        if not is_user:
            avatar_box = QVBoxLayout()
            avatar_box.setAlignment(Qt.AlignmentFlag.AlignTop)
            self.lbl_avatar = QLabel("✦")
            self.lbl_avatar.setFixedSize(28, 28)
            self.lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar_box.addWidget(self.lbl_avatar)
            row_layout.addLayout(avatar_box)

        # Mesaj İçerik Kartı (Kompakt Padding)
        self.content_card = QFrame()
        card_layout = QVBoxLayout(self.content_card)
        card_layout.setContentsMargins(14, 8, 14, 8)
        card_layout.setSpacing(5)

        # Üst Bilgi (Rol ve Saat)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        time_str = datetime.datetime.fromtimestamp(self.message.timestamp).strftime("%H:%M")
        
        if is_user:
            lbl_role = QLabel("Siz")
            lbl_role.setStyleSheet("font-weight: 700; color: #bae6fd; font-size: 11px;")
            lbl_time = QLabel(time_str)
            lbl_time.setStyleSheet("color: #9ca3af; font-size: 10px;")
            header_layout.addWidget(lbl_time)
            header_layout.addStretch()
            header_layout.addWidget(lbl_role)
        else:
            lbl_role = QLabel("LopixAI")
            lbl_role.setStyleSheet("font-weight: 700; color: #7dd3fc; font-size: 12px;")
            lbl_time = QLabel(time_str)
            lbl_time.setStyleSheet("color: #6b7280; font-size: 10px;")
            header_layout.addWidget(lbl_role)
            header_layout.addWidget(lbl_time)
            header_layout.addStretch()

        card_layout.addLayout(header_layout)

        # Metin Alanı
        self.lbl_content = QLabel()
        self.lbl_content.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.lbl_content.setWordWrap(True)
        self.lbl_content.setTextFormat(Qt.TextFormat.MarkdownText)
        self.lbl_content.setText(self.raw_content)

        card_layout.addWidget(self.lbl_content)

        # Asistan için alt aksiyonlar (Kopyala butonu)
        if not is_user:
            action_layout = QHBoxLayout()
            action_layout.setContentsMargins(0, 2, 0, 0)
            action_layout.addStretch()

            self.btn_copy = QPushButton("📋 Kopyala")
            self.btn_copy.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.btn_copy.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #9ca3af;
                    font-size: 10px;
                    border-radius: 5px;
                    padding: 2px 6px;
                    border: 1px solid #2f3242;
                }
                QPushButton:hover {
                    background-color: #272a38;
                    color: #ffffff;
                }
            """)
            self.btn_copy.clicked.connect(self._copy_text)
            action_layout.addWidget(self.btn_copy)
            card_layout.addLayout(action_layout)

        # Temayı uygula
        self.apply_theme_colors(get_current_theme_colors())

        row_layout.addWidget(self.content_card)

        if not is_user:
            row_layout.addStretch(1)

        main_layout.addLayout(row_layout)

    def apply_theme_colors(self, colors: dict):
        """Kart ve metin renklerini aktif temaya göre günceller."""
        is_user = (self.message.role == "user")
        if is_user:
            self.lbl_content.setStyleSheet(f"color: {colors.get('user_text', '#ffffff')}; font-size: 13px; line-height: 1.45;")
            self.content_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {colors.get('user_bubble', '#0891b2')};
                    border: 1px solid {colors.get('user_border', '#06b6d4')};
                    border-radius: 14px;
                    border-top-right-radius: 3px;
                }}
            """)
            self.content_card.setMaximumWidth(640)
        else:
            self.lbl_content.setStyleSheet(f"color: {colors.get('ai_text', '#f1f5f9')}; font-size: 13px; line-height: 1.5;")
            self.content_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {colors.get('ai_bubble', '#111622')};
                    border: 1px solid {colors.get('ai_border', '#1e293b')};
                    border-radius: 14px;
                    border-top-left-radius: 3px;
                }}
            """)
            self.content_card.setMaximumWidth(740)
            if self.lbl_avatar:
                accent = colors.get('accent', '#06b6d4')
                self.lbl_avatar.setStyleSheet(f"""
                    background-color: {accent};
                    color: #ffffff;
                    font-weight: bold;
                    font-size: 13px;
                    border-radius: 14px;
                """)

    def _copy_text(self):
        """Mesaj içeriğini panoya kopyalar."""
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self.raw_content)
            self.btn_copy.setText("✓ Kopyalandı")
            QTimer.singleShot(1800, lambda: self.btn_copy.setText("📋 Kopyala"))

    def set_content_stream(self, text: str, show_cursor: bool = True):
        """Yazı animasyonu sırasında metni günceller."""
        self.raw_content = text
        display_text = text + (" ▌" if show_cursor else "")
        self.lbl_content.setText(display_text)


class EmptyStateWidget(QWidget):
    """Yeni/boş sohbet açıldığında gösterilen modern karşılama ekranı."""
    prompt_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(24, 40, 24, 40)
        layout.setSpacing(20)

        # Logo ve Karşılama
        lbl_icon = QLabel("✦")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("""
            font-size: 46px;
            color: #818cf8;
            font-weight: 800;
        """)
        layout.addWidget(lbl_icon)

        lbl_greeting = QLabel("Size bugün nasıl yardımcı olabilirim?")
        lbl_greeting.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_greeting.setStyleSheet("font-size: 22px; font-weight: 800; color: #ffffff;")
        layout.addWidget(lbl_greeting)

        lbl_sub = QLabel("Aşağıdaki hızlı konulardan birini seçebilir veya doğrudan yazabilirsiniz.")
        lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sub.setStyleSheet("font-size: 13px; color: #9ca3af;")
        layout.addWidget(lbl_sub)

        layout.addSpacing(10)

        # 4 Öneri Kartı (2x2 Izgara)
        grid = QGridLayout()
        grid.setSpacing(12)

        cards = [
            ("⚡ Sistem & Donanım Durumu", "Bilgisayarımın işlemci ve RAM durumunu göster", "/durum"),
            ("💻 Python ile Otomasyon", "Masaüstü için pratik bir dosya düzenleyici kod örneği yaz", "Python ile masaüstü klasöründeki dosyaları uzantılarına göre düzenleyen bir script yaz"),
            ("🧠 Kalıcı Hafızaya Ekle", "Benim hakkımda kalıcı bir bilgi kaydet", "/hatirla"),
            ("💡 Yaratıcı Proje Fikirleri", "Geliştirebileceğim 3 yenilikçi yazılım projesi öner", "Yapay zeka kullanarak geliştirebileceğim 3 yaratıcı masaüstü uygulama fikri öner"),
        ]

        for idx, (title, desc, prompt_val) in enumerate(cards):
            btn = QPushButton()
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1a1b24;
                    border: 1px solid #2b2e3e;
                    border-radius: 12px;
                    text-align: left;
                    padding: 14px 16px;
                }
                QPushButton:hover {
                    background-color: #242736;
                    border: 1px solid #6366f1;
                }
            """)
            
            card_box = QVBoxLayout(btn)
            card_box.setContentsMargins(0, 0, 0, 0)
            card_box.setSpacing(4)

            lbl_t = QLabel(title)
            lbl_t.setStyleSheet("font-weight: 700; color: #f3f4f6; font-size: 13px;")
            lbl_d = QLabel(desc)
            lbl_d.setStyleSheet("color: #9ca3af; font-size: 11px;")

            card_box.addWidget(lbl_t)
            card_box.addWidget(lbl_d)

            btn.clicked.connect(lambda _, p=prompt_val: self.prompt_selected.emit(p))

            row = idx // 2
            col = idx % 2
            grid.addWidget(btn, row, col)

        grid_container = QWidget()
        grid_container.setMaximumWidth(740)
        grid_container.setLayout(grid)
        layout.addWidget(grid_container, alignment=Qt.AlignmentFlag.AlignCenter)


class ChatInputArea(QTextEdit):
    """Enter ile gönderen, Shift+Enter ile alt satıra geçen kompakt metin kutusu."""
    send_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("messageInput")
        self.setPlaceholderText("LopixAI'ye bir mesaj yazın... (Enter: Gönder, Shift+Enter: Alt satır)")
        self.setFixedHeight(38)
        self.setStyleSheet("""
            QTextEdit {
                background: transparent;
                border: none;
                color: #ffffff;
                font-size: 13px;
                line-height: 1.35;
                padding: 2px 4px;
            }
        """)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.send_requested.emit()
        else:
            super().keyPressEvent(event)


class ChatViewWidget(QWidget):
    """Gelişmiş, Şık ve Kompakt Sağ Sohbet Alanı."""

    title_updated = pyqtSignal(str, str)  # (conv_id, new_title)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chatMainArea")
        self.conversation: Optional[Conversation] = None
        self.ai_worker: Optional[AIWorker] = None

        # Yazı Animasyonu Durumu
        self.is_streaming: bool = False
        self.stream_target_text: str = ""
        self.stream_current_index: int = 0
        self.current_streaming_bubble: Optional[MessageBubble] = None
        self.stream_is_offline: bool = False

        self.typing_timer = QTimer(self)
        self.typing_timer.setInterval(16)  # 16 ms akıcı daktilo efekti
        self.typing_timer.timeout.connect(self._on_typing_tick)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Üst Başlık Çubuğu
        self.header_widget = QWidget()
        self.header_widget.setObjectName("chatHeader")
        self.header_widget.setStyleSheet("""
            QWidget#chatHeader {
                background-color: #15161b;
                border-bottom: 1px solid #232530;
                padding: 10px 24px;
            }
        """)
        header_layout = QHBoxLayout(self.header_widget)
        header_layout.setContentsMargins(24, 10, 24, 10)

        title_box = QHBoxLayout()
        title_box.setSpacing(8)
        
        lbl_sparkle = QLabel("✦")
        lbl_sparkle.setStyleSheet("font-size: 16px; color: #06b6d4; font-weight: bold;")
        
        self.lbl_title = QLabel("LopixAI")
        self.lbl_title.setObjectName("chatTitleLabel")
        self.lbl_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        
        title_box.addWidget(lbl_sparkle)
        title_box.addWidget(self.lbl_title)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        self.lbl_status = QLabel("🟢 Gemini (Otomatik)")
        self.lbl_status.setStyleSheet("""
            background-color: #1e202b;
            color: #10b981;
            font-weight: 600;
            font-size: 11px;
            border-radius: 12px;
            padding: 4px 10px;
            border: 1px solid #2c3040;
        """)
        header_layout.addWidget(self.lbl_status)

        layout.addWidget(self.header_widget)

        # 2. Mesaj Listesi (Kaydırılabilir)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("background-color: #090b10; border: none;")
        
        self.messages_container = QWidget()
        self.messages_container.setStyleSheet("background-color: transparent;")
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(32, 18, 32, 18)
        self.messages_layout.setSpacing(12)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.scroll_area.setWidget(self.messages_container)
        layout.addWidget(self.scroll_area)

        # 3. Giriş Alanı (Floating Pill Bar - Kompakt ve Ergonomik)
        input_wrapper = QWidget()
        input_wrapper.setStyleSheet("background-color: #13141a; border-top: 1px solid #1f212a;")
        wrapper_layout = QVBoxLayout(input_wrapper)
        wrapper_layout.setContentsMargins(24, 8, 24, 8)
        wrapper_layout.setSpacing(4)

        # Ortalanmış Bar
        pill_card = QFrame()
        pill_card.setStyleSheet("""
            QFrame {
                background-color: #1a1c24;
                border: 1px solid #2a2d3c;
                border-radius: 14px;
                padding: 2px 6px;
            }
            QFrame:focus-within {
                border: 1px solid #06b6d4;
                background-color: #1d202b;
            }
        """)
        pill_layout = QHBoxLayout(pill_card)
        pill_layout.setContentsMargins(8, 2, 6, 2)
        pill_layout.setSpacing(8)

        self.input_box = ChatInputArea()
        self.input_box.send_requested.connect(self._on_send_clicked)
        pill_layout.addWidget(self.input_box)

        # Gönder / Durdur Butonu (Kompakt 34x34)
        self.btn_send = QPushButton("➤")
        self.btn_send.setObjectName("btnSend")
        self.btn_send.setFixedSize(34, 34)
        self.btn_send.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #06b6d4;
                color: #ffffff;
                font-size: 15px;
                font-weight: bold;
                border-radius: 17px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0891b2;
            }
            QPushButton:pressed {
                background-color: #0e7490;
            }
            QPushButton:disabled {
                background-color: #252834;
                color: #6b7280;
            }
        """)
        self.btn_send.clicked.connect(self._on_send_clicked)
        pill_layout.addWidget(self.btn_send)

        wrapper_layout.addWidget(pill_card)

        lbl_disclaimer = QLabel("✦ LopixAI kişisel asistanınız. 100+ siteden bilgi tarama ve yerel öğrenme motoru aktiftir.")
        lbl_disclaimer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_disclaimer.setStyleSheet("font-size: 10px; color: #64748b;")
        wrapper_layout.addWidget(lbl_disclaimer)

        layout.addWidget(input_wrapper)

        self.apply_theme()
        self.update_status_indicator()

    def apply_theme(self):
        """Aktif tema renklerini sohbet görünümüne ve tüm mesaj balonlarına uygular."""
        colors = get_current_theme_colors()
        self.scroll_area.setStyleSheet(f"background-color: {colors['chat_bg']}; border: none;")
        
        acc = colors.get("accent", "#06b6d4")
        if not self.is_streaming:
            self.btn_send.setStyleSheet(f"""
                QPushButton {{
                    background-color: {acc};
                    color: #ffffff;
                    font-size: 15px;
                    font-weight: bold;
                    border-radius: 17px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: {acc};
                    opacity: 0.9;
                }}
                QPushButton:disabled {{
                    background-color: #252834;
                    color: #6b7280;
                }}
            """)

        for i in range(self.messages_layout.count()):
            item = self.messages_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), MessageBubble):
                item.widget().apply_theme_colors(colors)

    def update_status_indicator(self):
        """Çevrimiçi / Çevrimdışı göstergesini günceller."""
        if GeminiService.is_api_configured():
            self.lbl_status.setText("🟢 Gemini (Otomatik)")
            self.lbl_status.setStyleSheet("""
                background-color: #13241b;
                color: #10b981;
                font-weight: 600;
                font-size: 11px;
                border-radius: 12px;
                padding: 5px 12px;
                border: 1px solid #1c4530;
            """)
        else:
            self.lbl_status.setText("🟡 Çevrimdışı Mod")
            self.lbl_status.setStyleSheet("""
                background-color: #2a2213;
                color: #f59e0b;
                font-weight: 600;
                font-size: 11px;
                border-radius: 12px;
                padding: 5px 12px;
                border: 1px solid #4a3818;
            """)

    def load_conversation(self, conv_id: str):
        """Belirtilen sohbeti ve mesaj geçmişini SQLite'tan yükler."""
        self._stop_current_stream()
        self.conversation = ChatRepository.get_conversation(conv_id)
        if not self.conversation:
            return

        self.lbl_title.setText(self.conversation.title)
        self._clear_messages_ui()

        messages = ChatRepository.get_messages(conv_id)
        if not messages:
            # Boş sohbet için hoş geldiniz ekranı
            empty = EmptyStateWidget()
            empty.prompt_selected.connect(self._on_quick_prompt_selected)
            self.messages_layout.addWidget(empty)
        else:
            for msg in messages:
                self._add_message_bubble(msg)

        self._scroll_to_bottom()
        self.input_box.setFocus()

    def _clear_messages_ui(self):
        while self.messages_layout.count():
            child = self.messages_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _add_message_bubble(self, message: Message):
        bubble = MessageBubble(message)
        self.messages_layout.addWidget(bubble)

    def _scroll_to_bottom(self):
        QApplication.processEvents()
        vbar = self.scroll_area.verticalScrollBar()
        vbar.setValue(vbar.maximum())

    def _on_quick_prompt_selected(self, text: str):
        """Öneri kartı tıklandığında."""
        self.input_box.setText(text)
        self._on_send_clicked()

    def _on_send_clicked(self):
        # Eğer şu an yazı animasyonu akıyorsa durdur
        if self.is_streaming:
            self._stop_current_stream(instant_finish=True)
            return

        text = self.input_box.toPlainText().strip()
        if not text or not self.conversation:
            return

        # Boş sohbet ekranı varsa temizle
        if self.messages_layout.count() == 1:
            first_w = self.messages_layout.itemAt(0).widget()
            if isinstance(first_w, EmptyStateWidget):
                first_w.deleteLater()

        # 1. Kullanıcı mesajını kaydet ve göster
        user_msg = ChatRepository.add_message(self.conversation.id, "user", text)
        self._add_message_bubble(user_msg)
        self.input_box.clear()
        self._scroll_to_bottom()

        # 2. İlk mesajsa otomatik başlık üret
        msg_count = ChatRepository.get_message_count(self.conversation.id)
        if msg_count <= 2 and self.conversation.title in ("Yeni sohbet", "Telegram Sohbeti"):
            auto_title = GeminiService.generate_title_from_prompt(text)
            ChatRepository.rename_conversation(self.conversation.id, auto_title)
            self.conversation.title = auto_title
            self.lbl_title.setText(auto_title)
            self.title_updated.emit(self.conversation.id, auto_title)

        # 3. Girişi kilitle ve Düşünüyor animasyonu
        self.input_box.setEnabled(False)
        self.btn_send.setText("✦...")
        self.btn_send.setEnabled(False)

        # 4. Asenkron yanıt isteği
        self.ai_worker = AIWorker(self.conversation.id, text)
        self.ai_worker.finished.connect(self._start_typewriter_stream)
        self.ai_worker.start()

    def _start_typewriter_stream(self, reply_text: str, is_offline: bool):
        """Yapay zeka yanıtı geldiğinde daktilo yazı animasyonunu başlatır."""
        if not self.conversation:
            return

        self.stream_target_text = reply_text
        self.stream_current_index = 0
        self.stream_is_offline = is_offline
        self.is_streaming = True

        # Geçici balon oluştur (içinde henüz boş metin)
        temp_msg = Message(
            id="temp_stream",
            conversation_id=self.conversation.id,
            role="assistant",
            content="",
            timestamp=time.time()
        )
        self.current_streaming_bubble = MessageBubble(temp_msg)
        self.messages_layout.addWidget(self.current_streaming_bubble)

        # Butonu "Durdur ⏹" moduna al
        self.btn_send.setEnabled(True)
        self.btn_send.setText("⏹")
        self.btn_send.setToolTip("Yazmayı Durdur")
        self.btn_send.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: #ffffff;
                font-size: 14px;
                font-weight: bold;
                border-radius: 20px;
                border: none;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)

        # Zamanlayıcıyı başlat
        self.typing_timer.start()

    def _on_typing_tick(self):
        """Her 16 ms'de bir metinden parça ekler (Yazı Animasyonu)."""
        if not self.is_streaming or not self.current_streaming_bubble:
            self.typing_timer.stop()
            return

        total_len = len(self.stream_target_text)
        if self.stream_current_index < total_len:
            # Akış hızını ayarla: uzun metinlerde daha büyük adımlar (1-3 karakter)
            step = 3 if total_len > 400 else 2
            self.stream_current_index = min(self.stream_current_index + step, total_len)
            partial = self.stream_target_text[:self.stream_current_index]
            self.current_streaming_bubble.set_content_stream(partial, show_cursor=True)
            self._scroll_to_bottom()
        else:
            # Animasyon bitti
            self._stop_current_stream(instant_finish=False)

    def _stop_current_stream(self, instant_finish: bool = False):
        """Yazı animasyonunu tamamlar veya durdurur."""
        self.typing_timer.stop()
        if not self.is_streaming:
            return

        self.is_streaming = False

        if self.current_streaming_bubble and self.conversation:
            final_text = self.stream_target_text
            self.current_streaming_bubble.set_content_stream(final_text, show_cursor=False)

            # Veritabanına kaydet
            ChatRepository.add_message(
                self.conversation.id,
                "assistant",
                final_text,
                metadata={"is_offline": self.stream_is_offline}
            )

        self.current_streaming_bubble = None

        # Girişi ve Gönder butonunu normale döndür
        self.input_box.setEnabled(True)
        self.btn_send.setEnabled(True)
        self.btn_send.setText("➤")
        self.btn_send.setToolTip("Gönder")
        self.btn_send.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4f46e5, stop:1 #6366f1);
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
                border-radius: 20px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #4338ca, stop:1 #4f46e5);
            }
        """)
        self.input_box.setFocus()
        self._scroll_to_bottom()
        self.update_status_indicator()
