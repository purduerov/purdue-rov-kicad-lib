#!/usr/bin/env python3
"""Bridge from the Purdue ROV library to the shared ``rov`` CLI.

``KiCad/Libraries`` and ``KiCad/DevOps`` are separate repositories, so the
library cannot import ``rov_core`` directly. This module is the whole of that
seam: it locates a DevOps checkout and runs its CLI with the current
interpreter. Git branch creation, commit, push, and pull-request creation stay
in ``KiCad/DevOps`` so the Library Manager never becomes a second implementation
of those rules and never publishes to the protected library branch itself.

The DevOps checkout is searched in this order:

1. the ``ROV_DEVOPS_DIR`` environment variable, which always wins,
2. ``<library_dir>/.pcb-devops-cache``, the copy a board's ``LAUNCH_KICAD`` run
   caches next to the library,
3. ``<library_dir>/../DevOps``, the multi-repository workspace layout,
4. ``<library_dir>/../pcb-devops``, the older single-repository sibling name.

A candidate only counts when it actually contains ``scripts/rov.py``, so a stale
or unrelated directory is skipped instead of being reported as a usable CLI.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# The environment override is the only supported way to point the Library
# Manager at a DevOps checkout in an unusual layout.
DEVOPS_ENV_VAR = "ROV_DEVOPS_DIR"

# Where ``LAUNCH_KICAD`` caches the platform scripts inside a board repository.
CACHE_DIR_NAME = ".pcb-devops-cache"

# The two sibling names a library checkout may live next to.
SIBLING_DIR_NAME = "DevOps"
LEGACY_DIR_NAME = "pcb-devops"

# The single shared entry point, relative to a DevOps checkout.
CLI_RELATIVE_PATH = Path("scripts") / "rov.py"

MISSING_CLI_HINT = (
    "Run LAUNCH_KICAD once, or set ROV_DEVOPS_DIR to the KiCad/DevOps checkout, "
    "then run this action again."
)


def devops_candidates(library_dir: Path) -> list[Path]:
    """Return the DevOps locations that are searched, in priority order.

    The order is the contract, so a cached or sibling checkout is never preferred
    over an explicit ``ROV_DEVOPS_DIR``.
    """
    root = Path(library_dir)
    configured = (os.environ.get(DEVOPS_ENV_VAR) or "").strip()
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured))
    candidates.append(root / CACHE_DIR_NAME)
    candidates.append(root.parent / SIBLING_DIR_NAME)
    candidates.append(root.parent / LEGACY_DIR_NAME)
    return candidates


def resolve_devops_dir(library_dir: Path) -> Path:
    """Return the DevOps checkout that owns the shared CLI.

    Raises ``FileNotFoundError`` listing every path that was checked, so a user
    can see exactly where the Library Manager looked before being told how to
    fix it.
    """
    candidates = devops_candidates(library_dir)
    for candidate in candidates:
        if (candidate / CLI_RELATIVE_PATH).is_file():
            return candidate
    checked = "\n".join(f"  {candidate / CLI_RELATIVE_PATH}" for candidate in candidates)
    raise FileNotFoundError(
        f"The Purdue ROV DevOps CLI was not found for {Path(library_dir)}.\n"
        f"Checked:\n{checked}\n{MISSING_CLI_HINT}"
    )


def run_rov(
    library_dir: Path,
    args: list[str],
    check: bool = False,
    devops_dir: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one ``rov`` command in ``library_dir`` and capture its output.

    The current interpreter is used directly and no shell is involved, so a part
    name or category is passed as a single argument and can never be interpreted
    by a shell. ``check`` is ``False`` by default so a caller can turn a non-zero
    exit code into its own ``PASS``/``BLOCKED`` report instead of an exception.
    """
    devops = Path(devops_dir) if devops_dir is not None else resolve_devops_dir(library_dir)
    command = [
        sys.executable,
        str(devops / CLI_RELATIVE_PATH),
        *[str(argument) for argument in args],
    ]
    return subprocess.run(
        command,
        cwd=str(library_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
    )
