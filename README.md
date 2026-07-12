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

## 1. Quick Setup (Git Submodule)

Run this command from the **root directory of your board's repository** to add the library as a project-relative submodule:

```bash
git submodule add git@github.com:purduerov/purdue-rov-kicad-lib.git

```

## 2. Linking Libraries to KiCad

Do **not** configure this via the KiCad GUI. To ensure portability across team members, add the library entries directly into your board's project files.

Open the `sym-lib-table` and `fp-lib-table` files located in the root of your board project repository and append the following S-expressions inside the main outer brackets:

### `sym-lib-table`

```lisp
(lib (name "rov_parts")(type "KiCad")(uri "${KIPRJMOD}/purdue-rov-kicad-lib/Symbols/rov_parts.kicad_sym")(options "")(descr "Purdue ROV Central Symbols"))

```

### `fp-lib-table`

```lisp
(lib (name "rov_parts")(type "KiCad")(uri "${KIPRJMOD}/purdue-rov-kicad-lib/Footprints/rov_parts.pretty")(options "")(descr "Purdue ROV Central Footprints"))

```

## 3. Rules for Component Creation

When contributing or linking new parts, follow these non-negotiable rules:

* **3D Model Paths (CRITICAL):** Never link absolute local paths (`C:\Users\...`). Always use the relative variable format:
`${KIPRJMOD}/purdue-rov-kicad-lib/3D_Models/<model-name>.step`
* **Required Symbol Fields:** Every new schematic symbol must contain these populated custom attributes:
* `MPN` (Manufacturer Part Number)
* `DigiKey` (DigiKey SKU)
* `Datasheet` (Direct PDF URL)


* **Thermal Pads:** For ICs with large central exposed ground pads, set a custom **Solder Paste Clearance Override** to break the single large paste aperture into a grid of smaller apertures (50–80% target coverage). This prevents component floating and bridging during reflow.

## 4. Updating the Library

### To Pull the Latest Library Changes:

If someone else added components and you need to fetch them into your current board project, run:

```bash
git submodule update --remote --merge

```

### To Push New Parts to the Library:

1. Navigate into the library directory: `cd purdue-rov-kicad-lib`
2. Checkout a branch: `git checkout -b feature/add-[part-name]`
3. Commit and push your changes to the *library* repository, then open a Pull Request.

---

### Where should the `*-lib-table` files live?

> [!IMPORTANT]
> **Put them directly in the individual board project repositories.**
