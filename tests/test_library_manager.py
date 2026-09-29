#!/usr/bin/env python3
"""
Unit and Integration tests for Library Manager parser, editor, and operations.
"""

import io
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

# Add scripts directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

from library_manager_gui import LibraryParser, CATEGORIES, CATEGORY_FILES
import import_part

class TestLibraryManager(unittest.TestCase):
    def setUp(self):
        self.test_sym_name = "__TEST_COMPONENT_TMP__"
        self.test_raw_sym = f"""(symbol "{self.test_sym_name}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
    (property "Reference" "U" (id 0) (at 0 0 0) (effects (font (size 1.27 1.27))))
    (property "Value" "{self.test_sym_name}" (id 1) (at 0 0 0) (effects (font (size 1.27 1.27))))
    (property "Footprint" "rov_power:TEST_FP" (id 2) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "Datasheet" "https://example.com/datasheet.pdf" (id 3) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "Category" "Power" (id 4) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "MPN" "TEST-1234" (id 5) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "Manufacturer" "TestCorp" (id 6) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "DigiKey" "TEST-ND" (id 7) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "Temp_Range" "-40°C to 125°C" (id 8) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (property "Description" "Temporary test component" (id 9) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
    (symbol "{self.test_sym_name}_0_0"
      (rectangle (start -5.08 5.08) (end 5.08 -5.08) (stroke (width 0.254)) (fill (type background)))
      (pin power_in line (at 0 7.62 270) (length 2.54) (name "VIN" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))
      (pin power_out line (at 0 -7.62 90) (length 2.54) (name "VOUT" (effects (font (size 1.27 1.27)))) (number "2" (effects (font (size 1.27 1.27)))))
    )
  )"""

    def tearDown(self):
        # Cleanup test symbol from all categories
        for cat in CATEGORIES:
            LibraryParser.delete_symbol(self.test_sym_name, cat)

    def test_load_all_symbols(self):
        syms = LibraryParser.load_all_symbols()
        self.assertIsInstance(syms, dict)
        self.assertIn("XT60-M", syms)
        self.assertEqual(syms["XT60-M"]["category"], "Connectors")
        self.assertEqual(syms["XT60-M"]["properties"]["Manufacturer"], "AMASS")

    def test_insert_and_load_symbol(self):
        # Insert into Power
        LibraryParser.insert_symbol("Power", self.test_raw_sym)
        syms = LibraryParser.load_all_symbols()
        self.assertIn(self.test_sym_name, syms)
        self.assertEqual(syms[self.test_sym_name]["category"], "Power")
        self.assertEqual(syms[self.test_sym_name]["properties"]["MPN"], "TEST-1234")
        self.assertEqual(syms[self.test_sym_name]["properties"]["Manufacturer"], "TestCorp")

    def test_edit_symbol_properties(self):
        LibraryParser.insert_symbol("Power", self.test_raw_sym)
        syms = LibraryParser.load_all_symbols()
        
        # Modify properties
        updated_props = dict(syms[self.test_sym_name]["properties"])
        updated_props["MPN"] = "TEST-9999-NEW"
        updated_props["Manufacturer"] = "UpdatedManufacturer"
        
        LibraryParser.save_symbol(self.test_sym_name, "Power", "Power", updated_props, syms[self.test_sym_name]["raw_text"])
        
        # Verify changes persisted
        reloaded_syms = LibraryParser.load_all_symbols()
        self.assertEqual(reloaded_syms[self.test_sym_name]["properties"]["MPN"], "TEST-9999-NEW")
        self.assertEqual(reloaded_syms[self.test_sym_name]["properties"]["Manufacturer"], "UpdatedManufacturer")

    def test_move_symbol_category(self):
        # Insert into Power
        LibraryParser.insert_symbol("Power", self.test_raw_sym)
        syms = LibraryParser.load_all_symbols()
        self.assertEqual(syms[self.test_sym_name]["category"], "Power")

        # Move to Sensors
        updated_props = dict(syms[self.test_sym_name]["properties"])
        LibraryParser.save_symbol(self.test_sym_name, "Power", "Sensors", updated_props, syms[self.test_sym_name]["raw_text"])

        # Verify moved
        reloaded_syms = LibraryParser.load_all_symbols()
        self.assertEqual(reloaded_syms[self.test_sym_name]["category"], "Sensors")
        
        # Check power sym file doesn't have it
        power_file = BASE_DIR / "Symbols" / "rov_power.kicad_sym"
        with open(power_file, 'r', encoding='utf-8') as f:
            self.assertNotIn(self.test_sym_name, f.read())

        # Check sensors sym file has it
        sensor_file = BASE_DIR / "Symbols" / "rov_sensors.kicad_sym"
        with open(sensor_file, 'r', encoding='utf-8') as f:
            self.assertIn(self.test_sym_name, f.read())

    def test_delete_symbol(self):
        LibraryParser.insert_symbol("Power", self.test_raw_sym)
        self.assertIn(self.test_sym_name, LibraryParser.load_all_symbols())

        LibraryParser.delete_symbol(self.test_sym_name, "Power")
        self.assertNotIn(self.test_sym_name, LibraryParser.load_all_symbols())

    def test_insert_into_power_preserves_kicad_validity(self):
        # Specifically test that inserting into Power does not cause it to disappear or corrupt
        from kicad_sym_utils import validate_sexpr
        LibraryParser.insert_symbol("Power", self.test_raw_sym)
        
        power_file = BASE_DIR / "Symbols" / "rov_power.kicad_sym"
        with open(power_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        is_valid, err = validate_sexpr(content)
        self.assertTrue(is_valid, f"Power library became invalid S-expression: {err}")
        self.assertNotIn("#", content, "Illegal comment character found in power library")


class TestImportPartContributionHint(unittest.TestCase):
    """The importer must never publish to a protected branch itself.

    ``import_part.py`` writes library files and runs the metadata linter; turning
    those local changes into a branch, a commit, and a pull request is the job of
    ``rov library contribute``. These tests pin that division of work.
    """

    # A throwaway part number that cannot collide with a real library part, and
    # the symbol is removed again in tearDown so the suite leaves no change
    # behind in the repository it runs against.
    PART_NAME = "ZZTEST-ROV-HINT-0001"

    def tearDown(self):
        for cat in CATEGORIES:
            LibraryParser.delete_symbol(self.PART_NAME, cat)

    def test_importer_never_runs_git_publishing_commands(self):
        source = Path(import_part.__file__).read_text(encoding="utf-8")
        for forbidden in ('"git", "push"', '"git", "commit"', '"git", "add"', '"git", "checkout"'):
            self.assertNotIn(
                forbidden, source, f"import_part.py must not run {forbidden}"
            )

    def test_hint_prints_concrete_rov_command(self):
        output = self._hint_output(devops="C:/devops/DevOps")
        self.assertIn("Library changes validated. Run:", output)
        self.assertIn("C:/devops/DevOps", output.replace("\\", "/"))
        self.assertIn(
            f"library contribute --name {self.PART_NAME} --category Power --push --pr", output
        )

    def test_hint_explains_how_to_locate_devops_when_unresolved(self):
        output = self._hint_output(devops=None)
        self.assertIn("Set ROV_DEVOPS_DIR or run LAUNCH_KICAD once", output)
        self.assertIn("rov library contribute --push --pr", output)

    def test_hint_shell_quotes_a_part_name_with_metacharacters(self):
        """A part number is data, never a command.

        The MPN is read out of a downloaded symbol file, so it can contain a
        space or a shell metacharacter. The hint is meant to be copied and
        pasted, and an unquoted value would be reinterpreted by the shell the
        member pastes it into.
        """
        for mpn in ("TPS 62130", "A&B", "part;rm -rf /", "quote'part"):
            with self.subTest(mpn=mpn):
                output = self._hint_for(mpn, devops="C:/devops/DevOps")
                self.assertEqual(
                    self._parse_hint(output),
                    self._expected_command(mpn, devops="C:/devops/DevOps"),
                    f"the printed command must round-trip through a shell: {output!r}",
                )

    def test_hint_quotes_a_devops_path_containing_a_space(self):
        output = self._hint_for("ZZTEST", devops="C:/Program Files/DevOps")
        self.assertEqual(
            self._parse_hint(output),
            self._expected_command("ZZTEST", devops="C:/Program Files/DevOps"),
        )

    def test_shell_join_uses_the_platform_quoting_rules(self):
        # POSIX quoting pasted into a Windows terminal would reach the program
        # with the single quotes still attached, so each platform gets its own.
        command = ["python", "C:/Program Files/rov.py", "--name", "A B"]
        if os.name == "nt":
            self.assertEqual(
                import_part.shell_join(command),
                subprocess.list2cmdline(command),
            )
        else:
            self.assertEqual(shlex.split(import_part.shell_join(command)), command)

    def test_non_interactive_import_prints_the_same_hint_after_validation(self):
        """The argument-driven path gives the same next step as the wizard."""
        source_file = self._write_source_symbol()
        calls = []

        def fake_validate(*_args, **_kwargs):
            calls.append(True)
            return subprocess.CompletedProcess([], 0, "", "")

        argv = self._import_argv(source_file)
        buffer = io.StringIO()
        with patch.object(sys, "argv", argv), patch.object(
            import_part.rov_bridge, "run_rov", fake_validate
        ), patch.object(
            import_part.rov_bridge, "resolve_devops_dir", lambda _d: Path("C:/devops/DevOps")
        ):
            with redirect_stdout(buffer):
                import_part.main()

        self.assertTrue(calls, "the non-interactive path must still run the linter")
        output = buffer.getvalue()
        self.assertIn("Library changes validated. Run:", output)
        self.assertIn(
            f"library contribute --name {self.PART_NAME} --category Power --push --pr", output
        )

    def test_non_interactive_import_reports_a_failing_linter_without_a_hint(self):
        """A failing linter is reported and no next command is suggested."""
        source_file = self._write_source_symbol()

        def fake_validate(*_args, **_kwargs):
            return subprocess.CompletedProcess([], 1, "", "missing mandatory field: MPN")

        argv = self._import_argv(source_file)
        buffer = io.StringIO()
        with patch.object(sys, "argv", argv), patch.object(
            import_part.rov_bridge, "run_rov", fake_validate
        ), patch.object(
            import_part.rov_bridge, "resolve_devops_dir", lambda _d: Path("C:/devops/DevOps")
        ):
            with redirect_stdout(buffer):
                import_part.main()

        output = buffer.getvalue()
        self.assertIn("[FAIL] Linter check failed", output)
        self.assertIn("missing mandatory field: MPN", output)
        self.assertNotIn("Library changes validated. Run:", output)

    def test_non_interactive_import_missing_cli_prints_message_and_exits_nonzero(self):
        """A missing DevOps checkout is an actionable message, not a traceback."""
        source_file = self._write_source_symbol()

        def fake_run(*_args, **_kwargs):
            raise FileNotFoundError("checked ...")

        argv = self._import_argv(source_file)
        buffer = io.StringIO()
        with patch.object(sys, "argv", argv), patch.object(
            import_part.rov_bridge, "run_rov", fake_run
        ):
            with redirect_stdout(buffer):
                with self.assertRaises(SystemExit) as ctx:
                    import_part.main()

        self.assertEqual(1, ctx.exception.code)
        output = buffer.getvalue()
        self.assertIn("checked", output)
        self.assertNotIn("Traceback", output)

    def _import_argv(self, source_file):
        """Return the argument list the importer is driven with."""
        return [
            "import_part.py",
            "--symbol", str(source_file),
            "--category", "Power",
            "--mpn", self.PART_NAME,
        ]

    def _write_source_symbol(self):
        """Write a throwaway source symbol file for the import arguments."""
        temp_dir = tempfile.mkdtemp(prefix="rov-import-test-")
        self.addCleanup(shutil.rmtree, temp_dir, True)
        path = Path(temp_dir) / "source.kicad_sym"
        path.write_text(
            '(kicad_symbol_lib\n  (version 20211014)\n'
            f'  (symbol "{self.PART_NAME}"\n'
            f'    (property "MPN" "{self.PART_NAME}" (id 5) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
            '    (property "Manufacturer" "Test Vendor" (id 6) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
            '    (property "DigiKey" "000-00000-ND" (id 7) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
            '    (property "Datasheet" "https://example.invalid/datasheet.pdf" (id 3) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
            '    (property "Temp_Range" "-40C to 125C" (id 8) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
            '    (property "Category" "Power" (id 4) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
            '  )\n)\n',
            encoding="utf-8",
        )
        return path

    def _hint_output(self, devops):
        """Return the printed hint with the DevOps resolver patched."""

        def fake_resolve(_library_dir):
            if devops is None:
                raise FileNotFoundError("no DevOps checkout found")
            return Path(devops)

        buffer = io.StringIO()
        with patch.object(import_part.rov_bridge, "resolve_devops_dir", fake_resolve):
            with redirect_stdout(buffer):
                import_part.print_contribution_hint(self.PART_NAME, "Power")
        return buffer.getvalue()

    def _hint_for(self, mpn, devops):
        """Return the hint for an arbitrary part name and DevOps location."""

        def fake_resolve(_library_dir):
            return Path(devops)

        buffer = io.StringIO()
        with patch.object(import_part.rov_bridge, "resolve_devops_dir", fake_resolve):
            with redirect_stdout(buffer):
                import_part.print_contribution_hint(mpn, "Power")
        return buffer.getvalue()

    def _parse_hint(self, output):
        """Split the printed command back into the arguments it stands for."""
        command = output.split("Run:", 1)[1].strip()
        if os.name == "nt":
            # The Windows parser lives in the C runtime; assert on the exact
            # rendering `subprocess` itself would produce instead.
            return command
        return shlex.split(command)

    def _expected_command(self, mpn, devops):
        """The argument list the printed command has to stand for."""
        script = str(Path(devops) / "scripts" / "rov.py")
        command = [
            sys.executable,
            script,
            "library", "contribute",
            "--name", mpn,
            "--category", "Power",
            "--push", "--pr",
        ]
        return command if os.name != "nt" else import_part.shell_join(command)


class TestSharedValidation(unittest.TestCase):
    def test_success_returns_zero_and_output(self):
        from unittest.mock import MagicMock

        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = "Validation successful!"
        proc.stderr = ""
        with patch.object(import_part.rov_bridge, "run_rov", return_value=proc) as mock_run:
            code, output = import_part.run_shared_validation()
        mock_run.assert_called_once_with(import_part.BASE_DIR, ["library", "validate"])
        self.assertEqual(0, code)
        self.assertIn("Validation successful!", output)

    def test_failure_returns_nonzero(self):
        from unittest.mock import MagicMock

        proc = MagicMock()
        proc.returncode = 1
        proc.stdout = ""
        proc.stderr = "Rule violation"
        with patch.object(import_part.rov_bridge, "run_rov", return_value=proc):
            code, output = import_part.run_shared_validation()
        self.assertEqual(1, code)
        self.assertIn("Rule violation", output)

    def test_interactive_import_prints_failing_validation_output(self):
        """The wizard shows the violations, not just the FAIL line."""
        answers = iter([
            "",  # symbol path: standard passive, no file read
            "",  # footprint path
            "",  # 3D model path
            "",  # category: detected default
            "",  # passive symbol type: resistor
            "TEST-IM-0001",  # MPN
            "Test Vendor",  # manufacturer
            "https://example.invalid/datasheet.pdf",  # datasheet
            "000-00000-ND",  # DigiKey
            "",  # temp range: default
        ])

        def fake_validate(*_args, **_kwargs):
            return subprocess.CompletedProcess([], 1, "", "missing mandatory field: MPN")

        buffer = io.StringIO()
        with patch("builtins.input", lambda _prompt="": next(answers)), patch.object(
            import_part.rov_bridge, "run_rov", fake_validate
        ), patch.object(
            import_part, "append_symbol_to_category", lambda *a, **k: None
        ), patch.object(
            import_part, "write_part_source_file", lambda *a, **k: None
        ):
            with redirect_stdout(buffer):
                import_part.interactive_mode()

        output = buffer.getvalue()
        self.assertIn("[FAIL] Linter check failed", output)
        self.assertIn("missing mandatory field: MPN", output)

    def test_missing_cli_prints_message_and_exits_nonzero(self):
        """No DevOps checkout means an actionable message, never a traceback."""
        def fake_run(*_args, **_kwargs):
            raise FileNotFoundError("checked ...")

        buffer = io.StringIO()
        with patch.object(import_part.rov_bridge, "run_rov", fake_run):
            with redirect_stdout(buffer):
                with self.assertRaises(SystemExit) as ctx:
                    import_part.run_shared_validation()

        self.assertEqual(1, ctx.exception.code)
        self.assertIn("checked", buffer.getvalue())


class TestPerPartSourceFile(unittest.TestCase):
    """A CLI import must survive a rebuild of the aggregate category file.

    ``Symbols/rov_<category>.kicad_sym`` is derived output: ``build_symbol_libs.py``
    compiles ``Symbols/parts/<category>/*.kicad_sym`` and overwrites it. An import
    that only appends to the aggregate therefore loses the part on the next build,
    so the CLI has to write the per-part source file the build reads from.

    Both entry points are covered. The argument-driven path is one of two: the
    module docstring documents a bare ``python scripts/import_part.py`` as the
    primary usage, and ``main()`` routes to the wizard whenever ``--symbol`` is
    absent, so a wizard import that skipped the per-part write would still lose
    the part.

    The whole flow runs in a temp tree because the real ``import_part.py`` resolves
    ``Symbols/`` from its own location; importing it in place would write into the
    actual library, and a real build would rewrite all six aggregate files.
    """

    def test_imported_symbol_survives_rebuild(self):
        """The argument-driven path writes the source file the build reads."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lib, scripts, env = self._stage_library(tmpdir)
            source = self._write_source_symbol(tmpdir, "REBUILDPROBE")
            result = subprocess.run(
                [sys.executable, str(scripts / "import_part.py"),
                 "--symbol", str(source), "--category", "Power",
                 "--mpn", "REBUILDPROBE", "--mfr", "Acme",
                 "--datasheet", "https://example.com/p.pdf",
                 "--temp", "-40C to 125C"],
                capture_output=True, text=True, env=env, cwd=tmpdir,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self._assert_rebuild_keeps_part(lib, scripts, env, tmpdir, "REBUILDPROBE")

    def test_wizard_import_survives_rebuild(self):
        """The wizard writes the same source file, so a wizard import survives too.

        The wizard reads every field with ``input()``, so the responses are piped
        into stdin in exactly the order it prompts for them. ``Power`` is chosen
        by its menu number rather than by pressing Enter, because the wizard's
        default depends on what it infers from the source symbol. A prompt that
        goes unanswered raises ``EOFError`` and surfaces in the assertion message,
        so a reordering of the wizard is reported rather than silently absorbed.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            lib, scripts, env = self._stage_library(tmpdir)
            source = self._write_source_symbol(tmpdir, "WIZARDPROBE")
            answers = [
                str(source),                # downloaded symbol file
                "",                         # footprint: none
                "",                         # 3D model: none
                self._power_menu_choice(),   # component category
                "WIZARDPROBE",              # MPN
                "Acme",                     # manufacturer
                "https://example.com/w.pdf",  # datasheet URL
                "",                         # DigiKey part number: none
                "",                         # temperature range: keep the default
            ]
            result = subprocess.run(
                [sys.executable, str(scripts / "import_part.py")],
                input="\n".join(answers) + "\n",
                capture_output=True, text=True, env=env, cwd=tmpdir,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self._assert_rebuild_keeps_part(lib, scripts, env, tmpdir, "WIZARDPROBE")

    def _assert_rebuild_keeps_part(self, lib, scripts, env, tmpdir, part_name):
        """Assert the import left a per-part file that a rebuild compiles back in."""
        per_part = lib / "Symbols" / "parts" / "power" / f"{part_name}.kicad_sym"
        self.assertTrue(per_part.is_file(), "per-part source file was not written")

        rebuild = subprocess.run(
            [sys.executable, str(scripts / "build_symbol_libs.py")],
            capture_output=True, text=True, env=env, cwd=tmpdir,
        )
        self.assertEqual(rebuild.returncode, 0, rebuild.stderr)
        aggregate = (lib / "Symbols" / "rov_power.kicad_sym").read_text(encoding="utf-8")
        self.assertIn(f'(symbol "{part_name}"', aggregate,
                      "rebuild discarded the imported symbol")

    def _stage_library(self, tmpdir):
        """Copy the scripts into a throwaway library tree and return where to run them."""
        lib = Path(tmpdir)
        scripts = lib / "scripts"
        scripts.mkdir()
        (lib / "Symbols" / "parts").mkdir(parents=True)
        for name in ("import_part", "kicad_sym_utils", "build_symbol_libs", "rov_bridge"):
            shutil.copy2(BASE_DIR / "scripts" / f"{name}.py", scripts / f"{name}.py")
        (lib / "Symbols" / "rov_power.kicad_sym").write_text(
            '(kicad_symbol_lib (version 20211014)\n  (generator "kicad_symbol_editor")\n)\n',
            encoding="utf-8",
        )
        # The importer validates through the shared DevOps CLI before it
        # reports success. A stub keeps the subprocess self-contained: it
        # resolves the bridge without reaching for a real checkout.
        devops = lib / "DevOps"
        (devops / "scripts").mkdir(parents=True)
        (devops / "scripts" / "rov.py").write_text(
            "import sys\nsys.exit(0)\n", encoding="utf-8"
        )
        env = dict(os.environ, PYTHONPATH=str(scripts), ROV_DEVOPS_DIR=str(devops))
        return lib, scripts, env

    def _power_menu_choice(self):
        """Return the number the wizard's category menu prints for ``Power``."""
        return str(import_part.ALLOWED_CATEGORIES.index("Power") + 1)

    def _write_source_symbol(self, tmpdir, part_name):
        """Write the throwaway downloaded symbol the import is driven with."""
        path = Path(tmpdir) / f"{part_name}.kicad_sym"
        path.write_text(
            '(kicad_symbol_lib (version 20211014)\n'
            f'  (symbol "{part_name}" (in_bom yes) (on_board yes)\n'
            '    (property "Reference" "U" (id 0) (at 0 0 0))\n'
            '  )\n'
            ')\n',
            encoding="utf-8",
        )
        return path


if __name__ == "__main__":
    unittest.main()
