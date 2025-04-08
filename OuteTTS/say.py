import sys
import glob
import os
import outetts

def generate_audio_from_text(text, output_filename):
    # Set up the configuration for the model. Adjust parameters if needed.
    config = outetts.ModelConfig.auto_config(
        model=outetts.Models.VERSION_1_0_SIZE_1B,
        backend=outetts.Backend.LLAMACPP,
        quantization=outetts.LlamaCppQuantization.FP16
    )
    interface = outetts.Interface(config=config)
    # Load the default speaker profile
    speaker = interface.load_default_speaker("EN-FEMALE-1-NEUTRAL")
    
    # Generate speech from the text.
    output = interface.generate(
        config=outetts.GenerationConfig(
            text=text,
            generation_type=outetts.GenerationType.CHUNKED,
            speaker=speaker,
            sampler_config=outetts.SamplerConfig(temperature=0.4)
        )
    )
    
    # Save the generated audio as a WAV file.
    output.save(output_filename)
    print(f"✅ Generated audio saved as {output_filename}")

def main():
    # Ensure at least one argument is given (the text files)
    if len(sys.argv) < 2:
        print("Usage: python say.py <txt-file-pattern>")
        sys.exit(1)
    
    # Expand command line arguments into file list.
    file_patterns = sys.argv[1:]
    files = []
    for pattern in file_patterns:
        # The glob function will expand the wildcard pattern (if any).
        files.extend(glob.glob(pattern))

    # If no files were found, exit.
    if not files:
        print("No files matched the given pattern(s).")
        sys.exit(1)

    # Process each file.
    for file_path in files:
        if os.path.isfile(file_path):
            # Read the text from the file
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read().strip()
                
            # Generate output filename by replacing .txt with .wav
            base, ext = os.path.splitext(file_path)
            output_filename = base + ".wav"
            
            print(f"Processing {file_path} ...")
            generate_audio_from_text(text, output_filename)
        else:
            print(f"Skipping {file_path} (not a file)")

if __name__ == "__main__":
    main()
