#!/usr/bin/env python3
"""Validate a semantic editable PPTX reconstruction."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pptx", required=True, help="PPTX to validate.")
    parser.add_argument("--reference", action="append", default=[], help="Reference image to hash-check. Repeat per slide.")
    parser.add_argument("--manifest", help="asset_manifest.json path.")
    parser.add_argument("--inventory", help="visual_inventory.json path.")
    parser.add_argument("--out", required=True, help="Markdown validation report path.")
    parser.add_argument("--full-slide-size", default="", help="Optional WxH full-slide media size to reject, e.g. 1672x941.")
    parser.add_argument("--near-full-slide-ratio", type=float, default=0.85, help="Flag media covering at least this share of full-slide area.")
    return parser.parse_args()


def parse_size(value: str) -> tuple[int, int] | None:
    if not value:
        return None
    match = re.fullmatch(r"(\d+)x(\d+)", value)
    if not match:
        raise SystemExit("--full-slide-size must be WxH")
    return int(match.group(1)), int(match.group(2))


def count_slide_objects(zf: ZipFile) -> list[dict]:
    slides = sorted(
        [n for n in zf.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)],
        key=lambda n: int(re.search(r"slide(\d+)", n).group(1)),
    )
    rows = []
    for slide_name in slides:
        xml = zf.read(slide_name).decode("utf-8", errors="ignore")
        rows.append({
            "slide_xml": slide_name,
            "picture_objects": xml.count("<p:pic>"),
            "shape_objects": xml.count("<p:sp>"),
            "text_runs": xml.count("<a:t>"),
        })
    return rows


def inventory_items(inventory: object) -> list[dict]:
    if not isinstance(inventory, dict):
        return []
    if isinstance(inventory.get("slides"), list):
        items = []
        for slide in inventory["slides"]:
            if isinstance(slide, dict):
                items.extend([item for item in slide.get("items", []) if isinstance(item, dict)])
        return items
    return [item for item in inventory.get("items", []) if isinstance(item, dict)]


def main() -> None:
    args = parse_args()
    pptx = Path(args.pptx)
    reject_size = parse_size(args.full_slide_size)
    ref_hashes = {}
    for ref in args.reference:
        path = Path(ref)
        ref_hashes[hashlib.sha256(path.read_bytes()).hexdigest()] = str(path)

    errors = []
    media = []
    exact_ref_hits = []
    full_slide_hits = []
    near_full_slide_hits = []
    svg_media = []

    with ZipFile(pptx) as zf:
        bad_member = zf.testzip()
        if bad_member:
            errors.append(f"zip test failed at {bad_member}")
        for name in sorted(n for n in zf.namelist() if n.startswith("ppt/media/")):
            data = zf.read(name)
            sha = hashlib.sha256(data).hexdigest()
            dims = None
            try:
                with Image.open(BytesIO(data)) as img:
                    dims = img.size
            except Exception:
                pass
            item = {"name": name, "bytes": len(data), "size": list(dims) if dims else None}
            media.append(item)
            if Path(name).suffix.lower() == ".svg":
                svg_media.append(item)
            if sha in ref_hashes:
                exact_ref_hits.append({"name": name, "reference": ref_hashes[sha]})
            if reject_size and dims == reject_size:
                full_slide_hits.append(item)
            if reject_size and dims:
                media_area = dims[0] * dims[1]
                slide_area = reject_size[0] * reject_size[1]
                if media_area >= slide_area * args.near_full_slide_ratio:
                    near_full_slide_hits.append(item)
        slide_counts = count_slide_objects(zf)

    if exact_ref_hits:
        errors.append("reference image hash found in PPTX media")
    if full_slide_hits:
        errors.append(f"full-slide media size found: {reject_size[0]}x{reject_size[1]}")
    if near_full_slide_hits:
        errors.append("near-full-slide media found")
    if svg_media:
        errors.append("svg media found in semantic PPTX")

    manifest = None
    manifest_by_id = {}
    if args.manifest:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        for idx, item in enumerate(manifest):
            if item.get("semantic_unit_count") != 1:
                errors.append(f"manifest item {idx} is not semantic_unit_count=1")
            if item.get("source_type") not in {"imagegen_asset", "api_generated_asset", "provided_asset"}:
                errors.append(f"manifest item {idx} has invalid source_type")
            if item.get("source_type") in {"raw_crop", "reference_crop", "screenshot_crop", "placeholder", "prompt_only_asset"}:
                errors.append(f"manifest item {idx} has forbidden source_type")
            asset_path = item.get("asset_path")
            if asset_path:
                manifest_path = Path(args.manifest)
                resolved = Path(asset_path)
                if not resolved.is_absolute():
                    resolved = manifest_path.parent / resolved
                if not resolved.exists():
                    errors.append(f"manifest item {idx} asset file missing: {asset_path}")
            if item.get("semantic_unit_id") in manifest_by_id:
                errors.append(f"duplicate manifest semantic_unit_id: {item.get('semantic_unit_id')}")
            manifest_by_id[item.get("semantic_unit_id")] = item

    inventory = None
    semantic_inventory_items = []
    if args.inventory:
        inventory = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
        semantic_inventory_items = [
            item for item in inventory_items(inventory)
            if item.get("class") in {"imagegen_asset", "api_generated_asset", "provided_asset"}
            or item.get("type") in {"imagegen_asset", "api_generated_asset", "provided_asset"}
        ]
        if manifest is not None:
            for item in semantic_inventory_items:
                item_id = item.get("id")
                if item_id not in manifest_by_id:
                    errors.append(f"inventory semantic item missing manifest entry: {item_id}")

    total_picture_objects = sum(row["picture_objects"] for row in slide_counts)
    if manifest is not None and total_picture_objects < len(manifest):
        errors.append("pptx picture object count is lower than manifest entries")
    total_text_runs = sum(row["text_runs"] for row in slide_counts)
    status = "PASS"
    if errors:
        status = "FAIL"
    elif inventory is None or manifest is None or not semantic_inventory_items or total_text_runs == 0:
        status = "DRAFT_ONLY"

    report = [
        "# Semantic PPTX Validation Report",
        "",
        f"- PPTX: `{pptx}`",
        f"- Zip integrity: {'PASS' if not any(e.startswith('zip test') for e in errors) else 'FAIL'}",
        f"- Result status: {status}",
        f"- Slide count: {len(slide_counts)}",
        f"- Media object count: {len(media)}",
        f"- Exact reference image hash check: {'PASS' if not exact_ref_hits else 'FAIL'}",
        f"- Full-slide media check: {'PASS' if not full_slide_hits else 'FAIL'}",
        f"- Near-full-slide media check: {'PASS' if not near_full_slide_hits else 'FAIL'}",
        f"- SVG media check: {'PASS' if not svg_media else 'FAIL'}",
        f"- Manifest entries: {len(manifest) if manifest is not None else 'not provided'}",
        f"- Inventory provided: {'yes' if inventory is not None else 'no'}",
        f"- Inventory semantic asset items: {len(semantic_inventory_items)}",
        f"- PPT picture objects: {total_picture_objects}",
        f"- PPT text runs: {total_text_runs}",
        "",
        "## Slide Object Counts",
    ]
    for row in slide_counts:
        report.append(
            f"- {row['slide_xml']}: pictures {row['picture_objects']}, shapes {row['shape_objects']}, text runs {row['text_runs']}"
        )
    report += ["", "## Largest Embedded Media"]
    for item in sorted(media, key=lambda m: (m["size"] or [0, 0])[0] * (m["size"] or [0, 0])[1], reverse=True)[:10]:
        report.append(f"- {item['name']}: size {item['size']}, bytes {item['bytes']}")
    report += ["", "## Result"]
    if status == "FAIL":
        report.extend([f"- FAIL: {err}" for err in errors])
    elif status == "DRAFT_ONLY":
        report.append("- DRAFT_ONLY: no hard media violation found, but manifest, inventory, semantic assets, or native text evidence is incomplete.")
    else:
        report.append("- PASS: no reference image hash, rejected full-slide media, SVG media, invalid manifest entries, or manifest/object mismatch found.")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(out), "status": status, "errors": errors}, ensure_ascii=False))


if __name__ == "__main__":
    main()
