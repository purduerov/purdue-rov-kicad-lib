# Purdue ROV Central KiCad Library

This repository contains the unified, team-wide source of truth for symbols, footprints, 3D models, and Design Blocks used by Purdue ROV.

---

## Directory Structure

```
purdue-rov-kicad-lib/
├── Symbols/
│   ├── rov_passives.kicad_sym    # Passives (Resistors, Capacitors, Inductors)
│   ├── rov_power.kicad_sym       # Power (Regulators, MOSFETs, Batteries)
│   ├── rov_logic.kicad_sym       # Logic (MCUs, ICs, OpAmps, Drivers)
│   ├── rov_connectors.kicad_sym  # Connectors (Terminals, Headers, Plugs)
│   ├── rov_sensors.kicad_sym     # Sensors (IMUs, Cameras, Thermistors)
│   └── rov_mech.kicad_sym        # Mechanical (Mounting holes, standoffs)
├── Footprints/
│   ├── rov_passives.pretty/      # Passives footprints
│   ├── rov_power.pretty/         # Power footprints
│   ├── rov_logic.pretty/         # Logic footprints
│   ├── rov_connectors.pretty/    # Connectors footprints
│   ├── rov_sensors.pretty/       # Sensors footprints
│   └── rov_mech.pretty/          # Mechanical footprints
├── 3D_Models/                    # 3D models (.step/.wrl) for footprints
├── Design_Blocks/                # Reusable sub-circuits (e.g. buck converters)
└── scripts/
    └── linter_validator.py       # Python validation check script
```

---

## Adding Components

When creating or importing new symbols or footprints, you must adhere to the following standards:

### 1. Mandatory Symbol Fields
To pass the library validator, every symbol **must** have the following custom fields populated:
*   **`Category`**: Must be one of `Passives`, `Power`, `Logic`, `Connectors`, `Sensors`, `Mech`.
*   **`MPN`**: Manufacturer Part Number (exact match).
*   **`Manufacturer`**: The component's manufacturer name (e.g., `AMASS`, `Texas Instruments`).
*   **`DigiKey`**: The DigiKey Part Number/SKU (e.g., `1528-2615-ND`).
*   **`Datasheet`**: A direct, valid URL link pointing to the PDF datasheet (must start with `http://` or `https://` and end with `.pdf`).
*   **`Temp_Range`**: The manufacturer-specified operating temperature range (e.g., `-20°C to 120°C`).

### 2. General Library Rules
*   Ensure pins are matched exactly to the physical footprint.
*   Link 3D step models under `3D_Models/` using relative paths:
    `${KICAD_PROJECT_DIR}/libs/purdue-rov-kicad-lib/3D_Models/part.step`
*   **Solder Paste & Stencil Optimization**: For ICs with large central ground pads (thermal pads) and fine-pitch components, set a custom **Solder Paste Clearance Override** in the pad settings. Divide large paste apertures into a grid of smaller apertures (50-80% coverage) to prevent parts floating or bridging during SMD reflow.

### 3. Automated Part Importer (1-Click Desktop GUI & Watcher)
To make adding downloaded parts from online (SnapEDA, DigiKey, Ultra Librarian, Component Search Engine, LCSC) completely effortless:

#### **Double-Click 1-Click Launcher:**
Simply double-click **`IMPORT_PART_WIZARD.bat`** (Windows) or **`IMPORT_PART_WIZARD.sh`** (Mac/Linux) in the library folder!

#### **Features:**
* 📁 **Drag & Drop / ZIP Auto-Extraction:** Select or drag a `.zip`, `.kicad_sym`, or `.kicad_mod` file.
* 🟢 **Downloads Watcher Mode:** Click **"Start Downloads Watcher"**. As soon as you click "Download" in your browser, the wizard automatically pops up with pre-filled fields!
* 🚀 **1-Click Push:** Injects mandatory fields, links footprints, validates compliance, and pushes directly to `master`!

---


## Automated Validation & CI/CD

This repository enforces quality controls automatically:

### 1. Local Verification
Before committing, you can run the linter script locally to verify your symbols:
```bash
python3 scripts/linter_validator.py Symbols/*.kicad_sym
```
*Note: The linter is smart and automatically skips KiCad's unit/graphic sub-symbols (e.g., `XT60-M_0_0`), only validating the top-level parent components.*

### 2. GitHub Actions CI
On every push or Pull Request to `master` or `main`, the [Symbol Library Validation](.github/workflows/library-ci.yml) workflow runs. This triggers `linter_validator.py` in the cloud.

### 3. Branch Protection
To maintain the integrity of the central library:
*   Direct pushes to `master` are **blocked**.
*   All additions must be made through a Pull Request.
*   The **`lint-symbols`** status check must pass before merging is allowed.

---

## Adding Components

For a detailed, step-by-step developer tutorial on how to create parts from scratch, import symbols downloaded from online databases (such as SnapEDA, Digikey, or Ultra Librarian), and configure high-yield footprints, please refer to:

👉 **[CONTRIBUTING.md](CONTRIBUTING.md)**
