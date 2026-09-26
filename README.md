# Purdue ROV Central KiCad Library

Central KiCad library containing symbols, footprints, 3D models, and reusable
design blocks for Purdue ROV hardware projects.

This repository is the approved source for every board. `master` is protected:
changes land through a reviewable branch and pull request, and no tool here
pushes to it directly.

## Library Structure

Components are organized into six standard categories:

```
purdue-rov-kicad-lib/
├── Symbols/
│   ├── rov_passives.kicad_sym      # Resistors, capacitors, inductors, crystals
│   ├── rov_power.kicad_sym         # Regulators, buck/boost converters, MOSFETs, diodes
│   ├── rov_logic.kicad_sym         # MCUs, logic ICs, op-amps, drivers, transceivers
│   ├── rov_connectors.kicad_sym    # Terminals, XT60/XT30, headers, USB, JST
│   ├── rov_sensors.kicad_sym       # IMUs, pressure/temperature sensors, cameras
│   └── rov_mech.kicad_sym          # Mounting holes, standoffs, test points
├── Footprints/
│   ├── rov_passives.pretty/
│   ├── rov_power.pretty/
│   ├── rov_logic.pretty/
│   ├── rov_connectors.pretty/
│   ├── rov_sensors.pretty/
│   └── rov_mech.pretty/
├── 3D_Models/                      # STEP and WRL 3D CAD files
├── Design_Blocks/                  # Reusable schematic & PCB sub-circuits
└── scripts/                        # Import, linting, and maintenance utilities
```

Per-part source files are canonical. The six category libraries are generated,
validated, and committed, so existing KiCad library tables keep working.

## Required Symbol Fields

Every symbol must include these fields to pass linting:

| Field | Description | Example |
| :--- | :--- | :--- |
| `Category` | One of: `Passives`, `Power`, `Logic`, `Connectors`, `Sensors`, `Mech` | `Power` |
| `MPN` | Exact Manufacturer Part Number | `TPS54302DDCR` |
| `Manufacturer` | Manufacturer name | `Texas Instruments` |
| `DigiKey` | DigiKey part number or SKU | `296-48767-1-ND` |
| `Datasheet` | Direct PDF URL (`http://` or `https://`) | `https://www.ti.com/lit/ds/symlink/tps54302.pdf` |
| `Temp_Range` | Operating temperature range | `-40°C to 125°C` |

## Managing & Adding Components (GUI)

Launch the all-in-one component manager to browse, search, edit, import, delete,
and validate parts:

- **Windows:** Double-click `LIBRARY_MANAGER.bat`
- **macOS / Linux:** Run `./LIBRARY_MANAGER.sh` (or
  `python3 scripts/library_manager_gui.py`)

### Features

- **Live search and filtering:** search across MPN, Manufacturer, Description,
  and Category.
- **One-click part ingestion:** add a part to import `.zip` downloads from
  SnapEDA, Ultra Librarian, DigiKey, or LCSC. Symbols, footprints (`.kicad_mod`),
  and 3D models are extracted automatically.
- **Downloads watcher:** optional background watcher that detects newly
  downloaded CAD files in your `~/Downloads` folder.
- **In-place field editor:** edit and save any mandatory symbol metadata, or
  change categories in one click.
- **Safe component deletion:** remove unused symbols from `.kicad_sym` category
  files.
- **One-click linter validation:** verify compliance across all six category
  libraries before you propose a change.
- **Git sync:** fetch and fast-forward this checkout. It never pushes.

## Command Line

The CLI lives in the shared platform tools, in the separate `pcb-devops`
repository. The library calls it through `scripts/rov_bridge.py`, so the GUI and
the CLI run the same validation and the same Git safety rules.

### Finding the shared CLI

This repository does not contain a `LAUNCH_KICAD` launcher; that lives in board
repositories. `scripts/rov_bridge.py`, which the GUI uses, looks for the DevOps
checkout in this order, and the first candidate that really contains
`scripts/rov.py` wins:

1. the `ROV_DEVOPS_DIR` environment variable, which always wins;
2. `.pcb-devops-cache/` inside the library directory;
3. a sibling `../DevOps`, the multi-repository workspace layout;
4. a sibling `../pcb-devops`, the older single-repository sibling name.

`ROV_DEVOPS_DIR` is the only setting that works in every layout, so set it if the
others do not resolve. Note one known gap: when this library is a board
submodule, the board's `LAUNCH_KICAD` puts its cache in the **board root**, one
level above `libs/`, while candidate 2 looks inside the library directory. The
GUI therefore does not find a board's cache in that layout, and `ROV_DEVOPS_DIR`
is required. Running the CLI yourself, as below, is unaffected.

### Running the commands

`--library-dir` defaults to the current directory, so **the directory you run
from decides both which library is used and which path reaches the CLI.** Pick
the case that matches where you are.

#### From this repository's root, with a sibling `../DevOps` checkout

This is the standalone-clone layout. This is the only place `../DevOps` is
correct.

macOS / Linux:

```bash
python ../DevOps/scripts/rov.py library validate
python ../DevOps/scripts/rov.py library build
python ../DevOps/scripts/rov.py library list
python ../DevOps/scripts/rov.py library search PKU5511ESI
python ../DevOps/scripts/rov.py library sync
python ../DevOps/scripts/rov.py library contribute --name PKU5511ESI --category Power --push --pr
```

Windows:

```powershell
py -3 ..\DevOps\scripts\rov.py library validate
py -3 ..\DevOps\scripts\rov.py library sync
```

#### From a board repository root, after LAUNCH_KICAD has run once

A board keeps its own copy of the platform tools in `.pcb-devops-cache/` at the
board root. That is the same path the launcher and the generated
`.rov-hooks/pre-commit` use, and it needs no sibling checkout:

macOS / Linux:

```bash
python .pcb-devops-cache/scripts/rov.py library validate --library-dir libs/purdue-rov-kicad-lib
```

Windows:

```powershell
py -3 .pcb-devops-cache\scripts\rov.py library validate --library-dir libs\purdue-rov-kicad-lib
```

There is no `../DevOps` from a board root. A board lives at
`KiCad/Boards/<board>`, so `../DevOps` would mean `KiCad/Boards/DevOps`, which
does not exist.

#### From the library root inside a board submodule

The board's cache is two levels up from `libs/purdue-rov-kicad-lib`, so:

```bash
python ../../.pcb-devops-cache/scripts/rov.py library validate
```

#### With ROV_DEVOPS_DIR set

Use the absolute path it points at. This is the form that always works:

```bash
python "$ROV_DEVOPS_DIR/scripts/rov.py" library validate
```

```powershell
py -3 "$env:ROV_DEVOPS_DIR\scripts\rov.py" library validate
```

### Running library sync from a board root

`library sync` fetches and fast-forwards whatever directory it is given, because
`--library-dir` defaults to the current directory. That makes the two forms
below behave very differently, so treat them as different commands:

- **Unsafe from a board root: the bare form.** `library sync` with no
  `--library-dir` run from a board root resolves the library to the board itself
  and tries to fast-forward the board's own branch. Do not run it this way.
- **Safe from a board root: the explicit form.** Passing
  `--library-dir libs/purdue-rov-kicad-lib` names the library unambiguously, so
  the command acts on the library and leaves the board alone:

  ```bash
  python .pcb-devops-cache/scripts/rov.py library sync --library-dir libs/purdue-rov-kicad-lib
  ```

- **Safest of all: run it from the library checkout**, where the default
  resolves correctly and `--library-dir` is not needed.

For a board's library submodule, prefer the board-side command
`board sync-library` instead. It updates the board's submodule pointer through a
reviewable pull request and never touches the library checkout.

### What the commands do

| Command | Behavior |
| :--- | :--- |
| `library validate` | Runs the symbol metadata linter. A non-zero linter exit is a `FAIL`. |
| `library build` | Rebuilds the generated category symbol libraries. |
| `library list` / `library search` | Prints `name`, `category`, `MPN`, `manufacturer` as tab-separated rows. |
| `library sync` | Requires a clean worktree, then fetches and fast-forwards. It never pushes. Always confirm which directory it resolved before letting it run. |
| `library import` | Runs `scripts/import_part.py`. |
| `library contribute` | Validates, creates an `add-part-*` branch, stages only the four library directories, commits, and with `--push --pr` publishes the branch and opens a pull request. |
| `library gui` | Opens the Library Manager GUI. |

### CLI import

```bash
python3 scripts/import_part.py --symbol <path-to-sym> --footprint <path-to-mod> --category Power
```

`import_part.py` validates and then prints the exact `library contribute`
command to run. It does not commit or push anything.

## Safe Contribution Flow

Contributions always follow the same path, from either interface:

1. Import or select the part.
2. Choose its category.
3. Normalize the symbol, footprint, and 3D-model links.
4. Validate the required metadata and file structure.
5. Review the diff and the validation report.
6. Create a feature branch.
7. Stage only `Symbols/`, `Footprints/`, `3D_Models/`, and `Design_Blocks/`.
8. With `--push --pr`, publish the branch and open a pull request.

Rules that both interfaces obey:

- Validation runs before the commit, and an unrelated change anywhere else in
  the worktree is refused rather than swept into the commit.
- The contribution branch is created from the protected `master` base, not from
  a previous `add-part-*` branch, so contributions never stack.
- The push names the new branch only. `master` is never committed to and never
  pushed.
- The pull request is opened only when `--push` and `--pr` are both given.

`library sync` is the only Git action in the GUI. It fetches or fast-forwards a
clean checkout and stops on a dirty worktree or an unreachable remote.

## Exit codes

| Code | Meaning |
| :--- | :--- |
| `0` | No `FAIL` and no `BLOCKED`. |
| `1` | At least one check reported `FAIL`. |
| `2` | No `FAIL`, but at least one check was `BLOCKED`. |

`BLOCKED` means a prerequisite is missing or unreachable, for example a dirty
worktree or an offline remote. It is an action for a human, not a broken part.

## Known Follow-Ups

Recorded, not fixed. Each needs owner approval before anyone changes it.

1. **Legacy tracked `.githooks/pre-commit` files may still reach the network.**
   Boards and the board template that predate this platform carry a tracked
   `.githooks/` hook that runs `git fetch`/`git pull` against the library
   submodule and can stage a submodule change during an ordinary `git commit`.
   New boards get the untracked `.rov-hooks/` hook instead, which only validates
   and never syncs. The legacy files are teammate-authored and were left in
   place; removing or rewriting them is a separate, owner-approved change. Until
   then, use `--no-verify` if a hook surprises you, and check `git status` before
   you commit.
2. **Board update wrappers rely on repository default permissions.** The
   reusable `update-library.yml` declares least-privilege `contents: write` and
   `pull-requests: write`, but the thin wrappers in each board's
   `auto-update-submodule.yml` do not declare a `permissions:` block, so they
   inherit the repository default. Adding explicit blocks would mean rewriting
   eight already-correct commits; it is queued as an owner-approved follow-up.

## Local Validation

The linter on its own:

```bash
python3 scripts/linter_validator.py Symbols/*.kicad_sym
```

Or through the shared CLI, which is what CI and the GUI use. Run this from the
root of this repository, with a sibling `../DevOps` checkout:

```bash
python ../DevOps/scripts/rov.py library validate
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the step-by-step part workflow, symbol
pin conventions, footprint pad geometry, and thermal aperture masking.
