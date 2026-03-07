import json
import sys
import os
import tkinter as tk
from tkinter import messagebox, ttk

def process_json(file_path, settings_to_update):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            models = json.load(f)

        for model in models:
            # Ensure 'capabilities' key exists
            if 'capabilities' not in model:
                model['capabilities'] = {}
            
            # Update each setting based on GUI selection
            for setting, value in settings_to_update.items():
                model['capabilities'][setting] = value

        # Save the updated JSON
        output_path = file_path.replace(".json", "_updated.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(models, f, indent=4)
        
        return output_path
    except Exception as e:
        return str(e)

def launch_gui(file_path):
    root = tk.Tk()
    root.title(f"Open WebUI Batch Editor - {os.path.basename(file_path)}")
    root.geometry("400x350")

    label = tk.Label(root, text="Select Capabilities to Enable/Disable Globally:", pady=10)
    label.pack()

    # Define the capability toggles
    capabilities = {
        "citations": tk.BooleanVar(value=False),
        "vision": tk.BooleanVar(value=True),
        "web_search": tk.BooleanVar(value=True),
        "image_generation": tk.BooleanVar(value=True),
        "code_interpreter": tk.BooleanVar(value=True)
    }

    for cap, var in capabilities.items():
        cb = tk.Checkbutton(root, text=cap.replace("_", " ").title(), variable=var)
        cb.pack(anchor='w', padx=50)

    def on_submit():
        selected_settings = {k: v.get() for k, v in capabilities.items()}
        result = process_json(file_path, selected_settings)
        
        if "_updated.json" in result:
            messagebox.showinfo("Success", f"Updated file saved as:\n{result}")
            root.destroy()
        else:
            messagebox.showerror("Error", f"Failed to process: {result}")

    submit_btn = tk.Button(root, text="Apply to All Models", command=on_submit, bg="#4CAF50", fg="white", pady=10)
    submit_btn.pack(pady=20)

    root.mainloop()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python webui_batch_editor.py <path_to_models_json>")
        sys.exit(1)
    
    target_file = os.path.abspath(sys.argv[1])
    if not os.path.exists(target_file):
        print(f"File not found: {target_file}")
        sys.exit(1)

    launch_gui(target_file)