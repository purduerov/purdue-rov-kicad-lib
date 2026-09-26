"""
Script to fix X19-USB-Hub-Board project structure and library references:
1. Rename ROV_PCIE_USB_HUB_FINAL.* to X19-USB-Hub-Board.*
2. Update sym-lib-table and fp-lib-table to point to central Purdue ROV libraries.
3. Update all schematic sheets and PCB layout references:
   - ROV_PCIe_USB_HUB:MX25V5126FZUI -> rov_logic:MX25V5126FZUI
   - ROV_PCIe_USB_HUB:UPD720201K8-7x1-BAC-A -> rov_logic:UPD720201K8-7x1-BAC-A
   - ROV_PCIe_USB_HUB:USB2422_MJ -> rov_logic:USB2422_MJ
   - ROV_PCIe_USB_HUB:SFV16R-1STBE1HLF -> rov_connectors:SFV16R-1STBE1HLF
   - ROV_PCIe_USB_HUB:SFV16R-2STE1HLF -> rov_connectors:SFV16R-2STE1HLF
   - ROV_PCIe_USB_HUB:525591652 -> rov_connectors:525591652
   - ROV_PCIe_USB_HUB:SST25VF512A-33-4C-SAE -> rov_logic:SST25VF512A-33-4C-SAE
   - Footprints:
     - ROV_PCIe_USB_HUB:0436500227 -> rov_connectors:0436500227
     - ROV_PCIe_USB_HUB:0436500200 -> rov_connectors:0436500200
     - ROV_PCIe_USB_HUB:1053131102 -> rov_connectors:1053131102
     - ROV_PCIe_USB_HUB:525591652 -> rov_connectors:525591652
     - ROV_PCIe_USB_HUB:AMPHENOL_SFV16R-1STBE1HLF -> rov_connectors:AMPHENOL_SFV16R-1STBE1HLF
     - ROV_PCIe_USB_HUB:AMPHENOL_SFV16R-2STE1HLF -> rov_connectors:AMPHENOL_SFV16R-2STE1HLF
     - ROV_PCIe_USB_HUB:QFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm_ThermalVias -> rov_logic:QFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm_ThermalVias
     - ROV_PCIe_USB_HUB:QFN-68-1EP_8x8mm_P0.4mm_EP6.2x6.2mm -> rov_logic:QFN-68-1EP_8x8mm_P0.4mm_EP6.2x6.2mm
4. Replace hardcoded model path /Users/snadol/... with ${KIPRJMOD}/libs/purdue-rov-kicad-lib/3D_Models/436500227.stp
5. Update project references from ROV_PCIE_USB_HUB_FINAL to X19-USB-Hub-Board
6. Remove local lib/ directory
"""

import os
import shutil
from pathlib import Path

HUB_DIR = Path(r"C:\Users\aman\Documents\PCB Design\X19-PCB\X19-USB-Hub-Board")

REPLACEMENTS = {
    # Symbols
    "ROV_PCIe_USB_HUB:MX25V5126FZUI": "rov_logic:MX25V5126FZUI",
    "ROV_PCIe_USB_HUB:UPD720201K8-7x1-BAC-A": "rov_logic:UPD720201K8-7x1-BAC-A",
    "ROV_PCIe_USB_HUB:USB2422_MJ": "rov_logic:USB2422_MJ",
    "ROV_PCIe_USB_HUB:SFV16R-1STBE1HLF": "rov_connectors:SFV16R-1STBE1HLF",
    "ROV_PCIe_USB_HUB:SFV16R-2STE1HLF": "rov_connectors:SFV16R-2STE1HLF",
    "ROV_PCIe_USB_HUB:525591652": "rov_connectors:525591652",
    "ROV_PCIe_USB_HUB:SST25VF512A-33-4C-SAE": "rov_logic:SST25VF512A-33-4C-SAE",
    # Footprints
    "ROV_PCIe_USB_HUB:0436500227": "rov_connectors:0436500227",
    "ROV_PCIe_USB_HUB:0436500200": "rov_connectors:0436500200",
    "ROV_PCIe_USB_HUB:1053131102": "rov_connectors:1053131102",
    "ROV_PCIe_USB_HUB:525591652": "rov_connectors:525591652",
    "ROV_PCIe_USB_HUB:AMPHENOL_SFV16R-1STBE1HLF": "rov_connectors:AMPHENOL_SFV16R-1STBE1HLF",
    "ROV_PCIe_USB_HUB:AMPHENOL_SFV16R-2STE1HLF": "rov_connectors:AMPHENOL_SFV16R-2STE1HLF",
    "ROV_PCIe_USB_HUB:QFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm_ThermalVias": "rov_logic:QFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm_ThermalVias",
    "ROV_PCIe_USB_HUB:QFN-68-1EP_8x8mm_P0.4mm_EP6.2x6.2mm": "rov_logic:QFN-68-1EP_8x8mm_P0.4mm_EP6.2x6.2mm",
    # Hardcoded 3D model path
    "/Users/snadol/Desktop/ROV_PCIe_USB_HUB/lib/ROV_PCIe_USB_HUB.3d/436500227.stp": "${KIPRJMOD}/libs/purdue-rov-kicad-lib/3D_Models/436500227.stp",
    # Project renaming references
    'project "ROV_PCIE_USB_HUB_FINAL"': 'project "X19-USB-Hub-Board"',
    'sheetfile "ROV_PCIE_USB_HUB_FINAL.kicad_sch"': 'sheetfile "X19-USB-Hub-Board.kicad_sch"',
    '"filename": "ROV_PCIE_USB_HUB_FINAL.kicad_pro"': '"filename": "X19-USB-Hub-Board.kicad_pro"',
    '"filename": "ROV_PCIE_USB_HUB_FINAL.kicad_sch"': '"filename": "X19-USB-Hub-Board.kicad_sch"',
}

def update_file_contents(path: Path):
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8", errors="ignore")
    modified = False
    for k, v in REPLACEMENTS.items():
        if k in text:
            text = text.replace(k, v)
            modified = True
    if modified:
        path.write_text(text, encoding="utf-8")
        print(f"Updated: {path.name}")

def main():
    # 1. Update project tables
    sym_lib_table = """(sym_lib_table
	(version 7)
	(lib (name "rov_passives") (type "KiCad") (uri "${KIPRJMOD}/libs/purdue-rov-kicad-lib/Symbols/rov_passives.kicad_sym") (options "") (descr "Purdue ROV Passives Symbols"))
	(lib (name "rov_power") (type "KiCad") (uri "${KIPRJMOD}/libs/purdue-rov-kicad-lib/Symbols/rov_power.kicad_sym") (options "") (descr "Purdue ROV Power Symbols"))
	(lib (name "rov_logic") (type "KiCad") (uri "${KIPRJMOD}/libs/purdue-rov-kicad-lib/Symbols/rov_logic.kicad_sym") (options "") (descr "Purdue ROV Logic Symbols"))
	(lib (name "rov_connectors") (type "KiCad") (uri "${KIPRJMOD}/libs/purdue-rov-kicad-lib/Symbols/rov_connectors.kicad_sym") (options "") (descr "Purdue ROV Connectors Symbols"))
	(lib (name "rov_sensors") (type "KiCad") (uri "${KIPRJMOD}/libs/purdue-rov-kicad-lib/Symbols/rov_sensors.kicad_sym") (options "") (descr "Purdue ROV Sensors Symbols"))
	(lib (name "rov_mech") (type "KiCad") (uri "${KIPRJMOD}/libs/purdue-rov-kicad-lib/Symbols/rov_mech.kicad_sym") (options "") (descr "Purdue ROV Mechanical Symbols"))
)
"""
    (HUB_DIR / "sym-lib-table").write_text(sym_lib_table, encoding="utf-8")
    print("Rewrote sym-lib-table")

    fp_lib_table = """(fp_lib_table
  (lib (name "rov_passives")(type "KiCad")(uri "${KIPRJMOD}/libs/purdue-rov-kicad-lib/Footprints/rov_passives.pretty")(options "")(descr "Purdue ROV Passives Footprints"))
  (lib (name "rov_power")(type "KiCad")(uri "${KIPRJMOD}/libs/purdue-rov-kicad-lib/Footprints/rov_power.pretty")(options "")(descr "Purdue ROV Power Footprints"))
  (lib (name "rov_logic")(type "KiCad")(uri "${KIPRJMOD}/libs/purdue-rov-kicad-lib/Footprints/rov_logic.pretty")(options "")(descr "Purdue ROV Logic Footprints"))
  (lib (name "rov_connectors")(type "KiCad")(uri "${KIPRJMOD}/libs/purdue-rov-kicad-lib/Footprints/rov_connectors.pretty")(options "")(descr "Purdue ROV Connectors Footprints"))
  (lib (name "rov_sensors")(type "KiCad")(uri "${KIPRJMOD}/libs/purdue-rov-kicad-lib/Footprints/rov_sensors.pretty")(options "")(descr "Purdue ROV Sensors Footprints"))
  (lib (name "rov_mech")(type "KiCad")(uri "${KIPRJMOD}/libs/purdue-rov-kicad-lib/Footprints/rov_mech.pretty")(options "")(descr "Purdue ROV Mechanical Footprints"))
)
"""
    (HUB_DIR / "fp-lib-table").write_text(fp_lib_table, encoding="utf-8")
    print("Rewrote fp-lib-table")

    # 2. Rename files
    renames = [
        ("ROV_PCIE_USB_HUB_FINAL.kicad_pro", "X19-USB-Hub-Board.kicad_pro"),
        ("ROV_PCIE_USB_HUB_FINAL.kicad_sch", "X19-USB-Hub-Board.kicad_sch"),
        ("ROV_PCIE_USB_HUB_FINAL.kicad_pcb", "X19-USB-Hub-Board.kicad_pcb"),
        ("ROV_PCIE_USB_HUB_FINAL.kicad_dru", "X19-USB-Hub-Board.kicad_dru"),
    ]
    for old_name, new_name in renames:
        old_p = HUB_DIR / old_name
        new_p = HUB_DIR / new_name
        if old_p.exists():
            old_p.rename(new_p)
            print(f"Renamed {old_name} -> {new_name}")

    # 3. Update all schematic and pcb files
    for sch in HUB_DIR.glob("*.kicad_sch"):
        update_file_contents(sch)
    for pcb in HUB_DIR.glob("*.kicad_pcb"):
        update_file_contents(pcb)
    for pro in HUB_DIR.glob("*.kicad_pro"):
        update_file_contents(pro)

    # Clean up pinned libs in kicad_pro
    pro_path = HUB_DIR / "X19-USB-Hub-Board.kicad_pro"
    if pro_path.exists():
        pro_text = pro_path.read_text(encoding="utf-8")
        pro_text = pro_text.replace('"ROV_PCIe_USB_HUB"', '"rov_logic"')
        pro_path.write_text(pro_text, encoding="utf-8")

    # 4. Remove obsolete lib/ directory
    old_lib = HUB_DIR / "lib"
    if old_lib.exists():
        shutil.rmtree(old_lib)
        print("Removed obsolete lib/ directory")

    print("Project migration completed successfully.")

if __name__ == "__main__":
    main()
