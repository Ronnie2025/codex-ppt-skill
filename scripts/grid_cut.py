#!/usr/bin/env python3
"""Cut an image-generated asset grid into transparent per-object PNG assets."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", required=True, help="Generated asset grid image.")
    parser.add_argument("--rows", type=int, required=True, help="Grid row count.")
    parser.add_argument("--cols", type=int, required=True, help="Grid column count.")
    parser.add_argument("--names", required=True, help="Comma-separated asset ids or a JSON file containing a string list.")
    parser.add_argument("--out-dir", required=True, help="Output directory for cut PNG assets.")
    parser.add_argument("--manifest-out", help="Optional asset_manifest.json output path.")
    parser.add_argument("--chroma", default="00ff00", help="Chroma key color as RRGGBB. Default: 00ff00.")
    parser.add_argument("--tolerance", type=int, default=70, help="Chroma key distance tolerance.")
    parser.add_argument("--trim-pad", type=int, default=4, help="Transparent trim padding in pixels.")
    parser.add_argument("--min-component-area", type=int, default=80, help="Remove alpha components smaller than this area.")
    return parser.parse_args()


def load_names(value: str) -> list[str]:
    path = Path(value)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
            raise SystemExit("--names JSON must be a list of strings")
        return data
    return [x.strip() for x in value.split(",") if x.strip()]


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise SystemExit("--chroma must be RRGGBB")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def remove_chroma(img: Image.Image, chroma: tuple[int, int, int], tolerance: int) -> Image.Image:
    img = img.convert("RGBA")
    cr, cg, cb = chroma
    pix = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = pix[x, y]
            dist = abs(r - cr) + abs(g - cg) + abs(b - cb)
            if dist <= tolerance or (g > 150 and r < 130 and b < 130):
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
            q = deque([(xx, yy)])
            visited[idx] = 1
            comp = []
            while q:
                x, y = q.popleft()
                comp.append((x, y))
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if nx < 0 or ny < 0 or nx >= w or ny >= h:
                        continue
                    ni = ny * w + nx
                    if visited[ni] or a[nx, ny] < 12:
                        continue
                    visited[ni] = 1
                    q.append((nx, ny))
            if len(comp) >= min_area:
                for x, y in comp:
                    keep[y * w + x] = 1
    pix = img.load()
    for yy in range(h):
        for xx in range(w):
            if a[xx, yy] >= 12 and not keep[yy * w + xx]:
                pix[xx, yy] = (255, 255, 255, 0)
    return img


def trim_alpha(img: Image.Image, pad: int) -> Image.Image:
    alpha = img.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        return img
    left, top, right, bottom = bbox
    return img.crop((
        max(0, left - pad),
        max(0, top - pad),
        min(img.width, right + pad),
        min(img.height, bottom + pad),
    ))


def main() -> None:
    args = parse_args()
    names = load_names(args.names)
    expected = args.rows * args.cols
    if len(names) != expected:
        raise SystemExit(f"expected {expected} names for {args.rows}x{args.cols}, got {len(names)}")

    grid_path = Path(args.grid)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    src = Image.open(grid_path).convert("RGBA")
    cell_w = src.width / args.cols
    cell_h = src.height / args.rows
    chroma = hex_rgb(args.chroma)
    manifest = []

    for idx, name in enumerate(names):
        row, col = divmod(idx, args.cols)
        box = (
            int(round(col * cell_w)),
            int(round(row * cell_h)),
            int(round((col + 1) * cell_w)),
            int(round((row + 1) * cell_h)),
        )
        asset = src.crop(box)
        asset = remove_chroma(asset, chroma, args.tolerance)
        asset = remove_small_components(asset, args.min_component_area)
        asset = trim_alpha(asset, args.trim_pad)
        out = out_dir / f"{name}.png"
        asset.save(out)
        manifest.append({
            "semantic_unit_id": name,
            "source_type": "imagegen_asset",
            "asset_path": str(out),
            "semantic_unit_count": 1,
            "generated_grid": str(grid_path),
            "grid_cell": [row, col],
        })

    if args.manifest_out:
        Path(args.manifest_out).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"assets": len(manifest), "out_dir": str(out_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
