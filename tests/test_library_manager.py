#!/usr/bin/env python3
"""
Unit and Integration tests for Library Manager parser, editor, and operations.
"""

import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

# Add scripts directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

from library_manager_gui import LibraryParser, CATEGORIES, CATEGORY_FILES
import import_part

class TestLibraryManager(unittest.TestCase):
    def setUp(self):
        self.test_sym_name = "__TEST_COMPONENT_TMP__"
        self.test_raw_sym = f"""(symbol "{self.test_sym_name}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
    (property "Reference" "U" (id 0) (at 0 0 0) (effects (font (size 1.27 1.27))))
    (property "Value" "{self.test_sym_name}" (id 1) (at 0 0 0) (effects (font (size 1.27 1.27))))
    (property "Footprint" "rov_power:TEST_FP" (id 2) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "Datasheet" "https://example.com/datasheet.pdf" (id 3) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "Category" "Power" (id 4) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "MPN" "TEST-1234" (id 5) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "Manufacturer" "TestCorp" (id 6) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "DigiKey" "TEST-ND" (id 7) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "Temp_Range" "-40°C to 125°C" (id 8) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "Description" "Temporary test component" (id 9) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (symbol "{self.test_sym_name}_0_0"
      (rectangle (start -5.08 5.08) (end 5.08 -5.08) (stroke (width 0.254)) (fill (type background)))
      (pin power_in line (at 0 7.62 270) (length 2.54) (name "VIN" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      (pin power_out line (at 0 -7.62 90) (length 2.54) (name "VOUT" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
    )
  )"""

    def tearDown(self):
        # Cleanup test symbol from all categories
        for cat in CATEGORIES:
            LibraryParser.delete_symbol(self.test_sym_name, cat)

    def test_load_all_symbols(self):
        syms = LibraryParser.load_all_symbols()
        self.assertIsInstance(syms, dict)
        self.assertIn("XT60-M", syms)
        self.assertEqual(syms["XT60-M"]["category"], "Connectors")
        self.assertEqual(syms["XT60-M"]["properties"]["Manufacturer"], "AMASS")

    def test_insert_and_load_symbol(self):
        # Insert into Power
        LibraryParser.insert_symbol("Power", self.test_raw_sym)
        syms = LibraryParser.load_all_symbols()
        self.assertIn(self.test_sym_name, syms)
        self.assertEqual(syms[self.test_sym_name]["category"], "Power")
        self.assertEqual(syms[self.test_sym_name]["properties"]["MPN"], "TEST-1234")
        self.assertEqual(syms[self.test_sym_name]["properties"]["Manufacturer"], "TestCorp")

    def test_edit_symbol_properties(self):
        LibraryParser.insert_symbol("Power", self.test_raw_sym)
        syms = LibraryParser.load_all_symbols()
        
        # Modify properties
        updated_props = dict(syms[self.test_sym_name]["properties"])
        updated_props["MPN"] = "TEST-9999-NEW"
        updated_props["Manufacturer"] = "UpdatedManufacturer"
        
        LibraryParser.save_symbol(self.test_sym_name, "Power", "Power", updated_props, syms[self.test_sym_name]["raw_text"])
        
        # Verify changes persisted
        reloaded_syms = LibraryParser.load_all_symbols()
        self.assertEqual(reloaded_syms[self.test_sym_name]["properties"]["MPN"], "TEST-9999-NEW")
        self.assertEqual(reloaded_syms[self.test_sym_name]["properties"]["Manufacturer"], "UpdatedManufacturer")

    def test_move_symbol_category(self):
        # Insert into Power
        LibraryParser.insert_symbol("Power", self.test_raw_sym)
        syms = LibraryParser.load_all_symbols()
        self.assertEqual(syms[self.test_sym_name]["category"], "Power")

        # Move to Sensors
        updated_props = dict(syms[self.test_sym_name]["properties"])
        LibraryParser.save_symbol(self.test_sym_name, "Power", "Sensors", updated_props, syms[self.test_sym_name]["raw_text"])

        # Verify moved
        reloaded_syms = LibraryParser.load_all_symbols()
        self.assertEqual(reloaded_syms[self.test_sym_name]["category"], "Sensors")
        
        # Check power sym file doesn't have it
        power_file = BASE_DIR / "Symbols" / "rov_power.kicad_sym"
        with open(power_file, 'r', encoding='utf-8') as f:
            self.assertNotIn(self.test_sym_name, f.read())

        # Check sensors sym file has it
        sensor_file = BASE_DIR / "Symbols" / "rov_sensors.kicad_sym"
        with open(sensor_file, 'r', encoding='utf-8') as f:
            self.assertIn(self.test_sym_name, f.read())

    def test_delete_symbol(self):
        LibraryParser.insert_symbol("Power", self.test_raw_sym)
        self.assertIn(self.test_sym_name, LibraryParser.load_all_symbols())

        LibraryParser.delete_symbol(self.test_sym_name, "Power")
        self.assertNotIn(self.test_sym_name, LibraryParser.load_all_symbols())

    def test_insert_into_power_preserves_kicad_validity(self):
        # Specifically test that inserting into Power does not cause it to disappear or corrupt
        from kicad_sym_utils import validate_sexpr
        LibraryParser.insert_symbol("Power", self.test_raw_sym)
        
        power_file = BASE_DIR / "Symbols" / "rov_power.kicad_sym"
        with open(power_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        is_valid, err = validate_sexpr(content)
        self.assertTrue(is_valid, f"Power library became invalid S-expression: {err}")
        self.assertNotIn("#", content, "Illegal comment character found in power library")


class TestImportPartContributionHint(unittest.TestCase):
    """The importer must never publish to a protected branch itself.

    ``import_part.py`` writes library files and runs the metadata linter; turning
    those local changes into a branch, a commit, and a pull request is the job of
    ``rov library contribute``. These tests pin that division of work.
    """

    def test_importer_never_runs_git_publishing_commands(self):
        source = Path(import_part.__file__).read_text(encoding="utf-8")
        for forbidden in ('"git", "push"', '"git", "commit"', '"git", "add"', '"git", "checkout"'):
            self.assertNotIn(
                forbidden, source, f"import_part.py must not run {forbidden}"
            )

    def test_hint_prints_concrete_rov_command(self):
        output = self._hint_output(devops="C:/devops/DevOps")
        self.assertIn("Library changes validated. Run:", output)
        self.assertIn("C:/devops/DevOps", output.replace("\\", "/"))
        self.assertIn(
            "library contribute --name TPS54302 --category Power --push --pr", output
        )

    def test_hint_explains_how_to_locate_devops_when_unresolved(self):
        output = self._hint_output(devops=None)
        self.assertIn("Set ROV_DEVOPS_DIR or run LAUNCH_KICAD once", output)
        self.assertIn("rov library contribute --push --pr", output)

    def _hint_output(self, devops):
        """Return the printed hint with the DevOps resolver patched."""

        def fake_resolve(_library_dir):
            if devops is None:
                raise FileNotFoundError("no DevOps checkout found")
            return Path(devops)

        buffer = io.StringIO()
        with patch.object(import_part.rov_bridge, "resolve_devops_dir", fake_resolve):
            with redirect_stdout(buffer):
                import_part.print_contribution_hint("TPS54302", "Power")
        return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
