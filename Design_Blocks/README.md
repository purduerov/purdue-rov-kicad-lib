# Central Purdue ROV Design Blocks

Design Blocks (modular circuit fragments) allow the team to reuse pre-routed, club-approved circuit topologies (e.g., regulators, transceivers, microcontrollers) across multiple designs. This reduces design time, prevents layout errors, and ensures power/signal integrity.

## Structure

```
Design_Blocks/
├── power_regulator_5v/
│   ├── power_regulator_5v.kicad_sch   # Schematic sheet of the block
│   ├── power_regulator_5v.kicad_pcb   # Layout template of the block
│   └── README.md                       # Description, pinout, specs, and layout advice
└── can_bus_transceiver/
    ├── can_bus_transceiver.kicad_sch
    ├── can_bus_transceiver.kicad_pcb
    └── README.md
```

## Guidelines for Creating Design Blocks

1. **Schematic Hierarchical Sheets**: 
   - Draw the circuit on a standalone sub-sheet.
   - Use **Hierarchical Labels** for all inputs, outputs, power, and ground connections to make integration straightforward.
2. **PCB Layout Topology**:
   - Route the block with optimal trace widths, via placements, and pour geometries (especially for switching regulators and differential signal lines).
   - Draw a boundary on a user/info layer to show the recommended footprint footprint/keepout area.
3. **Documentation**:
   - Provide a brief `README.md` with:
     - Input/Output operating limits (e.g., "Input: 7V - 24V, Output: 5V @ 2A").
     - Minimum clearance/keepout guidelines.
     - Stackup requirements (e.g., "Tested on 4-layer stackup with solid GND reference plane").
