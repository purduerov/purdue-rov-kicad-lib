#!/usr/bin/env python3
"""
Comprehensive Headless Button and Flow Integration Test Suite for LibraryManagerApp.
Verifies all buttons, callbacks, filters, and dialog flows headlessly.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tkinter as tk

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

import library_manager_gui
from library_manager_gui import LibraryManagerApp, ImportPartDialog, E2ETestDialog

# TestLibraryManagerGui opens a real Tk root. A runner with no usable display
# does not fail fast on Tk: the root creation blocks, which is why the macOS
# library CI legs ran for hours instead of reporting a problem. The workflow sets
# ROV_SKIP_GUI_TESTS=1 where there is no display, and the decision is made here,
# before any Tk call, so skipping can never itself hang. The other classes in
# this module drive fakes and stay headless on every platform.
SKIP_GUI_TESTS = os.environ.get("ROV_SKIP_GUI_TESTS") == "1"


def _dialog_text(mock_dialog):
    """Return every text fragment passed to a patched message box."""
    return " ".join(
        str(part)
        for call in mock_dialog.call_args_list
        for part in (call.args[1:] if len(call.args) > 1 else ())
    )


@unittest.skipIf(SKIP_GUI_TESTS, "GUI tests skipped: no usable display on this runner")
class TestLibraryManagerGui(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception as e:
            raise unittest.SkipTest(f"Tkinter display not available: {e}")

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "root") and cls.root:
            try:
                cls.root.destroy()
            except Exception:
                pass

    def setUp(self):
        self.app = LibraryManagerApp(self.root)
        self.root.update()

    def test_app_initialization_and_symbols_loaded(self):
        """Verifies UI structures and symbols are initialized and populated."""
        self.assertIsNotNone(self.app.tree)
        self.assertGreater(len(self.app.symbols), 0, "Active library should contain parsed symbols.")
        self.assertEqual(len(self.app.filtered_symbols), len(self.app.symbols))

    def test_refresh_symbols(self):
        """Verifies refresh_symbols reloads symbol dict from disk."""
        initial_count = len(self.app.symbols)
        self.app.refresh_symbols()
        self.assertEqual(len(self.app.symbols), initial_count)

    def test_apply_filters_category(self):
        """Verifies filtering by category isolates matching parts."""
        self.app.category_filter_var.set("Power")
        self.app.apply_filters()
        for sym_name, sym_data in self.app.filtered_symbols.items():
            self.assertEqual(sym_data["category"], "Power")

        # Reset to All
        self.app.category_filter_var.set("All")
        self.app.apply_filters()
        self.assertEqual(len(self.app.filtered_symbols), len(self.app.symbols))

    def test_apply_filters_search_query(self):
        """Verifies search text query filters across MPN, Name, and Description."""
        # Pick the first known symbol
        first_sym = next(iter(self.app.symbols.keys()))
        self.app.search_var.set(first_sym)
        self.app.apply_filters()
        self.assertIn(first_sym, self.app.filtered_symbols)

        # Nonexistent search
        self.app.search_var.set("NONEXISTENT_SEARCH_STRING_XYZ_123")
        self.app.apply_filters()
        self.assertEqual(len(self.app.filtered_symbols), 0)

        # Clear search
        self.app.search_var.set("")
        self.app.apply_filters()
        self.assertEqual(len(self.app.filtered_symbols), len(self.app.symbols))

    def test_on_symbol_select_loads_properties(self):
        """Verifies selecting a symbol populates the property inspector entries."""
        first_sym = next(iter(self.app.symbols.keys()))
        sym_data = self.app.symbols[first_sym]
        expected_mpn = sym_data["properties"].get("MPN", "")

        self.app.tree.selection_set(first_sym)
        self.app.on_symbol_select(None)

        self.assertEqual(self.app.fields_entries["MPN"].get(), expected_mpn)
        self.assertEqual(self.app.fields_entries["Category"].get(), sym_data["category"])

    def test_clipboard_copy_operations(self):
        """Verifies copy_mpn and copy_digikey write to the system clipboard."""
        first_sym = next(iter(self.app.symbols.keys()))
        self.app.tree.selection_set(first_sym)
        self.app.on_symbol_select(None)

        mpn = self.app.fields_entries["MPN"].get()
        with patch.object(self.app.root, "clipboard_clear") as mock_clear, \
             patch.object(self.app.root, "clipboard_append") as mock_append:
            self.app.copy_mpn()
            mock_clear.assert_called_once()
            mock_append.assert_called_once_with(mpn)

        digikey = self.app.fields_entries["DigiKey"].get()
        with patch.object(self.app.root, "clipboard_clear") as mock_clear, \
             patch.object(self.app.root, "clipboard_append") as mock_append:
            self.app.copy_digikey()
            mock_clear.assert_called_once()
            mock_append.assert_called_once_with(digikey)

    @patch("library_manager_gui.webbrowser.open")
    def test_open_datasheet_valid_url(self, mock_web_open):
        """Verifies open_datasheet launches browser on valid URL."""
        self.app.fields_entries["Datasheet"].set("https://example.com/datasheet.pdf")
        self.app.open_datasheet()
        mock_web_open.assert_called_once_with("https://example.com/datasheet.pdf")

    @patch("library_manager_gui.messagebox.showwarning")
    def test_open_datasheet_invalid_url(self, mock_warning):
        """Verifies open_datasheet warns on invalid URL."""
        self.app.fields_entries["Datasheet"].set("N/A")
        self.app.open_datasheet()
        mock_warning.assert_called_once()

    @patch("library_manager_gui.subprocess.run")
    @patch("library_manager_gui.messagebox.showinfo")
    def test_run_linter_success(self, mock_info, mock_run):
        """Verifies run_linter executes linter_validator.py and notifies user."""
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_run.return_value = mock_proc

        self.app.run_linter()
        self.assertTrue(mock_run.called)
        mock_info.assert_called_once()

    @patch("library_manager_gui.subprocess.run")
    @patch("library_manager_gui.messagebox.showwarning")
    def test_run_linter_failure(self, mock_warn, mock_run):
        """Verifies run_linter displays warning when linter finds issues."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "Rule violation"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        self.app.run_linter()
        self.assertTrue(mock_run.called)
        mock_warn.assert_called_once()

    @patch("library_manager_gui.LibraryParser.save_symbol")
    @patch("library_manager_gui.messagebox.askyesno", return_value=True)
    @patch("library_manager_gui.messagebox.showinfo")
    def test_save_current_symbol_success(self, mock_info, mock_confirm, mock_save):
        """Verifies save_current_symbol validates rules and invokes save_symbol."""
        first_sym = next(iter(self.app.symbols.keys()))
        self.app.tree.selection_set(first_sym)
        self.app.on_symbol_select(None)

        self.app.save_current_symbol()
        self.assertTrue(mock_save.called)
        mock_info.assert_called_once()

    @patch("library_manager_gui.LibraryParser.save_symbol")
    @patch("library_manager_gui.messagebox.showerror")
    def test_save_current_symbol_validation_error(self, mock_error, mock_save):
        """Verifies save_current_symbol blocks save on rule violation."""
        first_sym = next(iter(self.app.symbols.keys()))
        self.app.tree.selection_set(first_sym)
        self.app.on_symbol_select(None)

        # Clear required MPN to force validation failure
        self.app.fields_entries["MPN"].set("")
        self.app.save_current_symbol()
        self.assertFalse(mock_save.called)
        mock_error.assert_called_once()

    @patch("library_manager_gui.LibraryParser.delete_symbol")
    @patch("library_manager_gui.messagebox.askyesno", return_value=True)
    @patch("library_manager_gui.messagebox.showinfo")
    def test_delete_current_symbol_confirmed(self, mock_info, mock_confirm, mock_del):
        """Verifies delete_current_symbol deletes part upon confirmation."""
        first_sym = next(iter(self.app.symbols.keys()))
        self.app.tree.selection_set(first_sym)
        self.app.on_symbol_select(None)

        self.app.delete_current_symbol()
        self.assertTrue(mock_del.called)
        mock_info.assert_called_once()
        self.assertIsNone(self.app.selected_symbol_name)

    @patch("library_manager_gui.LibraryParser.delete_symbol")
    @patch("library_manager_gui.messagebox.askyesno", return_value=False)
    def test_delete_current_symbol_cancelled(self, mock_confirm, mock_del):
        """Verifies delete_current_symbol does not delete part when cancelled."""
        first_sym = next(iter(self.app.symbols.keys()))
        self.app.tree.selection_set(first_sym)
        self.app.on_symbol_select(None)

        self.app.delete_current_symbol()
        self.assertFalse(mock_del.called)
        self.assertEqual(self.app.selected_symbol_name, first_sym)

    @patch("library_manager_gui.create_pull_request_flow")
    def test_create_pr_from_toolbar(self, mock_pr_flow):
        """Verifies toolbar PR button triggers create_pull_request_flow."""
        first_sym = next(iter(self.app.symbols.keys()))
        self.app.tree.selection_set(first_sym)
        self.app.on_symbol_select(None)

        self.app.create_pr_from_toolbar()
        self.assertEqual(mock_pr_flow.call_args.args, (first_sym, self.app.symbols[first_sym]["category"]))
        self.assertIs(mock_pr_flow.call_args.kwargs["root"], self.root)

    @patch("library_manager_gui.webbrowser.open")
    @patch("library_manager_gui.messagebox.showinfo")
    @patch("library_manager_gui.rov_bridge.run_rov")
    def test_git_sync_delegates_to_rov(self, mock_run, mock_info, mock_browser):
        """Verifies git_sync delegates to the shared rov library sync command."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "library is current"
        mock_run.return_value.stderr = ""

        worker = self.app.git_sync()
        self._finish(worker)

        self.assertIn("library", mock_run.call_args.args[1])
        self.assertIn("sync", mock_run.call_args.args[1])
        mock_info.assert_called_once()
        self.assertIn("library is current", _dialog_text(mock_info))
        mock_browser.assert_not_called()

    @patch("library_manager_gui.webbrowser.open")
    @patch("library_manager_gui.messagebox.showinfo")
    @patch("library_manager_gui.rov_bridge.run_rov")
    def test_create_pr_delegates_to_rov(self, mock_run, mock_info, mock_browser):
        """Verifies the pull request flow delegates to rov library contribute."""
        pr_url = "https://github.com/purduerov/purdue-rov-kicad-lib/pull/1"
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = pr_url
        mock_run.return_value.stderr = ""

        library_manager_gui.create_pull_request_flow("TPS54302", "Power")

        args = mock_run.call_args.args[1]
        self.assertIn("contribute", args)
        self.assertIn("--name", args)
        self.assertIn("--push", args)
        self.assertIn("--pr", args)
        # Success feedback is restored: the pull request URL is reported in a
        # message box and opened in the browser.
        mock_info.assert_called_once()
        self.assertIn(pr_url, _dialog_text(mock_info))
        mock_browser.assert_called_once_with(pr_url)

    @patch("library_manager_gui.webbrowser.open")
    @patch("library_manager_gui.messagebox.showinfo")
    @patch("library_manager_gui.rov_bridge.run_rov")
    def test_create_pr_opens_the_browser_only_for_an_http_url(self, mock_run, mock_info, mock_browser):
        """A non-URL summary is reported but never handed to the browser."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "prepared add-part-tps54302-4242 with 1 library file(s)"
        mock_run.return_value.stderr = ""

        library_manager_gui.create_pull_request_flow("TPS54302", "Power")

        mock_info.assert_called_once()
        self.assertIn("add-part-tps54302-4242", _dialog_text(mock_info))
        mock_browser.assert_not_called()

    @patch("library_manager_gui.webbrowser.open")
    @patch("library_manager_gui.messagebox.showerror")
    @patch("library_manager_gui.rov_bridge.run_rov")
    def test_create_pr_reports_a_refusal_without_opening_a_browser(self, mock_run, mock_error, mock_browser):
        """A blocked contribution is shown as an error and opens nothing."""
        mock_run.return_value.returncode = 2
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "[BLOCKED] library-contribute: changes are outside the library directories"

        library_manager_gui.create_pull_request_flow("TPS54302", "Power")

        mock_error.assert_called_once()
        self.assertIn("outside the library directories", _dialog_text(mock_error))
        mock_browser.assert_not_called()

    @patch("library_manager_gui.webbrowser.open")
    @patch("library_manager_gui.messagebox.showerror")
    @patch("library_manager_gui.rov_bridge.run_rov")
    def test_git_sync_reports_a_missing_devops_checkout(self, mock_run, mock_error, mock_browser):
        """A missing DevOps checkout is an actionable dialog, never a direct push."""
        mock_run.side_effect = FileNotFoundError(
            "The Purdue ROV DevOps CLI was not found.\n"
            "Checked:\n  C:/Libraries/.pcb-devops-cache/scripts/rov.py\n"
            "Run LAUNCH_KICAD once, or set ROV_DEVOPS_DIR to the KiCad/DevOps checkout, "
            "then run this action again."
        )

        worker = self.app.git_sync()
        self._finish(worker)

        mock_error.assert_called_once()
        self.assertIn("ROV_DEVOPS_DIR", _dialog_text(mock_error))
        self.assertIn("LAUNCH_KICAD", _dialog_text(mock_error))
        mock_browser.assert_not_called()

    @patch("library_manager_gui.webbrowser.open")
    @patch("library_manager_gui.messagebox.showerror")
    @patch("library_manager_gui.rov_bridge.run_rov")
    def test_git_sync_reports_a_timeout_as_a_failure(self, mock_run, mock_error, mock_browser):
        """A bounded timeout surfaces as an ordinary reported failure."""
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = ""
        mock_run.return_value.stderr = "rov did not finish within 900 seconds"

        worker = self.app.git_sync()
        self._finish(worker)

        mock_error.assert_called_once()
        self.assertIn("did not finish within", _dialog_text(mock_error))
        mock_browser.assert_not_called()

    def _finish(self, worker):
        """Wait for a bridge worker and let the Tk main thread run its callback."""
        if worker is not None:
            worker.join(timeout=10)
            self.assertFalse(worker.is_alive(), "the bridge worker must not block the UI")
        self.root.update()

    @patch("library_manager_gui.ImportPartDialog")
    def test_open_add_part_dialog(self, mock_dialog):
        """Verifies open_add_part_dialog creates ImportPartDialog."""
        self.app.open_add_part_dialog()
        mock_dialog.assert_called_once_with(self.root, callback_on_imported=self.app.refresh_symbols)

    @patch("library_manager_gui.E2ETestDialog")
    def test_open_e2e_test_dialog(self, mock_dialog):
        """Verifies open_e2e_test_dialog creates E2ETestDialog."""
        self.app.open_e2e_test_dialog()
        mock_dialog.assert_called_once_with(self.root)

    @patch("library_manager_gui.E2ETestDialog")
    def test_test_selected_part_in_kicad(self, mock_dialog):
        """Verifies test_selected_part_in_kicad launches targeted dialog."""
        first_sym = next(iter(self.app.symbols.keys()))
        self.app.tree.selection_set(first_sym)
        self.app.on_symbol_select(None)

        self.app.test_selected_part_in_kicad()
        mock_dialog.assert_called_once_with(
            self.root,
            target_part_name=first_sym,
            target_category=self.app.symbols[first_sym]["category"]
        )

    def test_import_part_dialog_watcher_toggle(self):
        """Verifies toggling watcher in ImportPartDialog switches running state."""
        dlg = ImportPartDialog(self.root, callback_on_imported=lambda: None)
        self.assertFalse(dlg.watcher_running)

        dlg.toggle_watcher()
        self.assertTrue(dlg.watcher_running)

        dlg.toggle_watcher()
        self.assertFalse(dlg.watcher_running)
        dlg.on_close()


class FakeRoot:
    """A stand-in Tk root that records ``after`` callbacks instead of running them.

    It needs no display, which is what makes the threading contract testable on a
    headless machine: the worker finishes, the callback is queued, and the test
    decides when the "main thread" runs it.
    """

    def __init__(self):
        self.pending = []

    def after(self, _milliseconds, func, *args):
        self.pending.append((func, args))
        return "after#1"


class TestRovActionThreading(unittest.TestCase):
    """A bridge action must never run the CLI on the Tk main thread.

    These tests create no window and start no real process, so they are safe on a
    headless Linux runner as well as a desktop.
    """

    def test_the_bridge_runs_on_a_worker_and_finishes_on_the_main_thread(self):
        caller = threading.current_thread()
        worker_threads = []
        root = FakeRoot()

        def fake_run(_library_dir, _args, **_kwargs):
            worker_threads.append(threading.current_thread())
            return subprocess.CompletedProcess([], 0, "library is current", "")

        with patch.object(library_manager_gui.rov_bridge, "run_rov", fake_run), patch.object(
            library_manager_gui.messagebox, "showinfo"
        ) as mock_info:
            worker = library_manager_gui._run_rov_action(
                "Git Sync Failed", ["library", "sync"], root=root
            )

            self.assertIsInstance(worker, threading.Thread)
            self.assertTrue(worker.daemon, "the worker must not keep the app alive")
            worker.join(timeout=10)
            self.assertFalse(worker.is_alive())
            self.assertEqual(len(worker_threads), 1)
            self.assertIsNot(worker_threads[0], caller, "the CLI must not run on the caller's thread")
            # Nothing is reported until the main thread runs the queued callback.
            mock_info.assert_not_called()
            self.assertEqual(len(root.pending), 1)

            root.pending.pop(0)[0]()

        mock_info.assert_called_once()
        self.assertIn("library is current", _dialog_text(mock_info))

    def test_the_worker_is_given_a_bounded_timeout(self):
        captured = {}

        def fake_run(_library_dir, _args, **kwargs):
            captured.update(kwargs)
            return subprocess.CompletedProcess([], 0, "ok", "")

        root = FakeRoot()
        with patch.object(library_manager_gui.rov_bridge, "run_rov", fake_run):
            worker = library_manager_gui._run_rov_action("t", ["library", "sync"], root=root)
            worker.join(timeout=10)

        timeout = captured.get("timeout")
        self.assertIsInstance(timeout, (int, float), f"no bounded timeout was passed: {captured}")
        self.assertGreater(timeout, 0)

    def test_a_failed_worker_still_reports_on_the_main_thread(self):
        root = FakeRoot()

        def fake_run(_library_dir, _args, **_kwargs):
            return subprocess.CompletedProcess([], 2, "", "[BLOCKED] library-sync: local changes")

        with patch.object(library_manager_gui.rov_bridge, "run_rov", fake_run), patch.object(
            library_manager_gui.messagebox, "showerror"
        ) as mock_error:
            worker = library_manager_gui._run_rov_action("Git Sync Failed", ["library", "sync"], root=root)
            worker.join(timeout=10)
            self.assertEqual(len(root.pending), 1)
            root.pending.pop(0)[0]()

        mock_error.assert_called_once()
        self.assertIn("local changes", _dialog_text(mock_error))

    def test_an_unexpected_worker_error_is_reported_not_raised(self):
        root = FakeRoot()

        def fake_run(*_args, **_kwargs):
            raise OSError("the interpreter could not be started")

        with patch.object(library_manager_gui.rov_bridge, "run_rov", fake_run), patch.object(
            library_manager_gui.messagebox, "showerror"
        ) as mock_error:
            worker = library_manager_gui._run_rov_action("t", ["library", "sync"], root=root)
            worker.join(timeout=10)
            root.pending.pop(0)[0]()

        mock_error.assert_called_once()
        self.assertIn("could not be started", _dialog_text(mock_error))

    def test_without_a_root_the_action_stays_synchronous(self):
        """A caller with no Tk window still gets a completed result."""
        with patch.object(library_manager_gui.rov_bridge, "run_rov") as mock_run, patch.object(
            library_manager_gui.messagebox, "showinfo"
        ) as mock_info:
            mock_run.return_value = subprocess.CompletedProcess([], 0, "library is current", "")
            outcome = library_manager_gui._run_rov_action("t", ["library", "sync"])

        self.assertIs(outcome, True)
        mock_info.assert_called_once()


class _Var:
    """A stand-in for a ``tk.StringVar`` that needs no display."""

    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value


class _FakeImportDialog:
    """A stand-in ``ImportPartDialog`` that needs no window.

    ``process_import`` is exercised as an unbound function against this object, so
    the call site that decides how the pull request is launched is tested without
    a Toplevel, a grab_set, or a display.
    """

    def __init__(self, parent, symbol_file, part_name, category="Power"):
        self.parent = parent
        self.dialog = None
        self.selected_category = _Var(category)
        self.entries = {
            "MPN": _Var(part_name),
            "Manufacturer": _Var("Test Vendor"),
            "DigiKey": _Var("000-00000-ND"),
            "Datasheet": _Var("https://example.invalid/datasheet.pdf"),
            "Temp_Range": _Var("-40C to 125C"),
        }
        self.sym_file = symbol_file
        self.fp_file = None
        self.model_3d_file = None
        self.callback_on_imported = None
        self.closed = False

    def on_close(self):
        self.closed = True


class TestImportDialogPullRequestRoot(unittest.TestCase):
    """The import dialog must not run the contribution on the main thread.

    ``process_import(open_pr=True)`` closes its Toplevel before launching the
    contribution, so it cannot pass the Toplevel as the Tk root. It has to pass
    the application parent it was constructed with, which keeps the worker
    thread and ``root.after(0, ...)`` path in use. No display, process, or
    remote is involved.
    """

    def setUp(self):
        temp_dir = tempfile.mkdtemp(prefix="rov-import-dialog-")
        self.addCleanup(shutil.rmtree, temp_dir, True)
        self.part_name = "ZZDIALOG-IMPORT-0001"
        symbol_file = Path(temp_dir) / "part.kicad_sym"
        # The same text is handed to the real extract/rename/inject helpers, so
        # the symbol name, and therefore the part name sent to the CLI, is the one
        # these tests assert on.
        self.symbol_text = (
            '(kicad_symbol_lib\n  (version 20211014)\n'
            f'  (symbol "{self.part_name}"\n'
            f'    (property "MPN" "{self.part_name}" (id 5) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
            '    (property "Manufacturer" "Test Vendor" (id 6) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
            '    (property "DigiKey" "000-00000-ND" (id 7) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
            '    (property "Datasheet" "https://example.invalid/datasheet.pdf" (id 3) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
            '    (property "Temp_Range" "-40C to 125C" (id 8) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
            '    (property "Category" "Power" (id 4) (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
            '  )\n)\n'
        )
        symbol_file.write_text(self.symbol_text, encoding="utf-8")
        self.app_root = FakeRoot()
        self.dialog = _FakeImportDialog(self.app_root, symbol_file, self.part_name)

    def _import_and_capture(self, open_pr=True):
        """Run ``process_import`` and return the recorded pull request call."""
        recorded = {}
        real_flow = library_manager_gui.create_pull_request_flow
        threads = {}

        def spy(component_name, category, root=None):
            recorded["component_name"] = component_name
            recorded["category"] = category
            recorded["root"] = root
            recorded["root_given"] = root is not None
            threads["call_site"] = threading.current_thread()
            return real_flow(component_name, category, root=root)

        def fake_run(_library_dir, _args, **_kwargs):
            # Where the CLI actually ran is the thing under test.
            threads["bridge"] = threading.current_thread()
            return subprocess.CompletedProcess(
                [], 0, "https://github.com/purduerov/purdue-rov-kicad-lib/pull/9", ""
            )

        with patch.object(library_manager_gui, "create_pull_request_flow", spy), patch.object(
            library_manager_gui.rov_bridge, "run_rov", fake_run
        ), patch.object(library_manager_gui, "validate_component_rules", return_value=([], [])), patch.object(
            library_manager_gui, "validate_sexpr", return_value=(True, "")
        ), patch.object(library_manager_gui.LibraryParser, "insert_symbol") as mock_insert, patch.object(
            library_manager_gui.messagebox, "showinfo"
        ) as mock_info, patch.object(
            # An error or a confirmation prompt here would block on a modal window
            # forever in a headless run, so both are captured and asserted on.
            library_manager_gui.messagebox, "showerror"
        ) as mock_error, patch.object(
            library_manager_gui.messagebox, "askyesno", return_value=True
        ) as mock_confirm, patch.object(
            library_manager_gui.webbrowser, "open"
        ) as mock_browser:
            library_manager_gui.ImportPartDialog.process_import(self.dialog, open_pr=open_pr)
            self._drain_worker()
            recorded["threads"] = threads
            recorded["inserted"] = mock_insert
            recorded["info"] = mock_info
            recorded["error"] = mock_error
            recorded["confirm"] = mock_confirm
            recorded["browser"] = mock_browser
        # The import must have reached the save step, not bailed out early.
        self.assertEqual(
            mock_error.call_args_list,
            [],
            f"process_import reported an error instead of importing: {mock_error.call_args_list}",
        )
        return recorded

    def _drain_worker(self):
        """Let the worker finish and run the callback it queued on the fake root."""
        deadline = time.monotonic() + 10
        while not self.app_root.pending and time.monotonic() < deadline:
            time.sleep(0.01)
        for callback, _args in list(self.app_root.pending):
            callback()
        self.app_root.pending.clear()

    def test_open_pr_passes_the_application_root(self):
        """The application parent, not the destroyed Toplevel, is the Tk root."""
        recorded = self._import_and_capture(open_pr=True)

        self.assertTrue(self.dialog.closed, "the import dialog closes before the PR flow")
        self.assertTrue(recorded.get("root_given"), "no root was passed to create_pull_request_flow")
        self.assertIs(
            recorded["root"],
            self.app_root,
            "the application parent root must be the Tk root, not the closed Toplevel",
        )
        self.assertIsNot(recorded["root"], self.dialog.dialog)
        self.assertEqual(recorded["component_name"], self.part_name)
        self.assertEqual(recorded["category"], "Power")
        # The whole point: the CLI did not run on the caller's thread.
        self.assertIsNot(
            recorded["threads"]["bridge"],
            recorded["threads"]["call_site"],
            "the contribution ran on the caller's thread instead of a worker",
        )

    def test_open_pr_reports_through_the_main_thread_and_opens_the_pull_request(self):
        """The threaded path is used and the restored feedback still happens."""
        recorded = self._import_and_capture(open_pr=True)

        recorded["info"].assert_called_once()
        self.assertIn("pull/9", _dialog_text(recorded["info"]))
        recorded["browser"].assert_called_once_with(
            "https://github.com/purduerov/purdue-rov-kicad-lib/pull/9"
        )

    def test_open_pr_does_not_write_to_the_real_symbol_files(self):
        """The call site is exercised without touching the real library."""
        recorded = self._import_and_capture(open_pr=True)

        recorded["inserted"].assert_called_once()

    def test_without_open_pr_no_pull_request_is_launched(self):
        """The plain import path is unchanged and launches nothing."""
        recorded = self._import_and_capture(open_pr=False)

        self.assertNotIn("root_given", recorded)
        self.assertEqual(self.app_root.pending, [])


if __name__ == "__main__":
    unittest.main()
