import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import linter_validator


SYM_TEMPLATE = """(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor)
  (symbol "TESTPART" (pin_names (offset 0.254)) (in_bom yes) (on_board yes)
    (property "Reference" "D" (id 0) (at 0 0 0)
      (effects (font (size 1.524 1.524)))
    )
    (property "Value" "TESTPART" (id 1) (at 0 0 0)
      (effects (font (size 1.524 1.524)))
    )
    (property "Footprint" "{footprint}" (id 2) (at 0 0 0)
      (effects (font (size 1.27 1.27) italic) hide)
    )
    (property "Datasheet" "https://example.com/testpart.pdf" (id 3) (at 0 0 0)
      (effects (font (size 1.27 1.27) italic) hide)
    )
    (property "MPN" "TESTPART" (id 9) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Manufacturer" "Test Mfr" (id 8) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Temp_Range" "-40C to 85C" (id 11) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Category" "Power" (id 12) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
  )
)
"""


class TestFootprintRefs(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.fp_dir = self.root / "Footprints"
        (self.fp_dir / "rov_power.pretty").mkdir(parents=True)
        self.sym_file = self.root / "test.kicad_sym"

    def tearDown(self):
        self._tmp.cleanup()

    def _write_sym(self, footprint):
        self.sym_file.write_text(
            SYM_TEMPLATE.format(footprint=footprint), encoding="utf-8"
        )

    def test_missing_footprint_is_reported(self):
        self._write_sym("rov_power:DOES_NOT_EXIST")
        errors = linter_validator.check_footprint_refs(
            str(self.sym_file), str(self.fp_dir)
        )
        self.assertTrue(
            any("DOES_NOT_EXIST" in err for err in errors),
            f"expected a missing-footprint error, got: {errors}",
        )

    def test_present_footprint_passes(self):
        (self.fp_dir / "rov_power.pretty" / "PRESENT.kicad_mod").write_text(
            "(footprint PRESENT)", encoding="utf-8"
        )
        self._write_sym("rov_power:PRESENT")
        self.assertEqual(
            linter_validator.check_footprint_refs(str(self.sym_file), str(self.fp_dir)),
            [],
        )


if __name__ == "__main__":
    unittest.main()
