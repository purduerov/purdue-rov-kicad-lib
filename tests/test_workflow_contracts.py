"""Contract test for the board notification trigger.

Boards must only be told to update after the approved library revision has
actually passed validation, so a failed library CI run never fans out update
requests to eight repositories.
"""

import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # The library CI installs no packages, so this stays optional.
    yaml = None

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github/workflows/notify-boards.yml"


class TestNotifyWorkflowContract(unittest.TestCase):
    def setUp(self):
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_notification_waits_for_library_ci(self):
        self.assertIn("workflow_run:", self.text)
        self.assertIn("Cross-Platform Library CI Matrix", self.text)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", self.text)

    def test_named_workflow_exists_exactly_once(self):
        # A rename or a duplicate name silently breaks the workflow_run filter.
        owners = [
            workflow.name
            for workflow in sorted((ROOT / ".github/workflows").glob("*.yml"))
            if "name: Cross-Platform Library CI Matrix" in workflow.read_text(encoding="utf-8")
        ]
        self.assertEqual(["library-ci.yml"], owners)

    def test_push_no_longer_triggers_a_notification(self):
        trigger_block = self.text.split("jobs:", 1)[0]
        self.assertNotIn("push:", trigger_block)

    def test_manual_dispatch_is_retained(self):
        trigger_block = self.text.split("jobs:", 1)[0]
        self.assertIn("workflow_dispatch:", trigger_block)

    def test_dispatch_matrix_keeps_every_board_repository(self):
        for repo in (
            "board-template",
            "X19-Control-Board",
            "X19-Electrical-New-Member-Board",
            "X19-Float-Board",
            "X19-Pi-Shield-Board",
            "X19-Power-Slab-Board",
            "X19-Pressure-Chamber-Board",
            "X19-USB-Hub-Board",
        ):
            with self.subTest(repo=repo):
                self.assertIn(repo, self.text)

    def test_dispatch_tolerates_an_unreachable_repository(self):
        self.assertIn("continue-on-error: true", self.text)
        self.assertIn("update-library", self.text)

    def test_workflow_parses(self):
        if yaml is None:
            self.skipTest("PyYAML is not installed in this environment")
        yaml.safe_load(self.text)


if __name__ == "__main__":
    unittest.main()
