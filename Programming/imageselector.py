import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import os
import shutil

class ImageSorterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Sorter")
        self.root.geometry("800x600")
        
        # Track the active directory instead of hardcoding to os.getcwd()
        self.current_working_dir = os.getcwd()
        self.last_processed_dir = None
        
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
        
        # Buttons
        self.process_btn = ttk.Button(main_frame, text="Process Selected", command=self.process_files)
        self.process_btn.pack(side=tk.RIGHT, padx=10, pady=10)

        self.load_processed_btn = ttk.Button(main_frame, text="Load Processed", command=self.load_processed_folder)
        self.load_processed_btn.pack(side=tk.RIGHT, padx=10, pady=10)
        
        self.open_folder_btn = ttk.Button(main_frame, text="Open Folder", command=self.open_folder)
        self.open_folder_btn.pack(side=tk.RIGHT, padx=10, pady=10)

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
        if self.image_files:
            self.reset_zoom()

    def update_scrollregion(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def load_images(self, file_list=None):
        # Look in the active working directory, not universally os.getcwd()
        if file_list is None:
            valid_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')
            try:
                all_files = [f for f in os.listdir(self.current_working_dir) if f.lower().endswith(valid_extensions)]
            except FileNotFoundError:
                all_files = []
        else:
            all_files = file_list
            
        self.image_files = []
        for filename in all_files:
            if self.create_thumbnail(filename):
                self.image_files.append(filename)

    def create_thumbnail(self, filename):
        try:
            # Join the current directory path with the file name
            img_path = os.path.join(self.current_working_dir, filename)
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
            return True
        except Exception as e:
            print(f"Error loading {filename}: {e}")
            return False

    def initial_preview(self):
        if self.image_files:
            self.show_preview(0)

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

    def load_preview_image(self, filename):
        try:
            # Need to specify full path so it doesn't just look where script was executed
            img_path = os.path.join(self.current_working_dir, filename)
            self.original_image = Image.open(img_path)
            self.reset_zoom()
        except Exception as e:
            print(f"Error loading preview for {filename}: {e}")
            if self.image_files:
                if self.current_index < len(self.image_files) - 1:
                    self.show_preview(self.current_index + 1)
                elif self.current_index > 0:
                    self.show_preview(self.current_index - 1)
                else:
                    self.preview_canvas.delete("all")

    def update_highlight(self):
        style = ttk.Style()
        style.configure('Selected.TFrame', background='#5555ff')
        for i, frame in enumerate(self.thumbnail_frames):
            if i == self.current_index:
                frame.configure(style='Selected.TFrame')
            else:
                frame.configure(style='TFrame')

    def center_filmstrip(self):
        if not self.thumbnail_frames or self.current_index >= len(self.thumbnail_frames):
            return
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
        if event.num == 4:    
            delta = 1
        elif event.num == 5:  
            delta = -1
        else:                 
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

    # --- NEW FOLDER LOADING LOGIC ---
    def process_files(self):
        files_to_process = [f for f in self.image_files if self.selected.get(f) and self.selected[f].get()]
        
        for filename in files_to_process:
            ext = os.path.splitext(filename)[1][1:].lower()
            if not ext: 
                continue
            
            # Destination directory is built inside the current working directory
            dest_dir = os.path.join(self.current_working_dir, ext.upper())
            os.makedirs(dest_dir, exist_ok=True)
            
            try:
                source_path = os.path.join(self.current_working_dir, filename)
                dest_path = os.path.join(dest_dir, filename)
                shutil.move(source_path, dest_path)
                
                # Remember where we just moved the files
                self.last_processed_dir = dest_dir 
            except Exception as e:
                print(f"Error processing {filename}: {e}")
        
        # Reload remaining files in the current folder
        remaining_files = [f for f in self.image_files if os.path.exists(os.path.join(self.current_working_dir, f))]
        self.refresh_interface(file_list=remaining_files)

    def load_processed_folder(self):
        # Switches the app's folder to the newly created directory (e.g. JPG)
        if self.last_processed_dir and os.path.exists(self.last_processed_dir):
            self.current_working_dir = self.last_processed_dir
            self.refresh_interface()
        else:
            print("No processed folder found to load.")

    def open_folder(self):
        # Allow the user to manually pick a folder 
        folder = filedialog.askdirectory(initialdir=self.current_working_dir, title="Select Image Folder")
        if folder:
            self.current_working_dir = folder
            self.last_processed_dir = None
            self.refresh_interface()

    def refresh_interface(self, file_list=None):
        for widget in self.filmstrip_frame.winfo_children():
            widget.destroy()
        self.image_files.clear()
        self.thumbnails.clear()
        self.selected.clear()
        self.thumbnail_frames.clear()
        self.preview_canvas.delete("all")
        
        self.current_index = 0
        self.load_images(file_list)
        self.root.after(100, self.initial_preview)

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageSorterApp(root)
    root.mainloop()