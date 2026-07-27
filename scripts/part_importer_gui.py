#!/usr/bin/env python3
"""
Purdue ROV KiCad Library - GUI & Downloads Watcher Part Importer
Drag & Drop / Auto-Watch Downloads Folder for 1-Click Part Importing into standard categories.
"""

import os
import sys
import re
import zipfile
import shutil
import subprocess
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

BASE_DIR = Path(__file__).resolve().parent.parent
SYMBOLS_DIR = BASE_DIR / "Symbols"
FOOTPRINTS_DIR = BASE_DIR / "Footprints"

ALLOWED_CATEGORIES = ["Passives", "Power", "Logic", "Connectors", "Sensors", "Mech"]
DOWNLOADS_DIR = Path.home() / "Downloads"

class PartImporterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Purdue ROV KiCad Library - 1-Click Part Importer")
        self.root.geometry("640x720")
        self.root.configure(bg="#1e1e2e")
        
        # Enable Dark Theme styling
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.configure_styles()

        self.sym_file = None
        self.fp_file = None
        self.temp_dir = None
        self.watcher_running = False
        self.seen_downloads = set()

        self.build_ui()
        self.init_seen_downloads()

    def configure_styles(self):
        self.style.configure("TFrame", background="#1e1e2e")
        self.style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#cba6f7", background="#1e1e2e")
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 10, "italic"), foreground="#a6adc8", background="#1e1e2e")
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), background="#313244", foreground="#cdd6f4", borderwidth=0)
        self.style.map("TButton", background=[("active", "#45475a")], foreground=[("active", "#cba6f7")])
        self.style.configure("Accent.TButton", background="#89b4fa", foreground="#11111b")
        self.style.map("Accent.TButton", background=[("active", "#b4befe")])

    def build_ui(self):
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title = ttk.Label(main_frame, text="Purdue ROV Part Importer", style="Header.TLabel")
        title.pack(anchor="w", pady=(0, 2))
        subtitle = ttk.Label(main_frame, text="Auto-detects downloaded parts & adds them to standard library", style="SubHeader.TLabel")
        subtitle.pack(anchor="w", pady=(0, 15))

        # Drop / Select Box
        drop_frame = tk.Frame(main_frame, bg="#313244", highlightbackground="#45475a", highlightthickness=2, height=90)
        drop_frame.pack(fill=tk.X, pady=(0, 15))
        drop_frame.pack_propagate(False)

        self.lbl_file_status = tk.Label(drop_frame, text="📁 Select or Drop .kicad_sym / .kicad_mod / .zip file here", bg="#313244", fg="#a6adc8", font=("Segoe UI", 11))
        self.lbl_file_status.pack(expand=True)

        btn_browse = ttk.Button(main_frame, text="Browse Files...", command=self.browse_files)
        btn_browse.pack(anchor="e", pady=(0, 15))

        # Category Selection
        lbl_cat = ttk.Label(main_frame, text="Select Component Category:", font=("Segoe UI", 11, "bold"))
        lbl_cat.pack(anchor="w", pady=(0, 5))

        cat_frame = ttk.Frame(main_frame)
        cat_frame.pack(fill=tk.X, pady=(0, 15))

        self.selected_category = tk.StringVar(value="Power")
        for cat in ALLOWED_CATEGORIES:
            rb = tk.Radiobutton(cat_frame, text=cat, value=cat, variable=self.selected_category,
                                bg="#1e1e2e", fg="#cdd6f4", selectcolor="#313244", activebackground="#1e1e2e",
                                activeforeground="#cba6f7", font=("Segoe UI", 10))
            rb.pack(side=tk.LEFT, padx=5)

        # Fields Frame
        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack(fill=tk.X, pady=(0, 15))

        self.entries = {}
        fields = [
            ("MPN", "Manufacturer Part Number"),
            ("Manufacturer", "Manufacturer Name"),
            ("Datasheet", "Datasheet PDF URL"),
            ("DigiKey", "DigiKey Part Number / SKU"),
            ("Temp_Range", "Temperature Range (default: -40°C to 125°C)")
        ]

        for idx, (field_key, field_label) in enumerate(fields):
            lbl = ttk.Label(fields_frame, text=f"{field_label}:")
            lbl.grid(row=idx*2, column=0, sticky="w", pady=(2, 0))
            
            ent = tk.Entry(fields_frame, bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4",
                           relief="flat", highlightbackground="#45475a", highlightthickness=1, font=("Consolas", 10))
            ent.grid(row=idx*2+1, column=0, sticky="ew", pady=(0, 8))
            if field_key == "Temp_Range":
                ent.insert(0, "-40°C to 125°C")
            self.entries[field_key] = ent

        fields_frame.columnconfigure(0, weight=1)

        # Action Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        self.btn_watcher = ttk.Button(btn_frame, text="🟢 Start Downloads Watcher", command=self.toggle_watcher)
        self.btn_watcher.pack(side=tk.LEFT)

        btn_import = ttk.Button(btn_frame, text="🚀 Import & Push to Library", style="Accent.TButton", command=self.process_import)
        btn_import.pack(side=tk.RIGHT)

        # Status log
        self.lbl_status = ttk.Label(main_frame, text="Ready", style="SubHeader.TLabel")
        self.lbl_status.pack(anchor="w", pady=(10, 0))

    def browse_files(self):
        file_path = filedialog.askopenfilename(
            title="Select KiCad Part or ZIP",
            filetypes=[("KiCad Files & ZIPs", "*.kicad_sym *.kicad_mod *.zip"), ("All Files", "*.*")]
        )
        if file_path:
            self.load_file(Path(file_path))

    def load_file(self, file_path):
        if file_path.suffix.lower() == ".zip":
            self.extract_zip(file_path)
        elif file_path.suffix.lower() == ".kicad_sym":
            self.sym_file = file_path
            self.lbl_file_status.config(text=f"📄 Symbol: {file_path.name}")
            self.auto_fill_fields_from_symbol(file_path)
        elif file_path.suffix.lower() == ".kicad_mod":
            self.fp_file = file_path
            self.lbl_file_status.config(text=f"📦 Footprint: {file_path.name}")

    def extract_zip(self, zip_path):
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.temp_dir)
            
        found_syms = list(Path(self.temp_dir).rglob("*.kicad_sym"))
        found_fps = list(Path(self.temp_dir).rglob("*.kicad_mod"))
        
        if found_syms:
            self.sym_file = found_syms[0]
            self.auto_fill_fields_from_symbol(self.sym_file)
        if found_fps:
            self.fp_file = found_fps[0]
            
        sym_name = self.sym_file.name if self.sym_file else "None"
        fp_name = self.fp_file.name if self.fp_file else "None"
        self.lbl_file_status.config(text=f"📦 ZIP: {zip_path.name}\n(Sym: {sym_name} | FP: {fp_name})")

    def auto_fill_fields_from_symbol(self, sym_path):
        content = sym_path.read_text(encoding="utf-8", errors="ignore")
        props = {}
        for match in re.finditer(r'\(property "([^"]+)" "([^"]*)"', content):
            k, v = match.group(1), match.group(2)
            if k == "DigiKey_SKU":
                k = "DigiKey"
            props[k] = v
            
        for key, entry in self.entries.items():
            if key in props and props[key]:
                entry.delete(0, tk.END)
                entry.insert(0, props[key])

    def init_seen_downloads(self):
        if DOWNLOADS_DIR.exists():
            self.seen_downloads = set(DOWNLOADS_DIR.glob("*"))

    def toggle_watcher(self):
        if not self.watcher_running:
            self.watcher_running = True
            self.btn_watcher.config(text="🔴 Stop Downloads Watcher")
            self.lbl_status.config(text="Watcher active: Monitoring ~/Downloads for new parts...")
            threading.Thread(target=self.watch_loop, daemon=True).start()
        else:
            self.watcher_running = False
            self.btn_watcher.config(text="🟢 Start Downloads Watcher")
            self.lbl_status.config(text="Watcher stopped.")

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
                    self.root.after(0, self.on_new_file_detected, f)

    def on_new_file_detected(self, file_path):
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.attributes("-topmost", False)
        messagebox.showinfo("New Part Downloaded!", f"Detected new part in Downloads:\n{file_path.name}")
        self.load_file(file_path)

    def process_import(self):
        if not self.sym_file:
            messagebox.showerror("Error", "Please select or drop a valid .kicad_sym or .zip file!")
            return
            
        category = self.selected_category.get()
        field_values = {k: v.get().strip() for k, v in self.entries.items()}
        
        # Import using backend logic
        try:
            from import_part import extract_symbols_from_file, inject_or_update_properties, copy_footprint_to_category, append_symbol_to_category
        except ImportError:
            sys.path.append(str(BASE_DIR / "scripts"))
            from import_part import extract_symbols_from_file, inject_or_update_properties, copy_footprint_to_category, append_symbol_to_category

        symbols = extract_symbols_from_file(self.sym_file)
        if not symbols:
            messagebox.showerror("Error", "No valid symbols found in symbol file!")
            return

        sym_block = symbols[0]
        if self.fp_file:
            fp_name = copy_footprint_to_category(category, self.fp_file)
            field_values["Footprint"] = f"rov_{category.lower()}:{fp_name}"
            
        field_values["Category"] = category
        updated_sym = inject_or_update_properties(sym_block, field_values)
        append_symbol_to_category(category, updated_sym)

        # Run Linter
        linter_script = BASE_DIR / "scripts" / "linter_validator.py"
        res = subprocess.run([sys.executable, str(linter_script)] + [str(p) for p in SYMBOLS_DIR.glob("*.kicad_sym")])
        
        if res.returncode == 0:
            # Commit & Push
            subprocess.run(["git", "add", "Symbols/", "Footprints/"], cwd=str(BASE_DIR))
            subprocess.run(["git", "commit", "-m", f"feat(lib): add {field_values.get('MPN', 'new part')} to {category} library"], cwd=str(BASE_DIR))
            subprocess.run(["git", "push", "origin", "master"], cwd=str(BASE_DIR))
            
            messagebox.showinfo("Success 🎉", f"Part '{field_values.get('MPN', 'Component')}' successfully added to {category} library and pushed to master!")
            self.lbl_status.config(text="✅ Import complete & pushed to master!")
        else:
            messagebox.showwarning("Linter Warning", "Part added, but linter failed. Check missing mandatory fields.")

if __name__ == "__main__":
    root = tk.Tk()
    app = PartImporterApp(root)
    root.mainloop()
