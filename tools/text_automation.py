"""
Text and Document Automation tools
"""
from config.tool_registry import BaseTool, ToolCategory
import subprocess
from loguru import logger

class ClipboardReadTool(BaseTool):
    name = "read_clipboard"
    description = "Membaca teks dari clipboard. Params: none"
    category = ToolCategory.TEXT_DOCUMENT
    async def execute(self) -> str:
        result = subprocess.run(["pbpaste"], capture_output=True, text=True)
        return result.stdout

class ClipboardWriteTool(BaseTool):
    name = "write_clipboard"
    description = "Menyalin teks ke clipboard. Params: text"
    category = ToolCategory.TEXT_DOCUMENT
    async def execute(self, text: str) -> str:
        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        process.communicate(text.encode('utf-8'))
        return f"Teks telah disalin ke clipboard."

class MusicControlTool(BaseTool):
    name = "music_control"
    description = "Mengontrol aplikasi Music/iTunes. Params: action ('play', 'pause', 'next', 'previous')"
    category = ToolCategory.MEDIA
    async def execute(self, action: str) -> str:
        actions = {"putar": "play", "play": "play", "pause": "pause", "jeda": "pause", "next": "next track", "previous": "previous track", "sebelumnya": "previous track"}
        command = actions.get(action.casefold())
        if not command:
            raise ValueError("Aksi Music harus play, pause, next, atau previous.")
        script = f'tell application "Music" to {command}'
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "Music gagal menjalankan aksi.")
        return f"Aksi {command} berhasil dilakukan di Music."
