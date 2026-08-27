# Purdue ROV Design Blocks

Reusable sub-circuits and layout snippets (regulators, transceivers, microcontrollers) for Purdue ROV hardware designs. Using verified blocks ensures consistent routing, correct pinouts, and tested power/signal integrity across boards.

## Directory Layout

Each design block lives in its own folder containing schematic, layout, and specification notes:

```
Design_Blocks/
├── <block_name>/
│   ├── <block_name>.kicad_sch   # Standalone hierarchical schematic sheet
│   ├── <block_name>.kicad_pcb   # Reference layout and copper routing
│   └── README.md                # Operating specs, pinout, and keepouts
```

## Guidelines for Adding Design Blocks

1. **Hierarchical Schematic**:
   - Draw the block on a standalone sheet.
   - Use hierarchical labels for all inputs, outputs, power rails, and grounds.
2. **Layout & Routing**:
   - Route with proven trace widths, via arrays, and copper pour geometry (especially for switching regulators and high-speed differential pairs).
   - Include a keepout or boundary outline on a documentation layer indicating recommended footprint area.
3. **Documentation (`README.md`)**:
   - Operating limits (input voltage range, maximum continuous current, switching frequency).
   - Thermal and layer stackup requirements (e.g. 4-layer stack with internal GND reference).
   - Any external component requirements (decoupling, pullups, filtering).
