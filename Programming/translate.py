import os
import argparse
import textwrap
from pathlib import Path
import ollama

def split_text(text, chunk_size=1000):
    """Split text into chunks while trying to preserve paragraphs"""
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = []
    current_length = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        para_length = len(para)
        if current_length + para_length > chunk_size and current_chunk:
            chunks.append('\n\n'.join(current_chunk))
            current_chunk = []
            current_length = 0

        current_chunk.append(para)
        current_length += para_length

    if current_chunk:
        chunks.append('\n\n'.join(current_chunk))

    return chunks

def translate_chunk(chunk, target_lang):
    """Translate a text chunk using Ollama"""
    response = ollama.generate(
        model='qwen2.5:14b',
        prompt=f"Translate the following text to {target_lang}. Maintain the original formatting, including markdown if present. Only respond with the translation.\n\n{chunk}"
    )
    return response['response'].strip()

def process_file(file_path, target_lang):
    """Process a single file through translation"""
    print(f"Processing {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    chunks = split_text(text)
    translated = []
    
    for i, chunk in enumerate(chunks, 1):
        print(f"  Translating chunk {i}/{len(chunks)}")
        translated_chunk = translate_chunk(chunk, target_lang)
        translated.append(translated_chunk)
    
    output_dir = Path(file_path).parent / 'translations'
    output_dir.mkdir(exist_ok=True)
    
    base_name = Path(file_path).stem
    output_path = output_dir / f"{base_name}_translated_{target_lang}.txt"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n\n'.join(translated))
    
    print(f"Saved translation to {output_path}\n")

def process_path(path, target_lang):
    """Process either a file or directory"""
    path = Path(path)
    if path.is_file() and path.suffix == '.txt':
        process_file(path, target_lang)
    elif path.is_dir():
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith('.txt'):
                    process_file(Path(root) / file, target_lang)
    else:
        print(f"Skipping non-text file: {path}")

def main():
    parser = argparse.ArgumentParser(description='Text File Translator')
    parser.add_argument('paths', nargs='*', help='Files or directories to process')
    parser.add_argument('-t', '--target', help='Target language code (e.g., es, fr, de)')
    
    args = parser.parse_args()
    paths = args.paths
    target_lang = args.target

    if not target_lang:
        target_lang = input("Enter target language code (e.g., es, fr, de): ").strip()

    if not paths:
        path_input = input("Enter file or directory path: ").strip('"')
        paths = [path_input]

    for path in paths:
        if not Path(path).exists():
            print(f"Path not found: {path}")
            continue
        process_path(path, target_lang)

if __name__ == '__main__':
    main()