#!/usr/bin/env python3
"""Extract figures from academic PDFs with tight cropping.

Two modes:
  auto   - Detect figures from caption blocks, then crop the artwork above them
  region - Render a specific page region by percentage coordinates (fallback)

Auto mode works column-wise: a caption block defines a horizontal band, and only
artwork overlapping that band is considered part of that figure. This keeps
side-by-side figures (very common in two-column and wide-margin ML papers) from
collapsing into one identical crop. Artwork is collected from both embedded
bitmaps and vector drawings, because most ML papers ship matplotlib output as
vectors -- a bitmap-only search silently misses them.

Usage:
    python3 extract_figures.py auto <pdf> <output_dir> [--prefix NAME] [--dpi 300]
    python3 extract_figures.py region <pdf> <output> --page N --top T --bottom B [--left L] [--right R]

Both modes write a downscaled `<name>-preview.png` next to each figure so the
result can be checked with the Read tool, which rejects images over 1500px.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import fitz  # PyMuPDF

# A caption starts its own text block: "Figure 3", "Fig. 3", "Table 2".
CAPTION_RE = re.compile(r"^\s*(Figure|Fig\.|Table)\s*(\d+)\b")


def find_caption_blocks(page, include_tables=True):
    """Find caption blocks on a page.

    Only text blocks whose *first line* begins with "Figure N" count. Inline
    cross-references ("as shown in Figure 7") live mid-sentence and are skipped,
    which is the main source of phantom figures in naive label matching.
    """
    out = []
    for b in page.get_text("dict").get("blocks", []):
        if b.get("type") != 0:
            continue
        lines = b.get("lines", [])
        if not lines:
            continue
        first = "".join(s.get("text", "") for s in lines[0].get("spans", []))
        m = CAPTION_RE.match(first)
        if not m:
            continue
        kind = "table" if m.group(1) == "Table" else "figure"
        if kind == "table" and not include_tables:
            continue
        text = "\n".join(
            "".join(s.get("text", "") for s in ln.get("spans", [])) for ln in lines
        ).strip()
        out.append({
            "kind": kind,
            "number": int(m.group(2)),
            "rect": fitz.Rect(b["bbox"]),
            "caption": text[:300] + ("..." if len(text) > 300 else ""),
        })
    return out


def _overlap_frac(a0, a1, b0, b1):
    """Fraction of span [a0,a1] that lies inside [b0,b1]."""
    span = max(a1 - a0, 1e-6)
    return max(0.0, min(a1, b1) - max(a0, b0)) / span


def is_prose(block, page_width):
    """Body paragraphs run the full text column; table rows and axis labels don't.

    Width is the reliable discriminator: a justified paragraph spans ~70-80% of
    the page, while a table column or a stack of tick labels is much narrower.
    """
    r = fitz.Rect(block["bbox"])
    return len(block.get("lines", [])) >= 2 and r.width >= page_width * 0.60


def collect_artwork(page, band_x0, band_x1, y_lo, y_hi, min_side=6):
    """Union of everything belonging to one figure inside a column band.

    Sources: embedded bitmaps, vector drawings, and non-prose text (axis labels,
    legends, table cells -- a table is text, so a drawings-only search returns
    just its rules).

    `band` is the caption's horizontal extent, widened a little: plots routinely
    overhang their caption by an axis label or a legend. The band test is
    one-sided on purpose -- a rect counts only if *it* sits inside the band.
    Testing the other way round lets page-wide decorations (an abstract box, a
    full-width rule) attach themselves to a single-column figure.
    """
    rects = []

    for img in page.get_images(full=True):
        try:
            found = page.get_image_rects(img[0])
        except Exception:
            continue
        for r in found:
            if r.width >= min_side and r.height >= min_side:
                rects.append(r)

    for d in page.get_drawings():
        r = fitz.Rect(d["rect"])
        if r.width >= min_side and r.height >= min_side:
            rects.append(r)

    page_width = page.rect.width
    for b in page.get_text("dict").get("blocks", []):
        if b.get("type") == 0 and not is_prose(b, page_width):
            rects.append(fitz.Rect(b["bbox"]))

    return [
        r for r in rects
        if r.y1 <= y_hi and r.y1 > y_lo
        and _overlap_frac(r.x0, r.x1, band_x0, band_x1) >= 0.8
    ]


def text_ceiling(page, caption_rect, band_x0, band_x1):
    """Bottom edge of the nearest body paragraph above the caption.

    Artwork never extends past the paragraph above it, so this is a safe upper
    bound and prevents a crop from swallowing half a page of prose. Only real
    prose counts -- mistaking a table row for prose collapses the crop to a
    sliver of the table's bottom rule.
    """
    ceiling = 0.0
    for b in page.get_text("dict").get("blocks", []):
        if b.get("type") != 0 or not is_prose(b, page.rect.width):
            continue
        bb = fitz.Rect(b["bbox"])
        if bb.y1 >= caption_rect.y0 - 2:
            continue
        # Only prose that actually sits over this column blocks the crop.
        if _overlap_frac(bb.x0, bb.x1, band_x0, band_x1) < 0.25:
            continue
        ceiling = max(ceiling, bb.y1)
    return ceiling


def column_band(page, cap, siblings, slack_frac=0.05):
    """Horizontal band owned by one caption.

    A caption is widened by some slack (plots overhang their caption with axis
    labels and legends), then clipped against captions sharing the same row, so
    a three-across figure row splits cleanly instead of each crop eating its
    neighbour.
    """
    r = cap["rect"]
    slack = page.rect.width * slack_frac
    x0, x1 = r.x0 - slack, r.x1 + slack
    for other in siblings:
        o = other["rect"]
        if other is cap or _overlap_frac(o.y0, o.y1, r.y0, r.y1) < 0.3:
            continue  # different row -- no horizontal conflict
        if o.x1 <= r.x0:
            x0 = max(x0, (o.x1 + r.x0) / 2)
        elif o.x0 >= r.x1:
            x1 = min(x1, (r.x1 + o.x0) / 2)
    return x0, x1


def nearest_cluster(rects, caption_top, max_gap):
    """Keep only artwork contiguous with the caption.

    Walking up from the caption, a vertical gap wider than `max_gap` means we
    have left the figure and reached unrelated page furniture (a header, a
    dateline, the paragraph above). Everything past that gap is dropped.
    """
    if not rects:
        return None
    ordered = sorted(rects, key=lambda r: -r.y1)
    union, prev_top = ordered[0], ordered[0].y0
    for r in ordered[1:]:
        if r.y1 < prev_top - max_gap:
            break
        union = union | r
        prev_top = min(prev_top, r.y0)
    return union


def compute_figure_bbox(page, cap, siblings=(), pad=8, include_caption=False):
    """Crop rect for one caption block."""
    r = cap["rect"]
    band_x0, band_x1 = column_band(page, cap, siblings)

    y_lo = text_ceiling(page, r, band_x0, band_x1)
    parts = collect_artwork(page, band_x0, band_x1, y_lo, r.y0 - 1)
    art = nearest_cluster(parts, r.y0, page.rect.height * 0.025)

    if art is None:  # nothing found: fall back to the whole band above the caption
        art = fitz.Rect(band_x0, max(y_lo, 0), band_x1, r.y0 - 2)

    bottom = (r.y1 if include_caption else art.y1) + pad
    return fitz.Rect(
        max(0, art.x0 - pad),
        max(0, art.y0 - pad),
        min(page.rect.width, art.x1 + pad),
        min(page.rect.height, bottom),
    )


def render_region(page, bbox, dpi=300):
    """Render a page region to PNG bytes."""
    mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    pix = page.get_pixmap(matrix=mat, clip=bbox, alpha=False)
    return pix.tobytes("png")


def write_with_preview(path: Path, png: bytes, preview_max=1400):
    """Write the figure plus a Read-tool-sized preview beside it."""
    path.write_bytes(png)
    pix = fitz.Pixmap(str(path))
    while pix.width > preview_max or pix.height > preview_max:
        pix.shrink(1)
    preview = path.with_name(path.stem + "-preview.png")
    pix.save(str(preview))
    return preview


def cmd_auto(args):
    doc = fitz.open(args.pdf)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    target = set(int(x) for x in args.figures.split(",")) if args.figures else None
    results, seen = [], set()

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        caps = find_caption_blocks(page, include_tables=args.tables)
        for cap in caps:
            key = (cap["kind"], cap["number"])
            if key in seen:
                continue
            if target and cap["number"] not in target:
                continue
            seen.add(key)

            bbox = compute_figure_bbox(
                page, cap, siblings=caps, pad=args.pad,
                include_caption=args.with_caption
            )
            if bbox.width < 20 or bbox.height < 20:
                print(f"skip {key}: degenerate bbox", file=sys.stderr)
                continue

            tag = "tab" if cap["kind"] == "table" else "fig"
            fpath = out_dir / f"{args.prefix}-{tag}{cap['number']}.png"
            preview = write_with_preview(fpath, render_region(page, bbox, args.dpi),
                                         args.preview_max)

            # A crop that is a thin sliver, or wildly elongated, usually means
            # the artwork search latched onto a rule or a stray label. Flagging
            # it here saves reading every preview to find the one bad one.
            h_frac = bbox.height / page.rect.height
            aspect = bbox.width / max(bbox.height, 1e-6)
            suspect = h_frac < 0.08 or aspect > 12 or aspect < 0.08

            results.append({
                "kind": cap["kind"],
                "number": cap["number"],
                "page": page_idx,  # 0-indexed, matches --page in region mode
                "filename": fpath.name,
                "path": str(fpath),
                "preview": str(preview),
                "suspect": suspect,
                "caption": cap["caption"],
                "bbox_pct": {
                    "top": round(bbox.y0 / page.rect.height, 3),
                    "bottom": round(bbox.y1 / page.rect.height, 3),
                    "left": round(bbox.x0 / page.rect.width, 3),
                    "right": round(bbox.x1 / page.rect.width, 3),
                },
            })
            print(f"{cap['kind']} {cap['number']} (page {page_idx}) -> {fpath.name}",
                  file=sys.stderr)

    doc.close()
    print(json.dumps(results, indent=2))


def cmd_region(args):
    doc = fitz.open(args.pdf)
    page = doc[args.page]
    rect = page.rect
    clip = fitz.Rect(rect.width * args.left, rect.height * args.top,
                     rect.width * args.right, rect.height * args.bottom)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    preview = write_with_preview(out, render_region(page, clip, args.dpi),
                                 args.preview_max)
    doc.close()

    print(json.dumps({"path": str(out), "preview": str(preview), "page": args.page,
                      "region": [args.top, args.bottom, args.left, args.right]}))
    print(f"Rendered page {args.page} region -> {out}", file=sys.stderr)


def cmd_pages(args):
    """Report per-page caption positions — coordinates for manual `region` calls."""
    doc = fitz.open(args.pdf)
    pages = (range(len(doc)) if not args.pages
             else [int(x) for x in args.pages.split(",")])
    for pi in pages:
        page = doc[pi]
        W, H = page.rect.width, page.rect.height
        caps = find_caption_blocks(page)
        if not caps:
            continue
        print(f"page {pi}:")
        for c in caps:
            r = c["rect"]
            print(f"  {c['kind']} {c['number']}: caption top={r.y0/H:.3f} "
                  f"x={r.x0/W:.3f}-{r.x1/W:.3f} | {c['caption'].splitlines()[0][:70]}")
    doc.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract figures from academic PDFs")
    sub = parser.add_subparsers(dest="command")

    p_auto = sub.add_parser("auto", help="Auto-detect and extract figures")
    p_auto.add_argument("pdf")
    p_auto.add_argument("output_dir")
    p_auto.add_argument("--prefix", default="paper")
    p_auto.add_argument("--dpi", type=int, default=300)
    p_auto.add_argument("--pad", type=float, default=8.0)
    p_auto.add_argument("--preview-max", type=int, default=1400)
    p_auto.add_argument("--figures", type=str, default=None,
                        help="Comma-separated figure numbers to extract")
    p_auto.add_argument("--tables", action="store_true",
                        help="Also extract Table N blocks")
    p_auto.add_argument("--with-caption", action="store_true",
                        help="Include the caption text in the crop")

    p_reg = sub.add_parser("region", help="Render a specific page region")
    p_reg.add_argument("pdf")
    p_reg.add_argument("output")
    p_reg.add_argument("--page", type=int, required=True, help="0-indexed page number")
    p_reg.add_argument("--top", type=float, required=True, help="Top boundary (0.0-1.0)")
    p_reg.add_argument("--bottom", type=float, required=True, help="Bottom boundary (0.0-1.0)")
    p_reg.add_argument("--left", type=float, default=0.0)
    p_reg.add_argument("--right", type=float, default=1.0)
    p_reg.add_argument("--dpi", type=int, default=300)
    p_reg.add_argument("--preview-max", type=int, default=1400)

    p_pg = sub.add_parser("pages", help="List caption coordinates per page")
    p_pg.add_argument("pdf")
    p_pg.add_argument("--pages", type=str, default=None,
                      help="Comma-separated 0-indexed pages (default: all)")

    args = parser.parse_args()
    if args.command == "auto":
        cmd_auto(args)
    elif args.command == "region":
        cmd_region(args)
    elif args.command == "pages":
        cmd_pages(args)
    else:
        parser.print_help()
