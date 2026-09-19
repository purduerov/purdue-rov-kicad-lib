#!/usr/bin/env python3
"""
Purdue ROV KiCad Library - Symbol Compiler
Compiles individual symbol files (Symbols/parts/<category>/<name>.kicad_sym)
into central monolithic category libraries (Symbols/rov_<category>.kicad_sym).
Eliminates Git merge conflicts while preserving KiCad's 6-category browser UI.
"""

import sys
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

from kicad_sym_utils import (
    validate_sexpr,
    extract_top_symbols,
    CATEGORIES,
    format_library_header
)

SYMBOLS_DIR = BASE_DIR / "Symbols"
PARTS_DIR = SYMBOLS_DIR / "parts"

CATEGORY_FILES = {
    "Passives": "rov_passives",
    "Power": "rov_power",
    "Logic": "rov_logic",
    "Connectors": "rov_connectors",
    "Sensors": "rov_sensors",
    "Mech": "rov_mech"
}


def build_all_categories():
    """
    Scans Symbols/parts/<category>/ for all *.kicad_sym files, validates them,
    and compiles them into Symbols/rov_<category>.kicad_sym.
    """
    PARTS_DIR.mkdir(parents=True, exist_ok=True)
    summary = {}

    for cat in CATEGORIES:
        cat_folder = PARTS_DIR / cat.lower()
        cat_folder.mkdir(parents=True, exist_ok=True)
        target_file = SYMBOLS_DIR / f"{CATEGORY_FILES[cat]}.kicad_sym"

        # Find all individual part symbol files
        sym_files = sorted(cat_folder.glob("*.kicad_sym"))
        symbols_found = []

        for f in sym_files:
            try:
                content = f.read_text(encoding="utf-8", errors="ignore")
                extracted = extract_top_symbols(content)
                if not extracted:
                    print(f"⚠️ Warning: No top-level symbol found in {f.name}")
                    continue
                for sym_name, raw_sym, _, _ in extracted:
                    symbols_found.append((sym_name, raw_sym.strip()))
            except Exception as e:
                print(f"❌ Error reading {f}: {e}")

        # Build monolithic category library
        header = '(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor)\n'
        if not symbols_found:
            compiled_content = header + ")\n"
        else:
            # Sort symbols alphabetically by name for deterministic builds
            symbols_found.sort(key=lambda s: s[0].lower())
            body_parts = []
            for _, raw_sym in symbols_found:
                body_parts.append(f"  {raw_sym}")
            compiled_content = header + "\n".join(body_parts) + "\n)\n"

        # Validate compiled output
        valid, err = validate_sexpr(compiled_content)
        if not valid:
            raise ValueError(f"Compiled library for {cat} has invalid S-expression syntax: {err}")

        # Write to disk
        target_file.write_text(compiled_content, encoding="utf-8")
        summary[cat] = len(symbols_found)

    return summary


def decompose_existing_libraries():
    """
    Helper to extract existing symbols from monolithic category files
    into Symbols/parts/<category>/<name>.kicad_sym if parts folder is empty.
    """
    total_decomposed = 0
    for cat in CATEGORIES:
        cat_file = SYMBOLS_DIR / f"{CATEGORY_FILES[cat]}.kicad_sym"
        cat_folder = PARTS_DIR / cat.lower()
        cat_folder.mkdir(parents=True, exist_ok=True)

        if not cat_file.exists():
            continue

        content = cat_file.read_text(encoding="utf-8", errors="ignore")
        extracted = extract_top_symbols(content)

        for sym_name, raw_sym, _, _ in extracted:
            safe_name = re.sub(r'[^a-zA-Z0-9_\-\.\+]', '_', sym_name)
            part_file = cat_folder / f"{safe_name}.kicad_sym"
            
            # Wrap into a standalone valid .kicad_sym file
            part_content = (
                '(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor)\n'
                f'  {raw_sym.strip()}\n'
                ')\n'
            )
            part_file.write_text(part_content, encoding="utf-8")
            total_decomposed += 1

    return total_decomposed


if __name__ == "__main__":
    # Check if parts directory is currently empty
    any_parts = list(PARTS_DIR.rglob("*.kicad_sym")) if PARTS_DIR.exists() else []
    if not any_parts:
        print("📦 Decomposing existing monolithic libraries into individual part files...")
        count = decompose_existing_libraries()
        print(f"✅ Decomposed {count} symbols into {PARTS_DIR}")

    print("🔨 Compiling individual part files into monolithic category libraries...")
    results = build_all_categories()
    for cat, count in results.items():
        print(f"  • rov_{cat.lower()}: {count} component(s)")
    print("✅ All category libraries compiled and verified!")
