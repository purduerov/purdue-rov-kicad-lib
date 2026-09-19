"""
Purdue ROV KiCad Tools - Dependency Check & Bootstrap Helper
Ensures all required Python packages (like tkinter, etc.) are available.
If a package is missing, prompts the user or automatically installs it via pip,
handling modern PEP 668 externally-managed environments (Homebrew, Linux distros).
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

def _try_pip_install(pkg_names):
    """
    Attempts pip install.
    If PEP 668 externally managed environment is encountered (e.g. Homebrew on macOS),
    retries with --break-system-packages or gives brew instructions.
    """
    base_cmd = [sys.executable, "-m", "pip", "install"] + pkg_names
    
    # 1. Standard attempt
    res = subprocess.run(base_cmd, capture_output=True, text=True)
    if res.returncode == 0:
        return True, ""

    err_output = (res.stderr or "") + (res.stdout or "")
    
    # 2. Check for PEP 668 (externally-managed-environment)
    if "externally-managed-environment" in err_output:
        # Retry with --break-system-packages (standard user CLI tool override)
        break_cmd = base_cmd + ["--break-system-packages"]
        res_break = subprocess.run(break_cmd, capture_output=True, text=True)
        if res_break.returncode == 0:
            return True, ""
        
        # If that also failed, provide clear platform-specific guidance
        if sys.platform == "darwin":
            brew_pkgs = " ".join([f"python-{p}" for p in pkg_names])
            return False, (
                f"Your Python environment is managed by Homebrew (PEP 668).\n"
                f"Please run:\n"
                f"  brew install {brew_pkgs}\n"
                f"or run with --break-system-packages:\n"
                f"  {' '.join(break_cmd)}"
            )

    return False, err_output.strip()

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
        elif sys.platform == "darwin":
            msg = (
                "Python 'tkinter' is missing on macOS!\n\n"
                "To install it via Homebrew, run:\n"
                "  brew install python-tk"
            )
        else:
            msg = (
                "Python 'tkinter' is missing!\n\n"
                "On Linux, install it via your package manager:\n"
                "  Ubuntu/Debian: sudo apt-get install python3-tk\n"
                "  Fedora:        sudo dnf install python3-tkinter\n"
                "  Arch:          sudo pacman -S tk"
            )
        _show_error_dialog("Missing Dependency: tkinter", msg)
        if not missing_pip:
            return False

    # Handle standard pip-installable modules
    if missing_pip:
        pkg_names = [p[1] for p in missing_pip]
        pkg_list_str = ", ".join(pkg_names)

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
            success, err_msg = _try_pip_install(pkg_names)
            if success:
                print("Installation successful!")
                return True
            else:
                _show_error_dialog("Installation Failed", f"Failed to install {pkg_list_str}:\n{err_msg}")
                return False
        else:
            print(f"Skipping installation. Please install manually: {pkg_list_str}")
            return False

    return len(missing_special) == 0

if __name__ == "__main__":
    ensure_dependencies({"tkinter": None})
    print("Dependencies verified successfully.")
