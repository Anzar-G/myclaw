"""
Discord Bot Integration Tool - Real API
"""
from config.tool_registry import BaseTool, ToolCategory
from config.settings import settings
from loguru import logger
import requests


class SendDiscordMessageTool(BaseTool):
    name = "send_discord"
    description = "Mengirim pesan ke Discord channel. Params: channel_id, message"
    category = ToolCategory.COMMUNICATION
    
    async def execute(self, channel_id: str, message: str) -> str:
        token = settings.discord_bot_token
        if not token:
            return "Discord Bot Token belum dikonfigurasi di .env"
        
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        headers = {
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json"
        }
        payload = {"content": message}
        
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code in [200, 201]:
            return f"Pesan berhasil dikirim ke Discord channel {channel_id}: '{message}'"
        raise Exception(f"Gagal mengirim ke Discord: {response.status_code} - {response.text}")


class ReadDiscordMessagesTool(BaseTool):
    name = "read_discord"
    description = "Membaca pesan terakhir dari Discord channel. Params: channel_id"
    category = ToolCategory.COMMUNICATION
    
    async def execute(self, channel_id: str) -> str:
        token = settings.discord_bot_token
        if not token:
            return "Discord Bot Token belum dikonfigurasi di .env"
        
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages?limit=5"
        headers = {"Authorization": f"Bot {token}"}
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            messages = response.json()
            if not messages:
                return "Tidak ada pesan di channel ini."
            formatted = "\n".join([f"- {m['author']['username']}: {m['content']}" for m in messages])
            return f"5 pesan terakhir di channel:\n{formatted}"
        raise Exception(f"Gagal membaca Discord: {response.status_code} - {response.text}")
