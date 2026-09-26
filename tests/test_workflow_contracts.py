"""Contract tests for the library automation workflows.

Boards must only be told to update after the approved library revision has
actually passed validation, so a failed library CI run never fans out update
requests to eight repositories. The library CI must also be able to parse the
workflow YAML it is responsible for, so the parser it installs is asserted here
too.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # Installed by the library CI; a local run may not have it.
    yaml = None

ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = ROOT / ".github/workflows/notify-boards.yml"
LIBRARY_CI_WORKFLOW = ROOT / ".github/workflows/library-ci.yml"


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

    def test_a_failed_dispatch_fails_the_job(self):
        """Important I6: a green run must mean every board was notified.

        `continue-on-error: true` keeps one unreachable repository from hiding
        the other seven, but on its own it also turned a dispatch that never
        reached the board into a successful run. A member watching the library
        repository had no way to tell that a board's scheduled update was never
        triggered. The dispatch step's own outcome is therefore checked, and a
        failure both annotates the run and fails the job.
        """
        self.assertIn("id: dispatch", self.text)
        self.assertIn("steps.dispatch.outcome", self.text)
        self.assertIn("::error::The update-library dispatch", self.text)
        self.assertIn("GITHUB_STEP_SUMMARY", self.text)
        # The failing step has to come after the dispatch it reports on.
        self.assertLess(
            self.text.index("Dispatch Library Update Event"),
            self.text.index("Report Dispatch Result"),
        )

    def test_the_dispatch_result_is_reported_for_every_matrix_entry(self):
        # The report step has no `if:` guard, so a failed dispatch is reported
        # rather than skipped.
        report = self.text.split("- name: Report Dispatch Result", 1)[1]
        self.assertNotIn("if:", report)

    def test_the_failure_message_names_the_board_that_was_not_notified(self):
        report = self.text.split("- name: Report Dispatch Result", 1)[1]
        self.assertIn("REPO: purduerov/${{ matrix.repo }}", report)
        self.assertIn("$REPO", report)

    def test_notification_uses_no_workflow_token_permissions(self):
        # A GITHUB_TOKEN cannot dispatch into another repository, so the job is
        # given no token permissions and relies on the org or personal token.
        self.assertIn("permissions: {}", self.text)

    def test_notification_ignores_non_push_library_ci_runs(self):
        # The library CI also answers pull_request events. A re-run of an old
        # pull_request workflow_run must not look like an approved push.
        self.assertIn("github.event.workflow_run.event == 'push'", self.text)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", self.text)
        self.assertIn("github.event_name == 'workflow_dispatch'", self.text)

    def test_token_fallback_is_warned_about(self):
        self.assertIn("ORG_DISPATCH_TOKEN", self.text)
        self.assertIn("PAT_TOKEN", self.text)
        self.assertIn("::warning::", self.text)


class TestLibraryCiContract(unittest.TestCase):
    """The library CI must be able to parse the workflows it validates."""

    def setUp(self):
        self.text = LIBRARY_CI_WORKFLOW.read_text(encoding="utf-8")

    def test_workflow_tests_install_the_yaml_parser_first(self):
        # The workflow contract tests parse the workflow YAML. Without the
        # parser in CI they would silently skip, so the install is required and
        # has to run before the tests.
        install = self.text.index("pip install pyyaml")
        tests = self.text.index("-m unittest discover -s tests -v")
        self.assertLess(install, tests, "PyYAML must be installed before the tests run")
        self.assertIn("python -m pip install --upgrade pip", self.text)

    def test_no_new_dependency_is_added_to_the_library_scripts(self):
        # Only the test-time parser is added, exactly once, and the library
        # scripts keep running on the standard library alone.
        installs = [
            line.strip()
            for line in self.text.splitlines()
            if line.strip().startswith("pip install")
        ]
        self.assertEqual(["pip install pyyaml"], installs)
        self.assertNotIn("pip install -r", self.text)
        self.assertNotIn("requirements", self.text)

    def test_workflow_parses(self):
        if yaml is None:
            self.skipTest("PyYAML is not installed in this environment")
        yaml.safe_load(self.text)


class TestWorkflowShellBlocksParse(unittest.TestCase):
    """Every `run:` block must be valid shell.

    The step that reports a failed dispatch is shell, and a syntax error there
    would turn a real dispatch failure back into a silent green run.
    """

    def bash(self) -> str | None:
        path = shutil.which("bash")
        if path is None:
            return None
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            probe = Path(tmp) / "probe.sh"
            probe.write_text("if true; then :; fi\n", encoding="utf-8", newline="\n")
            posix = subprocess.run(
                [path, "-c", "pwd -P"], cwd=tmp, capture_output=True, text=True, timeout=30
            ).stdout.strip()
            result = subprocess.run(
                [path, "-n", f"{posix}/probe.sh"], capture_output=True, text=True, timeout=60
            )
            return path if result.returncode == 0 else None

    def test_every_run_block_parses(self):
        bash = self.bash()
        if bash is None:
            self.skipTest("no bash is available to parse the workflow scripts")
        if yaml is None:
            self.skipTest("PyYAML is not installed in this environment")
        for workflow in sorted((ROOT / ".github/workflows").glob("*.yml")):
            data = yaml.safe_load(workflow.read_text(encoding="utf-8"))
            for job in (data.get("jobs") or {}).values():
                for step in job.get("steps") or []:
                    script = step.get("run")
                    if not script or "${" in script:
                        continue
                    with self.subTest(workflow=workflow.name, step=step.get("name")):
                        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
                            path = Path(tmp) / "step.sh"
                            path.write_text(script, encoding="utf-8", newline="\n")
                            posix = subprocess.run(
                                [bash, "-c", "pwd -P"],
                                cwd=tmp,
                                capture_output=True,
                                text=True,
                                timeout=30,
                            ).stdout.strip()
                            result = subprocess.run(
                                [bash, "-n", f"{posix}/step.sh"],
                                capture_output=True,
                                text=True,
                                timeout=60,
                            )
                        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
