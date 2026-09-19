#!/usr/bin/env python3
"""
Purdue ROV KiCad Library - Automated Part Importer CLI
Automates adding newly downloaded symbols (.kicad_sym) and footprints (.kicad_mod) into the standard library categories.

Usage (Interactive):
    python scripts/import_part.py

Usage (CLI Arguments):
    python scripts/import_part.py \
      --symbol path/to/part.kicad_sym \
      --footprint path/to/part.kicad_mod \
      --category Power \
      --mpn "TPS62130" \
      --mfr "Texas Instruments" \
      --datasheet "https://www.ti.com/lit/ds/symlink/tps62130.pdf" \
      --digikey "296-30230-1-ND" \
      --temp "-40°C to 125°C"
"""

import sys
import os
import re
import shutil
import argparse
from pathlib import Path
import subprocess

# Add script directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from kicad_sym_utils import (
    validate_sexpr,
    extract_top_symbols,
    parse_symbol_properties,
    update_or_inject_properties,
    autofill_component_data,
    clean_symbol_lib_file,
    get_standard_passive_symbol,
    rename_symbol,
    link_3d_model_to_footprint,
    CATEGORIES as ALLOWED_CATEGORIES
)

BASE_DIR = Path(__file__).resolve().parent.parent
SYMBOLS_DIR = BASE_DIR / "Symbols"
FOOTPRINTS_DIR = BASE_DIR / "Footprints"
MANDATORY_FIELDS = ["MPN", "Manufacturer", "Datasheet", "Temp_Range", "DigiKey", "Category"]

def parse_existing_properties(sym_str):
    props, _ = parse_symbol_properties(sym_str)
    return props

def inject_or_update_properties(sym_str, field_updates, next_id_start=10):
    return update_or_inject_properties(sym_str, field_updates, next_id_start=next_id_start)

def extract_symbols_from_file(sym_filepath):
    with open(sym_filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    return [s[1] for s in extract_top_symbols(content)]

def append_symbol_to_category(cat, sym_block):
    target_sym_file = SYMBOLS_DIR / f"rov_{cat.lower()}.kicad_sym"
    if not target_sym_file.exists():
        target_sym_file.write_text('(kicad_symbol_lib\n  (version 20211014)\n  (generator "kicad_symbol_editor")\n)\n', encoding='utf-8')
        
    clean_symbol_lib_file(target_sym_file)
    content = target_sym_file.read_text(encoding='utf-8').rstrip()
    
    last_paren = content.rfind(')')
    if last_paren != -1:
        new_content = content[:last_paren].rstrip() + "\n  " + sym_block.strip() + "\n)\n"
    else:
        new_content = content + "\n  " + sym_block.strip() + "\n)\n"
        
    is_valid, err = validate_sexpr(new_content)
    if not is_valid:
        raise ValueError(f"Failed to generate valid S-expression for {cat}: {err}")
        
    target_sym_file.write_text(new_content, encoding='utf-8')
    print(f"✅ Added symbol to: {target_sym_file}")

def copy_footprint_to_category(cat, fp_filepath):
    target_fp_dir = FOOTPRINTS_DIR / f"rov_{cat.lower()}.pretty"
    target_fp_dir.mkdir(parents=True, exist_ok=True)
    
    dest_path = target_fp_dir / Path(fp_filepath).name
    shutil.copy2(fp_filepath, dest_path)
    print(f"✅ Copied footprint to: {dest_path}")
    return Path(fp_filepath).stem

def interactive_mode():
    print("=" * 60)
    print("  Purdue ROV KiCad Library - Part Import Wizard")
    print("=" * 60)
    
    sym_path = input("📁 Path to downloaded symbol (.kicad_sym) file (press Enter for standard Passive): ").strip('"\' ')
    if sym_path and not os.path.exists(sym_path):
        print("❌ File not found. Please enter a valid path.")
        sym_path = input("📁 Path to downloaded symbol (.kicad_sym) file (press Enter for standard Passive): ").strip('"\' ')
        
    fp_path = input("📁 Path to footprint (.kicad_mod) file (press Enter if none): ").strip('"\' ')
    if fp_path and not os.path.exists(fp_path):
        print("⚠️ Footprint file not found, proceeding without footprint copy.")
        fp_path = None

    model_3d_path = input("📁 Path to 3D model (.step/.stp) file (press Enter if none): ").strip('"\' ')
    if model_3d_path and not os.path.exists(model_3d_path):
        print("⚠️ 3D model file not found, proceeding without 3D copy.")
        model_3d_path = None

    sym_block = None
    if sym_path and os.path.exists(sym_path):
        symbols = extract_symbols_from_file(sym_path)
        if symbols:
            sym_block = symbols[0]

    fp_name_guess = Path(fp_path).stem if fp_path else None
    if sym_block:
        autofilled = autofill_component_data(sym_block, fp_name=fp_name_guess)
    else:
        autofilled = {"Category": "Passives", "MPN": fp_name_guess or "", "Temp_Range": "-55°C to 125°C"}
    
    print("\nSelect Component Category:")
    default_cat_idx = 1
    for idx, cat in enumerate(ALLOWED_CATEGORIES, 1):
        marker = " (Detected)" if cat == autofilled.get("Category") else ""
        if cat == autofilled.get("Category"):
            default_cat_idx = idx
        print(f"  {idx}. {cat}{marker}")
    cat_idx = input(f"Enter choice (1-6) [{default_cat_idx}]: ").strip()
    if not cat_idx:
        category = ALLOWED_CATEGORIES[default_cat_idx - 1]
    elif cat_idx.isdigit() and 1 <= int(cat_idx) <= len(ALLOWED_CATEGORIES):
        category = ALLOWED_CATEGORIES[int(cat_idx) - 1]
    else:
        category = autofilled.get("Category", "Power")
    
    passive_type = "R"
    if category == "Passives":
        print("\nSelect Standard KiCad Passive Symbol Type:")
        print("  1. Resistor (R)")
        print("  2. Capacitor (C)")
        print("  3. Polarized Capacitor (C_Polarized)")
        print("  4. Inductor (L)")
        print("  5. Ferrite Bead (L_Ferrite)")
        pt_choice = input("Enter choice (1-5) [1]: ").strip()
        pt_map = {"1": "R", "2": "C", "3": "C_Polarized", "4": "L", "5": "L_Ferrite"}
        passive_type = pt_map.get(pt_choice, "R")

    print(f"\nProvide Component Fields (Press Enter to keep detected values):")
    mpn = input(f"  MPN [{autofilled.get('MPN', '')}]: ").strip() or autofilled.get('MPN', '')
    mfr = input(f"  Manufacturer [{autofilled.get('Manufacturer', '')}]: ").strip() or autofilled.get('Manufacturer', '')
    datasheet = input(f"  Datasheet URL [{autofilled.get('Datasheet', '')}]: ").strip() or autofilled.get('Datasheet', '')
    digikey = input(f"  DigiKey Part # [{autofilled.get('DigiKey', '')}]: ").strip() or autofilled.get('DigiKey', '')
    temp = input(f"  Temp Range [{autofilled.get('Temp_Range', '-40°C to 125°C')}]: ").strip() or autofilled.get('Temp_Range', '-40°C to 125°C')

    fp_name = None
    if fp_path:
        fp_name = copy_footprint_to_category(category, fp_path)
        dest_fp = FOOTPRINTS_DIR / f"rov_{category.lower()}.pretty" / Path(fp_path).name
        if model_3d_path:
            models_dir = BASE_DIR / "3D_Models"
            models_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(model_3d_path, models_dir / Path(model_3d_path).name)
            link_3d_model_to_footprint(dest_fp, Path(model_3d_path).name)
        fp_ref = f"rov_{category.lower()}:{fp_name}"
    else:
        fp_ref = autofilled.get('Footprint', '')
        
    field_updates = {
        "Category": category,
        "MPN": mpn,
        "Manufacturer": mfr,
        "Datasheet": datasheet,
        "DigiKey": digikey,
        "Temp_Range": temp,
        "Footprint": fp_ref
    }
    
    if category == "Passives":
        sym_name = mpn or fp_name or "PASSIVE_PART"
        updated_sym = get_standard_passive_symbol(passive_type, sym_name, field_updates)
    else:
        if not sym_block:
            print("❌ Active/Connector/Sensor/Power parts require an input .kicad_sym file!")
            sys.exit(1)
        if mpn:
            sym_block = rename_symbol(sym_block, mpn)
        updated_sym = inject_or_update_properties(sym_block, field_updates)

    append_symbol_to_category(category, updated_sym)
    
    print("\n🔍 Running Linter Verification...")
    linter_script = BASE_DIR / "scripts" / "linter_validator.py"
    result = subprocess.run([sys.executable, str(linter_script)] + [str(p) for p in SYMBOLS_DIR.glob("*.kicad_sym")])
    
    if result.returncode == 0:
        print("\n🎉 Part imported successfully and verified compliant!")
        git_commit = input("Commit & Push to master now? (y/N): ").strip().lower()
        if git_commit == 'y':
            subprocess.run(["git", "add", "Symbols/", "Footprints/", "3D_Models/"], cwd=str(BASE_DIR))
            subprocess.run(["git", "commit", "-m", f"feat(lib): add {mpn or 'new part'} to {category} library"], cwd=str(BASE_DIR))
            subprocess.run(["git", "push", "origin", "master"], cwd=str(BASE_DIR))
            print("🚀 Pushed to remote master!")
    else:
        print("\n❌ Linter check failed. Please correct fields.")

def main():
    parser = argparse.ArgumentParser(description="Import parts into Purdue ROV KiCad Library")
    parser.add_argument("--symbol", help="Path to downloaded .kicad_sym file")
    parser.add_argument("--footprint", help="Path to downloaded .kicad_mod file")
    parser.add_argument("--category", choices=ALLOWED_CATEGORIES, help="Component Category")
    parser.add_argument("--mpn", help="Manufacturer Part Number")
    parser.add_argument("--mfr", help="Manufacturer")
    parser.add_argument("--datasheet", help="Datasheet PDF URL")
    parser.add_argument("--digikey", help="DigiKey SKU / Part Number")
    parser.add_argument("--temp", default="-40°C to 125°C", help="Temperature Range")
    
    args = parser.parse_args()
    
    if not args.symbol:
        interactive_mode()
        return
        
    if not os.path.exists(args.symbol):
        print(f"❌ Symbol file not found: {args.symbol}")
        sys.exit(1)
        
    symbols = extract_symbols_from_file(args.symbol)
    if not symbols:
        print("❌ No valid symbols found in file!")
        sys.exit(1)
        
    sym_block = symbols[0]
    autofilled = autofill_component_data(sym_block)
    
    category = args.category or autofilled.get("Category", "Mech")
    fp_ref = autofilled.get("Footprint", "")
    
    if args.footprint and os.path.exists(args.footprint):
        fp_name = copy_footprint_to_category(category, args.footprint)
        fp_ref = f"rov_{category.lower()}:{fp_name}"
        
    field_updates = {
        "Category": category,
        "MPN": args.mpn or autofilled.get("MPN", ""),
        "Manufacturer": args.mfr or autofilled.get("Manufacturer", ""),
        "Datasheet": args.datasheet or autofilled.get("Datasheet", ""),
        "DigiKey": args.digikey or autofilled.get("DigiKey", ""),
        "Temp_Range": args.temp or autofilled.get("Temp_Range", "-40°C to 125°C"),
        "Footprint": fp_ref
    }
    
    target_mpn = field_updates["MPN"]
    if target_mpn:
        sym_block = rename_symbol(sym_block, target_mpn)

    updated_sym = inject_or_update_properties(sym_block, field_updates)
    append_symbol_to_category(category, updated_sym)
    
    # Run linter
    linter_script = BASE_DIR / "scripts" / "linter_validator.py"
    subprocess.run([sys.executable, str(linter_script)] + [str(p) for p in SYMBOLS_DIR.glob("*.kicad_sym")])

if __name__ == "__main__":
    main()
