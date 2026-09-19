#!/usr/bin/env bash
# 1-Click Launcher for Purdue ROV KiCad Central Library Manager
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

"$PYTHON_CMD" "$SCRIPT_DIR/scripts/library_manager_gui.py"
