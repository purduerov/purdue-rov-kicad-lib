#!/usr/bin/env python3
"""
Test suite validating that all library tooling scripts run safely under
restrictive non-UTF-8 console encodings (e.g. ASCII, cp1252) without crashing.
"""

import os
import sys
import subprocess
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BASE_DIR / "scripts"
SYMBOLS_DIR = BASE_DIR / "Symbols"

class TestCodepageSafety(unittest.TestCase):
    def _run_with_encoding(self, script_name: str, args: list, encoding_env: str):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = encoding_env
        env["PYTHONUTF8"] = "0"
        cmd = [sys.executable, str(SCRIPTS_DIR / script_name)] + args
        res = subprocess.run(
            cmd,
            cwd=str(BASE_DIR),
            env=env,
            capture_output=True,
            text=True,
            encoding=encoding_env,
            errors="replace"
        )
        self.assertNotIn("UnicodeEncodeError", res.stderr, f"{script_name} raised UnicodeEncodeError with PYTHONIOENCODING={encoding_env}")
        self.assertNotIn("UnicodeDecodeError", res.stderr, f"{script_name} raised UnicodeDecodeError with PYTHONIOENCODING={encoding_env}")
        return res

    def test_linter_validator_ascii_encoding(self):
        """Verify linter_validator executes cleanly under strict ASCII encoding."""
        sym_files = [str(p) for p in SYMBOLS_DIR.glob("*.kicad_sym")]
        res = self._run_with_encoding("linter_validator.py", sym_files, "ascii")
        self.assertEqual(res.returncode, 0, f"linter_validator failed with: {res.stderr}\n{res.stdout}")
        self.assertIn("[OK]", res.stdout)

    def test_linter_validator_cp1252_encoding(self):
        """Verify linter_validator executes cleanly under Windows cp1252 encoding."""
        sym_files = [str(p) for p in SYMBOLS_DIR.glob("*.kicad_sym")]
        res = self._run_with_encoding("linter_validator.py", sym_files, "cp1252")
        self.assertEqual(res.returncode, 0, f"linter_validator failed with: {res.stderr}\n{res.stdout}")
        self.assertIn("[OK]", res.stdout)

    def test_build_symbol_libs_ascii_encoding(self):
        """Verify build_symbol_libs compiles libraries cleanly under ASCII encoding."""
        res = self._run_with_encoding("build_symbol_libs.py", [], "ascii")
        self.assertEqual(res.returncode, 0, f"build_symbol_libs failed with: {res.stderr}\n{res.stdout}")
        self.assertIn("[OK]", res.stdout)

    def test_import_part_help_ascii_encoding(self):
        """Verify import_part CLI handles help display under ASCII encoding."""
        res = self._run_with_encoding("import_part.py", ["--help"], "ascii")
        self.assertEqual(res.returncode, 0, f"import_part --help failed with: {res.stderr}\n{res.stdout}")

    def test_test_e2e_flow_help_ascii_encoding(self):
        """Verify test_e2e_flow CLI handles help display under ASCII encoding."""
        res = self._run_with_encoding("test_e2e_flow.py", ["--help"], "ascii")
        self.assertEqual(res.returncode, 0, f"test_e2e_flow --help failed with: {res.stderr}\n{res.stdout}")

if __name__ == "__main__":
    unittest.main()
