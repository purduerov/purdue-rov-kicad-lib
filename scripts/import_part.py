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

BASE_DIR = Path(__file__).resolve().parent.parent
SYMBOLS_DIR = BASE_DIR / "Symbols"
FOOTPRINTS_DIR = BASE_DIR / "Footprints"

ALLOWED_CATEGORIES = ["Passives", "Power", "Logic", "Connectors", "Sensors", "Mech"]
MANDATORY_FIELDS = ["MPN", "Manufacturer", "Datasheet", "Temp_Range", "DigiKey", "Category"]

def parse_existing_properties(sym_str):
    props = {}
    for match in re.finditer(r'\(property "([^"]+)" "([^"]*)"', sym_str):
        name, val = match.group(1), match.group(2)
        if name == "DigiKey_SKU":
            name = "DigiKey"
        props[name] = val
    return props

def inject_or_update_properties(sym_str, field_updates, next_id_start=10):
    lines = sym_str.split('\n')
    existing_props = parse_existing_properties(sym_str)
    
    ids = [int(m) for m in re.findall(r'\(id\s+(\d+)\)', sym_str)]
    next_id = max(ids) + 1 if ids else next_id_start
    
    for field, value in field_updates.items():
        if not value:
            continue
            
        # If field exists, update it in place
        pattern = re.compile(rf'(\(property "{re.escape(field)}"\s+")[^"]*(")', re.IGNORECASE)
        if pattern.search(sym_str):
            sym_str = pattern.sub(rf'\g<1>{value}\g<2>', sym_str)
        else:
            # Inject new property right after symbol declaration line or first property
            indent = "    "
            new_prop = f'{indent}(property "{field}" "{value}" (id {next_id}) (at 0 0 0)\n{indent}  (effects (font (size 1.27 1.27)) hide)\n{indent})'
            next_id += 1
            
            # Find insertion point after initial symbol line or existing property
            insert_idx = 1
            l_list = sym_str.split('\n')
            for idx, l in enumerate(l_list):
                if re.search(r'^\s*\(property\s', l):
                    insert_idx = idx
                    break
            l_list.insert(insert_idx, new_prop)
            sym_str = '\n'.join(l_list)
            
    return sym_str

def extract_symbols_from_file(sym_filepath):
    with open(sym_filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        
    lines = content.split('\n')
    symbols = []
    current_symbol_lines = []
    paren_depth = 0
    in_symbol = False
    
    for line in lines:
        if not in_symbol:
            if re.match(r'^\s*\(symbol\s', line):
                in_symbol = True
                current_symbol_lines = [line]
                paren_depth = line.count('(') - line.count(')')
        else:
            current_symbol_lines.append(line)
            paren_depth += line.count('(') - line.count(')')
            if paren_depth == 0:
                symbols.append('\n'.join(current_symbol_lines))
                in_symbol = False
                
    return symbols

def append_symbol_to_category(cat, sym_block):
    target_sym_file = SYMBOLS_DIR / f"rov_{cat.lower()}.kicad_sym"
    if not target_sym_file.exists():
        # Create empty library header if file doesn't exist
        header = '(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor)\n'
        footer = ')\n'
        target_sym_file.write_text(header + footer, encoding='utf-8')
        
    content = target_sym_file.read_text(encoding='utf-8').rstrip()
    
    # Remove final closing parenthesis, append symbol, then re-add closing parenthesis
    if content.endswith(')'):
        content = content[:-1].rstrip()
        
    new_content = content + "\n" + sym_block.strip() + "\n)\n"
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
    
    sym_path = input("📁 Path to downloaded symbol (.kicad_sym) file: ").strip('"\' ')
    while not os.path.exists(sym_path):
        print("❌ File not found. Please enter a valid path.")
        sym_path = input("📁 Path to downloaded symbol (.kicad_sym) file: ").strip('"\' ')
        
    fp_path = input("📁 Path to downloaded footprint (.kicad_mod) file (press Enter if none): ").strip('"\' ')
    if fp_path and not os.path.exists(fp_path):
        print("⚠️ Footprint file not found, proceeding without footprint copy.")
        fp_path = None
        
    print("\nSelect Component Category:")
    for idx, cat in enumerate(ALLOWED_CATEGORIES, 1):
        print(f"  {idx}. {cat}")
    cat_idx = input("Enter choice (1-6): ").strip()
    while not (cat_idx.isdigit() and 1 <= int(cat_idx) <= len(ALLOWED_CATEGORIES)):
        cat_idx = input("Invalid choice. Enter choice (1-6): ").strip()
    category = ALLOWED_CATEGORIES[int(cat_idx) - 1]
    
    symbols = extract_symbols_from_file(sym_path)
    if not symbols:
        print("❌ No symbols found in file!")
        sys.exit(1)
        
    sym_block = symbols[0]
    existing_props = parse_existing_properties(sym_block)
    
    print("\nProvide Component Fields (Press Enter to keep existing / auto-detected):")
    mpn = input(f"  MPN [{existing_props.get('MPN', '')}]: ").strip() or existing_props.get('MPN', '')
    mfr = input(f"  Manufacturer [{existing_props.get('Manufacturer', '')}]: ").strip() or existing_props.get('Manufacturer', '')
    datasheet = input(f"  Datasheet URL [{existing_props.get('Datasheet', '')}]: ").strip() or existing_props.get('Datasheet', '')
    digikey = input(f"  DigiKey Part # [{existing_props.get('DigiKey', '')}]: ").strip() or existing_props.get('DigiKey', '')
    temp = input(f"  Temp Range [{existing_props.get('Temp_Range', '-40°C to 125°C')}]: ").strip() or existing_props.get('Temp_Range', '-40°C to 125°C')

    fp_name = None
    if fp_path:
        fp_name = copy_footprint_to_category(category, fp_path)
        fp_ref = f"rov_{category.lower()}:{fp_name}"
    else:
        fp_ref = existing_props.get('Footprint', '')
        
    field_updates = {
        "Category": category,
        "MPN": mpn,
        "Manufacturer": mfr,
        "Datasheet": datasheet,
        "DigiKey": digikey,
        "Temp_Range": temp,
        "Footprint": fp_ref
    }
    
    updated_sym = inject_or_update_properties(sym_block, field_updates)
    append_symbol_to_category(category, updated_sym)
    
    print("\n🔍 Running Linter Verification...")
    linter_script = BASE_DIR / "scripts" / "linter_validator.py"
    result = subprocess.run([sys.executable, str(linter_script)] + [str(p) for p in SYMBOLS_DIR.glob("*.kicad_sym")])
    
    if result.returncode == 0:
        print("\n🎉 Part imported successfully and verified compliant!")
        git_commit = input("Commit & Push to master now? (y/N): ").strip().lower()
        if git_commit == 'y':
            subprocess.run(["git", "add", "Symbols/", "Footprints/"], cwd=str(BASE_DIR))
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
    existing_props = parse_existing_properties(sym_block)
    
    category = args.category or "Mech"
    fp_ref = existing_props.get("Footprint", "")
    
    if args.footprint and os.path.exists(args.footprint):
        fp_name = copy_footprint_to_category(category, args.footprint)
        fp_ref = f"rov_{category.lower()}:{fp_name}"
        
    field_updates = {
        "Category": category,
        "MPN": args.mpn or existing_props.get("MPN", ""),
        "Manufacturer": args.mfr or existing_props.get("Manufacturer", ""),
        "Datasheet": args.datasheet or existing_props.get("Datasheet", ""),
        "DigiKey": args.digikey or existing_props.get("DigiKey", ""),
        "Temp_Range": args.temp or existing_props.get("Temp_Range", "-40°C to 125°C"),
        "Footprint": fp_ref
    }
    
    updated_sym = inject_or_update_properties(sym_block, field_updates)
    append_symbol_to_category(category, updated_sym)
    
    # Run linter
    linter_script = BASE_DIR / "scripts" / "linter_validator.py"
    subprocess.run([sys.executable, str(linter_script)] + [str(p) for p in SYMBOLS_DIR.glob("*.kicad_sym")])

if __name__ == "__main__":
    main()
