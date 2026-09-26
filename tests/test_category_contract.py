import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import kicad_sym_utils
import linter_validator


class TestCategoryContract(unittest.TestCase):
    def test_allowed_categories_come_from_one_source(self):
        self.assertEqual(
            set(kicad_sym_utils.CATEGORIES), linter_validator.ALLOWED_CATEGORIES
        )

    def test_all_six_short_names_present(self):
        self.assertEqual(
            {"Passives", "Power", "Logic", "Connectors", "Sensors", "Mech"},
            linter_validator.ALLOWED_CATEGORIES,
        )
