#!/usr/bin/env python3
"""Clean transparent semantic asset PNG files after grid cutting."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from PIL import Image, ImageFilter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", default=[], help="PNG asset file. Repeat as needed.")
    parser.add_argument("--input-dir", help="Directory of PNG assets to clean.")
    parser.add_argument("--out-dir", help="Output directory. Required unless --in-place is set.")
    parser.add_argument("--in-place", action="store_true", help="Overwrite input files.")
    parser.add_argument("--trim-pad", type=int, default=4, help="Transparent trim padding in pixels.")
    parser.add_argument("--min-component-area", type=int, default=80, help="Remove alpha components smaller than this area.")
    parser.add_argument("--alpha-threshold", type=int, default=10, help="Pixels below this alpha become fully transparent.")
    parser.add_argument("--soften-alpha", type=float, default=0.0, help="Optional alpha blur radius.")
    parser.add_argument("--report", help="Optional JSON report path.")
    return parser.parse_args()


def trim_alpha(img: Image.Image, pad: int) -> Image.Image:
    bbox = img.getchannel("A").getbbox()
    if not bbox:
        return img
    left, top, right, bottom = bbox
    return img.crop((
        max(0, left - pad),
        max(0, top - pad),
        min(img.width, right + pad),
        min(img.height, bottom + pad),
    ))


def threshold_alpha(img: Image.Image, threshold: int) -> Image.Image:
    img = img.convert("RGBA")
    pix = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = pix[x, y]
            if a <= threshold:
                pix[x, y] = (255, 255, 255, 0)
    return img


def remove_small_components(img: Image.Image, min_area: int) -> Image.Image:
    if min_area <= 0:
        return img
    img = img.convert("RGBA")
    alpha = img.getchannel("A")
    w, h = alpha.size
    a = alpha.load()
    visited = bytearray(w * h)
    keep = bytearray(w * h)
    for yy in range(h):
        for xx in range(w):
            idx = yy * w + xx
            if visited[idx] or a[xx, yy] < 12:
                continue
            queue = deque([(xx, yy)])
            visited[idx] = 1
            comp = []
            while queue:
                x, y = queue.popleft()
                comp.append((x, y))
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if nx < 0 or ny < 0 or nx >= w or ny >= h:
                        continue
                    ni = ny * w + nx
                    if visited[ni] or a[nx, ny] < 12:
                        continue
                    visited[ni] = 1
                    queue.append((nx, ny))
            if len(comp) >= min_area:
                for x, y in comp:
                    keep[y * w + x] = 1
    pix = img.load()
    for yy in range(h):
        for xx in range(w):
            if a[xx, yy] >= 12 and not keep[yy * w + xx]:
                pix[xx, yy] = (255, 255, 255, 0)
    return img


def soften_alpha(img: Image.Image, radius: float) -> Image.Image:
    if radius <= 0:
        return img
    img = img.convert("RGBA")
    alpha = img.getchannel("A").filter(ImageFilter.GaussianBlur(radius))
    img.putalpha(alpha)
    return img


def input_files(args: argparse.Namespace) -> list[Path]:
    files = [Path(p) for p in args.input]
    if args.input_dir:
        files.extend(sorted(Path(args.input_dir).glob("*.png")))
    return files


def main() -> None:
    args = parse_args()
    files = input_files(args)
    if not files:
        raise SystemExit("no input PNG files")
    if not args.in_place and not args.out_dir:
        raise SystemExit("--out-dir is required unless --in-place is set")
    out_dir = Path(args.out_dir) if args.out_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for src in files:
        if not src.exists():
            raise SystemExit(f"missing input: {src}")
        img = Image.open(src).convert("RGBA")
        before = img.size
        img = threshold_alpha(img, args.alpha_threshold)
        img = remove_small_components(img, args.min_component_area)
        img = trim_alpha(img, args.trim_pad)
        img = soften_alpha(img, args.soften_alpha)
        dst = src if args.in_place else out_dir / src.name
        img.save(dst)
        rows.append({"input": str(src), "output": str(dst), "before_size": list(before), "after_size": list(img.size)})

    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"cleaned": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
