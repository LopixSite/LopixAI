"""
LopixAI Güvenlik Muhafızı (Security Guard)
Kritik sistem işlemlerini onay sürecine tabi tutar ve denetim kayıtlarını
.lopixai/security/events/ altında saklar.
"""

import time
import json
import uuid
from typing import Dict, Any, Optional
from app.core.config import SECURITY_EVENTS_DIR, ensure_data_directories
from app.core.logger import get_logger

logger = get_logger("SecurityGuard")

class SecurityGuard:
    """Ajan eylemleri için güvenlik denetleyicisi."""

    @staticmethod
    def log_security_event(action_name: str, target: str, is_approved: bool, details: Optional[Dict[str, Any]] = None) -> str:
        """Güvenlik olayını .lopixai/security/events/ altına yazar."""
        ensure_data_directories()
        event_id = str(uuid.uuid4())
        event_data = {
            "event_id": event_id,
            "timestamp": time.time(),
            "action": action_name,
            "target": target,
            "approved": is_approved,
            "details": details or {}
        }
        
        file_path = SECURITY_EVENTS_DIR / f"event_{int(time.time())}_{event_id[:8]}.json"
        try:
            file_path.write_text(json.dumps(event_data, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info(f"Güvenlik olayı kaydedildi: {action_name} on '{target}' (Onaylandı: {is_approved})")
        except Exception as e:
            logger.error(f"Güvenlik olayı kaydedilemedi: {e}")

        return event_id
