#!/bin/bash
# Helper script to run basec CLI with virtual environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Error: Virtual environment not found. Run: python -m venv .venv"
    exit 1
fi

# Activate virtual environment and run basec
source "$VENV_DIR/bin/activate"
exec "$VENV_DIR/bin/basec" "$@"


