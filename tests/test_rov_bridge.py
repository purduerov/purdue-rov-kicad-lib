import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

import rov_bridge


def make_fake_devops(base: Path, body: str = "") -> Path:
    """Create a minimal DevOps checkout whose CLI prints ``body``."""
    devops = base / "DevOps"
    (devops / "scripts").mkdir(parents=True, exist_ok=True)
    (devops / "scripts" / "rov.py").write_text(body, encoding="utf-8")
    return devops


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


class TestRovBridgeTimeouts(unittest.TestCase):
    """The bridge must never wait on a hung CLI forever.

    ``subprocess.run`` is the only thing replaced, so the real
    ``subprocess.TimeoutExpired`` class is still the one the bridge catches and
    every assertion below is about the bridge's own behavior.
    """

    def test_default_timeout_is_bounded(self):
        """A caller that passes nothing still gets a bounded wait."""
        with patch.object(rov_bridge.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "", "")
            rov_bridge.run_rov(Path.cwd(), ["library", "sync"], devops_dir=Path.cwd())
        timeout = run.call_args.kwargs["timeout"]
        self.assertIsInstance(timeout, (int, float))
        self.assertGreater(timeout, 0)

    def test_explicit_timeout_is_forwarded(self):
        with patch.object(rov_bridge.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "", "")
            rov_bridge.run_rov(
                Path.cwd(), ["library", "sync"], devops_dir=Path.cwd(), timeout=12.5
            )
        self.assertEqual(run.call_args.kwargs["timeout"], 12.5)

    def test_no_shell_is_used(self):
        with patch.object(rov_bridge.subprocess, "run") as run:
            run.return_value = subprocess.CompletedProcess([], 0, "", "")
            rov_bridge.run_rov(Path.cwd(), ["library", "sync"], devops_dir=Path.cwd())
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_a_timeout_is_reported_as_a_failed_result(self):
        """A hung CLI becomes a non-zero result instead of an exception.

        The GUI and any other caller then report one ordinary failure rather than
        having to catch a subprocess exception themselves.
        """
        with patch.object(rov_bridge.subprocess, "run") as run:
            run.side_effect = subprocess.TimeoutExpired(cmd="rov", timeout=7)
            result = rov_bridge.run_rov(
                Path.cwd(), ["library", "sync"], devops_dir=Path.cwd(), timeout=7
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("7 seconds", result.stderr)
        self.assertIn("did not finish within", result.stderr)

    def test_a_real_timeout_is_reported_for_a_slow_cli(self):
        """End to end through a real subprocess that outlives its budget."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            devops = make_fake_devops(root, "import time\ntime.sleep(30)\n")
            result = rov_bridge.run_rov(
                root, ["library", "sync"], devops_dir=devops, timeout=1
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("did not finish within", result.stderr)


if __name__ == "__main__":
    unittest.main()
