#!/usr/bin/env python3
"""Cut image-generated asset grids into transparent per-object PNG assets."""

from __future__ import annotations

import argparse
import json
from collections import deque
from pathlib import Path
from typing import Any

from PIL import Image


VALID_SOURCE_TYPES = {"imagegen_asset", "api_generated_asset", "provided_asset"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grid", help="Generated asset grid image.")
    parser.add_argument("--rows", type=int, help="Grid row count.")
    parser.add_argument("--cols", type=int, help="Grid column count.")
    parser.add_argument("--names", help="Comma-separated asset ids or a JSON file containing a string list.")
    parser.add_argument("--grid-manifest", help="JSON prompt/grid manifest. Supports one or many grids.")
    parser.add_argument("--out-dir", required=True, help="Output directory for cut PNG assets.")
    parser.add_argument("--manifest-out", help="Optional asset_manifest.json output path.")
    parser.add_argument("--source-type", default="imagegen_asset", choices=sorted(VALID_SOURCE_TYPES), help="Source type written to manifest.")
    parser.add_argument("--background", default="chroma", choices=["chroma", "white", "auto"], help="Background removal mode.")
    parser.add_argument("--chroma", default="00ff00", help="Chroma key color as RRGGBB. Default: 00ff00.")
    parser.add_argument("--tolerance", type=int, default=70, help="Background color distance tolerance.")
    parser.add_argument("--trim-pad", type=int, default=4, help="Transparent trim padding in pixels.")
    parser.add_argument("--min-component-area", type=int, default=80, help="Remove alpha components smaller than this area.")
    parser.add_argument("--absolute-paths", action="store_true", help="Write absolute asset paths to manifest.")
    return parser.parse_args()


def load_names(value: str | list[Any]) -> list[str]:
    if isinstance(value, list):
        names = []
        for item in value:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict):
                sid = item.get("semantic_unit_id") or item.get("id") or item.get("name")
                if sid:
                    names.append(str(sid))
        return names
    path = Path(value)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return load_names(data)
    return [x.strip() for x in value.split(",") if x.strip()]


def hex_rgb(value: str) -> tuple[int, int, int]:
    value = value.strip().lstrip("#")
    if len(value) != 6:
        raise SystemExit("--chroma must be RRGGBB")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def bg_distance(pixel: tuple[int, int, int, int], target: tuple[int, int, int]) -> int:
    r, g, b, _ = pixel
    tr, tg, tb = target
    return abs(r - tr) + abs(g - tg) + abs(b - tb)


def remove_background(img: Image.Image, mode: str, chroma: tuple[int, int, int], tolerance: int) -> Image.Image:
    img = img.convert("RGBA")
    pix = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = pix[x, y]
            remove = False
            if mode in {"chroma", "auto"}:
                remove = bg_distance((r, g, b, a), chroma) <= tolerance or (g > 150 and r < 140 and b < 140)
            if mode in {"white", "auto"} and not remove:
                remove = r >= 245 and g >= 245 and b >= 245
            if remove:
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


def normalize_grid_specs(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.grid_manifest:
        manifest_path = Path(args.grid_manifest)
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("grids"), list):
            grids = data["grids"]
        elif isinstance(data, list):
            grids = data
        elif isinstance(data, dict):
            grids = [data]
        else:
            raise SystemExit("--grid-manifest must contain an object or list")
        specs = []
        for spec in grids:
            if not isinstance(spec, dict):
                raise SystemExit("grid manifest entries must be objects")
            grid_meta = spec.get("grid") if isinstance(spec.get("grid"), dict) else {}
            grid = spec.get("output") or spec.get("grid_image") or (spec.get("grid") if isinstance(spec.get("grid"), str) else None)
            if not grid:
                raise SystemExit("grid manifest entry missing grid/output")
            grid_path = Path(grid)
            if not grid_path.is_absolute():
                grid_path = manifest_path.parent / grid_path
            rows = spec.get("rows") or spec.get("grid_rows") or grid_meta.get("rows")
            cols = spec.get("cols") or spec.get("grid_cols") or grid_meta.get("cols")
            if not rows or not cols:
                raise SystemExit("grid manifest entry missing rows/cols")
            objects = spec.get("objects") or spec.get("names")
            specs.append({
                "grid": str(grid_path),
                "rows": int(rows),
                "cols": int(cols),
                "names": load_names(objects),
                "prompt_id": spec.get("prompt_id"),
                "source_reference": spec.get("source_reference") or spec.get("reference"),
                "quality_notes": spec.get("quality_notes"),
                "source_type": spec.get("source_type") or args.source_type,
                "background": spec.get("background") or args.background,
                "chroma": spec.get("chroma") or args.chroma,
                "tolerance": int(spec.get("tolerance") or args.tolerance),
            })
        return specs
    if not (args.grid and args.rows and args.cols and args.names):
        raise SystemExit("either --grid-manifest or --grid/--rows/--cols/--names is required")
    return [{
        "grid": args.grid,
        "rows": args.rows,
        "cols": args.cols,
        "names": load_names(args.names),
        "prompt_id": None,
        "source_reference": None,
        "quality_notes": None,
        "source_type": args.source_type,
        "background": args.background,
        "chroma": args.chroma,
        "tolerance": args.tolerance,
    }]


def manifest_path_for(out: Path, manifest_out: str | None, absolute: bool) -> str:
    if absolute or not manifest_out:
        return str(out)
    try:
        return str(out.relative_to(Path(manifest_out).parent))
    except ValueError:
        return str(out)


def cut_one_grid(spec: dict[str, Any], out_dir: Path, args: argparse.Namespace) -> list[dict[str, Any]]:
    names = spec["names"]
    rows = int(spec["rows"])
    cols = int(spec["cols"])
    expected = rows * cols
    if len(names) != expected:
        raise SystemExit(f"expected {expected} names for {rows}x{cols}, got {len(names)}")
    source_type = spec.get("source_type") or args.source_type
    if source_type not in VALID_SOURCE_TYPES:
        raise SystemExit(f"invalid source_type: {source_type}")

    grid_path = Path(spec["grid"])
    src = Image.open(grid_path).convert("RGBA")
    cell_w = src.width / cols
    cell_h = src.height / rows
    chroma = hex_rgb(spec.get("chroma") or args.chroma)
    manifest = []

    for idx, name in enumerate(names):
        row, col = divmod(idx, cols)
        box = (
            int(round(col * cell_w)),
            int(round(row * cell_h)),
            int(round((col + 1) * cell_w)),
            int(round((row + 1) * cell_h)),
        )
        asset = src.crop(box)
        asset = remove_background(asset, spec.get("background") or args.background, chroma, int(spec.get("tolerance") or args.tolerance))
        asset = remove_small_components(asset, args.min_component_area)
        asset = trim_alpha(asset, args.trim_pad)
        out = out_dir / f"{name}.png"
        asset.save(out)
        manifest.append({
            "semantic_unit_id": name,
            "source_type": source_type,
            "asset_path": manifest_path_for(out, args.manifest_out, args.absolute_paths),
            "semantic_unit_count": 1,
            "generated_grid": str(grid_path),
            "grid_cell": [row, col],
            "prompt_id": spec.get("prompt_id"),
            "source_reference": spec.get("source_reference"),
            "quality_notes": spec.get("quality_notes"),
        })
    return manifest


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = []
    for spec in normalize_grid_specs(args):
        manifest.extend(cut_one_grid(spec, out_dir, args))

    if args.manifest_out:
        Path(args.manifest_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.manifest_out).write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"assets": len(manifest), "out_dir": str(out_dir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
