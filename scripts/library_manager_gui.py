#!/usr/bin/env bash
#!/usr/bin/env python3
"""
Purdue ROV KiCad Central Library Manager GUI
View, search, edit, add, delete, validate, and sync components across all 6 standardized categories.
"""

import os
import sys
import re
import zipfile
import shutil
import subprocess
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
SYMBOLS_DIR = BASE_DIR / "Symbols"
FOOTPRINTS_DIR = BASE_DIR / "Footprints"
MODELS_DIR = BASE_DIR / "3D_Models"

CATEGORIES = ["Passives", "Power", "Logic", "Connectors", "Sensors", "Mech"]
CATEGORY_FILES = {
    "Passives": "rov_passives",
    "Power": "rov_power",
    "Logic": "rov_logic",
    "Connectors": "rov_connectors",
    "Sensors": "rov_sensors",
    "Mech": "rov_mech"
}

MANDATORY_FIELDS = ["Category", "MPN", "Manufacturer", "DigiKey", "Datasheet", "Temp_Range"]

def get_category_from_filename(filename):
    name = Path(filename).stem.lower()
    for cat in CATEGORIES:
        if cat.lower() in name:
            return cat
    return "Passives"

class LibraryParser:
    @staticmethod
    def load_all_symbols():
        """Returns dict of {symbol_name: {'category': cat, 'file': path, 'raw_text': str, 'properties': dict}}"""
        symbols = {}
        for cat, fname in CATEGORY_FILES.items():
            sym_file = SYMBOLS_DIR / f"{fname}.kicad_sym"
            if not sym_file.exists():
                continue
            try:
                with open(sym_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                print(f"Error reading {sym_file}: {e}")
                continue

            # Parse top-level symbols
            # Matches: (symbol "NAME" ... )
            # KiCad S-expression block parser
            sym_matches = list(re.finditer(r'\n\s*\(symbol\s+"([^"]+)"', content))
            for i, match in enumerate(sym_matches):
                sym_name = match.group(1)
                # Skip sub-symbols / units
                if re.search(r'_\d+_\d+$', sym_name):
                    continue

                start_pos = match.start()
                # Determine end position: either start of next top symbol or end of library
                next_top_pos = None
                for next_match in sym_matches[i+1:]:
                    if not re.search(r'_\d+_\d+$', next_match.group(1)):
                        next_top_pos = next_match.start()
                        break
                
                if next_top_pos is not None:
                    raw_sym = content[start_pos:next_top_pos]
                else:
                    # Last symbol before closing library paren
                    last_paren = content.rfind(')')
                    raw_sym = content[start_pos:last_paren] if last_paren != -1 else content[start_pos:]

                # Extract properties
                properties = {}
                # Property pattern: (property "Key" "Value" ...)
                prop_iter = re.finditer(r'\(property\s+"([^"]+)"\s+"([^"]*)"(?:\s+\(id\s+(\d+)\))?(?:\s+\(at\s+([^\)]+)\))?(?:\s+\(effects\s+([^\)]+(?:\([^\)]*\))*)\))?', raw_sym)
                for pm in prop_iter:
                    key = pm.group(1)
                    val = pm.group(2)
                    properties[key] = val.strip()

                symbols[sym_name] = {
                    "name": sym_name,
                    "category": properties.get("Category", cat),
                    "file": sym_file,
                    "raw_text": raw_sym.strip(),
                    "properties": properties
                }
        return symbols

    @staticmethod
    def save_symbol(sym_name, old_category, new_category, new_properties, raw_sym_text):
        """Updates or moves a symbol with new properties."""
        # 1. Update properties inside raw_sym_text
        updated_sym = raw_sym_text
        
        # Ensure Category property matches new_category
        new_properties["Category"] = new_category

        for prop_name, prop_val in new_properties.items():
            # Check if property already exists in raw_sym_text
            prop_regex = rf'(\(property\s+"{re.escape(prop_name)}"\s+")[^"]*(")'
            if re.search(prop_regex, updated_sym):
                updated_sym = re.sub(prop_regex, rf'\g<1>{prop_val}\g<2>', updated_sym)
            else:
                # Insert after (property "Value" ...) or at top of symbol
                val_m = re.search(r'\(property\s+"Value"\s+"[^"]*"\s*(?:\([^\)]*\)\s*)*\)', updated_sym)
                prop_str = f'\n    (property "{prop_name}" "{prop_val}" (at 0 0 0)\n      (effects (font (size 1.27 1.27)) hide)\n    )'
                if val_m:
                    idx = val_m.end()
                    updated_sym = updated_sym[:idx] + prop_str + updated_sym[idx:]
                else:
                    first_sym_line = updated_sym.find('\n')
                    updated_sym = updated_sym[:first_sym_line] + prop_str + updated_sym[first_sym_line:]

        # 2. If category didn't change, replace in place
        old_file = SYMBOLS_DIR / f"{CATEGORY_FILES[old_category]}.kicad_sym"
        new_file = SYMBOLS_DIR / f"{CATEGORY_FILES[new_category]}.kicad_sym"

        if old_category == new_category and old_file.exists():
            with open(old_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            # Replace old raw block
            if raw_sym_text in content:
                content = content.replace(raw_sym_text, updated_sym)
            else:
                # Fallback replace symbol declaration
                pattern = rf'(\(symbol\s+"{re.escape(sym_name)}".*?\n  \))'
                content = re.sub(pattern, updated_sym, content, flags=re.DOTALL)
            with open(old_file, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            # Delete from old file
            LibraryParser.delete_symbol(sym_name, old_category, raw_sym_text)
            # Append to new file
            LibraryParser.insert_symbol(new_category, updated_sym)

    @staticmethod
    def delete_symbol(sym_name, category, raw_sym_text=None):
        """Removes a symbol from its category file."""
        target_file = SYMBOLS_DIR / f"{CATEGORY_FILES.get(category, 'rov_passives')}.kicad_sym"
        if not target_file.exists():
            return
        with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        if raw_sym_text and raw_sym_text in content:
            content = content.replace(raw_sym_text, "")
        else:
            # Fallback regex removal
            pattern = rf'\n\s*\(symbol\s+"{re.escape(sym_name)}".*?\n  \)'
            content = re.sub(pattern, "", content, flags=re.DOTALL)

        # Clean multiple blank lines
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(content)

    @staticmethod
    def insert_symbol(category, raw_sym_text):
        """Appends a new symbol into the specified category file."""
        target_file = SYMBOLS_DIR / f"{CATEGORY_FILES[category]}.kicad_sym"
        if not target_file.exists():
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write('(kicad_symbol_lib (version 20211014) (generator kicad_symbol_editor)\n)\n')
        
        with open(target_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        last_paren = content.rfind(')')
        if last_paren != -1:
            new_content = content[:last_paren].rstrip() + "\n  " + raw_sym_text.strip() + "\n)\n"
        else:
            new_content = content + "\n  " + raw_sym_text.strip() + "\n)\n"

        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(new_content)


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

        # Treeview styling
        self.style.configure("Treeview", background="#1e1e2e", foreground="#cdd6f4", fieldbackground="#1e1e2e", rowheight=28, font=("Segoe UI", 10))
        self.style.configure("Treeview.Heading", background="#313244", foreground="#cba6f7", font=("Segoe UI", 10, "bold"))
        self.style.map("Treeview", background=[("selected", "#45475a")], foreground=[("selected", "#89b4fa")])

    def build_ui(self):
        # Top toolbar
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

        # Main Split Container
        paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left Panel: Search, Category Filter, and Part List
        left_frame = ttk.Frame(paned, style="Surface.TFrame", padding=10)
        paned.add(left_frame, weight=3)

        # Filter bar
        filter_frame = ttk.Frame(left_frame, style="Surface.TFrame")
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(filter_frame, text="🔍 Search:", style="Surface.TLabel").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.apply_filters())
        search_entry = tk.Entry(filter_frame, textvariable=self.search_var, bg="#313244", fg="#cdd6f4", insertbackground="#cdd6f4", font=("Segoe UI", 10), relief=tk.FLAT)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=4)

        ttk.Label(filter_frame, text="Category:", style="Surface.TLabel").pack(side=tk.LEFT, padx=(0, 5))
        self.category_filter_var = tk.StringVar(value="All")
        cat_combo = ttk.Combobox(filter_frame, textvariable=self.category_filter_var, values=["All"] + CATEGORIES, state="readonly", width=12)
        cat_combo.pack(side=tk.LEFT)
        cat_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        # Treeview table
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

        # Left bottom count label
        self.lbl_count = ttk.Label(left_frame, text="0 components loaded", style="Muted.TLabel")
        self.lbl_count.pack(anchor="w", pady=(5, 0))

        # Right Panel: Inspector & Property Editor
        right_frame = ttk.Frame(paned, style="Surface.TFrame", padding=15)
        paned.add(right_frame, weight=2)

        right_header = ttk.Label(right_frame, text="⚙️ Component Properties", style="Header.TLabel")
        right_header.pack(anchor="w", pady=(0, 10))

        # Editor Form inside Scrollable Canvas
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

        # Link button for Datasheet
        btn_open_ds = ttk.Button(self.form_frame, text="🌐 Open Datasheet URL", command=self.open_datasheet)
        btn_open_ds.pack(anchor="w", pady=(5, 15))

        # Bottom Action Buttons
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

            # Check compliance
            is_compliant = all(props.get(f, "").strip() for f in MANDATORY_FIELDS)
            status_icon = "✅" if is_compliant else "⚠️ Incomplete"

            self.filtered_symbols[name] = data
            self.tree.insert("", tk.END, iid=name, values=(name, cat, mpn, mfr, dk, status_icon))

        count = len(self.filtered_symbols)
        self.lbl_count.config(text=f"{count} component{'s' if count != 1 else ''} shown (Total {len(self.symbols)} in library)")

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

        # Build updated properties dict
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
        # Open the Part Importer GUI or simple manual addition dialog
        importer_script = BASE_DIR / "scripts" / "part_importer_gui.py"
        if importer_script.exists():
            subprocess.Popen([sys.executable, str(importer_script)])
        else:
            messagebox.showinfo("Add Part", "To add parts, drag and drop KiCad symbol/footprint downloads into the importer wizard.")

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
