import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from kicad_sym_utils import extract_top_symbols, parse_symbol_properties


def _sanitize(name):
    """Match the filename convention in build_symbol_libs.decompose."""
    return re.sub(r"[^a-zA-Z0-9_\-\.\+]", "_", name)


# Parts whose symbol name cannot equal the sanitized MPN yet. Each entry must
# name the blocker; exceptions are temporary, not a second naming scheme.
KNOWN_EXCEPTIONS = {
    # X19-USB-Hub-Board references rov_logic:UPD720201K8-7x1-BAC-A. Renaming
    # the symbol to the DigiKey MPN (...-711-...) breaks that board, so the
    # rename waits for a board-side migration.
    "UPD720201K8-7x1-BAC-A.kicad_sym": "kept for X19-USB-Hub-Board compatibility",
}


class TestSymbolMpnContract(unittest.TestCase):
    def test_top_level_symbol_name_matches_sanitized_mpn(self):
        mismatches = []
        for part_file in sorted((ROOT / "Symbols" / "parts").rglob("*.kicad_sym")):
            if part_file.name in KNOWN_EXCEPTIONS:
                continue
            content = part_file.read_text(encoding="utf-8", errors="ignore")
            for sym_name, raw_sym, _, _ in extract_top_symbols(content):
                props, _ = parse_symbol_properties(raw_sym)
                mpn = (props.get("MPN") or "").strip()
                if mpn and sym_name != _sanitize(mpn):
                    mismatches.append(
                        f"{part_file.name}: symbol '{sym_name}' != MPN '{mpn}'"
                    )
        self.assertEqual(mismatches, [])


if __name__ == "__main__":
    unittest.main()
