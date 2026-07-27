# Purdue ROV Central KiCad Library

This repository is the unified, team-wide source of truth for symbols, footprints, 3D models, and Design Blocks used by the Purdue ROV Electrical Team.

---

## 📁 Directory & Categorization Structure

All components are organized into 6 standard category libraries:

```
purdue-rov-kicad-lib/
├── Symbols/
│   ├── rov_passives.kicad_sym    # Passives (Resistors, Capacitors, Inductors, Crystals)
│   ├── rov_power.kicad_sym       # Power (Regulators, Buck/Boost, MOSFETs, Diodes, PMICs)
│   ├── rov_logic.kicad_sym       # Logic (MCUs, STM32, ESP32, OpAmps, Drivers, Transceivers)
│   ├── rov_connectors.kicad_sym  # Connectors (Terminals, XT60, JST, Headers, USB)
│   ├── rov_sensors.kicad_sym     # Sensors (IMUs, Pressure, Temperature, Cameras)
│   └── rov_mech.kicad_sym        # Mechanical (Mounting holes, heatsinks, standoffs)
├── Footprints/
│   ├── rov_passives.pretty/      # Passives footprints (.kicad_mod)
│   ├── rov_power.pretty/         # Power footprints (.kicad_mod)
│   ├── rov_logic.pretty/         # Logic footprints (.kicad_mod)
│   ├── rov_connectors.pretty/    # Connectors footprints (.kicad_mod)
│   ├── rov_sensors.pretty/       # Sensors footprints (.kicad_mod)
│   └── rov_mech.pretty/          # Mechanical footprints (.kicad_mod)
├── 3D_Models/                    # 3D models (.step / .wrl)
├── Design_Blocks/                # Reusable sub-circuits (e.g. buck converter modules)
├── IMPORT_PART_WIZARD.bat        # Windows 1-Click Desktop GUI Part Importer
├── IMPORT_PART_WIZARD.sh         # Mac/Linux 1-Click Desktop GUI Part Importer
└── scripts/
    ├── import_part_gui.py        # Desktop GUI & Downloads Watcher
    ├── import_part.py            # CLI Part Importer Backend
    ├── linter_validator.py       # Central Symbol Compliance Linter
    └── categorize_library.py     # Automated Category Migration Script
```

---

## ⚡ 1-Click Part Importer Wizard & Downloads Watcher

To make adding downloaded parts from online databases (SnapEDA, DigiKey, Ultra Librarian, Component Search Engine, LCSC) completely effortless:

### 1. **Launch the Desktop Wizard**
* **Windows:** Double-click **`IMPORT_PART_WIZARD.bat`**
* **Mac / Linux:** Double-click **`IMPORT_PART_WIZARD.sh`** (or run `python3 scripts/part_importer_gui.py`)

### 2. **Automatic Features**
* 📁 **Drag & Drop / ZIP Auto-Extraction:** Drag a downloaded `.zip`, `.kicad_sym`, or `.kicad_mod` file into the window.
* 🟢 **Downloads Watcher Mode:** Click **"Start Downloads Watcher"**. When you click "Download" in your browser, the wizard automatically pops up with pre-filled fields (`MPN`, `Manufacturer`, `Datasheet link`, `DigiKey SKU`).
* 🚀 **1-Click Import & Push:** Automatically injects mandatory fields, copies footprints, validates against linter rules, and pushes to `master`!

---

## 📋 Mandatory Symbol Fields

Every component symbol **must** have the following 6 custom fields to pass linter validation:

1. **`Category`**: Must be one of `Passives`, `Power`, `Logic`, `Connectors`, `Sensors`, `Mech`.
2. **`MPN`**: Manufacturer Part Number (exact match).
3. **`Manufacturer`**: Component manufacturer name (e.g., `AMASS`, `Texas Instruments`).
4. **`DigiKey`**: DigiKey SKU / Part Number (e.g., `1528-2615-ND`).
5. **`Datasheet`**: Direct PDF URL starting with `http://` or `https://` and ending with `.pdf`.
6. **`Temp_Range`**: Operating temperature range (e.g., `-40°C to 125°C`).

---

## 🔍 Automated Verification & CI/CD

Before committing, run local verification:
```bash
python3 scripts/linter_validator.py Symbols/*.kicad_sym
```

GitHub Actions automatically runs symbol linter checks on every push to `master`.

---

## 📖 Contributor Guidelines

For a detailed tutorial on creating custom symbols and footprint solder-paste aperture grid overrides for thermal pads, see **[CONTRIBUTING.md](CONTRIBUTING.md)**.
