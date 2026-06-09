#!/usr/bin/env python3

import os
import sys
import json
import fnmatch
import argparse
import subprocess

DEFAULT_PATTERN = "*.[Mm][Pp]4|*.[Mm][Kk][Vv]|*.[Aa][Vv][Ii]|*.[Mm][Oo][Vv]|*.[Ww][Ee][Bb][Mm]|*.[Tt][Ss]"


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Generate FFprobe reports for Resolve proxy debugging."
    )

    parser.add_argument(
        "pattern",
        nargs="?",
        default=DEFAULT_PATTERN,
        help="Input file pattern."
    )

    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare source files against proxies in sibling Proxy folders."
    )

    return parser.parse_args()


def find_video_files_recursive(base_dir, pattern):
    use_default = (pattern == DEFAULT_PATTERN)

    found = []
    skip_dirs = {"proxy", "input", "output", "ffprobe"}

    for dirpath, dirnames, filenames in os.walk(base_dir):
        dirnames[:] = [
            d for d in dirnames
            if d.lower() not in skip_dirs
        ]

        for fname in filenames:

            if use_default:
                if os.path.splitext(fname)[1].lower() in {
                    ".mp4",
                    ".mkv",
                    ".avi",
                    ".mov",
                    ".webm",
                    ".ts"
                }:
                    found.append(os.path.join(dirpath, fname))
            else:
                if fnmatch.fnmatch(fname, pattern):
                    found.append(os.path.join(dirpath, fname))

    return found


def ffprobe_json(filepath):

    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        "-show_chapters",
        "-show_programs",
        filepath
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    return json.loads(result.stdout)


def extract_resolve_summary(data):

    summary = {
        "format": {},
        "video_streams": [],
        "audio_streams": [],
        "data_streams": []
    }

    fmt = data.get("format", {})

    summary["format"] = {
        "filename": fmt.get("filename"),
        "format_name": fmt.get("format_name"),
        "duration": fmt.get("duration"),
        "size": fmt.get("size"),
        "bit_rate": fmt.get("bit_rate"),
        "tags": fmt.get("tags", {})
    }

    for stream in data.get("streams", []):

        codec_type = stream.get("codec_type")

        item = {
            "index": stream.get("index"),
            "codec_name": stream.get("codec_name"),
            "codec_tag_string": stream.get("codec_tag_string"),
            "codec_tag": stream.get("codec_tag"),
            "codec_type": codec_type,
            "time_base": stream.get("time_base"),
            "start_time": stream.get("start_time"),
            "duration": stream.get("duration"),
            "tags": stream.get("tags", {})
        }

        if codec_type == "video":
            item.update({
                "width": stream.get("width"),
                "height": stream.get("height"),
                "pix_fmt": stream.get("pix_fmt"),
                "field_order": stream.get("field_order"),
                "r_frame_rate": stream.get("r_frame_rate"),
                "avg_frame_rate": stream.get("avg_frame_rate")
            })

            summary["video_streams"].append(item)

        elif codec_type == "audio":
            item.update({
                "sample_rate": stream.get("sample_rate"),
                "channels": stream.get("channels"),
                "channel_layout": stream.get("channel_layout")
            })

            summary["audio_streams"].append(item)

        else:
            summary["data_streams"].append(item)

    return summary


def write_json_report(video_file):

    print(f"Probing: {video_file}")

    report_dir = os.path.join(
        os.path.dirname(video_file),
        "ffprobe"
    )

    os.makedirs(report_dir, exist_ok=True)

    basename = os.path.splitext(
        os.path.basename(video_file)
    )[0]

    output_json = os.path.join(
        report_dir,
        basename + ".json"
    )

    try:
        raw_data = ffprobe_json(video_file)

        report = {
            "summary": extract_resolve_summary(raw_data),
            "full_ffprobe": raw_data
        }

        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        print(f"  -> {output_json}")

        return output_json

    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def compare_dicts(a, b, path=""):

    differences = []

    keys = set(a.keys()) | set(b.keys())

    for key in sorted(keys):

        new_path = f"{path}.{key}" if path else key

        if key not in a:
            differences.append(
                f"MISSING IN SOURCE : {new_path}"
            )
            continue

        if key not in b:
            differences.append(
                f"MISSING IN PROXY  : {new_path}"
            )
            continue

        av = a[key]
        bv = b[key]

        if isinstance(av, dict) and isinstance(bv, dict):
            differences.extend(
                compare_dicts(av, bv, new_path)
            )
        else:
            if av != bv:
                differences.append(
                    f"DIFFERENT: {new_path}\n"
                    f"    SOURCE: {av}\n"
                    f"    PROXY : {bv}"
                )

    return differences


def compare_proxy(source_file):

    source_dir = os.path.dirname(source_file)

    basename = os.path.splitext(
        os.path.basename(source_file)
    )[0]

    proxy_file = os.path.join(
        source_dir,
        "Proxy",
        basename + ".mov"
    )

    if not os.path.exists(proxy_file):
        return

    print(f"\nComparing:")
    print(f"  SOURCE: {source_file}")
    print(f"  PROXY : {proxy_file}")

    try:

        source_data = extract_resolve_summary(
            ffprobe_json(source_file)
        )

        proxy_data = extract_resolve_summary(
            ffprobe_json(proxy_file)
        )

        differences = compare_dicts(
            source_data,
            proxy_data
        )

        report_dir = os.path.join(
            source_dir,
            "ffprobe"
        )

        os.makedirs(report_dir, exist_ok=True)

        report_file = os.path.join(
            report_dir,
            basename + ".diff.txt"
        )

        with open(report_file, "w", encoding="utf-8") as f:

            if differences:
                f.write(
                    "\n\n".join(differences)
                )
            else:
                f.write("NO DIFFERENCES FOUND")

        print(f"  -> {report_file}")

    except Exception as e:
        print(f"  ERROR: {e}")


def main():

    args = parse_arguments()

    base_dir = os.getcwd()

    files = find_video_files_recursive(
        base_dir,
        args.pattern
    )

    if not files:
        print("No video files found.")
        sys.exit(1)

    files.sort()

    print(f"Found {len(files)} files")

    for file in files:
        write_json_report(file)

    if args.compare:
        print("\nRunning comparisons...")

        for file in files:
            compare_proxy(file)

    print("\nDone.")


if __name__ == "__main__":
    main()