from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from loguru import logger

class ToolCategory(Enum):
    FILE = "File System"
    DATABASE = "Database"
    COMMUNICATION = "Communication"
    SYSTEM = "System execution"
    WEB = "Web & APIs"
    MAC_OS = "macOS Control" # New Category
    BROWSER_AUTOMATION = "Browser Automation" # New Category
    KEYBOARD_MOUSE = "Keyboard & Mouse" # New Category
    MEDIA = "Media & Content" # New Category
    DEVELOPMENT = "Development" # New Category
    TEXT_DOCUMENT = "Text & Document" # New Category

@dataclass
class ToolResult:
    success: bool
    message: str
    data: Any = None
    metadata: Dict = field(default_factory=dict)

class BaseTool:
    name: str = "BaseTool"
    description: str = "Base tool description"
    category: ToolCategory = ToolCategory.SYSTEM

    async def execute(self, **kwargs) -> Any:
        raise NotImplementedError
        
    async def safe_execute(self, **kwargs) -> ToolResult:
        try:
            res = await self.execute(**kwargs)
            message = res if isinstance(res, str) else f"{self.name} selesai dijalankan"
            return ToolResult(success=True, message=message, data=None if isinstance(res, str) else res)
        except Exception as e:
            logger.error(f"Tool {self.name} failed: {e}")
            return ToolResult(success=False, message=str(e))

class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Writes content to a file. Params: path, content"
    category = ToolCategory.FILE
    async def execute(self, path: str, content: str) -> str:
        with open(path, "w") as f:
            f.write(content)
        return f"File {path} written successfully."

class DeleteFileTool(BaseTool):
    name = "delete_file"
    description = "Deletes a file. Params: path"
    category = ToolCategory.FILE
    async def execute(self, path: str) -> str:
        import os
        if os.path.exists(path):
            os.remove(path)
            return f"File {path} deleted."
        return f"File {path} not found."


class SystemAutomationTool(BaseTool):
    name = "system_automation"
    description = "Executes a shell command. Params: command"
    category = ToolCategory.SYSTEM
    async def execute(self, command: str) -> str:
        import subprocess
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return result.stdout
        else:
            raise Exception(f"Command failed: {result.stderr}")

class ToolRegistry:
    def __init__(self):
        import importlib.util
        from pathlib import Path
        from tools.mac_automation import OpenMacAppTool, OpenFinderTool, CloseMacAppTool, OpenUrlTool
        from tools.mac_automation import (
            SleepMacTool, ShutdownMacTool, RestartMacTool, LockScreenTool, SetVolumeTool,
            SwitchAppTool, KillProcessTool, SendAppToTrashTool,
            SetBrightnessTool, ToggleWifiTool, ToggleBluetoothTool,
            MinimizeAppTool, MaximizeAppTool,
            CreateFileFolderTool, RenameFileFolderTool, SearchFileTool,
            AppleScriptTool, ScreenshotTool, ToggleDoNotDisturbTool, OpenSystemPreferencesPaneTool,
            MoveFileTool, OpenFileTool, CompressExtractFileTool, QuickLookTool, SendIMessageTool, CreateReminderTool,
            SendFileToTelegramTool
        )
        from tools.text_automation import ClipboardReadTool, ClipboardWriteTool, MusicControlTool
        from tools.system_tools import SystemInfoTool, BatteryStatusTool, ActiveAppTool, RunningAppsTool, OpenUrlInAppTool
        from tools.research import WebResearchTool
        from tools.system_tools import ListDirectoryTool
        from tools.browser_automation import OpenBrowserTool, BrowserScreenshotTool, BrowserActionTool
        # Input automation is optional at import time so its absence cannot prevent
        # read-only or remote integrations from starting.
        try:
            from tools.input_automation import KeyboardTypeTool, KeyboardHotkeyTool, MouseMoveClickTool, MouseMoveTool, MousePositionTool, MouseScrollTool
            input_tools_available = True
        except ImportError as exc:
            logger.warning(f"Keyboard/mouse tools unavailable: {exc}")
            input_tools_available = False
        from tools.integrations.spreadsheet import SpreadsheetTool
        from tools.integrations.discord import SendDiscordMessageTool, ReadDiscordMessagesTool
        from tools.design_generator import GenerateImageTool
        from tools.integrations.whatsapp import WhatsAppSendTool, WhatsAppReadTool
        from tools.integrations.gmail import ReadEmailTool, SendEmailTool
        from tools.integrations.notion import NotionCreatePageTool, NotionReadDatabaseTool, NotionAddCommentTool

        self.tools: Dict[str, BaseTool] = {}
        self.register(WriteFileTool())
        self.register(DeleteFileTool())
        self.register(SystemAutomationTool())
        self.register(SystemInfoTool())
        self.register(BatteryStatusTool())
        self.register(ActiveAppTool())
        self.register(RunningAppsTool())
        self.register(OpenUrlInAppTool())
        self.register(ListDirectoryTool())
        self.register(WebResearchTool())
        
        # macOS System Control (Batch 1)
        self.register(SleepMacTool())
        self.register(ShutdownMacTool())
        self.register(RestartMacTool())
        self.register(LockScreenTool())
        self.register(SetVolumeTool())
        self.register(SetBrightnessTool())
        self.register(ToggleWifiTool())
        self.register(ToggleBluetoothTool())
        self.register(ToggleDoNotDisturbTool())
        self.register(OpenSystemPreferencesPaneTool())

        # macOS Application Control (Batch 1)
        self.register(SwitchAppTool())
        self.register(KillProcessTool())
        self.register(SendAppToTrashTool())
        self.register(MinimizeAppTool())
        self.register(MaximizeAppTool())

        # File Operations
        self.register(CreateFileFolderTool())
        self.register(RenameFileFolderTool())
        self.register(SearchFileTool())
        self.register(MoveFileTool())
        self.register(OpenFileTool())
        self.register(CompressExtractFileTool())
        self.register(QuickLookTool())

        # Keyboard & Mouse
        if input_tools_available:
            self.register(KeyboardTypeTool())
            self.register(KeyboardHotkeyTool())
            self.register(MouseMoveClickTool())
            self.register(MouseMoveTool())
            self.register(MousePositionTool())
            self.register(MouseScrollTool())

        # Media & Text
        self.register(AppleScriptTool())
        self.register(ScreenshotTool())
        self.register(ClipboardReadTool())
        self.register(ClipboardWriteTool())
        self.register(MusicControlTool())
        
        # Phase 1: Local Automation & Web
        self.register(OpenMacAppTool())
        self.register(OpenFinderTool())
        self.register(CloseMacAppTool())
        self.register(OpenBrowserTool())
        self.register(BrowserScreenshotTool())
        self.register(BrowserActionTool())
        self.register(OpenUrlTool())

        # Phase 3 & 4: Integrations, Design, & WhatsApp
        self.register(SpreadsheetTool())
        self.register(SendDiscordMessageTool())
        self.register(ReadDiscordMessagesTool())
        self.register(GenerateImageTool())
        self.register(WhatsAppSendTool())
        self.register(WhatsAppReadTool())
        self.register(ReadEmailTool())
        self.register(SendEmailTool())
        self.register(NotionCreatePageTool())
        self.register(NotionReadDatabaseTool())
        self.register(NotionAddCommentTool())
        self.register(SendIMessageTool())
        self.register(CreateReminderTool())
        self.register(SendFileToTelegramTool())

        # Load optional local plugins without making startup depend on them.
        plugin_dir = Path(__file__).parent.parent / "plugins"
        for plugin_file in sorted(plugin_dir.glob("*.py")):
            if plugin_file.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(f"myclaw_plugin_{plugin_file.stem}", plugin_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for tool in getattr(module, "get_tools", lambda: [])() or []:
                    self.register(tool)
                    logger.info(f"Loaded plugin tool: {tool.name}")
            except Exception as exc:
                logger.error(f"Plugin {plugin_file.name} gagal dimuat: {exc}")


        
    def register(self, tool: BaseTool):
        self.tools[tool.name] = tool
        
    def get_tool(self, name: str) -> BaseTool:
        if name not in self.tools:
            raise ValueError(f"Tool {name} not found")
        return self.tools[name]
