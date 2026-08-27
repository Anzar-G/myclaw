"""
Multi-channel alerting system untuk critical events
"""

import asyncio
import json
import requests
from typing import Optional, List
from loguru import logger
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from config.settings import settings

class AlertSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

@dataclass
class Alert:
    message: str
    severity: AlertSeverity
    source: str
    metadata: Optional[dict] = None

class AlertingSystem:
    def __init__(self):
        self.telegram_token = settings.telegram_token
        self.telegram_chat_id = getattr(settings, 'telegram_chat_id', None)
        self.alert_log_file = Path(settings.log_dir) / "alerts.log"
        
    async def send_alert(self, alert: Alert):
        # Always log locally
        self._log_locally(alert)
        
        # Only send external alerts for WARNING and above
        if alert.severity in [AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
            await self._send_telegram(alert)
            
    def _log_locally(self, alert: Alert):
        log_msg = f"[{alert.severity.value}] {alert.source}: {alert.message}"
        if alert.severity == AlertSeverity.CRITICAL:
            logger.critical(log_msg)
        elif alert.severity == AlertSeverity.ERROR:
            logger.error(log_msg)
        elif alert.severity == AlertSeverity.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)
            
        with open(self.alert_log_file, "a") as f:
            f.write(json.dumps({
                "severity": alert.severity.value,
                "source": alert.source,
                "message": alert.message,
                "metadata": alert.metadata
            }) + "\n")

    async def _send_telegram(self, alert: Alert):
        if not self.telegram_token or not self.telegram_chat_id:
            return
            
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        text = f"🚨 *{alert.severity.value}* from {alert.source}\n\n{alert.message}"
        try:
            requests.post(url, json={"chat_id": self.telegram_chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5)
        except Exception as e:
            logger.error(f"Failed to send telegram alert: {e}")

alerter = AlertingSystem()
