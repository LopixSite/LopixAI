"""
LopixAI Modern Arayüz Teması ve QSS Tasarım Sistemi
ChatGPT ve Claude benzeri şık, göz yormayan, dinamik renk temaları destekli arayüz kimliği.
"""

from typing import Dict, Any
from app.core.settings import SettingsManager

THEME_PRESETS: Dict[str, Dict[str, str]] = {
    "neon_cyan": {
        "name": "💎 Lopix Neon Cyan (Logo Uyumu & Siber)",
        "user_bubble": "#0891b2",
        "user_border": "#06b6d4",
        "user_text": "#ffffff",
        "ai_bubble": "#111622",
        "ai_border": "#1e293b",
        "ai_text": "#f1f5f9",
        "chat_bg": "#090b10",
        "accent": "#06b6d4"
    },
    "indigo": {
        "name": "🌌 Gece Mavisi & İndigo (Klasik)",
        "user_bubble": "#312e81",
        "user_border": "#4338ca",
        "user_text": "#ffffff",
        "ai_bubble": "#1a1b24",
        "ai_border": "#282a38",
        "ai_text": "#f3f4f6",
        "chat_bg": "#111216",
        "accent": "#6366f1"
    },
    "emerald": {
        "name": "🌿 Zümrüt Yeşili (Huzurlu Doğa)",
        "user_bubble": "#065f46",
        "user_border": "#059669",
        "user_text": "#ffffff",
        "ai_bubble": "#0f1a15",
        "ai_border": "#1e3328",
        "ai_text": "#f0fdf4",
        "chat_bg": "#09110d",
        "accent": "#10b981"
    },
    "amethyst": {
        "name": "🔮 Ametist Moru (Zarif & Derin)",
        "user_bubble": "#581c87",
        "user_border": "#7e22ce",
        "user_text": "#ffffff",
        "ai_bubble": "#171222",
        "ai_border": "#2b1e3e",
        "ai_text": "#faf5ff",
        "chat_bg": "#0d0a14",
        "accent": "#a855f7"
    },
    "oled": {
        "name": "🖤 OLED Gece Siyahı (Saf Minimal)",
        "user_bubble": "#27272a",
        "user_border": "#3f3f46",
        "user_text": "#ffffff",
        "ai_bubble": "#121214",
        "ai_border": "#242428",
        "ai_text": "#f4f4f5",
        "chat_bg": "#000000",
        "accent": "#71717a"
    },
    "custom": {
        "name": "🎨 Özel Renk Paleti (Kullanıcı Tanımlı)",
        "user_bubble": "#0e7490",
        "user_border": "#06b6d4",
        "user_text": "#ffffff",
        "ai_bubble": "#151922",
        "ai_border": "#252b3b",
        "ai_text": "#f3f4f6",
        "chat_bg": "#0d0f15",
        "accent": "#06b6d4"
    }
}

def get_current_theme_colors() -> Dict[str, str]:
    """Ayarlara göre aktif renk paletini döner."""
    preset_key = SettingsManager.get("chat_theme_preset", "neon_cyan")
    if preset_key in THEME_PRESETS and preset_key != "custom":
        colors = THEME_PRESETS[preset_key].copy()
    else:
        colors = THEME_PRESETS["custom"].copy()
        colors["user_bubble"] = SettingsManager.get("user_bubble_color", "#0e7490")
        colors["user_border"] = colors["user_bubble"]
        colors["ai_bubble"] = SettingsManager.get("ai_bubble_color", "#151922")
        colors["ai_border"] = "#252b3b"
        colors["chat_bg"] = SettingsManager.get("chat_bg_color", "#0d0f15")
        colors["accent"] = SettingsManager.get("accent_color", "#06b6d4")
    return colors


DARK_THEME_QSS = """
/* Genel Pencere ve Arka Plan */
QWidget {
    background-color: #121316;
    color: #e5e7eb;
    font-family: "Segoe UI", "Inter", "Segoe UI Variable", -apple-system, sans-serif;
    font-size: 13px;
    selection-background-color: #6366f1;
    selection-color: #ffffff;
    border: none;
}

/* Sol Kenar Çubuğu (Sidebar) */
#sidebarWidget {
    background-color: #17181c;
    border-right: 1px solid #23252b;
}

#logoLabel {
    font-size: 18px;
    font-weight: 700;
    color: #f9fafb;
    padding: 6px 0;
}

#versionBadge {
    font-size: 10px;
    background-color: #272730;
    color: #a5b4fc;
    border-radius: 6px;
    padding: 2px 6px;
    font-weight: 600;
}

/* Yeni Sohbet Butonu */
#btnNewChat {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #6366f1);
    color: #ffffff;
    font-weight: 600;
    font-size: 13px;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: center;
}

#btnNewChat:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338ca, stop:1 #4f46e5);
}

#btnNewChat:pressed {
    background: #3730a3;
}

/* Arama Çubuğu */
#searchBar {
    background-color: #1e2025;
    border: 1px solid #2b2e36;
    border-radius: 8px;
    padding: 8px 12px;
    color: #f3f4f6;
    font-size: 12px;
}

#searchBar:focus {
    border: 1px solid #6366f1;
    background-color: #22252c;
}

/* Sohbet Listesi Öğeleri */
QScrollArea {
    background-color: transparent;
    border: none;
}

#chatListContainer {
    background-color: transparent;
}

.chat-item-btn {
    background-color: transparent;
    border-radius: 8px;
    padding: 8px 10px;
    text-align: left;
    color: #d1d5db;
    font-size: 13px;
    margin-bottom: 2px;
}

.chat-item-btn:hover {
    background-color: #22242b;
    color: #ffffff;
}

.chat-item-btn-active {
    background-color: #2a2d36;
    color: #ffffff;
    font-weight: 600;
    border-left: 3px solid #6366f1;
}

.chat-dots-btn {
    background-color: transparent;
    border-radius: 6px;
    color: #9ca3af;
    font-size: 15px;
    padding: 4px;
}

.chat-dots-btn:hover {
    background-color: #32353f;
    color: #ffffff;
}

/* Sağ Sohbet Alanı */
#chatMainArea {
    background-color: #121316;
}

#chatHeader {
    background-color: #17181c;
    border-bottom: 1px solid #23252b;
    padding: 12px 24px;
}

#chatTitleLabel {
    font-size: 15px;
    font-weight: 600;
    color: #f9fafb;
}

#chatStatusBadge {
    font-size: 11px;
    color: #10b981;
    font-weight: 500;
}

/* Mesaj Giriş Alanı */
#inputContainer {
    background-color: #17181c;
    border-top: 1px solid #23252b;
    padding: 16px 24px;
}

#messageInput {
    background-color: #1e2026;
    border: 1px solid #2d3039;
    border-radius: 12px;
    padding: 12px 16px;
    color: #f3f4f6;
    font-size: 14px;
    selection-background-color: #6366f1;
}

#messageInput:focus {
    border: 1px solid #6366f1;
    background-color: #22252d;
}

#btnSend {
    background-color: #6366f1;
    color: #ffffff;
    border-radius: 10px;
    padding: 10px 18px;
    font-weight: 600;
    font-size: 14px;
}

#btnSend:hover {
    background-color: #4f46e5;
}

#btnSend:pressed {
    background-color: #4338ca;
}

#btnSend:disabled {
    background-color: #2c2d36;
    color: #6b7280;
}

/* Kaydırma Çubukları */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 7px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #2e313b;
    min-height: 25px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #4b5563;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* Açılır Menüler (QMenu) */
QMenu {
    background-color: #1e2026;
    border: 1px solid #2f323c;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    background-color: transparent;
    color: #e5e7eb;
    padding: 8px 24px 8px 12px;
    border-radius: 6px;
    font-size: 13px;
}

QMenu::item:selected {
    background-color: #2e313c;
    color: #ffffff;
}

/* Modal ve Diyaloglar */
QDialog {
    background-color: #17181c;
    border: 1px solid #2a2c34;
    border-radius: 12px;
}

QPushButton.primary-btn {
    background-color: #6366f1;
    color: #ffffff;
    font-weight: 600;
    border-radius: 8px;
    padding: 8px 16px;
}

QPushButton.primary-btn:hover {
    background-color: #4f46e5;
}

QPushButton.danger-btn {
    background-color: #ef4444;
    color: #ffffff;
    font-weight: 600;
    border-radius: 8px;
    padding: 8px 16px;
}

QPushButton.danger-btn:hover {
    background-color: #dc2626;
}

QPushButton.secondary-btn {
    background-color: #262830;
    color: #d1d5db;
    font-weight: 500;
    border-radius: 8px;
    padding: 8px 16px;
    border: 1px solid #353842;
}

QPushButton.secondary-btn:hover {
    background-color: #2f323c;
    color: #ffffff;
}

QLineEdit.dialog-input {
    background-color: #1e2026;
    border: 1px solid #32353f;
    border-radius: 8px;
    padding: 8px 12px;
    color: #ffffff;
}

QLineEdit.dialog-input:focus {
    border: 1px solid #6366f1;
}

/* İlerleme Çubuğu (QProgressBar) */
QProgressBar {
    border: none;
    border-radius: 6px;
    background-color: #22242b;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    height: 12px;
}

QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #06b6d4);
    border-radius: 6px;
}
"""
