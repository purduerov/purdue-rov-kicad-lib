# Purdue ROV Central KiCad Library

Central KiCad library containing symbols, footprints, 3D models, and reusable design blocks for Purdue ROV hardware projects.

## Library Structure

Components are organized into six standard categories:

```
purdue-rov-kicad-lib/
├── Symbols/
│   ├── rov_passives.kicad_sym      # Resistors, capacitors, inductors, crystals
│   ├── rov_power.kicad_sym         # Regulators, buck/boost converters, MOSFETs, diodes
│   ├── rov_logic.kicad_sym         # MCUs, logic ICs, op-amps, drivers, transceivers
│   ├── rov_connectors.kicad_sym    # Terminals, XT60/XT30, headers, USB, JST
│   ├── rov_sensors.kicad_sym       # IMUs, pressure/temperature sensors, cameras
│   └── rov_mech.kicad_sym          # Mounting holes, standoffs, test points
├── Footprints/
│   ├── rov_passives.pretty/
│   ├── rov_power.pretty/
│   ├── rov_logic.pretty/
│   ├── rov_connectors.pretty/
│   ├── rov_sensors.pretty/
│   └── rov_mech.pretty/
├── 3D_Models/                      # STEP and WRL 3D CAD files
├── Design_Blocks/                  # Reusable schematic & PCB sub-circuits
└── scripts/                        # Import, linting, and maintenance utilities
```

## Managing & Adding Components (GUI)

Launch the all-in-one component manager to browse, search, edit, import, delete, and validate parts:

- **Windows:** Double-click `LIBRARY_MANAGER.bat`
- **macOS / Linux:** Run `./LIBRARY_MANAGER.sh` (or `python3 scripts/library_manager_gui.py`)

### Features
* 🔍 **Live Search & Filtering:** Search across MPN, Manufacturer, Description, and Category.
* ➕ **1-Click Part Ingestion:** Click **➕ Add / Import Part** to drag & drop `.zip` downloads from SnapEDA, Ultra Librarian, DigiKey, or LCSC. Automatically extracts symbols, footprints (`.kicad_mod`), and 3D models.
* 🟢 **Downloads Watcher:** Optional background watcher that auto-detects newly downloaded CAD files in your `~/Downloads` folder.
* ⚙️ **In-Place Field Editor:** Edit and save any mandatory symbol metadata, or change categories with 1-click.
* 🗑️ **Safe Component Deletion:** Cleanly delete unused symbols from `.kicad_sym` category files.
* 🔍 **1-Click Linter Validation:** Verify 100% compliance across all 6 library files before pushing.
* 🚀 **Git Sync:** Direct pull, commit, and push integration with GitHub `master`.

### CLI Import (Optional)
```bash
python3 scripts/import_part.py --symbol <path-to-sym> --footprint <path-to-mod> --category Power
```



## Required Symbol Fields

Every symbol must include these fields to pass CI linting:

| Field | Description | Example |
| :--- | :--- | :--- |
| `Category` | One of: `Passives`, `Power`, `Logic`, `Connectors`, `Sensors`, `Mech` | `Power` |
| `MPN` | Exact Manufacturer Part Number | `TPS54302DDCR` |
| `Manufacturer` | Manufacturer name | `Texas Instruments` |
| `DigiKey` | DigiKey part number or SKU | `296-48767-1-ND` |
| `Datasheet` | Direct PDF URL (`http://` or `https://`) | `https://www.ti.com/lit/ds/symlink/tps54302.pdf` |
| `Temp_Range` | Operating temperature range | `-40°C to 125°C` |

## Local Validation

Run the symbol linter before committing:
```bash
python3 scripts/linter_validator.py Symbols/*.kicad_sym
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for conventions on symbol pins, footprint pad geometry, and thermal aperture masking.
