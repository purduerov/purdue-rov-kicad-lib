import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

import kicad_sym_utils

SAMPLE_CORRECT_POWER_SYM = """(symbol "TPS62130RGTR" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
    (property "Reference" "U" (id 0) (at 0 5.08 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Value" "TPS62130RGTR" (id 1) (at 0 -5.08 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Footprint" "Package_DFN_QFN:QFN-16-1EP_3x3mm_P0.5mm_EP1.8x1.8mm" (id 2) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Datasheet" "https://www.ti.com/lit/ds/symlink/tps62130.pdf" (id 3) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Description" "3-17V 3A Step-Down Converter in 3x3 QFN" (id 4) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "MPN" "TPS62130RGTR" (id 5) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Manufacturer" "Texas Instruments" (id 6) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "DigiKey" "296-30230-1-ND" (id 7) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Category" "Power" (id 8) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Temp_Range" "-40°C to 125°C" (id 9) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (symbol "TPS62130RGTR_0_1"
      (rectangle (start -10.16 12.7) (end 10.16 -12.7)
        (stroke (width 0.254)) (fill (type background))
      )
    )
    (symbol "TPS62130RGTR_1_1"
      (pin power_in line (at -12.7 10.16 0) (length 2.54)
        (name "VIN" (effects (font (size 1.27 1.27))))
        (number "1" (effects (font (size 1.27 1.27))))
      )
      (pin power_out line (at 12.7 10.16 180) (length 2.54)
        (name "SW" (effects (font (size 1.27 1.27))))
        (number "2" (effects (font (size 1.27 1.27))))
      )
    )
  )"""

SAMPLE_RAW_DOWNLOADED_VENDOR_SYM = """(kicad_symbol_lib
	(version 20251024)
	(generator "kicad_symbol_editor")
	(generator_version "10.0")
	(symbol "TPS62130_RAW"
		(pin_names (offset 0.254))
		(in_bom yes)
		(on_board yes)
		(property "Reference" "U"
			(at 25.4 10.16 0)
			(effects (font (size 1.524 1.524)))
		)
		(property "Value" "TPS62130RGTR"
			(at 25.4 7.62 0)
			(effects (font (size 1.524 1.524)))
		)
		(property "Footprint" "QFN-16"
			(at 0 0 0)
			(effects (font (size 1.27 1.27)) hide)
		)
		(property "MF" "Texas Instruments"
			(at 0 0 0)
			(effects (font (size 1.27 1.27)) hide)
		)
		(property "Datasheet_URL" "https://www.ti.com/lit/ds/symlink/tps62130.pdf"
			(at 0 0 0)
			(effects (font (size 1.27 1.27)) hide)
		)
		(property "Digi-Key_Part_Number" "296-30230-1-ND"
			(at 0 0 0)
			(effects (font (size 1.27 1.27)) hide)
		)
		(property "ki_description" "High Efficiency 3A Step-Down Converter Regulator"
			(at 0 0 0)
			(effects (font (size 1.27 1.27)) hide)
		)
		(symbol "TPS62130_RAW_0_1"
			(rectangle (start -10.16 10.16) (end 10.16 -10.16) (stroke (width 0.254)))
		)
	)
)"""

class TestKiCadSymUtils(unittest.TestCase):
    def test_sexpr_validation(self):
        valid, err = kicad_sym_utils.validate_sexpr(SAMPLE_CORRECT_POWER_SYM)
        self.assertTrue(valid, f"Validation error: {err}")

        # Corrupted sexpr with extra parenthesis
        corrupt = SAMPLE_CORRECT_POWER_SYM + ")"
        valid, err = kicad_sym_utils.validate_sexpr(corrupt)
        self.assertFalse(valid)

    def test_extract_top_symbols(self):
        syms = kicad_sym_utils.extract_top_symbols(SAMPLE_CORRECT_POWER_SYM)
        self.assertEqual(len(syms), 1)
        self.assertEqual(syms[0][0], "TPS62130RGTR")
        self.assertIn('(symbol "TPS62130RGTR_1_1"', syms[0][1])

        syms_vendor = kicad_sym_utils.extract_top_symbols(SAMPLE_RAW_DOWNLOADED_VENDOR_SYM)
        self.assertEqual(len(syms_vendor), 1)
        self.assertEqual(syms_vendor[0][0], "TPS62130_RAW")

    def test_autofill_metadata(self):
        syms_vendor = kicad_sym_utils.extract_top_symbols(SAMPLE_RAW_DOWNLOADED_VENDOR_SYM)
        sym_name, raw = syms_vendor[0][0], syms_vendor[0][1]
        data = kicad_sym_utils.autofill_component_data(raw, sym_name)

        self.assertEqual(data["MPN"], "TPS62130RGTR") # Detected from Value
        self.assertEqual(data["Manufacturer"], "Texas Instruments") # Detected from MF
        self.assertEqual(data["DigiKey"], "296-30230-1-ND") # Detected from Digi-Key_Part_Number
        self.assertEqual(data["Datasheet"], "https://www.ti.com/lit/ds/symlink/tps62130.pdf") # Detected from Datasheet_URL
        self.assertEqual(data["Category"], "Power") # Predicted as Power (step-down converter regulator)
        self.assertEqual(data["Temp_Range"], "-40°C to 125°C") # Standard default

    def test_update_or_inject_properties(self):
        syms = kicad_sym_utils.extract_top_symbols(SAMPLE_RAW_DOWNLOADED_VENDOR_SYM)
        raw = syms[0][1]
        
        updates = {
            "Category": "Power",
            "MPN": "TPS62130RGTR",
            "Manufacturer": "Texas Instruments",
            "Datasheet": "https://www.ti.com/lit/ds/symlink/tps62130.pdf",
            "DigiKey": "296-30230-1-ND",
            "Temp_Range": "-40°C to 125°C",
            "Footprint": "rov_power:QFN-16"
        }

        updated = kicad_sym_utils.update_or_inject_properties(raw, updates)
        
        # S-expression must be strictly valid
        is_valid, err = kicad_sym_utils.validate_sexpr(updated)
        self.assertTrue(is_valid, f"Corrupted after property injection: {err}")

        # Check all properties are present
        props, _ = kicad_sym_utils.parse_symbol_properties(updated)
        for k, v in updates.items():
            self.assertEqual(props.get(k), v, f"Property {k} mismatch")

if __name__ == "__main__":
    unittest.main()
