"""
LopixAI Otonom Arka Plan Öğrenme Motoru (Background Autonomous Learner)
Kullanıcının tüm sohbetlerini (silinenler dahil kalıcı kasadan) inceler,
ilgi duyabileceği ve sorabileceği konuları analiz eder.
Uygulama boşta dururken her 1 dakikada bir web'den (Wikipedia, Reddit, Web)
bilgi indirip yerel SQLite hafızasına (learned_knowledge) kaydeder.
"""

import time
import re
import random
import threading
from typing import List, Set, Optional
from PyQt6.QtCore import QThread, pyqtSignal

from app.database.chat_repo import ChatRepository
from app.database.db_manager import DBManager
from app.ai.deep_search_engine import DeepSearchEngine
from app.core.logger import get_logger

logger = get_logger("KnowledgeLearner")

# Kullanıcı geçmişi henüz azken kullanılabilecek temel ilgi alanları ve keşif tohumları
DEFAULT_CURIOUS_TOPICS = [
    "Yapay zeka modelleri ve çalışma mantığı",
    "Python programlama dili en popüler kütüphaneleri",
    "Windows 11 performans hızlandırma ve kayıt defteri ayarları",
    "Kuantum bilgisayarlar ve geleceğin teknolojisi",
    "Makine öğrenimi ve derin öğrenme farkı",
    "Siber güvenlikte temel savunma yöntemleri",
    "Docker konteyner mimarisi nedir ve nasıl kullanılır",
    "Büyük Dil Modelleri (LLM) nasıl eğitilir",
    "Python asyncio ve asenkron programlama",
    "Veri yapıları ve algoritmalar temel kavramlar",
    "Ağ güvenliği ve firewall mantığı",
    "GPU grafik işlemci mimarisi ve CUDA",
    "Temiz kod (Clean Code) prensipleri",
    "Modern web teknolojileri ve API tasarımı",
    "Bilgisayar donanımı RAM ve CPU çalışma prensibi"
]

STOP_WORDS = {
    "bir", "bu", "ve", "de", "da", "için", "ile", "ne", "nedir", "nasıl", "mı", "mi",
    "mu", "mü", "daha", "çok", "en", "ben", "sen", "o", "biz", "siz", "onlar", "şey",
    "var", "yok", "ama", "fakat", "gibi", "kadar", "olan", "olarak", "ise", "ya", "veya",
    "merhaba", "selam", "günaydın", "iyi", "akşamlar", "lütfen", "teşekkür", "ederim",
    "the", "is", "at", "which", "on", "and", "a", "an", "in", "to", "for", "of", "it"
}


class KnowledgeLearner(QThread):
    """
    Arka planda 1 dakikada bir çalışan otonom bilgi öğrenme servisi.
    Kullanıcının ilgi alanlarını çıkarır ve web'den yeni bilgiler indirir.
    """
    knowledge_learned = pyqtSignal(str, str)  # (topic, title)

    def __init__(self, interval_seconds: int = 60, parent=None):
        super().__init__(parent)
        self.interval_seconds = interval_seconds
        self._is_running = True
        self._is_idle = True

    def set_idle_state(self, is_idle: bool):
        """Kullanıcının işlem yapıp yapmadığını günceller."""
        self._is_idle = is_idle

    def stop(self):
        """Servisi güvenli şekilde sonlandırır."""
        self._is_running = False

    def run(self):
        logger.info(f"[Otonom Öğrenici] Arka plan servisi başlatıldı (Döngü: {self.interval_seconds}s).")
        # Uygulama açılışında ilk öğrenmeyi 15 saniye sonra başlat, ardından her 60 saniyede bir çalıştır
        initial_wait = 15
        for _ in range(initial_wait):
            if not self._is_running:
                return
            time.sleep(1)

        while self._is_running:
            try:
                if self._is_idle:
                    self._perform_learning_cycle()
            except Exception as e:
                logger.error(f"[Otonom Öğrenici] Döngü sırasında hata: {e}")

            # 1 dakika (60 saniye) bekle
            for _ in range(self.interval_seconds):
                if not self._is_running:
                    break
                time.sleep(1)

    def _perform_learning_cycle(self):
        """1 dakikalık otonom öğrenme adımı."""
        # 1. Kullanıcının tüm geçmişini (silinenler dahil) tara ve ilgi konularını çıkar
        target_topic = self._determine_next_topic_to_learn()
        if not target_topic:
            return

        logger.info(f"[Otonom Öğrenici] Yeni konu araştırılıyor ve öğreniliyor: '{target_topic}'")

        # 2. Wikipedia'dan ansiklopedik özet ve derin bilgi çek
        wiki = DeepSearchEngine._fetch_wikipedia_summary(target_topic)
        title = target_topic
        content = ""
        summary = ""
        source = "Web & Ansiklopedi"
        url = ""

        if wiki and wiki.get("extract"):
            title = wiki.get("title", target_topic)
            content = wiki.get("extract", "")
            summary = content[:400]
            source = f"Wikipedia ({wiki.get('lang', 'tr')})"
            url = wiki.get("url", "")
        else:
            # Wikipedia'da doğrudan çıkmadıysa DuckDuckGo üzerinden genel web'den öğren
            web_hits = DeepSearchEngine._search_multi_source_web(target_topic)
            if web_hits:
                first = web_hits[0]
                title = first.get("title", target_topic)
                content = first.get("body", "")
                summary = content
                source = first.get("domain", "Web")
                url = first.get("href", "")

        if not content:
            return

        # 3. Anahtar kelimeleri çıkar
        keywords = ", ".join(self._extract_keywords(f"{target_topic} {title}"))

        # 4. Yerel SQLite learned_knowledge tablosuna kalıcı olarak kaydet
        success = ChatRepository.save_learned_knowledge(
            topic=target_topic,
            title=title,
            source=source,
            url=url,
            content=content,
            summary=summary,
            keywords=keywords
        )

        if success:
            logger.info(f"[Otonom Öğrenici] Başarıyla hafızaya alındı: '{title}' ({source})")
            self.knowledge_learned.emit(target_topic, title)

    def _determine_next_topic_to_learn(self) -> Optional[str]:
        """Kullanıcı geçmişini analiz ederek henüz öğrenilmemiş en uygun konuyu seçer."""
        # Halihazırda öğrenilmiş konuları veritabanından al
        already_learned_topics = self._get_already_learned_topics()

        # Kullanıcının aktif ve silinmiş tüm mesajlarını getir
        user_queries = ChatRepository.get_all_user_queries(include_deleted=True, limit=150)

        candidate_topics = []

        # Kullanıcı sorularından ilgi konuları üret
        for q in user_queries:
            clean_q = re.sub(r"[/\\?!.,'\"():;]+", " ", q).strip()
            if len(clean_q) > 4:
                # Komutları atla
                if clean_q.startswith("/"):
                    continue
                # Eğer soru ise konuyu türet
                derived = clean_q
                for prefix in ["nedir", "nasıl yapılır", "ne demek", "hakkında bilgi ver", "kimdir"]:
                    derived = derived.replace(prefix, "").strip()
                if len(derived) > 3 and derived not in already_learned_topics:
                    candidate_topics.append(derived)

        # Kullanıcı geçmişinden yeterli aday çıkmadıysa veya hepsi öğrenildiyse tohum listesinden seç
        unlearned_defaults = [t for t in DEFAULT_CURIOUS_TOPICS if t not in already_learned_topics]
        candidate_topics.extend(unlearned_defaults)

        if not candidate_topics:
            # Hepsi öğrenilmişse rastgele bir tohumu derinleştirmek için varyasyon üret
            base = random.choice(DEFAULT_CURIOUS_TOPICS)
            return f"{base} ileri düzey rehber"

        # İlk uygun konuyu seç
        return candidate_topics[0]

    def _get_already_learned_topics(self) -> Set[str]:
        """Daha önce öğrenilmiş konuların kümesini döner."""
        conn = DBManager.get_chats_conn()
        try:
            cur = conn.execute("SELECT topic, title FROM learned_knowledge;")
            items = set()
            for r in cur.fetchall():
                items.add(r["topic"].strip())
                items.add(r["title"].strip())
            return items
        except Exception:
            return set()
        finally:
            conn.close()

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        """Metinden anlamlı anahtar kelimeleri çıkarır."""
        words = re.findall(r"\b[a-zA-ZçğıöşüÇĞİÖŞÜ0-9_]{3,}\b", text.lower())
        meaningful = [w for w in words if w not in STOP_WORDS]
        return list(dict.fromkeys(meaningful))[:6]
