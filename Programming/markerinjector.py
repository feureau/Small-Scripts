#!/usr/bin/env python3
"""
markerinjector.py - Inject chapter markers into a video file.

Chapter source: DaVinci Resolve "Export Timeline Markers to EDL".

Usage:
    python markerinjector.py <video_file> [<edl_file>]

If <edl_file> is omitted, the script looks for:
    <video_basename>.edl      (next to the video)
    <video_basename>.EDL
    any single *.edl in the same folder

If the video already contains chapters, the user is prompted to either
replace them or merge the new EDL chapters with the existing ones.
"""

import subprocess
import sys
import os
import re
import json
import glob
import tempfile
from typing import List, Tuple, Optional


# ---------------------------------------------------------------------------
# EDL parsing
# ---------------------------------------------------------------------------

_EDIT_LINE_RE = re.compile(
    r'^\d+\s+\d+\s+V\s+C\s+'
    r'(\d{2}:\d{2}:\d{2}[:;]\d{2})\s+'
    r'(\d{2}:\d{2}:\d{2}[:;]\d{2})\s+'
    r'(\d{2}:\d{2}:\d{2}[:;]\d{2})\s+'
    r'(\d{2}:\d{2}:\d{2}[:;]\d{2})'
)

_MARKER_LINE_RE = re.compile(r'\|\s*M:(?P<name>[^|]+?)\s*(?:\||$)')


def parse_edl(edl_path: str) -> List[Tuple[str, str]]:
    markers: List[Tuple[str, str]] = []
    last_record_in: Optional[str] = None

    with open(edl_path, 'r', encoding='utf-8', errors='replace') as f:
        for raw in f:
            line = raw.rstrip('\n')
            m = _EDIT_LINE_RE.match(line.strip())
            if m:
                last_record_in = m.group(3)
                continue
            m = _MARKER_LINE_RE.search(line)
            if m and last_record_in is not None:
                markers.append((last_record_in, m.group('name').strip()))
                last_record_in = None
    return markers


def timecode_to_seconds(tc: str, fps: float) -> float:
    tc = tc.replace(';', ':')
    h, m, s, f = (int(x) for x in tc.split(':'))
    return h * 3600 + m * 60 + s + (f / fps)


# ---------------------------------------------------------------------------
# Video probing
# ---------------------------------------------------------------------------

def probe_video(path: str) -> Tuple[float, float]:
    dur_cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        path,
    ]
    dur_out = subprocess.run(dur_cmd, capture_output=True, text=True)
    if dur_out.returncode != 0:
        raise RuntimeError(f"ffprobe failed:\n{dur_out.stderr}")
    duration = float(dur_out.stdout.strip())

    fps_cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=r_frame_rate',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        path,
    ]
    fps_out = subprocess.run(fps_cmd, capture_output=True, text=True)
    if fps_out.returncode != 0:
        raise RuntimeError(f"ffprobe failed:\n{fps_out.stderr}")
    rate = fps_out.stdout.strip()
    if '/' in rate:
        num, den = rate.split('/')
        fps = float(num) / float(den)
    else:
        fps = float(rate)

    return duration, fps


def probe_existing_chapters(path: str) -> List[Tuple[float, float, str]]:
    cmd = ['ffprobe', '-v', 'error', '-show_chapters', '-of', 'json', path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout or '{}')
    except json.JSONDecodeError:
        return []
    chapters = []
    for ch in data.get('chapters', []):
        try:
            start = float(ch.get('start_time', 0))
            end = float(ch.get('end_time', 0))
        except (TypeError, ValueError):
            continue
        title = (ch.get('tags') or {}).get('title', '') or ''
        chapters.append((start, end, title))
    return chapters


def find_chapter_track_indices(video_path: str) -> List[int]:
    """
    Return stream indices of QuickTime chapter text tracks.

    These show up in ffprobe as:
        codec_type = "data"
        codec_name = "bin_data"
        codec_tag_string = "text"

    We must NOT drop the timecode track, which is also a data stream but has
    codec_tag_string = "tmcd".
    """
    cmd = ['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', video_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return []
    try:
        data = json.loads(result.stdout or '{}')
    except json.JSONDecodeError:
        return []

    drop = []
    for s in data.get('streams', []):
        if s.get('codec_type') == 'data' and s.get('codec_tag_string') == 'text':
            drop.append(s.get('index'))
    return [i for i in drop if isinstance(i, int)]


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

def ask_chapter_mode(
    existing: List[Tuple[float, float, str]],
    new: List[Tuple[float, float, str]],
) -> str:
    print(f"\nThis video already contains {len(existing)} chapter(s):")
    for s, e, t in existing:
        print(f"  {s:8.3f}s -> {e:8.3f}s  {t or '(untitled)'}")
    print(f"\nThe EDL provides {len(new)} chapter(s):")
    for s, e, t in new:
        print(f"  {s:8.3f}s -> {e:8.3f}s  {t or '(untitled)'}")

    print("\nWhat do you want to do?")
    print("  [r] Replace - discard existing chapters, use only the EDL chapters")
    print("  [m] Merge   - keep existing chapters, add the new EDL chapters")
    print("  [q] Quit")

    while True:
        try:
            ans = input("Choice [r/m/q]: ").strip().lower()
        except EOFError:
            return 'quit'
        if ans in ('r', 'replace'):
            return 'replace'
        if ans in ('m', 'merge'):
            return 'merge'
        if ans in ('q', 'quit'):
            return 'quit'
        print("Please type r, m, or q.")


# ---------------------------------------------------------------------------
# Chapter combination
# ---------------------------------------------------------------------------

def rechain(
    ordered: List[Tuple[float, str]], duration: float
) -> List[Tuple[float, float, str]]:
    result = []
    for i, (s, t) in enumerate(ordered):
        end = ordered[i + 1][0] if i + 1 < len(ordered) else duration
        if end <= s:
            continue
        result.append((s, end, t))
    return result


def merge_chapters(
    existing: List[Tuple[float, float, str]],
    new: List[Tuple[float, float, str]],
    duration: float,
) -> List[Tuple[float, float, str]]:
    combined = {}
    for s, _, t in existing:
        combined[int(round(s * 1000))] = (s, t)
    for s, _, t in new:
        combined[int(round(s * 1000))] = (s, t)  # new wins on collision
    ordered = sorted(combined.values(), key=lambda x: x[0])
    return rechain(ordered, duration)


# ---------------------------------------------------------------------------
# ffmetadata generation
# ---------------------------------------------------------------------------

def build_ffmetadata(chapters: List[Tuple[float, float, str]]) -> str:
    lines = [';FFMETADATA1']
    for start, end, title in chapters:
        lines.append('[CHAPTER]')
        lines.append('TIMEBASE=1/1000')
        lines.append(f'START={int(round(start * 1000))}')
        lines.append(f'END={int(round(end * 1000))}')
        safe = title.replace('\\', '\\\\').replace('=', '\\=').replace(';', '\\;')
        lines.append(f'title={safe}')
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def find_edl(video_path: str) -> Optional[str]:
    base = os.path.splitext(video_path)[0]
    for cand in (base + '.edl', base + '.EDL'):
        if os.path.exists(cand):
            return cand
    folder = os.path.dirname(os.path.abspath(video_path)) or '.'
    hits = glob.glob(os.path.join(folder, '*.edl')) + glob.glob(os.path.join(folder, '*.EDL'))
    if len(hits) == 1:
        return hits[0]
    return None


def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python markerinjector.py <video_file> [<edl_file>]")
        sys.exit(1)

    video_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(video_path):
        print(f"Error: video not found: {video_path}")
        sys.exit(1)

    edl_path = os.path.abspath(sys.argv[2]) if len(sys.argv) == 3 else find_edl(video_path)
    if not edl_path or not os.path.exists(edl_path):
        print("Error: no EDL found. Pass one explicitly or place '<video>.edl' next to the video.")
        sys.exit(1)

    print(f"Video: {video_path}")
    print(f"EDL:   {edl_path}")

    duration, fps = probe_video(video_path)
    print(f"Detected fps={fps:.3f}, duration={duration:.3f}s")

    markers = parse_edl(edl_path)
    if not markers:
        print("No markers found in EDL.")
        sys.exit(1)

    new_starts = sorted(
        ((timecode_to_seconds(tc, fps), name) for tc, name in markers),
        key=lambda x: x[0],
    )
    new_chapters = rechain(new_starts, duration)

    existing_chapters = probe_existing_chapters(video_path)

    if existing_chapters:
        mode = ask_chapter_mode(existing_chapters, new_chapters)
        if mode == 'quit':
            print("Aborted.")
            sys.exit(0)
        if mode == 'replace':
            chapters = new_chapters
        else:
            chapters = merge_chapters(existing_chapters, new_chapters, duration)
    else:
        chapters = new_chapters

    print(f"\nWriting {len(chapters)} chapter(s):")
    for s, e, t in chapters:
        print(f"  {s:8.3f}s -> {e:8.3f}s  {t or '(untitled)'}")

    metadata = build_ffmetadata(chapters)

    with tempfile.NamedTemporaryFile('w', suffix='.ffmeta', delete=False) as tmp:
        tmp.write(metadata)
        meta_path = tmp.name

    out_path = os.path.splitext(video_path)[0] + '_with_chapters' + os.path.splitext(video_path)[1]

    # Find old QuickTime chapter text tracks to drop
    drop_indices = find_chapter_track_indices(video_path)
    if drop_indices:
        print(f"\nDropping old chapter text stream(s): {drop_indices}")

    cmd = [
        'ffmpeg',
        '-hide_banner',
        '-i', video_path,
        '-i', meta_path,
        '-map', '0',
    ]
    for idx in drop_indices:
        cmd += ['-map', f'-0:{idx}']
    cmd += [
        '-map_metadata', '0',
        '-map_metadata', '1',
        '-map_chapters', '1',
        '-c', 'copy',
        '-y',
        out_path,
    ]

    print("\nRunning ffmpeg...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("ffmpeg failed:\n" + result.stderr)
            sys.exit(1)
    finally:
        os.unlink(meta_path)

    print(f"\nDone -> {out_path}")


if __name__ == '__main__':
    main()