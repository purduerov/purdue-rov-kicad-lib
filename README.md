# Purdue ROV Central KiCad Library

This repository contains the unified, team-wide source of truth for symbols, footprints, 3D models, and Design Blocks used by Purdue ROV.

## Directory Structure

```
purdue-rov-kicad-lib/
├── 3D_Models/                    # 3D models (.step/.wrl) for footprints
│   └── <model-name>.step         # STEP/WRL file (e.g., XT60-M.step)
├── Design_Blocks/                # Reusable sub-circuits (e.g. buck converters)
├── Footprints/
│   └── rov_parts.pretty/         # Central Footprint Library folder (required `.pretty` suffix)
│       └── *.kicad_mod           # Individual footprint files
├── Symbols/
│   └── rov_parts.kicad_sym       # Central Symbol Library file
```

> [!NOTE]
> **Why the `.pretty` folder is required:** KiCad treats footprint libraries as folders, not single aggregated files (unlike symbols which are stored in a single `.kicad_sym` file). The individual footprint files (`.kicad_mod`) must live inside a directory ending with a `.pretty` suffix. KiCad's library parser strictly requires this extension to recognize the directory as a valid footprint library.

## Integration into KiCad Project

To use this library in your KiCad project, it should be integrated into your project's root folder and registered in KiCad.

### 1. Clone the Library (Recommended: Git Submodule)
Cloning a repository inside another repository creates an untracked nested repo, which can lead to accidental commits or missing files. To avoid this, add this library as a Git Submodule from the root directory of your KiCad project:

```bash
git submodule add https://github.com/purdue-rov/purdue-rov-kicad-lib.git
```
This tracks the library under version control and places the folder (`purdue-rov-kicad-lib`) directly in your KiCad project root.

### 2. Configure Symbol & Footprint Libraries
There are two ways to register the libraries in KiCad: the automated configuration (recommended) or manual configuration.

#### Option A: Automated Configuration (Recommended)
KiCad project-specific libraries are managed via `sym-lib-table` (for symbols) and `fp-lib-table` (for footprints) files in your project's root directory. 

You can automate library registration for the entire team by committing these files to your KiCad project repository with the following entries:

**`sym-lib-table`**
```lisp
(sym_lib_table
  (lib (name "rov_parts")(type "KiCad")(uri "${KIPRJMOD}/purdue-rov-kicad-lib/Symbols/rov_parts.kicad_sym")(options "")(descr ""))
)
```

**`fp-lib-table`**
```lisp
(fp_lib_table
  (lib (name "rov_parts")(type "KiCad")(uri "${KIPRJMOD}/purdue-rov-kicad-lib/Footprints/rov_parts.pretty")(options "")(descr ""))
)
```
*Note: If these files already exist in your project root, simply append the `(lib ...)` line to the existing table.*

#### Option B: Manual Configuration (via KiCad GUI)
If you prefer to configure this manually through the KiCad GUI:

1. **Manage Symbol Libraries**:
   - Open your project in KiCad.
   - Go to **Preferences** > **Manage Symbol Libraries...**
   - Select the **Project Specific Libraries** tab.
   - Click the **+** (Add library) icon and enter:
     - **Nickname**: `rov_parts`
     - **Library Path**: `${KIPRJMOD}/purdue-rov-kicad-lib/Symbols/rov_parts.kicad_sym`
     - **Active**: Checked

2. **Manage Footprint Libraries**:
   - Go to **Preferences** > **Manage Footprint Libraries...**
   - Select the **Project Specific Libraries** tab.
   - Click the **+** (Add library) icon and enter:
     - **Nickname**: `rov_parts`
     - **Library Path**: `${KIPRJMOD}/purdue-rov-kicad-lib/Footprints/rov_parts.pretty`
     - **Active**: Checked

### 3. Setting Up 3D Models (CRITICAL)
When assigning 3D models to footprints:
- **DO NOT** use absolute local paths (e.g., `C:\Users\...` or `/Users/...`). Doing so will break the 3D rendering for other team members.
- **DO** use the project-relative path variable `${KIPRJMOD}`.
- Format the path exactly as:
  `${KIPRJMOD}/purdue-rov-kicad-lib/3D_Models/<model-name>.step`
  *(e.g., `${KIPRJMOD}/purdue-rov-kicad-lib/3D_Models/XT60-M.step`)*

## Adding Components

When creating or importing new symbols or footprints:
1. Ensure the symbol matches standard naming conventions.
2. Every symbol **must** have the following custom fields populated:
   - `MPN` (Manufacturer Part Number)
   - `DigiKey` (DigiKey Part Number / SKU)
   - `Datasheet` (URL link to the PDF datasheet)
3. Ensure pins are matched exactly to the physical footprint.
4. Keep 3D step models under `3D_Models/` and link them using the project-relative path variable `${KIPRJMOD}` (e.g., `${KIPRJMOD}/purdue-rov-kicad-lib/3D_Models/<model-name>.step`). Do **not** use absolute local paths.
5. **Solder Paste & Stencil Optimization**: For ICs with large central ground pads (thermal pads) and fine-pitch components, set a custom **Solder Paste Clearance Override** in the pad settings. Divide large paste apertures into a grid of smaller apertures (50-80% coverage) to prevent parts floating or bridging during SMD reflow.


## Contributions

1. Create a branch for your component addition: `git checkout -b feature/add-[part-name]`.
2. Add your parts using KiCad symbol and footprint editors.
3. Commit your changes and open a Pull Request.
4. Once reviewed and approved by the Electrical leads, it will be merged into the `main` branch.
