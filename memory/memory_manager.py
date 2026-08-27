"""
Lightweight Memory Manager with JSON fallback
"""

import json
from pathlib import Path
from typing import List, Dict, Any
import asyncio
from config.settings import settings
from loguru import logger

class MemoryManager:
    def __init__(self):
        self.memory_file = Path(settings.data_dir) / "memory.json"
        if not self.memory_file.exists():
            with open(self.memory_file, "w") as f:
                json.dump([
                    {"content": "Initialized system memory for Zero-Budget AI Agent.", "metadata": {"type": "system"}, "id": 0}
                ], f)
                
    async def get_all(self) -> List[Dict]:
        try:
            with open(self.memory_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read memory: {e}")
            return []
            
    async def search(self, query: str, top_k: int = 5) -> List[Dict]:
        memories = await self.get_all()
        query_lower = query.lower()
        results = []
        for mem in memories:
            if query_lower in mem.get("content", "").lower():
                mem["similarity"] = 0.95
                results.append(mem)
        return results[:top_k]
        
    async def add_memory(self, content: str, metadata: Dict):
        memories = await self.get_all()
        memories.append({
            "content": content,
            "metadata": metadata,
            "id": len(memories)
        })
        with open(self.memory_file, "w") as f:
            json.dump(memories, f, indent=2)

    async def clear_all(self):
        with open(self.memory_file, "w") as f:
            json.dump([], f)
