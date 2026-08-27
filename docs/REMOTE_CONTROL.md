# Remote control (PRD Layer 1)

MyClaw's `/live` endpoint is monitoring only. For full cursor/keyboard control,
use macOS Screen Sharing over a private Tailscale network. This avoids exposing
a remote-desktop port to the public internet.

1. Install Tailscale on the Mac and phone, sign in to the same tailnet, and
   confirm both devices appear online.
2. On the Mac open **System Settings → General → Sharing → Screen Sharing** and
   allow the account you will use. Keep the firewall enabled.
3. Grant **Accessibility** and **Screen Recording** to the Python/Terminal host
   that launches MyClaw. LaunchAgent services inherit these permissions from
   the signed-in user session.
4. Run `venv/bin/python scripts/check_remote_control.py` to verify readiness.
5. Restart the LaunchAgent: `launchctl kickstart -k gui/$(id -u)/com.myclaw.telegram`.
6. Use a VNC/Screen Sharing client on the phone with the Mac's Tailscale IPv4.

The secure default binds MyClaw's monitoring endpoint to localhost. When
Tailscale is installed and connected, MyClaw automatically binds to its
private IPv4 after restart, so `/live` returns a phone-reachable private URL.
Do not port-forward port 8765 or expose it on the public internet.
