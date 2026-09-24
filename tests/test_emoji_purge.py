#!/usr/bin/env python3
"""
Regression test suite ensuring zero emojis or decorative non-ASCII glyphs
exist in any library tooling scripts.
"""

import os
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"

# Degree symbol (\u00b0) and plus-minus (\u00b1) are standard technical engineering symbols in datasheets
ALLOWED_NON_ASCII = {"\u00b0", "\u00b1"}

class TestEmojiPurge(unittest.TestCase):
    def test_no_emojis_in_scripts(self):
        """Scans all python files in scripts/ for emojis or prohibited non-ASCII characters."""
        violations = []
        py_files = sorted(SCRIPTS_DIR.glob("*.py"))
        self.assertTrue(len(py_files) > 0, "No script files found to audit")

        for py_file in py_files:
            rel_path = py_file.relative_to(BASE_DIR)
            with open(py_file, "r", encoding="utf-8", errors="replace") as f:
                for line_idx, line in enumerate(f, 1):
                    for char in line:
                        code = ord(char)
                        if code > 127 and char not in ALLOWED_NON_ASCII:
                            violations.append(
                                f"{rel_path}:{line_idx} - Prohibited char U+{code:04X} ({char}): {line.strip()}"
                            )

        if violations:
            msg = f"\nFound {len(violations)} prohibited non-ASCII / emoji glyphs:\n" + "\n".join(violations[:25])
            if len(violations) > 25:
                msg += f"\n... and {len(violations) - 25} more violations."
            self.fail(msg)

if __name__ == "__main__":
    unittest.main()
