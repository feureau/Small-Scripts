"""
# lutconvert.py

Convert LUT files between formats using `colour-science` with robust `.3dl`
auto-detection. This script is designed to work even when `colour-science`
does not ship a native 3DL reader (e.g., version 0.4.7).

IMPORTANT:
- This documentation block MUST always remain at the top of the file.
- It MUST be reviewed and updated with every future change to this script.

## Features
- Batch conversion with glob patterns.
- Auto-detects multiple `.3dl` variants without flags:
  - `LUT_3D_SIZE N` headers.
  - `3DLUT` headers.
  - Plain size lines (`33`, `17`, etc.).
  - Affinity-style grid lines (e.g., `0 64 128 ... 1023`).
  - Fallback by counting N^3 RGB triplets.
- Uses `colour-science` writers for output formats (`.cube`, `.csp`, `.spi1d`,
  `.spi3d`, `.spimtx`, `.vlt`, `.png` where supported).
- Optional verbose errors for diagnosis.

## Requirements
- Python 3.8+
- `colour-science`
- `numpy`

## Install (example)
```bash
pip install colour-science numpy
```

## Usage
```bash
python lutconvert.py <inputs...> <out_format>
```

### Examples
```bash
python lutconvert.py "*.3dl" cube
python lutconvert.py "C:\LUTs\*.3dl" cube
python lutconvert.py "in.3dl" cube --out-dir "C:\out"
python lutconvert.py "in.3dl" cube --verbose
```

## Arguments
- `inputs`: One or more files or glob patterns.
- `out_format`: Output format/extension (`cube`, `3dl`, `csp`, `spi1d`,
  `spi3d`, `spimtx`, `vlt`, `png`), depending on `colour-science` support.

## Options
- `--in-format`: Force input format if auto-detection fails for non-3dl types.
- `--out-dir`: Write outputs to a specific directory.
- `--reader`: Advanced: force a specific reader callable name.
- `--verbose`: Print detailed reader failure diagnostics.

## Notes on `.3dl` Autodetection
The script parses and normalizes `.3dl` data into a `colour.LUT3D` object:
- Input values are normalized to 0..1 if needed.
- Domain is inferred from the grid line when present, otherwise defaults to
  `[0, 1]` per channel.
- It assumes the file contains exactly N^3 RGB triplets for a 3D LUT.

## Exit Codes
- `0`: Success
- `1`: One or more files failed to convert
- `2`: No files matched the input patterns
"""

import argparse
import sys
import glob
from pathlib import Path

try:
    import colour
    import numpy as np
    import re
    try:
        from colour.io import read_LUT, write_LUT
    except Exception:
        from colour.io.luts import read_LUT, write_LUT
except ImportError:
    print("\n[!] ERROR: colour-science not found in this Python environment.")
    sys.exit(1)


def _iter_files(patterns):
    for pattern in patterns:
        matched = glob.glob(pattern)
        if matched:
            for f in matched:
                yield f
        else:
            yield pattern


def _normalize_format(fmt):
    if not fmt:
        return None
    fmt = fmt.strip().lower().lstrip(".")
    aliases = {
        "cube": "cube",
        "3dl": "3dl",
        "csp": "csp",
        "spi1d": "spi1d",
        "spi3d": "spi3d",
        "vlt": "vlt",
        "png": "png",
    }
    return aliases.get(fmt, fmt)


def _resolve_reader_hint(reader_hint):
    if not reader_hint:
        return None
    if callable(reader_hint):
        return reader_hint
    if isinstance(reader_hint, str):
        try:
            from colour.io import luts as luts_module
        except Exception:
            luts_module = None
        if luts_module is not None:
            reader = getattr(luts_module, reader_hint, None)
            if callable(reader):
                return reader
        try:
            from colour.io.luts import lut_3dl as lut_3dl_module
            reader = getattr(lut_3dl_module, reader_hint, None)
            if callable(reader):
                return reader
        except Exception:
            pass
    return None


def _get_reader_candidates(ext, reader_hint=None):
    candidates = []
    resolved_hint = _resolve_reader_hint(reader_hint)
    if resolved_hint:
        return [resolved_hint]

    try:
        from colour.io import luts as luts_module
    except Exception:
        luts_module = None

    if luts_module is not None:
        lut_readers = getattr(luts_module, "LUT_READERS", None)
        if isinstance(lut_readers, dict):
            ext = ext.lower().lstrip(".")
            if ext in lut_readers:
                candidates.extend(lut_readers[ext])

    if ext.lower().lstrip(".") == "3dl":
        try:
            from colour.io.luts.lut_3dl import read_LUT_Lustre
            candidates.append(read_LUT_Lustre)
        except Exception:
            pass

    return candidates


def _read_lut(path, in_format=None, reader_hint=None, verbose=False):
    if in_format:
        try:
            return read_LUT(path, in_format=in_format)
        except TypeError:
            return read_LUT(path)

    try:
        return read_LUT(path)
    except Exception as e:
        if verbose:
            print(f"Primary reader failed for {path}: {e}")

    ext = Path(path).suffix
    for reader in _get_reader_candidates(ext, reader_hint=reader_hint):
        try:
            return reader(path)
        except Exception as e:
            if verbose:
                print(f"Reader {getattr(reader, '__name__', reader)} failed for {path}: {e}")

    if ext.lower().lstrip(".") == "3dl":
        try:
            return _read_3dl_autodetect(path)
        except Exception as e:
            if verbose:
                print(f"Custom 3dl reader failed for {path}: {e}")

    raise RuntimeError(f"No suitable reader found for {path}")


_NUM_RE = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")


def _is_non_decreasing(values):
    return all(b >= a for a, b in zip(values, values[1:]))


def _parse_numeric_line(line):
    return [float(x) for x in _NUM_RE.findall(line)]


def _read_3dl_autodetect(path):
    raw_lines = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("#") or line.startswith("//") or line.startswith(";"):
                continue
            raw_lines.append(line)

    if not raw_lines:
        raise RuntimeError("Empty .3dl file")

    size = None
    grid = None
    data_start = 0

    for idx, line in enumerate(raw_lines):
        upper = line.upper()
        if upper.startswith("LUT_3D_SIZE"):
            nums = _parse_numeric_line(line)
            if nums:
                size = int(nums[-1])
                data_start = idx + 1
                break
        if upper.startswith("3DLUT"):
            data_start = idx + 1
            continue

    if size is None:
        for idx, line in enumerate(raw_lines):
            nums = _parse_numeric_line(line)
            if len(nums) == 1 and 2 <= nums[0] <= 256:
                size = int(nums[0])
                data_start = idx + 1
                break

    if size is None or grid is None:
        for idx, line in enumerate(raw_lines):
            nums = _parse_numeric_line(line)
            if len(nums) >= 2 and _is_non_decreasing(nums):
                grid = nums
                size = len(grid)
                data_start = idx + 1
                break

    if size is None:
        triplet_lines = [ln for ln in raw_lines if len(_parse_numeric_line(ln)) >= 3]
        n = len(triplet_lines)
        cube = round(n ** (1 / 3))
        if cube ** 3 == n and cube >= 2:
            size = cube
            data_start = raw_lines.index(triplet_lines[0])

    if size is None:
        raise RuntimeError("Unable to determine 3dl size/grid")

    values = []
    triplet_lines = []
    for line in raw_lines[data_start:]:
        nums = _parse_numeric_line(line)
        if len(nums) >= 3:
            triplet_lines.append(nums[:3])

    expected = size ** 3
    if len(triplet_lines) < expected:
        raise RuntimeError(f"Expected {expected} LUT entries, found {len(triplet_lines)}")

    for i in range(expected):
        values.append(tuple(triplet_lines[i]))

    values_arr = np.array(values, dtype=np.float32)
    vmin = float(values_arr.min())
    vmax = float(values_arr.max())

    if vmax > 1.0 or vmin < 0.0:
        scale = max(abs(vmin), abs(vmax)) or 1.0
        values_arr /= scale

    table = values_arr.reshape((size, size, size, 3))

    if grid is None:
        domain_min = 0.0
        domain_max = 1.0
    else:
        domain_min = float(min(grid))
        domain_max = float(max(grid))
        if domain_max != 0.0:
            domain_min /= domain_max
            domain_max = 1.0
        else:
            domain_min = 0.0
            domain_max = 1.0

    domain = np.array([[domain_min, domain_min, domain_min], [domain_max, domain_max, domain_max]])

    name = Path(path).stem
    try:
        lut = colour.LUT3D(table, name=name, domain=domain)
    except TypeError:
        lut = colour.LUT3D(table)

    return lut


def _write_lut(lut, out_path, out_format=None):
    if out_format:
        try:
            return write_LUT(lut, out_path, out_format=out_format)
        except TypeError:
            return write_LUT(lut, out_path)
    return write_LUT(lut, out_path)


def convert(args):
    out_format = _normalize_format(args.out_format)
    in_format = _normalize_format(args.in_format)

    files = list(_iter_files(args.inputs))
    if not files:
        print("No files matched.")
        return 2

    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    for f in files:
        try:
            lut = _read_lut(
                f,
                in_format=in_format,
                reader_hint=args.reader,
                verbose=args.verbose,
            )

            in_path = Path(f)
            out_ext = out_format if out_format else in_path.suffix.lstrip(".")
            out_name = f"{in_path.stem}.{out_ext}"
            out_path = (out_dir / out_name) if out_dir else in_path.with_suffix(f".{out_ext}")

            _write_lut(lut, str(out_path), out_format=out_format)
            print(f"Done: {in_path.name} -> {out_path.name}")
        except Exception as e:
            failures += 1
            print(f"Failed {f}: {e}")

    return 0 if failures == 0 else 1


def build_parser():
    p = argparse.ArgumentParser(
        description="Convert LUT files using colour-science (e.g., 3dl -> cube).",
    )
    p.add_argument("inputs", nargs="+", help="Input file(s) or glob patterns.")
    p.add_argument("out_format", help="Output format/extension (e.g., cube, 3dl, csp).")
    p.add_argument("--in-format", dest="in_format", help="Force input format.")
    p.add_argument("--out-dir", dest="out_dir", help="Output directory.")
    p.add_argument(
        "--reader",
        help="Force a specific reader callable name (advanced).",
    )
    p.add_argument("--verbose", action="store_true", help="Verbose error output.")
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    return convert(args)


if __name__ == "__main__":
    sys.exit(main())
