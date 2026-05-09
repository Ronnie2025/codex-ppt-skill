#!/usr/bin/env python3
"""Create render comparison metrics, diff heatmaps, and a contact sheet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageOps, ImageStat


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", action="append", required=True, help="Reference slide image. Repeat per slide.")
    parser.add_argument("--render", action="append", required=True, help="Rendered output slide image. Repeat per slide.")
    parser.add_argument("--out-dir", required=True, help="Comparison output directory.")
    parser.add_argument("--thumb-width", type=int, default=520, help="Contact sheet column width.")
    parser.add_argument("--max-changed-pixel-pct", type=float, default=0.35, help="Warn when changed pixel share is above this value.")
    parser.add_argument("--max-mad", type=float, default=35.0, help="Warn when mean absolute difference is above this value.")
    return parser.parse_args()


def fit_width(img: Image.Image, width: int) -> Image.Image:
    height = round(img.height * width / img.width)
    return img.resize((width, height), Image.LANCZOS)


def main() -> None:
    args = parse_args()
    refs = [Path(p) for p in args.reference]
    renders = [Path(p) for p in args.render]
    if len(refs) != len(renders):
        raise SystemExit("--reference and --render counts must match")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics = []
    rows = []

    for idx, (ref_path, render_path) in enumerate(zip(refs, renders), start=1):
        ref = Image.open(ref_path).convert("RGB")
        render = Image.open(render_path).convert("RGB")
        render_for_diff = render.resize(ref.size, Image.LANCZOS)
        diff = ImageChops.difference(ref, render_for_diff)
        stat = ImageStat.Stat(diff)
        mad = sum(stat.mean) / 3.0
        changed = sum(1 for px in diff.getdata() if max(px) > 18) / (ref.width * ref.height)
        gray = ImageEnhance.Contrast(ImageOps.grayscale(diff)).enhance(2.2)
        heat = ImageOps.colorize(gray, black=(255, 255, 255), white=(255, 74, 74))
        overlay = Image.blend(ref, heat, 0.45)
        heat_path = out_dir / f"slide_{idx:02d}_diff_heatmap.png"
        overlay.save(heat_path)
        metrics.append({
            "slide": idx,
            "reference": str(ref_path),
            "render": str(render_path),
            "reference_size": list(ref.size),
            "render_size": list(render.size),
            "mean_absolute_difference": round(mad, 3),
            "changed_pixel_pct_threshold_18": round(changed, 4),
            "status": "PASS" if mad <= args.max_mad and changed <= args.max_changed_pixel_pct else "REVIEW",
            "repair_hints": [
                hint for hint, enabled in [
                    ("large visual drift: inspect missing assets, z-order, panel sizes, and shape fills", mad > args.max_mad),
                    ("many changed pixels: compare title/card positions and large decorative regions first", changed > args.max_changed_pixel_pct),
                    ("if text is visibly noisy, rerun build with text-fit report and collision QA enabled", mad > args.max_mad or changed > args.max_changed_pixel_pct),
                ] if enabled
            ],
            "heatmap": str(heat_path),
        })

        thumbs = [fit_width(ref, args.thumb_width), fit_width(render, args.thumb_width), fit_width(overlay, args.thumb_width)]
        row_h = max(t.height for t in thumbs) + 34
        row = Image.new("RGB", (args.thumb_width * 3 + 28, row_h), "white")
        draw = ImageDraw.Draw(row)
        labels = [f"Slide {idx} reference", f"Slide {idx} render", f"Slide {idx} diff"]
        for col, thumb in enumerate(thumbs):
            x = col * (args.thumb_width + 14)
            row.paste(thumb, (x, 30))
            draw.rectangle((x, 2, x + 220, 25), fill=(255, 255, 255))
            draw.text((x + 8, 6), labels[col], fill=(2, 64, 148))
        rows.append(row)

    sheet = Image.new("RGB", (max(r.width for r in rows), sum(r.height for r in rows) + 20 * (len(rows) - 1)), "white")
    y = 0
    for row in rows:
        sheet.paste(row, (0, y))
        y += row.height + 20
    sheet_path = out_dir / "contact_sheet.png"
    sheet.save(sheet_path)
    (out_dir / "comparison_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    status = "PASS" if all(item["status"] == "PASS" for item in metrics) else "REVIEW"
    print(json.dumps({"contact_sheet": str(sheet_path), "slides": len(metrics), "status": status}, ensure_ascii=False))


if __name__ == "__main__":
    main()
