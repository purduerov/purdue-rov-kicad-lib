# Guide to Contributing Components

This document outlines the step-by-step process for creating, importing, and submitting schematic symbols, PCB footprints, and 3D models to the central library database.

---

## Table of Contents
1. [Before You Start: One Set of Rules](#before-you-start-one-set-of-rules)
2. [Step-by-Step Guide to Adding a Component](#step-by-step-guide-to-adding-a-component)
3. [How to Import Symbols Downloaded Online](#how-to-import-symbols-downloaded-online)
4. [Footprint Design & Reflow Best Practices](#footprint-design--reflow-best-practices)

---

## Before You Start: One Set of Rules

`master` is protected. **Nothing in this repository, and nothing in the Library
Manager GUI, commits to or pushes `master`.** Every contribution lands on a
reviewable branch and arrives as a pull request.

The GUI and the command line are two front ends to the same implementation in
`purduerov/pcb-devops`. They run the same linter, enforce the same staging rules,
and refuse the same things, so a change that passes in one passes in the other.

### Finding the shared CLI

This repository has no `LAUNCH_KICAD` launcher; that belongs to board
repositories. The GUI resolves the shared CLI through `scripts/rov_bridge.py`,
which looks for a DevOps checkout in this order and takes the first one that
really contains `scripts/rov.py`:

1. the `ROV_DEVOPS_DIR` environment variable, which always wins;
2. `.pcb-devops-cache/` inside the library directory;
3. a sibling `../DevOps`, the multi-repository workspace layout;
4. a sibling `../pcb-devops`, the older single-repository sibling name.

`ROV_DEVOPS_DIR` is the only setting that works in every layout. One known gap:
when this library is a board submodule, the board's `LAUNCH_KICAD` puts its
cache in the **board root**, one level above `libs/`, while candidate 2 looks
inside the library directory. In that layout the GUI needs `ROV_DEVOPS_DIR` set.

### How the commands below are written

`--library-dir` defaults to the current directory, so **where you run a command
decides which library it acts on.** There is no `../DevOps` from a board
repository: a board lives at `KiCad/Boards/<board>`, so `../DevOps` would mean
`KiCad/Boards/DevOps`, which does not exist. Pick the form that matches where
you are. Every example is spelled out in full, because a shell variable holding
a multi-word command does not survive word splitting.

- **From this repository's root, with a sibling `../DevOps` checkout.** This is
  the standalone-clone layout, and the only place `../DevOps` is correct.

  macOS or Linux:

  ```bash
  python ../DevOps/scripts/rov.py library validate
  ```

  Windows, in PowerShell or `cmd`:

  ```text
  py -3 ..\DevOps\scripts\rov.py library validate
  ```

- **From the library root inside a board submodule**, where the board's cache is
  two levels up:

  ```bash
  python ../../.pcb-devops-cache/scripts/rov.py library validate
  ```

- **From a board repository root, after `LAUNCH_KICAD` has run once.** The
  board's copy of the platform tools sits at the board root, the same path the
  launcher and the generated `.rov-hooks/pre-commit` use. Name the library
  explicitly, because from a board root the default would resolve to the board
  itself:

  ```bash
  python .pcb-devops-cache/scripts/rov.py library validate --library-dir libs/purdue-rov-kicad-lib
  ```

  ```powershell
  py -3 .pcb-devops-cache\scripts\rov.py library validate --library-dir libs\purdue-rov-kicad-lib
  ```

- **`ROV_DEVOPS_DIR` set.** This is the form that always works.

  macOS or Linux:

  ```bash
  python "$ROV_DEVOPS_DIR/scripts/rov.py" library validate
  ```

  PowerShell:

  ```powershell
  py -3 "$env:ROV_DEVOPS_DIR\scripts\rov.py" library validate
  ```

Substitute the rest of the arguments exactly as written after `rov.py`, and
choose the path that matches your layout. If you prefer a shorthand, define a
shell **function** or an **array**, which both keep the arguments intact. These
work in both bash and zsh:

```bash
# standalone clone, sibling DevOps
rov() { python ../DevOps/scripts/rov.py "$@"; }

# library root inside a board submodule
rov() { python ../../.pcb-devops-cache/scripts/rov.py "$@"; }

# ROV_DEVOPS_DIR set
rov() { python "$ROV_DEVOPS_DIR/scripts/rov.py" "$@"; }
```

```powershell
# PowerShell, sibling DevOps
function Invoke-Rov { py -3 ..\DevOps\scripts\rov.py @args }

# PowerShell, ROV_DEVOPS_DIR set
function Invoke-Rov { py -3 "$env:ROV_DEVOPS_DIR\scripts\rov.py" @args }
```

An array works the same way where your shell supports it. For a standalone
clone with a sibling `../DevOps`:

```bash
ROV=(python ../DevOps/scripts/rov.py "$@")
"${ROV[@]}" library validate
```

Two known follow-ups are recorded rather than fixed, and both need owner
approval before anyone changes them:

- **Legacy tracked `.githooks/pre-commit` files may still reach the network.**
  Older boards and the board template carry a tracked `.githooks/` hook that runs
  `git fetch`/`git pull` against the library submodule and can stage a submodule
  change during an ordinary `git commit`. New boards get the untracked
  `.rov-hooks/` hook, which only validates. If a hook surprises you, use
  `--no-verify` and check `git status` before committing.
- **Board update wrappers rely on repository default permissions.** The reusable
  `update-library.yml` declares least-privilege permissions, but the thin
  `auto-update-submodule.yml` wrappers in each board do not, so they inherit the
  repository default.

---

## Step-by-Step Guide to Adding a Component

Follow these instructions exactly to create a new symbol, footprint, and 3D model from scratch:

### Step 1: Prep Your Local Workspace
1. Navigate to the library root. Use your standalone library clone, or the library submodule inside your board repository:
   ```bash
   cd libs/purdue-rov-kicad-lib
   ```
   Every `rov library` command in Steps 1, 5, and 6 must be run from this directory, because `--library-dir` defaults to the current directory. There is no `../DevOps` here when the library is a board submodule; the paths above cover that case.
2. Make sure you are on `master` and fully up to date. Use the safe sync, which requires a clean worktree, fetches, and fast-forwards. It never pushes and never resets your work. From the library root, use the form that matches your layout:
   ```bash
   # standalone clone, sibling DevOps
   python ../DevOps/scripts/rov.py library sync
   ```
   ```bash
   # library root inside a board submodule
   python ../../.pcb-devops-cache/scripts/rov.py library sync
   ```
   If the remote is unreachable, the command reports `BLOCKED` and keeps your cached revision rather than pretending you are current.
3. Do not create a branch by hand. `library contribute` creates the `add-part-*` branch from `master` after validation, which is what keeps contributions from stacking on each other.

### Step 2: Create and Link the Footprint
1. Open KiCad's **Footprint Editor**.
2. Select the appropriate categorized footprint library (`rov_passives`, `rov_power`, `rov_logic`, `rov_connectors`, `rov_sensors`, or `rov_mech`).
3. Create your footprint. (See [Footprint Design Best Practices](#footprint-design--reflow-best-practices) below).
4. Save the footprint inside the chosen library.

### Step 3: Add the 3D Model
1. Obtain the 3D model of the part in **`.step`** format (do not use `.wrl` as STEP is required for mechanical CAD exports to SolidWorks/Onshape).
2. Save the STEP file inside the `libs/purdue-rov-kicad-lib/3D_Models/` directory.
3. In the Footprint properties (under the **3D Models** tab), reference the model using the relative path:
   ```
   ${KICAD_PROJECT_DIR}/libs/purdue-rov-kicad-lib/3D_Models/[your-part-name].step
   ```

### Step 4: Create the Symbol and Fields
1. Open KiCad's **Symbol Editor**.
2. Select the appropriate categorized symbol library (`rov_passives`, `rov_power`, `rov_logic`, `rov_connectors`, `rov_sensors`, or `rov_mech`).
3. Create your symbol. 
4. In the symbol properties, set the **Footprint** field to:
   ```
   ROV_Footprints:[exact_footprint_name_you_saved]
   ```
5. Add the **6 mandatory fields** as custom fields:
   *   `Category`: Must be one of `Passives`, `Power`, `Logic`, `Connectors`, `Sensors`, `Mech`. Click the `+` button in Symbol Properties to add a new custom field.
   *   `MPN`: The Manufacturer Part Number (exact matching).
   *   `Manufacturer`: The manufacturer name.
   *   `DigiKey`: The DigiKey Part Number/SKU (if none exists, use `N/A`).
   *   `Datasheet`: The direct link to the datasheet PDF (must start with `http://` or `https://` and end with `.pdf`).
   *   `Temp_Range`: The operating temperature range (e.g., `-40°C to 125°C`).
6. Save the symbol inside the chosen library.

### Step 5: Verify Locally
1. Run the shared linter through the CLI. This is the same check CI runs. From the library root, use the form that matches your layout:
   ```bash
   # standalone clone, sibling DevOps
   python ../DevOps/scripts/rov.py library validate
   ```
   ```bash
   # library root inside a board submodule
   python ../../.pcb-devops-cache/scripts/rov.py library validate
   ```
2. Verify that the output says `Validation successful!`. If there are lint errors, fix the fields in the Symbol Editor and save again.
3. Optionally rebuild the generated category libraries so the new part is visible to every consuming table:
   ```bash
   # standalone clone, sibling DevOps
   python ../DevOps/scripts/rov.py library build
   ```
   ```bash
   # library root inside a board submodule
   python ../../.pcb-devops-cache/scripts/rov.py library build
   ```

### Step 6: Prepare the Branch and Pull Request
1. Check `git status` first. `library contribute` refuses to run when anything outside `Symbols/`, `Footprints/`, `3D_Models/`, or `Design_Blocks/` is modified, so clear out stray files such as `.DS_Store` or local `.kicad_prl` state before you start:
   ```bash
   git status
   ```
2. Validate, create the branch, stage only the library directories, commit, and open the pull request in one command, from the library root:
   ```bash
   # standalone clone, sibling DevOps
   python ../DevOps/scripts/rov.py library contribute --name [MPN] --category [Category] --push --pr
   ```
   ```bash
   # library root inside a board submodule
   python ../../.pcb-devops-cache/scripts/rov.py library contribute --name [MPN] --category [Category] --push --pr
   ```
   The branch is named `add-part-<part>-<timestamp>` and the commit message is `feat(parts): add [MPN] to [Category]`.
3. To prepare the branch and commit locally without publishing anything, run the same command without `--push --pr`. Nothing reaches GitHub until both flags are passed.
4. To review the change yourself before committing:
   ```bash
   # standalone clone, sibling DevOps
   python ../DevOps/scripts/rov.py library validate
   ```
   ```bash
   # library root inside a board submodule
   python ../../.pcb-devops-cache/scripts/rov.py library validate
   ```
   ```bash
   git status --short
   git diff --stat
   ```
5. From the Library Manager GUI, the same action is **Create Pull Request**, which calls `library contribute --name MPN --category Category --push --pr` for you. **Git Sync** calls `library sync`. Neither one pushes `master`.

### Step 7: Pull Request & Submodule Update
1. Once the automated library CI check passes, merge the PR into `master`.
2. Boards pick the change up through a reviewable update pull request. Run the local equivalent from the board repository root, where the board's copy of the platform tools lives:
   ```bash
   python .pcb-devops-cache/scripts/rov.py board sync-library
   ```
   It is a dry run: it prints the current commit, the target commit, and the changed library files without touching anything.
3. To apply the plan, review the printed change, then run:
   ```bash
   python .pcb-devops-cache/scripts/rov.py board sync-library --apply --branch chore/library-update --push --pr
   ```
   It requires a clean board worktree and a clean submodule. A dirty worktree or a diverged remote is reported as `BLOCKED`, not forced through.
4. Merge the resulting `chore/library-update` pull request in your board repository. The scheduled workflow in your board does this for you, and no command ever pushes your working branch directly.

   Note the two command families are not interchangeable. `rov library sync`
   updates this library repository and is meant to be run from the library root.
   `rov board sync-library` updates a board's submodule pointer and is meant to
   be run from the board root. Running the **bare** form of `library sync` from
   a board root would resolve the library to the board itself and try to
   fast-forward the board's own branch; the explicit form
   `library sync --library-dir libs/purdue-rov-kicad-lib` is safe from a board
   root because it names the library unambiguously.

---

## How to Import Symbols Downloaded Online

If you downloaded a symbol from Ultra Librarian, SnapEDA, or SamacSys, it will come as a standalone `.kicad_sym` file. Follow one of the methods below to merge it into one of the categorized `.kicad_sym` files.

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
    *   Scroll to find the appropriate categorized library (e.g. `rov_logic`, `rov_power`).
    *   Right-click the chosen library and click **Paste Symbol**.
4.  **Enrich Properties**:
    *   Double-click the pasted symbol to open its properties.
    *   Populate the **6 mandatory fields** (`Category`, `MPN`, `Manufacturer`, `DigiKey`, `Datasheet`, `Temp_Range`) and make sure the **Footprint** field points to `ROV_Footprints:[footprint_name]`. Click the `+` button to add any missing fields.
    *   Click **Save**.
5.  **Remove the Temporary Library**:
    *   Go back to **Preferences ➔ Manage Symbol Libraries** and remove the `temp_download` entry so your catalog stays clean.

### Method B: Text Editor Copy-Paste (Fast / Power-User Method)
Because KiCad symbols are stored as nested text blocks inside a single file, you can merge them using any text editor:
1.  Open the downloaded `.kicad_sym` file in your text editor (e.g. VS Code).
2.  Locate the symbol block starting with `(symbol "PART_NAME" ...)` and select the entire block (including all its contents and matching closing parentheses). **Copy it**.
3.  Open the appropriate categorized `Symbols/rov_*.kicad_sym` file in your text editor.
4.  Scroll to the very bottom of the file. Right before the final closing parenthesis `)` of the library, paste your copied symbol block.
5.  Open KiCad's **Symbol Editor**, load the library, verify the symbol loads correctly, add the 6 mandatory fields, and click **Save**.

---

## Footprint Design & Reflow Best Practices

When designing footprints, follow these industry standards to ensure high assembly yield:

### 1. Solder Paste Aperture Optimization (Thermal Pads)
For ICs with large central ground/thermal pads and large SMD power pads:
*   **The Issue**: Applying a solid layer of solder paste over a large area causes the component to "float" on liquid solder during reflow, leading to pins lifting, misaligning, or bridging.
*   **The Solution**: Go to pad properties in the Footprint Editor and set a custom **Solder Paste Clearance Override**. Divide the paste aperture into a grid of smaller squares, targeting **50-80% total copper coverage** with gaps in between. This allows outgassing channels for reflow volatiles and keeps the component flat.

### 2. Silk-to-Solder Mask Clearances
*   Ensure all silkscreen elements (drawings, outlines, refdes labels) are kept at least **0.2mm** away from open copper pads to prevent ink from contaminating the solder joints.
