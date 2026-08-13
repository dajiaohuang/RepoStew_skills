#!/usr/bin/env sh
# POSIX convenience wrapper. On Windows, run auto_fix.py directly.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$SCRIPT_DIR/auto_fix.py" "$@"
