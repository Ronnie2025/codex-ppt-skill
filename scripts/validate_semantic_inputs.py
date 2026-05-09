#!/usr/bin/env python3
"""Preflight semantic visual-replica inventory, manifest, and anchors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ALLOWED_CLASSES = {
    "text",
    "layout_native",
    "line_native",
    "connector_native",
    "imagegen_asset",
    "api_generated_asset",
    "provided_asset",
    "unresolved",
}
SEMANTIC_CLASSES = {"imagegen_asset", "api_generated_asset", "provided_asset"}
ALLOWED_SOURCE_TYPES = {"imagegen_asset", "api_generated_asset", "provided_asset"}
FORBIDDEN_SOURCE_TYPES = {"raw_crop", "reference_crop", "screenshot_crop", "placeholder", "prompt_only_asset"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, help="visual_inventory.json path.")
    parser.add_argument("--manifest", help="asset_manifest.json path.")
    parser.add_argument("--anchors", help="asset_anchors.json path.")
    parser.add_argument("--stage", choices=["plan", "build"], default="build", help="Validation strictness.")
    parser.add_argument("--require-anchors", action="store_true", help="Require every semantic placement to have an anchor.")
    parser.add_argument("--out", help="Optional JSON report path.")
    return parser.parse_args()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def as_items(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(inventory.get("slides"), list):
        items: list[dict[str, Any]] = []
        for idx, slide in enumerate(inventory["slides"], start=1):
            if not isinstance(slide, dict):
                continue
            slide_no = slide.get("slide", idx)
            for item in slide.get("items", []):
                if isinstance(item, dict):
                    item = dict(item)
                    item.setdefault("slide", slide_no)
                    items.append(item)
        return items
    return [item for item in inventory.get("items", []) if isinstance(item, dict)]


def read_optional_list(path_value: str | None) -> list[dict[str, Any]] | None:
    if not path_value:
        return None
    data = read_json(Path(path_value))
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return [item for item in data["items"] if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get("anchors"), list):
        return [item for item in data["anchors"] if isinstance(item, dict)]
    return []


def valid_bbox(value: Any, allow_zero_axis: bool = False) -> bool:
    if not (
        isinstance(value, list)
        and len(value) == 4
        and all(isinstance(v, (int, float)) for v in value)
    ):
        return False
    if allow_zero_axis:
        return value[2] >= 0 and value[3] >= 0 and (value[2] > 0 or value[3] > 0)
    return value[2] > 0 and value[3] > 0


def rel_path(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def main() -> None:
    args = parse_args()
    inventory_path = Path(args.inventory)
    inventory = read_json(inventory_path)
    base_dir = inventory_path.parent
    errors: list[str] = []
    warnings: list[str] = []

    slide_size = inventory.get("slide_size_px") or inventory.get("canvas_px")
    if not (
        isinstance(slide_size, list)
        and len(slide_size) == 2
        and all(isinstance(v, (int, float)) and v > 0 for v in slide_size)
    ):
        errors.append("inventory missing valid slide_size_px")
        slide_size = [1, 1]

    items = as_items(inventory)
    seen_ids: set[str] = set()
    semantic_ids: list[str] = []
    for idx, item in enumerate(items):
        item_id = item.get("id")
        if not item_id:
            errors.append(f"inventory item {idx} missing id")
            continue
        if item_id in seen_ids:
            errors.append(f"duplicate inventory item id: {item_id}")
        seen_ids.add(str(item_id))

        cls = item.get("class") or item.get("type")
        if cls not in ALLOWED_CLASSES:
            errors.append(f"{item_id} has invalid class: {cls}")
        if cls == "unresolved" and args.stage == "build":
            errors.append(f"{item_id} is unresolved during build stage")
        bbox = item.get("bbox_px") or item.get("bbox")
        if not valid_bbox(bbox, allow_zero_axis=cls in {"line_native", "connector_native"}):
            errors.append(f"{item_id} missing valid bbox_px")
        elif slide_size != [1, 1]:
            x, y, w, h = bbox
            if x < -2 or y < -2 or x + w > float(slide_size[0]) + 2 or y + h > float(slide_size[1]) + 2:
                warnings.append(f"{item_id} bbox extends outside slide bounds")
        if cls in SEMANTIC_CLASSES:
            semantic_ids.append(str(item_id))
            if item.get("semantic_unit_count") not in {None, 1}:
                errors.append(f"{item_id} semantic_unit_count must be 1")

    manifest_items = read_optional_list(args.manifest)
    manifest_by_id: dict[str, dict[str, Any]] = {}
    if manifest_items is None:
        if args.stage == "build" and semantic_ids:
            errors.append("manifest is required for build stage")
    else:
        manifest_base = Path(args.manifest).parent if args.manifest else base_dir
        for idx, item in enumerate(manifest_items):
            sid = item.get("semantic_unit_id")
            if not sid:
                errors.append(f"manifest item {idx} missing semantic_unit_id")
                continue
            if sid in manifest_by_id:
                errors.append(f"duplicate manifest semantic_unit_id: {sid}")
            manifest_by_id[str(sid)] = item
            source_type = item.get("source_type")
            if source_type in FORBIDDEN_SOURCE_TYPES:
                errors.append(f"manifest item {sid} uses forbidden source_type: {source_type}")
            if source_type not in ALLOWED_SOURCE_TYPES:
                errors.append(f"manifest item {sid} has invalid source_type: {source_type}")
            if item.get("semantic_unit_count") != 1:
                errors.append(f"manifest item {sid} semantic_unit_count must be 1")
            asset_path = item.get("asset_path")
            if args.stage == "build":
                if not asset_path:
                    errors.append(f"manifest item {sid} missing asset_path")
                elif not rel_path(manifest_base, str(asset_path)).exists():
                    errors.append(f"manifest item {sid} asset file missing: {asset_path}")

    if manifest_items is not None:
        for sid in semantic_ids:
            if sid not in manifest_by_id:
                errors.append(f"semantic inventory item missing manifest entry: {sid}")

    anchors = read_optional_list(args.anchors)
    anchor_ids: set[str] = set()
    if anchors is not None:
        for idx, anchor in enumerate(anchors):
            sid = anchor.get("semantic_unit_id") or anchor.get("id")
            if not sid:
                errors.append(f"anchor {idx} missing semantic_unit_id")
                continue
            anchor_ids.add(str(sid))
            bbox = anchor.get("target_bbox_px") or anchor.get("bbox_px") or anchor.get("bbox")
            if not valid_bbox(bbox):
                errors.append(f"anchor {sid} missing valid target bbox")
            if anchor.get("placement_rule") and "stretch" in str(anchor.get("placement_rule")).lower() and "no one-axis" not in str(anchor.get("placement_rule")).lower():
                errors.append(f"anchor {sid} placement_rule appears to allow image stretch")
    elif args.require_anchors:
        errors.append("anchors file is required")

    if args.require_anchors and anchors is not None:
        for sid in semantic_ids:
            if sid not in anchor_ids:
                errors.append(f"semantic inventory item missing anchor: {sid}")

    report = {
        "status": "FAIL" if errors else "PASS",
        "stage": args.stage,
        "inventory_items": len(items),
        "semantic_items": len(semantic_ids),
        "manifest_entries": len(manifest_items) if manifest_items is not None else None,
        "anchor_entries": len(anchors) if anchors is not None else None,
        "errors": errors,
        "warnings": warnings,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
