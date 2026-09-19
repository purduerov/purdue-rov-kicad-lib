#!/usr/bin/env python3
"""
Unit and Integration tests for End-to-End Component Flow
Verifies component creation, rules validation, library compilation, and KiCad integration.
"""

import unittest
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

from test_e2e_flow import (
    find_kicad_cli,
    run_e2e_addition_test,
    verify_all_library_parts
)


class TestEndToEndComponentFlow(unittest.TestCase):
    def test_e2e_component_addition_lifecycle(self):
        """Simulate adding a component, compiling, verifying KiCad recognition, and teardown."""
        result = run_e2e_addition_test(
            part_name="TEST_E2E_AUTOMATION_IC",
            category="Power",
            keep=False,
            verbose=False
        )
        self.assertTrue(result["success"], f"E2E addition test failed: {result}")
        for step in result["steps"]:
            self.assertTrue(step["passed"], f"Step failed: {step['step']} - {step['details']}")

    def test_existing_library_parts_pass_kicad_cli(self):
        """Verify that all parts in the library pass KiCad S-expression and rendering checks."""
        result = verify_all_library_parts(verbose=False)
        self.assertTrue(result["all_passed"], f"Some library parts failed KiCad verification: {result}")
        self.assertGreaterEqual(result["total"], 2, "Expected at least 2 parts in library")


if __name__ == "__main__":
    unittest.main()
