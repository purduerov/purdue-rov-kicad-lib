# Purdue ROV Central KiCad Library

This repository contains the unified, team-wide source of truth for symbols, footprints, 3D models, and Design Blocks used by Purdue ROV.

## Directory Structure

```
purdue-rov-kicad-lib/
├── Symbols/
│   └── rov_parts.kicad_sym       # Central Symbol Library file
├── Footprints/
│   └── rov_parts.pretty/         # Central Footprint Library directory
│       └── *.kicad_mod           # Individual Footprints
├── 3D_Models/                    # 3D models (.step/.wrl) for footprints
└── Design_Blocks/                # Reusable sub-circuits (e.g. buck converters)
```

## Adding Components

When creating or importing new symbols or footprints:
1. Ensure the symbol matches standard naming conventions.
2. Every symbol **must** have the following custom fields populated:
   - `MPN` (Manufacturer Part Number)
   - `DigiKey` (DigiKey Part Number / SKU)
   - `Datasheet` (URL link to the PDF datasheet)
3. Ensure pins are matched exactly to the physical footprint.
4. Keep 3D step models under `3D_Models/` and link them using relative paths (e.g., `${KICAD_PROJECT_DIR}/libs/purdue-rov-kicad-lib/3D_Models/part.step`).
5. **Solder Paste & Stencil Optimization**: For ICs with large central ground pads (thermal pads) and fine-pitch components, set a custom **Solder Paste Clearance Override** in the pad settings. Divide large paste apertures into a grid of smaller apertures (50-80% coverage) to prevent parts floating or bridging during SMD reflow.


## Contributions

1. Create a branch for your component addition: `git checkout -b feature/add-[part-name]`.
2. Add your parts using KiCad symbol and footprint editors.
3. Commit your changes and open a Pull Request.
4. Once reviewed and approved by the Electrical leads, it will be merged into the `main` branch.
