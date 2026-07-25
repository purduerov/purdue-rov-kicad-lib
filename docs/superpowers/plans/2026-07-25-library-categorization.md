# KiCad Library Categorization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize `purdue-rov-kicad-lib` symbols and footprints into 6 standard category libraries (`rov_passives`, `rov_power`, `rov_logic`, `rov_connectors`, `rov_sensors`, `rov_mech`), update the automated linter to enforce a mandatory `Category` property, update library tables, create a migration script, and update team documentation.

**Architecture:** Split the monolithic `rov_parts.kicad_sym` file and `rov_parts.pretty` directory into 6 targeted category libraries. Create a standalone Python migration script (`scripts/categorize_library.py`) to parse S-expression `.kicad_sym` files, inject `Category` properties, and output category-specific `.kicad_sym` files and `.pretty` directories. Update `scripts/linter_validator.py` to validate `Category` and update `sym-lib-table_EXAMPLE` & `fp-lib-table_EXAMPLE`.

**Tech Stack:** Python 3.x, KiCad 7/8/9 S-expression syntax (`.kicad_sym`, `.kicad_mod`), GitHub Actions CI.

## Global Constraints

- **Allowed Categories:** `Passives`, `Power`, `Logic`, `Connectors`, `Sensors`, `Mech`
- **Mandatory Symbol Fields:** `MPN`, `Manufacturer`, `Datasheet`, `Temp_Range`, `DigiKey`, `Category`
- **Backward Compatibility:** Preserved symbol and footprint names within category libraries so existing designs can easily remap.

---

### Task 1: Create Automated Migration Script (`scripts/categorize_library.py`)

**Files:**
- Create: `purdue-rov-kicad-lib/scripts/categorize_library.py`
- Test: Run python script on `purdue-rov-kicad-lib/Symbols/rov_parts.kicad_sym`

**Interfaces:**
- Consumes: Monolithic `Symbols/rov_parts.kicad_sym` and `Footprints/rov_parts.pretty/`
- Produces: 
  - `Symbols/rov_passives.kicad_sym`, `Symbols/rov_power.kicad_sym`, `Symbols/rov_logic.kicad_sym`, `Symbols/rov_connectors.kicad_sym`, `Symbols/rov_sensors.kicad_sym`, `Symbols/rov_mech.kicad_sym`
  - `Footprints/rov_passives.pretty/`, `Footprints/rov_power.pretty/`, `Footprints/rov_logic.pretty/`, `Footprints/rov_connectors.pretty/`, `Footprints/rov_sensors.pretty/`, `Footprints/rov_mech.pretty/`

- [ ] **Step 1: Write `categorize_library.py` script**

Create `purdue-rov-kicad-lib/scripts/categorize_library.py` with parsing logic to categorize symbols based on keywords/names and generate category `.kicad_sym` files and `.pretty` folders.

- [ ] **Step 2: Execute migration script**

Run: `python3 scripts/categorize_library.py` from `purdue-rov-kicad-lib/`
Expected: Output files created under `Symbols/` and directories under `Footprints/`.

- [ ] **Step 3: Commit migration script and generated category libraries**

```bash
git add scripts/categorize_library.py Symbols/ Footprints/
git commit -m "feat: migrate symbol and footprint libraries into 6 categories"
```

---

### Task 2: Update Linter Validator (`scripts/linter_validator.py`)

**Files:**
- Modify: `purdue-rov-kicad-lib/scripts/linter_validator.py`

**Interfaces:**
- Consumes: All `.kicad_sym` files under `Symbols/`
- Produces: Exit code 0 on pass, exit code 1 on fail with detailed missing field / category error output

- [ ] **Step 1: Update `linter_validator.py` to enforce `Category`**

Update `MANDATORY_FIELDS` list in `scripts/linter_validator.py` to include `"Category"` and validate that its value is one of `["Passives", "Power", "Logic", "Connectors", "Sensors", "Mech"]`. Also support passing directory or multiple `.kicad_sym` files as arguments.

- [ ] **Step 2: Run linter on all category libraries**

Run: `python3 scripts/linter_validator.py Symbols/*.kicad_sym`
Expected: `✅ Library verified. All components compliant with structural guidelines.`

- [ ] **Step 3: Commit linter updates**

```bash
git add scripts/linter_validator.py
git commit -m "feat: update linter validator to enforce Category property"
```

---

### Task 3: Update `sym-lib-table_EXAMPLE` & `fp-lib-table_EXAMPLE`

**Files:**
- Modify: `purdue-rov-kicad-lib/sym-lib-table_EXAMPLE`
- Modify: `purdue-rov-kicad-lib/fp-lib-table_EXAMPLE`

**Interfaces:**
- Consumes: Category files in `Symbols/` and `Footprints/`
- Produces: Valid KiCad 7/8/9 library table configuration files

- [ ] **Step 1: Update `sym-lib-table_EXAMPLE`**

Include entries for `rov_passives`, `rov_power`, `rov_logic`, `rov_connectors`, `rov_sensors`, and `rov_mech`.

- [ ] **Step 2: Update `fp-lib-table_EXAMPLE`**

Include entries for `rov_passives`, `rov_power`, `rov_logic`, `rov_connectors`, `rov_sensors`, and `rov_mech`.

- [ ] **Step 3: Commit updated library tables**

```bash
git add sym-lib-table_EXAMPLE fp-lib-table_EXAMPLE
git commit -m "docs: update sym-lib-table and fp-lib-table example files for categories"
```

---

### Task 4: Update Documentation (`README.md` & `CONTRIBUTING.md`)

**Files:**
- Modify: `purdue-rov-kicad-lib/README.md`
- Modify: `purdue-rov-kicad-lib/CONTRIBUTING.md`

**Interfaces:**
- Consumes: Updated library organization and linter rules
- Produces: Clear onboarding and contribution instructions for Purdue ROV electrical team members

- [ ] **Step 1: Update `README.md`**

Reflect the new 6-category directory layout, list mandatory fields including `Category`, and update linter commands.

- [ ] **Step 2: Update `CONTRIBUTING.md`**

Add instructions on choosing the right category library when adding a symbol/footprint.

- [ ] **Step 3: Commit documentation updates**

```bash
git add README.md CONTRIBUTING.md
git commit -m "docs: update README and CONTRIBUTING with category rules"
```
