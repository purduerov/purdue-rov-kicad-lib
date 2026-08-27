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

## Adding New Components

When downloading new parts (from SnapEDA, DigiKey, Ultra Librarian, LCSC, etc.), use the import wizard to format and validate them:

### Using the Import Wizard
- **Windows:** Double-click `IMPORT_PART_WIZARD.bat`
- **macOS / Linux:** Run `./IMPORT_PART_WIZARD.sh` (or `python3 scripts/part_importer_gui.py`)

The wizard unpacks downloaded ZIP files, copies `.kicad_mod` files into the appropriate `.pretty` directory, links 3D models, and prompts for required symbol fields.

### Using the CLI Script
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
