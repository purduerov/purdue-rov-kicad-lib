#!/usr/bin/env python3
"""
Test suite verifying thread safety and graceful window teardown across
all asynchronous Tkinter dialogs in library_manager_gui.py.
"""

import sys
import time
import unittest
from pathlib import Path
import tkinter as tk

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

from unittest.mock import patch
from library_manager_gui import E2ETestDialog, ImportPartDialog

class TestGuiThreadSafety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception as e:
            raise unittest.SkipTest(f"Tkinter display initialization not available: {e}")

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "root") and cls.root:
            try:
                cls.root.destroy()
            except Exception:
                pass

    @patch("library_manager_gui.verify_all_library_parts")
    def test_e2e_dialog_immediate_close_during_verify_all(self, mock_verify):
        """Spawns verify_all worker and immediately closes dialog; must not raise TclError."""
        mock_verify.return_value = {
            "total": 1, "passed": 1, "failed": 0, "all_passed": True,
            "results": [{"category": "Power", "part": "TEST_PART", "passed": True, "details": []}]
        }
        dlg = E2ETestDialog(self.root)
        self.assertFalse(dlg.is_closed)
        dlg.start_verify_all()
        self.assertTrue(dlg.is_running)

        # Immediately simulate user clicking 'X' window close button
        dlg.on_close()
        self.assertTrue(dlg.is_closed)
        
        # Give worker thread a moment to run and hit append_log/set_status
        time.sleep(0.1)
        self.root.update()

        # Calling append_log and set_status on destroyed dialog must safely no-op
        dlg.append_log("Post-destruction log entry", "info")
        dlg.set_status("Post-destruction status")

    @patch("library_manager_gui.run_e2e_addition_test")
    def test_e2e_dialog_immediate_close_during_simulated_test(self, mock_test):
        """Spawns simulated addition worker and immediately closes dialog; must not raise TclError."""
        mock_test.return_value = {
            "success": True,
            "steps": [{"step": "Add part", "passed": True, "details": "Success"}]
        }
        dlg = E2ETestDialog(self.root)
        dlg.start_simulated_test()
        dlg.on_close()
        self.assertTrue(dlg.is_closed)
        time.sleep(0.1)
        self.root.update()

    def test_import_part_dialog_watcher_thread_teardown(self):
        """Starts downloads watcher and closes dialog; watcher must stop cleanly."""
        dlg = ImportPartDialog(self.root, callback_on_imported=lambda: None)
        dlg.toggle_watcher()
        self.assertTrue(dlg.watcher_running)

        dlg.on_close()
        self.assertFalse(dlg.watcher_running)
        time.sleep(0.2)
        self.root.update()

if __name__ == "__main__":
    unittest.main()
