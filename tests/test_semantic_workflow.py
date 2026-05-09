#!/usr/bin/env python3
"""Regression tests for the reusable semantic visual-replica workflow."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "output" / "tests" / "semantic_workflow"


def run_cmd(*args: str, expect_ok: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if expect_ok and result.returncode != 0:
        raise AssertionError(f"command failed: {args}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
    if not expect_ok and result.returncode == 0:
        raise AssertionError(f"command unexpectedly passed: {args}\nSTDOUT:\n{result.stdout}")
    return result


def make_grid(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", (800, 400), (0, 255, 0, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse((80, 70, 250, 240), fill=(18, 100, 220, 255))
    draw.rounded_rectangle((500, 70, 660, 240), radius=28, fill=(255, 74, 74, 255))
    draw.polygon([(130, 305), (250, 345), (130, 385)], fill=(80, 145, 235, 255))
    draw.rounded_rectangle((500, 300, 660, 380), radius=22, fill=(35, 190, 120, 255))
    img.save(path)


def make_reference(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (1920, 1080), "white")
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((90, 80, 1830, 990), radius=40, fill=(248, 251, 255), outline=(190, 216, 250), width=4)
    draw.rectangle((120, 900, 1800, 960), fill=(2, 64, 148))
    img.save(path)


class SemanticWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        if WORK.exists():
            shutil.rmtree(WORK)
        WORK.mkdir(parents=True)

    def test_positive_multislide_workflow(self) -> None:
        make_grid(WORK / "generated" / "semantic_grid.png")
        make_reference(WORK / "reference" / "page-01.png")
        make_reference(WORK / "reference" / "page-02.png")

        grid_manifest = {
            "grids": [
                {
                    "prompt_id": "fixture_grid_01",
                    "output": "generated/semantic_grid.png",
                    "grid": {"rows": 2, "cols": 2},
                    "objects": [
                        {"semantic_unit_id": "domain_icon_01"},
                        {"semantic_unit_id": "risk_badge_01"},
                        {"semantic_unit_id": "workflow_arrow_01"},
                        {"semantic_unit_id": "status_pill_01"},
                    ],
                    "background": "chroma",
                }
            ]
        }
        (WORK / "grid_manifest.json").write_text(json.dumps(grid_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        run_cmd(
            "scripts/grid_cut.py",
            "--grid-manifest",
            str(WORK / "grid_manifest.json"),
            "--out-dir",
            str(WORK / "assets"),
            "--manifest-out",
            str(WORK / "asset_manifest.json"),
        )

        inventory = {
            "slide_size_px": [1920, 1080],
            "final_deck_type": "semantic_editable_replica",
            "source_image_policy": "reference only; do not embed the full source image in the final PPTX",
            "font_face": "Microsoft YaHei",
            "slides": [
                {
                    "slide": 1,
                    "reference": "reference/page-01.png",
                    "items": [
                        {"id": "s1_bg", "class": "layout_native", "bbox_px": [90, 80, 1740, 910], "fill": "F8FBFF", "line": "C8DBF6", "z_index": 0},
                        {"id": "s1_title", "class": "text", "text": "Semantic replica fixture", "bbox_px": [130, 110, 920, 70], "font_size": 28, "bold": True, "z_index": 5},
                        {"id": "domain_icon_01", "class": "imagegen_asset", "bbox_px": [180, 240, 180, 180], "semantic_unit_count": 1, "z_index": 10},
                        {"id": "workflow_arrow_01", "class": "imagegen_asset", "bbox_px": [430, 300, 260, 80], "semantic_unit_count": 1, "z_index": 10},
                        {"id": "s1_footer", "class": "layout_native", "bbox_px": [120, 900, 1680, 60], "fill": "024094", "line": "024094", "z_index": 2},
                        {"id": "s1_footer_text", "class": "text", "text": "Native text + generated semantic assets", "bbox_px": [180, 912, 1500, 34], "font_size": 16, "bold": True, "color": "FFFFFF", "align": "center", "z_index": 6},
                    ],
                },
                {
                    "slide": 2,
                    "reference": "reference/page-02.png",
                    "items": [
                        {"id": "s2_bg", "class": "layout_native", "bbox_px": [90, 80, 1740, 910], "fill": "F8FBFF", "line": "C8DBF6", "z_index": 0},
                        {"id": "s2_title", "class": "text", "text": "Second slide", "bbox_px": [130, 110, 920, 70], "font_size": 28, "bold": True, "z_index": 5},
                        {"id": "risk_badge_01", "class": "imagegen_asset", "bbox_px": [180, 260, 160, 160], "semantic_unit_count": 1, "z_index": 10},
                        {"id": "status_pill_01", "class": "imagegen_asset", "bbox_px": [430, 260, 180, 120], "semantic_unit_count": 1, "z_index": 10},
                        {"id": "s2_line", "class": "line_native", "bbox_px": [700, 340, 420, 0], "line": "5A93EA", "line_width": 2, "z_index": 7},
                    ],
                },
            ],
        }
        anchors = [
            {"semantic_unit_id": "domain_icon_01", "slide": 1, "target_bbox_px": [180, 240, 180, 180], "placement_rule": "uniform contain scaling; no one-axis stretch"},
            {"semantic_unit_id": "workflow_arrow_01", "slide": 1, "target_bbox_px": [430, 300, 260, 80], "placement_rule": "uniform contain scaling; no one-axis stretch"},
            {"semantic_unit_id": "risk_badge_01", "slide": 2, "target_bbox_px": [180, 260, 160, 160], "placement_rule": "uniform contain scaling; no one-axis stretch"},
            {"semantic_unit_id": "status_pill_01", "slide": 2, "target_bbox_px": [430, 260, 180, 120], "placement_rule": "uniform contain scaling; no one-axis stretch"},
        ]
        (WORK / "visual_inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
        (WORK / "asset_anchors.json").write_text(json.dumps(anchors, ensure_ascii=False, indent=2), encoding="utf-8")

        run_cmd(
            "scripts/validate_semantic_inputs.py",
            "--inventory",
            str(WORK / "visual_inventory.json"),
            "--manifest",
            str(WORK / "asset_manifest.json"),
            "--anchors",
            str(WORK / "asset_anchors.json"),
            "--require-anchors",
            "--stage",
            "build",
            "--out",
            str(WORK / "reports" / "preflight.json"),
        )
        run_cmd(
            "scripts/build_semantic_deck.py",
            "--inventory",
            str(WORK / "visual_inventory.json"),
            "--manifest",
            str(WORK / "asset_manifest.json"),
            "--base-dir",
            str(WORK),
            "--out-pptx",
            str(WORK / "reconstructed.pptx"),
            "--report",
            str(WORK / "reports" / "build_report.json"),
        )
        build_report = json.loads((WORK / "reports" / "build_report.json").read_text(encoding="utf-8"))
        self.assertIn("layout_qa", build_report)
        self.assertEqual(build_report["layout_qa"]["error_count"], 0)
        self.assertEqual(build_report["text_objects"], len(build_report["text_placements"]))
        result = run_cmd(
            "scripts/validate_semantic_deck.py",
            "--pptx",
            str(WORK / "reconstructed.pptx"),
            "--reference",
            str(WORK / "reference" / "page-01.png"),
            "--reference",
            str(WORK / "reference" / "page-02.png"),
            "--manifest",
            str(WORK / "asset_manifest.json"),
            "--inventory",
            str(WORK / "visual_inventory.json"),
            "--build-report",
            str(WORK / "reports" / "build_report.json"),
            "--full-slide-size",
            "1920x1080",
            "--out",
            str(WORK / "reports" / "validation_report.md"),
        )
        self.assertIn('"status": "PASS"', result.stdout)

    def test_raw_crop_manifest_fails_preflight(self) -> None:
        inventory = {
            "slide_size_px": [1920, 1080],
            "items": [{"id": "bad_asset", "class": "imagegen_asset", "bbox_px": [10, 10, 100, 100], "semantic_unit_count": 1}],
        }
        manifest = [{"semantic_unit_id": "bad_asset", "source_type": "raw_crop", "asset_path": "assets/bad.png", "semantic_unit_count": 1}]
        (WORK / "visual_inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
        (WORK / "asset_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        run_cmd(
            "scripts/validate_semantic_inputs.py",
            "--inventory",
            str(WORK / "visual_inventory.json"),
            "--manifest",
            str(WORK / "asset_manifest.json"),
            "--stage",
            "build",
            expect_ok=False,
        )

    def test_missing_manifest_entry_fails_preflight(self) -> None:
        inventory = {
            "slide_size_px": [1920, 1080],
            "items": [{"id": "missing_asset", "class": "imagegen_asset", "bbox_px": [10, 10, 100, 100], "semantic_unit_count": 1}],
        }
        (WORK / "visual_inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
        (WORK / "asset_manifest.json").write_text("[]\n", encoding="utf-8")
        run_cmd(
            "scripts/validate_semantic_inputs.py",
            "--inventory",
            str(WORK / "visual_inventory.json"),
            "--manifest",
            str(WORK / "asset_manifest.json"),
            "--stage",
            "build",
            expect_ok=False,
        )


if __name__ == "__main__":
    unittest.main()
