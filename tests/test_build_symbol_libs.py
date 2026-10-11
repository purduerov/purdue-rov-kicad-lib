import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_symbol_libs


PART_SRC = ROOT / "Symbols" / "parts" / "power" / "PKU5511ESI.kicad_sym"


class TestBuildGuard(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.symbols_dir = Path(self._tmp.name) / "Symbols"
        self._orig_symbols = build_symbol_libs.SYMBOLS_DIR
        self._orig_parts = build_symbol_libs.PARTS_DIR
        build_symbol_libs.SYMBOLS_DIR = self.symbols_dir
        build_symbol_libs.PARTS_DIR = self.symbols_dir / "parts"

    def tearDown(self):
        build_symbol_libs.SYMBOLS_DIR = self._orig_symbols
        build_symbol_libs.PARTS_DIR = self._orig_parts
        self._tmp.cleanup()

    def test_rebuild_refuses_to_empty_a_nonempty_category_library(self):
        cat_folder = self.symbols_dir / "parts" / "power"
        cat_folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PART_SRC, cat_folder / PART_SRC.name)

        build_symbol_libs.build_all_categories()
        compiled = self.symbols_dir / "rov_power.kicad_sym"
        self.assertIn("PKU5511ESI", compiled.read_text(encoding="utf-8"))

        # Empty the only part source, then rebuild: this must refuse and keep
        # the previously compiled library instead of writing an empty shell.
        (cat_folder / PART_SRC.name).unlink()
        with self.assertRaisesRegex(ValueError, "Refusing to empty"):
            build_symbol_libs.build_all_categories()
        self.assertIn("PKU5511ESI", compiled.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
