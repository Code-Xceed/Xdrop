#!/usr/bin/env bash
# Double-clickable macOS Finder command launcher for Xdrop Adobe Creative Cloud Setup
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"
chmod +x "$DIR/setup_mac.sh" 2>/dev/null || true
exec "$DIR/setup_mac.sh" --adobe "$@"
