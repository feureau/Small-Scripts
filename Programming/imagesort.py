import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
import shutil

class ImageSorterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Sorter")
        self.root.geometry("800x600")
        
        self.image_files = []
        self.thumbnails = []
        self.selected = {}
        self.current_index = 0
        self.thumbnail_frames = []
        self.zoom_level = 1.0
        self.pan_start = None
        self.image_canvas_img = None
        self.cursor_x = 0
        self.cursor_y = 0

        self.create_widgets()
        self.setup_bindings()
        self.load_images()
        self.root.after(100, self.initial_preview)

    def setup_bindings(self):
        self.root.bind("<Left>", self.previous_image)
        self.root.bind("<Right>", self.next_image)
        self.root.bind("<KeyPress-d>", self.toggle_selection)
        self.root.bind("<KeyPress-s>", self.previous_image)
        self.root.bind("<KeyPress-f>", self.next_image)
        self.root.bind("<KeyPress-z>", self.reset_zoom)

        # Bind scroll events to the filmstrip canvas
        self.canvas.bind("<MouseWheel>", self.on_filmstrip_scroll)
        self.canvas.bind("<Button-4>", self.on_filmstrip_scroll)
        self.canvas.bind("<Button-5>", self.on_filmstrip_scroll)

    def create_widgets(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Preview Canvas
        self.preview_canvas = tk.Canvas(main_frame, bg='#444444', highlightthickness=0)
        self.preview_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.preview_canvas.bind("<ButtonPress-3>", self.start_pan)
        self.preview_canvas.bind("<B3-Motion>", self.do_pan)
        self.preview_canvas.bind("<Motion>", self.store_cursor_position)
        self.preview_canvas.bind("<MouseWheel>", self.on_mousewheel)
        
        # Filmstrip container
        filmstrip_container = ttk.Frame(main_frame)
        filmstrip_container.pack(side=tk.TOP, fill=tk.X, expand=False)
        
        self.scroll_x = ttk.Scrollbar(filmstrip_container, orient=tk.HORIZONTAL)
        self.scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = tk.Canvas(filmstrip_container, height=150, 
                              xscrollcommand=self.scroll_x.set, highlightthickness=0)
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.scroll_x.config(command=self.canvas.xview)

        self.filmstrip_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.filmstrip_frame, anchor=tk.NW)
        
        self.process_btn = ttk.Button(main_frame, text="Process Selected", command=self.process_files)
        self.process_btn.pack(side=tk.RIGHT, padx=10, pady=10)

        self.filmstrip_frame.bind("<Configure>", self.update_scrollregion)
        self.root.bind("<Configure>", self.window_resize)

    def add_scroll_bindings(self, widget):
        widget.bind("<MouseWheel>", self.on_filmstrip_scroll)
        widget.bind("<Button-4>", self.on_filmstrip_scroll)
        widget.bind("<Button-5>", self.on_filmstrip_scroll)

    def store_cursor_position(self, event):
        self.cursor_x = event.x
        self.cursor_y = event.y

    def window_resize(self, event=None):
        if self.current_index < len(self.image_files):
            self.reset_zoom()

    def update_scrollregion(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def load_images(self):
        current_dir = os.getcwd()
        valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
        
        self.image_files = [f for f in os.listdir(current_dir) if f.lower().endswith(valid_extensions)]
        for filename in self.image_files:
            self.create_thumbnail(filename)

    def create_thumbnail(self, filename):
        try:
            img_path = os.path.join(os.getcwd(), filename)
            with Image.open(img_path) as img:
                img.thumbnail((100, 100))
                photo = ImageTk.PhotoImage(img)
                self.thumbnails.append(photo)
                
                frame = ttk.Frame(self.filmstrip_frame)
                frame.pack(side=tk.LEFT, padx=5, pady=5)
                self.thumbnail_frames.append(frame)
                self.add_scroll_bindings(frame)
                
                var = tk.BooleanVar(value=False)
                self.selected[filename] = var
                
                cb = ttk.Checkbutton(frame, variable=var)
                cb.pack(side=tk.TOP)
                self.add_scroll_bindings(cb)
                
                lbl = ttk.Label(frame, image=photo)
                lbl.image = photo
                lbl.bind("<Button-1>", lambda e, f=filename: self.show_preview_by_filename(f))
                self.add_scroll_bindings(lbl)
                lbl.pack(side=tk.TOP)
        except Exception as e:
            print(f"Error loading {filename}: {e}")

    def initial_preview(self):
        if self.image_files:
            self.show_preview(0)

    def show_preview_by_filename(self, filename):
        index = self.image_files.index(filename)
        self.show_preview(index)
        
    def show_preview(self, index):
        if 0 <= index < len(self.image_files):
            self.current_index = index
            self.update_highlight()
            filename = self.image_files[self.current_index]
            self.load_preview_image(filename)
            self.center_filmstrip()
    
    def load_preview_image(self, filename):
        try:
            self.original_image = Image.open(filename)
            self.reset_zoom()
        except Exception as e:
            print(f"Error loading preview for {filename}: {e}")

    def update_highlight(self):
        for i, frame in enumerate(self.thumbnail_frames):
            if i == self.current_index:
                frame.configure(style='Selected.TFrame')
            else:
                frame.configure(style='TFrame')
        self.root.style = ttk.Style()
        self.root.style.configure('Selected.TFrame', background='#5555ff')

    def center_filmstrip(self):
        if self.thumbnail_frames:
            frame = self.thumbnail_frames[self.current_index]
            frame_x = frame.winfo_x()
            frame_width = frame.winfo_width()
            canvas_width = self.canvas.winfo_width()
            
            view_left = self.canvas.xview()[0] * self.filmstrip_frame.winfo_width()
            view_right = self.canvas.xview()[1] * self.filmstrip_frame.winfo_width()
            frame_center = frame_x + frame_width/2
            
            if frame_center < view_left or frame_center > view_right:
                normalized = (frame_center - canvas_width/2) / self.filmstrip_frame.winfo_width()
                self.canvas.xview_moveto(max(0, min(normalized, 1)))

    def next_image(self, event=None):
        if self.current_index < len(self.image_files) - 1:
            self.show_preview(self.current_index + 1)

    def previous_image(self, event=None):
        if self.current_index > 0:
            self.show_preview(self.current_index - 1)

    def toggle_selection(self, event=None):
        if self.image_files:
            current = self.image_files[self.current_index]
            self.selected[current].set(not self.selected[current].get())
            
    def on_mousewheel(self, event):
        delta = event.delta
        if abs(delta) < 100:
            delta = -1 if delta < 0 else 1
        if delta > 0:
            self.zoom(1.1, (event.x, event.y))
        else:
            self.zoom(0.9, (event.x, event.y))

    def on_filmstrip_scroll(self, event):
        """Reverse scroll direction for horizontal scrolling"""
        if event.num == 4:    # Linux scroll up -> scroll left
            delta = 1
        elif event.num == 5:  # Linux scroll down -> scroll right
            delta = -1
        else:                 # Windows/MacOS
            delta = 1 if event.delta < 0 else -1
        
        self.canvas.xview_scroll(delta, "units")

    def start_pan(self, event):
        self.pan_start = (event.x, event.y)

    def do_pan(self, event):
        if self.pan_start and self.image_canvas_img:
            dx = event.x - self.pan_start[0]
            dy = event.y - self.pan_start[1]
            self.preview_canvas.move(self.image_canvas_img, dx, dy)
            self.pan_start = (event.x, event.y)

    def zoom(self, factor, center_point=None):
        if not center_point:
            center_point = (self.cursor_x, self.cursor_y)
            
        self.zoom_level *= factor
        self.update_zoom(center_point)
    
    def reset_zoom(self, event=None):
        self.zoom_level = 1.0
        self.update_zoom(reset=True)
    
    def update_zoom(self, center_point=None, reset=False):
        self.preview_canvas.delete("all")
        if not hasattr(self, 'original_image'):
            return
            
        w = self.preview_canvas.winfo_width()
        h = self.preview_canvas.winfo_height()
        
        if reset:
            img = self.original_image.copy()
            img.thumbnail((w, h))
            scale = 1.0
        else:
            new_size = (int(self.original_image.size[0] * self.zoom_level),
                       int(self.original_image.size[1] * self.zoom_level))
            img = self.original_image.resize(new_size, Image.LANCZOS)
            scale = self.zoom_level

        self.current_preview_image = ImageTk.PhotoImage(img)
        img_id = self.preview_canvas.create_image(
            w//2, h//2, 
            image=self.current_preview_image,
            anchor=tk.CENTER
        )
        
        if center_point and not reset:
            dw = (w//2 - center_point[0]) * (scale - 1)
            dh = (h//2 - center_point[1]) * (scale - 1)
            self.preview_canvas.move(img_id, dw, dh)
            
        self.image_canvas_img = img_id
        self.preview_canvas.config(scrollregion=self.preview_canvas.bbox(tk.ALL))

    def process_files(self):
        current_dir = os.getcwd()
        files_to_process = [f for f in self.image_files if self.selected[f].get()]
        
        for filename in files_to_process:
            ext = os.path.splitext(filename)[1][1:].lower()
            if not ext: continue
            dest_dir = os.path.join(current_dir, ext.upper())
            os.makedirs(dest_dir, exist_ok=True)
            shutil.move(os.path.join(current_dir, filename), os.path.join(dest_dir, filename))
        
        self.refresh_interface()

    def refresh_interface(self):
        for widget in self.filmstrip_frame.winfo_children():
            widget.destroy()
        self.image_files.clear()
        self.thumbnails.clear()
        self.selected.clear()
        self.thumbnail_frames.clear()
        self.preview_canvas.delete("all")
        self.load_images()
        self.root.after(100, self.initial_preview)

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageSorterApp(root)
    root.mainloop()