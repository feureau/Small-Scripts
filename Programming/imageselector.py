import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageOps
import os
import re
import math
import shutil
import io
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from collections import OrderedDict

try:
    import rawpy
    import numpy as np
    RAW_SUPPORT = True
except ImportError:
    RAW_SUPPORT = False

RAW_EXTENSIONS = ('.cr2', '.cr3', '.nef', '.arw', '.dng', '.orf', '.rw2', '.pef', '.raf')
STANDARD_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
VALID_EXTENSIONS = STANDARD_EXTENSIONS + (RAW_EXTENSIONS if RAW_SUPPORT else ())
ALL_PAIR_EXTENSIONS = STANDARD_EXTENSIONS + RAW_EXTENSIONS


def natural_sort_key(text):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r'(\d+)', text)]


def open_image_file(img_path, is_thumbnail=False):
    """
    Opens an image or camera RAW file, applies EXIF orientation transpose,
    and copies pixel data into memory so the underlying OS file handle is closed immediately.
    """
    ext = os.path.splitext(img_path)[1].lower()

    if ext in RAW_EXTENSIONS and RAW_SUPPORT:
        with rawpy.imread(img_path) as raw:
            # First try extracting embedded JPEG/bitmap preview
            try:
                thumb = raw.extract_thumb()
                if thumb.format == rawpy.ThumbFormat.JPEG:
                    with Image.open(io.BytesIO(thumb.data)) as img:
                        img = ImageOps.exif_transpose(img)
                        img.load()
                        return img.copy()
                elif thumb.format == rawpy.ThumbFormat.BITMAP:
                    return Image.fromarray(thumb.data).copy()
            except Exception:
                pass

            # Fallback if no embedded preview exists: half_size=is_thumbnail is much faster
            rgb = raw.postprocess(half_size=is_thumbnail, use_camera_wb=True)
            return Image.fromarray(rgb)
    else:
        with Image.open(img_path) as img:
            img = ImageOps.exif_transpose(img)
            img.load()
            return img.copy()


class ImageSorterApp:
    # Card colors for clear visual states on Windows/Linux/macOS
    COLOR_BG_DEFAULT = "#2b2b2b"
    COLOR_BORDER_DEFAULT = "#3f3f46"
    COLOR_BG_ACTIVE = "#1e3a8a"
    COLOR_BORDER_ACTIVE = "#3b82f6"
    COLOR_BG_SELECTED = "#14532d"
    COLOR_BORDER_SELECTED = "#22c55e"
    COLOR_BG_ACTIVE_SELECTED = "#065f46"
    COLOR_BORDER_ACTIVE_SELECTED = "#38bdf8"

    def __init__(self, root):
        self.root = root
        self.root.title("Image Sorter")
        self.root.geometry("1024x720")
        self.root.minsize(720, 500)

        # Active directory state
        self.current_working_dir = os.getcwd()
        self.last_processed_dir = None
        self.companion_map = {}  # stem_lower -> list of all matching files in directory

        # Image & selection state
        self.image_files = []
        self.thumbnails = {}
        self.selected = {}
        self.current_index = 0
        self.thumbnail_cards = []
        self.original_image = None
        self.current_preview_image = None

        # Viewport zoom & pan state
        self.zoom_level = 1.0
        self.fit_zoom_level = 1.0
        self.is_fit_mode = True
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.pan_start = None
        self.cursor_x = 0
        self.cursor_y = 0
        self._last_canvas_size = (0, 0)

        # Undo stack: list of dicts {"description": str, "moves": [(dest_path, src_path), ...], "selected": set()}
        self.undo_stack = []

        # Thread-safe background loading & LRU caching (max 25 full images in RAM)
        self.cache_lock = threading.Lock()
        self.preview_cache = OrderedDict()
        self.max_cache_size = 25
        self.folder_generation = 0
        self._closing = False
        self.ui_queue = queue.Queue()
        self._poll_job = None
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="preview")
        self.thumb_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="thumb")

        # Placeholder thumbnail for instant asynchronous filmstrip creation
        placeholder_img = Image.new("RGB", (100, 75), color=(55, 55, 60))
        self.placeholder_photo = ImageTk.PhotoImage(placeholder_img)

        self.include_pairs_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready")

        self.create_widgets()
        self.setup_bindings()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.load_images()
        self._poll_ui_queue()
        self.root.after(50, self.initial_preview)

    def _poll_ui_queue(self):
        if self._closing:
            return
        try:
            # Process up to 12 queued UI updates per tick to keep interface responsive
            for _ in range(12):
                msg = self.ui_queue.get_nowait()
                kind = msg[0]
                if kind == "thumb":
                    _, gen, idx, fname, pil_img = msg
                    self._apply_thumbnail(gen, idx, fname, pil_img)
                elif kind == "preview":
                    _, gen, fname = msg
                    self._apply_loaded_image(gen, fname)
        except queue.Empty:
            pass
        if not self._closing:
            self._poll_job = self.root.after(15, self._poll_ui_queue)

    def setup_bindings(self):
        # Navigation
        self.root.bind("<Left>", self.previous_image)
        self.root.bind("<Right>", self.next_image)
        self.root.bind("<KeyPress-s>", self.previous_image)
        self.root.bind("<KeyPress-f>", self.next_image)
        self.root.bind("<Home>", self.first_image)
        self.root.bind("<End>", self.last_image)

        # Selection & rapid culling
        self.root.bind("<KeyPress-d>", self.toggle_selection)
        self.root.bind("<space>", self.toggle_selection)
        self.root.bind("<Shift-Right>", self.toggle_and_advance)
        self.root.bind("<Shift-F>", self.toggle_and_advance)
        self.root.bind("<Shift-f>", self.toggle_and_advance)
        self.root.bind("<Shift-D>", self.toggle_and_advance)
        self.root.bind("<Shift-d>", self.toggle_and_advance)

        # Batch selection & undo
        self.root.bind("<Control-a>", lambda e: self.select_all())
        self.root.bind("<Control-A>", lambda e: self.select_all())
        self.root.bind("<Control-d>", lambda e: self.deselect_all())
        self.root.bind("<Control-D>", lambda e: self.deselect_all())
        self.root.bind("<Control-i>", lambda e: self.invert_selection())
        self.root.bind("<Control-I>", lambda e: self.invert_selection())
        self.root.bind("<Control-z>", lambda e: self.undo_last_action())
        self.root.bind("<Control-Z>", lambda e: self.undo_last_action())

        # Zoom controls
        self.root.bind("<KeyPress-z>", self.reset_zoom)
        self.root.bind("<KeyPress-0>", self.reset_zoom)
        self.root.bind("<KeyPress-1>", self.toggle_1to1_zoom)

        # Reject / delete shortcut
        self.root.bind("<Delete>", self.reject_files)
        self.root.bind("<KeyPress-x>", self.reject_files)

        # Filmstrip horizontal scroll bindings
        self.canvas.bind("<MouseWheel>", self.on_filmstrip_scroll)
        self.canvas.bind("<Button-4>", self.on_filmstrip_scroll)
        self.canvas.bind("<Button-5>", self.on_filmstrip_scroll)

    def create_widgets(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. Main Preview Canvas
        self.preview_canvas = tk.Canvas(main_frame, bg="#222225", highlightthickness=0, cursor="fleur")
        self.preview_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Support both Left-drag and Right-drag for panning, Double-click for 1:1 zoom
        self.preview_canvas.bind("<ButtonPress-1>", self.start_pan)
        self.preview_canvas.bind("<B1-Motion>", self.do_pan)
        self.preview_canvas.bind("<ButtonPress-3>", self.start_pan)
        self.preview_canvas.bind("<B3-Motion>", self.do_pan)
        self.preview_canvas.bind("<Double-Button-1>", self.toggle_1to1_zoom)
        self.preview_canvas.bind("<Motion>", self.store_cursor_position)
        self.preview_canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.preview_canvas.bind("<Button-4>", self.on_mousewheel)
        self.preview_canvas.bind("<Button-5>", self.on_mousewheel)
        self.preview_canvas.bind("<Configure>", self.on_canvas_configure)

        # 2. Filmstrip Container
        filmstrip_container = ttk.Frame(main_frame)
        filmstrip_container.pack(side=tk.TOP, fill=tk.X, expand=False)

        self.scroll_x = ttk.Scrollbar(filmstrip_container, orient=tk.HORIZONTAL)
        self.scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = tk.Canvas(
            filmstrip_container,
            height=155,
            bg="#18181b",
            xscrollcommand=self.scroll_x.set,
            highlightthickness=0
        )
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.scroll_x.config(command=self.canvas.xview)

        self.filmstrip_frame = tk.Frame(self.canvas, bg="#18181b")
        self.canvas.create_window((0, 0), window=self.filmstrip_frame, anchor=tk.NW)
        self.filmstrip_frame.bind("<Configure>", self.update_scrollregion)

        # 3. Controls Toolbar
        toolbar = ttk.Frame(main_frame, padding=(8, 6))
        toolbar.pack(side=tk.TOP, fill=tk.X)

        # Left group: Batch selection & RAW+JPG pairing
        left_group = ttk.Frame(toolbar)
        left_group.pack(side=tk.LEFT)

        ttk.Button(left_group, text="Select All", width=10, command=self.select_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_group, text="Deselect All", width=11, command=self.deselect_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_group, text="Invert", width=8, command=self.invert_selection).pack(side=tk.LEFT, padx=2)

        ttk.Separator(left_group, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=2)

        self.pairs_cb = ttk.Checkbutton(
            left_group,
            text="Include RAW/JPG Pairs",
            variable=self.include_pairs_var,
            command=self.update_status_and_hud
        )
        self.pairs_cb.pack(side=tk.LEFT, padx=4)

        # Right group: Folder & processing actions
        right_group = ttk.Frame(toolbar)
        right_group.pack(side=tk.RIGHT)

        self.process_btn = ttk.Button(right_group, text="Process Selected (0)", command=self.process_files)
        self.process_btn.pack(side=tk.RIGHT, padx=3)

        self.reject_btn = ttk.Button(right_group, text="Reject (Del)", command=self.reject_files)
        self.reject_btn.pack(side=tk.RIGHT, padx=3)

        self.undo_btn = ttk.Button(right_group, text="Undo", command=self.undo_last_action, state=tk.DISABLED)
        self.undo_btn.pack(side=tk.RIGHT, padx=3)

        self.load_processed_btn = ttk.Button(right_group, text="Load Processed", command=self.load_processed_folder)
        self.load_processed_btn.pack(side=tk.RIGHT, padx=3)

        self.open_folder_btn = ttk.Button(right_group, text="Open Folder", command=self.open_folder)
        self.open_folder_btn.pack(side=tk.RIGHT, padx=3)

        # 4. Status Bar
        status_bar = ttk.Label(
            main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(8, 3)
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def add_scroll_bindings(self, widget):
        widget.bind("<MouseWheel>", self.on_filmstrip_scroll)
        widget.bind("<Button-4>", self.on_filmstrip_scroll)
        widget.bind("<Button-5>", self.on_filmstrip_scroll)

    def store_cursor_position(self, event):
        self.cursor_x = event.x
        self.cursor_y = event.y

    def on_canvas_configure(self, event):
        new_size = (event.width, event.height)
        if new_size != self._last_canvas_size and event.width > 10 and event.height > 10:
            old_w, old_h = self._last_canvas_size
            self._last_canvas_size = new_size
            if self.original_image is not None:
                if self.is_fit_mode or old_w <= 10 or old_h <= 10:
                    self.reset_zoom()
                else:
                    # Keep relative pan offset when resizing window while zoomed
                    self.pan_x += (event.width - old_w) / 2.0
                    self.pan_y += (event.height - old_h) / 2.0
                    self._recompute_fit_zoom()
                    self.render_preview()
            else:
                self.render_preview()

    def update_scrollregion(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    # --- IMAGE & THUMBNAIL LOADING ---
    def _scan_directory_companions(self):
        """Index all valid image/RAW files by lowercase stem for fast RAW+JPG pair lookup."""
        self.companion_map.clear()
        try:
            for entry in os.listdir(self.current_working_dir):
                full_p = os.path.join(self.current_working_dir, entry)
                if os.path.isfile(full_p) and entry.lower().endswith(ALL_PAIR_EXTENSIONS):
                    stem = os.path.splitext(entry)[0].lower()
                    self.companion_map.setdefault(stem, []).append(entry)
        except OSError:
            pass

    def get_companion_files(self, filename):
        """Return other files in the current directory sharing the same base filename stem."""
        stem = os.path.splitext(filename)[0].lower()
        matches = self.companion_map.get(stem, [])
        return [f for f in matches if f != filename]

    def load_images(self, file_list=None):
        self._scan_directory_companions()

        if file_list is None:
            try:
                all_files = [
                    f for f in os.listdir(self.current_working_dir)
                    if f.lower().endswith(VALID_EXTENSIONS)
                    and os.path.isfile(os.path.join(self.current_working_dir, f))
                ]
                all_files.sort(key=natural_sort_key)
            except FileNotFoundError:
                all_files = []
        else:
            all_files = sorted(file_list, key=natural_sort_key)

        self.image_files = list(all_files)
        gen = self.folder_generation

        for idx, filename in enumerate(self.image_files):
            self._create_thumbnail_slot(idx, filename)
            self.thumb_executor.submit(self._async_load_thumbnail, gen, idx, filename)

        self.update_scrollregion()
        self.update_status_and_hud()

    def _create_thumbnail_slot(self, index, filename):
        card = tk.Frame(
            self.filmstrip_frame,
            bg=self.COLOR_BG_DEFAULT,
            highlightbackground=self.COLOR_BORDER_DEFAULT,
            highlightcolor=self.COLOR_BORDER_DEFAULT,
            highlightthickness=2,
            padx=4,
            pady=3
        )
        card.pack(side=tk.LEFT, padx=4, pady=5)
        self.add_scroll_bindings(card)

        var = tk.BooleanVar(value=False)
        self.selected[filename] = var

        top_row = tk.Frame(card, bg=self.COLOR_BG_DEFAULT)
        top_row.pack(side=tk.TOP, fill=tk.X)
        self.add_scroll_bindings(top_row)

        cb = tk.Checkbutton(
            top_row,
            variable=var,
            bg=self.COLOR_BG_DEFAULT,
            activebackground=self.COLOR_BG_DEFAULT,
            selectcolor="#111827",
            fg="#ffffff",
            bd=0,
            highlightthickness=0,
            command=lambda i=index: self.on_card_selection_changed(i)
        )
        cb.pack(side=tk.LEFT)
        self.add_scroll_bindings(cb)

        short_name = filename if len(filename) <= 13 else filename[:10] + "..."
        name_lbl = tk.Label(
            top_row,
            text=short_name,
            fg="#d4d4d8",
            bg=self.COLOR_BG_DEFAULT,
            font=("Segoe UI", 8)
        )
        name_lbl.pack(side=tk.LEFT, padx=(2, 0))
        name_lbl.bind("<Button-1>", lambda e, i=index: self.show_preview(i))
        self.add_scroll_bindings(name_lbl)

        img_lbl = tk.Label(
            card,
            image=self.placeholder_photo,
            bg=self.COLOR_BG_DEFAULT,
            bd=0,
            width=100,
            height=85
        )
        img_lbl.image = self.placeholder_photo
        img_lbl.pack(side=tk.TOP, pady=(2, 0))
        img_lbl.bind("<Button-1>", lambda e, i=index: self.show_preview(i))
        img_lbl.bind("<Double-Button-1>", lambda e, i=index: self._select_and_focus_card(i))
        self.add_scroll_bindings(img_lbl)

        card.bind("<Button-1>", lambda e, i=index: self.show_preview(i))

        self.thumbnail_cards.append({
            "frame": card,
            "top_row": top_row,
            "cb": cb,
            "name_lbl": name_lbl,
            "img_lbl": img_lbl,
            "filename": filename
        })

    def _select_and_focus_card(self, index):
        self.show_preview(index)
        self.toggle_selection()

    def _async_load_thumbnail(self, generation, index, filename):
        if self._closing or generation != self.folder_generation:
            return
        try:
            img_path = os.path.join(self.current_working_dir, filename)
            img = open_image_file(img_path, is_thumbnail=True)
            img.thumbnail((100, 85), Image.BILINEAR)
            if not self._closing and generation == self.folder_generation:
                self.ui_queue.put(("thumb", generation, index, filename, img))
        except Exception as e:
            print(f"Error loading thumbnail for {filename}: {e}")

    def _apply_thumbnail(self, generation, index, filename, pil_img):
        if generation != self.folder_generation:
            return
        if index < len(self.thumbnail_cards):
            card_info = self.thumbnail_cards[index]
            if card_info["filename"] == filename and card_info["img_lbl"].winfo_exists():
                photo = ImageTk.PhotoImage(pil_img)
                self.thumbnails[filename] = photo
                card_info["img_lbl"].configure(image=photo)
                card_info["img_lbl"].image = photo

    def initial_preview(self):
        if self.image_files:
            self.show_preview(0)
        else:
            self.original_image = None
            self.render_preview()
            self.update_status_and_hud()

    def show_preview_by_filename(self, filename):
        if filename in self.image_files:
            index = self.image_files.index(filename)
            self.show_preview(index)

    def show_preview(self, index):
        if 0 <= index < len(self.image_files):
            self.current_index = index
            self.update_highlight()
            filename = self.image_files[self.current_index]
            self.load_preview_image(filename)
            self.center_filmstrip()
            self.prefetch_neighbors(index)
            self.update_status_and_hud()

    def _cache_key(self, filename):
        return os.path.normpath(os.path.join(self.current_working_dir, filename))

    def load_preview_image(self, filename):
        key = self._cache_key(filename)
        with self.cache_lock:
            cached_img = self.preview_cache.get(key)
            if cached_img is not None:
                self.preview_cache.move_to_end(key)

        if cached_img is not None:
            self.original_image = cached_img
            self.reset_zoom()
        else:
            gen = self.folder_generation
            self.executor.submit(self._async_load_image, gen, filename, self.current_index)

    def _async_load_image(self, generation, filename, request_index):
        if self._closing or generation != self.folder_generation:
            return
        try:
            key = self._cache_key(filename)
            img = open_image_file(key, is_thumbnail=False)
            if self._closing or generation != self.folder_generation:
                return

            with self.cache_lock:
                self.preview_cache[key] = img
                self.preview_cache.move_to_end(key)
                while len(self.preview_cache) > self.max_cache_size:
                    self.preview_cache.popitem(last=False)

            if not self._closing and generation == self.folder_generation and self.current_index == request_index:
                self.ui_queue.put(("preview", generation, filename))
        except Exception as e:
            print(f"Error loading preview for {filename}: {e}")

    def _apply_loaded_image(self, generation, filename):
        if generation != self.folder_generation:
            return
        if self.image_files and 0 <= self.current_index < len(self.image_files):
            if self.image_files[self.current_index] == filename:
                key = self._cache_key(filename)
                with self.cache_lock:
                    img = self.preview_cache.get(key)
                if img is not None:
                    self.original_image = img
                    self.reset_zoom()
                    self.update_status_and_hud()

    def prefetch_neighbors(self, index):
        gen = self.folder_generation
        neighbors_indices = [index + 1, index - 1, index + 2, index - 2]
        for idx in neighbors_indices:
            if 0 <= idx < len(self.image_files):
                fname = self.image_files[idx]
                key = self._cache_key(fname)
                with self.cache_lock:
                    already_cached = key in self.preview_cache
                if not already_cached:
                    self.executor.submit(self._async_prefetch_image, gen, fname)

    def _async_prefetch_image(self, generation, filename):
        if generation != self.folder_generation:
            return
        try:
            key = self._cache_key(filename)
            with self.cache_lock:
                if key in self.preview_cache:
                    return
            img = open_image_file(key, is_thumbnail=False)
            if generation != self.folder_generation:
                return
            with self.cache_lock:
                self.preview_cache[key] = img
                self.preview_cache.move_to_end(key)
                while len(self.preview_cache) > self.max_cache_size:
                    self.preview_cache.popitem(last=False)
        except Exception:
            pass

    # --- FILMSTRIP VISUAL STATES & NAVIGATION ---
    def _style_card(self, index):
        if not (0 <= index < len(self.thumbnail_cards)):
            return
        card_info = self.thumbnail_cards[index]
        fname = card_info["filename"]
        is_active = (index == self.current_index)
        is_sel = bool(self.selected.get(fname) and self.selected[fname].get())

        if is_active and is_sel:
            bg = self.COLOR_BG_ACTIVE_SELECTED
            border = self.COLOR_BORDER_ACTIVE_SELECTED
        elif is_active:
            bg = self.COLOR_BG_ACTIVE
            border = self.COLOR_BORDER_ACTIVE
        elif is_sel:
            bg = self.COLOR_BG_SELECTED
            border = self.COLOR_BORDER_SELECTED
        else:
            bg = self.COLOR_BG_DEFAULT
            border = self.COLOR_BORDER_DEFAULT

        card_info["frame"].configure(bg=bg, highlightbackground=border, highlightcolor=border)
        card_info["top_row"].configure(bg=bg)
        card_info["cb"].configure(bg=bg, activebackground=bg)
        card_info["name_lbl"].configure(bg=bg)
        card_info["img_lbl"].configure(bg=bg)

    def update_highlight(self):
        for i in range(len(self.thumbnail_cards)):
            self._style_card(i)

    def on_card_selection_changed(self, index):
        self._style_card(index)
        self.update_status_and_hud()
        if index == self.current_index:
            self.render_preview()

    def center_filmstrip(self):
        if not self.thumbnail_cards or self.current_index >= len(self.thumbnail_cards):
            return
        self.root.update_idletasks()
        frame = self.thumbnail_cards[self.current_index]["frame"]
        total_width = self.filmstrip_frame.winfo_width()
        if total_width <= 1:
            return
        frame_x = frame.winfo_x()
        frame_width = frame.winfo_width()
        canvas_width = self.canvas.winfo_width()

        view_left = self.canvas.xview()[0] * total_width
        view_right = self.canvas.xview()[1] * total_width
        frame_center = frame_x + frame_width / 2.0

        if frame_center < view_left + frame_width or frame_center > view_right - frame_width:
            normalized = (frame_center - canvas_width / 2.0) / total_width
            self.canvas.xview_moveto(max(0.0, min(normalized, 1.0)))

    def next_image(self, event=None):
        if self.current_index < len(self.image_files) - 1:
            self.show_preview(self.current_index + 1)

    def previous_image(self, event=None):
        if self.current_index > 0:
            self.show_preview(self.current_index - 1)

    def first_image(self, event=None):
        if self.image_files:
            self.show_preview(0)

    def last_image(self, event=None):
        if self.image_files:
            self.show_preview(len(self.image_files) - 1)

    def toggle_selection(self, event=None):
        if self.image_files and 0 <= self.current_index < len(self.image_files):
            current = self.image_files[self.current_index]
            self.selected[current].set(not self.selected[current].get())
            self.on_card_selection_changed(self.current_index)

    def toggle_and_advance(self, event=None):
        self.toggle_selection()
        self.next_image()

    def select_all(self):
        for fname in self.image_files:
            if fname in self.selected:
                self.selected[fname].set(True)
        self.update_highlight()
        self.update_status_and_hud()
        self.render_preview()

    def deselect_all(self):
        for fname in self.image_files:
            if fname in self.selected:
                self.selected[fname].set(False)
        self.update_highlight()
        self.update_status_and_hud()
        self.render_preview()

    def invert_selection(self):
        for fname in self.image_files:
            if fname in self.selected:
                self.selected[fname].set(not self.selected[fname].get())
        self.update_highlight()
        self.update_status_and_hud()
        self.render_preview()

    # --- VIEWPORT-CROPPED SMOOTH ZOOM & PAN ENGINE ---
    def _recompute_fit_zoom(self):
        if self.original_image is None:
            self.fit_zoom_level = 1.0
            return
        w = max(1, self.preview_canvas.winfo_width())
        h = max(1, self.preview_canvas.winfo_height())
        img_w, img_h = self.original_image.size
        if img_w <= 0 or img_h <= 0:
            self.fit_zoom_level = 1.0
            return
        self.fit_zoom_level = min(w / img_w, h / img_h)

    def reset_zoom(self, event=None):
        if self.original_image is None:
            self.render_preview()
            return
        w = max(1, self.preview_canvas.winfo_width())
        h = max(1, self.preview_canvas.winfo_height())
        self._recompute_fit_zoom()
        self.zoom_level = self.fit_zoom_level
        self.is_fit_mode = True
        self.pan_x = w / 2.0
        self.pan_y = h / 2.0
        self.render_preview()
        self.update_status_and_hud()

    def toggle_1to1_zoom(self, event=None):
        if self.original_image is None:
            return
        cx = event.x if event and hasattr(event, "x") else self.cursor_x
        cy = event.y if event and hasattr(event, "y") else self.cursor_y

        if not self.is_fit_mode and abs(self.zoom_level - 1.0) < 0.02:
            self.reset_zoom()
        else:
            old_zoom = self.zoom_level if self.zoom_level > 0 else 1.0
            new_zoom = 1.0
            self.pan_x = cx - (cx - self.pan_x) * (new_zoom / old_zoom)
            self.pan_y = cy - (cy - self.pan_y) * (new_zoom / old_zoom)
            self.zoom_level = new_zoom
            self.is_fit_mode = False
            self.render_preview()
            self.update_status_and_hud()

    def on_mousewheel(self, event):
        if self.original_image is None:
            return
        if getattr(event, "num", None) == 4:
            factor = 1.15
        elif getattr(event, "num", None) == 5:
            factor = 1.0 / 1.15
        else:
            factor = 1.15 if event.delta > 0 else (1.0 / 1.15)
        self.zoom(factor, (event.x, event.y))

    def zoom(self, factor, center_point=None):
        if self.original_image is None:
            return
        if not center_point:
            center_point = (self.cursor_x, self.cursor_y)

        cx, cy = center_point
        self._recompute_fit_zoom()
        old_zoom = self.zoom_level if self.zoom_level > 0 else self.fit_zoom_level
        min_zoom = min(self.fit_zoom_level * 0.5, 0.05)
        max_zoom = 16.0
        new_zoom = max(min_zoom, min(max_zoom, old_zoom * factor))

        if abs(new_zoom - old_zoom) < 1e-6:
            return

        # Anchor the exact image coordinate currently under the cursor
        self.pan_x = cx - (cx - self.pan_x) * (new_zoom / old_zoom)
        self.pan_y = cy - (cy - self.pan_y) * (new_zoom / old_zoom)
        self.zoom_level = new_zoom
        self.is_fit_mode = False

        self.render_preview()
        self.update_status_and_hud()

    def start_pan(self, event):
        self.pan_start = (event.x, event.y)

    def do_pan(self, event):
        if self.pan_start and self.original_image is not None:
            dx = event.x - self.pan_start[0]
            dy = event.y - self.pan_start[1]
            self.pan_x += dx
            self.pan_y += dy
            self.pan_start = (event.x, event.y)
            self.is_fit_mode = False
            self.render_preview()

    def render_preview(self):
        self.preview_canvas.delete("all")
        w = self.preview_canvas.winfo_width()
        h = self.preview_canvas.winfo_height()
        if w <= 2 or h <= 2:
            return

        if self.original_image is None or not self.image_files:
            msg = "No images found in current folder" if not self.image_files else "Loading preview..."
            self.preview_canvas.create_text(
                w // 2, h // 2,
                text=msg,
                fill="#a1a1aa",
                font=("Segoe UI", 13)
            )
            return

        img_w, img_h = self.original_image.size
        zoom = max(1e-4, self.zoom_level)
        disp_w = img_w * zoom
        disp_h = img_h * zoom

        # Top-left corner of the full virtual zoomed image in canvas coordinates
        img_left = self.pan_x - disp_w / 2.0
        img_top = self.pan_y - disp_h / 2.0

        # Intersection of visible canvas [0, w] x [0, h] with the virtual image
        vis_x0 = max(0.0, img_left)
        vis_y0 = max(0.0, img_top)
        vis_x1 = min(float(w), img_left + disp_w)
        vis_y1 = min(float(h), img_top + disp_h)

        if vis_x1 > vis_x0 and vis_y1 > vis_y0:
            # Map visible region back into source image pixel coordinates
            src_x0 = max(0, int(math.floor((vis_x0 - img_left) / zoom)))
            src_y0 = max(0, int(math.floor((vis_y0 - img_top) / zoom)))
            src_x1 = min(img_w, int(math.ceil((vis_x1 - img_left) / zoom)))
            src_y1 = min(img_h, int(math.ceil((vis_y1 - img_top) / zoom)))

            if src_x1 > src_x0 and src_y1 > src_y0:
                cropped = self.original_image.crop((src_x0, src_y0, src_x1, src_y1))
                target_w = max(1, int(round((src_x1 - src_x0) * zoom)))
                target_h = max(1, int(round((src_y1 - src_y0) * zoom)))

                if zoom >= 2.5:
                    resample_filter = Image.NEAREST
                elif self.is_fit_mode:
                    resample_filter = Image.LANCZOS
                else:
                    resample_filter = Image.BILINEAR

                resized = cropped.resize((target_w, target_h), resample_filter)
                self.current_preview_image = ImageTk.PhotoImage(resized)

                draw_x = int(round(img_left + src_x0 * zoom))
                draw_y = int(round(img_top + src_y0 * zoom))
                self.preview_canvas.create_image(
                    draw_x,
                    draw_y,
                    image=self.current_preview_image,
                    anchor=tk.NW
                )

        self._draw_canvas_hud(w, h)

    def _draw_canvas_hud(self, canvas_w, canvas_h):
        if not self.image_files or not (0 <= self.current_index < len(self.image_files)):
            return

        filename = self.image_files[self.current_index]
        img_w, img_h = self.original_image.size if self.original_image else (0, 0)
        zoom_pct = int(round(self.zoom_level * 100))
        zoom_mode = f"Fit ({zoom_pct}%)" if self.is_fit_mode else f"{zoom_pct}%"

        companions = self.get_companion_files(filename)
        pair_tag = ""
        if companions:
            exts = sorted({os.path.splitext(c)[1].upper().lstrip(".") for c in companions})
            pair_tag = f"  [+{','.join(exts)}]"

        hud_text = (
            f"[{self.current_index + 1} / {len(self.image_files)}]  "
            f"{filename}{pair_tag}   |   {img_w}×{img_h}   |   Zoom: {zoom_mode}"
        )

        # Draw semi-dark pill background in top-left corner
        text_id = self.preview_canvas.create_text(
            18, 16,
            text=hud_text,
            anchor=tk.NW,
            fill="#f4f4f5",
            font=("Segoe UI", 10, "bold")
        )
        bbox = self.preview_canvas.bbox(text_id)
        if bbox:
            bg_id = self.preview_canvas.create_rectangle(
                bbox[0] - 8, bbox[1] - 4, bbox[2] + 8, bbox[3] + 4,
                fill="#18181b",
                outline="#3f3f46",
                width=1
            )
            self.preview_canvas.tag_raise(text_id, bg_id)

        # Draw SELECTED badge in top-right corner when current image is checked
        is_sel = bool(self.selected.get(filename) and self.selected[filename].get())
        if is_sel:
            sel_text_id = self.preview_canvas.create_text(
                canvas_w - 18, 16,
                text="✓ SELECTED",
                anchor=tk.NE,
                fill="#ffffff",
                font=("Segoe UI", 10, "bold")
            )
            s_bbox = self.preview_canvas.bbox(sel_text_id)
            if s_bbox:
                s_bg_id = self.preview_canvas.create_rectangle(
                    s_bbox[0] - 10, s_bbox[1] - 4, s_bbox[2] + 10, s_bbox[3] + 4,
                    fill="#16a34a",
                    outline="#4ade80",
                    width=1
                )
                self.preview_canvas.tag_raise(sel_text_id, s_bg_id)

    def update_status_and_hud(self):
        total = len(self.image_files)
        selected_files = [f for f in self.image_files if self.selected.get(f) and self.selected[f].get()]
        sel_count = len(selected_files)

        pair_extra = 0
        if self.include_pairs_var.get() and sel_count > 0:
            all_to_move = set(selected_files)
            for f in selected_files:
                all_to_move.update(self.get_companion_files(f))
            pair_extra = len(all_to_move) - sel_count

        if pair_extra > 0:
            self.process_btn.configure(text=f"Process Selected ({sel_count} + {pair_extra} pair)")
        else:
            self.process_btn.configure(text=f"Process Selected ({sel_count})")

        if self.undo_stack:
            self.undo_btn.configure(state=tk.NORMAL, text=f"Undo ({len(self.undo_stack)})")
        else:
            self.undo_btn.configure(state=tk.DISABLED, text="Undo")

        shortcuts_hint = "Keys: [←/→ or S/F] Nav | [D/Space] Select | [Shift+F] Select & Next | [Z/0] Fit | [1/DblClick] 100% | [Del/X] Reject | [Ctrl+Z] Undo"
        self.status_var.set(
            f"Folder: {self.current_working_dir}   |   Images: {total}   |   Selected: {sel_count}   |   {shortcuts_hint}"
        )

    def on_filmstrip_scroll(self, event):
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = 1 if event.delta < 0 else -1
        self.canvas.xview_scroll(delta, "units")

    # --- FILE PROCESSING, COMPANION PAIRING, REJECT & UNDO ---
    def _evict_from_cache(self, filenames):
        with self.cache_lock:
            for fname in filenames:
                key = self._cache_key(fname)
                self.preview_cache.pop(key, None)

    def _expand_with_companions(self, base_files):
        """Expand a list of filenames with any matching RAW/JPG companion files if enabled."""
        if not self.include_pairs_var.get():
            return list(dict.fromkeys(base_files))
        expanded = []
        seen = set()
        for fname in base_files:
            if fname not in seen:
                expanded.append(fname)
                seen.add(fname)
            for comp in self.get_companion_files(fname):
                if comp not in seen:
                    expanded.append(comp)
                    seen.add(comp)
        return expanded

    def process_files(self):
        selected_files = [f for f in self.image_files if self.selected.get(f) and self.selected[f].get()]
        if not selected_files:
            return

        files_to_move = self._expand_with_companions(selected_files)
        self._evict_from_cache(files_to_move)
        self.original_image = None

        moved_records = []
        created_dirs = set()

        for filename in files_to_move:
            ext = os.path.splitext(filename)[1][1:].lower()
            if not ext:
                continue

            dest_dir = os.path.join(self.current_working_dir, ext.upper())
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)
                created_dirs.add(dest_dir)

            source_path = os.path.join(self.current_working_dir, filename)
            dest_path = os.path.join(dest_dir, filename)
            if not os.path.exists(source_path):
                continue

            try:
                shutil.move(source_path, dest_path)
                moved_records.append((dest_path, source_path))
                self.last_processed_dir = dest_dir
            except Exception as e:
                print(f"Error processing {filename}: {e}")

        if moved_records:
            self.undo_stack.append({
                "description": f"Processed {len(moved_records)} file(s)",
                "moves": moved_records,
                "created_dirs": list(created_dirs),
                "selected": set(selected_files),
                "working_dir": self.current_working_dir
            })

        self.refresh_interface(preserve_index=self.current_index)

    def reject_files(self, event=None):
        if not self.image_files:
            return

        selected_files = [f for f in self.image_files if self.selected.get(f) and self.selected[f].get()]
        target_files = selected_files if selected_files else [self.image_files[self.current_index]]
        files_to_move = self._expand_with_companions(target_files)

        self._evict_from_cache(files_to_move)
        self.original_image = None

        reject_dir = os.path.join(self.current_working_dir, "_Rejected")
        created_dirs = set()
        if not os.path.exists(reject_dir):
            os.makedirs(reject_dir, exist_ok=True)
            created_dirs.add(reject_dir)

        moved_records = []
        for filename in files_to_move:
            source_path = os.path.join(self.current_working_dir, filename)
            dest_path = os.path.join(reject_dir, filename)
            if not os.path.exists(source_path):
                continue
            try:
                shutil.move(source_path, dest_path)
                moved_records.append((dest_path, source_path))
            except Exception as e:
                print(f"Error rejecting {filename}: {e}")

        if moved_records:
            self.undo_stack.append({
                "description": f"Rejected {len(moved_records)} file(s)",
                "moves": moved_records,
                "created_dirs": list(created_dirs),
                "selected": set(selected_files),
                "working_dir": self.current_working_dir
            })

        self.refresh_interface(preserve_index=self.current_index)

    def undo_last_action(self):
        if not self.undo_stack:
            return

        record = self.undo_stack.pop()
        restored_files = []
        for dest_path, source_path in reversed(record["moves"]):
            if os.path.exists(dest_path):
                try:
                    os.makedirs(os.path.dirname(source_path), exist_ok=True)
                    shutil.move(dest_path, source_path)
                    restored_files.append(os.path.basename(source_path))
                except Exception as e:
                    print(f"Error undoing move for {dest_path}: {e}")

        # Clean up any directories created by the action if they are now empty
        for d in record.get("created_dirs", []):
            try:
                if os.path.isdir(d) and not os.listdir(d):
                    os.rmdir(d)
            except OSError:
                pass

        if self.current_working_dir != record["working_dir"] and os.path.isdir(record["working_dir"]):
            self.current_working_dir = record["working_dir"]

        focus_file = restored_files[-1] if restored_files else None
        self.refresh_interface(
            restore_selection=record.get("selected", set()),
            focus_filename=focus_file
        )

    def load_processed_folder(self):
        if self.last_processed_dir and os.path.exists(self.last_processed_dir):
            self.current_working_dir = self.last_processed_dir
            self.refresh_interface()
        else:
            messagebox.showinfo("Load Processed", "No processed folder found to load yet.")

    def open_folder(self):
        folder = filedialog.askdirectory(initialdir=self.current_working_dir, title="Select Image Folder")
        if folder:
            self.current_working_dir = folder
            self.last_processed_dir = None
            self.refresh_interface()

    def refresh_interface(self, file_list=None, preserve_index=0, restore_selection=None, focus_filename=None):
        self.folder_generation += 1

        for widget in self.filmstrip_frame.winfo_children():
            widget.destroy()

        self.image_files.clear()
        self.thumbnails.clear()
        self.selected.clear()
        self.thumbnail_cards.clear()
        with self.cache_lock:
            self.preview_cache.clear()
        self.original_image = None
        self.current_preview_image = None
        self.preview_canvas.delete("all")

        self.load_images(file_list)

        if restore_selection:
            for fname in restore_selection:
                if fname in self.selected:
                    self.selected[fname].set(True)

        if self.image_files:
            if focus_filename and focus_filename in self.image_files:
                target_idx = self.image_files.index(focus_filename)
            else:
                target_idx = max(0, min(preserve_index, len(self.image_files) - 1))
            self.current_index = target_idx
            self.root.after(20, lambda idx=target_idx: self.show_preview(idx))
        else:
            self.current_index = 0
            self.root.after(20, self.initial_preview)

    def on_close(self):
        import gc
        self._closing = True
        self.folder_generation += 1
        if self._poll_job is not None:
            try:
                self.root.after_cancel(self._poll_job)
            except Exception:
                pass
            self._poll_job = None

        self.executor.shutdown(wait=True, cancel_futures=True)
        self.thumb_executor.shutdown(wait=True, cancel_futures=True)

        while not self.ui_queue.empty():
            try:
                self.ui_queue.get_nowait()
            except queue.Empty:
                break

        self.thumbnails.clear()
        self.selected.clear()
        self.thumbnail_cards.clear()
        self.current_preview_image = None
        self.placeholder_photo = None
        self.include_pairs_var = None
        self.status_var = None
        gc.collect()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageSorterApp(root)
    root.mainloop()
