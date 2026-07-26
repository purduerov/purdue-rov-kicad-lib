import os
import re
import shutil
from pathlib import Path

# Setup paths
base_dir = Path(__file__).resolve().parent.parent
symbols_dir = base_dir / "Symbols"
footprints_dir = base_dir / "Footprints"

kicad_sym_file = symbols_dir / "rov_parts.kicad_sym"
rov_parts_pretty = footprints_dir / "rov_parts.pretty"

CATEGORIES = {
    'Passives': ['Resistor', 'Capacitor', 'Inductor', 'Ferrite', 'Crystal'],
    'Power': ['Buck', 'Boost', 'Regulator', 'PMIC', 'MOSFET', 'Fuse', 'Diode', 'LDO'],
    'Logic': ['MCU', 'STM32', 'ESP32', 'Logic', 'Gate', 'Level Shifter', 'OpAmp', 'Transceiver'],
    'Connectors': ['Connector', 'XT60', 'JST', 'Header', 'Terminal', 'USB', 'Jack', 'Plug'],
    'Sensors': ['Sensor', 'IMU', 'Pressure', 'Temp', 'Thermistor'],
    'Mech': ['Mounting Hole', 'Heatsink', 'Hardware', 'Standoff']
}

_LOWERCASE_CATEGORIES = {
    cat: [kw.lower() for kw in keywords]
    for cat, keywords in CATEGORIES.items()
}

def extract_symbols(kicad_sym_content):
    lines = kicad_sym_content.split('\n')
    header_lines = []
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
                header_lines.append(line)
        else:
            current_symbol_lines.append(line)
            paren_depth += line.count('(') - line.count(')')
            if paren_depth == 0:
                symbols.append('\n'.join(current_symbol_lines))
                in_symbol = False
                
    # Handle the final parenthesis
    footer = ')'
    if header_lines:
        for i in range(len(header_lines) - 1, -1, -1):
            if header_lines[i].strip() == ')':
                footer = header_lines.pop(i)
                break
                
    return '\n'.join(header_lines), symbols, footer

def determine_category(sym_content):
    text_lower = sym_content.lower()
    for cat, keywords in _LOWERCASE_CATEGORIES.items():
        for kw in keywords:
            if kw in text_lower:
                return cat
    return 'Mech'  # Default

def inject_category(sym_content, category):
    if '(property "Category"' in sym_content:
        return sym_content
        
    ids = [int(m) for m in re.findall(r'\(id\s+(\d+)\)', sym_content)]
    next_id = max(ids) + 1 if ids else 100
    
    lines = sym_content.split('\n')
    indent = "    "
    prop_lines = [
        f'{indent}(property "Category" "{category}" (id {next_id}) (at 0 0 0)',
        f'{indent}  (effects (font (size 1.27 1.27)) hide)',
        f'{indent})'
    ]
    
    for i, line in enumerate(lines):
        if re.search(r'^\s*\(property\s', line):
            return '\n'.join(lines[:i] + prop_lines + lines[i:])
            
    return '\n'.join(lines[:1] + prop_lines + lines[1:])

def main():
    if not kicad_sym_file.exists():
        print(f"File not found: {kicad_sym_file}")
        return
        
    with open(kicad_sym_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    header, symbols, footer = extract_symbols(content)
    
    categorized_symbols = {cat: [] for cat in CATEGORIES.keys()}
    
    for sym in symbols:
        cat = determine_category(sym)
        sym_injected = inject_category(sym, cat)
        categorized_symbols[cat].append(sym_injected)
        
    for cat, syms in categorized_symbols.items():
        cat_file = symbols_dir / f"rov_{cat.lower()}.kicad_sym"
        with open(cat_file, 'w', encoding='utf-8') as f:
            f.write(header)
            if not header.endswith('\n'):
                f.write('\n')
            if syms:
                f.write('\n'.join(syms) + '\n')
            f.write(footer + '\n')
            
        # Create footprint dir
        cat_pretty = footprints_dir / f"rov_{cat.lower()}.pretty"
        cat_pretty.mkdir(parents=True, exist_ok=True)
        
    # Move footprints
    if rov_parts_pretty.exists() and rov_parts_pretty.is_dir():
        for fp_file in rov_parts_pretty.glob('*.kicad_mod'):
            with open(fp_file, 'r', encoding='utf-8') as f:
                fp_content = f.read()
            cat = determine_category(fp_content)
            cat_pretty = footprints_dir / f"rov_{cat.lower()}.pretty"
            dest = cat_pretty / fp_file.name
            print(f"Moving {fp_file.name} to {cat_pretty.name}")
            shutil.move(str(fp_file), str(dest))

    print("Categorization complete.")

if __name__ == "__main__":
    main()
