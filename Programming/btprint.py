"""
==============================================================================
BLUETOOTH THERMAL PRINTER MANAGER (TSPL & CPCL)
==============================================================================

DESCRIPTION:
    A professional-grade utility for printing PDFs and Images to Bluetooth 
    Thermal Printers on Windows. Designed for hybrid printers (like LP-9200UB, 
    RPP series) that support both TSC (TSPL) and Zebra (CPCL) protocols.

    Features:
    - Profile Manager: Create, Duplicate, Rename, Delete, Import, Export profiles.
    - Multi-Protocol: Native generation of TSPL and CPCL command sets.
    - Smart Detection: Scans Windows Registry for "Friendly Names" to map COM ports.
    - Robust Config: Auto-heals corrupt JSON files; auto-backups.
    - Batch Processing: Handles wildcards (*.pdf) and multiple files.

DEPENDENCIES:
    pip install pyserial pymupdf Pillow

USAGE:
    1. CLI Printing:
       python btprint.py label.pdf              # Use default profile
       python btprint.py -p "Receipt" *.pdf     # Use specific profile
       python btprint.py -s label.pdf           # Force manual COM port selection

    2. GUI Editor:
       python btprint.py -e                     # Open Settings Manager

DETAILED CONFIGURATION GUIDE:

    1. CONNECTION & PROTOCOL
       - Protocol:
         * TSPL: Standard for desktop shipping printers (LP-9200, TSC, Godex).
         * CPCL: Standard for mobile belt printers (Zebra, RPP, QR-380).
       - Registry Keyword:
         The substring to look for in the Windows Registry (e.g., "BlueTooth").
         Allows auto-connection without asking for COM port every time.

    2. HARDWARE SENSORS (Critical for alignment)
       - GAP:
         Uses the Transmissive sensor. Detects the space between die-cut labels.
         *Required* for shipping labels to keep alignment.
       - CONTINUOUS:
         Ignores sensors. Prints blindly. Use for receipt rolls.
         *Warning:* If used on labels, print will drift across the gap.
       - BLINE:
         Uses Reflective sensor. Detects black bars printed on the back of paper.

    3. POST-PRINT ACTION (Physical Behavior)
       - TEAR (Standard):
         Feeds paper to the serrated tear-bar after printing.
         *Crucial:* Pulls paper BACK (Backfeed) before printing the next page.
         *Risk:* Can cause jams on continuous paper if backfeed is too aggressive.
       - NONE (Safe Mode):
         Stops exactly where the image ends. No feed, no backfeed.
         Use this if TEAR mode is jamming your paper.
       - PEEL (Dispenser):
         *Hardware Required.* Feeds and separates the sticker from backing.
         Pauses printing until the sensor detects the label was taken.
       - CUTTER:
         *Hardware Required.* Activates the guillotine blade after printing.

    4. GEOMETRY & QUALITY
       - Label Height (Fixed mm):
         * Set to 0 for Receipts (variable length based on PDF content).
         * Set to Physical Height (e.g., 150mm) for Labels. This acts as a 
           safety limit to prevent infinite feeding if the sensor misses a gap.
       - Extra Feed:
         Adds blank space at the end of a job (useful for tearing off receipts).
         Keep at 0 for shipping labels to avoid wasting stickers.
       - Invert Image:
         Thermal printers burn "Black" on "White" paper.
         * Checked (True): Converts image pixels to Black=Burn. (Standard).
         * Unchecked (False): Prints photo negative.

    5. INIT COMMANDS
       Raw commands sent before the image data. Useful for overrides.
       Common TSPL Commands:
       - HOME:     Force calibration/alignment before printing.
       - OFFSET 0: Reset label resting position.
       - SPEED 4:  Override print speed.

TROUBLESHOOTING:
    [ERROR] "Semaphore timeout period has expired":
        The Windows Bluetooth socket is dead. This cannot be fixed by code.
        FIX: Remove device in Windows Settings > Bluetooth, Turn Printer OFF/ON, Re-Pair.

    [ISSUE] Printer keeps feeding blank paper:
        1. Check Sensor Type. Is it set to GAP for receipt paper? (Set to CONTINUOUS).
        2. Is the Fixed Height set to 0 on a label printer? (Set to 100mm/150mm).
        3. Is the sensor blocked by dust?

    [ISSUE] Print is inverted (Photo Negative):
        Toggle the "Invert Image" checkbox in the GUI.

IMPORTANT: This documentation must be included and updated with every change to this script.
==============================================================================
"""

import sys
import glob
import time
import serial
import serial.tools.list_ports
import winreg
import re
import json
import os
import argparse
import shutil
import copy
import fitz      # PyMuPDF
from PIL import Image, ImageOps

# GUI Imports
import tkinter as tk
from tkinter import ttk, messagebox, Text, simpledialog, filedialog

# ==============================================================================
# GLOBAL SETUP
# ==============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "btprinter.preset.json")

# ==============================================================================
# 1. ROBUST CONFIG MANAGER
# ==============================================================================
class ConfigManager:
    DEFAULT_PROFILE = {
        "description": "New Profile",
        "keyword": "BlueTooth Printer",
        "protocol": "TSPL",
        "paper_width_mm": 100,
        "fixed_label_height_mm": 0,
        "dots_per_mm": 8,
        "feed_extra_dots": 0,
        "add_height_margin_mm": 0,
        "baudrate": 9600,
        "invert_image": True,
        "density": 10,
        "speed": 3,
        "sensor_type": "GAP",
        "action_type": "TEAR",
        "init_commands": []
    }

    DEFAULT_CONFIG = {
        "selected_profile": "Default TSPL",
        "profiles": {
            "Default TSPL": DEFAULT_PROFILE.copy()
        }
    }

    @staticmethod
    def load():
        if not os.path.exists(CONFIG_FILE):
            ConfigManager.reset_to_default()
            return ConfigManager.DEFAULT_CONFIG

        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
            # Ensure at least one profile exists
            if not data.get("profiles"):
                return ConfigManager.DEFAULT_CONFIG
            return data
        except json.JSONDecodeError:
            print(f"[ERROR] JSON is corrupt. Backing up and resetting.")
            shutil.copy(CONFIG_FILE, CONFIG_FILE + ".corrupt.bak")
            ConfigManager.reset_to_default()
            return ConfigManager.DEFAULT_CONFIG

    @staticmethod
    def save(data):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            print(f"[ERROR] Could not save config: {e}")
            return False

    @staticmethod
    def reset_to_default():
        with open(CONFIG_FILE, 'w') as f:
            json.dump(ConfigManager.DEFAULT_CONFIG, f, indent=4)

# ==============================================================================
# 2. GUI SETTINGS EDITOR (Profile Manager)
# ==============================================================================
class PrinterSettingsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Bluetooth Printer Studio (Profile Manager)")
        self.root.geometry("950x750")
        
        style = ttk.Style()
        try: style.theme_use('vista')
        except: pass

        self.data = ConfigManager.load()
        self.profiles = self.data.get("profiles", {})
        self.current_profile_key = None

        # Variables
        self.var_selected_default = tk.StringVar(value=self.data.get("selected_profile", ""))
        
        # Form Vars
        self.var_desc = tk.StringVar()
        self.var_keyword = tk.StringVar()
        self.var_protocol = tk.StringVar()
        self.var_width = tk.IntVar()
        self.var_height_fixed = tk.IntVar()
        self.var_dpmm = tk.IntVar()
        self.var_feed = tk.IntVar()
        self.var_margin = tk.IntVar()
        self.var_baud = tk.IntVar()
        self.var_invert = tk.BooleanVar()
        self.var_density = tk.IntVar()
        self.var_speed = tk.IntVar()
        self.var_sensor = tk.StringVar()
        self.var_action = tk.StringVar()

        self.build_ui()
        self.refresh_profile_list()

    def build_ui(self):
        # --- MENU BAR (Import/Export) ---
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Import Profile (JSON)", command=self.cmd_import)
        filemenu.add_command(label="Export Current Profile", command=self.cmd_export)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.destroy)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

        # --- LEFT PANEL (List & Tools) ---
        left_frame = ttk.Frame(self.root, padding=10)
        left_frame.pack(side="left", fill="y")
        
        ttk.Label(left_frame, text="Profiles:").pack(anchor="w")
        self.profile_listbox = tk.Listbox(left_frame, height=30, width=25, exportselection=False)
        self.profile_listbox.pack(fill="y", expand=True, pady=5)
        self.profile_listbox.bind('<<ListboxSelect>>', self.on_profile_select)

        # Toolbar
        toolbar = ttk.Frame(left_frame)
        toolbar.pack(fill="x", pady=5)
        
        # Row 1
        ttk.Button(toolbar, text="+ New", width=8, command=self.cmd_new).grid(row=0, column=0, padx=1, pady=1)
        ttk.Button(toolbar, text="Copy", width=8, command=self.cmd_copy).grid(row=0, column=1, padx=1, pady=1)
        # Row 2
        ttk.Button(toolbar, text="Rename", width=8, command=self.cmd_rename).grid(row=1, column=0, padx=1, pady=1)
        ttk.Button(toolbar, text="Delete", width=8, command=self.cmd_delete).grid(row=1, column=1, padx=1, pady=1)

        # --- RIGHT PANEL (Form) ---
        right_frame = ttk.Frame(self.root, padding=10)
        right_frame.pack(side="right", fill="both", expand=True)

        # 1. Global
        gf = ttk.LabelFrame(right_frame, text="Global Defaults", padding=10)
        gf.pack(fill="x", pady=(0, 5))
        ttk.Label(gf, text="Default Profile:").pack(side="left")
        self.combo_default = ttk.Combobox(gf, textvariable=self.var_selected_default, state="readonly")
        self.combo_default.pack(side="left", padx=5)

        # 2. Connection
        cf = ttk.LabelFrame(right_frame, text="Connection & Protocol", padding=10)
        cf.pack(fill="x", pady=5)
        
        def grid_entry(parent, lbl, var, r, c, w=15):
            ttk.Label(parent, text=lbl).grid(row=r, column=c, sticky="e", padx=5, pady=2)
            ttk.Entry(parent, textvariable=var, width=w).grid(row=r, column=c+1, sticky="w", padx=5, pady=2)

        grid_entry(cf, "Description:", self.var_desc, 0, 0, 25)
        grid_entry(cf, "Keyword:", self.var_keyword, 0, 2)
        grid_entry(cf, "Baudrate:", self.var_baud, 1, 0)
        
        ttk.Label(cf, text="Protocol:").grid(row=1, column=2, sticky="e")
        ttk.Combobox(cf, textvariable=self.var_protocol, values=["TSPL", "CPCL"], state="readonly", width=12).grid(row=1, column=3, sticky="w")

        # 3. Geometry
        geo = ttk.LabelFrame(right_frame, text="Paper Geometry", padding=10)
        geo.pack(fill="x", pady=5)
        grid_entry(geo, "Width (mm):", self.var_width, 0, 0)
        grid_entry(geo, "DPI (8=203):", self.var_dpmm, 0, 2)
        
        ttk.Label(geo, text="Label Height (mm):").grid(row=1, column=0, sticky="e", padx=5)
        ttk.Entry(geo, textvariable=self.var_height_fixed, width=15).grid(row=1, column=1, sticky="w", padx=5)
        ttk.Label(geo, text="(0 = Auto/Receipt)").grid(row=1, column=2, columnspan=2, sticky="w")

        grid_entry(geo, "Extra Feed:", self.var_feed, 2, 0)
        ttk.Checkbutton(geo, variable=self.var_invert, text="Invert Image").grid(row=2, column=2, columnspan=2, sticky="w")

        # 4. Hardware
        qf = ttk.LabelFrame(right_frame, text="Hardware Sensors", padding=10)
        qf.pack(fill="x", pady=5)

        ttk.Label(qf, text="Density (Heat):").grid(row=0, column=0, sticky="e")
        tk.Scale(qf, from_=0, to=15, orient="horizontal", variable=self.var_density).grid(row=0, column=1, sticky="ew")
        
        ttk.Label(qf, text="Speed:").grid(row=0, column=2, sticky="e")
        ttk.Combobox(qf, textvariable=self.var_speed, values=[1,2,3,4,5,6], width=5, state="readonly").grid(row=0, column=3, sticky="w")

        ttk.Label(qf, text="Sensor:").grid(row=1, column=0, sticky="e")
        ttk.Combobox(qf, textvariable=self.var_sensor, values=["GAP", "CONTINUOUS", "BLINE"], state="readonly").grid(row=1, column=1, sticky="ew")

        ttk.Label(qf, text="Post-Print:").grid(row=1, column=2, sticky="e")
        ttk.Combobox(qf, textvariable=self.var_action, values=["TEAR", "NONE", "PEEL", "CUTTER"], state="readonly").grid(row=1, column=3, sticky="ew")

        # 5. Raw Commands
        af = ttk.LabelFrame(right_frame, text="Raw Init Commands (One per line)", padding=10)
        af.pack(fill="both", expand=True, pady=5)
        self.txt_init = Text(af, height=5, font=("Consolas", 9))
        self.txt_init.pack(fill="both", expand=True)

        # Buttons
        bf = ttk.Frame(right_frame)
        bf.pack(fill="x", pady=10)
        ttk.Button(bf, text="Close", command=self.root.destroy).pack(side="right", padx=5)
        ttk.Button(bf, text="Apply (Save)", command=self.save_to_disk).pack(side="right", padx=5)

    # --- LIST MANAGEMENT ---
    def refresh_profile_list(self, select_key=None):
        self.profile_listbox.delete(0, tk.END)
        keys = sorted(list(self.profiles.keys()))
        for k in keys:
            self.profile_listbox.insert(tk.END, k)
        
        # Update combo defaults
        self.combo_default['values'] = keys
        
        if select_key and select_key in keys:
            idx = keys.index(select_key)
            self.profile_listbox.selection_set(idx)
            self.on_profile_select(None)
        elif keys:
            self.profile_listbox.selection_set(0)
            self.on_profile_select(None)

    def on_profile_select(self, event):
        selection = self.profile_listbox.curselection()
        if not selection: return
        new_key = self.profile_listbox.get(selection[0])
        
        if self.current_profile_key and self.current_profile_key != new_key:
            self.capture_form(self.current_profile_key)

        self.current_profile_key = new_key
        p = self.profiles[new_key]
        self.load_profile_to_form(p)

    def load_profile_to_form(self, p):
        self.var_desc.set(p.get("description", ""))
        self.var_keyword.set(p.get("keyword", ""))
        self.var_protocol.set(p.get("protocol", "TSPL"))
        self.var_width.set(p.get("paper_width_mm", 100))
        self.var_height_fixed.set(p.get("fixed_label_height_mm", 0))
        self.var_dpmm.set(p.get("dots_per_mm", 8))
        self.var_feed.set(p.get("feed_extra_dots", 0))
        self.var_baud.set(p.get("baudrate", 9600))
        self.var_invert.set(p.get("invert_image", True))
        self.var_density.set(p.get("density", 10))
        self.var_speed.set(p.get("speed", 3))
        self.var_sensor.set(p.get("sensor_type", "GAP"))
        self.var_action.set(p.get("action_type", "TEAR"))
        self.txt_init.delete("1.0", tk.END)
        if "init_commands" in p:
            self.txt_init.insert("1.0", "\n".join(p["init_commands"]))

    def capture_form(self, key):
        if key not in self.profiles: return
        raw = self.txt_init.get("1.0", tk.END).strip()
        cmds = [x.strip() for x in raw.split('\n') if x.strip()]
        
        self.profiles[key].update({
            "description": self.var_desc.get(),
            "keyword": self.var_keyword.get(),
            "protocol": self.var_protocol.get(),
            "paper_width_mm": self.var_width.get(),
            "fixed_label_height_mm": self.var_height_fixed.get(),
            "dots_per_mm": self.var_dpmm.get(),
            "feed_extra_dots": self.var_feed.get(),
            "add_height_margin_mm": self.var_margin.get(),
            "baudrate": self.var_baud.get(),
            "invert_image": self.var_invert.get(),
            "density": self.var_density.get(),
            "speed": self.var_speed.get(),
            "sensor_type": self.var_sensor.get(),
            "action_type": self.var_action.get(),
            "init_commands": cmds
        })

    # --- ACTIONS ---
    def cmd_new(self):
        new_name = simpledialog.askstring("New Profile", "Enter profile name:")
        if new_name:
            if new_name in self.profiles:
                messagebox.showerror("Error", "Profile name already exists.")
                return
            self.capture_form(self.current_profile_key)
            self.profiles[new_name] = ConfigManager.DEFAULT_PROFILE.copy()
            self.refresh_profile_list(new_name)

    def cmd_copy(self):
        if not self.current_profile_key: return
        new_name = simpledialog.askstring("Copy Profile", "Enter name for copy:")
        if new_name:
            if new_name in self.profiles:
                messagebox.showerror("Error", "Profile name already exists.")
                return
            self.capture_form(self.current_profile_key)
            self.profiles[new_name] = copy.deepcopy(self.profiles[self.current_profile_key])
            self.refresh_profile_list(new_name)

    def cmd_rename(self):
        if not self.current_profile_key: return
        new_name = simpledialog.askstring("Rename", "Enter new name:", initialvalue=self.current_profile_key)
        if new_name and new_name != self.current_profile_key:
            if new_name in self.profiles:
                messagebox.showerror("Error", "Profile name already exists.")
                return
            self.capture_form(self.current_profile_key)
            data = self.profiles[self.current_profile_key]
            del self.profiles[self.current_profile_key]
            self.profiles[new_name] = data
            
            # Update default if needed
            if self.var_selected_default.get() == self.current_profile_key:
                self.var_selected_default.set(new_name)
                
            self.refresh_profile_list(new_name)

    def cmd_delete(self):
        if not self.current_profile_key: return
        if len(self.profiles) <= 1:
            messagebox.showerror("Error", "Cannot delete the last profile.")
            return
        if messagebox.askyesno("Confirm", f"Delete '{self.current_profile_key}'?"):
            del self.profiles[self.current_profile_key]
            self.current_profile_key = None
            self.refresh_profile_list()

    def cmd_export(self):
        if not self.current_profile_key: return
        self.capture_form(self.current_profile_key)
        f = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if f:
            data = {
                "profile_name": self.current_profile_key,
                "data": self.profiles[self.current_profile_key]
            }
            try:
                with open(f, 'w') as file:
                    json.dump(data, file, indent=4)
                messagebox.showinfo("Export", "Profile exported successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export: {e}")

    def cmd_import(self):
        f = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if f:
            try:
                with open(f, 'r') as file:
                    data = json.load(file)
                
                # Check format
                if "profile_name" in data and "data" in data:
                    name = data["profile_name"]
                    p_data = data["data"]
                else:
                    # Assume simple dict
                    name = os.path.splitext(os.path.basename(f))[0]
                    p_data = data

                if name in self.profiles:
                    if not messagebox.askyesno("Conflict", f"Profile '{name}' exists. Overwrite?"):
                        return
                
                self.profiles[name] = p_data
                self.refresh_profile_list(name)
                messagebox.showinfo("Import", "Profile imported successfully.")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import: {e}")

    def save_to_disk(self):
        if self.current_profile_key: self.capture_form(self.current_profile_key)
        data = { "selected_profile": self.var_selected_default.get(), "profiles": self.profiles }
        if ConfigManager.save(data): messagebox.showinfo("Saved", "Configuration saved.")
        else: messagebox.showerror("Error", "Failed to save configuration.")

def open_gui():
    root = tk.Tk()
    app = PrinterSettingsApp(root)
    root.mainloop()

# ==============================================================================
# 3. GENERATORS (TSPL & CPCL)
# ==============================================================================
def generate_tspl(img, cfg, final_h_mm):
    wb = (img.size[0] + 7) // 8
    bmp_data = f"BITMAP 0,0,{wb},{img.size[1]},0,".encode('ascii') + img.tobytes()
    
    cmds = ["CLS"]
    cmds.append(f"SPEED {cfg.get('speed', 3)}")
    cmds.append(f"DENSITY {cfg.get('density', 10)}")
    
    st = cfg.get("sensor_type", "GAP")
    if st != "CONTINUOUS":
        # Limit feed safety
        cmds.append(f"LIMITFEED {final_h_mm + 20} mm")

    if st == "CONTINUOUS": cmds.append("GAP 0,0")
    elif st == "BLINE": cmds.append("BLINE 2 mm, 0")
    else: cmds.append("GAP 2 mm, 0")

    at = cfg.get("action_type", "TEAR")
    if at == "TEAR": cmds.extend(["SET TEAR ON", "SET PEEL OFF", "SET CUTTER OFF"])
    elif at == "PEEL": cmds.append("SET PEEL ON")
    elif at == "CUTTER": cmds.append("SET CUTTER ON")
    elif at == "NONE": cmds.append("SET TEAR OFF")

    init = cfg.get("init_commands", [])
    if init: cmds.extend(init)

    cmds.append(f"SIZE {cfg['paper_width_mm']} mm, {final_h_mm} mm")
    cmds.append(f"DIRECTION 1")
    
    header = "\r\n".join(cmds).encode('utf-8') + b"\r\n"
    footer = b"\r\nPRINT 1\r\n"
    ex = cfg.get("feed_extra_dots", 0)
    if ex > 0: footer += f"FEED {ex}\r\n".encode()

    return header + bmp_data + footer

def generate_cpcl(img, cfg, final_h_mm):
    # ! 0 200 200 {height} 1
    # PAGE-WIDTH {width}
    # BAR-SENSE
    
    h_dots = img.size[1]
    # In CPCL, height must be set in header
    cmds = [f"! 0 200 200 {int(h_dots + 50)} 1"]
    
    w_dots = int(cfg["paper_width_mm"] * cfg["dots_per_mm"])
    cmds.append(f"PAGE-WIDTH {w_dots}")
    
    st = cfg.get("sensor_type", "GAP")
    if st == "CONTINUOUS": cmds.append("JOURNAL")
    else: cmds.append("BAR-SENSE")
    
    # Init Commands
    init = cfg.get("init_commands", [])
    if init: cmds.extend(init)

    header = "\r\n".join(cmds).encode('utf-8') + b"\r\n"
    
    # Graphic: EG width_bytes height x y data
    wb = (img.size[0] + 7) // 8
    img_cmd = f"EG {wb} {img.size[1]} 0 0 ".encode('ascii') + img.tobytes() + b"\r\n"
    
    # Footer (Form Feed)
    if st == "CONTINUOUS": footer = b"PRINT\r\n"
    else: footer = b"FORM\r\n"
    
    return header + img_cmd + footer

# ==============================================================================
# 4. PORT SCANNING
# ==============================================================================
def get_friendly_port_map():
    mac_to_name = {}
    reg_path = r"SYSTEM\CurrentControlSet\Enum\BTHENUM"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    sub = winreg.EnumKey(key, i)
                    if sub.startswith("Dev_"):
                        mac = sub.split("_")[1]
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{reg_path}\\{sub}") as dkey:
                            for j in range(winreg.QueryInfoKey(dkey)[0]):
                                with winreg.OpenKey(dkey, winreg.EnumKey(dkey, j)) as ikey:
                                    try:
                                        name, _ = winreg.QueryValueEx(ikey, "FriendlyName")
                                        mac_to_name[mac] = name
                                    except: pass
                except: continue
    except: pass

    final_map = {}
    ports = serial.tools.list_ports.comports()
    for p in ports:
        name = p.description
        clean_hwid = re.sub(r'[^A-F0-9]', '', p.hwid.upper())
        for mac, fname in mac_to_name.items():
            if mac.upper() in clean_hwid:
                name = fname
                break
        final_map[p.device] = name
    return final_map

def get_port_manual():
    print("\n--- Scanning Ports (Registry Enhanced) ---")
    pmap = get_friendly_port_map()
    sorted_keys = sorted(pmap.keys(), key=lambda x: int(x.replace("COM","")) if "COM" in x else x)
    if not sorted_keys: return None
    valid_ports = []
    for i, port in enumerate(sorted_keys):
        name = pmap[port]
        prefix = "** " if any(x in name.upper() for x in ["PRINTER", "LP-", "RPP", "POS"]) else "   "
        print(f"[{i}] {port:<6} | {prefix}{name}")
        valid_ports.append(port)
    while True:
        try:
            sel = input("\nEnter ID number to select: ")
            return valid_ports[int(sel)]
        except: print("Invalid selection.")

def find_port_auto(keyword):
    print(f"--- Auto-scanning for '{keyword}' ---")
    pmap = get_friendly_port_map()
    for port, name in pmap.items():
        if keyword.lower() in name.lower():
            return port, name
    return None, None

# ==============================================================================
# 5. IMAGE PROCESSOR
# ==============================================================================
def image_to_bitmap(pil_image, cfg):
    target_w = cfg["paper_width_mm"] * cfg["dots_per_mm"]
    should_invert = cfg.get("invert_image", True)
    if pil_image.mode in ('RGBA', 'LA'):
        bg = Image.new('RGB', pil_image.size, (255, 255, 255))
        bg.paste(pil_image, mask=pil_image.split()[-1])
        pil_image = bg
    w, h = pil_image.size
    if w > target_w:
        ratio = target_w / w
        pil_image = pil_image.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)
    img = pil_image.convert('L')
    if should_invert: img = ImageOps.invert(img)
    img = img.convert('1')
    return img

# ==============================================================================
# 6. MAIN
# ==============================================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--printer", help="Override printer profile")
    parser.add_argument("-e", "--edit", action="store_true", help="Open Settings GUI")
    parser.add_argument("-s", "--scan", action="store_true", help="Force manual port selection")
    parser.add_argument("files", nargs="*", help="PDF files")
    args = parser.parse_args()

    if args.edit:
        open_gui()
        return

    if not args.files:
        print("Usage: python btprint.py [files] OR python btprint.py -e")
        return

    data = ConfigManager.load()
    p_name = args.printer if args.printer else data["selected_profile"]
    cfg = data["profiles"].get(p_name)
    if not cfg:
        print(f"[ERROR] Profile '{p_name}' not found.")
        return
    
    files = []
    for f in args.files: files.extend(glob.glob(f) or [f])
    if not files: return

    protocol = cfg.get("protocol", "TSPL")
    print(f"Profile: {p_name} | Protocol: {protocol} | Mode: {cfg.get('sensor_type', 'GAP')}")

    port = None
    if args.scan: port = get_port_manual()
    else:
        port, name = find_port_auto(cfg["keyword"])
        if not port: port = get_port_manual()

    if not port: return

    try:
        with serial.Serial(port, cfg["baudrate"], timeout=3, dsrdtr=True) as p:
            print(f"Connected to {port}. Initializing...")
            time.sleep(1.5)

            for fname in files:
                if not os.path.exists(fname): continue
                print(f"Processing: {fname}...")
                
                try:
                    doc = fitz.open(fname)
                    for i, page in enumerate(doc):
                        print(f"  > Page {i+1}...", end="\r")
                        pix = page.get_pixmap(dpi=203)
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        
                        # Process Image
                        img_1bit = image_to_bitmap(img, cfg)

                        # Determine Height
                        fixed_h = cfg.get("fixed_label_height_mm", 0)
                        if fixed_h > 0:
                            final_h_mm = fixed_h
                        else:
                            final_h_mm = int(img_1bit.size[1] / cfg["dots_per_mm"])

                        # Dispatch Protocol
                        if protocol == "CPCL":
                            data_bytes = generate_cpcl(img_1bit, cfg, final_h_mm)
                        else:
                            data_bytes = generate_tspl(img_1bit, cfg, final_h_mm)
                        
                        p.write(data_bytes)
                        p.flush()
                        time.sleep(1.5)
                    doc.close()
                except Exception as e:
                    print(f"  [Error] {e}")

    except Exception as e:
        print(f"[CRITICAL] {e}")
        if "semaphore" in str(e).lower():
            print(">> FIX: Remove device from Windows Settings and Re-Pair.")

if __name__ == "__main__":
    main()