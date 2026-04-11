#!/usr/bin/env python3
"""
SUPRA MIDI/Audio Metadata Tool - extract, export, and rename MIDI and audio files.

Examples:
    python supra-mido.py "*.mid"
    python supra-mido.py -e "*.mid"
    python supra-mido.py --export-csv out.csv "*.mid"
    python supra-mido.py -r "*.mid"
    python supra-mido.py --rename --dry-run "*.mid"
    python supra-mido.py -e -r "*.mid"
    python supra-mido.py -r --xml merged_output.xml "*.mid"
    python supra-mido.py -r --xml merged_output.xml "*.wav"
    python supra-mido.py -r --xml merged_output.xml "*.mp3" "*.m4a"
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

try:
    import mido
except ImportError:
    print("Error: mido not installed. Run: pip install mido")
    sys.exit(1)

try:
    from tqdm import tqdm

    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

MIDI_EXTENSIONS = {".mid", ".midi"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aiff", ".aif", ".wma"}
ALL_SUPPORTED_EXTENSIONS = MIDI_EXTENSIONS | AUDIO_EXTENSIONS
MAX_FILENAME_LENGTH = 200
DEFAULT_RENAME_TEMPLATE = "{COMPOSER} - {PERFORMER} - {TITLE}"
DRUID_RE = re.compile(r"[a-z]{2}\d{3}[a-z]{2}\d{4}", re.IGNORECASE)


def extract_all_metadata(midi_path: Path) -> Dict[str, str]:
    """Return a dict of all @KEY: value pairs from a MIDI file."""
    metadata: Dict[str, str] = {"filename": str(midi_path)}
    try:
        mid = mido.MidiFile(midi_path)
        for track in mid.tracks:
            for msg in track:
                if msg.type == "text":
                    text = msg.text.strip()
                    if text.startswith("@") and ":" in text:
                        key, value = text.split(":", 1)
                        metadata[key.strip()] = html.unescape(value.strip())
    except Exception as exc:
        metadata["error"] = str(exc)
    return metadata


def extract_audio_metadata(audio_path: Path) -> Dict[str, str]:
    """Return minimal metadata for a non-MIDI audio file (filename only).

    The DRUID is inferred from the filename so that XML enrichment can
    supply COMPOSER / PERFORMER / TITLE later.
    """
    return {"filename": str(audio_path)}


def _clean_marc_text(value: str) -> str:
    cleaned = html.unescape((value or "").strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned.rstrip(" /:;,")


def _best_druid_from_text(text: str) -> str:
    match = DRUID_RE.search((text or "").lower())
    return match.group(0) if match else ""


def _infer_druid_from_path(path: Path) -> str:
    stem = path.stem
    if stem.lower().endswith("_exp"):
        stem = stem[:-4]
    found = _best_druid_from_text(stem)
    return found or stem.lower()


def _extract_datafields(record: ET.Element, tag: str) -> List[ET.Element]:
    out: List[ET.Element] = []
    for datafield in record.findall("./{*}datafield"):
        if datafield.attrib.get("tag") == tag:
            out.append(datafield)
    return out


def _subfield_values(datafield: ET.Element, code: str) -> List[str]:
    vals: List[str] = []
    for subfield in datafield.findall("./{*}subfield"):
        if subfield.attrib.get("code") == code:
            txt = _clean_marc_text(subfield.text or "")
            if txt:
                vals.append(txt)
    return vals


def _join_name(parts: Sequence[str]) -> str:
    joined = " ".join(part for part in parts if part)
    joined = re.sub(r"\s+", " ", joined).strip(" ,")
    return joined


def _extract_performer_from_record(record: ET.Element) -> str:
    # Prefer 700 entries explicitly marked as performer/instrumentalist/pianist.
    first_fallback = ""
    for field in _extract_datafields(record, "700"):
        a = (_subfield_values(field, "a") or [""])[0]
        d = (_subfield_values(field, "d") or [""])[0]
        e_all = [e.lower() for e in _subfield_values(field, "e")]
        candidate = _join_name([a, d])
        if not candidate:
            continue
        if not first_fallback:
            first_fallback = candidate
        if any(token in e for e in e_all for token in ("instrumentalist", "performer", "pianist")):
            return candidate

    if first_fallback:
        return first_fallback

    # Fallback to 511 performance note, taking artist before first comma.
    for field in _extract_datafields(record, "511"):
        a = (_subfield_values(field, "a") or [""])[0]
        if a:
            return _clean_marc_text(a.split(",")[0])
    return ""


def load_xml_name_index(xml_path: Path) -> Dict[str, Dict[str, str]]:
    """Load merged MARC XML and index likely naming fields by DRUID."""
    try:
        root = ET.parse(xml_path).getroot()
    except Exception as exc:
        print(f"Warning: failed to parse XML '{xml_path}': {exc}")
        return {}

    index: Dict[str, Dict[str, str]] = {}
    for record in root.findall(".//{*}record"):
        source = record.attrib.get("source", "")
        druid = _best_druid_from_text(source)
        if not druid:
            continue

        composer = ""
        fields_100 = _extract_datafields(record, "100")
        if fields_100:
            composer = _join_name([
                (_subfield_values(fields_100[0], "a") or [""])[0],
                (_subfield_values(fields_100[0], "d") or [""])[0],
            ])

        performer = _extract_performer_from_record(record)

        title = ""
        fields_245 = _extract_datafields(record, "245")
        if fields_245:
            f245 = fields_245[0]
            title = _clean_marc_text(" ".join(
                (_subfield_values(f245, "a") or [])
                + (_subfield_values(f245, "b") or [])
                + (_subfield_values(f245, "n") or [])
            ))
        if not title:
            fields_240 = _extract_datafields(record, "240")
            if fields_240:
                f240 = fields_240[0]
                title = _clean_marc_text(" ".join(_subfield_values(f240, "a") or []))

        index[druid.lower()] = {
            "@COMPOSER": composer,
            "@PERFORMER": performer,
            "@TITLE": title,
        }

    return index


def enrich_metadata_with_xml(meta: Dict[str, str], file_path: Path, xml_index: Dict[str, Dict[str, str]]) -> None:
    """Fill missing naming metadata from XML index when available."""
    if not xml_index:
        return

    druid = _best_druid_from_text(meta.get("@DRUID", "")) or _infer_druid_from_path(file_path)
    if not druid:
        return

    xml_meta = xml_index.get(druid.lower())
    if not xml_meta:
        return

    for key in ("@COMPOSER", "@PERFORMER", "@TITLE"):
        if not meta.get(key):
            value = _clean_marc_text(xml_meta.get(key, ""))
            if value:
                meta[key] = value


def sanitize_filename(name: str) -> str:
    """Remove invalid characters for Windows/Linux filenames."""
    cleaned = re.sub(r'[<>:"/\\|?*]', "", name).strip(". ")
    if len(cleaned) > MAX_FILENAME_LENGTH:
        cleaned = cleaned[:MAX_FILENAME_LENGTH].rstrip(". ")
    return cleaned or "untitled"


def _metadata_value(metadata: Dict[str, str], key: str) -> str:
    token = key.strip().upper()
    if not token:
        return ""
    lookup = token if token.startswith("@") else f"@{token}"
    return metadata.get(lookup, "").strip()


def _render_name_template(template: str, metadata: Dict[str, str]) -> str:
    def repl(match: re.Match[str]) -> str:
        return _metadata_value(metadata, match.group(1))

    rendered = re.sub(r"\{\s*([@A-Za-z0-9_]+)\s*\}", repl, template)
    rendered = re.sub(r"\s+", " ", rendered).strip(" -_.")
    return rendered


def generate_new_name(
    metadata: Dict[str, str],
    original_path: Path,
    name_format: str = DEFAULT_RENAME_TEMPLATE,
) -> str:
    """Generate a new filename based on metadata and naming template."""
    composer = _metadata_value(metadata, "COMPOSER")
    performer = _metadata_value(metadata, "PERFORMER")
    title = _metadata_value(metadata, "TITLE") or _metadata_value(metadata, "LABEL")
    druid = metadata.get("@DRUID", original_path.stem)

    # Keep old behavior that strips year tags from performer field.
    performer = re.sub(r"\s*\([0-9\-]+\)", "", performer).strip()

    if name_format == DEFAULT_RENAME_TEMPLATE:
        base = " - ".join(part for part in (composer, performer, title) if part)
    else:
        base = _render_name_template(name_format, metadata)

    if not base:
        base = druid

    return sanitize_filename(f"{base}{original_path.suffix}")


def make_unique_target_path(old_path: Path, requested_name: str) -> Path:
    """
    Resolve name collisions by appending " (N)".
    Returns old_path if requested name equals old filename.
    """
    target = old_path.with_name(requested_name)
    if target == old_path:
        return old_path
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    counter = 1
    while True:
        candidate = old_path.with_name(f"{stem} ({counter}){suffix}")
        if not candidate.exists() or candidate == old_path:
            return candidate
        counter += 1


def rename_single_file(
    meta: Dict[str, str],
    dry_run: bool = False,
    name_format: str = DEFAULT_RENAME_TEMPLATE,
) -> bool:
    """Rename one file. Returns True if renamed (or would rename)."""
    old_path = Path(meta["filename"])
    if not old_path.exists():
        print(f"  Missing file: {old_path}")
        return False
    if meta.get("error"):
        print(f"  Skipping {old_path.name}: metadata error ({meta['error']})")
        return False

    requested_name = generate_new_name(meta, old_path, name_format)
    new_path = make_unique_target_path(old_path, requested_name)
    if new_path == old_path:
        if name_format == DEFAULT_RENAME_TEMPLATE:
            has_any = any(
                _metadata_value(meta, key)
                for key in ("COMPOSER", "PERFORMER", "TITLE", "LABEL")
            )
            if not has_any:
                print(
                    f"  Skipping {old_path.name}: no COMPOSER/PERFORMER/TITLE metadata; kept original name."
                )
        return False

    if dry_run:
        print(f"  Would rename: {old_path.name} -> {new_path.name}")
        return True

    try:
        old_path.rename(new_path)
        print(f"  Renamed: {old_path.name} -> {new_path.name}")
        meta["filename"] = str(new_path)
        return True
    except Exception as exc:
        print(f"  Error renaming {old_path.name}: {exc}")
        return False


def _iter_with_progress(items: Sequence, desc: str):
    if HAS_TQDM:
        return tqdm(items, desc=desc, unit="file")
    print(f"{desc} ({len(items)} files)...")
    return items


def rename_files_sequential(
    file_paths: Sequence[Path],
    dry_run: bool = False,
    name_format: str = DEFAULT_RENAME_TEMPLATE,
    xml_index: Dict[str, Dict[str, str]] | None = None,
) -> int:
    """Rename files one by one, reading metadata on-demand."""
    renamed_count = 0
    iterator = _iter_with_progress(file_paths, "Renaming files")
    for file_path in iterator:
        if file_path.suffix.lower() in MIDI_EXTENSIONS:
            meta = extract_all_metadata(file_path)
        else:
            meta = extract_audio_metadata(file_path)
        enrich_metadata_with_xml(meta, file_path, xml_index or {})
        if rename_single_file(meta, dry_run, name_format):
            renamed_count += 1
    return renamed_count


def rename_files_from_metadata(
    metadata_list: Sequence[Dict[str, str]],
    dry_run: bool = False,
    name_format: str = DEFAULT_RENAME_TEMPLATE,
) -> int:
    """Rename files using pre-extracted metadata (for combined mode)."""
    renamed_count = 0
    iterator = _iter_with_progress(metadata_list, "Renaming files")
    for meta in iterator:
        if rename_single_file(meta, dry_run, name_format):
            renamed_count += 1
    return renamed_count


def print_metadata(metadata_list: Sequence[Dict[str, str]]) -> None:
    """Print metadata to console."""
    for meta in metadata_list:
        print(f"\n=== {meta['filename']} ===")
        for key, value in sorted(meta.items()):
            if key == "filename":
                continue
            print(f"  {key}: {value}")
        if len(meta) == 1:
            print("  No metadata found.")


def default_export_filename() -> str:
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return f"supra_metadata_{stamp}.csv"


def export_to_csv(metadata_list: Sequence[Dict[str, str]], output_file: str) -> None:
    """Write all metadata to CSV."""
    all_keys = set()
    for meta in metadata_list:
        all_keys.update(meta.keys())
    all_keys.discard("filename")
    all_keys = sorted(all_keys)

    output_path = Path(output_file).expanduser()
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path

    # Normalize output target so users always get a proper CSV filename.
    if output_path.exists() and output_path.is_dir():
        output_path = output_path / default_export_filename()
    elif str(output_file).endswith(("\\", "/")):
        output_path.mkdir(parents=True, exist_ok=True)
        output_path = output_path / default_export_filename()
    elif output_path.suffix == "":
        output_path = output_path.with_suffix(".csv")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # utf-8-sig helps LibreOffice/Excel reliably detect UTF-8.
    with output_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["filename"] + all_keys)
        for meta in metadata_list:
            row = [Path(meta["filename"]).name]
            for key in all_keys:
                row.append(meta.get(key, ""))
            writer.writerow(row)
    print(f"\nExported {len(metadata_list)} files to: {output_path}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract metadata from MIDI text events, export CSV, and/or rename MIDI/audio files."
    )
    parser.add_argument(
        "patterns",
        nargs="+",
        help='Glob pattern(s), e.g. "*.mid" "*.wav" "*.mp3". Quote patterns to avoid shell expansion.',
    )
    parser.add_argument("-e", "--export-csv", nargs="?", const="__AUTO__", metavar="PATH")
    parser.add_argument("-r", "--rename", action="store_true", help="Rename files using metadata.")
    parser.add_argument("--dry-run", action="store_true", help="Preview rename actions.")
    parser.add_argument(
        "--name-format",
        default=DEFAULT_RENAME_TEMPLATE,
        help='Rename template with metadata placeholders, e.g. "{COMPOSER} - {PERFORMER} - {TITLE}" or "{TITLE}".',
    )
    parser.add_argument(
        "--xml",
        metavar="PATH",
        help="Optional merged MARC XML file used to fill missing COMPOSER/PERFORMER/TITLE metadata.",
    )
    return parser.parse_args(argv)


def collect_files(patterns: Iterable[str]) -> List[Path]:
    """
    Resolve patterns relative to CWD, dedupe overlaps, and keep deterministic ordering.
    Accepts both MIDI and audio file extensions.
    """
    found: List[Path] = []
    seen: set[Path] = set()
    cwd = Path.cwd()

    for pattern in patterns:
        for filepath in cwd.glob(pattern):
            if not filepath.is_file():
                continue
            if filepath.suffix.lower() not in ALL_SUPPORTED_EXTENSIONS:
                continue
            resolved = filepath.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            found.append(resolved)

    found.sort(key=lambda p: str(p).lower())
    return found


def read_metadata_for_files(
    file_paths: Sequence[Path],
    xml_index: Dict[str, Dict[str, str]] | None = None,
) -> List[Dict[str, str]]:
    metadata_list: List[Dict[str, str]] = []
    midi_count = sum(1 for p in file_paths if p.suffix.lower() in MIDI_EXTENSIONS)
    audio_count = len(file_paths) - midi_count
    desc_parts = []
    if midi_count:
        desc_parts.append(f"{midi_count} MIDI")
    if audio_count:
        desc_parts.append(f"{audio_count} audio")
    desc = f"Reading {', '.join(desc_parts)} files" if desc_parts else "Reading files"
    iterator = _iter_with_progress(file_paths, desc)
    for file_path in iterator:
        if file_path.suffix.lower() in MIDI_EXTENSIONS:
            metadata = extract_all_metadata(file_path)
        else:
            metadata = extract_audio_metadata(file_path)
        enrich_metadata_with_xml(metadata, file_path, xml_index or {})
        metadata_list.append(metadata)
    return metadata_list


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    export_csv = args.export_csv is not None
    csv_output = default_export_filename() if args.export_csv == "__AUTO__" else args.export_csv

    print(f"Working directory: {Path.cwd()}")
    print(f"Patterns: {list(args.patterns)}")

    all_files = collect_files(args.patterns)
    midi_count = sum(1 for f in all_files if f.suffix.lower() in MIDI_EXTENSIONS)
    audio_count = len(all_files) - midi_count
    parts = []
    if midi_count:
        parts.append(f"{midi_count} MIDI")
    if audio_count:
        parts.append(f"{audio_count} audio")
    print(f"Found {' + '.join(parts) if parts else '0'} file(s).")
    if not all_files:
        print("No supported files found for the supplied pattern(s).")
        return 1

    xml_index: Dict[str, Dict[str, str]] = {}
    if args.xml:
        xml_path = Path(args.xml).expanduser()
        if not xml_path.is_absolute():
            xml_path = Path.cwd() / xml_path
        if not xml_path.exists():
            print(f"XML file not found: {xml_path}")
            return 1
        xml_index = load_xml_name_index(xml_path)
        print(f"Loaded {len(xml_index)} XML records from: {xml_path}")

    if args.rename and not export_csv:
        print(f"\n--- {'DRY RUN: ' if args.dry_run else ''}Renaming {len(all_files)} files ---")
        renamed = rename_files_sequential(all_files, args.dry_run, args.name_format, xml_index)
        print(f"{'Would rename' if args.dry_run else 'Renamed'} {renamed} files.")
        return 0

    metadata_list = read_metadata_for_files(all_files, xml_index)

    if export_csv:
        export_to_csv(metadata_list, csv_output)

    if args.rename:
        print(f"\n--- {'DRY RUN: ' if args.dry_run else ''}Renaming {len(metadata_list)} files ---")
        renamed = rename_files_from_metadata(metadata_list, args.dry_run, args.name_format)
        print(f"{'Would rename' if args.dry_run else 'Renamed'} {renamed} files.")

    if not export_csv and not args.rename:
        print_metadata(metadata_list)

    return 0


if __name__ == "__main__":
    sys.exit(main())
