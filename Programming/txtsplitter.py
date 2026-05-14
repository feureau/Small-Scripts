import os
import sys
import argparse
import re

try:
    import nltk
except ImportError:
    print("Error: nltk is not installed. Please install it using 'pip install nltk'")
    sys.exit(1)

def ensure_nltk_data():
    """Ensure that the necessary NLTK tokenizers are downloaded."""
    try:
        nltk.data.find('tokenizers/punkt_tab')
    except LookupError:
        try:
             nltk.data.find('tokenizers/punkt')
        except LookupError:
            print("Downloading NLTK punkt tokenizer...")
            nltk.download('punkt', quiet=True)
            nltk.download('punkt_tab', quiet=True)

def split_text_file(input_file, output_dir, max_chars=None, max_tokens=None):
    """
    Split a text file into smaller chunks without breaking paragraphs or sentences.
    """
    if not os.path.isfile(input_file):
        print(f"Error: File '{input_file}' not found.")
        return

    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Determine size calculation method
    if max_tokens is not None:
        try:
            import tiktoken
            # cl100k_base is the encoding used by gpt-3.5-turbo and gpt-4
            encoder = tiktoken.get_encoding("cl100k_base")
            def get_len(text):
                return len(encoder.encode(text))
            limit = max_tokens
        except ImportError:
            print("Error: 'tiktoken' is not installed. Please install it using 'pip install tiktoken' to use token limits.")
            return
    else:
        def get_len(text):
            return len(text)
        limit = max_chars if max_chars else 5000
        
    with open(input_file, 'r', encoding='utf-8') as f:
        text = f.read()

    ensure_nltk_data()

    # Split text into paragraphs based on one or more empty lines
    paragraphs = re.split(r'\n\s*\n', text)
    
    chunks = []
    current_chunk = ""
    current_len = 0
    
    for para in paragraphs:
        # Strip trailing/leading whitespaces from the paragraph
        para = para.strip()
        if not para:
            continue
            
        para_len = get_len(para)
        separator_len = get_len("\n\n") if current_chunk else 0

        # If the paragraph fits in the current chunk, add it
        if current_len + separator_len + para_len <= limit:
            if current_chunk:
                current_chunk += "\n\n" + para
                current_len += separator_len + para_len
            else:
                current_chunk = para
                current_len = para_len
        else:
            # If current_chunk has content, push it to chunks and start a new one
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
                current_len = 0
            
            # Now we process the current paragraph.
            # If the paragraph alone is within the limit, it becomes the new chunk
            if para_len <= limit:
                current_chunk = para
                current_len = para_len
            else:
                # The paragraph itself is too large, need to split by sentences
                sentences = nltk.tokenize.sent_tokenize(para)
                for sent in sentences:
                    sent_len = get_len(sent)
                    sep_len = get_len(" ") if current_chunk else 0
                    
                    # If sentence fits in the current chunk
                    if current_len + sep_len + sent_len <= limit:
                        if current_chunk:
                            current_chunk += " " + sent
                            current_len += sep_len + sent_len
                        else:
                            current_chunk = sent
                            current_len = sent_len
                    else:
                        # If current chunk has content, push it
                        if current_chunk:
                            chunks.append(current_chunk)
                        
                        # Set current chunk to the current sentence
                        # If a single sentence exceeds limit, it's kept whole 
                        # to avoid cutting it randomly.
                        current_chunk = sent
                        current_len = sent_len

    if current_chunk:
        chunks.append(current_chunk)

    if not chunks:
        print("Warning: No text to split found in the file.")
        return

    base_name = os.path.splitext(os.path.basename(input_file))[0]
    out_dir = output_dir if output_dir else os.path.dirname(os.path.abspath(input_file))
    
    num_digits = len(str(len(chunks)))
    for i, chunk in enumerate(chunks):
        # Format filename like filename_part01.txt
        out_file = os.path.join(out_dir, f"{base_name}_part{str(i+1).zfill(num_digits)}.txt")
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(chunk)
        print(f"Created {out_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split a text file contextually into multiple files without breaking sentences/paragraphs.")
    parser.add_argument("input_file", help="Path to the input text file")
    parser.add_argument("-o", "--output-dir", help="Directory to save the split files (defaults to input file's directory)")
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-c", "--max-chars", type=int, help="Maximum characters per split file (default: 5000 if no token limit is set)")
    group.add_argument("-t", "--max-tokens", type=int, help="Maximum LLM tokens per split file (uses OpenAI cl100k_base tokenizer)")
    
    args = parser.parse_args()
    
    input_path = os.path.abspath(args.input_file)
    output_path = os.path.abspath(args.output_dir) if args.output_dir else None
    
    split_text_file(input_path, output_path, max_chars=args.max_chars, max_tokens=args.max_tokens)
