#!/usr/bin/env bash
# 1-Click Launcher for Purdue ROV KiCad Part Importer Wizard
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/scripts/part_importer_gui.py"
