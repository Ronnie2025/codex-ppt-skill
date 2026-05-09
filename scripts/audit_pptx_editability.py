#!/usr/bin/env python3
"""Audit whether a PPTX is likely image-only or practically editable."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pptx", help="PPTX file to audit.")
    parser.add_argument("--json", dest="json_path", help="Optional JSON report path.")
    return parser.parse_args()


def natural_slide_key(name: str) -> list[object]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", name)]


def audit_pptx(pptx_path: Path) -> dict:
    with zipfile.ZipFile(pptx_path) as zf:
        names = zf.namelist()
        media = [name for name in names if name.startswith("ppt/media/")]
        slides = sorted(
            [name for name in names if re.match(r"ppt/slides/slide\d+\.xml$", name)],
            key=natural_slide_key,
        )
        slide_reports = []
        for idx, name in enumerate(slides, start=1):
            root = ET.fromstring(zf.read(name))
            text_runs = [node.text or "" for node in root.findall(".//a:t", NS)]
            text_chars = sum(len(text.strip()) for text in text_runs)
            shape_count = len(root.findall(".//p:sp", NS))
            picture_count = len(root.findall(".//p:pic", NS))
            group_count = len(root.findall(".//p:grpSp", NS))
            graphic_frame_count = len(root.findall(".//p:graphicFrame", NS))
            flags = []
            if picture_count > 0 and text_chars == 0 and shape_count <= 1:
                flags.append("likely_image_only_slide")
            if text_chars > 0 and picture_count > 0:
                flags.append("mixed_native_text_and_images")
            if group_count > 20:
                flags.append("many_group_shapes_may_be_fragile")
            slide_reports.append(
                {
                    "slide": idx,
                    "shape_count": shape_count,
                    "picture_count": picture_count,
                    "group_count": group_count,
                    "graphic_frame_count": graphic_frame_count,
                    "text_run_count": len(text_runs),
                    "text_char_count": text_chars,
                    "flags": flags,
                }
            )

    media_by_ext: dict[str, int] = {}
    for item in media:
        ext = Path(item).suffix.lower() or "<none>"
        media_by_ext[ext] = media_by_ext.get(ext, 0) + 1

    deck_flags = []
    if all("likely_image_only_slide" in slide["flags"] for slide in slide_reports):
        deck_flags.append("deck_looks_image_only")
    if media_by_ext.get(".svg", 0) > 0:
        deck_flags.append("contains_svg_media_check_powerpoint_editability")

    return {
        "pptx": str(pptx_path),
        "slide_count": len(slide_reports),
        "media_count": len(media),
        "media_by_ext": media_by_ext,
        "deck_flags": deck_flags,
        "slides": slide_reports,
    }


def print_report(report: dict) -> None:
    print(f"PPTX: {report['pptx']}")
    print(f"Slides: {report['slide_count']} | Media: {report['media_count']} | Flags: {', '.join(report['deck_flags']) or 'none'}")
    for slide in report["slides"]:
        flags = ", ".join(slide["flags"]) or "none"
        print(
            f"- slide {slide['slide']:02d}: text={slide['text_char_count']} chars, "
            f"shapes={slide['shape_count']}, pics={slide['picture_count']}, "
            f"groups={slide['group_count']}, frames={slide['graphic_frame_count']}, flags={flags}"
        )


def main() -> None:
    args = parse_args()
    report = audit_pptx(Path(args.pptx))
    print_report(report)
    if args.json_path:
        out = Path(args.json_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
