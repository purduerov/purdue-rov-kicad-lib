import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

import rov_bridge


class TestRovBridge(unittest.TestCase):
    def test_environment_path_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = root / "env"
            sibling = root / "sibling"
            (env / "scripts").mkdir(parents=True)
            (env / "scripts" / "rov.py").write_text("", encoding="utf-8")
            (sibling / "scripts").mkdir(parents=True)
            (sibling / "scripts" / "rov.py").write_text("", encoding="utf-8")
            with patch.dict(os.environ, {"ROV_DEVOPS_DIR": str(env)}):
                self.assertEqual(rov_bridge.resolve_devops_dir(sibling), env)

    def test_sibling_path_is_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / "Libraries"
            devops = root / "DevOps"
            library.mkdir()
            (devops / "scripts").mkdir(parents=True)
            (devops / "scripts" / "rov.py").write_text("", encoding="utf-8")
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(rov_bridge.resolve_devops_dir(library), devops)

    def test_run_rov_uses_explicit_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            devops = root / "DevOps"
            (devops / "scripts").mkdir(parents=True)
            script = devops / "scripts" / "rov.py"
            script.write_text("import sys\nprint('|'.join(sys.argv[1:]))\n", encoding="utf-8")
            result = rov_bridge.run_rov(root, ["library", "validate"], devops_dir=devops)
            self.assertEqual(result.stdout.strip(), "library|validate")


if __name__ == "__main__":
    unittest.main()
