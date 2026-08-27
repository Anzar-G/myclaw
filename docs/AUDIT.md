# MyClaw audit — 2026-08-27

## PRD execution update — 2026-08-28

- Live view now serves a mobile-compatible HTML page that polls authenticated JPEG frames; the legacy MJPEG endpoint remains at `/stream`.
- Secure bind defaults to `127.0.0.1`. If Tailscale is installed and connected, the service automatically binds to its private IPv4 after restart; no public port-forwarding is required.
- Added `scripts/check_remote_control.py` and `deploy/REMOTE_CONTROL.md` for Tailscale + macOS Screen Sharing readiness.
- Added `/log` to expose a redacted tail of the audit log to the authorized Telegram chat, and execution events are now recorded there.
- Added persistent recurring reminders through `/schedule_every <menit> <pesan>`; recurring entries survive restart and can be cancelled with `/cancel_schedule`.
- Workflow steps now expose explicit checkpoint states (`passed`, `failed`, `rejected`) and stop safely after a failed/rejected checkpoint.
- AppleScript string parameters for app/window activation and Finder trash actions are now escaped before interpolation; arbitrary custom AppleScript remains approval-gated.
- The Telegram LaunchAgent was restarted and is running; local live-view health and authenticated HTML endpoint checks pass.

## Scope

Static review of the Python modules, import/startup smoke tests, tool registration, approval policy, and macOS automation boundaries. No destructive tool was executed.

## Findings and disposition

| Severity | Finding | Disposition |
|---|---|---|
| Critical | Missing `pyautogui` prevented `ToolRegistry` from importing | Added dependency and made input tools optional at import time |
| Critical | Approval without a callback auto-approved gated actions | Missing callback now rejects the action safely |
| Critical | LLM-supplied risk could downgrade dangerous tools | Parser now always applies the local risk map |
| High | `osascript`/`screencapture` failures were ignored and reported as success | Centralized exit-code and permission error handling |
| High | Keyboard/mouse actions had no Accessibility preflight | Added explicit Accessibility check and user-facing System Settings guidance |
| High | `.env`, Gmail credentials, WhatsApp session, logs, and generated data lacked ignore rules | Added `.gitignore` protections |
| High | Brightness action actually toggled dark mode; image generation returned a 1×1 placeholder | Disabled both misleading implementations with explicit `NotImplementedError` |
| Medium | Notion tool names/parameters disagreed with parser/registry | Normalized to `notion_read_database` and `comment_text` |
| Medium | Copied virtualenv's `pip`/Streamlit launchers reference an old absolute path | Dependencies and UI were run through `venv/bin/python -m pip` / `venv/bin/python -m streamlit`; recreate the venv before distributing |

## macOS permissions required by feature

Grant only to the terminal/Python launcher that runs MyClaw:

- Privacy & Security → Accessibility: keyboard, mouse, window management, lock screen.
- Privacy & Security → Automation: the target apps and System Events.
- Privacy & Security → Screen & System Audio Recording: desktop screenshots.

The application cannot grant these permissions itself. The new preflight messages identify the exact panel instead of silently claiming success.

## Known incomplete integrations

Bluetooth, Focus/DND, Spreadsheet, and image generation remain incomplete or provider-dependent. They are now surfaced as such rather than returning fabricated success.

## Verification

- Python bytecode compilation: passed.
- Tool registry import: passed, 55 tools registered.
- Command parser smoke tests: passed; shutdown is CRITICAL and email is MEDIUM.
- Real macOS actions: not run during audit to avoid changing system state; must be tested manually after permissions are granted.
