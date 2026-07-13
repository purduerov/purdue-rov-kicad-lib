# Guide to Contributing Components

This document outlines the step-by-step process for creating, importing, and submitting schematic symbols, PCB footprints, and 3D models to the central library database.

---

## Table of Contents
1. [Step-by-Step Guide to Adding a Component](#step-by-step-guide-to-adding-a-component)
2. [How to Import Symbols Downloaded Online](#how-to-import-symbols-downloaded-online)
3. [Footprint Design & Reflow Best Practices](#footprint-design--reflow-best-practices)

---

## Step-by-Step Guide to Adding a Component

Follow these instructions exactly to create a new symbol, footprint, and 3D model from scratch:

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
3. Create your footprint. (See [Footprint Design Best Practices](#footprint-design--reflow-best-practices) below).
4. Save the footprint inside the `rov_parts` library.

### Step 3: Add the 3D Model
1. Obtain the 3D model of the part in **`.step`** format (do not use `.wrl` as STEP is required for mechanical CAD exports to SolidWorks/Onshape).
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

---

## How to Import Symbols Downloaded Online

If you downloaded a symbol from Ultra Librarian, SnapEDA, or SamacSys, it will come as a standalone `.kicad_sym` file. Follow one of the methods below to merge it into the central `rov_parts.kicad_sym` file.

### Method A: Using the KiCad Symbol Editor (Recommended)
1.  **Add the Downloaded File as a Temporary Library**:
    *   Open KiCad.
    *   Go to **Preferences ➔ Manage Symbol Libraries**.
    *   Select the **Project Specific Libraries** tab.
    *   Click the **Add Library (folder icon)** button, select the downloaded `.kicad_sym` file, and name it `temp_download`. Click **OK**.
2.  **Copy the Symbol**:
    *   Open the **Symbol Editor**.
    *   In the library panel on the left, scroll down to find `temp_download`.
    *   Expand it, right-click the symbol, and select **Copy**.
3.  **Paste into the Central Library**:
    *   Scroll to find the `rov_parts` library (which maps to your `purdue-rov-kicad-lib` submodule).
    *   Right-click `rov_parts` and click **Paste Symbol**.
4.  **Enrich Properties**:
    *   Double-click the pasted symbol in `rov_parts` to open its properties.
    *   Populate the **5 mandatory fields** (`MPN`, `Manufacturer`, `DigiKey`, `Datasheet`, `Temp_Range`) and make sure the **Footprint** field points to `ROV_Footprints:[footprint_name]`.
    *   Click **Save**.
5.  **Remove the Temporary Library**:
    *   Go back to **Preferences ➔ Manage Symbol Libraries** and remove the `temp_download` entry so your catalog stays clean.

### Method B: Text Editor Copy-Paste (Fast / Power-User Method)
Because KiCad symbols are stored as nested text blocks inside a single file, you can merge them using any text editor:
1.  Open the downloaded `.kicad_sym` file in your text editor (e.g. VS Code).
2.  Locate the symbol block starting with `(symbol "PART_NAME" ...)` and select the entire block (including all its contents and matching closing parentheses). **Copy it**.
3.  Open the central `Symbols/rov_parts.kicad_sym` file in your text editor.
4.  Scroll to the very bottom of the file. Right before the final closing parenthesis `)` of the library, paste your copied symbol block.
5.  Open KiCad's **Symbol Editor**, load `rov_parts`, verify the symbol loads correctly, add the 5 mandatory fields, and click **Save**.

---

## Footprint Design & Reflow Best Practices

When designing footprints, follow these industry standards to ensure high assembly yield:

### 1. Solder Paste Aperture Optimization (Thermal Pads)
For ICs with large central ground/thermal pads and large SMD power pads:
*   **The Issue**: Applying a solid layer of solder paste over a large area causes the component to "float" on liquid solder during reflow, leading to pins lifting, misaligning, or bridging.
*   **The Solution**: Go to pad properties in the Footprint Editor and set a custom **Solder Paste Clearance Override**. Divide the paste aperture into a grid of smaller squares, targeting **50-80% total copper coverage** with gaps in between. This allows outgassing channels for reflow volatiles and keeps the component flat.

### 2. Silk-to-Solder Mask Clearances
*   Ensure all silkscreen elements (drawings, outlines, refdes labels) are kept at least **0.2mm** away from open copper pads to prevent ink from contaminating the solder joints.
