#!/usr/bin/env python3
"""
vidsplit.py – Losslessly split video files into speech segments based on SRT subtitles.
Generates matching SRT files for each clip by default.
Glob patterns and recursive subfolder scanning are supported.
"""

import argparse
import csv
import glob
import logging
import os
import re
import subprocess
import statistics
import sys
from collections import namedtuple

# ----------------------------------------------------------------------
# Data structures
# ----------------------------------------------------------------------
Segment = namedtuple("Segment", "start end")
Clip = namedtuple("Clip", "index start end duration")
SRTBlock = namedtuple("SRTBlock", "index start end text")

# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
logging.basicConfig(format="%(message)s", level=logging.INFO)
log = logging.getLogger("vidsplit")


# ----------------------------------------------------------------------
# Utility functions
# ----------------------------------------------------------------------
def timestamp_to_seconds(ts: str) -> float:
    """Convert SRT timestamp HH:MM:SS,mmm to float seconds."""
    ts = ts.replace(".", ",")
    hours, minutes, sec_ms = ts.strip().split(":")
    seconds, millis = sec_ms.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000.0


def seconds_to_timestamp(secs: float) -> str:
    """Reverse: float seconds -> HH:MM:SS.mmm (comma for milliseconds)."""
    hours = int(secs // 3600)
    minutes = int((secs % 3600) // 60)
    seconds = secs % 60
    whole_sec = int(seconds)
    millis = int(round((seconds - whole_sec) * 1000))
    return f"{hours:02d}:{minutes:02d}:{whole_sec:02d},{millis:03d}"


def get_video_duration(video_path: str) -> float:
    """Use ffprobe to return duration in seconds."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode().strip()
        return float(out)
    except (subprocess.CalledProcessError, ValueError) as e:
        log.error("Failed to get duration for %s: %s", video_path, e)
        sys.exit(1)


def get_keyframes(video_path: str) -> list:
    """
    Extract video keyframe timestamps using ffprobe.
    This ensures we can snap our clips to keyframes so that SRT files perfectly
    sync with the resulting losslessly copied video.
    """
    cmd = [
        "ffprobe",
        "-loglevel", "error",
        "-select_streams", "v:0",
        "-show_entries", "packet=pts_time,dts_time,flags",
        "-of", "csv=print_section=0",
        video_path
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode()
        keyframes = []
        for line in out.splitlines():
            parts = line.strip().split(',')
            # Expecting pts_time, dts_time, flags
            if len(parts) >= 3 and 'K' in parts[2]:
                pts = parts[0]
                if not pts or pts == 'N/A':
                    pts = parts[1]
                try:
                    keyframes.append(float(pts))
                except ValueError:
                    pass
        return sorted(list(set(keyframes)))
    except Exception as e:
        log.warning("Failed to extract keyframes for %s: %s", video_path, e)
        return []


# ----------------------------------------------------------------------
# File discovery
# ----------------------------------------------------------------------
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv"}


def _has_glob_chars(s: str) -> bool:
    return any(c in s for c in "*?[")


def _collect_videos_from_dir(directory: str, recursive: bool) -> list:
    """Collect video file paths from a directory, optionally recursive."""
    candidates = []
    if recursive:
        for root, dirs, files in os.walk(directory):
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in VIDEO_EXTENSIONS:
                    candidates.append(os.path.join(root, fname))
    else:
        for fname in os.listdir(directory):
            ext = os.path.splitext(fname)[1].lower()
            if ext in VIDEO_EXTENSIONS:
                candidates.append(os.path.join(directory, fname))
    return candidates


def find_video_srt_pairs(args) -> list:
    """
    Return list of (video_path, srt_path) based on args.
    Supports positional video files, --dir, or current directory (recursive by default).
    Glob patterns are expanded automatically.
    """
    pairs = []
    candidates = []

    if args.dir:
        folder = args.dir
        if not os.path.isdir(folder):
            log.error("Directory not found: %s", folder)
            sys.exit(1)
        candidates = _collect_videos_from_dir(folder, recursive=not args.no_recursive)
    elif args.videos:
        for arg in args.videos:
            if _has_glob_chars(arg):
                matches = glob.glob(arg, recursive=True)
                if not matches:
                    log.warning("No files matched pattern: %s", arg)
                    continue
                for path in matches:
                    if os.path.isfile(path) and os.path.splitext(path)[1].lower() in VIDEO_EXTENSIONS:
                        candidates.append(path)
            else:
                if os.path.isfile(arg):
                    if os.path.splitext(arg)[1].lower() in VIDEO_EXTENSIONS:
                        candidates.append(arg)
                else:
                    log.warning("File not found: %s", arg)
    else:
        # current directory – recursive by default
        candidates = _collect_videos_from_dir(os.getcwd(), recursive=not args.no_recursive)

    if not candidates:
        log.error("No video files found.")
        sys.exit(1)

    # Deduplicate
    candidates = list(dict.fromkeys(candidates))

    for video in candidates:
        base = os.path.splitext(video)[0]
        srt_candidates = [base + ".srt", base + ".SRT"]
        srt_found = None
        for srt in srt_candidates:
            if os.path.isfile(srt):
                srt_found = srt
                break
        if srt_found:
            pairs.append((video, srt_found))
        else:
            log.warning("No matching SRT found for %s, skipping.", video)

    if not pairs:
        log.error("No video+SRT pairs discovered. Exiting.")
        sys.exit(1)

    return pairs


# ----------------------------------------------------------------------
# SRT parsing
# ----------------------------------------------------------------------
SRT_BLOCK_RE = re.compile(
    r"(\d+)\s*\n"
    r"(\d{2}:\d{2}:\d{2}[,\.]\d{1,3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{1,3})\s*\n"
    r"((?:.+\n?)+?)(?=\n\n|\n\Z|\Z)",
    re.MULTILINE
)


def parse_srt_blocks(srt_path: str) -> list:
    """
    Parse SRT file and return list of SRTBlock namedtuples.
    Each block has: index, start (seconds), end (seconds), text.
    """
    with open(srt_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    blocks = []
    for m in SRT_BLOCK_RE.finditer(content):
        idx = int(m.group(1))
        start = timestamp_to_seconds(m.group(2))
        end = timestamp_to_seconds(m.group(3))
        text = m.group(4).strip()
        if start >= end:
            log.warning("Invalid SRT interval in block %d: %s -> %s, skipping.", idx, start, end)
            continue
        blocks.append(SRTBlock(idx, start, end, text))

    return sorted(blocks, key=lambda b: b.start)


def parse_srt_intervals(srt_path: str) -> list:
    """
    Return list of (start_sec, end_sec) from SRT, for interval analysis.
    """
    blocks = parse_srt_blocks(srt_path)
    return [(b.start, b.end) for b in blocks]


# ----------------------------------------------------------------------
# Interval utilities
# ----------------------------------------------------------------------
def merge_intervals(intervals: list, max_gap: float) -> list:
    """Merge intervals that are within max_gap seconds of each other."""
    if not intervals:
        return []
    merged = [Segment(*intervals[0])]
    for start, end in intervals[1:]:
        last = merged[-1]
        if start - last.end <= max_gap:
            merged[-1] = Segment(last.start, max(last.end, end))
        else:
            merged.append(Segment(start, end))
    return merged


def add_buffer(segments: list, buffer_sec: float, total_duration: float) -> list:
    """Add buffer before and after each segment, clipped to video bounds."""
    buffered = []
    for seg in segments:
        new_start = max(0.0, seg.start - buffer_sec)
        new_end = min(total_duration, seg.end + buffer_sec)
        buffered.append(Segment(new_start, new_end))
    return buffered


def merge_overlaps(segments: list) -> list:
    """Merge segments that overlap or touch (gap ≤ 0)."""
    return merge_intervals(segments, 0.0)


# ----------------------------------------------------------------------
# Auto‑tune parameters
# ----------------------------------------------------------------------
def auto_tune(intervals: list) -> tuple:
    """
    Return (merge_gap, buffer) based on subtitle statistics.
    """
    if not intervals:
        return 2.0, 2.0

    blocks = merge_intervals(intervals, 0.0)

    gaps = []
    for i in range(1, len(blocks)):
        g = blocks[i].start - blocks[i-1].end
        if g > 0:
            gaps.append(g)

    durations = [b.end - b.start for b in blocks]

    if len(gaps) >= 4:
        sorted_gaps = sorted(gaps)
        idx = int((len(sorted_gaps) - 1) * 0.75)
        p75 = sorted_gaps[idx]
        auto_gap = max(1.0, min(5.0, p75))
    else:
        auto_gap = 2.0

    if durations:
        median_dur = statistics.median(durations)
        auto_buf = median_dur * 0.5
        auto_buf = max(1.0, min(3.0, auto_buf))
    else:
        auto_buf = 2.0

    return auto_gap, auto_buf


# ----------------------------------------------------------------------
# Splitting engine
# ----------------------------------------------------------------------
def build_clips(intervals, merge_gap, buffer_sec, total_duration, keyframes=None):
    if not intervals:
        return []

    if merge_gap > 0:
        speech = merge_intervals(intervals, merge_gap)
    else:
        speech = [Segment(*iv) for iv in intervals]

    buffered = add_buffer(speech, buffer_sec, total_duration)

    # Snap to the nearest preceding keyframe to align `-c copy` behavior
    # with the timestamp logic mapped to our subtitles.
    if keyframes:
        snapped = []
        for seg in buffered:
            start = seg.start
            best_kf = 0.0
            for kf in keyframes:
                if kf <= start:
                    best_kf = kf
                else:
                    break
            snapped.append(Segment(best_kf, seg.end))
        buffered = snapped

    final_segments = merge_overlaps(buffered)

    clips = []
    for idx, seg in enumerate(final_segments, 1):
        dur = seg.end - seg.start
        clips.append(Clip(idx, seg.start, seg.end, dur))
    return clips


def run_ffmpeg_split(video_path, clips, output_dir, basename, ext):
    for clip in clips:
        out_name = f"{basename}_speech_{clip.index:03d}{ext}"
        out_path = os.path.join(output_dir, out_name)
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(clip.start),
            "-to", str(clip.end),
            "-i", video_path,
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            out_path,
        ]
        log.info("  Clip %d/%d: %s", clip.index, len(clips), out_name)
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            log.error("ffmpeg failed for clip %d:\n%s", clip.index, e.stderr.decode())
            sys.exit(1)


# ----------------------------------------------------------------------
# SRT splitting for clips
# ----------------------------------------------------------------------
def split_srt_for_video(srt_path, clips, output_dir, basename):
    blocks = parse_srt_blocks(srt_path)
    if not blocks:
        return

    for clip in clips:
        clip_entries = []
        for block in blocks:
            s = max(block.start, clip.start)
            e = min(block.end, clip.end)
            if s < e:
                new_start = s - clip.start
                new_end = e - clip.start
                clip_entries.append((new_start, new_end, block.text))

        out_name = f"{basename}_speech_{clip.index:03d}.srt"
        out_path = os.path.join(output_dir, out_name)

        with open(out_path, "w", encoding="utf-8") as f:
            for idx, (start, end, text) in enumerate(clip_entries, 1):
                f.write(f"{idx}\n")
                f.write(f"{seconds_to_timestamp(start)} --> {seconds_to_timestamp(end)}\n")
                f.write(f"{text}\n\n")

        if clip_entries:
            log.info("    SRT written: %s (%d entries)", out_name, len(clip_entries))
        else:
            open(out_path, "w").close()
            log.info("    SRT written: %s (empty)", out_name)


# ----------------------------------------------------------------------
# CSV output
# ----------------------------------------------------------------------
def write_csv(csv_path, all_plans):
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["source_video", "output_clip", "start_seconds", "end_seconds",
                          "start_timecode", "end_timecode"])
        for video_path, clips, _, _ in all_plans:
            base = os.path.splitext(os.path.basename(video_path))[0]
            ext = os.path.splitext(video_path)[1]
            for clip in clips:
                out_name = f"{base}_speech_{clip.index:03d}{ext}"
                writer.writerow([
                    video_path,
                    out_name,
                    f"{clip.start:.3f}",
                    f"{clip.end:.3f}",
                    seconds_to_timestamp(clip.start),
                    seconds_to_timestamp(clip.end),
                ])


# ----------------------------------------------------------------------
# Main CLI
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Losslessly split video into speech clips using SRT subtitles. "
                    "Generates matching SRT files by default. "
                    "Glob patterns and recursive subfolder scanning are supported."
    )
    parser.add_argument("videos", nargs="*", help="Video files (or glob patterns).")
    parser.add_argument("--dir", help="Process all videos in this directory.")
    parser.add_argument(
        "--merge-gap", type=float, default=None,
        help="Max silence (seconds) to merge adjacent subtitles. Overrides auto.",
    )
    parser.add_argument(
        "--buffer", type=float, default=None,
        help="Seconds to add before/after each speech segment. Overrides auto.",
    )
    parser.add_argument(
        "--keep-silence", action="store_true",
        help="Treat every subtitle line as separate speech (skip merging).",
    )
    parser.add_argument(
        "--output-dir", default="split_output",
        help="Directory for output clips (default: ./split_output).",
    )
    parser.add_argument(
        "--no-recursive", action="store_true",
        help="Do not scan subdirectories when processing --dir or current folder.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Only print plan, do not split.",
    )
    parser.add_argument(
        "--yes", "-y", action="store_true",
        help="Skip confirmation prompt and execute splitting.",
    )
    parser.add_argument(
        "--csv", nargs="?", const="split_manifest.csv", default=None,
        help="Write CSV summary of clips. Optional filename (default: split_manifest.csv).",
    )
    parser.add_argument(
        "--no-srt", action="store_true",
        help="Do not generate accompanying SRT files for clips.",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging.")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    pairs = find_video_srt_pairs(args)

    os.makedirs(args.output_dir, exist_ok=True)

    all_plans = []

    for video, srt in pairs:
        log.info("Processing: %s", video)
        intervals = parse_srt_intervals(srt)
        if not intervals:
            log.warning("No valid subtitle intervals in %s, skipping.", srt)
            continue

        if args.merge_gap is not None:
            merge_gap = args.merge_gap
        else:
            auto_gap, auto_buf = auto_tune(intervals)
            merge_gap = auto_gap

        if args.buffer is not None:
            buffer_sec = args.buffer
        else:
            if args.merge_gap is None:
                buffer_sec = auto_buf
            else:
                _, auto_buf = auto_tune(intervals)
                buffer_sec = auto_buf

        if args.keep_silence:
            merge_gap = 0.0
            log.info("  --keep-silence: using each subtitle line as separate speech.")

        log.info("  Merge gap: %.1fs, Buffer: %.1fs", merge_gap, buffer_sec)

        dur = get_video_duration(video)
        
        # New Step: Extract keyframes to avoid desync
        log.info("  Extracting keyframes to sync SRT with copied video...")
        keyframes = get_keyframes(video)
        if not keyframes:
            log.warning("    No keyframes found. Synchronization might be slightly off.")

        clips = build_clips(intervals, merge_gap, buffer_sec, dur, keyframes=keyframes)

        if not clips:
            log.warning("  No speech segments produced, skipping.")
            continue

        log.info("  Cutting plan for %s:", os.path.basename(video))
        for c in clips:
            log.info("    Clip %2d: %s -> %s  (%.1fs)",
                     c.index, seconds_to_timestamp(c.start),
                     seconds_to_timestamp(c.end), c.duration)
        log.info("  Total clips: %d", len(clips))

        all_plans.append((video, clips, merge_gap, buffer_sec))

    if not all_plans:
        log.info("Nothing to do.")
        return

    if args.csv:
        csv_path = args.csv if isinstance(args.csv, str) else "split_manifest.csv"
        if not os.path.dirname(csv_path):
            csv_path = os.path.join(args.output_dir, csv_path)
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        write_csv(csv_path, all_plans)
        log.info("CSV written to %s", csv_path)

    if args.dry_run:
        log.info("Dry run complete. No files were split.")
        return

    if not args.yes:
        response = input("Proceed with splitting? [y/N]: ").strip().lower()
        if response not in ("y", "yes"):
            log.info("Aborted by user.")
            return

    for video, clips, _, _ in all_plans:
        base = os.path.splitext(os.path.basename(video))[0]
        ext = os.path.splitext(video)[1]
        log.info("Splitting %s...", os.path.basename(video))

        run_ffmpeg_split(video, clips, args.output_dir, base, ext)

        if not args.no_srt:
            srt_path = next(srt for v, srt in pairs if v == video)
            split_srt_for_video(srt_path, clips, args.output_dir, base)

    log.info("All done. Clips saved to %s", args.output_dir)


if __name__ == "__main__":
    main()