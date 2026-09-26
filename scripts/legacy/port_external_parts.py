#!/usr/bin/env python3
"""
Port and standardize external components from board repos (Pi Shield & Power Slab)
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
    parse_symbol_properties,
    update_or_inject_properties,
    autofill_component_data,
    validate_component_rules,
    link_3d_model_to_footprint,
    validate_sexpr
)
from build_symbol_libs import build_all_categories

ROOT_DIR = BASE_DIR.parent
PI_SHIELD_DIR = ROOT_DIR / "X19-Pi-Shield-Board"
POWER_SLAB_DIR = ROOT_DIR / "X19-Power-Slab-Board"
SYMBOLS_PARTS_DIR = BASE_DIR / "Symbols" / "parts"
FOOTPRINTS_DIR = BASE_DIR / "Footprints"
MODELS_DIR = BASE_DIR / "3D_Models"

# Component definitions and metadata overrides to ensure 100% compliance
PARTS_TO_PORT = [
    {
        "name": "ECS-400-18-33-JGN-TR",
        "category": "Passives",
        "sym_source": PI_SHIELD_DIR / "libraries" / "ECS_400_18_33_JGN_TR" / "ECS-400-18-33-JGN-TR.kicad_sym",
        "fp_source": PI_SHIELD_DIR / "libraries" / "ECS_400_18_33_JGN_TR" / "XTAL_ECS-400-18-33-JGN-TR.kicad_mod",
        "fp_name": "XTAL_ECS-400-18-33-JGN-TR",
        "step_source": PI_SHIELD_DIR / "libraries" / "ECS_400_18_33_JGN_TR" / "ECS-400-18-33-JGN-TR.step",
        "step_name": "ECS-400-18-33-JGN-TR.step",
        "properties": {
            "Reference": "Y",
            "Value": "40MHz",
            "Footprint": "rov_passives:XTAL_ECS-400-18-33-JGN-TR",
            "Datasheet": "https://www.ecsxtal.com/store/pdf/ecx-33.pdf",
            "Description": "40 MHz SMD Crystal 18pF 3.2x2.5mm",
            "Manufacturer": "ECS Inc.",
            "MPN": "ECS-400-18-33-JGN-TR",
            "DigiKey": "XC1806TR-ND",
            "Temp_Range": "-40°C to 85°C",
            "Category": "Passives",
            "Verified": "Yes"
        }
    },
    {
        "name": "MCP2518FDT-E_QBB",
        "category": "Logic",
        "sym_source": PI_SHIELD_DIR / "libraries" / "2026-09-19_01-29-46.kicad_sym",
        "fp_source": None,
        "fp_name": None,
        "step_source": None,
        "step_name": None,
        "properties": {
            "Reference": "U",
            "Value": "MCP2518FDT-E/QBB",
            "Footprint": "Package_DFN_QFN:Microchip_VDFN-14-1EP_4.5x3mm_P0.65mm_EP2.2x1.5mm",
            "Datasheet": "https://ww1.microchip.com/downloads/en/DeviceDoc/MCP2518FD-External-CAN-FD-Controller-with-SPI-Interface-20006027B.pdf",
            "Description": "Stand-Alone CAN FD Controller with SPI Interface 14-VDFN",
            "Manufacturer": "Microchip Technology",
            "MPN": "MCP2518FDT-E/QBB",
            "DigiKey": "MCP2518FDT-E/QBBCT-ND",
            "Temp_Range": "-40°C to 125°C",
            "Category": "Logic",
            "Verified": "Yes"
        }
    },
    {
        "name": "796636-6",
        "category": "Connectors",
        "sym_source": POWER_SLAB_DIR / "DigikeyParts" / "796636-6 (tether wall connector)" / "2026-09-19_00-39-41.kicad_sym",
        "fp_source": POWER_SLAB_DIR / "DigikeyParts" / "796636-6 (tether wall connector)" / "footprints.pretty" / "CON6_P5MM_VER_TERM-BLK_TYC.kicad_mod",
        "fp_name": "CON6_P5MM_VER_TERM-BLK_TYC",
        "step_source": None,
        "step_name": None,
        "properties": {
            "Reference": "J",
            "Value": "796636-6",
            "Footprint": "rov_connectors:CON6_P5MM_VER_TERM-BLK_TYC",
            "Datasheet": "https://www.te.com/commerce/DocumentDelivery/DDEController?Action=showdoc&DocId=Customer+Drawing%7F796636%7FB1%7Fpdf%7FEnglish%7FENG_CD_796636_B1.pdf",
            "Description": "Terminal Block Header 6 Pos 5mm Vertical",
            "Manufacturer": "TE Connectivity",
            "MPN": "796636-6",
            "DigiKey": "A98336-ND",
            "Temp_Range": "-40°C to 105°C",
            "Category": "Connectors",
            "Verified": "Yes"
        }
    },
    {
        "name": "INA237AIDGSR",
        "category": "Sensors",
        "sym_source": POWER_SLAB_DIR / "DigikeyParts" / "INA237AIDGSR" / "2026-09-19_00-01-31.kicad_sym",
        "fp_source": POWER_SLAB_DIR / "DigikeyParts" / "INA237AIDGSR" / "footprints.pretty" / "VSSOP_IDGSR_TEX.kicad_mod",
        "fp_name": "VSSOP_IDGSR_TEX",
        "step_source": None,
        "step_name": None,
        "properties": {
            "Reference": "U",
            "Value": "INA237AIDGSR",
            "Footprint": "rov_sensors:VSSOP_IDGSR_TEX",
            "Datasheet": "https://www.ti.com/lit/ds/symlink/ina237.pdf",
            "Description": "85V, 16-Bit, High-Precision Current/Voltage/Power Monitor with I2C",
            "Manufacturer": "Texas Instruments",
            "MPN": "INA237AIDGSR",
            "DigiKey": "296-INA237AIDGSRCT-ND",
            "Temp_Range": "-40°C to 125°C",
            "Category": "Sensors",
            "Verified": "Yes"
        }
    },
    {
        "name": "MIC5504-3.3YM5-TR",
        "category": "Power",
        "sym_source": POWER_SLAB_DIR / "DigikeyParts" / "MIC5504-3.3YM5-TR" / "2026-09-18_23-52-43.kicad_sym",
        "fp_source": POWER_SLAB_DIR / "DigikeyParts" / "MIC5504-3.3YM5-TR" / "footprints.pretty" / "SOT-23-5_MC_MCH.kicad_mod",
        "fp_name": "SOT-23-5_MC_MCH",
        "step_source": None,
        "step_name": None,
        "properties": {
            "Reference": "U",
            "Value": "MIC5504-3.3YM5-TR",
            "Footprint": "rov_power:SOT-23-5_MC_MCH",
            "Datasheet": "https://ww1.microchip.com/downloads/en/DeviceDoc/MIC550X-300mA-Single-LDO-DS20006584A.pdf",
            "Description": "300mA Single LDO Regulator 3.3V Output SOT-23-5",
            "Manufacturer": "Microchip Technology",
            "MPN": "MIC5504-3.3YM5-TR",
            "DigiKey": "576-4763-1-ND",
            "Temp_Range": "-40°C to 125°C",
            "Category": "Power",
            "Verified": "Yes"
        }
    },
    {
        "name": "PKU5511ESI",
        "category": "Power",
        "sym_source": POWER_SLAB_DIR / "DigikeyParts" / "PKU5511ESI" / "PKU5511ESI.kicad_sym",
        "fp_source": POWER_SLAB_DIR / "DigikeyParts" / "PKU5511ESI" / "CONV_PKU5511ESI.kicad_mod",
        "fp_name": "CONV_PKU5511ESI",
        "step_source": None,
        "step_name": None,
        "properties": {
            "Reference": "U",
            "Value": "PKU5511ESI",
            "Footprint": "rov_power:CONV_PKU5511ESI",
            "Datasheet": "https://flexpowermodules.com/documents/fpm-techspec-pku5000s.pdf",
            "Description": "Isolated DC-DC Converter 18-75V Input 5V 10A 50W Output",
            "Manufacturer": "Flex Power Modules",
            "MPN": "PKU5511ESI",
            "DigiKey": "2293-PKU5511ESITR-ND",
            "Temp_Range": "-40°C to 125°C",
            "Category": "Power",
            "Verified": "Yes"
        }
    },
    {
        "name": "SMCJ58A",
        "category": "Power",
        "sym_source": POWER_SLAB_DIR / "DigikeyParts" / "SMCJ58A" / "2026-09-19_01-36-18.kicad_sym",
        "fp_source": POWER_SLAB_DIR / "DigikeyParts" / "SMCJ58A" / "footprints.pretty" / "SMB_STM.kicad_mod",
        "fp_name": "SMB_STM",
        "step_source": None,
        "step_name": None,
        "properties": {
            "Reference": "D",
            "Value": "SMCJ58A",
            "Footprint": "rov_power:SMB_STM",
            "Datasheet": "https://www.st.com/resource/en/datasheet/smcj.pdf",
            "Description": "1500W Surface Mount Transient Voltage Suppressor 58V Unidirectional",
            "Manufacturer": "STMicroelectronics",
            "MPN": "SMCJ58A-TR",
            "DigiKey": "497-7105-1-ND",
            "Temp_Range": "-55°C to 150°C",
            "Category": "Power",
            "Verified": "Yes"
        }
    },
    {
        "name": "TCAN1044",
        "category": "Logic",
        "sym_source": POWER_SLAB_DIR / "DigikeyParts" / "TCAN1044" / "2026-09-19_01-29-57.kicad_sym",
        "fp_source": POWER_SLAB_DIR / "DigikeyParts" / "TCAN1044" / "footprints.pretty" / "D0008A-IPC_A.kicad_mod",
        "fp_name": "D0008A-IPC_A",
        "step_source": None,
        "step_name": None,
        "properties": {
            "Reference": "U",
            "Value": "TCAN1044D",
            "Footprint": "rov_logic:D0008A-IPC_A",
            "Datasheet": "https://www.ti.com/lit/ds/symlink/tcan1044-q1.pdf",
            "Description": "Automotive Fault-Protected CAN FD Transceiver SOIC-8",
            "Manufacturer": "Texas Instruments",
            "MPN": "TCAN1044D",
            "DigiKey": "296-TCAN1044DCT-ND",
            "Temp_Range": "-55°C to 125°C",
            "Category": "Logic",
            "Verified": "Yes"
        }
    },
    {
        "name": "TMP1075NDRLR",
        "category": "Sensors",
        "sym_source": POWER_SLAB_DIR / "DigikeyParts" / "TMP1075NDRLR" / "2026-09-19_00-08-04.kicad_sym",
        "fp_source": POWER_SLAB_DIR / "DigikeyParts" / "TMP1075NDRLR" / "footprints.pretty" / "SOT5X3-6_DRL_TEX.kicad_mod",
        "fp_name": "SOT5X3-6_DRL_TEX",
        "step_source": None,
        "step_name": None,
        "properties": {
            "Reference": "U",
            "Value": "TMP1075NDRLR",
            "Footprint": "rov_sensors:SOT5X3-6_DRL_TEX",
            "Datasheet": "https://www.ti.com/lit/ds/symlink/tmp1075.pdf",
            "Description": "±0.5°C Accurate Digital Temperature Sensor with I2C/SMBus Interface",
            "Manufacturer": "Texas Instruments",
            "MPN": "TMP1075NDRLR",
            "DigiKey": "296-49272-1-ND",
            "Temp_Range": "-55°C to 125°C",
            "Category": "Sensors",
            "Verified": "Yes"
        }
    }
]


def port_all_parts():
    print("[INFO] Beginning porting of external board components into standard library...\n")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    success_count = 0

    for part_def in PARTS_TO_PORT:
        name = part_def["name"]
        cat = part_def["category"]
        print(f"[INFO] Processing [{cat}] {name}...")

        # 1. 3D Model
        if part_def["step_source"] and part_def["step_source"].is_file():
            dest_step = MODELS_DIR / part_def["step_name"]
            shutil.copy2(part_def["step_source"], dest_step)
            print(f"  - 3D Model: Copied to {dest_step.relative_to(BASE_DIR)}")

        # 2. Footprint
        if part_def["fp_source"] and part_def["fp_source"].is_file():
            cat_pretty = FOOTPRINTS_DIR / f"rov_{cat.lower()}.pretty"
            cat_pretty.mkdir(parents=True, exist_ok=True)
            dest_fp = cat_pretty / f"{part_def['fp_name']}.kicad_mod"
            shutil.copy2(part_def["fp_source"], dest_fp)

            # If 3D model exists for this part, link it in footprint
            if part_def["step_name"]:
                link_3d_model_to_footprint(dest_fp, part_def["step_name"])
                print(f"  - Footprint: Copied to {dest_fp.relative_to(BASE_DIR)} and linked 3D model '{part_def['step_name']}'.")
            else:
                print(f"  - Footprint: Copied to {dest_fp.relative_to(BASE_DIR)}.")

        # 3. Symbol
        if not part_def["sym_source"].is_file():
            print(f"  [ERROR] Source symbol file missing at {part_def['sym_source']}")
            continue

        raw_content = part_def["sym_source"].read_text(encoding="utf-8", errors="ignore")
        extracted = extract_top_symbols(raw_content)
        if not extracted:
            print(f"  [ERROR] Could not extract symbol from {part_def['sym_source']}")
            continue

        orig_name, raw_sym, _, _ = extracted[0]

        # Inject / standardize properties
        updated_sym = update_or_inject_properties(raw_sym, part_def["properties"])

        # Validate S-expression
        wrapped = (
            '(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor)\n'
            f'  {updated_sym.strip()}\n'
            ')\n'
        )
        sexpr_ok, sexpr_err = validate_sexpr(wrapped)
        if not sexpr_ok:
            print(f"  [ERROR] Invalid S-expression syntax for {name}: {sexpr_err}")
            continue

        # Rule validation
        errs, warns = validate_component_rules(part_def["properties"])
        if errs:
            print(f"  [FAIL] Rule validation failed: {errs}")
            continue

        # Save to Symbols/parts/<category>/<name>.kicad_sym
        cat_folder = SYMBOLS_PARTS_DIR / cat.lower()
        cat_folder.mkdir(parents=True, exist_ok=True)
        dest_part_file = cat_folder / f"{name}.kicad_sym"
        dest_part_file.write_text(wrapped, encoding="utf-8")
        print(f"  - Symbol: Saved atomic part file to {dest_part_file.relative_to(BASE_DIR)}")
        success_count += 1

    # Recompile all monolithic libraries
    print("\n[INFO] Recompiling monolithic category libraries...")
    summary = build_all_categories()
    for c, cnt in summary.items():
        print(f"  - rov_{c.lower()}: {cnt} part(s)")

    print(f"\n[OK] Successfully ported {success_count}/{len(PARTS_TO_PORT)} parts into standard library!\n")
    return success_count == len(PARTS_TO_PORT)


if __name__ == "__main__":
    if not port_all_parts():
        sys.exit(1)
