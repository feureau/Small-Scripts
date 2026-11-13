import math
import sys
import time
from pathlib import Path
from . import __version__
from .maxine import Maxine, sdk_directory
from .video import GPUVideo, probe


def run_tracking(path, options):
    print("Inspecting compressed packet timestamps (no CPU video decoding)...", file=sys.stderr)
    video = probe(path)
    sdk = sdk_directory(options.sdk_dir)
    models = Path(options.models).resolve() if options.models else sdk / "models"
    decoder = GPUVideo(path, options.gpu, options.allow_cpu_decode)
    cp, stream = decoder.cp, decoder.stream
    tracker = None
    rows = []
    width, height = video["width"], video["height"]
    roi = options.roi or [0, 0, width, height]
    x, y, w, h = roi
    if min(x, y) < 0 or min(w, h) <= 0 or x+w > width or y+h > height:
        decoder.close()
        raise ValueError("ROI must lie within the source frame (x y width height, top-left pixels)")
    indices = range(36, 48) if options.anchor == "eyes" else [27, 28, 29, 30]
    cuts = set(options.cuts or [])
    segment = 0
    started = time.monotonic()
    last_log = started
    previous_thumb = None
    try:
        with stream:
            bgr = cp.empty((h, w, 3), dtype=cp.uint8)
            for i, rgb in enumerate(decoder.frames()):
                if i >= len(video["pts"]):
                    raise ValueError("Decoded frame count exceeds packet timing count; this container is unsupported")
                if rgb.shape[:2] != (height, width):
                    raise ValueError("Changing resolution is not supported")
                is_cut = i in cuts
                if options.cut_threshold > 0:
                    thumb = rgb[::max(1, height//48), ::max(1, width//64)].astype(cp.float32)
                    if previous_thumb is not None:
                        is_cut |= float(cp.mean(cp.abs(thumb - previous_thumb)).get()) / 255 > options.cut_threshold
                    previous_thumb = thumb
                if tracker is None or is_cut:
                    if tracker:
                        tracker.close()
                        segment += 1
                    tracker = Maxine(sdk, models, stream, options.quality == "quality")
                cp.copyto(bgr, rgb[y:y+h, x:x+w, ::-1])
                found, points, confidence, box = tracker.run(bgr)
                score = sum(confidence[k] for k in indices) / len(indices)
                sane = all(math.isfinite(v) for p in points for v in p) and all(math.isfinite(v) for v in confidence + box)
                ax = sum(points[k][0] for k in indices) / len(indices) if sane else 0
                ay = sum(points[k][1] for k in indices) / len(indices) if sane else 0
                valid = found and sane and score >= options.min_confidence and score > 0 and box[2] > 0 and box[3] > 0 and 0 <= ax < w and 0 <= ay < h
                rows.append({"frame": i, "pts_seconds": video["pts_seconds"][i], "segment": segment,
                    "valid": bool(valid), "confidence": score if math.isfinite(score) else 0,
                    "anchor_x_px": ax+x if valid else None, "anchor_y_px": ay+y if valid else None,
                    "landmarks": [[p[0]+x, p[1]+y] for p in points] if sane and found else None,
                    "landmark_confidence": confidence if sane and found else None,
                    "bbox": [box[0]+x, box[1]+y, box[2], box[3]] if sane and found else None})
                now = time.monotonic()
                if now - last_log >= 1:
                    print(f"\rTracking {i+1}/{len(video['pts'])} | {(i+1)/(now-started):.1f} fps", end="", file=sys.stderr, flush=True)
                    last_log = now
                if options.limit and i+1 >= options.limit:
                    break
        expected = min(len(video["pts"]), options.limit) if options.limit else len(video["pts"])
        if len(rows) != expected:
            raise ValueError(f"Decoded {len(rows)} frames, expected {expected}; refusing misaligned export")
    finally:
        if tracker:
            tracker.close()
        decoder.close()
        print(file=sys.stderr)
    elapsed = time.monotonic()-started
    video.pop("pts_seconds")
    video["pts"] = video["pts"][:len(rows)]
    stat = path.stat()
    return {"schema": "maxine-face-track/1", "tool_version": __version__,
        "source": {"path": str(path), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns},
        "video": video, "coordinates": "source pixels; origin top left; x right, y down",
        "tracking": {"backend": "Maxine AR 68 landmarks", "decoder": decoder.backend, "gpu": options.gpu,
            "anchor": options.anchor, "roi": roi, "quality": options.quality,
            "min_confidence": options.min_confidence, "confidence_units": "raw SDK landmark score, not a probability",
            "cut_threshold": options.cut_threshold, "explicit_cuts": sorted(cuts),
            "elapsed_seconds": elapsed, "frames_per_second": len(rows)/elapsed},
        "frames": rows}
