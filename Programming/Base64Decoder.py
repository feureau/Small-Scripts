import sys
import os
import glob
import base64
import tkinter as tk
from tkinter import filedialog, messagebox


# ---------- CORE ----------
def decode_base64_text(b64_text: str) -> str:
    b64_text = "".join(b64_text.split())
    decoded_bytes = base64.b64decode(b64_text, validate=True)

    try:
        return decoded_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return decoded_bytes.decode("latin-1")


def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def write_output_file(input_path: str, decoded_text: str):
    directory, filename = os.path.split(input_path)
    name, ext = os.path.splitext(filename)

    output_name = f"{name}_decoded{ext}"
    output_path = os.path.join(directory, output_name)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(decoded_text)

    return output_path


# ---------- CLI MODE ----------
def run_cli(args):
    expanded = []
    for arg in args:
        if any(ch in arg for ch in "*?[]"):
            expanded.extend(glob.glob(arg))
        else:
            expanded.append(arg)

    if not expanded:
        print("Error: No matching input.", file=sys.stderr)
        sys.exit(1)

    for item in expanded:
        if os.path.isfile(item):
            try:
                content = read_text_file(item)
                decoded = decode_base64_text(content)
                out_path = write_output_file(item, decoded)
                print(f"Decoded: {item} -> {out_path}")
            except Exception as e:
                print(f"Error processing {item}: {e}", file=sys.stderr)
        else:
            # raw Base64 string
            try:
                decoded = decode_base64_text(item)
                print(decoded)
            except Exception as e:
                print(f"Error decoding input: {e}", file=sys.stderr)


# ---------- GUI MODE ----------
def decode_base64_gui():
    try:
        input_text = input_box.get("1.0", tk.END)
        decoded_text = decode_base64_text(input_text)

        output_box.delete("1.0", tk.END)
        output_box.insert(tk.END, decoded_text)

    except Exception as e:
        messagebox.showerror("Decode Error", str(e))


def load_input():
    file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.*")])
    if file_path:
        input_box.delete("1.0", tk.END)
        input_box.insert(tk.END, read_text_file(file_path))


def save_output():
    file_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text files", "*.*")]
    )
    if file_path:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(output_box.get("1.0", tk.END))


# ---------- ENTRY ----------
if len(sys.argv) > 1:
    run_cli(sys.argv[1:])
    sys.exit(0)


# ---------- GUI ----------
root = tk.Tk()
root.title("Base64 Decoder")
root.geometry("800x500")

tk.Label(root, text="Base64 Input").pack()
input_box = tk.Text(root, height=10)
input_box.pack(fill=tk.BOTH, expand=True, padx=10)

button_frame = tk.Frame(root)
button_frame.pack(pady=5)

tk.Button(button_frame, text="Load Input", command=load_input).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="Decode", command=decode_base64_gui).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="Save Output", command=save_output).pack(side=tk.LEFT, padx=5)

tk.Label(root, text="Decoded Output").pack()
output_box = tk.Text(root, height=10)
output_box.pack(fill=tk.BOTH, expand=True, padx=10)

root.mainloop()
