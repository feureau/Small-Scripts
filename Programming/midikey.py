#!/usr/bin/env python3
"""
Analyze MIDI files and output the detected musical key.
Usage: python midi_key_finder.py file1.mid file2.mid ... *.mid
"""

import sys
import glob
from pathlib import Path

# Try to import music21 for key detection
try:
    from music21 import converter, key
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False
    print("Error: music21 is not installed. Please run: pip install music21")
    sys.exit(1)

def detect_key(midi_path: str) -> tuple[str, float]:
    """
    Detect the key of a MIDI file using music21's Krumhansl-Schmuckler algorithm.
    Returns (key_name, correlation_coefficient)
    """
    score = converter.parse(midi_path)
    k = score.analyze('key')
    return (k.tonicPitchNameWithCase + ' ' + k.mode, k.correlationCoefficient)

def main():
    if len(sys.argv) < 2:
        print("Usage: python midi_key_finder.py <midi_file1> <midi_file2> ...")
        print("       Wildcards like *.mid are supported.")
        sys.exit(1)

    midi_files = []
    for arg in sys.argv[1:]:
        if '*' in arg or '?' in arg:
            expanded = glob.glob(arg)
            midi_files.extend(Path(p) for p in expanded if Path(p).is_file())
        else:
            path = Path(arg)
            if path.is_file():
                midi_files.append(path)
            else:
                print(f"Warning: '{arg}' is not a valid file, skipping.")

    if not midi_files:
        print("No valid MIDI files found.")
        sys.exit(1)

    print(f"{'File':<50} {'Key':<15} {'Confidence'}")
    print("-" * 75)

    for midi_file in midi_files:
        try:
            key_name, confidence = detect_key(str(midi_file))
            print(f"{midi_file.name:<50} {key_name:<15} {confidence:.3f}")
        except Exception as e:
            print(f"{midi_file.name:<50} ERROR: {e}")

if __name__ == "__main__":
    main()