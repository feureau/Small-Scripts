#!/usr/bin/env python3
"""
labelgenerator.py — A6 label sheet, one or more texts, uniform gap,
column-locked layout (each column contains only one word).

Usage:
    labelgenerator.py "cat"
    labelgenerator.py cat dog mom
    labelgenerator.py "cat", "dog", "mom"
    labelgenerator.py "cat", "dog", "mom" --split
    labelgenerator.py "White Lotus" "Red Bean" --font 8
    labelgenerator.py cat dog mom --font 6 --gap-factor 0.4
"""

import argparse
import re
import sys
from pathlib import Path

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A6
    from reportlab.lib.units import mm
    from reportlab.pdfbase.pdfmetrics import stringWidth
except ImportError:
    sys.exit("ReportLab not installed. Run: pip install reportlab")


MARGIN_MM   = 1.5
MARGIN      = MARGIN_MM * mm
FONT_NAME   = "Helvetica-Bold"

# Helvetica-Bold metrics (ratios of font size)
CAP_RATIO   = 0.718
XH_RATIO    = 0.523
DESC_RATIO  = 0.207
ASCENDERS   = set("bdfhklt")
DESCENDERS  = set("gjpqy")


def slugify(s):
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    return re.sub(r"[\s_-]+", "_", s) or "label"


def parse_labels(raw):
    """Split each arg on commas; drop empties. Handles 'cat,' → 'cat'."""
    out = []
    for a in raw:
        for part in a.split(","):
            part = part.strip()
            if part:
                out.append(part)
    return out


def ink_metrics(text, font_pt):
    has_top = any(c.isupper() or c in ASCENDERS for c in text)
    top   = (CAP_RATIO if has_top else XH_RATIO) * font_pt
    depth = (DESC_RATIO if any(c in DESCENDERS for c in text) else 0.0) * font_pt
    return top, depth


def compute(labels, font_pt, gap_factor):
    # Cell size = worst case across all labels
    text_w = max(stringWidth(t, FONT_NAME, font_pt) for t in labels)
    metrics = [ink_metrics(t, font_pt) for t in labels]
    cell_h  = max(top + bot for top, bot in metrics)

    # Per-label baseline offset so each label is visually centred in its cell
    offsets = [cell_h / 2 - (top - bot) / 2 for top, bot in metrics]

    target_gap = font_pt * gap_factor
    avail_w    = A6[0] - 2 * MARGIN
    avail_h    = A6[1] - 2 * MARGIN

    cols = max(1, int((avail_w + target_gap) // (text_w + target_gap)))
    rows = max(1, int((avail_h + target_gap) // (cell_h + target_gap)))

    gx = (avail_w - cols * text_w) / (cols - 1) if cols > 1 else None
    gy = (avail_h - rows * cell_h) / (rows - 1) if rows > 1 else None
    candidates = [g for g in (gx, gy) if g is not None]
    gap = max(0.0, min(candidates)) if candidates else target_gap

    block_w = cols * text_w + (cols - 1) * gap
    block_h = rows * cell_h + (rows - 1) * gap
    x0 = MARGIN + (avail_w - block_w) / 2
    y0 = MARGIN + (avail_h - block_h) / 2

    return {
        "labels": labels, "offsets": offsets,
        "font_pt": font_pt, "text_w": text_w, "cell_h": cell_h,
        "gap": gap, "cols": cols, "rows": rows,
        "x0": x0, "y0": y0,
        "nominal_gap": target_gap,
    }


def draw(c, L):
    c.setFont(FONT_NAME, L["font_pt"])
    n = len(L["labels"])
    for r in range(L["rows"]):
        row_bottom = L["y0"] + (L["rows"] - 1 - r) * (L["cell_h"] + L["gap"])
        for col in range(L["cols"]):
            i        = col % n                        # column picks the label
            text     = L["labels"][i]
            baseline = row_bottom + L["offsets"][i]
            xc       = L["x0"] + col * (L["text_w"] + L["gap"]) + L["text_w"] / 2
            c.drawCentredString(xc, baseline, text)


def render_sheet(labels, font_pt, gap_factor, out_path):
    """Compute layout and write a single PDF for the given label(s)."""
    L = compute(labels, font_pt, gap_factor)
    c = canvas.Canvas(str(out_path), pagesize=A6)
    c.setTitle(" / ".join(labels)); c.setAuthor("labelgenerator.py")
    draw(c, L); c.showPage(); c.save()
    return L


def report(L, labels, out_path):
    pt_to_mm = 25.4 / 72.0
    cells    = L["cols"] * L["rows"]
    shown = ", ".join(f'"{l}"' for l in labels[:5])
    if len(labels) > 5:
        shown += f", … ({len(labels)} total)"

    print(f"Wrote {out_path}")
    print(f"  labels: {shown}")
    print(f"  {cells} cells  ({L['cols']} cols × {L['rows']} rows)")
    print(f"  font {L['font_pt']:.2f} pt ({L['font_pt'] * pt_to_mm:.2f} mm)"
          f"   cell {L['text_w']:.2f} × {L['cell_h']:.2f} pt")
    print(f"  gap {L['gap']:.2f} pt (uniform)   "
          f"nominal {L['nominal_gap']:.2f} pt")

    if L["cols"] == 1:
        print("  warning: only 1 column fits — use --font to shrink.")
    if L["rows"] == 1:
        print("  warning: only 1 row fits — use --font to shrink.")
    if len(labels) > L["cols"]:
        print(f"  note: {len(labels)} labels given but only {L['cols']} columns; "
              f"columns 0–{L['cols']-1} will use the first {L['cols']} labels.")


def main():
    p = argparse.ArgumentParser(
        description="A6 label sheet — column-locked, uniform gap.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("texts", nargs="+",
                   help='One or more label texts. Commas are treated as '
                        'separators, so "cat", "dog", "mom" also works.')
    p.add_argument("-o", "--output", default=None)
    p.add_argument("-s", "--split", action="store_true",
                   help="Generate one PDF per label instead of one combined sheet.")
    p.add_argument("--font", type=float, default=12.0,
                   help="Font size in points (applies to all labels)")
    p.add_argument("--gap-factor", type=float, default=0.5,
                   help="Nominal gap ÷ font size. Lower = tighter.")
    args = p.parse_args()

    if args.font <= 0:      p.error("--font must be > 0")
    if args.gap_factor < 0: p.error("--gap-factor must be >= 0")

    labels = parse_labels(args.texts)
    if not labels:
        p.error("no labels given")

    if args.split:
        if args.output:
            p.error("-o cannot be combined with --split; "
                    "split mode names each file after its label.")
        seen = set()
        for label in labels:
            slug = slugify(label)
            if slug in seen:
                print(f"  warning: duplicate slug '{slug}' — "
                      f"'{label}' will overwrite an earlier file.")
            seen.add(slug)
            out = Path(slug + ".pdf")
            L   = render_sheet([label], args.font, args.gap_factor, out)
            report(L, [label], out)
    else:
        if args.output:
            out = Path(args.output)
        else:
            stem = "_".join(slugify(l) for l in labels)
            if len(stem) > 120:
                stem = stem[:120].rstrip("_")
            out = Path(stem + ".pdf")
        L = render_sheet(labels, args.font, args.gap_factor, out)
        report(L, labels, out)


if __name__ == "__main__":
    main()