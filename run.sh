#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
export PYTHONPATH="$DIR/src/desktop-service:$PYTHONPATH"
if command -v python3 >/dev/null 2>&1; then
    exec python3 -m xdrop.main "$@"
else
    exec python -m xdrop.main "$@"
fi
