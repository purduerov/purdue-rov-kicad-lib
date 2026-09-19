"""
Purdue ROV KiCad Library - Robust S-Expression and Metadata Utilities
Provides bulletproof S-expression parsing, property injection, format validation,
and smart metadata autofill across various component vendor formats.
"""

import re
import os
import json
import urllib.parse
from pathlib import Path

CATEGORIES = ["Passives", "Power", "Logic", "Connectors", "Sensors", "Mech"]

CATEGORY_KEYWORDS = {
    'Power': [
        'buck', 'boost', 'regulator', 'pmic', 'ldo', 'vreg', 'converter',
        'power', 'supply', 'charger', 'battery', 'bms', 'dcdc', 'dc-dc',
        'switchmode', 'vout', 'vin', 'mosfet', 'fet', 'diode', 'zener',
        'fuse', 'varistor', 'rectifier', 'inverter', 'tps', 'linear',
        'current limiter', 'gate driver', 'flyback'
    ],
    'Passives': [
        'resistor', 'capacitor', 'inductor', 'ferrite', 'bead', 'crystal',
        'oscillator', 'resonator', 'potentiometer', 'trimmer', 'varistor',
        'choke', 'filter', 'attenuator'
    ],
    'Logic': [
        'mcu', 'microcontroller', 'stm32', 'esp32', 'cortex', 'processor',
        'fpga', 'cpld', 'logic', 'gate', 'flip-flop', 'latch', 'buffer',
        'transceiver', 'uart', 'can', 'spi', 'i2c', 'rs485', 'rs232',
        'level shifter', 'opamp', 'amplifier', 'adc', 'dac', 'comparator',
        'multiplexer', 'demultiplexer', 'optocoupler', 'isolator'
    ],
    'Connectors': [
        'connector', 'header', 'terminal', 'receptacle', 'plug', 'jack',
        'socket', 'usb', 'type-c', 'jst', 'xt60', 'xt30', 'molex', 'sma',
        'ethernet', 'rj45', 'fpc', 'ffc', 'ribbon', 'pinheader', 'conn'
    ],
    'Sensors': [
        'sensor', 'imu', 'accelerometer', 'gyro', 'gyroscope', 'magnetometer',
        'barometer', 'pressure', 'humidity', 'thermistor', 'temperature sensor',
        'hall', 'current sensor', 'ultrasonic', 'lidar', 'encoder', 'tof'
    ],
    'Mech': [
        'heatsink', 'standoff', 'screw', 'nut', 'washer', 'mounting hole',
        'spacer', 'enclosure', 'bracket', 'hardware', 'test point',
        'fiducial', 'jumper'
    ]
}

def escape_sexpr_string(s):
    """
    Escapes double quotes, backslashes, and newlines for KiCad S-expression string literals.
    """
    if s is None:
        return ""
    s = str(s)
    s = s.replace('\\', '\\\\').replace('"', '\\"')
    s = s.replace('\r\n', '\\n').replace('\n', '\\n').replace('\r', '\\n')
    return s


def unescape_sexpr_string(s):
    """
    Unescapes KiCad S-expression string literals.
    """
    if s is None:
        return ""
    def _repl(match):
        c = match.group(1)
        if c == 'n':
            return '\n'
        elif c == 'r':
            return '\r'
        elif c == 't':
            return '\t'
        elif c == '"':
            return '"'
        elif c == '\\':
            return '\\'
        return c
    return re.sub(r'\\(.)', _repl, s)


def validate_sexpr(text):
    """
    Validates that parentheses in an S-expression text are balanced outside of quoted strings.
    Returns (is_valid: bool, error_message: str).
    """
    depth = 0
    in_string = False
    escape = False
    line_num = 1

    for idx, ch in enumerate(text):
        if ch == '\n':
            line_num += 1

        if escape:
            escape = False
            continue

        if ch == '\\' and in_string:
            escape = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if not in_string:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth < 0:
                    return False, f"Unexpected closing parenthesis ')' at line {line_num}"

    if in_string:
        return False, "Unterminated quoted string in S-expression"
    if depth != 0:
        return False, f"Unbalanced parentheses: {depth} unclosed opening '(' at EOF"

    return True, ""


def extract_top_symbols(content):
    """
    Extracts all top-level (symbol "Name" ...) blocks from a .kicad_sym file or raw snippet.
    Returns a list of tuples: (symbol_name, raw_symbol_text, start_char, end_char).
    Accurately preserves all nested sub-symbols (e.g. units _0_1, _1_1), graphics, and pins.
    """
    symbols = []
    length = len(content)
    idx = 0
    in_string = False
    escape = False
    depth = 0
    
    # Check if root is (kicad_symbol_lib ...)
    has_lib_wrapper = bool(re.search(r'^\s*\(kicad_symbol_lib', content))
    target_start_depth = 1 if has_lib_wrapper else 0

    current_sym_name = None
    current_sym_start = -1

    while idx < length:
        ch = content[idx]

        if escape:
            escape = False
            idx += 1
            continue

        if ch == '\\' and in_string:
            escape = True
            idx += 1
            continue

        if ch == '"':
            in_string = not in_string
            idx += 1
            continue

        if not in_string:
            if ch == '(':
                if depth == target_start_depth:
                    # Check if this starts a symbol: (symbol "NAME"
                    rest = content[idx:min(idx+120, length)]
                    m = re.match(r'^\(\s*symbol\s+"([^"]+)"', rest)
                    if m:
                        name = m.group(1)
                        # Top level symbol only (not units like Name_0_1 or Name_1_1)
                        if not re.search(r'_\d+_\d+$', name):
                            current_sym_name = name
                            current_sym_start = idx
                depth += 1
            elif ch == ')':
                depth -= 1
                if current_sym_start != -1 and depth == target_start_depth:
                    # Completed top-level symbol block
                    sym_raw = content[current_sym_start:idx+1]
                    symbols.append((current_sym_name, sym_raw, current_sym_start, idx+1))
                    current_sym_name = None
                    current_sym_start = -1

        idx += 1

    return symbols


def parse_symbol_properties(sym_text):
    """
    Parses all (property "Key" "Value" ...) definitions in a symbol block.
    Returns a dict of {key: value} and a dict of detailed metadata {key: {'val': val, 'id': id, 'raw': raw, 'start': s, 'end': e}}.
    Accurately handles escaped characters, quotes, and arbitrarily long strings.
    """
    props = {}
    details = {}
    length = len(sym_text)
    idx = 0
    in_string = False
    escape = False
    depth = 0

    prop_start = -1

    while idx < length:
        ch = sym_text[idx]

        if escape:
            escape = False
            idx += 1
            continue

        if ch == '\\' and in_string:
            escape = True
            idx += 1
            continue

        if ch == '"':
            in_string = not in_string
            idx += 1
            continue

        if not in_string:
            if ch == '(':
                # Properties are directly inside the top-level symbol (depth 1)
                if depth == 1:
                    if re.match(r'^\(\s*property\b', sym_text[idx:min(idx+30, length)]):
                        prop_start = idx
                depth += 1
            elif ch == ')':
                depth -= 1
                if prop_start != -1 and depth == 1:
                    raw_prop = sym_text[prop_start:idx+1]
                    m = re.match(r'^\(\s*property\s+"((?:[^"\\]|\\.)+)"\s+"((?:[^"\\]|\\.)*)"', raw_prop)
                    if m:
                        prop_key = unescape_sexpr_string(m.group(1))
                        prop_val = unescape_sexpr_string(m.group(2))
                        id_m = re.search(r'\(id\s+(\d+)\)', raw_prop)
                        prop_id = int(id_m.group(1)) if id_m else None
                        props[prop_key] = prop_val
                        details[prop_key] = {
                            'val': prop_val,
                            'id': prop_id,
                            'raw': raw_prop,
                            'start': prop_start,
                            'end': idx + 1
                        }
                    prop_start = -1

        idx += 1

    return props, details


def update_or_inject_properties(sym_text, field_updates, next_id_start=10):
    """
    Safely updates existing properties or injects new ones into a symbol S-expression.
    Guarantees that nested parentheses in effects/font/at are NEVER corrupted and
    special characters (quotes, backslashes) are escaped properly.
    """
    existing_props, details = parse_symbol_properties(sym_text)
    
    # Calculate next property id
    existing_ids = [d['id'] for d in details.values() if d['id'] is not None]
    next_id = max(existing_ids) + 1 if existing_ids else next_id_start

    updated_sym = sym_text

    # First pass: update existing properties in-place
    for field, val in field_updates.items():
        if val is None:
            continue
        val_str = str(val)
        escaped_val = escape_sexpr_string(val_str)
        if field in details:
            d = details[field]
            old_raw = d['raw']
            # Safely replace only the value part: (property "KEY" "OLD_VAL" -> (property "KEY" "NEW_VAL"
            escaped_field = re.escape(escape_sexpr_string(field))
            pattern = re.compile(rf'(\(\s*property\s+"{escaped_field}"\s+")[^"\\]*(?:\\.[^"\\]*)*(")')
            new_raw = pattern.sub(lambda m: f"{m.group(1)}{escaped_val}{m.group(2)}", old_raw)
            if new_raw != old_raw:
                updated_sym = updated_sym.replace(old_raw, new_raw, 1)

    # Re-parse details after in-place updates to get accurate positions for insertions
    existing_props, details = parse_symbol_properties(updated_sym)
    existing_ids = [d['id'] for d in details.values() if d['id'] is not None]
    if existing_ids:
        next_id = max(next_id, max(existing_ids) + 1)

    # Second pass: inject new properties that do not exist yet
    props_to_add = []
    for field, val in field_updates.items():
        if val is None or not str(val).strip():
            continue
        if field not in existing_props:
            props_to_add.append((field, str(val).strip()))

    if props_to_add:
        # Determine clean insertion point: right after the last existing property
        insert_idx = -1
        if details:
            # Find maximum 'end' among existing properties
            last_prop_end = max(d['end'] for d in details.values())
            insert_idx = last_prop_end
        else:
            # Insert after the first line (symbol opening line)
            first_line_end = updated_sym.find('\n')
            if first_line_end != -1:
                insert_idx = first_line_end
            else:
                insert_idx = len(updated_sym) - 1

        new_props_text = ""
        for field, val in props_to_add:
            indent = "    "
            esc_field = escape_sexpr_string(field)
            esc_val = escape_sexpr_string(val)
            new_props_text += f'\n{indent}(property "{esc_field}" "{esc_val}" (id {next_id}) (at 0 0 0)\n{indent}  (effects (font (size 1.27 1.27)) hide)\n{indent})'
            next_id += 1

        updated_sym = updated_sym[:insert_idx] + new_props_text + updated_sym[insert_idx:]

    # Validate syntax before returning
    is_valid, err = validate_sexpr(updated_sym)
    if not is_valid:
        raise ValueError(f"S-Expression syntax error after property update: {err}")

    return updated_sym


def predict_category(sym_name, props, footprint="", description=""):
    """
    Intelligently predicts the component category based on properties, reference designator,
    MPN, description, and keywords.
    """
    # 1. Check if Category property is already explicitly set and valid
    cat_prop = props.get("Category", "").strip()
    if cat_prop in CATEGORIES:
        return cat_prop, "Explicitly defined in symbol properties"

    # 2. Check Reference Designator prefix
    ref = props.get("Reference", "").strip().upper()
    if ref in ["R", "C", "L", "FB", "Y"]:
        return "Passives", f"Standard passive reference designator '{ref}'"
    if ref in ["J", "P", "CONN", "HDR"]:
        return "Connectors", f"Standard connector reference designator '{ref}'"
    if ref in ["H", "MH", "MP", "HS"]:
        return "Mech", f"Standard mechanical reference designator '{ref}'"

    # 3. Keyword Scoring across all metadata text
    combined_text = f"{sym_name} {description} {props.get('Value', '')} {props.get('MPN', '')} {props.get('ki_description', '')} {props.get('ki_keywords', '')} {footprint}".lower()

    scores = {cat: 0 for cat in CATEGORIES}
    matched_words = {cat: [] for cat in CATEGORIES}

    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            # Word boundary or standalone match
            if re.search(rf'\b{re.escape(kw)}\b', combined_text):
                scores[cat] += 3
                matched_words[cat].append(kw)
            elif kw in combined_text:
                scores[cat] += 1
                matched_words[cat].append(kw)

    best_cat = max(scores, key=scores.get)
    if scores[best_cat] > 0:
        return best_cat, f"Matched keywords: {', '.join(matched_words[best_cat][:3])}"

    return "Power", "Default fallback category"


def autofill_component_data(sym_text, sym_name=None, fp_name=None, zip_files=None):
    """
    Extracts and standardizes all available metadata from a symbol and related files,
    resolving vendor field aliases and inferring missing values.
    Returns: dict with standardized fields, predicted category, and list of autofilled fields.
    """
    props, _ = parse_symbol_properties(sym_text)
    autofilled = []

    # If sym_name is not provided, extract from symbol declaration
    if not sym_name:
        m = re.search(r'^\s*\(\s*symbol\s+"([^"]+)"', sym_text)
        if m:
            sym_name = m.group(1)
        else:
            sym_name = props.get("Value", "New_Component")

    # 1. MPN Detection
    mpn = None
    mpn_aliases = [
        "MPN", "mpn", "Mfr_PN", "MFR_PN", "MFR PART #", "Mfr Part #",
        "Part Number", "PartNumber", "Manufacturer Part Number",
        "MANUFACTURER_PART_NUMBER", "SnapEDA_PN", "Package_Part_Number"
    ]
    for alias in mpn_aliases:
        if props.get(alias) and props[alias].strip():
            mpn = props[alias].strip()
            autofilled.append("MPN")
            break

    if not mpn:
        val = props.get("Value", "").strip()
        # If Value is meaningful (not a generic resistor 'R', '10k', 'C', 'U', etc.)
        if val and val not in ["R", "C", "L", "U", "D", "J", "Q", "Device"] and not re.match(r'^\d+(\.\d+)?[kKMmupn]?$', val):
            mpn = val
            autofilled.append("MPN (from Value)")
        elif sym_name and not sym_name.startswith("~"):
            mpn = sym_name
            autofilled.append("MPN (from Symbol Name)")
        else:
            mpn = ""

    # 2. Manufacturer Detection
    mfr = None
    mfr_aliases = [
        "Manufacturer", "MANUFACTURER", "MF", "MFR", "Mfr", "Mfr_Name",
        "Manufacturer_Name", "MANUFACTURER_NAME", "Vendor", "SnapEDA_Manufacturer"
    ]
    for alias in mfr_aliases:
        if props.get(alias) and props[alias].strip():
            mfr = props[alias].strip()
            autofilled.append("Manufacturer")
            break
    if not mfr:
        mfr = ""

    # 3. Datasheet Detection
    datasheet = None
    ds_aliases = [
        "Datasheet", "datasheet", "Data Sheet", "DataSheet", "Datasheet_URL",
        "Datasheet URL", "Documentation", "URL", "Doc_URL", "SnapEDA_Datasheet"
    ]
    for alias in ds_aliases:
        v = props.get(alias, "").strip()
        if v and (v.startswith("http://") or v.startswith("https://")):
            datasheet = v
            autofilled.append("Datasheet")
            break

    if not datasheet:
        # Scan all property values for PDF URLs
        for k, v in props.items():
            if (v.startswith("http://") or v.startswith("https://")) and v.lower().endswith(".pdf"):
                datasheet = v.strip()
                autofilled.append(f"Datasheet (from {k})")
                break
    if not datasheet:
        datasheet = ""

    # 4. DigiKey SKU Detection
    digikey = None
    dk_aliases = [
        "DigiKey", "Digi-Key", "DigiKey_SKU", "Digi-Key_SKU",
        "DigiKey_Part_Number", "Digi-Key_Part_Number", "Digi-Key Part Number",
        "DigiKey Part Number", "Digi-Key_PN", "DigiKey_PN", "DK_Part_Number"
    ]
    for alias in dk_aliases:
        if props.get(alias) and props[alias].strip():
            digikey = props[alias].strip()
            autofilled.append("DigiKey")
            break

    if not digikey:
        # Scan for standard DigiKey suffix pattern (e.g. -ND, -1-ND, DICT-ND, TR-ND)
        for k, v in props.items():
            v_clean = v.strip()
            if re.search(r'[\w\-]+-(?:ND|DICT-ND|DKR-ND|TR-ND|1-ND)$', v_clean, re.IGNORECASE):
                digikey = v_clean
                autofilled.append(f"DigiKey (detected from {k})")
                break
    if not digikey:
        digikey = ""

    # 5. Temperature Range Detection
    temp_range = None
    temp_aliases = [
        "Temp_Range", "Operating Temperature", "Operating_Temperature",
        "Temperature Range", "Temp Range", "Temperature_Range", "Temp"
    ]
    for alias in temp_aliases:
        if props.get(alias) and props[alias].strip():
            temp_range = props[alias].strip()
            autofilled.append("Temp_Range")
            break
    if not temp_range:
        # Look for temperature pattern in any property value (e.g. -40°C to 125°C or -40~85 C)
        for k, v in props.items():
            if re.search(r'-?\d+\s*°?C\s*(?:to|~|-)\s*\+?\d+\s*°?C', v, re.IGNORECASE):
                temp_range = v.strip()
                autofilled.append("Temp_Range (pattern)")
                break
    if not temp_range:
        temp_range = "-40°C to 125°C"

    # 6. Description Detection
    description = None
    desc_aliases = ["Description", "ki_description", "ki_keywords", "Description_1", "Item_Description", "Comment"]
    for alias in desc_aliases:
        if props.get(alias) and props[alias].strip():
            description = props[alias].strip()
            autofilled.append("Description")
            break
    if not description:
        description = props.get("Value", "")

    # 7. Footprint Detection
    footprint = props.get("Footprint", "").strip()
    if fp_name:
        footprint = fp_name
        autofilled.append("Footprint (from file)")
    elif footprint:
        autofilled.append("Footprint")

    # 8. Category Prediction
    predicted_cat, cat_reason = predict_category(sym_name, props, footprint, description)
    autofilled.append(f"Category -> {predicted_cat}")

    # Standardize footprint format to rov_<category>:<footprint_name> if category is decided
    if footprint and not footprint.startswith("rov_") and ":" not in footprint:
        footprint = f"rov_{predicted_cat.lower()}:{footprint}"

    return {
        "sym_name": sym_name,
        "MPN": mpn,
        "Manufacturer": mfr,
        "Datasheet": datasheet,
        "DigiKey": digikey,
        "Temp_Range": temp_range,
        "Description": description,
        "Footprint": footprint,
        "Category": predicted_cat,
        "Category_Reason": cat_reason,
        "Autofilled_Fields": autofilled,
        "Value": props.get("Value", sym_name),
        "Reference": props.get("Reference", "U")
    }


def format_library_header():
    """Returns standard clean KiCad symbol library header without illegal comments."""
    return '(kicad_symbol_lib\n  (version 20211014)\n  (generator "kicad_symbol_editor")\n'


def clean_symbol_lib_file(filepath):
    """
    Cleans a .kicad_sym file, removing illegal line comments (#) and formatting properly.
    """
    if not os.path.exists(filepath):
        return False, "File does not exist"
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Remove illegal # comments
    lines = content.split('\n')
    cleaned_lines = [l for l in lines if not re.match(r'^\s*#', l)]
    cleaned_content = '\n'.join(cleaned_lines).strip()

    # Validate syntax
    is_valid, err = validate_sexpr(cleaned_content)
    if is_valid:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(cleaned_content + '\n')
    return is_valid, err


def get_standard_passive_symbol(passive_type, symbol_name, properties):
    """
    Generates a clean KiCad symbol S-expression using official standard KiCad Device templates
    (Resistor 'R', Capacitor 'C', Polarized Capacitor 'C_Polarized', Inductor 'L', Ferrite 'L_Ferrite'),
    renamed to symbol_name with customized properties and footprint.
    """
    json_path = Path(__file__).resolve().parent / "standard_passives.json"
    if not json_path.exists():
        raise FileNotFoundError(f"Standard passives definitions not found at {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        templates = json.load(f)

    # Resolve template key
    type_key = passive_type.strip()
    if type_key not in templates:
        # Fallback guesses
        if type_key.upper().startswith("R"):
            type_key = "R"
        elif type_key.upper().startswith("CP") or "POL" in type_key.upper():
            type_key = "C_Polarized"
        elif type_key.upper().startswith("C"):
            type_key = "C"
        elif type_key.upper().startswith("FB") or "FERRITE" in type_key.upper():
            type_key = "L_Ferrite"
        elif type_key.upper().startswith("L"):
            type_key = "L"
        else:
            type_key = "R"

    base_sym = templates[type_key]

    # Rename symbol header: (symbol "KEY" ... -> (symbol "symbol_name" ...
    renamed = re.sub(r'^\(\s*symbol\s+"[^"]+"', f'(symbol "{symbol_name}"', base_sym.strip())
    # Rename sub-units: (symbol "KEY_0_1" ... -> (symbol "symbol_name_0_1" ...
    renamed = re.sub(r'\(\s*symbol\s+"[^"]+_([0-9]+_[0-9]+)"', rf'(symbol "{symbol_name}_\1"', renamed)

    # Ensure required properties are injected
    props_to_apply = dict(properties)
    props_to_apply["Value"] = properties.get("MPN", symbol_name)
    props_to_apply["Category"] = "Passives"

    return update_or_inject_properties(renamed, props_to_apply)


def rename_symbol(sym_text, new_name):
    """
    Renames a symbol and all its sub-units (e.g. NAME_0_1, NAME_1_1) to new_name.
    Also updates the 'Value' property to match new_name if it was previously set to the old name.
    """
    if not sym_text or not new_name:
        return sym_text
    old_name = None
    for m in re.finditer(r'\(\s*symbol\s+"([^"]+)"', sym_text):
        name = m.group(1)
        if not re.search(r'_\d+_\d+$', name):
            old_name = name
            break
    if not old_name or old_name == new_name:
        return sym_text

    escaped_old = re.escape(old_name)
    # 1. Replace top-level symbol name
    renamed = re.sub(rf'(\(\s*symbol\s+)"{escaped_old}"', rf'\1"{new_name}"', sym_text, count=1)
    # 2. Replace sub-unit names
    renamed = re.sub(rf'(\(\s*symbol\s+)"{escaped_old}_([0-9]+_[0-9]+)"', rf'\1"{new_name}_\2"', renamed)
    # 3. Update Value property to match new_name if Value matched old_name
    props, _ = parse_symbol_properties(renamed)
    if props.get("Value") == old_name:
        renamed = update_or_inject_properties(renamed, {"Value": new_name})

    return renamed


def link_3d_model_to_footprint(fp_filepath, model_filename):
    """
    Ensures a .kicad_mod footprint references its 3D model (.step/.stp)
    using the standard relative path '${KIPRJMOD}/libs/purdue-rov-kicad-lib/3D_Models/<model_filename>'.
    If the footprint already has a (model ...) statement, updates its path.
    Also resets scale to (xyz 1 1 1) when replacing with a .step/.stp model to prevent VRML scale distortion.
    Otherwise, injects the model statement right before the closing parenthesis.
    """
    fp_path = Path(fp_filepath)
    if not fp_path.exists():
        return False

    with open(fp_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read().rstrip()

    model_rel_path = f"${{KIPRJMOD}}/libs/purdue-rov-kicad-lib/3D_Models/{model_filename}"

    # Check if a model statement already exists
    if "(model " in content:
        # Update existing model path
        updated_content = re.sub(
            r'\(model\s+"[^"]*"',
            f'(model "{model_rel_path}"',
            content,
            count=1
        )
        if model_filename.lower().endswith(('.step', '.stp')):
            # Reset scale to 1 1 1 for STEP models to prevent VRML scale distortion (e.g. 0.3937)
            m_block = re.search(r'\(model\s+"[^"]*".*?\n\s*\)', updated_content, re.DOTALL)
            if m_block:
                old_block = m_block.group(0)
                new_block = re.sub(r'\(scale\s+\(xyz\s+[^)]+\)\)', '(scale (xyz 1 1 1))', old_block)
                updated_content = updated_content.replace(old_block, new_block, 1)
    else:
        # Insert model clause before the last closing paren
        model_block = (
            f'\n  (model "{model_rel_path}"\n'
            f'    (offset (xyz 0 0 0))\n'
            f'    (scale (xyz 1 1 1))\n'
            f'    (rotate (xyz 0 0 0))\n'
            f'  )\n'
        )
        last_paren = content.rfind(')')
        if last_paren != -1:
            updated_content = content[:last_paren].rstrip() + model_block + ")\n"
        else:
            updated_content = content + model_block

    with open(fp_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    return True

