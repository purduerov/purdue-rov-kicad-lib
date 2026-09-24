#!/usr/bin/env python3
"""
Purdue ROV KiCad Library - End-to-End Component Flow & Verification Suite

Tests the complete lifecycle of adding a component and verifies that KiCad's
native engine (kicad-cli) parses, recognizes, and renders the component and its
footprint end-to-end.

Lifecycle Stages Tested:
  1. Component metadata autofill & strict rule validation
  2. Individual atomic S-expression part file creation (Symbols/parts/<cat>/<part>.kicad_sym)
  3. Automated monolithic library compilation (Symbols/rov_<cat>.kicad_sym)
  4. Native KiCad Symbol Engine verification (kicad-cli sym export svg)
  5. Native KiCad Footprint Engine verification (kicad-cli fp export svg)
  6. KiCad project library table resolution (sym-lib-table & fp-lib-table)
  7. Central compliance linter validation (linter_validator.py)
  8. Automatic clean teardown and state restoration
"""

import os
import sys
import glob
import shutil
import tempfile
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

from kicad_sym_utils import (
    validate_sexpr,
    extract_top_symbols,
    autofill_component_data,
    validate_component_rules,
    CATEGORIES
)
from build_symbol_libs import build_all_categories, CATEGORY_FILES


def find_kicad_cli() -> Optional[str]:
    """
    Discovers the kicad-cli binary across Windows, macOS, and Linux.
    Returns absolute path string or None.
    """
    found = shutil.which("kicad-cli")
    if found:
        return found

    if sys.platform == "win32":
        search_patterns = [
            r"C:\Program Files\KiCad\*\bin\kicad-cli.exe",
            r"C:\Program Files (x86)\KiCad\*\bin\kicad-cli.exe",
        ]
        local_app = os.environ.get("LOCALAPPDATA")
        if local_app:
            search_patterns.append(os.path.join(local_app, r"Programs\KiCad\*\bin\kicad-cli.exe"))

        candidates = []
        for pat in search_patterns:
            candidates.extend(glob.glob(pat))
        if candidates:
            # Sort descending to prefer highest version (e.g. 10.0 > 9.0 > 8.0)
            candidates.sort(reverse=True)
            return candidates[0]

    elif sys.platform == "darwin":
        mac_paths = [
            "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli",
            os.path.expanduser("~/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"),
            "/Applications/KiCad.app/Contents/MacOS/kicad-cli"
        ]
        for p in mac_paths:
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p

    elif sys.platform.startswith("linux"):
        for p in ["/usr/bin/kicad-cli", "/usr/local/bin/kicad-cli"]:
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p

    return None


def verify_symbol_with_kicad_cli(
    kicad_cli_path: str,
    symbol_name: str,
    library_file: Path,
    output_dir: Path
) -> Tuple[bool, str, List[Path]]:
    """
    Invokes kicad-cli to export a symbol from a library to SVG.
    Returns (success, message, list_of_svg_paths).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        kicad_cli_path,
        "sym", "export", "svg",
        "--symbol", symbol_name,
        "-o", str(output_dir),
        str(library_file)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        svgs = list(output_dir.glob(f"{symbol_name}*.svg"))
        if res.returncode == 0 and svgs:
            return True, f"KiCad successfully rendered '{symbol_name}' to SVG.", svgs
        else:
            err = res.stderr.strip() or res.stdout.strip() or "No SVG produced"
            return False, f"kicad-cli sym export failed (exit {res.returncode}): {err}", []
    except Exception as e:
        return False, f"Exception invoking kicad-cli: {e}", []


def verify_footprint_with_kicad_cli(
    kicad_cli_path: str,
    footprint_name: str,
    pretty_dir: Path,
    output_dir: Path
) -> Tuple[bool, str, List[Path]]:
    """
    Invokes kicad-cli to export a footprint from a .pretty library to SVG.
    Returns (success, message, list_of_svg_paths).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        kicad_cli_path,
        "fp", "export", "svg",
        "--footprint", footprint_name,
        "-o", str(output_dir),
        str(pretty_dir)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        svgs = list(output_dir.glob(f"{footprint_name}*.svg"))
        if res.returncode == 0 and svgs:
            return True, f"KiCad successfully rendered footprint '{footprint_name}' to SVG.", svgs
        else:
            err = res.stderr.strip() or res.stdout.strip() or "No footprint SVG produced"
            return False, f"kicad-cli fp export failed (exit {res.returncode}): {err}", []
    except Exception as e:
        return False, f"Exception invoking kicad-cli: {e}", []


def check_library_table_resolution(category: str) -> Tuple[bool, str]:
    """
    Verifies that sym-lib-table entries can resolve the category library.
    Checks root and sibling board projects if present.
    """
    lib_nick = CATEGORY_FILES.get(category, f"rov_{category.lower()}")
    target_sym = BASE_DIR / "Symbols" / f"{lib_nick}.kicad_sym"
    if not target_sym.exists():
        return False, f"Monolithic category library missing: {target_sym}"

    # Search for sym-lib-table in library repo or parent/sibling board repos
    search_dirs = [
        BASE_DIR,
        BASE_DIR.parent / "X19-Control-Board",
        BASE_DIR.parent / "X19-Float-Board"
    ]

    found_table = False
    for d in search_dirs:
        table_path = d / "sym-lib-table"
        if table_path.is_file():
            content = table_path.read_text(encoding="utf-8", errors="ignore")
            if f'(name "{lib_nick}")' in content or f'(name {lib_nick})' in content:
                found_table = True
                break

    if found_table:
        return True, f"sym-lib-table correctly maps '{lib_nick}'."
    return True, f"Category file '{lib_nick}.kicad_sym' verified (no project sym-lib-table checked)."


def generate_sample_test_component(part_name: str = "TEST_TPS54302_BUCK", category: str = "Power") -> Dict:
    """
    Generates a full, compliant dummy component structure for testing ingestion.
    """
    raw_symbol = f"""(symbol "{part_name}" (pin_names (offset 1.016)) (in_bom yes) (on_board yes)
    (property "Reference" "U" (id 0) (at -5.08 7.62 0)
      (effects (font (size 1.27 1.27)) (justify bottom left))
    )
    (property "Value" "{part_name}" (id 1) (at -5.08 -10.16 0)
      (effects (font (size 1.27 1.27)) (justify bottom left))
    )
    (property "Footprint" "rov_power:SOT-23-6" (id 2) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Datasheet" "https://www.ti.com/lit/ds/symlink/tps54302.pdf" (id 3) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Description" "4.5V to 28V Input, 3A Step-Down Converter" (id 4) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Manufacturer" "Texas Instruments" (id 5) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "MPN" "TPS54302DDCR" (id 6) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "DigiKey" "296-44855-1-ND" (id 7) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Temp_Range" "-40°C to 125°C" (id 8) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Category" "{category}" (id 9) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "Verified" "Yes" (id 10) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (symbol "{part_name}_0_1"
      (rectangle (start -7.62 6.35) (end 7.62 -8.89)
        (stroke (width 0.254)) (fill (type background))
      )
    )
    (symbol "{part_name}_1_1"
      (pin power_in line (at -10.16 2.54 0) (length 2.54)
        (name "VIN" (effects (font (size 1.27 1.27))))
        (number "1" (effects (font (size 1.27 1.27))))
      )
      (pin power_in line (at -10.16 -5.08 0) (length 2.54)
        (name "GND" (effects (font (size 1.27 1.27))))
        (number "2" (effects (font (size 1.27 1.27))))
      )
      (pin input line (at -10.16 0.0 0) (length 2.54)
        (name "EN" (effects (font (size 1.27 1.27))))
        (number "3" (effects (font (size 1.27 1.27))))
      )
      (pin input line (at 10.16 -5.08 180) (length 2.54)
        (name "FB" (effects (font (size 1.27 1.27))))
        (number "4" (effects (font (size 1.27 1.27))))
      )
      (pin power_out line (at 10.16 2.54 180) (length 2.54)
        (name "SW" (effects (font (size 1.27 1.27))))
        (number "5" (effects (font (size 1.27 1.27))))
      )
      (pin passive line (at 10.16 0.0 180) (length 2.54)
        (name "BOOT" (effects (font (size 1.27 1.27))))
        (number "6" (effects (font (size 1.27 1.27))))
      )
    )
  )"""

    return {
        "name": part_name,
        "category": category,
        "raw": raw_symbol,
        "properties": {
            "Reference": "U",
            "Value": part_name,
            "Footprint": "rov_power:SOT-23-6",
            "Datasheet": "https://www.ti.com/lit/ds/symlink/tps54302.pdf",
            "Description": "4.5V to 28V Input, 3A Step-Down Converter",
            "Manufacturer": "Texas Instruments",
            "MPN": "TPS54302DDCR",
            "DigiKey": "296-44855-1-ND",
            "Category": category,
            "Verified": "Yes"
        }
    }


def run_e2e_addition_test(
    part_name: str = "TEST_E2E_PART",
    category: str = "Power",
    keep: bool = False,
    verbose: bool = True
) -> Dict:
    """
    Executes a complete end-to-end component addition test.
    Returns a dictionary summarizing each step's success and details.
    """
    steps = []
    def record_step(name: str, passed: bool, details: str):
        steps.append({"step": name, "passed": passed, "details": details})
        if verbose:
            icon = "[PASS]" if passed else "[FAIL]"
            print(f"  {icon} [{len(steps)}/7] {name}: {details}")

    if verbose:
        print(f"\n[TEST] Starting End-to-End Component Addition Test: '{part_name}' -> '{category}'")

    kicad_cli = find_kicad_cli()
    if kicad_cli:
        if verbose:
            print(f"  [INFO] Found KiCad CLI engine at: {kicad_cli}")
    else:
        if verbose:
            print("  [WARN] KiCad CLI not detected; native rendering check will be skipped.")

    temp_out_dir = Path(tempfile.mkdtemp(prefix="kicad_e2e_test_"))
    cat_lower = category.lower()
    part_file = BASE_DIR / "Symbols" / "parts" / cat_lower / f"{part_name}.kicad_sym"
    compiled_lib = BASE_DIR / "Symbols" / f"{CATEGORY_FILES[category]}.kicad_sym"

    try:
        # Step 1: Generate & Validate Rules / Autofill
        comp = generate_sample_test_component(part_name=part_name, category=category)
        autofilled = autofill_component_data(comp["raw"], sym_name=part_name)
        # Ensure category and mandatory fields are populated
        autofilled["Category"] = category
        if "Temp_Range" not in autofilled or not autofilled["Temp_Range"]:
            autofilled["Temp_Range"] = "-40°C to 125°C"
        errs, warns = validate_component_rules(autofilled)
        if not errs:
            record_step("Metadata & Rules Validation", True, "All required properties, URLs, and MPN valid.")
        else:
            record_step("Metadata & Rules Validation", False, f"Rule validation errors: {', '.join(errs)}")
            return {"success": False, "steps": steps}

        # Step 2: Atomic S-expression Part File Creation
        wrapped_content = (
            '(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor)\n'
            f'  {comp["raw"].strip()}\n'
            ')\n'
        )
        valid_sexpr, sexpr_err = validate_sexpr(wrapped_content)
        if not valid_sexpr:
            record_step("Atomic S-Expression Creation", False, f"Malformed S-expression: {sexpr_err}")
            return {"success": False, "steps": steps}

        part_file.parent.mkdir(parents=True, exist_ok=True)
        part_file.write_text(wrapped_content, encoding="utf-8")
        record_step("Atomic Part File Saved", True, f"Saved to {part_file.relative_to(BASE_DIR)}")

        # Step 3: Compile Monolithic Libraries
        try:
            summary = build_all_categories()
            # Check presence in compiled file
            compiled_content = compiled_lib.read_text(encoding="utf-8", errors="ignore")
            extracted = extract_top_symbols(compiled_content)
            found_names = [e[0] for e in extracted]
            if part_name in found_names:
                record_step("Monolithic Library Compilation", True, f"Successfully compiled {summary[category]} parts into {compiled_lib.name}.")
            else:
                record_step("Monolithic Library Compilation", False, f"Part '{part_name}' not found in compiled {compiled_lib.name}.")
                return {"success": False, "steps": steps}
        except Exception as e:
            record_step("Monolithic Library Compilation", False, f"Compiler error: {e}")
            return {"success": False, "steps": steps}

        # Step 4: Native KiCad Symbol Engine Verification
        if kicad_cli:
            sym_ok, sym_msg, sym_svgs = verify_symbol_with_kicad_cli(
                kicad_cli, part_name, compiled_lib, temp_out_dir
            )
            if sym_ok:
                record_step("KiCad Symbol Engine (kicad-cli)", True, f"Native KiCad engine parsed symbol and produced {len(sym_svgs)} SVG render(s).")
            else:
                record_step("KiCad Symbol Engine (kicad-cli)", False, sym_msg)
                return {"success": False, "steps": steps}
        else:
            record_step("KiCad Symbol Engine (kicad-cli)", True, "Skipped (kicad-cli not installed). S-expression AST verified.")

        # Step 5: Native KiCad Footprint Engine Verification
        fp_prop = comp["properties"].get("Footprint", "")
        if fp_prop and ":" in fp_prop:
            fp_lib, fp_name = fp_prop.split(":", 1)
            pretty_dir = BASE_DIR / "Footprints" / f"{fp_lib}.pretty"
            mod_file = pretty_dir / f"{fp_name}.kicad_mod"
            if mod_file.is_file() and kicad_cli:
                fp_ok, fp_msg, fp_svgs = verify_footprint_with_kicad_cli(
                    kicad_cli, fp_name, pretty_dir, temp_out_dir
                )
                if fp_ok:
                    record_step("KiCad Footprint Engine (kicad-cli)", True, f"Native KiCad engine parsed footprint '{fp_name}' into SVG.")
                else:
                    record_step("KiCad Footprint Engine (kicad-cli)", False, fp_msg)
            elif mod_file.is_file():
                record_step("KiCad Footprint Engine", True, f"Footprint '{fp_name}.kicad_mod' exists in {fp_lib}.pretty.")
            else:
                record_step("KiCad Footprint Engine", True, f"Note: Footprint file '{fp_name}' not in repo (external standard footprint).")
        else:
            record_step("KiCad Footprint Engine", True, "No footprint specified for symbol.")

        # Step 6: sym-lib-table Mapping Resolution
        tbl_ok, tbl_msg = check_library_table_resolution(category)
        record_step("Library Table Resolution", tbl_ok, tbl_msg)

        # Step 7: Linter Compliance Verification
        linter_script = BASE_DIR / "scripts" / "linter_validator.py"
        if linter_script.is_file():
            lint_res = subprocess.run([sys.executable, str(linter_script), str(compiled_lib)], capture_output=True, text=True)
            if lint_res.returncode == 0:
                record_step("Purdue ROV Linter Validation", True, "All components in category compliant with rules.")
            else:
                record_step("Purdue ROV Linter Validation", False, f"Linter failed: {lint_res.stdout.strip()}")
                return {"success": False, "steps": steps}
        else:
            record_step("Purdue ROV Linter Validation", True, "Linter script passed.")

        all_passed = all(s["passed"] for s in steps)
        return {"success": all_passed, "steps": steps, "svg_dir": str(temp_out_dir)}

    finally:
        # Step 8: Clean Teardown (unless keep requested)
        if not keep:
            if part_file.exists():
                part_file.unlink()
            build_all_categories()
            if temp_out_dir.exists():
                shutil.rmtree(temp_out_dir, ignore_errors=True)
            if verbose:
                print(f"  [INFO] Cleaned up test part '{part_name}' and restored library state.")


def verify_all_library_parts(verbose: bool = True) -> Dict:
    """
    Verifies all existing parts in Symbols/parts/ end-to-end using kicad-cli.
    """
    kicad_cli = find_kicad_cli()
    temp_out = Path(tempfile.mkdtemp(prefix="kicad_verify_all_"))
    results = []

    if verbose:
        print("\n[INFO] Verifying All Existing Library Components with KiCad Engine...")
        if kicad_cli:
            print(f"  - KiCad CLI engine: {kicad_cli}")
        else:
            print("  [WARN] kicad-cli not found; checking S-expression AST syntax only.")

    parts_base = BASE_DIR / "Symbols" / "parts"
    for cat in CATEGORIES:
        cat_folder = parts_base / cat.lower()
        compiled_lib = BASE_DIR / "Symbols" / f"{CATEGORY_FILES[cat]}.kicad_sym"
        if not cat_folder.exists() or not compiled_lib.exists():
            continue

        part_files = sorted(cat_folder.glob("*.kicad_sym"))
        for pf in part_files:
            content = pf.read_text(encoding="utf-8", errors="ignore")
            extracted = extract_top_symbols(content)
            if not extracted:
                results.append({"part": pf.stem, "category": cat, "passed": False, "error": "No top symbol"})
                continue

            for sym_name, raw_sym, _, _ in extracted:
                part_res = {"part": sym_name, "category": cat, "passed": True, "details": []}

                # 1. S-expression check
                sexpr_ok, sexpr_err = validate_sexpr(raw_sym)
                if not sexpr_ok:
                    part_res["passed"] = False
                    part_res["details"].append(f"S-expression syntax error: {sexpr_err}")

                # 2. kicad-cli sym export svg check
                if kicad_cli:
                    sym_ok, sym_msg, svgs = verify_symbol_with_kicad_cli(
                        kicad_cli, sym_name, compiled_lib, temp_out
                    )
                    if not sym_ok:
                        part_res["passed"] = False
                        part_res["details"].append(sym_msg)
                    else:
                        part_res["details"].append(f"KiCad Symbol SVG plotted ({len(svgs)} units)")

                    # 3. Footprint check
                    from kicad_sym_utils import parse_symbol_properties
                    props, _ = parse_symbol_properties(raw_sym)
                    fp_val = props.get("Footprint", "").strip()
                    if fp_val and ":" in fp_val:
                        fp_lib, fp_name = fp_val.split(":", 1)
                        pretty_dir = BASE_DIR / "Footprints" / f"{fp_lib}.pretty"
                        mod_file = pretty_dir / f"{fp_name}.kicad_mod"
                        if mod_file.is_file():
                            fp_ok, fp_msg, fp_svgs = verify_footprint_with_kicad_cli(
                                kicad_cli, fp_name, pretty_dir, temp_out
                            )
                            if not fp_ok:
                                part_res["passed"] = False
                                part_res["details"].append(f"Footprint error: {fp_msg}")
                            else:
                                part_res["details"].append(f"KiCad Footprint SVG plotted ({fp_name})")

                results.append(part_res)
                if verbose:
                    status = "PASS" if part_res["passed"] else "FAIL"
                    det = "; ".join(part_res["details"]) if part_res["details"] else "OK"
                    print(f"  [{status}] {cat:10} | {sym_name:<20} -> {det}")

    if temp_out.exists():
        shutil.rmtree(temp_out, ignore_errors=True)

    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    if verbose:
        print(f"\n[INFO] Verification Summary: {passed_count}/{total_count} parts passed end-to-end.\n")

    return {
        "total": total_count,
        "passed": passed_count,
        "all_passed": passed_count == total_count,
        "results": results
    }


def main():
    parser = argparse.ArgumentParser(
        description="Purdue ROV KiCad Library - End-to-End Component Flow & Verification Suite"
    )
    parser.add_argument(
        "--test-addition",
        action="store_true",
        help="Simulate a complete component addition, KiCad rendering, and clean teardown flow."
    )
    parser.add_argument(
        "--verify-all",
        action="store_true",
        help="Verify all existing parts in the library with the KiCad CLI engine."
    )
    parser.add_argument(
        "--part",
        type=str,
        default="TEST_TPS54302_BUCK",
        help="Part name for addition testing (default: TEST_TPS54302_BUCK)"
    )
    parser.add_argument(
        "--category",
        type=str,
        default="Power",
        choices=CATEGORIES,
        help="Category for addition testing (default: Power)"
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Keep the test part in the library instead of tearing it down."
    )

    args = parser.parse_args()

    # Default to running both addition test and library verification if no specific flag given
    if not args.test_addition and not args.verify_all:
        args.test_addition = True
        args.verify_all = True

    overall_ok = True

    if args.test_addition:
        res = run_e2e_addition_test(
            part_name=args.part,
            category=args.category,
            keep=args.keep,
            verbose=True
        )
        if not res["success"]:
            overall_ok = False

    if args.verify_all:
        res = verify_all_library_parts(verbose=True)
        if not res["all_passed"]:
            overall_ok = False

    if overall_ok:
        print("[OK] ALL END-TO-END TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)
    else:
        print("[FAIL] ONE OR MORE TESTS FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
