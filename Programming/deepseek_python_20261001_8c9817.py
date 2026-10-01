#!/usr/bin/env python3
"""
patch_transcribe_normtoken.py
-----------------------------
Fixes the "name '_norm_token' is not defined" error introduced by the
hanging-word patch. Promotes _norm_token to module scope so that
split_long_subtitle_segments() can use it.

Usage:
  python patch_transcribe_normtoken.py transcribe.py
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


ANCHOR = 'def _normalize_text_for_compare(text: str) -> str:'

INSERT = '''def _norm_token(t: str) -> str:
    """Lowercase and strip punctuation from a single token for comparison."""
    t = (t or "").strip().lower()
    t = re.sub(r"[^\\wÀ-ÖØ-öø-ÿ]", "", t)
    return t


def _normalize_text_for_compare(text: str) -> str:'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?", default="transcribe.py")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()

    target = Path(args.target).resolve()
    if not target.is_file():
        print(f"Error: {target} is not a file.")
        return 2

    src = target.read_text(encoding="utf-8")

    if "def _norm_token(t: str) -> str:" in src and src.count("def _norm_token") > 1:
        # One module-level + one nested -> already patched.
        pass
    if "\ndef _norm_token(t: str) -> str:" in src:
        print("Module-level _norm_token already present. Nothing to do.")
        return 0

    n = src.count(ANCHOR)
    if n != 1:
        print(f"Aborted: anchor found {n} time(s), expected 1.")
        return 1

    src = src.replace(ANCHOR, INSERT, 1)

    if not args.no_backup:
        backup = target.with_suffix(target.suffix + ".bak2")
        if not backup.exists():
            shutil.copy2(target, backup)
            print(f"Backup written: {backup}")

    target.write_text(src, encoding="utf-8")
    print(f"Patched: {target}")
    print("Added module-level _norm_token(). Re-run your transcription.")
    return 0


if __name__ == "__main__":
    sys.exit(main())