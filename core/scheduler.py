"""Persistent, notification-only scheduler."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import asyncio, json, uuid
from config.settings import settings

class Scheduler:
    def __init__(self, callback):
        self.callback = callback
        self.path = Path(settings.data_dir) / "scheduled_notifications.json"
        try: self.items = json.loads(self.path.read_text()) if self.path.exists() else []
        except (OSError, json.JSONDecodeError): self.items = []
        self.task = None

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.items, ensure_ascii=False, indent=2))

    def add(self, chat_id, message, minutes):
        item = {"id": uuid.uuid4().hex[:8], "chat_id": chat_id, "message": message,
                "due": (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()}
        self.items.append(item); self._save(); return item

    def add_every(self, chat_id, message, minutes):
        minutes = max(1, int(minutes))
        item = {"id": uuid.uuid4().hex[:8], "chat_id": chat_id, "message": message,
                "interval_minutes": minutes,
                "due": (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()}
        self.items.append(item); self._save(); return item

    def cancel(self, item_id):
        before = len(self.items); self.items = [x for x in self.items if x["id"] != item_id]
        self._save(); return len(self.items) < before

    def list(self, chat_id): return [x for x in self.items if str(x["chat_id"]) == str(chat_id)]

    async def start(self):
        if self.task is None: self.task = asyncio.create_task(self._run())

    async def stop(self):
        if self.task: self.task.cancel(); self.task = None

    async def _run(self):
        while True:
            now = datetime.now(timezone.utc); due=[]; pending=[]
            for item in self.items:
                if datetime.fromisoformat(item["due"]) <= now: due.append(item)
                else: pending.append(item)
            if due:
                recurring = []
                for item in due:
                    try: await self.callback(item["chat_id"], item["message"], item["id"])
                    except Exception: pass
                    if item.get("interval_minutes"):
                        item["due"] = (now + timedelta(minutes=int(item["interval_minutes"]))).isoformat()
                        recurring.append(item)
                self.items = pending + recurring; self._save()
            await asyncio.sleep(5)
