#!/usr/bin/env python3
import os
import sys
import argparse
import glob
import spacy

# Default maximum tokens per chunk (adjust as needed to stay below your LLM limit)
DEFAULT_MAX_TOKENS = 3000

def load_text(file_path):
    """Read the file content using UTF-8 encoding."""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

def chunk_text_with_spacy(text, max_tokens):
    """
    Use spaCy to split the text into sentences and then group them into chunks.
    Each chunk will not exceed max_tokens.
    """
    nlp = spacy.load("en_core_web_sm")
    nlp.max_length = 5000000  # Increase to 5 million characters (adjust as needed)
    doc = nlp(text)
    
    chunks = []
    current_chunk = []
    current_token_count = 0
    
    # Iterate over sentences from spaCy
    for sent in doc.sents:
        # Use spaCy's token count for the sentence (including punctuation)
        sent_token_count = len(sent)
        # If adding this sentence would exceed the limit and we already have something in the chunk, finalize it.
        if current_token_count + sent_token_count > max_tokens and current_chunk:
            chunks.append(" ".join(current_chunk))
            current_chunk = [sent.text.strip()]
            current_token_count = sent_token_count
        else:
            current_chunk.append(sent.text.strip())
            current_token_count += sent_token_count
    
    # Append any remaining text as the last chunk.
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

def process_file(input_file, max_tokens):
    print(f"Processing file: {input_file}")
    text = load_text(input_file)
    chunks = chunk_text_with_spacy(text, max_tokens)
    
    # Create an output folder based on the input file name and max_tokens
    base_name = os.path.basename(input_file)
    name, ext = os.path.splitext(base_name)
    output_dir = f"chunked_output_{max_tokens}_{name}"
    os.makedirs(output_dir, exist_ok=True)
    
    for i, chunk in enumerate(chunks, 1):
        output_file = os.path.join(output_dir, f"{name}_chunk_{i}{ext}")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(chunk)
        print(f"Created: {output_file}")
    
    total_tokens = sum(len(chunk.split()) for chunk in chunks)
    print(f"\nFile: {input_file}")
    print(f"Total chunks created: {len(chunks)}")
    print(f"Approximate total tokens (by split words): {total_tokens}")
    avg_tokens = total_tokens // len(chunks) if chunks else 0
    print(f"Average tokens per chunk: {avg_tokens}\n")

def main():
    parser = argparse.ArgumentParser(
        description="Split text files into chunks using spaCy sentence tokenization, ensuring each chunk stays under a maximum token count."
    )
    parser.add_argument("input_files", nargs="+", help="Input file(s) or file patterns (e.g., '*.txt')")
    parser.add_argument("-m", "--max_tokens", type=int, default=DEFAULT_MAX_TOKENS,
                        help=f"Maximum tokens per chunk (default: {DEFAULT_MAX_TOKENS})")
    args = parser.parse_args()

    # Expand file patterns
    files = []
    for pattern in args.input_files:
        found = glob.glob(pattern)
        if found:
            files.extend(found)
        else:
            print(f"Warning: No files match the pattern '{pattern}'", file=sys.stderr)
    
    if not files:
        print("Error: No valid input files found.", file=sys.stderr)
        sys.exit(1)

    for file_path in files:
        process_file(file_path, args.max_tokens)

if __name__ == "__main__":
    main()
