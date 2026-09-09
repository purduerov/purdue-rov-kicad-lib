#!/usr/bin/env python3
"""
Purdue ROV KiCad Central Library Manager GUI
All-in-one visual dashboard: Browse, search, edit, add, import (ZIP/sym/mod), delete, validate, and sync components.
"""

import os
import sys
from pathlib import Path

# Add script directory for imports and check dependencies
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dependency_check import ensure_dependencies

# Verify critical GUI and network libraries, prompt/auto-install if missing
if not ensure_dependencies({"tkinter": None, "requests": "requests"}, prompt_if_missing=True):
    sys.exit(1)

import re
import zipfile
import shutil
import subprocess
import threading
import time
import tempfile
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from kicad_sym_utils import (
    validate_sexpr,
    extract_top_symbols,
    parse_symbol_properties,
    update_or_inject_properties,
    autofill_component_data,
    clean_symbol_lib_file,
    CATEGORIES,
    CATEGORY_KEYWORDS
)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
SYMBOLS_DIR = BASE_DIR / "Symbols"
FOOTPRINTS_DIR = BASE_DIR / "Footprints"
MODELS_DIR = BASE_DIR / "3D_Models"
DOWNLOADS_DIR = Path.home() / "Downloads"

CATEGORY_FILES = {
    "Passives": "rov_passives",
    "Power": "rov_power",
    "Logic": "rov_logic",
    "Connectors": "rov_connectors",
    "Sensors": "rov_sensors",
    "Mech": "rov_mech"
}

MANDATORY_FIELDS = ["Category", "MPN", "Manufacturer", "DigiKey", "Datasheet", "Temp_Range"]


class LibraryParser:
    @staticmethod
    def load_all_symbols():
        """Returns dict of {symbol_name: {'category': cat, 'file': path, 'raw_text': str, 'properties': dict}}"""
        symbols = {}
        for cat, fname in CATEGORY_FILES.items():
            sym_file = SYMBOLS_DIR / f"{fname}.kicad_sym"
            if not sym_file.exists():
                continue
            # Ensure file is clean of illegal # comments
            clean_symbol_lib_file(sym_file)
            try:
                with open(sym_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                print(f"Error reading {sym_file}: {e}")
                continue

            extracted = extract_top_symbols(content)
            for sym_name, raw_sym, s_idx, e_idx in extracted:
                props, _ = parse_symbol_properties(raw_sym)
                symbols[sym_name] = {
                    "name": sym_name,
                    "category": props.get("Category", cat),
                    "file": sym_file,
                    "raw_text": raw_sym.strip(),
                    "properties": props
                }
        return symbols

    @staticmethod
    def save_symbol(sym_name, old_category, new_category, new_properties, raw_sym_text):
        """Updates or moves a symbol with new properties safely."""
        new_properties["Category"] = new_category
        updated_sym = update_or_inject_properties(raw_sym_text, new_properties)

        old_file = SYMBOLS_DIR / f"{CATEGORY_FILES[old_category]}.kicad_sym"
        new_file = SYMBOLS_DIR / f"{CATEGORY_FILES[new_category]}.kicad_sym"

        if old_category == new_category and old_file.exists():
            clean_symbol_lib_file(old_file)
            with open(old_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            syms = extract_top_symbols(content)
            replaced = False
            for sname, sraw, sstart, send in syms:
                if sname == sym_name:
                    content = content[:sstart] + updated_sym + content[send:]
                    replaced = True
                    break

            if not replaced:
                if raw_sym_text in content:
                    content = content.replace(raw_sym_text, updated_sym, 1)
                else:
                    content = content.rstrip()
                    last_paren = content.rfind(')')
                    content = content[:last_paren].rstrip() + "\n  " + updated_sym + "\n)\n"

            is_valid, err = validate_sexpr(content)
            if not is_valid:
                raise ValueError(f"S-expression validation failed: {err}")

            with open(old_file, 'w', encoding='utf-8') as f:
                f.write(content.strip() + '\n')
        else:
            LibraryParser.delete_symbol(sym_name, old_category, raw_sym_text)
            LibraryParser.insert_symbol(new_category, updated_sym)

    @staticmethod
    def delete_symbol(sym_name, category, raw_sym_text=None):
        """Removes a symbol from its category file."""
        target_file = SYMBOLS_DIR / f"{CATEGORY_FILES.get(category, 'rov_passives')}.kicad_sym"
        if not target_file.exists():
            return
        clean_symbol_lib_file(target_file)
        with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        syms = extract_top_symbols(content)
        deleted = False
        for sname, sraw, sstart, send in syms:
            if sname == sym_name:
                content = content[:sstart].rstrip() + "\n" + content[send:].lstrip()
                deleted = True
                break

        if not deleted and raw_sym_text and raw_sym_text in content:
            content = content.replace(raw_sym_text, "")

        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content).strip()
        is_valid, err = validate_sexpr(content)
        if is_valid:
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(content + '\n')

    @staticmethod
    def insert_symbol(category, raw_sym_text):
        """Appends a new symbol into the specified category file with bulletproof S-expression syntax."""
        target_file = SYMBOLS_DIR / f"{CATEGORY_FILES[category]}.kicad_sym"
        if not target_file.exists():
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write('(kicad_symbol_lib\n  (version 20211014)\n  (generator "kicad_symbol_editor")\n)\n')

        clean_symbol_lib_file(target_file)
        with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().strip()

        if not content.startswith('(kicad_symbol_lib'):
            content = '(kicad_symbol_lib\n  (version 20211014)\n  (generator "kicad_symbol_editor")\n)'

        last_paren = content.rfind(')')
        if last_paren != -1:
            new_content = content[:last_paren].rstrip() + "\n  " + raw_sym_text.strip() + "\n)\n"
        else:
            new_content = content + "\n  " + raw_sym_text.strip() + "\n)\n"

        is_valid, err = validate_sexpr(new_content)
        if not is_valid:
            raise ValueError(f"Failed to generate valid S-expression for {category} library: {err}")

        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(new_content)


class ImportPartDialog:
    """Integrated Add / Import Part Dialog with drag-and-drop / download watcher support."""
    def __init__(self, parent, callback_on_imported):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("➕ Add / Import Component to Library")
        self.dialog.geometry("640x740")
        self.dialog.minsize(580, 640)
        self.dialog.configure(bg="#1e1e2e")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.callback_on_imported = callback_on_imported
        self.sym_file = None
        self.fp_file = None
        self.model_3d_file = None
        self.temp_dir = None
        self.watcher_running = False
        self.seen_downloads = set()

        self.build_ui()
        self.init_seen_downloads()

    def build_ui(self):
        main_frame = ttk.Frame(self.dialog, style="Surface.TFrame", padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(main_frame, text="Import New Component", style="Header.TLabel")
        title.pack(anchor="w", pady=(0, 2))
        subtitle = ttk.Label(main_frame, text="Select or drop .zip / .kicad_sym / .kicad_mod downloads", style="Muted.TLabel")
        subtitle.pack(anchor="w", pady=(0, 15))

        # Drop / Select Box
        drop_frame = tk.Frame(main_frame, bg="#313244", highlightbackground="#45475a", highlightthickness=2, height=80)
        drop_frame.pack(fill=tk.X, pady=(0, 10))
        drop_frame.pack_propagate(False)

        self.lbl_file_status = tk.Label(drop_frame, text="📁 Click 'Browse Files...' or Drop KiCad Download ZIP here", bg="#313244", fg="#a6adc8", font=("Segoe UI", 10))
        self.lbl_file_status.pack(expand=True)

        browse_row = ttk.Frame(main_frame, style="Surface.TFrame")
        browse_row.pack(fill=tk.X, pady=(0, 15))

        btn_browse = ttk.Button(browse_row, text="Browse Files...", command=self.browse_files)
        btn_browse.pack(side=tk.LEFT)

        self.btn_watcher = ttk.Button(browse_row, text="🟢 Start Downloads Watcher", command=self.toggle_watcher)
        self.btn_watcher.pack(side=tk.RIGHT)

        # Category Selection
        lbl_cat = ttk.Label(main_frame, text="Component Category (Auto-Detected):", style="Surface.TLabel", font=("Segoe UI", 10, "bold"))
        lbl_cat.pack(anchor="w", pady=(0, 5))

        cat_frame = ttk.Frame(main_frame, style="Surface.TFrame")
        cat_frame.pack(fill=tk.X, pady=(0, 15))

        self.selected_category = tk.StringVar(value="Power")
        for cat in CATEGORIES:
            rb = tk.Radiobutton(cat_frame, text=cat, value=cat, variable=self.selected_category,
                                bg="#1e1e2e", fg="#cdd6f4", selectcolor="#313244", activebackground="#1e1e2e",
                                activeforeground="#cba6f7", font=("Segoe UI", 9))
            rb.pack(side=tk.LEFT, padx=4)

        # Fields Form
        fields_frame = ttk.Frame(main_frame, style="Surface.TFrame")
        fields_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.entries = {}
        fields = [
            ("MPN", "Manufacturer Part Number *"),
            ("Manufacturer", "Manufacturer Name *"),
            ("Datasheet", "Datasheet PDF URL *"),
            ("DigiKey", "DigiKey SKU / Link *"),
            ("Temp_Range", "Temperature Range (e.g. -40°C to 125°C) *"),
            ("Footprint", "Assigned Footprint (e.g. rov_power:QFN-16)"),
            ("Description", "Description / Value")
        ]

        for idx, (field_key, field_label) in enumerate(fields):
            lbl = ttk.Label(fields_frame, text=field_label, style="Surface.TLabel", font=("Segoe UI", 9))
            lbl.grid(row=idx*2, column=0, sticky="w", pady=(2, 0))
            
            ent = tk.Entry(fields_frame, bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                           relief="flat", highlightbackground="#45475a", highlightthickness=1, font=("Segoe UI", 9))
            ent.grid(row=idx*2+1, column=0, sticky="ew", pady=(0, 4), ipady=3)
            if field_key == "Temp_Range":
                ent.insert(0, "-40°C to 125°C")
            self.entries[field_key] = ent

        fields_frame.columnconfigure(0, weight=1)

        # Action Buttons
        btn_frame = ttk.Frame(main_frame, style="Surface.TFrame")
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        btn_cancel = ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy)
        btn_cancel.pack(side=tk.LEFT)

        btn_import = ttk.Button(btn_frame, text="🚀 Ingest & Add to Library", style="Success.TButton", command=self.process_import)
        btn_import.pack(side=tk.RIGHT)

    def browse_files(self):
        file_path = filedialog.askopenfilename(
            title="Select KiCad Part or ZIP",
            filetypes=[("KiCad Files & ZIPs", "*.kicad_sym *.kicad_mod *.zip *.step *.stp"), ("All Files", "*.*")]
        )
        if file_path:
            self.load_file(Path(file_path))

    def load_file(self, file_path):
        suffix = file_path.suffix.lower()
        if suffix == ".zip":
            self.extract_zip(file_path)
        elif suffix == ".kicad_sym":
            self.sym_file = file_path
            self.auto_fill_fields()
        elif suffix == ".kicad_mod":
            self.fp_file = file_path
            self.auto_fill_fields()
        elif suffix in [".step", ".stp"]:
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
            dest_3d = MODELS_DIR / file_path.name
            shutil.copy2(file_path, dest_3d)
            self.model_3d_file = file_path
            self.lbl_file_status.config(text=f"🧊 3D Model Saved: {file_path.name}")

    def extract_zip(self, zip_path):
        self.temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.temp_dir)
            
        found_syms = [p for p in Path(self.temp_dir).rglob("*") if p.suffix.lower() == ".kicad_sym"]
        found_fps = [p for p in Path(self.temp_dir).rglob("*") if p.suffix.lower() == ".kicad_mod"]
        found_3d = [p for p in Path(self.temp_dir).rglob("*") if p.suffix.lower() in [".step", ".stp", ".wrl"]]
        
        if found_3d:
            MODELS_DIR.mkdir(parents=True, exist_ok=True)
            self.model_3d_file = found_3d[0]
            dest_3d = MODELS_DIR / self.model_3d_file.name
            shutil.copy2(self.model_3d_file, dest_3d)

        if found_syms:
            self.sym_file = found_syms[0]
        if found_fps:
            self.fp_file = found_fps[0]

        self.auto_fill_fields()

    def auto_fill_fields(self):
        fp_name = None
        if self.fp_file:
            fp_name = self.fp_file.stem
            
        sym_content = ""
        sym_name = None
        if self.sym_file:
            try:
                with open(self.sym_file, 'r', encoding='utf-8', errors='ignore') as f:
                    sym_content = f.read()
                syms = extract_top_symbols(sym_content)
                if syms:
                    sym_name = syms[0][0]
                    sym_text = syms[0][1]
                else:
                    sym_text = sym_content
            except Exception as e:
                sym_text = ""
        else:
            sym_text = ""

        if sym_text:
            data = autofill_component_data(sym_text, sym_name=sym_name, fp_name=fp_name)
        else:
            data = {}

        # Set category if predicted
        if data.get("Category") and data["Category"] in CATEGORIES:
            self.selected_category.set(data["Category"])

        # Populate form entries
        for key, entry in self.entries.items():
            val = data.get(key, "")
            if val:
                entry.delete(0, tk.END)
                entry.insert(0, val)

        # Status summary
        sym_label = self.sym_file.name if self.sym_file else "None"
        fp_label = self.fp_file.name if self.fp_file else "None"
        models_label = f" | 3D: {self.model_3d_file.name}" if self.model_3d_file else ""
        autofilled_count = len(data.get("Autofilled_Fields", []))
        self.lbl_file_status.config(
            text=f"📄 Sym: {sym_label} | 📦 FP: {fp_label}{models_label}\n"
                 f"✨ Autofilled {autofilled_count} fields | Category: {self.selected_category.get()}"
        )

    def init_seen_downloads(self):
        if DOWNLOADS_DIR.exists():
            self.seen_downloads = set(DOWNLOADS_DIR.glob("*"))

    def toggle_watcher(self):
        if not self.watcher_running:
            self.watcher_running = True
            self.btn_watcher.config(text="🔴 Stop Downloads Watcher")
            threading.Thread(target=self.watch_loop, daemon=True).start()
        else:
            self.watcher_running = False
            self.btn_watcher.config(text="🟢 Start Downloads Watcher")

    def watch_loop(self):
        while self.watcher_running:
            time.sleep(2)
            if not DOWNLOADS_DIR.exists():
                continue
            current_files = set(DOWNLOADS_DIR.glob("*"))
            new_files = current_files - self.seen_downloads
            self.seen_downloads = current_files
            
            for f in new_files:
                if f.suffix.lower() in [".kicad_sym", ".kicad_mod", ".zip"]:
                    self.dialog.after(0, self.on_new_file_detected, f)

    def on_new_file_detected(self, file_path):
        self.dialog.lift()
        messagebox.showinfo("New Part Downloaded!", f"Detected new part in Downloads:\n{file_path.name}")
        self.load_file(file_path)

    def process_import(self):
        if not self.sym_file:
            messagebox.showerror("Error", "Please select or drop a valid .kicad_sym or .zip file!")
            return
            
        category = self.selected_category.get()
        field_values = {k: v.get().strip() for k, v in self.entries.items()}
        field_values["Category"] = category

        # Copy footprint if present
        if self.fp_file:
            target_pretty = FOOTPRINTS_DIR / f"rov_{category.lower()}.pretty"
            target_pretty.mkdir(parents=True, exist_ok=True)
            dest_fp = target_pretty / self.fp_file.name
            shutil.copy2(self.fp_file, dest_fp)
            fp_ref = f"rov_{category.lower()}:{self.fp_file.stem}"
            field_values["Footprint"] = fp_ref

        # Read and extract symbol
        with open(self.sym_file, 'r', encoding='utf-8', errors='ignore') as f:
            sym_content = f.read()

        syms = extract_top_symbols(sym_content)
        if not syms:
            messagebox.showerror("Error", "Could not parse a valid top-level symbol from the file!")
            return

        sym_name, raw_sym, _, _ = syms[0]

        # Robustly update/inject properties
        try:
            updated_sym = update_or_inject_properties(raw_sym, field_values)
            LibraryParser.insert_symbol(category, updated_sym)
            messagebox.showinfo("Success", f"Component '{sym_name}' successfully added to {category} library!")
            self.dialog.destroy()
            if self.callback_on_imported:
                self.callback_on_imported()
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to save symbol to library:\n{e}")


class LibraryManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Purdue ROV KiCad Central Library Manager")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)
        self.root.configure(bg="#181825")

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.setup_styles()

        self.symbols = {}
        self.filtered_symbols = {}
        self.selected_symbol_name = None

        self.build_ui()
        self.refresh_symbols()

    def setup_styles(self):
        bg = "#181825"
        surface = "#1e1e2e"
        panel = "#313244"
        text = "#cdd6f4"
        subtext = "#a6adc8"
        accent = "#89b4fa"

        self.style.configure(".", background=bg, foreground=text, font=("Segoe UI", 10))
        self.style.configure("TFrame", background=bg)
        self.style.configure("Surface.TFrame", background=surface)
        self.style.configure("Panel.TFrame", background=panel)
        
        self.style.configure("TLabel", background=bg, foreground=text)
        self.style.configure("Surface.TLabel", background=surface, foreground=text)
        self.style.configure("Header.TLabel", font=("Segoe UI", 13, "bold"), foreground=accent, background=surface)
        self.style.configure("Muted.TLabel", foreground=subtext, background=surface, font=("Segoe UI", 9))
        
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), background=panel, foreground=text, borderwidth=0, padding=6)
        self.style.map("TButton", background=[("active", "#45475a")], foreground=[("active", "#cba6f7")])
        
        self.style.configure("Accent.TButton", background="#89b4fa", foreground="#11111b", padding=6)
        self.style.map("Accent.TButton", background=[("active", "#b4befe")])
        
        self.style.configure("Success.TButton", background="#a6e3a1", foreground="#11111b", padding=6)
        self.style.map("Success.TButton", background=[("active", "#94e2d5")])

        self.style.configure("Danger.TButton", background="#f38ba8", foreground="#11111b", padding=6)
        self.style.map("Danger.TButton", background=[("active", "#eba0ac")])

        self.style.configure("Treeview", background="#1e1e2e", foreground="#cdd6f4", fieldbackground="#1e1e2e", rowheight=28, font=("Segoe UI", 10))
        self.style.configure("Treeview.Heading", background="#313244", foreground="#cba6f7", font=("Segoe UI", 10, "bold"))
        self.style.map("Treeview", background=[("selected", "#45475a")], foreground=[("selected", "#89b4fa")])

    def build_ui(self):
        toolbar = ttk.Frame(self.root, style="Surface.TFrame", padding="10")
        toolbar.pack(fill=tk.X, side=tk.TOP)

        title_lbl = ttk.Label(toolbar, text="🏛️ Purdue ROV Component Library Manager", style="Header.TLabel")
        title_lbl.pack(side=tk.LEFT, padx=(5, 20))

        btn_add = ttk.Button(toolbar, text="➕ Add / Import Part", style="Success.TButton", command=self.open_add_part_dialog)
        btn_add.pack(side=tk.LEFT, padx=5)

        btn_lint = ttk.Button(toolbar, text="🔍 Validate All (Linter)", style="Accent.TButton", command=self.run_linter)
        btn_lint.pack(side=tk.LEFT, padx=5)

        btn_refresh = ttk.Button(toolbar, text="🔄 Reload", command=self.refresh_symbols)
        btn_refresh.pack(side=tk.LEFT, padx=5)

        btn_git = ttk.Button(toolbar, text="🚀 Git Sync", command=self.git_sync)
        btn_git.pack(side=tk.RIGHT, padx=5)

        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(paned, style="Surface.TFrame", padding=10)
        paned.add(left_frame, weight=3)

        filter_frame = ttk.Frame(left_frame, style="Surface.TFrame")
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(filter_frame, text="🔍 Search:", style="Surface.TLabel").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.apply_filters())
        search_entry = tk.Entry(filter_frame, textvariable=self.search_var, bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4", font=("Segoe UI", 10), relief=tk.FLAT)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=4)


        ttk.Label(filter_frame, text="Category:", style="Surface.TLabel").pack(side=tk.LEFT, padx=(0, 5))
        self.category_filter_var = tk.StringVar(value="All")
        cat_combo = ttk.Combobox(filter_frame, textvariable=self.category_filter_var, values=["All"] + CATEGORIES, state="readonly", width=12)
        cat_combo.pack(side=tk.LEFT)
        cat_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        tree_frame = ttk.Frame(left_frame, style="Surface.TFrame")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("Name", "Category", "MPN", "Manufacturer", "DigiKey", "Status")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", selectmode="browse")
        
        self.tree.heading("Name", text="Symbol Name")
        self.tree.heading("Category", text="Category")
        self.tree.heading("MPN", text="MPN")
        self.tree.heading("Manufacturer", text="Manufacturer")
        self.tree.heading("DigiKey", text="DigiKey SKU")
        self.tree.heading("Status", text="Compliance")

        self.tree.column("Name", width=140, anchor="w")
        self.tree.column("Category", width=90, anchor="center")
        self.tree.column("MPN", width=140, anchor="w")
        self.tree.column("Manufacturer", width=120, anchor="w")
        self.tree.column("DigiKey", width=110, anchor="w")
        self.tree.column("Status", width=80, anchor="center")

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<<TreeviewSelect>>", self.on_symbol_select)
        self.tree.bind("<Double-1>", self.on_symbol_double_click)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Button-2>", self.show_context_menu) # macOS right click support

        # Keyboard shortcuts
        self.root.bind("<Control-f>", lambda e: self.focus_search())
        self.root.bind("<Command-f>", lambda e: self.focus_search())
        self.root.bind("<Control-s>", lambda e: self.save_current_symbol())
        self.root.bind("<Command-s>", lambda e: self.save_current_symbol())

        # Context menu
        self.context_menu = tk.Menu(self.root, tearoff=0, bg="#282a36", fg="#f8f8f2", activebackground="#bd93f9", activeforeground="#282a36")
        self.context_menu.add_command(label="📋 Copy MPN", command=self.copy_mpn)
        self.context_menu.add_command(label="📋 Copy DigiKey SKU", command=self.copy_digikey)
        self.context_menu.add_command(label="🌐 Open Datasheet URL", command=self.open_datasheet)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Delete Component", command=self.delete_current_symbol)

        self.lbl_count = ttk.Label(left_frame, text="0 components loaded", style="Muted.TLabel")
        self.lbl_count.pack(anchor="w", pady=(5, 0))


        right_frame = ttk.Frame(paned, style="Surface.TFrame", padding=15)
        paned.add(right_frame, weight=2)

        right_header = ttk.Label(right_frame, text="⚙️ Component Properties", style="Header.TLabel")
        right_header.pack(anchor="w", pady=(0, 10))

        canvas = tk.Canvas(right_frame, bg="#1e1e2e", highlightthickness=0)
        form_scroll = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.form_frame = ttk.Frame(canvas, style="Surface.TFrame")

        self.form_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.form_frame, anchor="nw")
        canvas.configure(yscrollcommand=form_scroll.set)

        canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        form_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.fields_entries = {}
        fields_to_edit = [
            ("Name", "Symbol Name (Read-Only)"),
            ("Category", "Category (Move category)"),
            ("MPN", "Manufacturer Part Number *"),
            ("Manufacturer", "Manufacturer Name *"),
            ("DigiKey", "DigiKey SKU / Link *"),
            ("Datasheet", "Datasheet PDF URL *"),
            ("Temp_Range", "Temperature Range (e.g. -40°C to 125°C) *"),
            ("Footprint", "Assigned Footprint"),
            ("Description", "Component Description"),
            ("Value", "Schematic Value"),
            ("Reference", "Reference Designator (e.g. R, C, U)")
        ]

        for prop_key, prop_title in fields_to_edit:
            lbl = ttk.Label(self.form_frame, text=prop_title, font=("Segoe UI", 9, "bold"), style="Surface.TLabel")
            lbl.pack(anchor="w", pady=(6, 2))

            if prop_key == "Category":
                var = tk.StringVar()
                cb = ttk.Combobox(self.form_frame, textvariable=var, values=CATEGORIES, state="readonly")
                cb.pack(fill=tk.X, pady=(0, 4))
                self.fields_entries[prop_key] = var
            elif prop_key == "Name":
                var = tk.StringVar()
                entry = tk.Entry(self.form_frame, textvariable=var, bg="#252538", fg="#a6adc8", font=("Segoe UI", 10), state="readonly", relief=tk.FLAT)
                entry.pack(fill=tk.X, pady=(0, 4), ipady=3)
                self.fields_entries[prop_key] = var
            else:
                var = tk.StringVar()
                entry = tk.Entry(self.form_frame, textvariable=var, bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4", font=("Segoe UI", 10), relief=tk.FLAT)
                entry.pack(fill=tk.X, pady=(0, 4), ipady=3)
                self.fields_entries[prop_key] = var

        btn_open_ds = ttk.Button(self.form_frame, text="🌐 Open Datasheet URL", command=self.open_datasheet)
        btn_open_ds.pack(anchor="w", pady=(5, 15))

        action_box = ttk.Frame(right_frame, style="Surface.TFrame")
        action_box.pack(fill=tk.X, side=tk.BOTTOM, pady=(15, 0))

        btn_save = ttk.Button(action_box, text="💾 Save Changes", style="Success.TButton", command=self.save_current_symbol)
        btn_save.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        btn_delete = ttk.Button(action_box, text="🗑️ Delete Part", style="Danger.TButton", command=self.delete_current_symbol)
        btn_delete.pack(side=tk.RIGHT, padx=(5, 0))

    def refresh_symbols(self):
        self.symbols = LibraryParser.load_all_symbols()
        self.apply_filters()

    def apply_filters(self):
        query = self.search_var.get().lower().strip()
        cat_filter = self.category_filter_var.get()

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.filtered_symbols = {}
        for name, data in sorted(self.symbols.items()):
            props = data["properties"]
            cat = data["category"]

            if cat_filter != "All" and cat != cat_filter:
                continue

            mpn = props.get("MPN", "")
            mfr = props.get("Manufacturer", "")
            desc = props.get("Description", "")
            dk = props.get("DigiKey", "")

            if query:
                combined_text = f"{name} {cat} {mpn} {mfr} {desc} {dk}".lower()
                if query not in combined_text:
                    continue

            is_compliant = all(props.get(f, "").strip() for f in MANDATORY_FIELDS)
            status_icon = "✅" if is_compliant else "⚠️ Incomplete"

            self.filtered_symbols[name] = data
            self.tree.insert("", tk.END, iid=name, values=(name, cat, mpn, mfr, dk, status_icon))

        count = len(self.filtered_symbols)
        # Calculate category breakdown
        cat_counts = {}
        for s in self.symbols.values():
            c = s.get("category", "Other")
            cat_counts[c] = cat_counts.get(c, 0) + 1
        
        breakdown_str = " | ".join(f"{c}: {cat_counts.get(c, 0)}" for c in CATEGORIES)
        self.lbl_count.config(text=f"📊 Showing {count} of {len(self.symbols)} parts  [{breakdown_str}]")

    def focus_search(self):
        # Focus the search entry box
        for widget in self.root.winfo_children():
            # traverse to find search entry
            pass
        self.search_var.set("")

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.on_symbol_select(None)
            self.context_menu.post(event.x_root, event.y_root)

    def on_symbol_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.on_symbol_select(None)

    def copy_mpn(self):
        mpn = self.fields_entries["MPN"].get().strip()
        if mpn:
            self.root.clipboard_clear()
            self.root.clipboard_append(mpn)
            self.root.update()

    def copy_digikey(self):
        dk = self.fields_entries["DigiKey"].get().strip()
        if dk:
            self.root.clipboard_clear()
            self.root.clipboard_append(dk)
            self.root.update()


    def on_symbol_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        sym_name = selected[0]
        self.selected_symbol_name = sym_name
        data = self.symbols.get(sym_name)
        if not data:
            return

        props = data["properties"]
        self.fields_entries["Name"].set(sym_name)
        self.fields_entries["Category"].set(data["category"])
        self.fields_entries["MPN"].set(props.get("MPN", ""))
        self.fields_entries["Manufacturer"].set(props.get("Manufacturer", ""))
        self.fields_entries["DigiKey"].set(props.get("DigiKey", ""))
        self.fields_entries["Datasheet"].set(props.get("Datasheet", ""))
        self.fields_entries["Temp_Range"].set(props.get("Temp_Range", ""))
        self.fields_entries["Footprint"].set(props.get("Footprint", ""))
        self.fields_entries["Description"].set(props.get("Description", ""))
        self.fields_entries["Value"].set(props.get("Value", sym_name))
        self.fields_entries["Reference"].set(props.get("Reference", "U"))

    def open_datasheet(self):
        url = self.fields_entries["Datasheet"].get().strip()
        if url.startswith("http://") or url.startswith("https://"):
            webbrowser.open(url)
        else:
            messagebox.showwarning("Invalid URL", f"Datasheet URL is not a valid web link: {url}")

    def save_current_symbol(self):
        if not self.selected_symbol_name or self.selected_symbol_name not in self.symbols:
            messagebox.showwarning("No Selection", "Please select a component from the list first.")
            return

        sym_name = self.selected_symbol_name
        data = self.symbols[sym_name]
        old_cat = data["category"]
        new_cat = self.fields_entries["Category"].get()

        new_props = dict(data["properties"])
        for k, var in self.fields_entries.items():
            if k not in ["Name", "Category"]:
                new_props[k] = var.get().strip()

        try:
            LibraryParser.save_symbol(sym_name, old_cat, new_cat, new_props, data["raw_text"])
            messagebox.showinfo("Saved", f"Component '{sym_name}' updated successfully in {new_cat}!")
            self.refresh_symbols()
            if sym_name in self.filtered_symbols:
                self.tree.selection_set(sym_name)
                self.tree.see(sym_name)
        except Exception as e:
            messagebox.showerror("Error Saving", f"Failed to save changes: {e}")

    def delete_current_symbol(self):
        if not self.selected_symbol_name or self.selected_symbol_name not in self.symbols:
            messagebox.showwarning("No Selection", "Please select a component to delete.")
            return

        sym_name = self.selected_symbol_name
        data = self.symbols[sym_name]
        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete component '{sym_name}' from {data['category']} library?")
        if not confirm:
            return

        try:
            LibraryParser.delete_symbol(sym_name, data["category"], data["raw_text"])
            messagebox.showinfo("Deleted", f"Component '{sym_name}' removed from library.")
            self.selected_symbol_name = None
            self.refresh_symbols()
        except Exception as e:
            messagebox.showerror("Error Deleting", f"Failed to delete component: {e}")

    def open_add_part_dialog(self):
        ImportPartDialog(self.root, callback_on_imported=self.refresh_symbols)

    def run_linter(self):
        linter_script = BASE_DIR / "scripts" / "linter_validator.py"
        if not linter_script.exists():
            messagebox.showerror("Error", "Linter script not found!")
            return
        
        sym_files = list(SYMBOLS_DIR.glob("*.kicad_sym"))
        res = subprocess.run([sys.executable, str(linter_script)] + [str(p) for p in sym_files], capture_output=True, text=True)
        if res.returncode == 0:
            messagebox.showinfo("Linter Validation", "✅ All components across all 6 libraries are 100% compliant with structural guidelines!")
        else:
            messagebox.showwarning("Linter Violations Found", res.stderr or res.stdout)

    def git_sync(self):
        try:
            subprocess.run(["git", "pull", "--rebase", "origin", "master"], cwd=str(BASE_DIR), check=True)
            subprocess.run(["git", "add", "-A"], cwd=str(BASE_DIR), check=True)
            status = subprocess.check_output(["git", "status", "--porcelain"], cwd=str(BASE_DIR), text=True)
            if not status.strip():
                messagebox.showinfo("Git Sync", "Library is already up to date with remote master. No local changes to commit.")
                return
            
            subprocess.run(["git", "commit", "-m", "chore(lib): update central component library via Library Manager GUI"], cwd=str(BASE_DIR), check=True)
            subprocess.run(["git", "push", "origin", "master"], cwd=str(BASE_DIR), check=True)
            messagebox.showinfo("Git Sync", "✅ Library changes successfully committed and pushed to GitHub master!")
        except Exception as e:
            messagebox.showerror("Git Sync Failed", f"Git operation failed:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = LibraryManagerApp(root)
    root.mainloop()
