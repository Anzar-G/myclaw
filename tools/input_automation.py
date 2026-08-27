"""
Keyboard and Mouse Automation using PyAutoGUI
"""
from config.tool_registry import BaseTool, ToolCategory
import pyautogui
from loguru import logger
from config.macos_permissions import require_accessibility

# PyAutoGUI safety settings
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

class KeyboardTypeTool(BaseTool):
    name = "keyboard_type"
    description = "Mengetik teks secara otomatis. Params: text"
    category = ToolCategory.KEYBOARD_MOUSE
    async def execute(self, text: str) -> str:
        require_accessibility()
        pyautogui.write(text, interval=0.1)
        return f"Teks '{text}' telah diketik."

class KeyboardHotkeyTool(BaseTool):
    name = "keyboard_hotkey"
    description = "Menekan kombinasi tombol (hotkey). Params: keys (list of keys like ['command', 'c'] atau string 'command,c')"
    category = ToolCategory.KEYBOARD_MOUSE
    async def execute(self, keys) -> str:
        require_accessibility()
        if isinstance(keys, str):
            import re
            keys_list = re.split(r'[,\s\+]+', keys)
        elif isinstance(keys, list):
            keys_list = keys
        else:
            keys_list = [str(keys)]
        pyautogui.hotkey(*keys_list)
        return f"Hotkey {keys_list} telah ditekan."

class MouseMoveClickTool(BaseTool):
    name = "mouse_click"
    description = "Menggerakkan mouse dan melakukan klik. Params: x, y, clicks (default 1)"
    category = ToolCategory.KEYBOARD_MOUSE
    async def execute(self, x: int, y: int, clicks: int = 1) -> str:
        require_accessibility()
        pyautogui.click(x=x, y=y, clicks=clicks)
        return f"Melakukan klik {clicks} kali di koordinat ({x}, {y})."


class MouseMoveTool(BaseTool):
    name = "mouse_move"
    description = "Menggerakkan cursor tanpa klik. Params: x, y, duration (opsional)"
    category = ToolCategory.KEYBOARD_MOUSE
    async def execute(self, x: int, y: int, duration: float = 0.2) -> str:
        require_accessibility()
        pyautogui.moveTo(x, y, duration=max(0, min(float(duration), 5)))
        return f"Cursor dipindahkan ke ({x}, {y})."


class MousePositionTool(BaseTool):
    name = "mouse_position"
    description = "Membaca posisi cursor saat ini. Params: none"
    category = ToolCategory.KEYBOARD_MOUSE
    async def execute(self) -> str:
        require_accessibility()
        x, y = pyautogui.position()
        return f"Posisi cursor: ({x}, {y})"

class MouseScrollTool(BaseTool):
    name = "mouse_scroll"
    description = "Melakukan scroll mouse. Params: amount (positif untuk ke atas, negatif untuk ke bawah)"
    category = ToolCategory.KEYBOARD_MOUSE
    async def execute(self, amount: int) -> str:
        require_accessibility()
        pyautogui.scroll(amount)
        return f"Melakukan scroll sebanyak {amount} unit."
