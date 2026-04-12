#!/usr/bin/env python3

"""
# 🔊 WAVTrimmer.py
> **High-performance audio utility for batch trimming, joining, and segmenting WAV files.**

A versatile command-line tool designed for precision audio editing. It supports automatic silence detection, percentage-based trimming, and seamless file concatenation without re-encoding when possible.

---

## 🚀 Key Features
- 🔇 **Silence Trimming:** Automatically detect and remove silence from the start, end, or both.
- ✂️ **Precision Segmenting:** Split files at specific timestamps or intervals.
- 🔗 **Lossless Joining:** Concatenate multiple WAV files using FFmpeg's stream copy.
- 🔄 **Safe Overwriting:** Overwrites original files by default using a safe temporary-swap strategy.
- 📦 **Batch Processing:** Handle entire directories recursively.
- ⚡ **FFmpeg Integration:** Uses FFmpeg for lightning-fast, high-quality operations.

---

## 🛠 Usage
```bash
python wavtrim.py [files] [options]
```

### 📋 Main Options
| Flag | Name | Description |
| :--- | :--- | :--- |
| `-s` | `--silence` | Trim silence (e.g., `-s 60` or `-s auto`). |
| `-c` | `--copy` | Save as a new file (`_trimmed.wav`) instead of overwriting. |
| `-r` | `--recursive` | Process subfolders recursively. |
| `--start` | `--start [time]` | Trim from a specific start point (e.g., `01:30`). |
| `--end` | `--end [time]` | Trim to a specific end point. |
| `--join` | `--join` | Join provided files into one. |
| `--segment` | `--segment [pts]` | Split file at comma-separated points. |

### ⚙️ Configuration
- **Padding:** Use `--pad [ms]` and `--pad-end [ms]` to add breathing room after silence removal.
- **Re-encoding:** Use `--reencode` if you need to force a full rewrite (e.g., changing bit depth).

---

## 💡 Examples

### 1. Batch Trim Silence (Overwrite)
Remove silence from all `.wav` files in the current directory, overwriting the originals.
```bash
python wavtrim.py *.wav -s
```

### 2. Trim Silence and Keep Original
Save the trimmed versions as new files with a `_trimmed` suffix.
```bash
python wavtrim.py *.wav -s --copy
```

### 3. Join Multiple Files
```bash
python wavtrim.py file1.wav file2.wav --join --output final.wav
```

### 4. Split at Specific Points
```bash
python wavtrim.py long_audio.wav --segment "00:30, 01:45, 05:00"
```

---

## ⚠️ Requirements
- **Python 3.10+**
- **FFmpeg** (Recommended for performance and lossless stream copying)
- **soundfile** (`pip install soundfile`)
- **numpy** (`pip install numpy`)

---
*Last updated: 2026-04-13*
"""

import argparse
import glob
import os
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Tuple

import numpy as np

# --- CONFIGURATION DEFAULTS ---
DEFAULT_SILENCE_THRESHOLD = "auto"  # "auto" or numeric dB (e.g. 60)
AUTO_THRESHOLD_OFFSET = 0  # dB above noise floor for auto-detection
AUTO_THRESHOLD_MIN = 40  # Minimum (quietest) allowed auto-threshold (dB)
AUTO_THRESHOLD_MAX = 65  # Maximum (loudest) allowed auto-threshold (dB)
DEFAULT_PADDING_START_MS = 200  # Default lead-in padding
DEFAULT_PADDING_END_MS = 200  # Default lead-out padding
DEFAULT_TRIM_MODE = "start"  # Options: "start", "end", "both"
# ------------------------------

try:
    import soundfile as sf
except ImportError:
    print("Error: soundfile is not installed.")
    print("Install it with: pip install soundfile")
    sys.exit(1)


class WAVTrimmer:
    def __init__(self, verbose: bool = True, reencode: bool = False):
        """
        Initialize the trimmer with user preferences.
        
        WHAT: Sets up logging verbosity, re-encoding preference, and stats tracking.
        WHY:  Initializing stats here allows a single class instance to track 
              progress across a multi-file batch process.
        """
        self.verbose = verbose
        self.reencode = reencode
        self.ffmpeg_cmd = os.environ.get("FFMPEG_PATH", "ffmpeg")
        self.stats = {"processed": 0, "skipped": 0, "errors": 0}

    def check_ffmpeg(self):
        """
        Verifies if FFmpeg is installed and accessible.
        
        WHAT: Attempts to run 'ffmpeg -version'.
        WHY:  Fast-failing here prevents the script from crashing mid-process 
              with cryptic errors during actual audio operations.
        """
        try:
            subprocess.run(
                [self.ffmpeg_cmd, "-version"],
                capture_output=True,
                check=True,
                text=True,
                timeout=5,
            )
            return True
        except Exception:
            return False

    def run_ffmpeg(self, cmd: List[str], operation: str):
        """
        Executes an FFmpeg command via subprocess.
        
        WHAT: Runs the command, captures output, and logs errors on failure.
        WHY:  Centralizing FFmpeg calls ensures consistent logging (DEBUG vs ERROR) 
              and makes it easier to mock or swap dependencies in the future.
        """
        full_cmd = [self.ffmpeg_cmd] + cmd
        cmd_str = " ".join([f'"{c}"' if " " in str(c) else str(c) for c in full_cmd])
        self.log(f"  [DEBUG] Command: {cmd_str}")
        self.log(f"  FFmpeg: Running {operation}...")
        try:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            return result
        except subprocess.CalledProcessError as e:
            self.log(f"  [ERROR] FFmpeg failed with exit code {e.returncode}")
            self.log(f"  [ERROR] Stderr: {e.stderr}")
            raise Exception(f"FFmpeg {operation} failed (see logs above)")

    def log(self, message: str):
        if self.verbose:
            print(message)

    def format_duration(self, seconds: float) -> str:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes:02d}:{secs:06.3f}"

    def format_filesize(self, size_bytes: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"

    def load_wav(self, filepath: str) -> Tuple[np.ndarray, int, int, int, float]:
        """
        Reads a WAV file into memory.
        
        WHAT: Uses soundfile to extract audio data as a NumPy array.
        WHY:  We use a context manager (sf.SoundFile) to ensure the file handle 
              is explicitly closed immediately after reading, preventing 
              Windows "Access Denied" errors during later file operations.
        """
        try:
            with sf.SoundFile(filepath, "r") as f:
                # Load as float32 to maintain precision during processing
                audio_data = f.read(dtype="float32")
                frame_rate = f.samplerate
                channels = f.channels
                sample_width = f.subtype_info.split("_")[-1] # Approximation
                # subtype_info is something like 'PCM_16'
                if "16" in str(f.subtype): sample_width = 2
                elif "24" in str(f.subtype): sample_width = 3
                elif "32" in str(f.subtype): sample_width = 4
                else: sample_width = 2
                
                duration = len(audio_data) / frame_rate
                return audio_data, frame_rate, channels, sample_width, duration
        except Exception as e:
            raise Exception(f"Failed to load {filepath}: {e}")

    def save_wav(
        self,
        filepath: str,
        audio_data: np.ndarray,
        frame_rate: int,
        subtype: str = "PCM_16",
    ):
        try:
            sf.write(filepath, audio_data, frame_rate, subtype=subtype)
        except Exception as e:
            raise Exception(f"Failed to save {filepath}: {e}")

    def trim_by_time(
        self,
        input_file: str,
        output_file: str,
        start_sec: float = None,
        end_sec: float = None,
    ):
        """
        Trims a file between two absolute timestamps.
        
        WHAT: Uses FFmpeg stream copying if possible, otherwise falls back to numpy.
        WHY:  Lossless stream copying is preferred because it's nearly instantaneous 
              and preserves 100% of the original audio quality.
        """
        if not self.reencode and self.check_ffmpeg():
            cmd = ["-y", "-i", input_file]
            if start_sec is not None:
                cmd.extend(["-ss", str(start_sec)])
            if end_sec is not None:
                cmd.extend(["-to", str(end_sec)])
            cmd.extend(["-c", "copy", output_file])
            self.run_ffmpeg(cmd, "trim")
            self.log(f"  Done (no re-encode)! Output: {output_file}")
            return

        self.log(f"  Loading: {input_file}")
        audio, frame_rate, channels, sample_width, duration = self.load_wav(input_file)

        start_sample = 0 if start_sec is None else int(start_sec * frame_rate)
        end_sample = len(audio) if end_sec is None else int(end_sec * frame_rate)

        if start_sample < 0:
            start_sample = 0
        if end_sample > len(audio):
            end_sample = len(audio)
        if start_sample >= end_sample:
            raise Exception("Start time must be less than end time")

        trimmed = audio[start_sample:end_sample]

        self.log(
            f"  Duration: {self.format_duration(duration)} -> {self.format_duration((end_sample - start_sample) / frame_rate)}"
        )
        self.log(f"  Saving: {output_file}")
        self.save_wav(output_file, trimmed, frame_rate)
        self.log(f"  Done! Output: {output_file}")

    def trim_by_percentage(
        self,
        input_file: str,
        output_file: str,
        percent_start: float = 0,
        percent_end: float = 0,
    ):
        self.log(f"  Loading: {input_file}")
        audio, frame_rate, channels, sample_width, duration = self.load_wav(input_file)

        total_samples = len(audio)
        start_skip = int(total_samples * (percent_start / 100))
        end_skip = int(total_samples * (percent_end / 100))

        start_sample = start_skip
        end_sample = total_samples - end_skip

        if start_sample >= end_sample:
            raise Exception("Percentage values result in invalid range")

        trimmed = audio[start_sample:end_sample]

        self.log(
            f"  Duration: {self.format_duration(duration)} -> {self.format_duration((end_sample - start_sample) / frame_rate)}"
        )
        self.log(f"  Saving: {output_file}")
        self.save_wav(output_file, trimmed, frame_rate)
        self.log(f"  Done! Output: {output_file}")

    def trim_silence(
        self,
        input_file: str,
        output_file: str,
        threshold: str | int = DEFAULT_SILENCE_THRESHOLD,
        padding_start_ms: int = DEFAULT_PADDING_START_MS,
        padding_end_ms: int = DEFAULT_PADDING_END_MS,
        mode: str = DEFAULT_TRIM_MODE,  # start, end, both
    ):
        self.log(f"  Analyzing: {input_file}")
        audio, frame_rate, channels, sample_width, duration = self.load_wav(input_file)

        if channels > 1:
            audio_mono = np.mean(audio, axis=1)
        else:
            audio_mono = audio.flatten()

        # Vectorized RMS calculation using convolve (MUCH faster)
        # WHY: Looping over samples in Python is extremely slow. Using NumPy's 
        #      convolution allows us to calculate moving averages at C-speed.
        # 10ms window for RMS
        rms_window = int(0.01 * frame_rate)
        if rms_window < 1:
            rms_window = 1

        squared = audio_mono**2
        window = np.ones(rms_window) / rms_window
        rms = np.sqrt(np.convolve(squared, window, mode="same"))

        # --- Threshold Calculation ---
        # WHY: 'Auto' thresholding works by analyzing the noise floor.
        #      The 10th percentile typically represents the background hiss, 
        #      allowing us to set a threshold just above it.
        actual_threshold_db = 60  # Default fallback

        if str(threshold).lower() == "auto":
            # Convert RMS to dB for analysis. Clip to -100dB floor.
            rms_db = 20 * np.log10(np.clip(rms, 1e-5, 1.0))
            # The 10th percentile is usually the noise floor in most recordings
            noise_floor_db = np.percentile(rms_db, 10)
            # Set threshold above the noise floor
            actual_threshold_db = -(noise_floor_db + AUTO_THRESHOLD_OFFSET)
            # Constrain to sane limits
            actual_threshold_db = np.clip(
                actual_threshold_db, AUTO_THRESHOLD_MIN, AUTO_THRESHOLD_MAX
            )
            self.log(
                f"  Auto-detected noise floor: {noise_floor_db:.1f}dB | Setting threshold to: -{actual_threshold_db:.1f}dB"
            )
        else:
            try:
                actual_threshold_db = float(threshold)
            except ValueError:
                actual_threshold_db = 60

        threshold_linear = 10 ** (-actual_threshold_db / 20)
        non_silent = np.where(rms > threshold_linear)[0]

        if len(non_silent) == 0:
            self.log(f"  Warning: Entire file is silent, keeping original")
            if not self.reencode and self.check_ffmpeg():
                self.run_ffmpeg(
                    ["-y", "-i", input_file, "-c", "copy", output_file], "copy"
                )
            else:
                self.save_wav(output_file, audio, frame_rate)
        else:
            pad_start = int((padding_start_ms / 1000) * frame_rate)
            pad_end = int((padding_end_ms / 1000) * frame_rate)

            start_sample = 0
            end_sample = len(audio)

            if mode in ["start", "both"]:
                start_sample = max(0, non_silent[0] - pad_start)

            if mode in ["end", "both"]:
                end_sample = min(len(audio), non_silent[-1] + pad_end)

            start_sec = start_sample / frame_rate
            end_sec = end_sample / frame_rate

            self.log(
                f"  Silence Analysis: Detected speech range {self.format_duration(start_sec)} to {self.format_duration(end_sec)}"
            )
            self.log(
                f"  (Relative timestamps: Start {start_sec:.3f}s, End {end_sec:.3f}s)"
            )

            if not self.reencode and self.check_ffmpeg():
                self.run_ffmpeg(
                    [
                        "-y",
                        "-i",
                        input_file,
                        "-ss",
                        str(start_sec),
                        "-to",
                        str(end_sec),
                        "-c",
                        "copy",
                        output_file,
                    ],
                    "trim_silence",
                )
                self.log(f"  Done (no re-encode)! Output: {output_file}")
            else:
                trimmed = audio[start_sample:end_sample]
                self.log(
                    f"  Duration: {self.format_duration(duration)} -> {self.format_duration((end_sample - start_sample) / frame_rate)}"
                )
                self.log(f"  Saving: {output_file}")
                self.save_wav(output_file, trimmed, frame_rate)
                self.log(f"  Done! Output: {output_file}")

    def segment(self, input_file: str, output_dir: str, points: List[str]):
        if not self.reencode and self.check_ffmpeg():
            input_basename = Path(input_file).stem
            # Construced a complex segment command or just multiple individual ones
            # Multiple individual ones are more robust for no-reencode starting points
            audio, frame_rate, channels, sample_width, duration = self.load_wav(
                input_file
            )
            total_samples = len(audio)

            time_points_sec = []
            for point in points:
                if ":" in point:
                    parts = point.split(":")
                    if len(parts) == 2:
                        time_points_sec.append(int(parts[0]) * 60 + float(parts[1]))
                    else:
                        time_points_sec.append(
                            int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                        )
                else:
                    time_points_sec.append(float(point))

            time_points_sec = sorted(
                set([p for p in time_points_sec if 0 < p < duration])
            )
            boundaries = [0] + time_points_sec + [duration]

            for i in range(len(boundaries) - 1):
                start = boundaries[i]
                end = boundaries[i + 1]
                output_file = os.path.join(
                    output_dir, f"{input_basename}_part{i + 1:03d}.wav"
                )
                self.log(
                    f"  Segmenting part {i + 1}: {self.format_duration(start)}-{self.format_duration(end)}"
                )
                self.run_ffmpeg(
                    [
                        "-y",
                        "-i",
                        input_file,
                        "-ss",
                        str(start),
                        "-to",
                        str(end),
                        "-c",
                        "copy",
                        output_file,
                    ],
                    "segment",
                )
            return

        self.log(f"  Loading: {input_file}")
        audio, frame_rate, channels, sample_width, duration = self.load_wav(input_file)

        total_samples = len(audio)

        time_points = []
        for point in points:
            if ":" in point:
                parts = point.split(":")
                minutes = int(parts[0])
                seconds = float(parts[1])
                time_points.append(int((minutes * 60 + seconds) * frame_rate))
            else:
                time_points.append(int(float(point) * frame_rate))

        time_points = sorted(set([p for p in time_points if 0 < p < total_samples]))

        if not time_points:
            raise Exception("No valid time points provided")

        boundaries = [0] + time_points + [total_samples]

        input_basename = Path(input_file).stem

        for i in range(len(boundaries) - 1):
            start_sample = boundaries[i]
            end_sample = boundaries[i + 1]
            segment = audio[start_sample:end_sample]

            output_file = os.path.join(
                output_dir, f"{input_basename}_part{i + 1:03d}.wav"
            )
            start_sec = start_sample / frame_rate
            end_sec = end_sample / frame_rate
            self.log(
                f"  Exporting part {i + 1}: {self.format_duration(start_sec)}-{self.format_duration(end_sec)}"
            )
            self.save_wav(output_file, segment, frame_rate)

        self.log(f"  Done! Created {len(boundaries) - 1} segments")

    def join(self, input_files: List[str], output_file: str):
        """
        Concatenates multiple WAV files into a single output.
        
        WHAT: Uses FFmpeg's concat demuxer if possible.
        WHY:  The 'concat' demuxer is much faster than manual numpy concatenation 
              as it only re-wraps the audio stream without re-encoding.
        """
        if len(input_files) < 2:
            raise Exception("At least 2 input files required for join")

        if not self.reencode and self.check_ffmpeg():
            # Use concat demuxer
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                for file in input_files:
                    # FFmpeg concat file needs escaped paths
                    abs_path = os.path.abspath(file).replace("\\", "/")
                    f.write(f"file '{abs_path}'\n")
                temp_list = f.name

            try:
                self.run_ffmpeg(
                    [
                        "-y",
                        "-f",
                        "concat",
                        "-safe",
                        "0",
                        "-i",
                        temp_list,
                        "-c",
                        "copy",
                        output_file,
                    ],
                    "join",
                )
                self.log(f"  Done (no re-encode)! Output: {output_file}")
            finally:
                if os.path.exists(temp_list):
                    os.remove(temp_list)
            return

        self.log(f"  Loading {len(input_files)} files...")
        combined = None
        frame_rate = None
        channels = None
        sample_width = None
        total_duration = 0

        for filepath in input_files:
            audio, fr, ch, sw, dur = self.load_wav(filepath)

            if frame_rate is None:
                frame_rate = fr
                channels = ch
            elif fr != frame_rate:
                raise Exception(
                    f"Frame rate mismatch: {filepath} ({fr}) vs expected ({frame_rate})"
                )
            elif ch != channels:
                raise Exception(
                    f"Channel mismatch: {filepath} ({ch}) vs expected ({channels})"
                )

            if combined is None:
                combined = audio
            else:
                combined = np.concatenate([combined, audio])

            self.log(
                f"    Added: {os.path.basename(filepath)} ({self.format_duration(dur)})"
            )
            total_duration += dur

        self.log(f"  Total duration: {self.format_duration(total_duration)}")
        self.log(f"  Saving: {output_file}")
        self.save_wav(output_file, combined, frame_rate)
        self.log(f"  Done! Output: {output_file}")

    def print_summary(self):
        self.log("\n" + "=" * 60)
        self.log("PROCESSING SUMMARY")
        self.log("=" * 60)
        self.log(f"  Processed: {self.stats['processed']}")
        self.log(f"  Skipped:   {self.stats['skipped']}")
        self.log(f"  Errors:    {self.stats['errors']}")
        self.log(f"  Total:     {sum(self.stats.values())}")

        if self.stats["errors"] > 0:
            self.log(f"\n  Warning: {self.stats['errors']} file(s) had errors")

        self.log("=" * 60)


def parse_time(value: str) -> float:
    if ":" in value:
        parts = value.split(":")
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        elif len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
    try:
        return float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid time format: {value}")


def parse_points(value: str) -> List[str]:
    points = [p.strip() for p in value.split(",")]
    if not points:
        raise argparse.ArgumentTypeError("At least one time point required")
    return points


def main():
    parser = argparse.ArgumentParser(
        description="WAV Audio Trimmer - Edit and trim WAV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage Examples:
  wavtrim.py *.wav -s           # Batch trim silence (current dir)
  wavtrim.py file.wav --join file2.wav --output joined.wav
  wavtrim.py file.wav --segment "01:30, 02:45"
  wavtrim.py file.wav -s --pad 200  # Silence trim with 200ms padding
        """,
    )

    parser.add_argument("files", nargs="*", help="Input files")
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Search recursively in subfolders (batch mode)",
    )
    parser.add_argument(
        "-s",
        "--silence",
        nargs="?",
        const=DEFAULT_SILENCE_THRESHOLD,
        default=None,
        help=f"Trim silence (dB value or 'auto', default: {DEFAULT_SILENCE_THRESHOLD})",
    )
    parser.add_argument(
        "--pad",
        type=int,
        default=DEFAULT_PADDING_START_MS,
        help=f"Padding in ms for start (default: {DEFAULT_PADDING_START_MS})",
    )
    parser.add_argument(
        "--pad-end",
        type=int,
        default=DEFAULT_PADDING_END_MS,
        help=f"Padding in ms for end (default: {DEFAULT_PADDING_END_MS})",
    )

    # Trim Modes
    parser.add_argument(
        "--both", action="store_true", help="Trim silence from both start and end"
    )
    parser.add_argument(
        "--only-end", action="store_true", help="Trim silence from end only"
    )
    parser.add_argument(
        "--only-start",
        action="store_true",
        help=f"Trim silence from start only {'(Default)' if DEFAULT_TRIM_MODE == 'start' else ''}",
    )
    parser.add_argument("--start", type=parse_time, help="Start time for trim")
    parser.add_argument("--end", type=parse_time, help="End time for trim")
    parser.add_argument(
        "--join", action="store_true", help="Join multiple files into one"
    )
    parser.add_argument(
        "--segment",
        type=parse_points,
        help="Split file at time points (comma separated)",
    )
    parser.add_argument(
        "--reencode", action="store_true", help="Force re-encoding (no stream copy)"
    )
    parser.add_argument("-o", "--output", help="Output filename (for join/single file)")
    parser.add_argument(
        "-c",
        "--copy",
        action="store_true",
        help="Save as a new file (_trimmed.wav) instead of overwriting the original",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=True,
        help="Verbose output (default)",
    )
    parser.add_argument(
        "-no-v", "--quiet", action="store_false", dest="verbose", help="Quiet output"
    )
    parser.add_argument(
        "-i", "--info", action="store_true", help="Information only (no trimming)"
    )

    args = parser.parse_args()
    trimmer = WAVTrimmer(verbose=args.verbose, reencode=args.reencode)

    # 1. Expand wildcards/directories if in batch mode (no files provided or single *)
    input_files = []
    seen = set()
    for f in args.files or []:
        if f == "*":
            extensions = ["wav", "WAV"]
            globs = [
                f"**/*.{ext}" if args.recursive else f"*.{ext}" for ext in extensions
            ]
            for g in globs:
                for match in sorted(glob.glob(g, recursive=args.recursive)):
                    if match not in seen:
                        input_files.append(match)
                        seen.add(match)
        elif "*" in f or "?" in f:
            for match in sorted(glob.glob(f, recursive=args.recursive)):
                if match not in seen:
                    input_files.append(match)
                    seen.add(match)
        else:
            if f not in seen or args.join:  # Allow duplicates for join
                input_files.append(f)
                seen.add(f)

    # 1.4 Setting Default Action (Silence Trim)
    action_found = any(
        [
            args.join,
            args.segment,
            args.silence is not None,
            args.start is not None,
            args.end is not None,
            args.info,
        ]
    )
    if not action_found:
        args.silence = DEFAULT_SILENCE_THRESHOLD

    if not input_files:
        parser.print_help()
        sys.exit(0)

    # 1.5 Plan Reporting
    if args.verbose:
        mode = "INFO ONLY (No changes)"
        if args.info:
            mode = "INFO ONLY (No changes)"
        elif args.join:
            mode = "JOIN"
        elif args.segment:
            mode = "SEGMENT"
            mode = "SILENCE TRIM"
            if not action_found:
                mode += " (DEFAULT)"

        # Determine sub-mode for silence trim
        trim_mode = DEFAULT_TRIM_MODE
        if args.both:
            trim_mode = "both"
        elif args.only_end:
            trim_mode = "end"
        elif args.only_start:
            trim_mode = "start"

        print(f"\n--- Processing Plan ---")
        print(f"  Mode:      {mode}")
        if "SILENCE" in mode:
            print(
                f"  Target:    {trim_mode.upper()} ONLY"
                if trim_mode != "both"
                else "  Target:    BOTH ENDS"
            )
        print(f"  Files:     {len(input_files)}")
        print(f"  Action:    {'COPY (_trimmed)' if args.copy else 'OVERWRITE (Original)'}")
        print(f"  Re-encode: {args.reencode}")
        if args.silence is not None:
            print(
                f"  Threshold: {args.silence}{'dB' if args.silence != 'auto' else ''}"
            )
            print(f"  Pad Start: {args.pad}ms")
            print(f"  Pad End:   {args.pad_end}ms")

        if args.info:
            print(f"  [!] Run without --info to perform default silence trimming.")

        print(f"-----------------------\n")

    # 2. Case: Join
    if args.join:
        output = args.output or "combined.wav"
        trimmer.join(input_files, output)
        sys.exit(0)

    # 3. Case: Segment (Single file only)
    if args.segment:
        if len(input_files) > 1:
            print("Error: --segment only supports one file at a time.")
            sys.exit(1)
        output_dir = os.path.dirname(input_files[0]) or "."
        trimmer.segment(input_files[0], output_dir, args.segment)
        sys.exit(0)

    # 4. Standard Processing (Single or Multiple)
    for input_file in input_files:
        if not os.path.exists(input_file):
            print(f"File not found: {input_file}")
            continue

        # Determine output name
        if len(input_files) == 1 and args.output:
            final_output = args.output
        elif args.copy:
            final_output = f"{Path(input_file).stem}_trimmed.wav"
        else:
            final_output = input_file

        # Info mode doesn't need temp files
        if args.info:
            try:
                audio, fr, ch, sw, dur = trimmer.load_wav(input_file)
                trimmer.log(
                    f"File: {input_file} | {fr}Hz | {ch}ch | {trimmer.format_duration(dur)}"
                )
            except Exception as e:
                print(f"Error reading {input_file}: {e}")
            continue

        # For writing, always use a temp file first for safety.
        # WHY: Writing output to a file that is also the input (overwrite) 
        #      can lead to data truncation or corruption if the process crashes. 
        #      Writing to a .tmp file and then 'os.replace'ing ensures atomicity.
        #      We use a '.wav' extension so FFmpeg can correctly guess the format.
        temp_output = str(Path(final_output).with_suffix("")) + "_tmp_trim.wav"
        
        try:
            if args.silence is not None:
                # Determine trim mode
                trim_mode = DEFAULT_TRIM_MODE
                if args.both:
                    trim_mode = "both"
                elif args.only_end:
                    trim_mode = "end"
                elif args.only_start:
                    trim_mode = "start"

                trimmer.trim_silence(
                    input_file,
                    temp_output,
                    args.silence,
                    args.pad,
                    args.pad_end,
                    mode=trim_mode,
                )
            elif args.start is not None or args.end is not None:
                trimmer.trim_by_time(input_file, temp_output, args.start, args.end)
            
            # If successful, move temp to final
            if os.path.exists(temp_output):
                # Ensure the final_output is not Read-Only (common WinError 5 cause)
                if os.path.exists(final_output):
                    mode = os.stat(final_output).st_mode
                    if not mode & stat.S_IWRITE:
                        os.chmod(final_output, mode | stat.S_IWRITE)

                # Robust replace/rename with a small retry loop to handle transient locks
                max_retries = 5
                success = False
                last_error = None

                for attempt in range(max_retries):
                    try:
                        if final_output == input_file:
                            os.replace(temp_output, final_output)
                        else:
                            if os.path.exists(final_output):
                                os.remove(final_output)
                            os.rename(temp_output, final_output)
                        success = True
                        break
                    except OSError as e:
                        last_error = e
                        # Short sleep to let background processes (like AV) release the lock
                        time.sleep(0.1)
                
                if success:
                    trimmer.stats["processed"] += 1
                else:
                    raise Exception(f"Failed to overwrite {final_output} after {max_retries} attempts: {last_error}")
            else:
                trimmer.stats["skipped"] += 1

        except Exception as e:
            print(f"Error processing {input_file}: {e}")
            trimmer.stats["errors"] += 1
            if os.path.exists(temp_output):
                os.remove(temp_output)

    trimmer.print_summary()


if __name__ == "__main__":
    main()
