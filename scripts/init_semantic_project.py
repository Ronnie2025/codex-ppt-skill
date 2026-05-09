#!/usr/bin/env python3
"""Initialize a reusable semantic visual-replica project folder."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from PIL import Image


SUBDIRS = [
    "reference",
    "reference_crops",
    "generated",
    "assets",
    "render",
    "compare",
    "reports",
    "prompts",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", required=True, help="Project directory to create.")
    parser.add_argument("--reference", action="append", default=[], help="Reference slide image. Repeat per slide.")
    parser.add_argument("--force", action="store_true", help="Allow writing into an existing directory.")
    return parser.parse_args()


def slide_size(path: Path) -> list[int]:
    with Image.open(path) as img:
        return [img.width, img.height]


def main() -> None:
    args = parse_args()
    out = Path(args.out_dir)
    if out.exists() and any(out.iterdir()) and not args.force:
        raise SystemExit(f"{out} already exists and is not empty; pass --force to reuse it")
    out.mkdir(parents=True, exist_ok=True)
    for subdir in SUBDIRS:
        (out / subdir).mkdir(parents=True, exist_ok=True)

    references = []
    slide_px = [1920, 1080]
    for idx, ref in enumerate(args.reference, start=1):
        src = Path(ref)
        if not src.exists():
            raise SystemExit(f"reference image not found: {src}")
        ext = src.suffix.lower() or ".png"
        dst = out / "reference" / f"page-{idx:02d}{ext}"
        shutil.copy2(src, dst)
        size = slide_size(dst)
        if idx == 1:
            slide_px = size
        references.append({"slide": idx, "path": str(dst.relative_to(out)), "size_px": size})

    inventory = {
        "slide_size_px": slide_px,
        "final_deck_type": "semantic_editable_replica",
        "source_image_policy": "reference only; do not embed the full source image in the final PPTX",
        "font_face": "Microsoft YaHei",
        "references": references,
        "slides": [
            {
                "slide": ref["slide"],
                "reference": ref["path"],
                "items": [],
            }
            for ref in references
        ] or [{"slide": 1, "reference": "", "items": []}],
    }
    layout_rules = {
        "slide_size_px": slide_px,
        "font_policy": {
            "default_font_face": "Microsoft YaHei",
            "text_box_extra_room_pct": 12,
        },
        "image_fit": "uniform_contain_only",
        "allowed_source_types": ["imagegen_asset", "api_generated_asset", "provided_asset"],
        "forbidden_media": [
            "full_slide_reference_image",
            "near_full_slide_reference_image",
            "svg_media",
            "raw_crop_asset",
            "prompt_only_asset",
        ],
        "comparison": {
            "diff_threshold": 18,
            "changed_pixel_pct_target": 0.25,
        },
    }
    prompt_stub = {
        "slide": 1,
        "prompt_id": "assets_cycle_1_grid_01",
        "output": "generated/assets_cycle_1_grid_01.png",
        "grid": {"rows": 1, "cols": 1},
        "objects": [{"semantic_unit_id": "domain_icon_01", "description": "replace with target semantic visual"}],
        "prompt": "Create an isolated asset grid for a PowerPoint visual replica. Use the full reference and crops for style. No readable text, no numbers, no labels, no watermark.",
        "negative": "no card frames, no crop borders, no fake logos, no surrounding slide context",
    }

    (out / "visual_inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "asset_anchors.json").write_text("[]\n", encoding="utf-8")
    (out / "asset_manifest.json").write_text("[]\n", encoding="utf-8")
    (out / "layout_rules.json").write_text(json.dumps(layout_rules, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "prompts" / "assets_cycle_1.jsonl").write_text(json.dumps(prompt_stub, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "conversion_report.md").write_text(
        "# Semantic Visual-Replica Conversion Report\n\n"
        "- Reference images: see `reference/`\n"
        "- Generated grids: see `generated/`\n"
        "- Final assets: see `assets/`\n"
        "- Render comparison: see `compare/`\n"
        "- Validation reports: see `reports/`\n",
        encoding="utf-8",
    )
    print(json.dumps({"project": str(out), "references": len(references)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
