# Purdue ROV Central KiCad Library

This repository contains the unified, team-wide source of truth for symbols, footprints, 3D models, and Design Blocks used by Purdue ROV.

---

## Directory Structure

```
purdue-rov-kicad-lib/
├── Symbols/
│   └── rov_parts.kicad_sym       # Central Symbol Library file (all parts nested here)
├── Footprints/
│   └── rov_parts.pretty/         # Central Footprint Library directory
│       └── *.kicad_mod           # Individual Footprints
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

---

## Automated Validation & CI/CD

This repository enforces quality controls automatically:

### 1. Local Verification
Before committing, you can run the linter script locally to verify your symbols:
```bash
python3 scripts/linter_validator.py Symbols/rov_parts.kicad_sym
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

## Contributions Workflow

1.  Create a branch for your component addition: `git checkout -b feature/add-[part-name]`.
2.  Add your parts to [rov_parts.kicad_sym](Symbols/rov_parts.kicad_sym) and [rov_parts.pretty](Footprints/rov_parts.pretty) using KiCad editors.
3.  Verify locally: `python3 scripts/linter_validator.py Symbols/rov_parts.kicad_sym`.
4.  Commit your changes and open a Pull Request.
5.  Once the status checks pass, merge the PR.
6.  Once merged, update the submodule in your project repository:
    ```bash
    git submodule update --remote --merge
    ```
