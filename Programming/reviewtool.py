#!/usr/bin/env python3
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from PIL import Image, ImageTk

# ==========================================
# CONFIGURATION
# ==========================================

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif'}
TEXT_EXTENSIONS = {'.txt', '.md', '.srt', '.log', '.json', '.xml', '.csv', '.ini', '.cfg', '.yaml', '.yml', '.rst', '.html', '.htm'}

# Dark Mode Palette
COLORS = {
    "bg": "#1e1e1e",           # Main Window Background
    "fg": "#e0e0e0",           # Main Text Color
    "panel_bg": "#252526",     # Pane Background
    "input_bg": "#1e1e1e",     # Text Editor Background
    "input_fg": "#d4d4d4",     # Text Editor Text
    "cursor":   "#ffffff",     # Cursor Color
    "btn_bg":   "#333333",     # Button Background
    "btn_fg":   "#ffffff",     # Button Text
    "btn_active": "#505050",   # Button Hover
    "highlight": "#007acc"     # Accent Blue
}

class TranscriptionReviewer:
    def __init__(self, root, working_dir):
        self.root = root
        self.root.title("Transcription Reviewer")
        
        # Maximize Window (Windows compliant)
        try:
            self.root.state('zoomed')
        except:
            # Fallback for Linux/Mac
            self.root.attributes('-zoomed', True)
            
        self.root.configure(bg=COLORS["bg"])
        
        self.working_dir = working_dir
        self.pairs = [] 
        self.current_index = 0
        self.image_ref = None 
        self.original_image = None
        
        self.all_versions = set()
        self.current_version_var = tk.StringVar()

        # UI Setup
        self._setup_ui()
        
        # Load Files
        self._find_files_fuzzy()
        self._update_version_dropdown()
        
        if self.pairs:
            self.load_pair(0)
        else:
            messagebox.showinfo("No Files", f"No matching pairs found in:\n{self.working_dir}")
            self.root.destroy()
            return

        # FORCE 50/50 SPLIT
        # We wait 100ms for the window to render, then force sash position
        self.root.after(100, self._force_50_split)

    def _setup_ui(self):
        # 1. Paned Window
        self.paned_window = tk.PanedWindow(
            self.root, 
            orient=tk.HORIZONTAL, 
            bg=COLORS["bg"], 
            sashwidth=6,
            sashrelief=tk.RAISED,
            opaqueresize=False
        )
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # 2. Left Side: Image
        self.image_frame = tk.Frame(self.paned_window, bg=COLORS["panel_bg"])
        self.paned_window.add(self.image_frame, stretch="always")
        
        self.image_label = tk.Label(self.image_frame, bg=COLORS["panel_bg"])
        self.image_label.pack(fill=tk.BOTH, expand=True)
        
        # 3. Right Side: Text Editor
        self.text_frame = tk.Frame(self.paned_window, bg=COLORS["panel_bg"])
        self.paned_window.add(self.text_frame, stretch="always")
        
        self.text_editor = scrolledtext.ScrolledText(
            self.text_frame, 
            font=("Consolas", 13), 
            wrap=tk.WORD,
            bg=COLORS["input_bg"],
            fg=COLORS["input_fg"],
            insertbackground=COLORS["cursor"],
            selectbackground=COLORS["highlight"],
            relief=tk.FLAT,
            padx=15, pady=15,
            width=40 # Increased default width to ensure visibility
        )
        self.text_editor.pack(fill=tk.BOTH, expand=True)
        
        # 4. Bottom Bar: Controls
        self.control_frame = tk.Frame(self.root, bg=COLORS["bg"])
        self.control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def style_btn(btn):
            btn.config(
                bg=COLORS["btn_bg"], fg=COLORS["btn_fg"], 
                activebackground=COLORS["btn_active"], activeforeground=COLORS["btn_fg"],
                relief=tk.FLAT, bd=0, padx=15, pady=6, font=("Segoe UI", 10)
            )

        self.btn_prev = tk.Button(self.control_frame, text="<< Prev (PgUp)", command=self.prev_pair)
        style_btn(self.btn_prev)
        self.btn_prev.pack(side=tk.LEFT)
        
        self.lbl_status = tk.Label(self.control_frame, text="0 / 0", font=("Segoe UI", 11, "bold"), bg=COLORS["bg"], fg=COLORS["fg"])
        self.lbl_status.pack(side=tk.LEFT, padx=20)
        
        self.btn_next = tk.Button(self.control_frame, text="Next >> (PgDn)", command=self.next_pair)
        style_btn(self.btn_next)
        self.btn_next.pack(side=tk.LEFT)
        
        # Version Selection
        self.lbl_version = tk.Label(self.control_frame, text="Version:", fg=COLORS["fg"], bg=COLORS["bg"], font=("Segoe UI", 9))
        self.lbl_version.pack(side=tk.LEFT, padx=(20, 5))
        
        self.combo_version = ttk.Combobox(self.control_frame, textvariable=self.current_version_var, state="readonly", width=15)
        self.combo_version.pack(side=tk.LEFT)
        self.combo_version.bind("<<ComboboxSelected>>", lambda e: self.load_pair(self.current_index))

        self.lbl_filename = tk.Label(self.control_frame, text="", fg=COLORS["highlight"], bg=COLORS["bg"], font=("Segoe UI", 9))
        self.lbl_filename.pack(side=tk.LEFT, padx=20)

        self.btn_save = tk.Button(self.control_frame, text="Save (Ctrl+S)", command=self.save_current_text)
        style_btn(self.btn_save)
        self.btn_save.config(bg="#2e5e2e") 
        self.btn_save.pack(side=tk.RIGHT)

        self.btn_refresh = tk.Button(self.control_frame, text="Refresh", command=self.refresh_data)
        style_btn(self.btn_refresh)
        self.btn_refresh.config(bg="#4a4a4a")
        self.btn_refresh.pack(side=tk.RIGHT, padx=10)

        # Bindings
        self.root.bind('<Control-s>', lambda e: self.save_current_text())
        self.root.bind('<Prior>', lambda e: self.prev_pair()) 
        self.root.bind('<Next>', lambda e: self.next_pair())
        self.image_frame.bind('<Configure>', self._resize_image_event)

    def _force_50_split(self):
        window_width = self.paned_window.winfo_width()
        if window_width > 1:
            self.paned_window.sash_place(0, window_width // 2, 0)

    def _find_files_fuzzy(self):
        try:
            files_in_root = os.listdir(self.working_dir)
        except Exception as e:
            print(f"Error reading directory: {e}")
            return

        images = sorted([f for f in files_in_root if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS])
        text_files_root = sorted([f for f in files_in_root if os.path.splitext(f)[1].lower() in TEXT_EXTENSIONS])
        
        # Find subdirectories
        subdirs = [d for d in files_in_root if os.path.isdir(os.path.join(self.working_dir, d))]
        
        for img_file in images:
            img_basename = os.path.splitext(img_file)[0]
            versions = {}
            
            # 1. Look for Default (Root)
            match = None
            if f"{img_basename}.txt" in text_files_root:
                match = f"{img_basename}.txt"
            else:
                candidates = [t for t in text_files_root if t.startswith(img_basename)]
                if candidates: match = candidates[0]
            
            if match:
                versions["Default"] = os.path.join(self.working_dir, match)

            # 2. Look in Subdirectories
            for subdir in subdirs:
                subdir_path = os.path.join(self.working_dir, subdir)
                try:
                    subdir_files = os.listdir(subdir_path)
                    # Check for exact name match first
                    if f"{img_basename}.txt" in subdir_files:
                         versions[subdir] = os.path.join(subdir_path, f"{img_basename}.txt")
                    else:
                        # Fuzzy match in subdir? Maybe overkill, but consistent
                        candidates = [t for t in subdir_files if t.startswith(img_basename) and os.path.splitext(t)[1].lower() in TEXT_EXTENSIONS]
                        if candidates:
                             versions[subdir] = os.path.join(subdir_path, candidates[0])
                except Exception:
                    continue

            if versions:
                self.pairs.append((os.path.join(self.working_dir, img_file), versions))
                self.all_versions.update(versions.keys())
        
        if "Default" not in self.all_versions and self.all_versions:
            print("No Default version found. Versions available:", self.all_versions)

        print(f"Found {len(self.pairs)} pairs with versions: {self.all_versions}")

    def _update_version_dropdown(self):
        sorted_versions = sorted(list(self.all_versions))
        if "Default" in sorted_versions:
            # Move Default to top
            sorted_versions.remove("Default")
            sorted_versions.insert(0, "Default")
        
        self.combo_version['values'] = sorted_versions
        if sorted_versions:
            if self.current_version_var.get() not in sorted_versions:
                self.current_version_var.set(sorted_versions[0])
        else:
            self.current_version_var.set("")

    def load_pair(self, index):
        if not (0 <= index < len(self.pairs)): return
        self.current_index = index
        img_path, versions = self.pairs[index]
        
        selected_ver = self.current_version_var.get()
        txt_path = versions.get(selected_ver)

        self.root.title(f"Reviewing: {os.path.basename(img_path)}")
        self.lbl_status.config(text=f"{index + 1} / {len(self.pairs)}")
        
        if txt_path:
            self.lbl_filename.config(text=f"{selected_ver}: {os.path.basename(txt_path)}")
            try:
                print(f"Loading text file: {txt_path}")
                with open(txt_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if not content:
                    content = "[File is empty]"

                self.text_editor.delete('1.0', tk.END)
                self.text_editor.insert('1.0', content)
                self.text_editor.config(state=tk.NORMAL, bg=COLORS["input_bg"])
                
                # FOCUS TEXT EDITOR
                self.text_editor.focus_set()
                
            except Exception as e:
                self.text_editor.delete('1.0', tk.END)
                self.text_editor.insert('1.0', f"Error: {e}")
        else:
             self.lbl_filename.config(text=f"{selected_ver}: (Not Found)")
             self.text_editor.delete('1.0', tk.END)
             self.text_editor.insert('1.0', f"[No text file found for version '{selected_ver}' for this image]")
             # Could disable editing here if desired
             # self.text_editor.config(state=tk.DISABLED, bg="#333333")


        try:
            self.original_image = Image.open(img_path)
            self._display_image()
        except: pass

    def _display_image(self):
        if self.original_image is None: return
        frame_width = self.image_frame.winfo_width()
        frame_height = self.image_frame.winfo_height()
        
        if frame_width < 10: return

        img_w, img_h = self.original_image.size
        ratio = min(frame_width/img_w, frame_height/img_h)
        new_w = int(img_w * ratio)
        new_h = int(img_h * ratio)
        
        resized = self.original_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.image_ref = ImageTk.PhotoImage(resized)
        self.image_label.config(image=self.image_ref)

    def _resize_image_event(self, event):
        self._display_image()

    def save_current_text(self):
        if not self.pairs: return
        _, versions = self.pairs[self.current_index]
        selected_ver = self.current_version_var.get()
        txt_path = versions.get(selected_ver)
        
        if not txt_path:
            messagebox.showerror("Save Error", f"No file exists for version '{selected_ver}' to save to.")
            return

        content = self.text_editor.get('1.0', 'end-1c')
        try:
            with open(txt_path, 'w', encoding='utf-8') as f: f.write(content)
            orig_bg = self.btn_save.cget("background")
            self.btn_save.config(bg="#44aa44", text="Saved!")
            self.root.after(500, lambda: self.btn_save.config(bg=orig_bg, text="Save (Ctrl+S)"))
        except Exception as e:
            messagebox.showerror("Save Error", f"{e}")

    def next_pair(self):
        self.save_current_text() 
        if self.current_index < len(self.pairs) - 1: self.load_pair(self.current_index + 1)
        else: messagebox.showinfo("Done", "End of list.")

    def prev_pair(self):
        self.save_current_text() 
        if self.current_index > 0: self.load_pair(self.current_index - 1)

    def refresh_data(self):
        """Re-scans the directories for text versions and reloads the current pair."""
        old_index = self.current_index
        old_version = self.current_version_var.get()
        
        self.pairs = []
        self.all_versions = set()
        
        self._find_files_fuzzy()
        self._update_version_dropdown()
        
        if old_version in self.all_versions:
            self.current_version_var.set(old_version)
            
        if self.pairs:
            # Try to stay on the same image index
            new_index = min(old_index, len(self.pairs) - 1)
            self.load_pair(new_index)
            
            orig_bg = self.btn_refresh.cget("background")
            self.btn_refresh.config(bg=COLORS["highlight"], text="Refreshed!")
            self.root.after(800, lambda: self.btn_refresh.config(bg=orig_bg, text="Refresh"))
        else:
            messagebox.showinfo("No Files", f"No matching pairs found in:\n{self.working_dir}")

if __name__ == "__main__":
    target_dir = os.getcwd()
    root = tk.Tk()
    app = TranscriptionReviewer(root, target_dir)
    root.mainloop()