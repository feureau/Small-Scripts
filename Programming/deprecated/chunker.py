import os
import requests
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import stanfordnlp
import tiktoken
from unstructured.partition.auto import partition
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("document_processor.log"),
        logging.StreamHandler()
    ]
)

class DocumentProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Document Processor")
        self.root.geometry("500x400")
        self.root.resizable(False, False)

        # Initialize variables
        self.file_paths = []
        self.selected_model = tk.StringVar(value="mistral")
        self.max_tokens = tk.IntVar(value=4000)

        # Initialize Stanford NLP
        logging.info("Initializing Stanford NLP...")
        try:
            stanfordnlp.download('en', resource_dir='models', quiet=True)
            self.nlp = stanfordnlp.Pipeline(lang='en', models_dir='models')
            logging.info("Stanford NLP initialized successfully.")
        except Exception as e:
            logging.error(f"Error initializing Stanford NLP: {e}")
            messagebox.showerror("Initialization Error", f"Failed to initialize Stanford NLP: {e}")
            self.root.destroy()

        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            logging.info("Tokenizer initialized successfully.")
        except Exception as e:
            logging.error(f"Error initializing tokenizer: {e}")
            messagebox.showerror("Initialization Error", f"Failed to initialize tokenizer: {e}")
            self.root.destroy()

        # OLLama API Endpoint
        self.OLLAMA_URL = "http://localhost:11434/api/generate"  # Modify if different

        # Setup GUI
        self.setup_gui()

    def setup_gui(self):
        # Title Label
        tk.Label(self.root, text="Document Processor", font=("Helvetica", 16, "bold")).pack(pady=10)

        # File selection button
        tk.Button(self.root, text="Select Files", command=self.select_files, width=20).pack(pady=5)
        self.file_label = tk.Label(self.root, text="No files selected", wraplength=450)
        self.file_label.pack(pady=5)

        # Model selection dropdown
        models = ["mistral", "llama3", "gemma", "custom_model"]
        tk.Label(self.root, text="Select OLLama Model:", font=("Helvetica", 12)).pack(pady=5)
        model_menu = tk.OptionMenu(self.root, self.selected_model, *models)
        model_menu.config(width=20)
        model_menu.pack(pady=5)

        # Token limit entry
        tk.Label(self.root, text="Max Tokens per Chunk:", font=("Helvetica", 12)).pack(pady=5)
        self.token_entry = tk.Entry(self.root, textvariable=self.max_tokens, width=22)
        self.token_entry.pack(pady=5)

        # Progress bar
        self.progress = ttk.Progressbar(self.root, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=10)

        # Process button
        tk.Button(self.root, text="Process", command=self.start_processing, width=20, bg="green", fg="white").pack(pady=10)

    def select_files(self):
        """Open file dialog to choose multiple documents."""
        self.file_paths = filedialog.askopenfilenames(
            title="Select Files",
            filetypes=[("All Supported Formats", "*.txt *.md *.docx *.odt *.pdf"), ("All Files", "*.*")]
        )
        if self.file_paths:
            display_text = f"{len(self.file_paths)} file(s) selected."
            self.file_label.config(text=display_text)
            logging.info(f"{len(self.file_paths)} file(s) selected for processing.")
        else:
            self.file_label.config(text="No files selected.")
            logging.info("No files selected.")

    def estimate_token_count(self, text):
        """Estimate token count using OpenAI tokenizer."""
        return len(self.tokenizer.encode(text))

    def extract_text(self, file_path):
        """Extract text from any document format using unstructured."""
        try:
            elements = partition(file_path)
            extracted_text = "\n".join([elem.text for elem in elements if elem.text])
            logging.info(f"Extracted text from {file_path}")
            return extracted_text
        except Exception as e:
            logging.error(f"Error extracting text from {file_path}: {e}")
            return ""

    def chunk_text(self, text, max_tokens):
        """Split text into chunks of max_tokens while keeping sentence integrity."""
        doc = self.nlp(text)
        sentences = [sentence.text for sentence in doc.sentences]
        
        chunks = []
        current_chunk = []
        current_token_count = 0

        for sentence in sentences:
            sentence_tokens = self.estimate_token_count(sentence)
            
            if sentence_tokens > max_tokens:
                logging.warning(f"A sentence exceeds the max token limit ({max_tokens}). It will be skipped.")
                continue  # Optionally, implement further splitting of long sentences
            
            if current_token_count + sentence_tokens > max_tokens:
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_token_count = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_token_count += sentence_tokens

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        logging.info(f"Text split into {len(chunks)} chunks.")
        return chunks

    def send_to_ollama(self, text, model):
        """Send text chunk to OLLama for processing."""
        payload = {"model": model, "prompt": text, "stream": False}
        try:
            response = requests.post(self.OLLAMA_URL, json=payload, timeout=120)
            response.raise_for_status()
            logging.info("Chunk processed successfully.")
            return response.json().get("response", "")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error communicating with OLLama: {e}")
            return ""

    def process_file(self, file_path, model, max_tokens):
        """Extract, chunk, and process a single document with OLLama."""
        logging.info(f"Processing file: {file_path}")
        text = self.extract_text(file_path)
        if not text:
            logging.error(f"No text extracted from {file_path}. Skipping.")
            return ""
        
        chunks = self.chunk_text(text, max_tokens)
        if not chunks:
            logging.error(f"No chunks created from {file_path}. Skipping.")
            return ""
        
        results = []
        for i, chunk in enumerate(chunks, start=1):
            logging.info(f"Processing Chunk {i}/{len(chunks)} (Tokens: {self.estimate_token_count(chunk)})")
            response = self.send_to_ollama(chunk, model)
            if response:
                results.append(response)
            self.progress['value'] += 1
            self.root.update_idletasks()
        
        final_output = "\n".join(results)
        logging.info(f"Finished processing {file_path}")
        return final_output

    def process_all_files(self):
        """Process all selected files."""
        if not self.file_paths:
            logging.error("No files selected. Exiting...")
            messagebox.showerror("Error", "No files selected. Please select files to process.")
            return

        model = self.selected_model.get()
        try:
            max_tokens = int(self.token_entry.get())
            if max_tokens <= 0:
                raise ValueError
        except ValueError:
            max_tokens = 4000
            self.token_entry.delete(0, tk.END)
            self.token_entry.insert(0, "4000")
            logging.warning("Invalid token limit entered. Reset to default (4000).")
            messagebox.showwarning("Warning", "Invalid token limit entered. Reset to default (4000).")

        all_results = []
        total_chunks = sum([len(self.chunk_text(self.extract_text(fp), max_tokens)) for fp in self.file_paths])
        self.progress['maximum'] = total_chunks
        self.progress['value'] = 0

        for file_path in self.file_paths:
            result = self.process_file(file_path, model, max_tokens)
            if result:
                all_results.append(result)

        final_output = "\n".join(all_results)
        logging.info("All files processed.")
        messagebox.showinfo("Success", "All files have been processed successfully.")
        self.save_output(final_output)

    def save_output(self, final_output):
        """Save the final output to a file."""
        if not final_output.strip():
            logging.warning("No output to save.")
            messagebox.showwarning("No Output", "There is no output to save.")
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if save_path:
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(final_output)
                logging.info(f"Output saved to {save_path}")
                messagebox.showinfo("Saved", f"Output saved to {save_path}")
            except Exception as e:
                logging.error(f"Error saving output: {e}")
                messagebox.showerror("Error", f"Failed to save output: {e}")

    def start_processing(self):
        """Start processing in a separate thread to keep GUI responsive."""
        processing_thread = threading.Thread(target=self.process_all_files)
        processing_thread.start()

if __name__ == "__main__":
    root = tk.Tk()
    app = DocumentProcessorApp(root)
    root.mainloop()
