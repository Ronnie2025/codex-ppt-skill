#!/usr/bin/env python3
"""Build an editable PPTX from semantic inventory and asset manifest files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt


EMU_PER_INCH = 914400
DEFAULT_SLIDE_W = 13.333333
DEFAULT_SLIDE_H = 7.5
VALID_ASSET_SOURCES = {"imagegen_asset", "api_generated_asset", "provided_asset"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", required=True, help="visual_inventory.json path.")
    parser.add_argument("--manifest", required=True, help="asset_manifest.json path.")
    parser.add_argument("--out-pptx", required=True, help="Output editable PPTX path.")
    parser.add_argument("--base-dir", help="Base directory for relative asset paths. Defaults to inventory parent.")
    parser.add_argument("--slide-width", type=float, default=DEFAULT_SLIDE_W, help="Slide width in inches.")
    parser.add_argument("--slide-height", type=float, default=DEFAULT_SLIDE_H, help="Slide height in inches.")
    parser.add_argument("--report", help="Optional JSON build report path.")
    return parser.parse_args()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def hex_to_rgb(value: str | None, default: str = "FFFFFF") -> RGBColor:
    value = (value or default).strip().lstrip("#")
    if len(value) != 6:
        value = default
    return RGBColor(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def rel_or_abs(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else base / path


def px_box_to_inches(box: list[float], slide_size_px: list[float], slide_w: float, slide_h: float) -> tuple[float, float, float, float]:
    if len(box) != 4:
        raise ValueError(f"bbox must contain 4 numbers: {box}")
    sx = slide_w / float(slide_size_px[0])
    sy = slide_h / float(slide_size_px[1])
    return box[0] * sx, box[1] * sy, box[2] * sx, box[3] * sy


def as_emu(value_in: float) -> int:
    return int(round(value_in * EMU_PER_INCH))


def add_text(slide, item: dict[str, Any], box: tuple[float, float, float, float], default_font: str) -> None:
    x, y, w, h = box
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    vertical = str(item.get("vertical_anchor", "middle")).lower()
    shape.vertical_anchor = {
        "top": MSO_ANCHOR.TOP,
        "middle": MSO_ANCHOR.MIDDLE,
        "bottom": MSO_ANCHOR.BOTTOM,
    }.get(vertical, MSO_ANCHOR.MIDDLE)
    if item.get("rotation") is not None:
        shape.rotation = float(item.get("rotation"))
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = bool(item.get("word_wrap", True))
    tf.margin_left = Inches(item.get("margin_left", 0.03))
    tf.margin_right = Inches(item.get("margin_right", 0.03))
    tf.margin_top = Inches(item.get("margin_top", 0.02))
    tf.margin_bottom = Inches(item.get("margin_bottom", 0.02))
    lines = str(item.get("text", "")).split("\n")
    p = tf.paragraphs[0]
    p.text = lines[0] if lines else ""
    align = str(item.get("align", "left")).lower()
    p.alignment = {
        "left": PP_ALIGN.LEFT,
        "center": PP_ALIGN.CENTER,
        "right": PP_ALIGN.RIGHT,
    }.get(align, PP_ALIGN.LEFT)
    for line in lines[1:]:
        next_p = tf.add_paragraph()
        next_p.text = line
        next_p.alignment = p.alignment
    for para in tf.paragraphs:
        if item.get("line_spacing") is not None:
            para.line_spacing = float(item.get("line_spacing"))
        for run in para.runs:
            run.font.name = item.get("font_face", default_font)
            run.font.size = Pt(float(item.get("font_size", 14)))
            run.font.bold = bool(item.get("bold", False))
            run.font.italic = bool(item.get("italic", False))
            run.font.color.rgb = hex_to_rgb(item.get("color"), "003B7A")


def add_native_shape(slide, item: dict[str, Any], box: tuple[float, float, float, float]) -> None:
    x, y, w, h = box
    shape_name = str(item.get("shape", "round_rect")).lower()
    shape_type = {
        "rect": MSO_SHAPE.RECTANGLE,
        "rectangle": MSO_SHAPE.RECTANGLE,
        "round_rect": MSO_SHAPE.ROUNDED_RECTANGLE,
        "rounded_rectangle": MSO_SHAPE.ROUNDED_RECTANGLE,
        "ellipse": MSO_SHAPE.OVAL,
        "oval": MSO_SHAPE.OVAL,
    }.get(shape_name, MSO_SHAPE.ROUNDED_RECTANGLE)
    shape = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    if item.get("rotation") is not None:
        shape.rotation = float(item.get("rotation"))
    fill = str(item.get("fill", "FFFFFF"))
    if fill.lower() in {"none", "transparent"}:
        shape.fill.background()
    else:
        shape.fill.solid()
        shape.fill.fore_color.rgb = hex_to_rgb(fill)
        transparency = float(item.get("fill_transparency", 0))
        if transparency:
            shape.fill.transparency = max(0, min(100, transparency)) / 100
    line = item.get("line", "C7DAF6")
    if str(line).lower() in {"none", "transparent"}:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = hex_to_rgb(str(line), "C7DAF6")
        shape.line.width = Pt(float(item.get("line_width", 1)))


def add_native_line(slide, item: dict[str, Any], box: tuple[float, float, float, float]) -> None:
    x, y, w, h = box
    connector = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT,
        Inches(x),
        Inches(y),
        Inches(x + w),
        Inches(y + h),
    )
    connector.line.color.rgb = hex_to_rgb(str(item.get("line", item.get("color", "5A93EA"))), "5A93EA")
    connector.line.width = Pt(float(item.get("line_width", 1.5)))


def fit_contain(img_path: Path, box: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    x, y, w, h = box
    with Image.open(img_path) as img:
        src_ratio = img.width / img.height
    slot_ratio = w / h
    if src_ratio > slot_ratio:
        fw = w
        fh = w / src_ratio
        fx = x
        fy = y + (h - fh) / 2
    else:
        fh = h
        fw = h * src_ratio
        fx = x + (w - fw) / 2
        fy = y
    return fx, fy, fw, fh


def add_asset(slide, item: dict[str, Any], asset: dict[str, Any], box: tuple[float, float, float, float], base_dir: Path) -> dict[str, Any]:
    source = asset.get("source_type")
    if source not in VALID_ASSET_SOURCES:
        raise ValueError(f"{item.get('id')} has invalid source_type: {source}")
    if asset.get("semantic_unit_count") != 1:
        raise ValueError(f"{item.get('id')} must have semantic_unit_count=1")
    img_path = rel_or_abs(base_dir, str(asset["asset_path"]))
    if not img_path.exists():
        raise FileNotFoundError(f"asset not found for {item.get('id')}: {img_path}")
    fx, fy, fw, fh = fit_contain(img_path, box)
    pic = slide.shapes.add_picture(str(img_path), Inches(fx), Inches(fy), width=Inches(fw), height=Inches(fh))
    if item.get("rotation") is not None:
        pic.rotation = float(item.get("rotation"))
    return {
        "semantic_unit_id": item.get("id"),
        "asset_path": str(img_path),
        "slot_in": [round(v, 4) for v in box],
        "fitted_in": [round(v, 4) for v in (fx, fy, fw, fh)],
    }


def get_items(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(inventory.get("slides"), list):
        items = []
        for idx, slide in enumerate(inventory["slides"], start=1):
            for item in slide.get("items", []):
                item = dict(item)
                item.setdefault("slide", idx)
                items.append(item)
        return sorted(items, key=lambda item: (int(item.get("slide", 1)), float(item.get("z_index", item.get("z", 0)))))
    return sorted([dict(item) for item in inventory.get("items", [])], key=lambda item: (int(item.get("slide", 1)), float(item.get("z_index", item.get("z", 0)))))


def main() -> None:
    args = parse_args()
    inventory_path = Path(args.inventory)
    manifest_path = Path(args.manifest)
    base_dir = Path(args.base_dir) if args.base_dir else inventory_path.parent
    inventory = read_json(inventory_path)
    manifest = read_json(manifest_path)
    manifest_by_id = {item["semantic_unit_id"]: item for item in manifest}
    slide_size_px = inventory.get("slide_size_px") or inventory.get("canvas_px") or [1920, 1080]
    default_font = inventory.get("font_face", "Arial Unicode MS")

    prs = Presentation()
    prs.slide_width = Inches(args.slide_width)
    prs.slide_height = Inches(args.slide_height)
    blank = prs.slide_layouts[6]
    slides = {}
    report = {"text_objects": 0, "native_layout_objects": 0, "asset_objects": 0, "asset_placements": []}

    for item in get_items(inventory):
        slide_no = int(item.get("slide", 1))
        while len(slides) < slide_no:
            slides[len(slides) + 1] = prs.slides.add_slide(blank)
        slide = slides[slide_no]
        cls = item.get("class") or item.get("type")
        bbox = item.get("bbox_px") or item.get("bbox")
        if not bbox:
            raise ValueError(f"item {item.get('id')} missing bbox_px")
        box = px_box_to_inches(bbox, slide_size_px, args.slide_width, args.slide_height)
        if cls == "text":
            add_text(slide, item, box, default_font)
            report["text_objects"] += 1
        elif cls == "layout_native":
            add_native_shape(slide, item, box)
            report["native_layout_objects"] += 1
        elif cls in {"line_native", "connector_native"}:
            add_native_line(slide, item, box)
            report["native_layout_objects"] += 1
        elif cls in {"imagegen_asset", "api_generated_asset", "provided_asset"}:
            asset = manifest_by_id.get(item.get("id"))
            if not asset:
                raise ValueError(f"no manifest entry for asset item: {item.get('id')}")
            report["asset_placements"].append(add_asset(slide, item, asset, box, base_dir))
            report["asset_objects"] += 1
        elif cls == "unresolved":
            raise ValueError(f"unresolved item cannot be built: {item.get('id')}")
        else:
            raise ValueError(f"unsupported item class for {item.get('id')}: {cls}")

    out_pptx = Path(args.out_pptx)
    out_pptx.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out_pptx)
    report["pptx"] = str(out_pptx)
    report["slide_count"] = len(slides)
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
