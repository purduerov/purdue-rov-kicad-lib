#!/usr/bin/env python3
"""
Port components, footprints, and 3D STEP models from X19-USB-Hub-Board
into the Purdue ROV KiCad Central Library (purdue-rov-kicad-lib).
"""

import os
import re
import sys
import shutil
from pathlib import Path

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

from kicad_sym_utils import (
    extract_top_symbols,
    update_or_inject_properties,
    link_3d_model_to_footprint,
    validate_sexpr,
    validate_component_rules
)
from build_symbol_libs import build_all_categories

USB_HUB_DIR = BASE_DIR.parent / "X19-USB-Hub-Board"
USB_LIB_DIR = USB_HUB_DIR / "lib"
SYMBOLS_PARTS_DIR = BASE_DIR / "Symbols" / "parts"
FOOTPRINTS_DIR = BASE_DIR / "Footprints"
MODELS_DIR = BASE_DIR / "3D_Models"

# 1. 3D Models mapping: (src_file, dst_filename)
STEP_MODELS = [
    ("1053131102.stp", "1053131102.stp"),
    ("436500200.step", "436500200.step"),
    ("436500227.stp", "436500227.stp"),
    ("525591652.stp", "525591652.stp"),
    ("61400826021.step", "61400826021.step"),
    ("691311500102.stp", "691311500102.stp"),
    ("SFV16R-1STBE1HLF.step", "SFV16R-1STBE1HLF.step"),
    ("SFV16R-2STE1HLF.step", "SFV16R-2STE1HLF.step")
]

# 2. Footprints mapping: (src_mod, cat, dst_mod, linked_3d_model)
FOOTPRINTS = [
    ("0436500200.kicad_mod", "Connectors", "0436500200.kicad_mod", "436500200.step"),
    ("0436500227.kicad_mod", "Connectors", "0436500227.kicad_mod", "436500227.stp"),
    ("1053131102.kicad_mod", "Connectors", "1053131102.kicad_mod", "1053131102.stp"),
    ("525591652.kicad_mod", "Connectors", "525591652.kicad_mod", "525591652.stp"),
    ("AMPHENOL_SFV16R-1STBE1HLF.kicad_mod", "Connectors", "AMPHENOL_SFV16R-1STBE1HLF.kicad_mod", "SFV16R-1STBE1HLF.step"),
    ("AMPHENOL_SFV16R-2STE1HLF.kicad_mod", "Connectors", "AMPHENOL_SFV16R-2STE1HLF.kicad_mod", "SFV16R-2STE1HLF.step"),
    ("QFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm_ThermalVias.kicad_mod", "Logic", "QFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm_ThermalVias.kicad_mod", None),
    ("QFN-68-1EP_8x8mm_P0.4mm_EP6.2x6.2mm.kicad_mod", "Logic", "QFN-68-1EP_8x8mm_P0.4mm_EP6.2x6.2mm.kicad_mod", None)
]

# 3. Component Symbol Definitions
SYMBOLS = [
    {
        "source_name": "525591652",
        "target_name": "525591652",
        "category": "Connectors",
        "properties": {
            "Reference": "J",
            "Value": "52559-1652",
            "Footprint": "rov_connectors:525591652",
            "Datasheet": "https://www.molex.com/pdm_docs/sd/525591652_sd.pdf",
            "Description": "Easy-On FFC/FPC Connector, 0.50mm Pitch, Vertical, 16 Circuits",
            "Manufacturer": "Molex",
            "MPN": "52559-1652",
            "DigiKey": "WM14878CT-ND",
            "Temp_Range": "-40°C to 85°C",
            "Category": "Connectors",
            "Verified": "Yes"
        }
    },
    {
        "source_name": "SFV16R-1STBE1HLF",
        "target_name": "SFV16R-1STBE1HLF",
        "category": "Connectors",
        "properties": {
            "Reference": "J",
            "Value": "SFV16R-1STBE1HLF",
            "Footprint": "rov_connectors:AMPHENOL_SFV16R-1STBE1HLF",
            "Datasheet": "https://www.amphenol-cs.com/media/wysiwyg/files/drawing/sfv_r.pdf",
            "Description": "FFC/FPC Connector, 0.50mm Pitch, Right-Angle, 16 Circuits, Top Contact",
            "Manufacturer": "Amphenol ICC (FCI)",
            "MPN": "SFV16R-1STBE1HLF",
            "DigiKey": "609-1786-1-ND",
            "Temp_Range": "-55°C to 105°C",
            "Category": "Connectors",
            "Verified": "Yes"
        }
    },
    {
        "source_name": "SFV16R-2STE1HLF",
        "target_name": "SFV16R-2STE1HLF",
        "category": "Connectors",
        "properties": {
            "Reference": "J",
            "Value": "SFV16R-2STE1HLF",
            "Footprint": "rov_connectors:AMPHENOL_SFV16R-2STE1HLF",
            "Datasheet": "https://www.amphenol-cs.com/media/wysiwyg/files/drawing/sfv_r.pdf",
            "Description": "FFC/FPC Connector, 0.50mm Pitch, Right-Angle, 16 Circuits, Bottom Contact",
            "Manufacturer": "Amphenol ICC (FCI)",
            "MPN": "SFV16R-2STE1HLF",
            "DigiKey": "609-1787-1-ND",
            "Temp_Range": "-55°C to 105°C",
            "Category": "Connectors",
            "Verified": "Yes"
        }
    },
    {
        "source_name": "UPD720201K8-7x1-BAC-A",
        "target_name": "UPD720201K8-7x1-BAC-A",
        "category": "Logic",
        "properties": {
            "Reference": "U",
            "Value": "UPD720201K8-711-BAC-A",
            "Footprint": "rov_logic:QFN-68-1EP_8x8mm_P0.4mm_EP6.2x6.2mm",
            "Datasheet": "https://www.renesas.com/en/document/dst/upd720201-upd720202-datasheet.pdf",
            "Description": "USB 3.0 Host Controller, 4 Ports, PCIe to USB 3.0, 68-QFN",
            "Manufacturer": "Renesas Electronics Corporation",
            "MPN": "UPD720201K8-711-BAC-A",
            "DigiKey": "UPD720201K8-711-BAC-ACT-ND",
            "Temp_Range": "0°C to 85°C",
            "Category": "Logic",
            "Verified": "Yes"
        }
    },
    {
        "source_name": "USB2422_MJ",
        "target_name": "USB2422_MJ",
        "category": "Logic",
        "properties": {
            "Reference": "U",
            "Value": "USB2422/MJ",
            "Footprint": "rov_logic:QFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm_ThermalVias",
            "Datasheet": "https://ww1.microchip.com/downloads/en/DeviceDoc/00000062A.pdf",
            "Description": "2-Port USB 2.0 Hi-Speed Hub Controller, 24-QFN",
            "Manufacturer": "Microchip Technology",
            "MPN": "USB2422/MJ",
            "DigiKey": "USB2422/MJ-ND",
            "Temp_Range": "0°C to 70°C",
            "Category": "Logic",
            "Verified": "Yes"
        }
    },
    {
        "source_name": "MX25V5126FZUI",
        "target_name": "MX25V5126FZUI",
        "category": "Logic",
        "properties": {
            "Reference": "U",
            "Value": "MX25V5126FZUI",
            "Footprint": "Package_SON:Winbond_USON-8-1EP_3x2mm_P0.5mm_EP0.2x1.6mm",
            "Datasheet": "https://www.macronix.com/Lists/Datasheet/Attachments/7434/MX25V5126F,%202.5V-3.6V,%20512Kb,%20v1.1.pdf",
            "Description": "512Kb (64K x 8) Serial NOR Flash Memory, SPI, 8-USON",
            "Manufacturer": "Macronix",
            "MPN": "MX25V5126FZUI",
            "DigiKey": "1092-1065-1-ND",
            "Temp_Range": "-40°C to 85°C",
            "Category": "Logic",
            "Verified": "Yes"
        }
    },
    {
        "source_name": "SST25VF512A-33-4C-SAE",
        "target_name": "SST25VF512A-33-4C-SAE",
        "category": "Logic",
        "properties": {
            "Reference": "U",
            "Value": "SST25VF512A-33-4C-SAE",
            "Footprint": "rov_logic:D0008A-IPC_A",
            "Datasheet": "https://ww1.microchip.com/downloads/en/DeviceDoc/20005039B.pdf",
            "Description": "512Kb SPI Serial Flash Memory, 33MHz, 8-SOIC",
            "Manufacturer": "Microchip Technology",
            "MPN": "SST25VF512A-33-4C-SAE",
            "DigiKey": "SST25VF512A-33-4C-SAE-ND",
            "Temp_Range": "0°C to 70°C",
            "Category": "Logic",
            "Verified": "Yes"
        }
    }
]


def port_usb_hub_components():
    print("[INFO] Porting USB Hub Board components into purdue-rov-kicad-lib...\n")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: Copy 3D models
    print("[INFO] Step 1: Copying 3D STEP models...")
    for src_name, dst_name in STEP_MODELS:
        src_path = USB_LIB_DIR / "ROV_PCIe_USB_HUB.3d" / src_name
        if src_path.is_file():
            dst_path = MODELS_DIR / dst_name
            shutil.copy2(src_path, dst_path)
            print(f"  - Copied 3D model: {dst_name}")
        else:
            print(f"  [WARN] 3D model not found at {src_path}")

    # Step 2: Copy Footprints and link 3D models
    print("\n[INFO] Step 2: Copying and standardizing footprints...")
    for src_mod, cat, dst_mod, linked_step in FOOTPRINTS:
        src_path = USB_LIB_DIR / "ROV_PCIe_USB_HUB.pretty" / src_mod
        cat_pretty = FOOTPRINTS_DIR / f"rov_{cat.lower()}.pretty"
        cat_pretty.mkdir(parents=True, exist_ok=True)
        dst_path = cat_pretty / dst_mod
        if src_path.is_file():
            shutil.copy2(src_path, dst_path)
            if linked_step:
                link_3d_model_to_footprint(dst_path, linked_step)
                print(f"  - Footprint: {dst_mod} -> linked 3D model '{linked_step}'")
            else:
                print(f"  - Footprint: {dst_mod}")
        else:
            print(f"  [WARN] Footprint not found at {src_path}")

    # Step 3: Extract and standardize symbols
    print("\n[INFO] Step 3: Standardizing symbols...")
    sym_file = USB_LIB_DIR / "ROV_PCIe_USB_HUB.kicad_sym"
    if not sym_file.is_file():
        print(f"[ERROR] Symbol file not found at {sym_file}")
        return False

    raw_lib = sym_file.read_text(encoding="utf-8", errors="ignore")
    extracted_symbols = {name: raw for name, raw, _, _ in extract_top_symbols(raw_lib)}

    for sdef in SYMBOLS:
        src_name = sdef["source_name"]
        tgt_name = sdef["target_name"]
        cat = sdef["category"]
        if src_name not in extracted_symbols:
            print(f"  [ERROR] Symbol '{src_name}' not found in source library")
            continue

        raw_sym = extracted_symbols[src_name]
        updated_sym = update_or_inject_properties(raw_sym, sdef["properties"])
        wrapped = (
            '(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor)\n'
            f'  {updated_sym.strip()}\n'
            ')\n'
        )

        sexpr_ok, sexpr_err = validate_sexpr(wrapped)
        if not sexpr_ok:
            print(f"  [ERROR] Invalid S-expression error for {tgt_name}: {sexpr_err}")
            continue

        errs, warns = validate_component_rules(sdef["properties"])
        if errs:
            print(f"  [FAIL] Rule validation failed for {tgt_name}: {errs}")
            continue

        cat_folder = SYMBOLS_PARTS_DIR / cat.lower()
        cat_folder.mkdir(parents=True, exist_ok=True)
        dest_file = cat_folder / f"{tgt_name}.kicad_sym"
        dest_file.write_text(wrapped, encoding="utf-8")
        print(f"  - Symbol: [{cat}] {tgt_name} -> {dest_file.name}")

    # Step 4: Recompile central category libraries
    print("\n[INFO] Step 4: Compiling monolithic category libraries...")
    summary = build_all_categories()
    for c, cnt in summary.items():
        print(f"  - rov_{c.lower()}: {cnt} part(s)")

    print("\n[OK] Porting complete!")
    return True


if __name__ == "__main__":
    if not port_usb_hub_components():
        sys.exit(1)
