"""Small, explicit preflight checks for macOS privacy permissions."""

from __future__ import annotations

import platform
from typing import Optional


class MacOSPermissionError(RuntimeError):
    """Raised when macOS has not granted an automation permission."""


def require_macos() -> None:
    if platform.system() != "Darwin":
        raise MacOSPermissionError("Aksi ini hanya tersedia di macOS.")


def require_accessibility() -> None:
    """Check the Accessibility permission used for keyboard/mouse automation."""
    require_macos()
    try:
        from ApplicationServices import AXIsProcessTrusted
    except ImportError as exc:
        raise MacOSPermissionError(
            "Pemeriksaan Accessibility membutuhkan PyObjC. Jalankan `pip install pyobjc`."
        ) from exc
    if not AXIsProcessTrusted():
        raise MacOSPermissionError(
            "Izin Accessibility belum diberikan. Buka System Settings > Privacy & Security "
            "> Accessibility, lalu aktifkan aplikasi terminal/Python yang menjalankan MyClaw."
        )


def automation_permission_hint(target: Optional[str] = None) -> str:
    target_text = f" untuk {target}" if target else ""
    return (
        "macOS menolak Automation"
        f"{target_text}. Buka System Settings > Privacy & Security > Automation, "
        "aktifkan aplikasi terminal/Python yang menjalankan MyClaw, lalu coba lagi."
    )
