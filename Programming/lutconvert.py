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
- Reads/writes Hald CLUT PNGs with proper 3D mapping and optional resampling.
- Optional color space and white point transforms for LUT data.
- Optional verbose errors for diagnosis.

## Requirements
- Python 3.8+
- `colour-science`
- `numpy`
- `Pillow` (for Hald CLUT PNG)

## Install (example)
```bash
pip install colour-science numpy pillow
```

## Usage
```bash
python lutconvert.py <inputs...> <out_format>
```

### Examples
```bash
python lutconvert.py "*.3dl" cube
python lutconvert.py "C:\\LUTs\\*.3dl" cube
python lutconvert.py "in.3dl" cube --out-dir "C:\\out"
python lutconvert.py "in.3dl" cube --verbose
python lutconvert.py "hald.png" cube
python lutconvert.py "in.cube" hald --hald-level 8
python lutconvert.py "in.cube" hald --color-space rec709 --white-point D65
```

## Arguments
- `inputs`: One or more files or glob patterns.
- `out_format`: Output format/extension (`cube`, `3dl`, `csp`, `spi1d`,
  `spi3d`, `spimtx`, `vlt`, `png`, `hald`), depending on `colour-science`
  support.

## Options
- `--in-format`: Force input format if auto-detection fails for non-3dl types.
- `--out-dir`: Write outputs to a specific directory.
- `--reader`: Advanced: force a specific reader callable name.
- `--verbose`: Print detailed reader failure diagnostics.
- `--hald-level`: Hald CLUT level to write (required if LUT size isn't a square).
- `-c`: Prompt for target color space.
- `--color-space`: Target color space (any `colour.RGB_COLOURSPACES` name).
- `-w`: Prompt for target white point.
- `--white-point`: Target white point (D55/D60/D65 or Kelvin).
- `--source-color-space`: Source color space for LUT values (any `colour.RGB_COLOURSPACES` name).
- `--source-white-point`: Source white point override (D55/D60/D65 or Kelvin).

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
    from PIL import Image
    try:
        from colour.io import read_LUT, write_LUT
    except Exception:
        from colour.io.luts import read_LUT, write_LUT
except ImportError:
    print("\n[!] ERROR: Required dependencies not found (colour-science, numpy, Pillow).")
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
        "hald": "hald",
        "haldclut": "hald",
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
    if in_format in ("hald", "haldclut"):
        return _read_haldclut(path)

    if in_format:
        try:
            return read_LUT(path, in_format=in_format)
        except TypeError:
            return read_LUT(path)

    try:
        if Path(path).suffix.lower() == ".png":
            return _read_haldclut(path)
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


def _is_perfect_square(n):
    root = int(round(n ** 0.5))
    return root * root == n, root


def _infer_hald_size(image_size):
    # For Hald CLUT: image size = L^3 x L^3, cube size = L^2.
    cube_size = int(round(image_size ** (2.0 / 3.0)))
    if cube_size <= 1:
        raise RuntimeError("Invalid Hald CLUT image size")
    if cube_size ** 3 != image_size * image_size:
        raise RuntimeError("Image is not a valid Hald CLUT square")
    is_sq, level = _is_perfect_square(cube_size)
    if not is_sq:
        raise RuntimeError("Invalid Hald CLUT: cube size is not a perfect square")
    return cube_size, level


def _read_haldclut(path):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    if w != h:
        raise RuntimeError("Hald CLUT image must be square")
    cube_size, _level = _infer_hald_size(w)

    arr = np.asarray(img, dtype=np.float32) / 255.0
    flat = arr.reshape((w * h, 3))
    table = np.empty((cube_size, cube_size, cube_size, 3), dtype=np.float32)

    for i in range(cube_size ** 3):
        r = i % cube_size
        g = (i // cube_size) % cube_size
        b = i // (cube_size * cube_size)
        table[r, g, b] = flat[i]

    name = Path(path).stem
    try:
        lut = colour.LUT3D(table, name=name, domain=np.array([[0, 0, 0], [1, 1, 1]]))
    except TypeError:
        lut = colour.LUT3D(table)
    return lut


def _resample_lut3d(lut, new_size):
    table = np.asarray(lut.table, dtype=np.float32)
    src = table.shape[0]
    if src == new_size:
        return table

    scale = (src - 1) / max(new_size - 1, 1)
    dst = np.empty((new_size, new_size, new_size, 3), dtype=np.float32)

    for b in range(new_size):
        bz = b * scale
        b0 = int(np.floor(bz))
        b1 = min(b0 + 1, src - 1)
        wb = bz - b0
        for g in range(new_size):
            gy = g * scale
            g0 = int(np.floor(gy))
            g1 = min(g0 + 1, src - 1)
            wg = gy - g0
            for r in range(new_size):
                rx = r * scale
                r0 = int(np.floor(rx))
                r1 = min(r0 + 1, src - 1)
                wr = rx - r0

                c000 = table[r0, g0, b0]
                c100 = table[r1, g0, b0]
                c010 = table[r0, g1, b0]
                c110 = table[r1, g1, b0]
                c001 = table[r0, g0, b1]
                c101 = table[r1, g0, b1]
                c011 = table[r0, g1, b1]
                c111 = table[r1, g1, b1]

                c00 = c000 * (1 - wr) + c100 * wr
                c10 = c010 * (1 - wr) + c110 * wr
                c01 = c001 * (1 - wr) + c101 * wr
                c11 = c011 * (1 - wr) + c111 * wr

                c0 = c00 * (1 - wg) + c10 * wg
                c1 = c01 * (1 - wg) + c11 * wg

                dst[r, g, b] = c0 * (1 - wb) + c1 * wb

    return dst


def _write_haldclut(lut, out_path, level=None):
    table = np.asarray(lut.table, dtype=np.float32)
    if table.ndim != 4 or table.shape[0] != table.shape[1] or table.shape[0] != table.shape[2]:
        raise RuntimeError("Hald CLUT requires a 3D LUT with equal dimensions")
    cube_size = table.shape[0]

    is_sq, inferred_level = _is_perfect_square(cube_size)
    if is_sq:
        level = inferred_level
    else:
        if not level:
            raise RuntimeError("Hald CLUT level required for non-square LUT sizes")
        if level < 2:
            raise RuntimeError("Hald CLUT level must be >= 2")
        new_size = level * level
        table = _resample_lut3d(lut, new_size)
        cube_size = new_size

    img_size = level ** 3
    flat = np.empty((cube_size ** 3, 3), dtype=np.float32)
    for i in range(cube_size ** 3):
        r = i % cube_size
        g = (i // cube_size) % cube_size
        b = i // (cube_size * cube_size)
        flat[i] = table[r, g, b]

    img = np.clip(flat.reshape((img_size, img_size, 3)), 0.0, 1.0)
    img8 = (img * 255.0 + 0.5).astype(np.uint8)
    Image.fromarray(img8, mode="RGB").save(out_path)


def _write_lut(lut, out_path, out_format=None):
    if out_format in ("hald", "haldclut"):
        return _write_haldclut(lut, out_path, level=None)
    if out_format:
        try:
            return write_LUT(lut, out_path, out_format=out_format)
        except TypeError:
            return write_LUT(lut, out_path)
    return write_LUT(lut, out_path)


def _resolve_colourspace(name):
    if not name:
        raise RuntimeError("Color space name is required")
    name = _resolve_colourspace_alias(name)
    key = name.strip().lower().replace("_", "-")
    aliases = {
        "srgb": "sRGB",
        "rec709": "ITU-R BT.709",
        "bt709": "ITU-R BT.709",
        "rec2020": "ITU-R BT.2020",
        "bt2020": "ITU-R BT.2020",
        "p3-d65": "P3-D65",
        "acescg": "ACEScg",
    }

    spaces = getattr(colour, "RGB_COLOURSPACES", {})
    if not spaces:
        raise RuntimeError("colour-science RGB colour spaces not available")

    if key in aliases and aliases[key] in spaces:
        return spaces[aliases[key]]

    lower_map = {k.lower(): k for k in spaces.keys()}
    if key in lower_map:
        return spaces[lower_map[key]]

    if key == "p3-d65":
        for k in spaces.keys():
            lk = k.lower()
            if "p3" in lk and "d65" in lk:
                return spaces[k]
            if "display p3" in lk:
                return spaces[k]

    raise RuntimeError(f"Unsupported color space: {name}")


def _resolve_colourspace_alias(name):
    if not name:
        return name
    key = name.strip().lower().replace("_", "-")
    aliases = {
        "srgb": "sRGB",
        "rec709": "ITU-R BT.709",
        "bt709": "ITU-R BT.709",
        "rec2020": "ITU-R BT.2020",
        "bt2020": "ITU-R BT.2020",
        "p3-d65": "P3-D65",
        "p3d65": "P3-D65",
        "display-p3": "Display P3",
        "acescg": "ACEScg",
        "acescct": "ACEScct",
        "acescc": "ACEScc",
        "aces2065-1": "ACES2065-1",
        "arri-logc3": "ARRI Wide Gamut 3",
        "arri-wide-gamut-3": "ARRI Wide Gamut 3",
        "arri-wide-gamut-4": "ARRI Wide Gamut 4",
        "dci-p3": "DCI-P3",
        "dci-p3-p": "DCI-P3-P",
        "dwg": "DaVinci Wide Gamut",
        "davinci-wide-gamut": "DaVinci Wide Gamut",
        "redwidegamutrgb": "REDWideGamutRGB",
        "s-gamut": "S-Gamut",
        "s-gamut3": "S-Gamut3",
        "s-gamut3cine": "S-Gamut3.Cine",
        "venice-s-gamut3": "Venice S-Gamut3",
        "venice-s-gamut3cine": "Venice S-Gamut3.Cine",
    }
    return aliases.get(key, name)


def _white_point_from_kelvin(kelvin):
    if kelvin < 1000 or kelvin > 40000:
        raise RuntimeError("Kelvin value must be between 1000 and 40000")
    return colour.CCT_to_xy(kelvin)


def _parse_white_point(value):
    if not value:
        return None
    val = value.strip().upper()
    try:
        illuminants = colour.CCS_ILLUMINANTS.get(
            "CIE 1931 2 Degree Standard Observer", {}
        )
        if val in illuminants:
            return illuminants[val]
    except Exception:
        pass

    if val.startswith("D") and val[1:].isdigit():
        return _white_point_from_kelvin(float(val[1:]) * 100.0)

    try:
        return _white_point_from_kelvin(float(value))
    except Exception as exc:
        raise RuntimeError(f"Invalid white point: {value}") from exc


def _with_whitepoint(cs, whitepoint_xy, label):
    primaries = cs.primaries
    try:
        from colour.models.rgb import normalised_primary_matrix
    except Exception as exc:
        raise RuntimeError("normalised_primary_matrix not available in colour-science") from exc

    try:
        rgb_cls = colour.RGB_Colourspace
    except Exception:
        from colour.models import RGB_Colourspace as rgb_cls

    m_rgb_to_xyz = normalised_primary_matrix(primaries, whitepoint_xy)
    m_xyz_to_rgb = np.linalg.inv(m_rgb_to_xyz)
    return rgb_cls(
        name=f"{cs.name} ({label})",
        primaries=primaries,
        whitepoint=whitepoint_xy,
        whitepoint_name=label,
        matrix_RGB_to_XYZ=m_rgb_to_xyz,
        matrix_XYZ_to_RGB=m_xyz_to_rgb,
        cctf_encoding=cs.cctf_encoding,
        cctf_decoding=cs.cctf_decoding,
    )


def _transform_lut_color_space(lut, src_name, dst_name, src_white_point=None, dst_white_point=None):
    table = np.asarray(lut.table, dtype=np.float32)
    if table.ndim != 4 or table.shape[3] != 3:
        raise RuntimeError("Color space transform requires a 3D LUT")

    src_cs = _resolve_colourspace(src_name)
    dst_cs = _resolve_colourspace(dst_name)

    if src_white_point is not None:
        src_cs = _with_whitepoint(src_cs, src_white_point, "custom white point")
    if dst_white_point is not None:
        dst_cs = _with_whitepoint(dst_cs, dst_white_point, "custom white point")

    if src_cs.cctf_decoding is not None:
        linear = src_cs.cctf_decoding(table)
    else:
        linear = table

    converted = colour.RGB_to_RGB(
        linear,
        src_cs,
        dst_cs,
        chromatic_adaptation_transform="Bradford",
    )

    if dst_cs.cctf_encoding is not None:
        encoded = dst_cs.cctf_encoding(converted)
    else:
        encoded = converted

    encoded = np.clip(encoded, 0.0, 1.0)

    try:
        return colour.LUT3D(encoded, name=getattr(lut, "name", None), domain=lut.domain)
    except Exception:
        return colour.LUT3D(encoded)


def _prompt_nonempty(label):
    while True:
        value = input(label).strip()
        if value:
            return value


def _prompt_optional(label):
    return input(label).strip()


def _prompt_choice(label, options, allow_blank=False, blank_value="", normalize=None):
    print(label)
    for idx, opt in enumerate(options, start=1):
        print(f"  {idx}. {opt}")
    while True:
        choice = input("Select by number or name: ").strip()
        if not choice:
            if allow_blank:
                return blank_value
            continue
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        normalized_choice = normalize(choice) if normalize else choice
        lowered = normalized_choice.lower()
        for opt in options:
            normalized_opt = normalize(opt) if normalize else opt
            if lowered == normalized_opt.lower():
                return opt


def _sanitize_dir_name(value):
    cleaned = []
    for ch in value:
        if ch.isalnum() or ch in ("-", "_", "."):
            cleaned.append(ch)
        else:
            cleaned.append("_")
    return "".join(cleaned).strip("_") or "output"


def _build_output_dir_name(out_format, transform_requested, source_cs, target_cs, source_wp, target_wp):
    parts = [f"{out_format}"]
    if transform_requested:
        parts.append(f"{source_cs}_to_{target_cs}")
        if source_wp:
            parts.append(f"src{source_wp}")
        if target_wp:
            parts.append(f"dst{target_wp}")
    return _sanitize_dir_name("_".join(parts))


def convert(args):
    out_format = _normalize_format(args.out_format)
    in_format = _normalize_format(args.in_format)

    if not out_format:
        out_format = _normalize_format(
            _prompt_choice(
                "Output format:",
                ["cube", "3dl", "csp", "spi1d", "spi3d", "spimtx", "vlt", "png", "hald"],
            )
        )

    files = list(_iter_files(args.inputs))
    if not files:
        print("No files matched.")
        return 2

    source_cs = args.source_color_space
    target_cs = args.color_space
    source_wp = args.source_white_point
    target_wp = args.white_point

    transform_requested = (
        getattr(args, "color_space_set", False)
        or getattr(args, "white_point_set", False)
        or getattr(args, "source_color_space_set", False)
        or getattr(args, "source_white_point_set", False)
        or getattr(args, "color_space_prompt", False)
        or getattr(args, "white_point_prompt", False)
    )

    if transform_requested:
        cs_options = sorted(getattr(colour, "RGB_COLOURSPACES", {}).keys())
        wp_options = ["D55", "D60", "D65", "Kelvin (enter value)"]

        if source_cs == "srgb" and not getattr(args, "source_color_space_set", False):
            source_cs = _prompt_choice(
                "Source color space (any colour-science RGB_COLOURSPACES name):",
                cs_options,
                normalize=_resolve_colourspace_alias,
            )
        if target_cs == "srgb" and not getattr(args, "color_space_set", False) and not getattr(
            args, "color_space_prompt", False
        ):
            target_cs = _prompt_choice(
                "Target color space (any colour-science RGB_COLOURSPACES name):",
                cs_options,
                normalize=_resolve_colourspace_alias,
            )

        if getattr(args, "color_space_prompt", False):
            target_cs = _prompt_choice(
                "Target color space (any colour-science RGB_COLOURSPACES name):",
                cs_options,
                normalize=_resolve_colourspace_alias,
            )
        if getattr(args, "white_point_prompt", False):
            target_wp = _prompt_choice("Target white point:", wp_options)
            if target_wp.lower().startswith("kelvin"):
                target_wp = _prompt_nonempty("Enter Kelvin value (e.g., 6500): ")
        if getattr(args, "source_white_point_set", False):
            if source_wp and source_wp.lower().startswith("kelvin"):
                source_wp = _prompt_nonempty("Enter Kelvin value (e.g., 6500): ")

    source_wp_parsed = _parse_white_point(source_wp) if source_wp else None
    target_wp_parsed = _parse_white_point(target_wp) if target_wp else None

    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir is None:
        name = _build_output_dir_name(out_format, transform_requested, source_cs, target_cs, source_wp, target_wp)
        out_dir = Path.cwd() / name
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
            if transform_requested:
                lut = _transform_lut_color_space(
                    lut,
                    source_cs,
                    target_cs,
                    src_white_point=source_wp_parsed,
                    dst_white_point=target_wp_parsed,
                )

            in_path = Path(f)
            out_ext = out_format if out_format else in_path.suffix.lstrip(".")
            out_name = f"{in_path.stem}.{out_ext}"
            out_path = out_dir / out_name

            if out_format in ("hald", "haldclut"):
                _write_haldclut(lut, str(out_path), level=args.hald_level)
            else:
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
    p.add_argument("out_format", nargs="?", help="Output format/extension (e.g., cube, 3dl, csp).")
    p.add_argument("--in-format", dest="in_format", help="Force input format.")
    p.add_argument("--out-dir", dest="out_dir", help="Output directory.")
    p.add_argument(
        "--reader",
        help="Force a specific reader callable name (advanced).",
    )
    p.add_argument("--verbose", action="store_true", help="Verbose error output.")
    class _StoreWithFlag(argparse.Action):
        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, values)
            setattr(namespace, f"{self.dest}_set", True)

    p.add_argument(
        "--source-color-space",
        dest="source_color_space",
        action=_StoreWithFlag,
        default="srgb",
        help="Source color space for LUT values (default: srgb).",
    )
    p.add_argument(
        "--source-white-point",
        dest="source_white_point",
        action=_StoreWithFlag,
        default=None,
        help="Source white point override (D55/D60/D65 or Kelvin).",
    )
    p.add_argument(
        "-c",
        dest="color_space_prompt",
        action="store_true",
        help="Prompt for target color space.",
    )
    p.add_argument(
        "--color-space",
        dest="color_space",
        action=_StoreWithFlag,
        default="srgb",
        help="Target color space (srgb, rec709, rec2020, p3-d65, acescg).",
    )
    p.add_argument(
        "-w",
        dest="white_point_prompt",
        action="store_true",
        help="Prompt for target white point.",
    )
    p.add_argument(
        "--white-point",
        dest="white_point",
        action=_StoreWithFlag,
        default=None,
        help="Target white point (D55/D60/D65 or Kelvin).",
    )
    p.add_argument(
        "--hald-level",
        dest="hald_level",
        type=int,
        default=None,
        help="Hald CLUT level to write (required if LUT size isn't a square).",
    )
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    return convert(args)


if __name__ == "__main__":
    sys.exit(main())
