#!/usr/bin/env bash
# 1-Click Launcher for Purdue ROV KiCad Central Library Manager
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

if ! command -v "$PYTHON_CMD" &> /dev/null; then
    echo "===================================================================="
    echo "[ERROR] Python was not found on your system!"
    echo "Please install Python 3 (with tkinter enabled) from python.org or via Homebrew/apt."
    echo "===================================================================="
    exit 1
fi

"$PYTHON_CMD" "$SCRIPT_DIR/scripts/library_manager_gui.py"
