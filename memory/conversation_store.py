"""Small persistent per-chat conversation store for Telegram sessions."""

from pathlib import Path
import json
from typing import Any
from config.settings import settings


class ConversationStore:
    def __init__(self, max_messages: int = 20):
        self.path = Path(settings.data_dir) / "telegram_conversations.json"
        self.max_messages = max_messages
        self._data: dict[str, list[dict[str, Any]]] = {}
        try:
            if self.path.exists():
                self._data = json.loads(self.path.read_text())
        except (OSError, json.JSONDecodeError):
            self._data = {}

    def recent(self, chat_id: int | str) -> list[dict[str, Any]]:
        return self._data.get(str(chat_id), [])[-self.max_messages :]

    def append(self, chat_id: int | str, role: str, content: str) -> None:
        history = self._data.setdefault(str(chat_id), [])
        history.append({"role": role, "content": content})
        self._data[str(chat_id)] = history[-self.max_messages :]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2))
