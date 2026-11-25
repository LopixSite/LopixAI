"""
LopixAI Gemini API Servisi ve Context Yöneticisi (Product Rules #3, #9, #12)
Sohbet geçmişinden context üretir, Gemini API'ye iletir, otomatik model fallback uygular.
Google model güncellemelerinde asla çökmez.
"""

import re
import json
import requests
from typing import List, Dict, Any, Optional, Tuple
from app.core.secrets import SecretsManager
from app.core.settings import SettingsManager
from app.core.logger import get_logger
from app.database.chat_repo import Message, ChatRepository
from app.ai.offline_service import OfflineService

logger = get_logger("GeminiService")

GEMINI_API_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

class GeminiService:
    """Gemini API iletişim, model fallback ve context yönetim servisi."""

    # Google API'nin desteklediği güncel modeller (öncelik sırasına göre)
    CANDIDATE_MODELS = [
        "gemini-3.6-flash",
        "gemini-flash-latest",
        "gemini-3.7-flash",
        "gemini-3.5-flash",
        "gemini-2.5-flash-lite",
    ]

    _working_model: Optional[str] = None

    @classmethod
    def is_api_configured(cls) -> bool:
        """API anahtarı mevcut mu kontrol eder."""
        key = SecretsManager.get_gemini_api_key()
        return bool(key and key.strip())

    @classmethod
    def get_model_name(cls) -> str:
        """Kullanılacak aktif Gemini model adını döner."""
        return cls._working_model or cls.CANDIDATE_MODELS[0]

    @classmethod
    def test_connection(cls, api_key: Optional[str] = None) -> Tuple[bool, str]:
        """
        API anahtarını Google Gemini sunucusu ile test eder ve çalışan modeli tespit eder.
        Döner: (başarılı_mı, mesaj)
        """
        key = api_key or SecretsManager.get_gemini_api_key()
        if not key or not key.strip():
            return False, "Gemini API anahtarı boş olamaz."

        key = key.strip()

        # Aday modelleri sırayla test et
        models_to_try = [cls._working_model] if cls._working_model else []
        models_to_try.extend([m for m in cls.CANDIDATE_MODELS if m not in models_to_try])

        last_error = ""

        for model in models_to_try:
            url = GEMINI_API_URL_TEMPLATE.format(model=model, key=key)
            payload = {
                "contents": [{"role": "user", "parts": [{"text": "ping"}]}],
                "generationConfig": {"maxOutputTokens": 10}
            }
            try:
                resp = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=12.0)
                if resp.status_code == 200:
                    cls._working_model = model
                    logger.info(f"Gemini bağlantısı doğrulandı. Aktif model: {model}")
                    return True, f"Bağlantı Başarılı ({model})"
                elif resp.status_code == 404:
                    # Model kullanımdan kalkmış olabilir, bir sonrakini dene
                    last_error = f"{model} modeli kullanılamıyor (404)"
                    continue
                elif resp.status_code == 400:
                    # API key geçersiz olabilir
                    err_json = resp.json()
                    msg = err_json.get("error", {}).get("message", "Geçersiz parametre.")
                    return False, f"Geçersiz API Anahtarı: {msg}"
                elif resp.status_code == 403:
                    return False, "API Anahtarı yetkisiz veya kota sınırında (403)."
                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:120]}"
            except requests.exceptions.RequestException as e:
                return False, f"Ağ bağlantı hatası: {e}"

        return False, f"Gemini API yanıt vermedi: {last_error}"

    @classmethod
    def build_context(cls, conversation_id: str, current_prompt: str) -> List[Dict[str, Any]]:
        """
        chats.db'den konuşma geçmişini çeker ve Gemini API'nin beklediği
        contents listesini (sliding window ile) oluşturur.
        """
        max_context = SettingsManager.get("max_context_messages", 20)
        history_messages = ChatRepository.get_messages(conversation_id)

        # Son N mesajı al (mevcut prompt hariç)
        if len(history_messages) > max_context:
            history_messages = history_messages[-max_context:]

        contents: List[Dict[str, Any]] = []

        for msg in history_messages:
            role = "user" if msg.role == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg.content}]
            })

        # Son kullanıcı mesajını ekle
        contents.append({
            "role": "user",
            "parts": [{"text": current_prompt}]
        })

        return contents

    @classmethod
    def send_message(cls, conversation_id: str, prompt: str) -> Tuple[str, bool]:
        """
        Kullanıcı mesajını Gemini'ye gönderir. Otomatik model fallback uygular.
        Döner: (yanıt_metni, is_offline_mode)
        """
        api_key = SecretsManager.get_gemini_api_key()
        if not api_key or not api_key.strip():
            logger.info("Gemini API key tanımlı değil, OfflineService devreye giriyor.")
            return OfflineService.generate_response(prompt, conversation_id), True

        contents = cls.build_context(conversation_id, prompt)

        system_instruction = (
            "Sen LopixAI adlı, Windows 10/11 x64 üzerinde çalışan, kullanıcı dostu, "
            "hızlı ve yardımcı bir masaüstü kişisel yapay zeka asistanısın. "
            "Yanıtlarını net, anlaşılır ve Türkçe olarak ver. "
            "Kod bloklarını markdown ile şık formatla."
        )

        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 4096,
            }
        }

        # Aday modeller listesi
        models_to_try = [cls._working_model] if cls._working_model else []
        models_to_try.extend([m for m in cls.CANDIDATE_MODELS if m not in models_to_try])

        last_error = ""

        for model in models_to_try:
            url = GEMINI_API_URL_TEMPLATE.format(model=model, key=api_key)
            try:
                response = requests.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=30.0
                )

                if response.status_code == 200:
                    cls._working_model = model
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        first_cand = candidates[0]
                        parts = first_cand.get("content", {}).get("parts", [])
                        if parts:
                            reply_text = parts[0].get("text", "")
                            return reply_text, False
                    return "Yapay zeka boş bir yanıt döndürdü.", False

                elif response.status_code == 404:
                    # Model deprecated veya bulunamadı, sonrakine geç
                    logger.warning(f"{model} modeli için HTTP 404 alındı, fallback model deneniyor...")
                    last_error = response.text
                    continue
                else:
                    err_msg = response.text
                    logger.warning(f"Gemini API HTTP {response.status_code} ({model}): {err_msg}")
                    last_error = err_msg
                    break

            except requests.exceptions.RequestException as req_err:
                logger.warning(f"Ağ/Bağlantı hatası: {req_err}")
                offline_reply = OfflineService.generate_response(prompt, conversation_id)
                prefix = "⚠️ **İnternet / Sunucu Bağlantı Hatası** (Çevrimdışı mod devrede)\n\n"
                return prefix + offline_reply, True
            except Exception as e:
                logger.error(f"Beklenmeyen Gemini servis hatası: {e}")
                last_error = str(e)
                break

        # Tüm modeller başarısız olduysa offline fallback
        offline_reply = OfflineService.generate_response(prompt, conversation_id)
        prefix = (
            f"⚠️ **Gemini API Bağlantı Hatası**\n"
            f"*{last_error[:120]}...*\n\n"
            "LopixAI Çevrimdışı Mod'a geçiş yaptı:\n\n"
        )
        return prefix + offline_reply, True

    @classmethod
    def generate_title_from_prompt(cls, prompt: str) -> str:
        """
        İlk mesajdan kısa ve öz bir sohbet başlığı türetir (Product Rule #9).
        Örn: 'Python'da class nedir?' -> 'Python'da Class'
        """
        clean = prompt.strip().replace("\n", " ")
        clean = re.sub(r"[?!.,:;]+$", "", clean)

        patterns = [
            r"^(bana\s+)?(hakkında\s+)?bilgi\s+ver\s*",
            r"^(lütfen\s+)?anlat\s*",
            r"^(nasıl\s+yapılır|nedir|ne\s+demek|kimdir)\s*",
        ]
        for p in patterns:
            clean = re.sub(p, "", clean, flags=re.IGNORECASE)

        words = clean.split()
        if len(words) > 5:
            title = " ".join(words[:5])
        else:
            title = clean

        if len(title) > 35:
            title = title[:35] + "..."

        title = title.strip()
        if not title:
            title = "Yeni sohbet"
        else:
            title = title[0].upper() + title[1:]

        return title
