import argparse
import importlib.util
import json
import math
import shutil
import sys
from pathlib import Path
from . import __version__
from .export import fusion_setting, write_outputs
from .maxine import BRIDGE, sdk_directory
from .motion import calculate


def nonnegative(value):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("must be a finite nonnegative number")
    return number


def parser():
    p = argparse.ArgumentParser(description="GPU Maxine face lock / smooth follow -> Fusion .setting, CSV and JSON. Outputs go to the calling folder.")
    p.add_argument("input", nargs="?", type=Path, help="video or saved .track.json")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--doctor", action="store_true", help="check installation without processing video")
    p.add_argument("--mode", choices=("lock", "follow"), default="lock")
    p.add_argument("--smooth", type=nonnegative, default=0.5, metavar="SECONDS", help="centered follow window; default 0.5")
    p.add_argument("--target", nargs=2, type=nonnegative, metavar=("X", "Y"), help="normalized bottom-left coordinates; default first valid position")
    p.add_argument("--max-gap", type=nonnegative, default=0.2, metavar="SECONDS")
    p.add_argument("--output-dir", type=Path, default=Path.cwd())
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--source-start", type=int, default=0, help="first source frame to export (clip trim)")
    p.add_argument("--fusion-start", type=int, default=0, help="Fusion frame corresponding to source-start")
    p.add_argument("--zoom", type=nonnegative, default=1, help="constant zoom AFTER stabilization")
    p.add_argument("--auto-zoom", action="store_true", help="constant zoom to cover translated borders")
    p.add_argument("--preview", action="store_true", help="silent GPU diagnostic MP4, full tracked range")
    p.add_argument("--source", type=Path, help="replacement source path for previewing saved tracking")
    p.add_argument("--gpu", type=int, default=0)
    p.add_argument("--sdk-dir", type=Path, help="directory containing nvARPose.dll; or NVAR_SDK_PATH")
    p.add_argument("--models", type=Path, help="default: SDK directory/models")
    p.add_argument("--quality", choices=("quality", "performance"), default="quality")
    p.add_argument("--anchor", choices=("eyes", "nose"), default="eyes")
    p.add_argument("--roi", nargs=4, type=int, metavar=("X", "Y", "W", "H"), help="fixed analysis crop, top-left source pixels")
    p.add_argument("--min-confidence", type=nonnegative, default=15.0, help="raw SDK landmark confidence threshold (not probability); default 15, calibrate to your SDK")
    p.add_argument("--cuts", nargs="*", type=int, default=[], help="source frame numbers beginning new shots")
    p.add_argument("--cut-threshold", type=nonnegative, default=0, help="optional GPU image-change cut heuristic, 0 disables; try 0.45")
    p.add_argument("--allow-cpu-decode", action="store_true", help="permit PyAV fallback only if NVDEC initialization fails")
    p.add_argument("--limit", type=int, help="track only the first N frames for a smoke test")
    p.add_argument("--debug", action="store_true")
    return p


def doctor(args):
    sdk = sdk_directory(args.sdk_dir)
    models = args.models or sdk / "models"
    checks = {"Windows x64 Python": sys.platform == "win32" and sys.maxsize > 2**32,
        "CuPy": importlib.util.find_spec("cupy") is not None,
        "PyNvVideoCodec": importlib.util.find_spec("PyNvVideoCodec") is not None,
        "ffprobe": bool(shutil.which("ffprobe")), "ffmpeg (preview)": bool(shutil.which("ffmpeg")),
        f"Maxine runtime: {sdk}": (sdk / "nvARPose.dll").is_file(),
        f"Maxine models: {models}": Path(models).is_dir(), f"Native bridge: {BRIDGE}": BRIDGE.is_file()}
    if checks["CuPy"]:
        try:
            import cupy as cp
            cp.cuda.Device(args.gpu).use()
            checks["CUDA allocation"] = bool(cp.zeros(1).size)
        except Exception as error:
            checks[f"CUDA allocation ({error})"] = False
    for label, success in checks.items():
        print(f"{'OK     ' if success else 'MISSING'} {label}")
    print("Setup: " + str(Path(__file__).with_name("README.md")))
    return 0 if all(checks.values()) else 2


def main(argv=None):
    p = parser()
    args = p.parse_args(argv)
    if args.doctor:
        return doctor(args)
    if args.input is None:
        p.error("input is required unless --doctor is used")
    if args.source_start < 0 or args.gpu < 0 or (args.limit is not None and args.limit <= 0) or any(c < 0 for c in args.cuts):
        p.error("frame indices and GPU must be nonnegative; --limit must be positive")
    if args.zoom < 1 or args.cut_threshold > 1 or (args.target and max(args.target) > 1):
        p.error("--zoom must be >= 1; target and cut threshold must be <= 1")
    try:
        source = args.input.resolve(strict=True)
        saved = source.name.lower().endswith(".track.json")
        stem = source.name[:-11] if saved else source.stem
        out = args.output_dir.resolve()
        paths = [out / f"{stem}.track.json", out / f"{stem}.track.csv", out / f"{stem}.{args.mode}.setting"]
        # Re-exporting beside the input keeps the original raw tracking untouched.
        if saved and paths[0] == source:
            paths[0] = out / f"{stem}.{args.mode}.track.json"
        preview = out / f"{stem}.{args.mode}.preview.mp4"
        collisions = [str(path) for path in paths + ([preview] if args.preview else []) if path.exists()]
        if collisions and not args.overwrite:
            raise FileExistsError("Outputs exist (use --overwrite): " + ", ".join(collisions))
        if source in paths or (args.preview and preview == source):
            raise ValueError("An output path would overwrite the input")
        if saved:
            data = json.loads(source.read_text(encoding="utf-8"))
        else:
            from .tracking import run_tracking
            data = run_tracking(source, args)
        rows, warnings, required_zoom = calculate(data, args.mode, args.smooth, args.target, args.max_gap)
        zoom = args.zoom
        if args.auto_zoom:
            if required_zoom is None:
                raise ValueError("Motion exceeds half the frame; centered zoom cannot cover borders")
            zoom = max(zoom, required_zoom)
        setting = fusion_setting(rows, data["video"]["width"], data["video"]["height"], args.source_start, args.fusion_start, zoom)
        data["motion"] = {"mode": args.mode, "smooth_seconds": args.smooth, "target": args.target,
            "max_gap_seconds": args.max_gap, "zoom": zoom, "required_zoom": required_zoom,
            "source_start": args.source_start, "fusion_start": args.fusion_start, "warnings": warnings}
        data["frames"] = rows
        write_outputs(paths, data, rows, setting, args.overwrite)
        for path in paths:
            print(path)
        invalid = sum(not row["valid"] for row in rows)
        print(f"{len(rows)} frames; {invalid} invalid detections; required centered zoom: {required_zoom if required_zoom is not None else 'not possible'}", file=sys.stderr)
        for message in warnings:
            print("Warning: " + message, file=sys.stderr)
        if args.preview:
            from .preview import render
            media = args.source.resolve(strict=True) if args.source else Path(data["source"]["path"])
            stat = media.stat()
            if not args.source and (stat.st_size != data["source"]["size"] or stat.st_mtime_ns != data["source"]["mtime_ns"]):
                raise ValueError("Preview source changed since tracking; use --source only for frame-identical media")
            print("Rendering GPU diagnostic preview (no audio)...", file=sys.stderr)
            render(media, preview, rows, data["video"], args.gpu, zoom, args.overwrite, args.allow_cpu_decode)
            print(preview)
        return 0
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130
    except Exception as error:
        if args.debug:
            raise
        print(f"track: {error}", file=sys.stderr)
        return 1
