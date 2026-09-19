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

    def test_get_standard_passive_symbol(self):
        props = {
            "MPN": "CRCW080510K0FKEA",
            "Manufacturer": "Vishay Dale",
            "Datasheet": "https://www.vishay.com/docs/20035/dcrcwe3.pdf",
            "DigiKey": "541-10.0KCCT-ND",
            "Temp_Range": "-55°C to 155°C",
            "Footprint": "rov_passives:R_0805_2012Metric",
            "Description": "RES 10K OHM 1% 1/8W 0805"
        }
        res_sym = kicad_sym_utils.get_standard_passive_symbol("R", "CRCW080510K0FKEA", props)
        
        is_valid, err = kicad_sym_utils.validate_sexpr(res_sym)
        self.assertTrue(is_valid, f"Generated standard passive symbol S-expr invalid: {err}")
        self.assertIn('(symbol "CRCW080510K0FKEA"', res_sym)
        self.assertIn('(symbol "CRCW080510K0FKEA_0_1"', res_sym)
        self.assertIn('(symbol "CRCW080510K0FKEA_1_1"', res_sym)

        parsed_props, _ = kicad_sym_utils.parse_symbol_properties(res_sym)
        self.assertEqual(parsed_props.get("MPN"), "CRCW080510K0FKEA")
        self.assertEqual(parsed_props.get("Manufacturer"), "Vishay Dale")
        self.assertEqual(parsed_props.get("Category"), "Passives")
        self.assertEqual(parsed_props.get("Footprint"), "rov_passives:R_0805_2012Metric")
        self.assertEqual(parsed_props.get("Reference"), "R")

        # Test Capacitor
        cap_props = dict(props, MPN="GRM188R71C104KA01D")
        cap_sym = kicad_sym_utils.get_standard_passive_symbol("C", "GRM188R71C104KA01D", cap_props)
        is_valid, err = kicad_sym_utils.validate_sexpr(cap_sym)
        self.assertTrue(is_valid)
        self.assertIn('(symbol "GRM188R71C104KA01D"', cap_sym)
        parsed_cap_props, _ = kicad_sym_utils.parse_symbol_properties(cap_sym)
        self.assertEqual(parsed_cap_props.get("Reference"), "C")

    def test_link_3d_model_to_footprint(self):
        import tempfile
        sample_mod_without_3d = """(footprint "R_0805_2012Metric"
  (version 20240108)
  (generator "kicad_footprint_editor")
  (layer "F.Cu")
  (pad "1" smd roundrect (at -0.95 0) (size 1 1.45) (layers "F.Cu" "F.Paste" "F.Mask"))
  (pad "2" smd roundrect (at 0.95 0) (size 1 1.45) (layers "F.Cu" "F.Paste" "F.Mask"))
)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            fp_path = Path(tmpdir) / "test.kicad_mod"
            fp_path.write_text(sample_mod_without_3d, encoding="utf-8")

            success = kicad_sym_utils.link_3d_model_to_footprint(fp_path, "resistor_0805.step")
            self.assertTrue(success)

            content = fp_path.read_text(encoding="utf-8")
            self.assertIn('(model "${KIPRJMOD}/libs/purdue-rov-kicad-lib/3D_Models/resistor_0805.step"', content)
            valid, err = kicad_sym_utils.validate_sexpr(content)
            self.assertTrue(valid, f"Footprint S-expr corrupted: {err}")

            # Test updating existing model path and resetting VRML scale for STEP model
            vrml_mod = """(footprint "CONN_HDR"
  (layer "F.Cu")
  (model "${KIPRJMOD}/libs/purdue-rov-kicad-lib/3D_Models/conn.wrl"
    (offset (xyz 0 0 0))
    (scale (xyz 0.3937 0.3937 0.3937))
    (rotate (xyz 0 0 0))
  )
)"""
            fp_vrml_path = Path(tmpdir) / "vrml_test.kicad_mod"
            fp_vrml_path.write_text(vrml_mod, encoding="utf-8")
            kicad_sym_utils.link_3d_model_to_footprint(fp_vrml_path, "conn.step")
            vrml_updated = fp_vrml_path.read_text(encoding="utf-8")
            self.assertIn('(scale (xyz 1 1 1))', vrml_updated)
            self.assertNotIn('0.3937', vrml_updated)

    def test_property_quotes_and_backslashes_escaping(self):
        updates = {
            "Description": '0.1" Pitch Header 1x4 Pin \\ Gold Plated',
            "MPN": 'CONN-"TEST"\\123'
        }
        updated = kicad_sym_utils.update_or_inject_properties(SAMPLE_CORRECT_POWER_SYM, updates)
        valid, err = kicad_sym_utils.validate_sexpr(updated)
        self.assertTrue(valid, f"Escaping error resulted in invalid S-expr: {err}")

        parsed_props, _ = kicad_sym_utils.parse_symbol_properties(updated)
        self.assertEqual(parsed_props.get("Description"), '0.1" Pitch Header 1x4 Pin \\ Gold Plated')
        self.assertEqual(parsed_props.get("MPN"), 'CONN-"TEST"\\123')

    def test_long_property_values(self):
        long_desc = "A" * 600 + " - Very long description exceeding old 350 char limit"
        updates = {"Description": long_desc}
        updated = kicad_sym_utils.update_or_inject_properties(SAMPLE_CORRECT_POWER_SYM, updates)
        valid, err = kicad_sym_utils.validate_sexpr(updated)
        self.assertTrue(valid, f"S-expression corrupted on long property: {err}")

        parsed_props, _ = kicad_sym_utils.parse_symbol_properties(updated)
        self.assertEqual(parsed_props.get("Description"), long_desc)

    def test_rename_symbol(self):
        renamed = kicad_sym_utils.rename_symbol(SAMPLE_RAW_DOWNLOADED_VENDOR_SYM, "TPS62130RGTR")
        self.assertIn('(symbol "TPS62130RGTR"', renamed)
        self.assertIn('(symbol "TPS62130RGTR_0_1"', renamed)
        self.assertNotIn('(symbol "TPS62130_RAW"', renamed)
        self.assertNotIn('(symbol "TPS62130_RAW_0_1"', renamed)

        valid, err = kicad_sym_utils.validate_sexpr(renamed)
        self.assertTrue(valid, f"Renamed symbol S-expr invalid: {err}")

    def test_validate_component_rules_success(self):
        good_fields = {
            "MPN": "STM32C542CCT6",
            "Manufacturer": "STMicroelectronics",
            "Category": "Logic",
            "Datasheet": "https://www.st.com/resource/en/datasheet/stm32c542cc.pdf",
            "DigiKey": "https://www.digikey.com/en/products/detail/stmicroelectronics/STM32C542CCT6/28948246",
            "Temp_Range": "-40°C to 125°C",
            "Footprint": "rov_logic:LQFP48-7X7"
        }
        errors, warnings = kicad_sym_utils.validate_component_rules(good_fields)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_validate_component_rules_catches_errors(self):
        bad_fields = {
            "MPN": "497-STM32C542CCT6-ND", # DigiKey SKU in MPN
            "Manufacturer": "497-STM32C542CCT6-ND", # Same as MPN
            "Category": "InvalidCat",
            "Datasheet": "https://not-a-pdf.com/info.html",
            "DigiKey": "",
            "Temp_Range": ""
        }
        errors, warnings = kicad_sym_utils.validate_component_rules(bad_fields)
        self.assertTrue(any("DigiKey part number" in e for e in errors))
        self.assertTrue(any("identical to MPN" in e for e in errors))
        self.assertTrue(any("Invalid Category" in e for e in errors))
        self.assertTrue(any("PDF document" in e for e in errors))
        self.assertTrue(any("Missing mandatory field: 'DigiKey'" in e for e in errors))
        self.assertTrue(any("Missing mandatory field: 'Temp_Range'" in e for e in errors))

    def test_smart_autofill_mfr_and_digikey_swap(self):
        raw_sym = """(symbol "497-STM32C542CCT6-ND"
            (property "Value" "497-STM32C542CCT6-ND" (id 1) (at 0 0 0))
            (property "Datasheet" "https://example.com/doc.pdf" (id 2) (at 0 0 0))
        )"""
        data = kicad_sym_utils.autofill_component_data(raw_sym)
        # MPN should be cleaned to STM32C542CCT6
        self.assertEqual(data["MPN"], "STM32C542CCT6")
        self.assertEqual(data["DigiKey"], "497-STM32C542CCT6-ND")
        self.assertEqual(data["Manufacturer"], "STMicroelectronics")
        self.assertEqual(data["Category"], "Logic")

if __name__ == "__main__":
    unittest.main()

