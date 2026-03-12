import sys
import os
import glob
import subprocess
import nemo.collections.asr as nemo_asr

MEDIA_EXTS = {
    ".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm", ".mpg", ".mpeg",
    ".m4v", ".3gp", ".3g2", ".ts", ".m2ts", ".vob", ".ogv",
    ".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".oga", ".opus", ".wma",
    ".alac", ".aiff", ".aif", ".amr", ".ac3", ".eac3", ".mka", ".m4b", ".m4p",
}

def format_time(seconds):
    """Converts seconds to SRT time format (HH:MM:SS,mmm)."""
    msec = int((seconds - int(seconds)) * 1000)
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{msec:03d}"

def extract_audio(input_file, output_wav):
    """Extracts audio to 16kHz mono WAV using FFmpeg."""
    cmd = [
        "ffmpeg", "-y", "-i", input_file,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1", output_wav
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

def write_srt(words, srt_filename):
    """Groups words into segments and writes the SRT file."""
    with open(srt_filename, 'w', encoding='utf-8') as f:
        segment_index = 1
        current_segment = []
        segment_start = 0.0

        for i, word_info in enumerate(words):
            if not current_segment:
                segment_start = word_info['start_time']

            current_segment.append(word_info['word'])

            if len(current_segment) >= 10 or i == len(words) - 1:
                segment_end = word_info['end_time']
                text = " ".join(current_segment)

                f.write(f"{segment_index}\n")
                f.write(f"{format_time(segment_start)} --> {format_time(segment_end)}\n")
                f.write(f"{text}\n\n")

                segment_index += 1
                current_segment = []

def is_media_file(path):
    _, ext = os.path.splitext(path)
    return ext.lower() in MEDIA_EXTS

def iter_media_files(root, recursive):
    if recursive:
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                path = os.path.join(dirpath, name)
                if is_media_file(path):
                    yield path
    else:
        for name in os.listdir(root):
            path = os.path.join(root, name)
            if os.path.isfile(path) and is_media_file(path):
                yield path

def collect_input_files(args):
    cwd = os.getcwd()
    files = []

    if not args:
        return list(iter_media_files(cwd, recursive=True))

    if len(args) == 1 and args[0] == "*":
        return list(iter_media_files(cwd, recursive=False))

    for raw in args:
        # Allow user-provided globs like *.mp4 or **/*.mkv
        if any(ch in raw for ch in "*?["):
            matches = glob.glob(raw, recursive=True)
            for m in matches:
                if os.path.isdir(m):
                    files.extend(iter_media_files(m, recursive=True))
                elif os.path.isfile(m) and is_media_file(m):
                    files.append(m)
            continue

        path = raw
        if not os.path.isabs(path):
            path = os.path.abspath(os.path.join(cwd, path))

        if os.path.isdir(path):
            files.extend(iter_media_files(path, recursive=True))
        elif os.path.isfile(path) and is_media_file(path):
            files.append(path)

    # De-duplicate while preserving order
    seen = set()
    unique = []
    for p in files:
        ap = os.path.abspath(p)
        if ap not in seen:
            seen.add(ap)
            unique.append(ap)
    return unique

def transcribe_file(input_file, model):
    base_name = os.path.splitext(input_file)[0]
    wav_file = f"{base_name}_temp.wav"
    srt_file = f"{base_name}.srt"

    extract_audio(input_file, wav_file)

    hypotheses = model.transcribe([wav_file], return_hypotheses=True)
    hypothesis = hypotheses[0]

    if hasattr(hypothesis, 'word_timestamps') and hypothesis.word_timestamps:
        write_srt(hypothesis.word_timestamps, srt_file)
    else:
        print("Word timestamps not natively returned by this model version. Writing flat text file.")
        with open(f"{base_name}.txt", "w", encoding="utf-8") as f:
            f.write(hypothesis.text)

    if os.path.exists(wav_file):
        os.remove(wav_file)

def main():
    args = sys.argv[1:]
    input_files = collect_input_files(args)

    if not input_files:
        print("No media files found to process.")
        print("Usage:")
        print("  python transcribe-p.py <input_video>")
        print("  python transcribe-p.py *   (current folder only)")
        print("  python transcribe-p.py     (recursive from current folder)")
        sys.exit(1)

    model = nemo_asr.models.ASRModel.from_pretrained(model_name="nvidia/parakeet-tdt-1.1b")

    for input_file in input_files:
        transcribe_file(input_file, model)

if __name__ == "__main__":
    main()
