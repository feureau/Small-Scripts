"""Fusion settings and portable, versioned tracking output."""
import csv
import io
import json
import os
import tempfile
from pathlib import Path


def fusion_setting(rows, width, height, source_start=0, fusion_start=0, zoom=1.0):
    selected = rows[source_start:]
    if not selected:
        raise ValueError("Source start is outside the tracked clip")
    def spline(axis):
        entries = []
        for row in selected:
            frame = row["frame"] - source_start + fusion_start
            value = 0.5 + (row["dx_px"] / width if axis == "X" else -row["dy_px"] / height)
            entries.append(f"                [{frame}] = {{ {value:.12g}, Flags = {{ Linear = true }} }},")
        return "\n".join(entries)
    # XYPath uses independent scalar curves, avoiding displacement/path interpolation.
    return '''{
    Tools = ordered() {
        FaceTrack = Transform {
            Inputs = {
                Center = Input { SourceOp = "FaceTrackPath", Source = "Value" },
                Size = Input { Value = 1 },
                Angle = Input { Value = 0 },
            },
            ViewInfo = OperatorInfo { Pos = { 0, 0 } },
        },
        FaceTrackPath = XYPath {
            Inputs = {
                X = Input { SourceOp = "FaceTrackX", Source = "Value" },
                Y = Input { SourceOp = "FaceTrackY", Source = "Value" },
            },
        },
        FaceTrackX = BezierSpline {
            KeyFrames = {
''' + spline("X") + '''
            },
        },
        FaceTrackY = BezierSpline {
            KeyFrames = {
''' + spline("Y") + '''
            },
        },
''' + (f'''        FaceTrackCrop = Transform {{
            Inputs = {{
                Input = Input {{ SourceOp = "FaceTrack", Source = "Output" }},
                Size = Input {{ Value = {zoom:.12g} }},
            }},
            ViewInfo = OperatorInfo {{ Pos = {{ 1, 0 }} }},
        }},
''' if zoom != 1 else "") + '''    },
    ActiveTool = "FaceTrack"
}
'''


def csv_text(rows):
    out = io.StringIO(newline="")
    fields = ["frame", "pts_seconds", "segment", "valid", "confidence", "anchor_x_px", "anchor_y_px", "dx_px", "dy_px", "status"]
    writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def write_outputs(paths, data, rows, setting, overwrite=False):
    """Stage all files before publishing; never overwrite without explicit consent."""
    existing = [str(p) for p in paths if p.exists()]
    if existing and not overwrite:
        raise FileExistsError("Outputs exist (use --overwrite): " + ", ".join(existing))
    contents = [json.dumps(data, indent=2, allow_nan=False) + "\n", csv_text(rows), setting]
    temporary = []
    try:
        for path, content in zip(paths, contents):
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent, suffix=".tmp", delete=False) as stream:
                temporary.append(Path(stream.name))
                stream.write(content)
        for temp, path in zip(temporary, paths):
            if overwrite:
                os.replace(temp, path)
            else:
                # Atomic no-clobber publication, including on Windows.
                os.link(temp, path)
                temp.unlink()
    finally:
        for temp in temporary:
            temp.unlink(missing_ok=True)
