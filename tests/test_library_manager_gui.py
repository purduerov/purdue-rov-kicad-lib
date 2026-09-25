#!/usr/bin/env python3
"""
Comprehensive Headless Button and Flow Integration Test Suite for LibraryManagerApp.
Verifies all buttons, callbacks, filters, and dialog flows headlessly.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tkinter as tk

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

import library_manager_gui
from library_manager_gui import LibraryManagerApp, ImportPartDialog, E2ETestDialog


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
        mock_pr_flow.assert_called_once_with(first_sym, self.app.symbols[first_sym]["category"])

    @patch("library_manager_gui.rov_bridge.run_rov")
    def test_git_sync_delegates_to_rov(self, mock_run):
        """Verifies git_sync delegates to the shared rov library sync command."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "library is current"
        mock_run.return_value.stderr = ""
        self.app.git_sync()
        self.assertIn("library", mock_run.call_args.args[1])
        self.assertIn("sync", mock_run.call_args.args[1])

    @patch("library_manager_gui.rov_bridge.run_rov")
    def test_create_pr_delegates_to_rov(self, mock_run):
        """Verifies the pull request flow delegates to rov library contribute."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "https://github.com/purduerov/purdue-rov-kicad-lib/pull/1"
        mock_run.return_value.stderr = ""
        library_manager_gui.create_pull_request_flow("TPS54302", "Power")
        args = mock_run.call_args.args[1]
        self.assertIn("contribute", args)
        self.assertIn("--name", args)
        self.assertIn("--push", args)
        self.assertIn("--pr", args)

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


if __name__ == "__main__":
    unittest.main()
