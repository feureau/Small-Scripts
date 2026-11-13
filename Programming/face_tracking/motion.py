"""Small coordinate-only calculations; video pixels never enter this module."""
import math


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate(data):
    if data.get("schema") != "maxine-face-track/1":
        raise ValueError("Unsupported tracking JSON schema")
    meta, rows = data["video"], data["frames"]
    from fractions import Fraction
    fps = float(Fraction(meta["fps"]))
    if not finite(fps) or fps <= 0 or any(not isinstance(meta[k], int) or meta[k] <= 0 for k in ("width", "height")):
        raise ValueError("Invalid video dimensions or frame rate")
    if not rows:
        raise ValueError("No frames in tracking data")
    previous_time = -math.inf
    previous_segment = -1
    for i, row in enumerate(rows):
        if row["frame"] != i or not finite(row["pts_seconds"]) or row["pts_seconds"] <= previous_time:
            raise ValueError("Frames must be consecutive, with increasing timestamps")
        segment = row["segment"]
        if not isinstance(segment, int) or segment < previous_segment or segment < 0:
            raise ValueError("Invalid segment order")
        if not isinstance(row["valid"], bool) or not finite(row["confidence"]):
            raise ValueError("Invalid confidence/validity")
        if row["valid"] and (not finite(row["anchor_x_px"]) or not finite(row["anchor_y_px"])):
            raise ValueError("Valid frames require finite anchor coordinates")
        previous_time, previous_segment = row["pts_seconds"], segment
    return fps


def segments(rows):
    start = 0
    for i in range(1, len(rows) + 1):
        if i == len(rows) or rows[i]["segment"] != rows[start]["segment"]:
            yield start, i
            start = i


def smooth(points, radius):
    """Centered box filter with truncated windows, O(n), no phase lag."""
    sums = [[0.0, 0.0]]
    for x, y in points:
        sums.append([sums[-1][0] + x, sums[-1][1] + y])
    result = []
    for i in range(len(points)):
        lo, hi = max(0, i - radius), min(len(points), i + radius + 1)
        result.append([(sums[hi][a] - sums[lo][a]) / (hi - lo) for a in (0, 1)])
    return result


def calculate(data, mode="lock", smoothing=0.5, target=None, max_gap=0.2):
    fps = validate(data)
    if mode not in ("lock", "follow") or not finite(smoothing) or smoothing < 0 or not finite(max_gap) or max_gap < 0:
        raise ValueError("Invalid motion options")
    if target is not None and (len(target) != 2 or any(not finite(x) or not 0 <= x <= 1 for x in target)):
        raise ValueError("Target must contain two normalized coordinates between 0 and 1")
    width, height = data["video"]["width"], data["video"]["height"]
    rows = [dict(row) for row in data["frames"]]
    warnings = []
    radius = round(smoothing * fps / 2)
    limit = math.floor(max_gap * fps + 1e-8)
    for start, end in segments(rows):
        part = rows[start:end]
        points = [[r["anchor_x_px"], r["anchor_y_px"]] if r["valid"] else None for r in part]
        usable = [i for i, p in enumerate(points) if p is not None]
        if not usable:
            warnings.append(f"Segment {part[0]['segment']}: no reliable face; identity transform")
            for r in part:
                r.update(dx_px=0.0, dy_px=0.0, status="untracked")
            continue
        for r in part:
            r["status"] = "tracked" if r["valid"] else "held"
        for left, right in zip(usable, usable[1:]):
            gap = right - left - 1
            if 0 < gap <= limit:
                for i in range(left + 1, right):
                    alpha = (i - left) / (right - left)
                    points[i] = [points[left][a] * (1-alpha) + points[right][a] * alpha for a in (0, 1)]
                    part[i]["status"] = "interpolated"
        anchor = points[usable[0]]
        desired_target = [target[0] * width, (1-target[1]) * height] if target else anchor
        offset = [desired_target[a] - anchor[a] for a in (0, 1)]
        # Smooth each reliable run independently; never smooth across a long gap.
        i = 0
        last = [0.0, 0.0]
        while i < len(part):
            if points[i] is None:
                part[i].update(dx_px=last[0], dy_px=last[1])
                i += 1
                continue
            j = i + 1
            while j < len(part) and points[j] is not None:
                j += 1
            desired = smooth(points[i:j], radius) if mode == "follow" else [desired_target] * (j-i)
            for k in range(i, j):
                last = [desired[k-i][a] + (offset[a] if mode == "follow" else 0) - points[k][a] for a in (0, 1)]
                part[k].update(dx_px=last[0], dy_px=last[1])
            i = j
        held = sum(r["status"] == "held" for r in part)
        if held:
            warnings.append(f"Segment {part[0]['segment']}: correction held on {held} frames; inspect reacquisition")
    if not any(r["valid"] for r in rows):
        raise ValueError("No reliable face detected in the entire clip; no animation exported")
    # A separate zoom AFTER translation scales displacement too.
    extent = max(max(abs(r["dx_px"])/width, abs(r["dy_px"])/height) for r in rows)
    zoom = 1 / (1 - 2 * extent) if extent < 0.5 else None
    return rows, warnings, zoom
