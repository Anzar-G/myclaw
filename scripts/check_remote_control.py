"""Read-only readiness check for PRD Layer 1 remote control."""
import os
import shutil
import subprocess


def run(command):
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=4, check=False)
    except (OSError, subprocess.SubprocessError):
        return None


def main():
    tailscale = shutil.which("tailscale")
    print("MyClaw remote-control readiness")
    print(f"Tailscale CLI: {'installed' if tailscale else 'NOT installed'}")
    if tailscale:
        status = run([tailscale, "status", "--self"])
        ips = run([tailscale, "ip", "-4"])
        print(f"Tailscale state: {(status.stdout.strip() if status else 'unavailable') or 'not connected'}")
        print(f"Tailscale IPv4: {(ips.stdout.strip() if ips else '') or 'none'}")
    bind = os.getenv("LIVE_VIEW_BIND", "127.0.0.1")
    print(f"Live-view bind: {bind}")
    print("Screen Sharing: enable it in System Settings > General > Sharing")
    print("Accessibility + Screen Recording: grant them to the LaunchAgent's Python/Terminal host")
    if not tailscale:
        print("Next: install Tailscale, sign in on this Mac and phone, then restart MyClaw.")


if __name__ == "__main__":
    main()
