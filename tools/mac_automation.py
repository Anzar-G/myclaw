"""
Local Mac Automation Tools using AppleScript (osascript)
"""
from config.tool_registry import BaseTool, ToolCategory
import subprocess
from loguru import logger
from pathlib import Path
from difflib import SequenceMatcher
import re
from config.macos_permissions import require_accessibility, automation_permission_hint

def _as_quote(value: str) -> str:
    """Safely quote a string literal for AppleScript source."""
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n") + '"'


def _run_osascript(script: str, target: str = "System Events") -> str:
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
        if "not authorized" in detail.lower() or "-1743" in detail:
            raise PermissionError(f"{automation_permission_hint(target)} Detail: {detail}")
        raise RuntimeError(detail)
    return result.stdout.strip()


def _resolve_app_name(app_name: str) -> str:
    """Resolve conversational/typo-prone names against installed .app bundles."""
    raw = app_name.strip()
    aliases = {"brave": "Brave Browser", "browser brave": "Brave Browser", "browser arc": "Arc"}
    if raw.casefold() in aliases:
        return aliases[raw.casefold()]

    def key(value: str) -> str:
        value = re.sub(r"\.(app)$", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\b(browser|application|app)\b", " ", value, flags=re.IGNORECASE)
        return re.sub(r"[^a-z0-9]", "", value.casefold())

    requested = key(raw)
    if not requested:
        return raw

    installed = set()
    for root in (Path("/Applications"), Path("/System/Applications"), Path.home() / "Applications"):
        if root.exists():
            installed.update(p.stem for p in root.glob("*.app"))
    if not installed:
        return raw

    exact = next((name for name in installed if key(name) == requested), None)
    if exact:
        return exact

    ranked = sorted(
        ((SequenceMatcher(None, requested, key(name)).ratio(), name) for name in installed),
        reverse=True,
    )
    score, candidate = ranked[0]
    if score >= 0.62 and (len(ranked) == 1 or score - ranked[1][0] >= 0.08):
        logger.info(f"Resolved app name '{raw}' to '{candidate}' (match={score:.2f})")
        return candidate
    return raw

class OpenMacAppTool(BaseTool):
    name = "open_mac_app"
    description = "Membuka aplikasi NATIVE di Macbook (seperti Finder, Safari, Notes, Brave, dll). JANGAN GUNAKAN INI UNTUM MEMBUKA WEBSITE ATAU URL. Params: app_name"
    category = ToolCategory.SYSTEM
    
    async def execute(self, app_name: str) -> str:
        resolved = _resolve_app_name(app_name)
        result = subprocess.run(["open", "-a", resolved], capture_output=True, text=True)
        if result.returncode != 0:
            detail = result.stderr.strip() or f"Aplikasi '{resolved}' tidak ditemukan."
            raise RuntimeError(detail)
        return f"Berhasil membuka aplikasi: {resolved}"

class OpenFinderTool(BaseTool):
    name = "open_finder_path"
    description = "Membuka Finder pada folder tertentu. Params: path"
    category = ToolCategory.SYSTEM
    
    async def execute(self, path: str) -> str:
        # Native macOS open command
        result = subprocess.run(["open", path], capture_output=True, text=True)
        if result.returncode == 0:
            return f"Berhasil membuka direktori: {path}"
        raise Exception(f"Gagal membuka direktori {path}: {result.stderr}")

class CloseMacAppTool(BaseTool):
    name = "close_mac_app"
    description = "Menutup aplikasi di Macbook. Params: app_name"
    category = ToolCategory.SYSTEM
    
    async def execute(self, app_name: str) -> str:
        resolved = _resolve_app_name(app_name)
        script = f'tell application {_as_quote(resolved)} to quit'
        _run_osascript(script, resolved)
        return f"Berhasil menutup aplikasi: {resolved}"

class SleepMacTool(BaseTool):
    name = "sleep_mac"
    description = "Menidurkan (sleep) Macbook. Params: none"
    category = ToolCategory.MAC_OS
    async def execute(self) -> str:
        _run_osascript('tell application "System Events" to sleep')
        return "Macbook sedang memasuki mode sleep..."

class ShutdownMacTool(BaseTool):
    name = "shutdown_mac"
    description = "Mematikan (shutdown) Macbook. Params: none"
    category = ToolCategory.MAC_OS
    async def execute(self) -> str:
        _run_osascript('tell application "System Events" to shut down')
        return "Macbook sedang dimatikan..."

class RestartMacTool(BaseTool):
    name = "restart_mac"
    description = "Menyalakan ulang (restart) Macbook. Params: none"
    category = ToolCategory.MAC_OS
    async def execute(self) -> str:
        _run_osascript('tell application "System Events" to restart')
        return "Macbook sedang dinyalakan ulang..."

class LockScreenTool(BaseTool):
    name = "lock_screen"
    description = "Mengunci layar Macbook. Params: none"
    category = ToolCategory.MAC_OS
    async def execute(self) -> str:
        require_accessibility()
        _run_osascript('tell application "System Events" to keystroke "q" using {command down, control down}')
        return "Layar Macbook telah dikunci."

class SetVolumeTool(BaseTool):
    name = "set_volume"
    description = "Mengatur volume suara Macbook (0-100). Params: volume_level"
    category = ToolCategory.MAC_OS
    async def execute(self, volume_level: int) -> str:
        if not 0 <= volume_level <= 100:
            raise ValueError("volume_level harus di antara 0 dan 100")
        script = f"set volume output volume {volume_level}"
        _run_osascript(script, "System Settings")
        return f"Volume diatur ke {volume_level}%"

class SetBrightnessTool(BaseTool):
    name = "set_brightness"
    description = "Mengatur kecerahan layar Macbook (0.0 - 1.0). Params: brightness_level"
    category = ToolCategory.MAC_OS
    async def execute(self, brightness_level: float) -> str:
        raise NotImplementedError("Pengaturan kecerahan belum didukung secara andal; fitur ini dinonaktifkan agar tidak mengubah dark mode secara keliru.")

class ToggleWifiTool(BaseTool):
    name = "toggle_wifi"
    description = "Menyalakan atau mematikan Wi-Fi. Params: state ('on' atau 'off')"
    category = ToolCategory.MAC_OS
    async def execute(self, state: str) -> str:
        # Use networksetup
        result = subprocess.run(["networksetup", "-setairportpower", "en0", state], capture_output=True, text=True)
        if result.returncode == 0:
            return f"Wi-Fi telah diatur ke {state}"
        return f"Gagal mengatur Wi-Fi: {result.stderr}"

class ToggleBluetoothTool(BaseTool):
    name = "toggle_bluetooth"
    description = "Menyalakan atau mematikan Bluetooth. Params: state ('on' atau 'off')"
    category = ToolCategory.MAC_OS
    async def execute(self, state: str) -> str:
        # Bluetooth is tricky on macOS without blueutil. We'll try AppleScript on System Settings.
        state_bool = "true" if state == "on" else "false"
        script = 'tell application "System Events" to tell process "ControlCenter" to click checkbox "Bluetooth" of group 1 of window 1'
        # This is very UI dependent. For now, we'll provide a placeholder or use blueutil if available.
        return "Fitur Bluetooth Toggle sedang dalam pengembangan (membutuhkan blueutil atau akses UI khusus)."

class MinimizeAppTool(BaseTool):
    name = "minimize_app"
    description = "Meminimalkan (minimize) semua jendela aplikasi tertentu. Params: app_name"
    category = ToolCategory.SYSTEM
    async def execute(self, app_name: str) -> str:
        script = f'tell application "System Events" to set miniaturized of every window of process {_as_quote(app_name)} to true'
        require_accessibility()
        _run_osascript(script)
        return f"Jendela {app_name} telah diminimalkan."

class MaximizeAppTool(BaseTool):
    name = "maximize_app"
    description = "Memaksimalkan (zoom/maximize) jendela aplikasi tertentu. Params: app_name"
    category = ToolCategory.SYSTEM
    async def execute(self, app_name: str) -> str:
        script = f'tell application "System Events" to set zoomed of window 1 of process {_as_quote(app_name)} to true'
        require_accessibility()
        _run_osascript(script)
        return f"Jendela {app_name} telah dimaksimalkan."

class CreateFileFolderTool(BaseTool):
    name = "create_item"
    description = "Membuat file atau folder baru. Params: path, type ('file' atau 'folder')"
    category = ToolCategory.FILE
    async def execute(self, path: str, type: str) -> str:
        import os
        if type == "folder":
            os.makedirs(path, exist_ok=True)
            return f"Folder berhasil dibuat: {path}"
        else:
            with open(path, 'w') as f:
                pass
            return f"File berhasil dibuat: {path}"

class RenameFileFolderTool(BaseTool):
    name = "rename_item"
    description = "Mengubah nama file atau folder. Params: old_path, new_path"
    category = ToolCategory.FILE
    async def execute(self, old_path: str, new_path: str) -> str:
        import os
        os.rename(old_path, new_path)
        return f"Berhasil mengubah nama dari {old_path} menjadi {new_path}"

class SearchFileTool(BaseTool):
    name = "search_file"
    description = "Mencari file menggunakan Spotlight (mdfind). Params: query"
    category = ToolCategory.FILE
    async def execute(self, query: str) -> str:
        result = subprocess.run(["mdfind", query], capture_output=True, text=True)
        files = result.stdout.splitlines()[:10] # Limit to 10 results
        if not files:
            return "Tidak ditemukan file yang cocok."
        return "File ditemukan:\n" + "\n".join(files)

class AppleScriptTool(BaseTool):
    name = "execute_applescript"
    description = "Menjalankan script AppleScript kustom. Params: script"
    category = ToolCategory.MAC_OS
    async def execute(self, script: str) -> str:
        return f"Berhasil menjalankan script: {_run_osascript(script)}"

class ScreenshotTool(BaseTool):
    name = "take_screenshot"
    description = "Mengambil tangkapan layar seluruh desktop atau aplikasi tertentu. Params: path (opsional), app_name (opsional)"
    category = ToolCategory.MEDIA
    async def execute(self, path: str = "screenshot.png", app_name: str = "") -> dict:
        import time
        if app_name:
            script = f'tell application {_as_quote(app_name)} to activate'
            subprocess.run(["osascript", "-e", script])
            time.sleep(1) # Tunggu animasi aplikasi muncul ke depan
            
        result = subprocess.run(["screencapture", path], capture_output=True, text=True)
        if result.returncode != 0:
            raise PermissionError("Screen Recording belum diizinkan. Buka System Settings > Privacy & Security > Screen & System Audio Recording lalu aktifkan aplikasi terminal/Python yang menjalankan MyClaw.")
        return {
            "type": "file",
            "path": path,
            "caption": f"Screenshot {'dari aplikasi ' + app_name if app_name else 'Desktop'}"
        }

class SwitchAppTool(BaseTool):
    name = "switch_app"
    description = "Berpindah ke aplikasi tertentu yang sedang berjalan. Params: app_name"
    category = ToolCategory.SYSTEM
    async def execute(self, app_name: str) -> str:
        script = f'tell application {_as_quote(app_name)} to activate'
        _run_osascript(script, app_name)
        return f"Berpindah ke aplikasi {app_name}"

class KillProcessTool(BaseTool):
    name = "kill_process"
    description = "Mematikan proses aplikasi secara paksa (force quit). Params: process_name"
    category = ToolCategory.SYSTEM
    async def execute(self, process_name: str) -> str:
        result = subprocess.run(["killall", process_name], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"Proses {process_name} tidak ditemukan.")
        return f"Proses {process_name} telah dimatikan secara paksa."

class SendAppToTrashTool(BaseTool):
    name = "send_to_trash"
    description = "Memindahkan file atau folder ke Trash. Params: path"
    category = ToolCategory.FILE
    async def execute(self, path: str) -> str:
        script = f'tell application "Finder" to delete POSIX file {_as_quote(path)}'
        _run_osascript(script, "Finder")
        return f"File {path} telah dipindahkan ke Trash."

class OpenUrlTool(BaseTool):
    name = "open_url"
    description = "Membuka sebuah URL/website atau mencari sesuatu langsung di browser utama. GUNAKAN INI JIKA USER MEMINTA MEMBUKA WEBSITE SEPERTI YOUTUBE, GOOGLE, DLL. Params: url"
    category = ToolCategory.SYSTEM
    
    async def execute(self, url: str) -> str:
        if not url.startswith("http"):
            url = "https://" + url
        result = subprocess.run(["open", url], capture_output=True, text=True)
        if result.returncode == 0:
            return f"Berhasil membuka URL di browser pengguna: {url}"
        raise Exception(f"Gagal membuka URL {url}: {result.stderr}")

class ToggleDoNotDisturbTool(BaseTool):
    name = "toggle_dnd"
    description = "Mengaktifkan atau menonaktifkan mode Do Not Disturb (Focus). Params: state ('on' atau 'off')"
    category = ToolCategory.MAC_OS
    async def execute(self, state: str) -> str:
        # Note: This uses a trick with Option-Click on Notification Center, or Shortcuts on newer macOS
        if state.lower() == "on":
            script = 'tell application "System Events" to keystroke "d" using {command down, shift down, option down, control down}'
            # A more robust way for macOS Monterey+ is running a shortcut if it exists, or just return placeholder
        else:
            script = 'tell application "System Events" to keystroke "d" using {command down, shift down, option down, control down}'
        return "Fitur Do Not Disturb sedang dalam pengembangan untuk mendukung semua versi macOS. Silakan set manual."

class OpenSystemPreferencesPaneTool(BaseTool):
    name = "open_sys_prefs"
    description = "Membuka bagian tertentu di System Settings. Params: pane_name (contoh: 'displays', 'network', 'sound')"
    category = ToolCategory.MAC_OS
    async def execute(self, pane_name: str) -> str:
        result = subprocess.run(["open", f"x-apple.systempreferences:com.apple.preference.{pane_name}"], capture_output=True, text=True)
        if result.returncode == 0:
            return f"Berhasil membuka System Settings: {pane_name}"
        raise Exception(f"Gagal membuka pengaturan: {result.stderr}")

class MoveFileTool(BaseTool):
    name = "move_file"
    description = "Memindahkan file atau folder. Params: source_path, dest_path"
    category = ToolCategory.FILE
    async def execute(self, source_path: str, dest_path: str) -> str:
        import shutil
        shutil.move(source_path, dest_path)
        return f"File dipindahkan dari {source_path} ke {dest_path}."

class OpenFileTool(BaseTool):
    name = "open_file"
    description = "Membuka file menggunakan aplikasi defaultnya. Params: path"
    category = ToolCategory.FILE
    async def execute(self, path: str) -> str:
        result = subprocess.run(["open", path], capture_output=True, text=True)
        if result.returncode == 0:
            return f"File {path} berhasil dibuka."
        raise Exception(f"Gagal membuka file: {result.stderr}")

class CompressExtractFileTool(BaseTool):
    name = "compress_extract"
    description = "Mengompres ke zip atau mengekstrak file zip. Params: action ('compress' atau 'extract'), source_path, dest_path (opsional)"
    category = ToolCategory.FILE
    async def execute(self, action: str, source_path: str, dest_path: str = "") -> str:
        if action == "compress":
            dest = dest_path if dest_path else source_path + ".zip"
            result = subprocess.run(["zip", "-r", dest, source_path], capture_output=True, text=True)
        elif action == "extract":
            dest = dest_path if dest_path else "."
            result = subprocess.run(["unzip", source_path, "-d", dest], capture_output=True, text=True)
        else:
            raise ValueError("Action must be 'compress' or 'extract'")
        
        if result.returncode == 0:
            return f"Berhasil melakukan {action} pada {source_path}."
        raise Exception(f"Gagal {action}: {result.stderr}")

class QuickLookTool(BaseTool):
    name = "quick_look"
    description = "Membuka preview file (Quick Look). Params: path"
    category = ToolCategory.FILE
    async def execute(self, path: str) -> str:
        subprocess.Popen(["qlmanage", "-p", path])
        return f"Menampilkan preview untuk {path}."

class SendIMessageTool(BaseTool):
    name = "send_imessage"
    description = "Mengirim pesan iMessage/SMS melalui aplikasi Messages. Params: contact_number, message"
    category = ToolCategory.COMMUNICATION
    async def execute(self, contact_number: str, message: str) -> str:
        script = f'''
        tell application "Messages"
            set targetService to 1st service whose service type = iMessage
            set targetBuddy to buddy "{contact_number}" of targetService
            send "{message}" to targetBuddy
        end tell
        '''
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if result.returncode == 0:
            return f"Pesan terkirim ke {contact_number}."
        raise Exception(f"Gagal mengirim pesan: {result.stderr}")

class CreateReminderTool(BaseTool):
    name = "create_reminder"
    description = "Membuat pengingat (Reminder) baru di macOS. Params: title, list_name (opsional, default: 'Reminders')"
    category = ToolCategory.MAC_OS
    async def execute(self, title: str, list_name: str = "Reminders") -> str:
        script = f'''
        tell application "Reminders"
            tell list "{list_name}"
                make new reminder with properties {{name:"{title}"}}
            end tell
        end tell
        '''
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if result.returncode == 0:
            return f"Pengingat '{title}' berhasil dibuat."
        raise Exception(f"Gagal membuat pengingat: {result.stderr}")

class SendFileToTelegramTool(BaseTool):
    name = "send_file_to_telegram"
    description = "Mengirimkan dokumen atau file yang ada di Mac pengguna ke chat Telegram. Params: path"
    category = ToolCategory.COMMUNICATION
    async def execute(self, path: str) -> dict:
        import os
        if not os.path.exists(path):
            raise Exception(f"File {path} tidak ditemukan.")
        return {
            "type": "file",
            "path": path,
            "caption": f"Berikut adalah file yang Anda minta: {os.path.basename(path)}"
        }
