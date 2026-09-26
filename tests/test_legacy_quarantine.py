import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEGACY = ROOT / "scripts" / "legacy"
DEAD = [
    "categorize_library.py",
    "port_external_parts.py",
    "port_usb_hub_parts.py",
    "fix_usb_hub_project.py",
    "benchmark.py",
]


class TestLegacyQuarantine(unittest.TestCase):
    def test_dead_scripts_are_quarantined(self):
        missing = [name for name in DEAD if not (LEGACY / name).is_file()]
        self.assertEqual([], missing)

    def test_live_code_does_not_import_dead_scripts(self):
        offenders = []
        for base in (ROOT / "scripts", ROOT / "tests"):
            for path in base.rglob("*.py"):
                if "scripts/legacy" in path.as_posix():
                    continue
                text = path.read_text(encoding="utf-8")
                for name in DEAD:
                    stem = Path(name).stem
                    if f"import {stem}" in text or f"from {stem}" in text:
                        offenders.append(f"{path}:{stem}")
        self.assertEqual([], offenders)
