#!/usr/bin/env python3
import sys
import glob
import shutil
from pathlib import Path

ALL_FILE_PATTERNS = {"*", "*.*"}


def collect_files(patterns):
    seen = set()
    files = []

    def add(path: Path):
        try:
            path = path.resolve()
        except OSError:
            return

        if path.is_file() and path not in seen:
            seen.add(path)
            files.append(path)

    for pattern in patterns:
        p = Path(pattern).expanduser()

        # Already-expanded file from PowerShell, drag/drop, etc.
        if p.is_file():
            add(p)
            continue

        # Windows CMD usually passes "*" literally.
        # Treat "*" and "*.*" as "all files in this folder".
        if p.name in ALL_FILE_PATTERNS:
            base = p.parent
            if base.is_dir():
                try:
                    entries = list(base.iterdir())
                except OSError:
                    continue

                for entry in sorted(entries, key=lambda x: x.name.lower()):
                    if entry.is_file():
                        add(entry)
                continue

        # Other wildcard patterns like file?.txt, [abc]*.txt, etc.
        for match in glob.glob(str(p)):
            match_path = Path(match)
            if match_path.is_file():
                add(match_path)

    return files


def make_target_dir(src: Path) -> Path:
    # Creates folder with the full filename.
    # Example: photo.jpg -> photo.jpg/photo.jpg
    #
    # If you want photo.jpg -> photo/photo.jpg instead,
    # change src.name below to src.stem.
    target = src.parent / src.name

    n = 1
    while target.exists():
        target = src.parent / f"{src.name} ({n})"
        n += 1

    return target


def main():
    patterns = sys.argv[1:] or ["*"]
    script_path = Path(__file__).resolve()

    files = collect_files(patterns)

    if not files:
        print("No files found.")
        return

    moved = 0

    for src in files:
        # Do not move this script itself if it happens to be in the folder.
        if src == script_path:
            continue

        target_dir = make_target_dir(src)

        try:
            target_dir.mkdir()
            shutil.move(str(src), str(target_dir / src.name))
            print(f"{src.name} -> {target_dir.name}/")
            moved += 1
        except (OSError, shutil.Error) as e:
            print(f"Failed to move {src}: {e}", file=sys.stderr)

    print(f"Moved {moved} file(s).")


if __name__ == "__main__":
    main()