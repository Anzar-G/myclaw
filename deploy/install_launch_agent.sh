#!/bin/sh
set -eu

PROJECT_DIR="/Users/muhammadnizaralfaris/Documents/MyClaw copy"
PLIST_SOURCE="$PROJECT_DIR/deploy/com.myclaw.telegram.plist"
PLIST_TARGET="$HOME/Library/LaunchAgents/com.myclaw.telegram.plist"

mkdir -p "$HOME/Library/LaunchAgents" "$PROJECT_DIR/logs"
cp "$PLIST_SOURCE" "$PLIST_TARGET"
chmod 600 "$PLIST_TARGET"

launchctl bootout "gui/$(id -u)/com.myclaw.telegram" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_TARGET"
launchctl enable "gui/$(id -u)/com.myclaw.telegram"
launchctl kickstart -k "gui/$(id -u)/com.myclaw.telegram"

echo "MyClaw Telegram LaunchAgent aktif: $PLIST_TARGET"
