"""Read-only system introspection tools for remote diagnostics."""

from config.tool_registry import BaseTool, ToolCategory
import platform
import subprocess
import psutil


class SystemInfoTool(BaseTool):
    name = "system_info"
    description = "Menampilkan status Mac: OS, CPU, RAM, disk, dan uptime. Params: none"
    category = ToolCategory.SYSTEM

    async def execute(self) -> str:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        uptime = int(__import__("time").time() - psutil.boot_time())
        hours, rem = divmod(uptime, 3600)
        minutes = rem // 60
        return (
            f"OS: {platform.platform()}\n"
            f"CPU: {psutil.cpu_percent(interval=0.2):.1f}% ({psutil.cpu_count()} logical cores)\n"
            f"RAM: {memory.percent:.1f}% used ({memory.available / 1024**3:.1f} GB free)\n"
            f"Disk: {disk.percent:.1f}% used ({disk.free / 1024**3:.1f} GB free)\n"
            f"Uptime: {hours}h {minutes}m"
        )


class BatteryStatusTool(BaseTool):
    name = "battery_status"
    description = "Menampilkan status baterai dan charger Mac. Params: none"
    category = ToolCategory.SYSTEM

    async def execute(self) -> str:
        battery = psutil.sensors_battery()
        if battery is None:
            return "Status baterai tidak tersedia (mungkin Mac desktop)."
        state = "mengisi daya" if battery.power_plugged else "tidak terhubung charger"
        return f"Baterai: {battery.percent:.0f}% ({state})"


class ActiveAppTool(BaseTool):
    name = "active_app"
    description = "Menampilkan aplikasi yang sedang aktif di depan. Params: none"
    category = ToolCategory.MAC_OS

    async def execute(self) -> str:
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to name of first process whose frontmost is true'],
            capture_output=True, text=True,
        )
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "Tidak dapat membaca aplikasi aktif.")
        return f"Aplikasi aktif: {result.stdout.strip()}"


class RunningAppsTool(BaseTool):
    name = "running_apps"
    description = "Menampilkan daftar aplikasi yang sedang berjalan. Params: none"
    category = ToolCategory.SYSTEM

    async def execute(self) -> str:
        result = subprocess.run(["ps", "-axo", "comm="], capture_output=True, text=True)
        apps = sorted({line.strip().split("/")[-1] for line in result.stdout.splitlines() if line.strip() and ".app/" in line})
        return "Aplikasi berjalan:\n" + ("\n".join(f"- {app}" for app in apps[:40]) if apps else "Tidak ditemukan.")


class OpenUrlInAppTool(BaseTool):
    name = "open_url_in_app"
    description = "Membuka URL menggunakan aplikasi tertentu. Params: url, app_name"
    category = ToolCategory.WEB

    async def execute(self, url: str, app_name: str) -> str:
        from tools.mac_automation import _resolve_app_name
        if not url.startswith(("https://", "http://")):
            raise ValueError("URL harus diawali http:// atau https://")
        app = _resolve_app_name(app_name)
        result = subprocess.run(["open", "-a", app, url], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or f"Aplikasi '{app}' tidak ditemukan.")
        return f"URL dibuka di {app}: {url}"


class ListDirectoryTool(BaseTool):
    name = "list_directory"
    description = "Menampilkan isi folder secara read-only. Params: path (default home directory)"
    category = ToolCategory.FILE

    async def execute(self, path: str = "~") -> str:
        from pathlib import Path
        folder = Path(path or "~").expanduser().resolve()
        if not folder.is_dir():
            raise ValueError(f"Folder tidak ditemukan: {folder}")
        entries = sorted(folder.iterdir(), key=lambda item: (not item.is_dir(), item.name.casefold()))
        if not entries:
            return f"Folder kosong: {folder}"
        lines = [f"{'[DIR]' if item.is_dir() else '[FILE]'} {item.name}" for item in entries[:100]]
        suffix = "\n... (hasil dibatasi 100 item)" if len(entries) > 100 else ""
        return f"Isi folder {folder}:\n" + "\n".join(lines) + suffix
