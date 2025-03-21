import sys
import glob
import os
from pydub import AudioSegment
from pyannote.audio import Pipeline

def main():
    # Check if any file patterns were provided
    if len(sys.argv) < 2:
        print("Usage: Diariaze.py *.wav")
        sys.exit(1)
    
    # Expand glob patterns from the command-line arguments
    files = []
    for pattern in sys.argv[1:]:
        files.extend(glob.glob(pattern))
    
    if not files:
        print("No files found. Please check your file pattern.")
        sys.exit(1)
    
    # Retrieve Hugging Face token from Windows environment variable
    hf_token = os.environ.get("HF_TOKEN")
    if not hf_token:
        print("Error: HF_TOKEN environment variable not found. Please set it to your Hugging Face token.")
        sys.exit(1)
    
    # Load the pre-trained diarization pipeline using your token.
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token=hf_token)
    
    # Process each audio file
    for file in files:
        print(f"Processing file: {file}")
        
        # Run speaker diarization on the file
        diarization = pipeline(file)
        
        # Load the entire audio file with pydub
        audio = AudioSegment.from_file(file)
        duration_ms = len(audio)  # Total duration in milliseconds
        
        # Dictionary to hold silent tracks for each speaker
        speakers = {}
        
        # Initialize a silent track for each unique speaker label in the diarization result
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            if speaker not in speakers:
                speakers[speaker] = AudioSegment.silent(duration=duration_ms)
        
        # Overlay the original audio segments onto the corresponding speaker's silent track
        for turn, _, speaker in diarization.itertracks(yield_label=True):
            start_ms = int(turn.start * 1000)
            end_ms = int(turn.end * 1000)
            segment_audio = audio[start_ms:end_ms]
            # Overlay the segment at its correct position on the speaker's track
            speakers[speaker] = speakers[speaker].overlay(segment_audio, position=start_ms)
        
        # Create output files for each speaker
        base_name = os.path.splitext(os.path.basename(file))[0]
        for speaker, track in speakers.items():
            output_filename = f"{base_name}_speaker{speaker}.wav"
            print(f"Exporting: {output_filename}")
            track.export(output_filename, format="wav")
    
if __name__ == "__main__":
    main()
