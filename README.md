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

## Step-by-Step Guide to Adding a Component

Follow these instructions exactly to add a new symbol, footprint, and 3D model to the library:

### Step 1: Prep Your Local Workspace
1. Navigate to the library submodule folder inside your board repository (or your standalone library clone):
   ```bash
   cd libs/purdue-rov-kicad-lib
   ```
2. Make sure you are on `master` and fully up to date:
   ```bash
   git checkout master
   git pull origin master
   ```
3. Create a branch for your part:
   ```bash
   git checkout -b feature/add-[part-name]
   ```

### Step 2: Create and Link the Footprint
1. Open KiCad's **Footprint Editor**.
2. Select the `rov_parts` library (mapped to `libs/purdue-rov-kicad-lib/Footprints/rov_parts.pretty`).
3. Create your footprint. 
   * *Reflow Optimization*: For large central ground pads (thermal pads), set a custom **Solder Paste Clearance Override** in the pad settings. Divide the solder paste apertures into a grid of smaller squares (covering 50-80% of the pad area) to prevent component floating or solder bridging during reflow.
4. Save the footprint inside the `rov_parts` library.

### Step 3: Add the 3D Model
1. Obtain the 3D model of the part in **`.step`** format (do not use `.wrl` as STEP is required for exporting to SolidWorks/Onshape).
2. Save the STEP file inside the `libs/purdue-rov-kicad-lib/3D_Models/` directory.
3. In the Footprint properties (under the **3D Models** tab), reference the model using the relative path:
   ```
   ${KICAD_PROJECT_DIR}/libs/purdue-rov-kicad-lib/3D_Models/[your-part-name].step
   ```

### Step 4: Create the Symbol and Fields
1. Open KiCad's **Symbol Editor**.
2. Select the `rov_parts` library (mapped to `libs/purdue-rov-kicad-lib/Symbols/rov_parts.kicad_sym`).
3. Create your symbol. 
4. In the symbol properties, set the **Footprint** field to:
   ```
   ROV_Footprints:[exact_footprint_name_you_saved]
   ```
5. Add the **5 mandatory fields** as custom fields:
   *   `MPN`: The Manufacturer Part Number (exact matching).
   *   `Manufacturer`: The manufacturer name.
   *   `DigiKey`: The DigiKey Part Number/SKU (if none exists, use `N/A`).
   *   `Datasheet`: The direct link to the datasheet PDF (must start with `http://` or `https://` and end with `.pdf`).
   *   `Temp_Range`: The operating temperature range (e.g., `-40°C to 125°C`).
6. Save the symbol inside `rov_parts`.

### Step 5: Verify Locally
1. Run the python linter script from the library root to ensure it passes all validations:
   ```bash
   python scripts/linter_validator.py Symbols/rov_parts.kicad_sym
   ```
2. Verify that the output says `Validation successful!`. If there are lint errors, fix the fields in the Symbol Editor and save again.

### Step 6: Commit and Push
1. Check git status to ensure you aren't staging junk files (like `.DS_Store` or local `.kicad_prl` configs):
   ```bash
   git status
   ```
2. Stage only the new files and library modifications:
   ```bash
   git add Symbols/rov_parts.kicad_sym Footprints/rov_parts.pretty/[your-footprint].kicad_mod 3D_Models/[your-model].step
   ```
3. Commit and push your branch:
   ```bash
   git commit -m "feat(library): add [part-name] symbol, footprint, and 3D model"
   git push origin feature/add-[part-name]
   ```

### Step 7: Pull Request & Submodule Update
1. Go to [purdue-rov-kicad-lib on GitHub](https://github.com/purduerov/purdue-rov-kicad-lib) and open a Pull Request.
2. Once the automated `lint-symbols` check passes, merge the PR into `master`.
3. Go back to your board project's root folder:
   ```bash
   cd ../..
   ```
4. Update the submodule reference in your board repo to pull in the newly merged part:
   ```bash
   git submodule update --remote --merge
   ```
5. Commit and push the updated submodule pointer in your board repository:
   ```bash
   git add libs/purdue-rov-kicad-lib
   git commit -m "chore(submodule): update central library to latest master"
   git push origin [your-board-branch]
   ```
