#!/usr/bin/env python3
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from PIL import Image, ImageTk
import re
import io
import ctypes

# ==========================================
# CONFIGURATION
# ==========================================

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif'}
TEXT_EXTENSIONS = {'.txt', '.md', '.srt', '.log', '.json', '.xml', '.csv', '.ini', '.cfg', '.yaml', '.yml', '.rst', '.html', '.htm'}

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

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
        self.current_txt_path = None
        self.current_file_loaded_empty = False
        self.needs_fit = False
        
        self.all_versions = set()
        self.current_version_var = tk.StringVar()
        self.last_mtime = None  # Track modification time for auto-reload

        # UI State
        self.zoom_factor = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.text_font_size = 13
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self.split_attempts = 10
        self.split_settled = False
        self.allow_render = False

        # UI Setup
        self._setup_ui()
        
        # Load Files
        self._find_files_fuzzy()
        self._update_version_dropdown()
        
        if self.pairs:
            self._update_page_dropdown()
            self.load_pair(0)
        else:
            messagebox.showinfo("No Files", f"No matching pairs found in:\n{self.working_dir}")
            self.root.destroy()
            return

        # FORCE 50/50 SPLIT
        # Keep trying briefly during startup until the panes have real size.
        self.root.after(100, self._schedule_split_enforce)
        self.root.bind('<Map>', lambda e: self._schedule_split_enforce())

        # Start auto-reload check loop
        self.root.after(1000, self._check_file_modifications)

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
        
        self.image_canvas = tk.Canvas(self.image_frame, bg=COLORS["panel_bg"], highlightthickness=0)
        self.image_canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas_image_id = None
        
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
        
        self.combo_page = ttk.Combobox(self.control_frame, state="readonly", width=5)
        self.combo_page.pack(side=tk.LEFT, padx=(20, 0))
        self.combo_page.bind("<<ComboboxSelected>>", self._on_page_selected)
        
        self.lbl_page_total = tk.Label(self.control_frame, text=" / 0", font=("Segoe UI", 11, "bold"), bg=COLORS["bg"], fg=COLORS["fg"])
        self.lbl_page_total.pack(side=tk.LEFT, padx=(0, 20))
        
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
        self.btn_copy_image = tk.Button(self.control_frame, text="Copy Image (Ctrl+C)", command=self.copy_current_image_to_clipboard)
        style_btn(self.btn_copy_image)
        self.btn_copy_image.config(bg="#3b3b3b")
        self.btn_copy_image.pack(side=tk.RIGHT)

        self.btn_open_ext = tk.Button(self.control_frame, text="Open Ext", command=self.open_external_editor)
        style_btn(self.btn_open_ext)
        self.btn_open_ext.config(bg="#4a4a4a")
        self.btn_open_ext.pack(side=tk.RIGHT, padx=(0, 10))

        # Bindings
        self.root.bind('<Control-s>', lambda e: self.save_current_text())
        self.root.bind('<Prior>', lambda e: self.prev_pair(jump_set=False)) 
        self.root.bind('<Next>', lambda e: self.next_pair(jump_set=False))
        self.root.bind('<Shift-Prior>', lambda e: self.prev_pair(jump_set=True))
        self.root.bind('<Shift-Next>', lambda e: self.next_pair(jump_set=True))

        # IMPORTANT: Bind to text_editor and return "break" to suppress default scrolling
        self.text_editor.bind('<Prior>', lambda e: self.prev_pair(jump_set=False) or "break")
        self.text_editor.bind('<Next>', lambda e: self.next_pair(jump_set=False) or "break")
        self.text_editor.bind('<Shift-Prior>', lambda e: self.prev_pair(jump_set=True) or "break")
        self.text_editor.bind('<Shift-Next>', lambda e: self.next_pair(jump_set=True) or "break")

        self.image_frame.bind('<Configure>', self._resize_image_event)
        
        # Zoom and Pan Bindings for Image
        self.image_canvas.bind('<Control-MouseWheel>', self._on_image_zoom)
        self.image_canvas.bind('<Button-3>', self._on_pan_start)
        self.image_canvas.bind('<B3-Motion>', self._on_pan_drag)
        self.image_canvas.bind('<Button-1>', self._focus_image_canvas)
        self.image_canvas.bind('<Control-c>', self._on_copy_image_shortcut)
        self.image_canvas.configure(takefocus=1)        
        # Zoom for Text
        self.text_editor.bind('<Control-MouseWheel>', self._on_text_zoom)

    def _check_file_modifications(self):
        """Periodically checks if the current text file has been modified externally."""
        if self.current_txt_path and os.path.exists(self.current_txt_path):
            try:
                new_mtime = os.path.getmtime(self.current_txt_path)
                if self.last_mtime is not None and new_mtime != self.last_mtime:
                    # If local editor is not modified, reload silently
                    if not self.text_editor.edit_modified():
                        print(f"File {self.current_txt_path} modified externally. Reloading...")
                        with open(self.current_txt_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        self.text_editor.delete('1.0', tk.END)
                        self.text_editor.insert('1.0', content)
                        self.text_editor.edit_modified(False)
                        self.current_file_loaded_empty = (content == "")
                        self.last_mtime = new_mtime
                    else:
                        # Editor is dirty, just acknowledge the new mtime but don't overwrite local changes
                        # This prevents constant "modified externally" logic if user keeps it dirty.
                        self.last_mtime = new_mtime
            except Exception as e:
                print(f"Error checking file modification: {e}")
        
        # Schedule next check
        self.root.after(1000, self._check_file_modifications)

    def _on_page_selected(self, event=None):
        try:
            new_index = int(self.combo_page.get()) - 1
            if 0 <= new_index < len(self.pairs):
                self.load_pair(new_index)
        except ValueError:
            pass

    def _update_page_dropdown(self):
        total_pages = len(self.pairs)
        self.combo_page['values'] = [str(i + 1) for i in range(total_pages)]
        self.lbl_page_total.config(text=f" / {total_pages}")

    def _force_50_split(self):
        if self.split_attempts <= 0:
            return
        window_width = self.paned_window.winfo_width()
        if window_width >= 200:
            self.paned_window.sash_place(0, window_width // 2, 0)
            self.split_attempts -= 1
            if not self.split_settled:
                self.split_settled = True
                self.allow_render = True
                self.needs_fit = False
            # After geometry settles, refit to the new pane size
            self.root.after_idle(lambda: self._display_image(reset_view=True))
        else:
            # Don't burn attempts until size is realistic
            return

    def _schedule_split_enforce(self):
        if self.split_attempts <= 0:
            return
        self._force_50_split()
        if self.split_attempts > 0:
            self.root.after(200, self._schedule_split_enforce)

    def _find_files_fuzzy(self):
        try:
            files_in_root = os.listdir(self.working_dir)
        except Exception as e:
            print(f"Error reading directory: {e}")
            return

        images = sorted([f for f in files_in_root if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS], key=natural_sort_key)
        
        # Find subdirectories
        subdirs = [d for d in files_in_root if os.path.isdir(os.path.join(self.working_dir, d))]
        
        # Pre-scan all text files in root and subdirs for range patterns
        def scan_text_files(directory):
            try:
                txts = [f for f in os.listdir(directory) if os.path.splitext(f)[1].lower() in TEXT_EXTENSIONS]
                return txts
            except:
                return []

        root_text_files = scan_text_files(self.working_dir)
        subdir_texts = {sd: scan_text_files(os.path.join(self.working_dir, sd)) for sd in subdirs}

        range_pattern = re.compile(r'page-(\d+)_to_page-(\d+)', re.IGNORECASE)

        def get_matching_texts(img_name, txt_list):
            img_basename = os.path.splitext(img_name)[0]
            # Try to get a number from the image name
            img_num_match = re.search(r'(\d+)', img_name)
            img_num = int(img_num_match.group(1)) if img_num_match else None
            
            matches = []
            for txt in txt_list:
                txt_basename = os.path.splitext(txt)[0]
                # 1. Exact or prefix match
                if txt_basename == img_basename or txt_basename.startswith(img_basename):
                    matches.append(txt)
                    continue
                
                # 2. Range match
                range_match = range_pattern.search(txt_basename)
                if range_match and img_num is not None:
                    start, end = int(range_match.group(1)), int(range_match.group(2))
                    if start <= img_num <= end:
                        matches.append(txt)
            return matches

        for img_file in images:
            versions = {}
            
            # 1. Look for matches in Root
            matches = get_matching_texts(img_file, root_text_files)
            if matches:
                # If multiple matches (rare), pick the first one as "Default"
                versions["Default"] = os.path.join(self.working_dir, matches[0])

            # 2. Look in Subdirectories
            for subdir in subdirs:
                matches = get_matching_texts(img_file, subdir_texts[subdir])
                if matches:
                    # Handle multiple versions in same subdir if needed (e.g. _1, _2)
                    for i, m in enumerate(matches):
                        ver_name = subdir if i == 0 else f"{subdir}_{i}"
                        versions[ver_name] = os.path.join(self.working_dir, subdir, m)

            # ALWAYS add the image, even if versions is empty
            self.pairs.append((os.path.join(self.working_dir, img_file), versions))
            self.all_versions.update(versions.keys())
        
        print(f"Found {len(self.pairs)} images with versions: {self.all_versions}")

    def _update_version_dropdown(self):
        sorted_versions = sorted(list(self.all_versions), key=natural_sort_key)
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
        self.combo_page.set(str(index + 1))
        self.lbl_page_total.config(text=f" / {len(self.pairs)}")
        
        if txt_path:
            self.lbl_filename.config(text=f"{selected_ver}: {os.path.basename(txt_path)}")
            try:
                print(f"Loading text file: {txt_path}")
                with open(txt_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                self.text_editor.delete('1.0', tk.END)
                self.text_editor.insert('1.0', content)
                self.text_editor.config(state=tk.NORMAL, bg=COLORS["input_bg"])
                self.text_editor.edit_modified(False)

                # FOCUS TEXT EDITOR
                self.text_editor.focus_set()
                self.current_txt_path = txt_path
                self.current_file_loaded_empty = (content == "")
                if os.path.exists(txt_path):
                    self.last_mtime = os.path.getmtime(txt_path)
                else:
                    self.last_mtime = None

            except FileNotFoundError:
                # File was deleted after initial scan: treat as blank and allow recreating on save.
                self.text_editor.delete('1.0', tk.END)
                self.text_editor.config(state=tk.NORMAL, bg=COLORS["input_bg"])
                self.text_editor.edit_modified(False)
                self.current_txt_path = txt_path
                self.current_file_loaded_empty = True
            except Exception as e:
                self.text_editor.delete('1.0', tk.END)
                self.text_editor.insert('1.0', f"Error: {e}")
                self.text_editor.edit_modified(False)
                self.current_txt_path = None
                self.current_file_loaded_empty = False
        else:
             self.lbl_filename.config(text=f"{selected_ver}: (Not Found)")
             self.text_editor.delete('1.0', tk.END)
             self.text_editor.insert('1.0', f"[No text file found for version '{selected_ver}' for this image]")
             self.text_editor.edit_modified(False)
             self.current_txt_path = None
             self.current_file_loaded_empty = False


        try:
            self.original_image = Image.open(img_path)
            # Defer fit until we have a real frame size
            self.needs_fit = True
            if self.split_settled:
                self.allow_render = True
                self._display_image(reset_view=True)
                # Also schedule a fit after idle to reduce first-draw jump
                self.root.after_idle(self._fit_image_after_idle)
            else:
                # Avoid flash of full-GUI render before panes settle
                self.allow_render = False
                self.image_canvas.delete("all")
                self._schedule_split_enforce()
        except: pass

    def _display_image(self, reset_view=False):
        if self.original_image is None: return
        if not self.allow_render: return
        
        frame_width = self.image_frame.winfo_width()
        frame_height = self.image_frame.winfo_height()
        if frame_width < 10 or frame_height < 10: return

        img_w, img_h = self.original_image.size
        
        if reset_view:
            # Fit to screen
            ratio = min(frame_width/img_w, frame_height/img_h)
            self.zoom_factor = ratio
            self.pan_x = (frame_width - img_w * self.zoom_factor) / 2
            self.pan_y = (frame_height - img_h * self.zoom_factor) / 2

        new_w = max(1, int(img_w * self.zoom_factor))
        new_h = max(1, int(img_h * self.zoom_factor))
        
        try:
            # Avoid excessive resizing for very small changes if needed, 
            # but usually LANCZOS is fine for interactive if not too huge.
            resized = self.original_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
            self.image_ref = ImageTk.PhotoImage(resized)
            
            if self.canvas_image_id:
                self.image_canvas.delete(self.canvas_image_id)
            
            self.canvas_image_id = self.image_canvas.create_image(
                self.pan_x, self.pan_y, anchor=tk.NW, image=self.image_ref
            )
        except Exception as e:
            print(f"Error rendering image: {e}")

    def _resize_image_event(self, event):
        # When container is resized (e.g. window resize or sash move)
        # We only want to reset view if we haven't zoomed/panned yet? 
        # Actually, let's just keep current zoom/pan but maybe re-center if it's the first load.
        # For now, let's just re-display.
        if self.needs_fit:
            frame_width = self.image_frame.winfo_width()
            frame_height = self.image_frame.winfo_height()
            if frame_width >= 10 and frame_height >= 10:
                self.needs_fit = False
                self._display_image(reset_view=True)
                return
        self._display_image()

    def _fit_image_after_idle(self):
        if not self.needs_fit:
            return
        frame_width = self.image_frame.winfo_width()
        frame_height = self.image_frame.winfo_height()
        if frame_width >= 10 and frame_height >= 10:
            self.needs_fit = False
            self._display_image(reset_view=True)

    def _on_image_zoom(self, event):
        if self.original_image is None: return
        
        # Zoom in/out factor
        scale = 1.1 if event.delta > 0 else 0.9
        
        # Mouse position relative to canvas
        mx = self.image_canvas.canvasx(event.x)
        my = self.image_canvas.canvasy(event.y)
        
        # Update zoom factor
        old_zoom = self.zoom_factor
        self.zoom_factor *= scale
        
        # Cap zoom
        self.zoom_factor = max(0.01, min(self.zoom_factor, 50.0))
        
        # Real scale used (might have been capped)
        actual_scale = self.zoom_factor / old_zoom
        
        # Adjust pan to zoom towards mouse cursor
        self.pan_x = mx - (mx - self.pan_x) * actual_scale
        self.pan_y = my - (my - self.pan_y) * actual_scale
        
        self._display_image()

    def _on_pan_start(self, event):
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y

    def _on_pan_drag(self, event):
        dx = event.x - self.last_mouse_x
        dy = event.y - self.last_mouse_y
        
        self.pan_x += dx
        self.pan_y += dy
        
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y
        
        self._display_image()

    def _focus_image_canvas(self, event=None):
        self.image_canvas.focus_set()

    def _on_copy_image_shortcut(self, event=None):
        self.copy_current_image_to_clipboard()
        return "break"

    def copy_current_image_to_clipboard(self):
        if self.original_image is None:
            messagebox.showwarning("Copy Image", "No image loaded to copy.")
            return

        if sys.platform != "win32":
            messagebox.showwarning("Copy Image", "Image clipboard copy is currently implemented for Windows only.")
            return

        try:
            image = self.original_image
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA")
            if image.mode == "RGBA":
                image = image.convert("RGB")

            output = io.BytesIO()
            image.save(output, "BMP")
            data = output.getvalue()[14:]  # CF_DIB expects BMP without file header.

            CF_DIB = 8
            GMEM_MOVEABLE = 0x0002

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

            SIZE_T = ctypes.c_size_t
            HANDLE = ctypes.c_void_p
            LPVOID = ctypes.c_void_p
            UINT = ctypes.c_uint

            kernel32.GlobalAlloc.argtypes = [UINT, SIZE_T]
            kernel32.GlobalAlloc.restype = HANDLE
            kernel32.GlobalLock.argtypes = [HANDLE]
            kernel32.GlobalLock.restype = LPVOID
            kernel32.GlobalUnlock.argtypes = [HANDLE]
            kernel32.GlobalUnlock.restype = ctypes.c_int
            kernel32.GlobalFree.argtypes = [HANDLE]
            kernel32.GlobalFree.restype = HANDLE

            user32.OpenClipboard.argtypes = [HANDLE]
            user32.OpenClipboard.restype = ctypes.c_int
            user32.EmptyClipboard.argtypes = []
            user32.EmptyClipboard.restype = ctypes.c_int
            user32.SetClipboardData.argtypes = [UINT, HANDLE]
            user32.SetClipboardData.restype = HANDLE
            user32.CloseClipboard.argtypes = []
            user32.CloseClipboard.restype = ctypes.c_int

            hglobal = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
            if not hglobal:
                raise ctypes.WinError(ctypes.get_last_error())

            pglobal = kernel32.GlobalLock(hglobal)
            if not pglobal:
                kernel32.GlobalFree(hglobal)
                raise ctypes.WinError(ctypes.get_last_error())

            ctypes.memmove(pglobal, data, len(data))
            kernel32.GlobalUnlock(hglobal)

            if not user32.OpenClipboard(None):
                kernel32.GlobalFree(hglobal)
                raise ctypes.WinError(ctypes.get_last_error())

            try:
                if not user32.EmptyClipboard():
                    kernel32.GlobalFree(hglobal)
                    raise ctypes.WinError(ctypes.get_last_error())
                if not user32.SetClipboardData(CF_DIB, hglobal):
                    kernel32.GlobalFree(hglobal)
                    raise ctypes.WinError(ctypes.get_last_error())
                # Ownership transferred to the clipboard on success.
                hglobal = None
            finally:
                user32.CloseClipboard()
                if hglobal:
                    kernel32.GlobalFree(hglobal)

            orig_bg = self.btn_copy_image.cget("background")
            self.btn_copy_image.config(bg="#44aa44", text="Copied!")
            self.root.after(700, lambda: self.btn_copy_image.config(bg=orig_bg, text="Copy Image (Ctrl+C)"))
        except Exception as e:
            messagebox.showerror("Copy Image Error", str(e))

    def _on_text_zoom(self, event):
        if event.delta > 0:
            self.text_font_size += 1
        else:
            self.text_font_size = max(6, self.text_font_size - 1)
            
        self.text_editor.configure(font=("Consolas", self.text_font_size))
        return "break" # Prevent double processing if any

    def open_external_editor(self):
        """Opens the current text file in the system's default application."""
        if not self.current_txt_path:
            messagebox.showwarning("Open External", "No text file found for this version.")
            return
            
        # Optional: Save current changes before opening externally so the editor sees them
        if self.text_editor.edit_modified():
            self.save_current_text()

        try:
            if sys.platform == "win32":
                os.startfile(self.current_txt_path)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.call(["open", self.current_txt_path])
            else:
                import subprocess
                subprocess.call(["xdg-open", self.current_txt_path])
        except Exception as e:
            messagebox.showerror("Error", f"Could not open file: {e}")

    def _infer_missing_txt_path(self, selected_ver):
        img_path, _ = self.pairs[self.current_index]
        img_basename = os.path.splitext(os.path.basename(img_path))[0]
        filename = f"{img_basename}.txt"

        if selected_ver == "Default":
            return os.path.join(self.working_dir, filename)

        subdir = selected_ver
        suffix_match = re.match(r"^(.*)_(\d+)$", selected_ver)
        if suffix_match:
            subdir = suffix_match.group(1)

        return os.path.join(self.working_dir, subdir, filename)

    def save_current_text(self):
        if not self.pairs:
            return False
            
        # If the editor is not modified, skip saving.
        # This handles unchanged files and avoids redundant writes on navigation.
        if not self.text_editor.edit_modified():
            return True

        _, versions = self.pairs[self.current_index]
        selected_ver = self.current_version_var.get()
        txt_path = versions.get(selected_ver)

        content = self.text_editor.get('1.0', 'end-1c')

        if not txt_path:
            txt_path = self._infer_missing_txt_path(selected_ver)
            versions[selected_ver] = txt_path
            self.current_txt_path = txt_path
            self.lbl_filename.config(text=f"{selected_ver}: {os.path.basename(txt_path)}")

        # Never persist the informational placeholder as file content.
        if content.startswith("[No text file found for version '") and content.endswith("for this image]"):
            content = ""

        # Blank file protection: If the file doesn't exist and the content is empty, don't create it.
        if not os.path.exists(txt_path) and content.strip() == "":
            return True

        try:
            os.makedirs(os.path.dirname(txt_path), exist_ok=True)
            with open(txt_path, 'w', encoding='utf-8') as f: f.write(content)
            self.last_mtime = os.path.getmtime(txt_path) # Update mtime after internal save
            self.current_file_loaded_empty = (content == "")
            self.text_editor.edit_modified(False)
            orig_bg = self.btn_save.cget("background")
            self.btn_save.config(bg="#44aa44", text="Saved!")
            self.root.after(500, lambda: self.btn_save.config(bg=orig_bg, text="Save (Ctrl+S)"))
            return True
        except Exception as e:
            messagebox.showerror("Save Error", f"{e}")
            return False

    def next_pair(self, jump_set=False):
        if not self.save_current_text():
            return
        if self.current_index >= len(self.pairs) - 1:
            messagebox.showinfo("Done", "End of list.")
            return

        if not jump_set:
            self.load_pair(self.current_index + 1)
        else:
            # Jump to the next image that has a different text file version (or none)
            current_ver = self.current_version_var.get()
            current_txt = self.pairs[self.current_index][1].get(current_ver)
            
            new_index = self.current_index + 1
            while new_index < len(self.pairs):
                next_txt = self.pairs[new_index][1].get(current_ver)
                if next_txt != current_txt:
                    break
                new_index += 1
            
            if new_index < len(self.pairs):
                self.load_pair(new_index)
            else:
                messagebox.showinfo("Done", "End of list (no more sets).")

    def prev_pair(self, jump_set=False):
        if not self.save_current_text():
            return
        if self.current_index <= 0: return

        if not jump_set:
            self.load_pair(self.current_index - 1)
        else:
            # Jump to the previous image that has a different text file version (or none)
            current_ver = self.current_version_var.get()
            current_txt = self.pairs[self.current_index][1].get(current_ver)
            
            new_index = self.current_index - 1
            # First, find the start of the current set (if we are in the middle)
            while new_index >= 0:
                if self.pairs[new_index][1].get(current_ver) != current_txt:
                    break
                new_index -= 1
            
            # Now new_index is the last item of the PREVIOUS set, or -1
            # If we want to jump to the START of the previous set:
            if new_index >= 0:
                prev_txt = self.pairs[new_index][1].get(current_ver)
                # Walk back to the start of that set
                while new_index > 0:
                    if self.pairs[new_index - 1][1].get(current_ver) != prev_txt:
                        break
                    new_index -= 1
                self.load_pair(new_index)
            else:
                self.load_pair(0) # Already at the first set

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
            self._update_page_dropdown()
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
