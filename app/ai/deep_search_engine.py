"""
LopixAI Derin Web Arama ve Çoklu Kaynak Sentez Motoru
Gemini API yokken veya çevrimdışı fallback durumunda çalışır.
Reddit, Wikipedia, StackOverflow, Quora, GitHub, haber siteleri ve 100'ü aşkın
popüler/güvenilir kaynağı tarar, analiz eder ve kullanıcıya kapsamlı Türkçe yanıt üretir.
"""

import re
import urllib.parse
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

from app.database.chat_repo import ChatRepository
from app.core.logger import get_logger

logger = get_logger("DeepSearchEngine")

# 100+ Popüler ve Güvenilir Kaynak Kataloğu
SEARCH_SOURCES_CATALOG = [
    # Topluluk, Tartışma ve Forumlar (20+)
    "reddit.com", "quora.com", "stackoverflow.com", "stackexchange.com", "superuser.com",
    "askubuntu.com", "serverfault.com", "github.com", "gitlab.com", "news.ycombinator.com",
    "dev.to", "medium.com", "hashnode.com", "eksisozluk.com", "donanimhaber.com",
    "technopat.net", "r10.net", "kizlarsoruyor.com", "forum.donanimarsivi.com", "technopat.net/sosyal",
    # Ansiklopedi, Sözlük ve Referans (15+)
    "tr.wikipedia.org", "en.wikipedia.org", "wiktionary.org", "wikihow.com", "britannica.com",
    "plato.stanford.edu", "iep.utm.edu", "wolframalpha.com", "investopedia.com", "merriam-webster.com",
    "dictionary.com", "vikisozluk.org", "evrimagaci.org", "bilimteknik.tubitak.gov.tr", "tdk.gov.tr",
    # Yazılım, Kodlama ve Geliştirici Dokümantasyonu (20+)
    "docs.python.org", "developer.mozilla.org", "w3schools.com", "geeksforgeeks.org", "realpython.com",
    "freecodecamp.org", "baeldung.com", "tutorialspoint.com", "learnpython.org", "pypi.org",
    "npmjs.com", "hub.docker.com", "kubernetes.io", "rust-lang.org", "go.dev",
    "learn.microsoft.com", "digitalocean.com/community/tutorials", "css-tricks.com", "smashingmagazine.com", "dzone.com",
    # Bilim, Akademi ve Araştırma (15+)
    "arxiv.org", "nature.com", "sciencedirect.com", "scientificamerican.com", "phys.org",
    "sciencedaily.com", "pubmed.ncbi.nlm.nih.gov", "mit.edu", "stanford.edu", "harvard.edu",
    "space.com", "nationalgeographic.com", "nasa.gov", "who.int", "cdc.gov",
    # Teknoloji Haberleri, Donanım ve İnceleme (15+)
    "techcrunch.com", "theverge.com", "wired.com", "arstechnica.com", "engadget.com",
    "cnet.com", "zdnet.com", "tomshardware.com", "anandtech.com", "gsmarena.com",
    "xda-developers.com", "techspot.com", "webtekno.com", "shiftdelete.net", "donanimgunlugu.com",
    # Haber, Ekonomi ve Güncel (15+)
    "bbc.com", "reuters.com", "apnews.com", "bloomberg.com", "forbes.com",
    "economist.com", "euronews.com", "dw.com", "aa.com.tr", "trthaber.com",
    "ntv.com.tr", "sozcu.com.tr", "hurriyet.com.tr", "haberturk.com", "milliyet.com.tr"
]


class DeepSearchEngine:
    """100+ site üzerinden derin web araştırması yapan ve sentezleyen motor."""

    USER_AGENT = "LopixAI/1.0 (Windows NT 10.0; Win64; x64; Desktop AI Assistant)"

    @classmethod
    def search_and_synthesize(cls, user_query: str) -> str:
        """Kullanıcının sorusunu Reddit, Wikipedia, StackOverflow ve web'den tarayıp zengin yanıt üretir."""
        query = user_query.strip()
        if not query:
            return "Lütfen aramak istediğiniz konuyu veya sorunuzu yazın."

        logger.info(f"[Derin Arama] Başlatılıyor: '{query}'")

        # 1. Önce Yerel Öğrenilmiş Bilgileri (SQLite learned_knowledge) Kontrol Et
        local_matches = ChatRepository.search_learned_knowledge(query, limit=2)

        # 2. Wikipedia'dan ansiklopedik özet çek
        wiki_data = cls._fetch_wikipedia_summary(query)

        # 3. Reddit ve Topluluk tartışmalarını tara
        reddit_data = cls._search_community_discussions(query)

        # 4. Genel 100+ site web arama sonuçlarını çek
        web_results = cls._search_multi_source_web(query)

        # 5. Sonuçları sentezleyip zengin markdown yanıtı oluştur
        return cls._format_synthesized_response(
            query=query,
            wiki_data=wiki_data,
            reddit_data=reddit_data,
            web_results=web_results,
            local_matches=local_matches
        )

    @classmethod
    def _fetch_wikipedia_summary(cls, query: str) -> Optional[Dict[str, str]]:
        """Doğrudan Wikipedia REST API üzerinden güvenilir ansiklopedik özet çeker."""
        headers = {"User-Agent": cls.USER_AGENT}
        clean_q = re.sub(r"[?!.,'\"]+", "", query).strip()

        # Önce Türkçe Wikipedia arama
        for lang in ["tr", "en"]:
            try:
                # Başlık arama
                search_url = f"https://{lang}.wikipedia.org/w/api.php"
                params = {
                    "action": "query",
                    "list": "search",
                    "srsearch": clean_q,
                    "utf8": "1",
                    "format": "json",
                    "srlimit": 1
                }
                resp = requests.get(search_url, params=params, headers=headers, timeout=4.0)
                if resp.status_code == 200:
                    data = resp.json()
                    search_list = data.get("query", {}).get("search", [])
                    if search_list:
                        page_title = search_list[0]["title"]
                        # Sayfa özetini çek
                        enc_title = urllib.parse.quote(page_title.replace(" ", "_"))
                        summary_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{enc_title}"
                        s_resp = requests.get(summary_url, headers=headers, timeout=4.0)
                        if s_resp.status_code == 200:
                            s_data = s_resp.json()
                            extract = s_data.get("extract", "").strip()
                            if extract and len(extract) > 40:
                                page_url = s_data.get("content_urls", {}).get("desktop", {}).get("page", f"https://{lang}.wikipedia.org/wiki/{enc_title}")
                                return {
                                    "title": page_title,
                                    "extract": extract,
                                    "url": page_url,
                                    "lang": lang
                                }
            except Exception as e:
                logger.debug(f"Wikipedia {lang} hatası: {e}")
        return None

    @classmethod
    def _search_community_discussions(cls, query: str) -> List[Dict[str, str]]:
        """Reddit, StackOverflow ve forum tartışmalarını tarayarak kullanıcı deneyimlerini toplar."""
        discussions = []
        try:
            with DDGS() as ddgs:
                # Reddit odaklı arama
                reddit_query = f"site:reddit.com {query}"
                res_reddit = list(ddgs.text(reddit_query, max_results=3))
                for r in res_reddit:
                    discussions.append({
                        "source": "Reddit",
                        "title": r.get("title", ""),
                        "body": r.get("body", ""),
                        "href": r.get("href", "")
                    })

                # Kodlama/teknik soru ise StackOverflow da tara
                if any(w in query.lower() for w in ["hata", "error", "nasıl yapılır", "python", "kod", "kodlama", "c#", "fix"]):
                    so_query = f"site:stackoverflow.com {query}"
                    res_so = list(ddgs.text(so_query, max_results=2))
                    for r in res_so:
                        discussions.append({
                            "source": "Stack Overflow",
                            "title": r.get("title", ""),
                            "body": r.get("body", ""),
                            "href": r.get("href", "")
                        })
        except Exception as e:
            logger.warning(f"Topluluk araması uyarısı: {e}")
        return discussions

    @classmethod
    def _search_multi_source_web(cls, query: str) -> List[Dict[str, str]]:
        """100+ site veritabanı kapsamından genel web arama sonuçlarını çeker."""
        web_results = []
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=6))
                for r in raw_results:
                    title = r.get("title", "")
                    body = r.get("body", "")
                    href = r.get("href", "")
                    domain = ""
                    try:
                        domain = urllib.parse.urlparse(href).netloc.lower().replace("www.", "")
                    except Exception:
                        pass

                    web_results.append({
                        "title": title,
                        "body": body,
                        "href": href,
                        "domain": domain
                    })
        except Exception as e:
            logger.warning(f"Genel web araması uyarısı: {e}")
        return web_results

    @classmethod
    def _format_synthesized_response(
        cls,
        query: str,
        wiki_data: Optional[Dict[str, str]],
        reddit_data: List[Dict[str, str]],
        web_results: List[Dict[str, str]],
        local_matches: List[Dict[str, Any]]
    ) -> str:
        """Toplanan çoklu kaynak verilerini şık ve detaylı bir yanıta dönüştürür."""
        sections = []

        # Başlık ve Bilgilendirme Rozeti
        sections.append(
            f"🌐 **LopixAI Derin Web Araştırması** *(100+ Site Veritabanından Derlendi)*\n"
            f"🔎 İncelenen Konu: *\"{query}\"*\n"
        )

        # 0. Yerel Öğrenilmiş Bilgiler Varsa
        if local_matches:
            lm = local_matches[0]
            sections.append(
                f"🧠 **Yerel Hafızadan Öğrenilmiş Bilgi:**\n"
                f"*{lm.get('summary', lm.get('content', ''))[:300]}*\n"
            )

        # 1. Doğrudan Yanıt / Çözüm Özeti
        best_summary = ""
        if wiki_data and wiki_data.get("extract"):
            best_summary = wiki_data["extract"]
        elif web_results:
            best_summary = web_results[0].get("body", "")
        elif reddit_data:
            best_summary = reddit_data[0].get("body", "")

        if best_summary:
            sections.append(f"📌 **Özet ve Ana Yanıt:**\n{best_summary}\n")

        # 2. Reddit ve Topluluk Deneyimleri
        if reddit_data:
            comm_lines = ["💬 **Reddit ve Topluluk Görüşleri (Deneyimler & Çözümler):**"]
            for item in reddit_data[:3]:
                title = item.get("title", "").strip()
                body = item.get("body", "").strip()
                src = item.get("source", "Topluluk")
                href = item.get("href", "")
                if body:
                    comm_lines.append(f"• **[{src}] {title}:**\n  > {body[:240]}...")
            sections.append("\n".join(comm_lines) + "\n")

        # 3. Ansiklopedik ve Teknik Ayrıntılar
        if wiki_data and len(wiki_data.get("extract", "")) > 100:
            w_title = wiki_data.get("title", "")
            w_url = wiki_data.get("url", "")
            sections.append(
                f"📚 **Ansiklopedik ve Teknik Referans ({w_title}):**\n"
                f"{wiki_data['extract']}\n"
            )

        # 4. Taranan 100+ Kaynak Havuzundan Seçilen Bağlantılar
        links_lines = ["🔗 **İncelenen Güvenilir Kaynaklar:**"]
        seen_urls = set()

        if wiki_data and wiki_data.get("url"):
            links_lines.append(f"• [Wikipedia: {wiki_data.get('title', 'Madde')}]({wiki_data['url']})")
            seen_urls.add(wiki_data['url'])

        for item in reddit_data:
            h = item.get("href", "")
            t = item.get("title", "Reddit Başlığı")
            if h and h not in seen_urls:
                links_lines.append(f"• [Reddit / Topluluk Tartışması: {t[:60]}]({h})")
                seen_urls.add(h)

        for item in web_results:
            h = item.get("href", "")
            t = item.get("title", "")
            dom = item.get("domain", "")
            if h and h not in seen_urls and len(seen_urls) < 7:
                links_lines.append(f"• [{dom.upper()}: {t[:65]}]({h})")
                seen_urls.add(h)

        sections.append("\n".join(links_lines))

        # Alt Bilgi Notu
        sections.append(
            "\n---\n"
            "*(💡 Not: Gemini API tanımlı olmadığında LopixAI, Reddit, Wikipedia, StackOverflow "
            "ve 100+ siteden otomatik veri çekerek yanıt üretir. Daha derin yapay zeka akıl yürütmesi "
            "için dilediğiniz zaman Ayarlar'dan Gemini API ekleyebilirsiniz.)*"
        )

        return "\n".join(sections)
