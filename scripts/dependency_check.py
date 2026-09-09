"""
Purdue ROV KiCad Tools - Dependency Check & Bootstrap Helper
Ensures all required Python packages (like tkinter, requests, etc.) are available.
If a package is missing, prompts the user or automatically installs it via pip.
"""

import sys
import os
import subprocess
import importlib

def _prompt_user_yes_no(title, message):
    """
    Prompts the user with Yes/No.
    Uses Win32 native MessageBox on Windows if available,
    falls back to console input.
    """
    if sys.platform == "win32":
        try:
            import ctypes
            # MB_YESNO (0x04) | MB_ICONQUESTION (0x20) | MB_SYSTEMMODAL (0x1000)
            res = ctypes.windll.user32.MessageBoxW(0, message, title, 0x00000004 | 0x00000020 | 0x00001000)
            return res == 6
        except Exception:
            pass

    # Terminal prompt fallback
    print(f"\n[{title}]")
    print(message)
    try:
        ans = input("Do you want to proceed? [Y/n]: ").strip().lower()
        return ans in ("", "y", "yes")
    except Exception:
        return False

def _show_error_dialog(title, message):
    """Shows an error dialog using native Win32 or console."""
    if sys.platform == "win32":
        try:
            import ctypes
            # MB_OK (0x00) | MB_ICONERROR (0x10) | MB_SYSTEMMODAL (0x1000)
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x00000010 | 0x00001000)
            return
        except Exception:
            pass
    print(f"\n[ERROR: {title}]\n{message}\n", file=sys.stderr)

def ensure_dependencies(packages, auto_install=False, prompt_if_missing=True):
    """
    Checks that the specified Python modules can be imported.
    If missing and prompt_if_missing is True:
        Prompts the user to install them (or installs automatically if auto_install is True).
    If tkinter is missing on Windows/Linux:
        Gives OS-specific guidance because tkinter cannot be pip-installed directly.
    
    packages: dict of {import_name: pip_package_name}
    e.g. {'requests': 'requests', 'tkinter': None}
    """
    missing_pip = []
    missing_special = []

    for mod_name, pip_name in packages.items():
        try:
            importlib.import_module(mod_name)
        except ImportError:
            if pip_name:
                missing_pip.append((mod_name, pip_name))
            else:
                missing_special.append(mod_name)

    if not missing_pip and not missing_special:
        return True

    # Handle special modules like tkinter
    if "tkinter" in missing_special:
        if sys.platform == "win32":
            msg = (
                "Python 'tkinter' is missing or not installed!\n\n"
                "On Windows, tkinter is included with the official Python installer.\n"
                "To fix this:\n"
                "1. Open Windows 'Add or remove programs' (Settings > Installed Apps)\n"
                "2. Find Python, click the 3 dots (...) and choose 'Modify'\n"
                "3. Ensure 'tcl/tk and IDLE' is checked and click Next/Install."
            )
        else:
            msg = (
                "Python 'tkinter' is missing!\n\n"
                "On Linux/macOS, install it via your package manager:\n"
                "  Ubuntu/Debian: sudo apt-get install python3-tk\n"
                "  Fedora:        sudo dnf install python3-tkinter\n"
                "  Arch:          sudo pacman -S tk\n"
                "  Homebrew:      brew install python-tk"
            )
        _show_error_dialog("Missing Dependency: tkinter", msg)
        if not missing_pip:
            return False

    # Handle standard pip-installable modules
    if missing_pip:
        pkg_names = [p[1] for p in missing_pip]
        pkg_list_str = ", ".join(pkg_names)
        install_cmd = [sys.executable, "-m", "pip", "install"] + pkg_names

        should_install = auto_install
        if not should_install and prompt_if_missing:
            prompt_msg = (
                f"The following required Python library is missing:\n\n"
                f"  {pkg_list_str}\n\n"
                f"Would you like to install it automatically now via pip?"
            )
            should_install = _prompt_user_yes_no("Missing Python Library", prompt_msg)

        if should_install:
            print(f"Installing missing libraries ({pkg_list_str})...")
            try:
                subprocess.check_call(install_cmd)
                print("Installation successful!")
                return True
            except subprocess.CalledProcessError as e:
                err_msg = f"Failed to install {pkg_list_str}.\nError code: {e.returncode}\nRun manually: {' '.join(install_cmd)}"
                _show_error_dialog("Installation Failed", err_msg)
                return False
        else:
            print(f"Skipping installation. Please install manually using: {' '.join(install_cmd)}")
            return False

    return len(missing_special) == 0

if __name__ == "__main__":
    ensure_dependencies({"tkinter": None, "requests": "requests"})
    print("Dependencies verified successfully.")
