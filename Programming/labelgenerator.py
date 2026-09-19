#!/usr/bin/env python3
"""
labelgenerator.py — A6 label sheet, font-driven, uniform gap.

Usage:
    labelgenerator.py "cat"
    labelgenerator.py "cat" --font 8 --gap-factor 0.7
    labelgenerator.py "White Lotus" --font 10
"""

import argparse, re, sys
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

# Helvetica-Bold font metrics (ratios of font size)
CAP_RATIO   = 0.718
XH_RATIO    = 0.523
DESC_RATIO  = 0.207
ASCENDERS   = set("bdfhklt")
DESCENDERS  = set("gjpqy")


def slugify(s):
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    return re.sub(r"[\s_-]+", "_", s) or "labels"


def ink_metrics(text, font_pt):
    """Return (top_above_baseline, depth_below_baseline) in points."""
    has_top = any(c.isupper() or c in ASCENDERS for c in text)
    top   = (CAP_RATIO if has_top else XH_RATIO) * font_pt
    depth = (DESC_RATIO if any(c in DESCENDERS for c in text) else 0.0) * font_pt
    return top, depth


def compute(text, font_pt, gap_factor):
    text_w  = stringWidth(text, FONT_NAME, font_pt)
    top, bot = ink_metrics(text, font_pt)
    cell_h  = top + bot                          # ← the fix

    target_gap = font_pt * gap_factor
    avail_w    = A6[0] - 2 * MARGIN
    avail_h    = A6[1] - 2 * MARGIN

    cols = max(1, int((avail_w + target_gap) // (text_w + target_gap)))
    rows = max(1, int((avail_h + target_gap) // (cell_h + target_gap)))

    # Resolve a single gap that works for both axes.
    gx = (avail_w - cols * text_w) / (cols - 1) if cols > 1 else None
    gy = (avail_h - rows * cell_h) / (rows - 1) if rows > 1 else None
    candidates = [g for g in (gx, gy) if g is not None]
    gap = max(0.0, min(candidates)) if candidates else target_gap

    block_w = cols * text_w + (cols - 1) * gap
    block_h = rows * cell_h + (rows - 1) * gap
    x0 = MARGIN + (avail_w - block_w) / 2
    y0 = MARGIN + (avail_h - block_h) / 2

    return {
        "font_pt": font_pt, "text_w": text_w, "cell_h": cell_h,
        "gap": gap, "cols": cols, "rows": rows,
        "x0": x0, "y0": y0, "baseline_off": bot,
        "nominal_gap": target_gap, "top": top, "bot": bot,
    }


def draw(c, L, text):
    c.setFont(FONT_NAME, L["font_pt"])
    for r in range(L["rows"]):
        row_bottom = L["y0"] + (L["rows"] - 1 - r) * (L["cell_h"] + L["gap"])
        baseline   = row_bottom + L["baseline_off"]
        for col in range(L["cols"]):
            xc = L["x0"] + col * (L["text_w"] + L["gap"]) + L["text_w"] / 2
            c.drawCentredString(xc, baseline, text)


def main():
    p = argparse.ArgumentParser(
        description="A6 label sheet — font-driven, uniform gap.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("text")
    p.add_argument("-o", "--output", default=None)
    p.add_argument("--font", type=float, default=12.0,
                   help="Font size in points")
    p.add_argument("--gap-factor", type=float, default=0.5,
                   help="Nominal gap ÷ font size. Lower = tighter.")
    args = p.parse_args()

    if args.font <= 0: p.error("--font must be > 0")
    if args.gap_factor < 0: p.error("--gap-factor must be >= 0")

    L   = compute(args.text, args.font, args.gap_factor)
    out = Path(args.output) if args.output else Path(slugify(args.text) + ".pdf")

    c = canvas.Canvas(str(out), pagesize=A6)
    c.setTitle(args.text); c.setAuthor("labelgenerator.py")
    draw(c, L, args.text); c.showPage(); c.save()

    pt_to_mm = 25.4 / 72.0
    print(f"Wrote {out}")
    print(f"  {L['cols'] * L['rows']} labels  "
          f"({L['cols']} cols × {L['rows']} rows)")
    print(f"  font {L['font_pt']:.2f} pt ({L['font_pt'] * pt_to_mm:.2f} mm)"
          f"   text {L['text_w']:.2f} pt   cell_h {L['cell_h']:.2f} pt")
    print(f"  gap {L['gap']:.2f} pt (uniform)   "
          f"nominal {L['nominal_gap']:.2f} pt")

    if L["cols"] == 1:
        print("  warning: only 1 column fits — use --font to shrink.")
    if L["rows"] == 1:
        print("  warning: only 1 row fits — use --font to shrink.")


if __name__ == "__main__":
    main()