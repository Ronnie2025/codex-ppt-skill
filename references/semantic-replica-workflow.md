# Semantic Editable Replica Workflow

Use this reference when an image-only slide, screenshot, rendered PPT page, or generated page must become a practical editable PPTX.

## Required Flow

Element rebuild is a reference-driven asset workflow:

```text
reference
-> visual_inventory
-> asset_anchors
-> layout_rules
-> reference crops / residual redboxes
-> imagegen or API asset grid
-> grid_cut and alpha cleanup
-> asset_manifest
-> semantic input preflight
-> build_semantic_deck
-> render compare
-> validation
```

If this flow is skipped, the result is only an editable draft or structure preview. Do not call it a completed element rebuild.

## Reusable Project Layout

Use the same artifact layout for every production reconstruction:

```text
reference/
reference_crops/
generated/
assets/
render/
compare/
reports/
prompts/assets_cycle_1.jsonl
visual_inventory.json
asset_anchors.json
asset_manifest.json
layout_rules.json
conversion_report.md
```

Run `scripts/init_semantic_project.py` to create the layout. The v4/v5 lesson is that project-local scripts can be temporary, but these ledgers must stay stable across pages:

- `visual_inventory.json`: every text, native layout object, and semantic visual placement.
- `asset_anchors.json`: target bboxes, z-order, fitted bboxes, and placement rules for semantic visuals.
- `asset_manifest.json`: one final transparent asset file per semantic unit, including source grid and cell.
- `layout_rules.json`: font policy, image-fit policy, forbidden media, source-type whitelist, and comparison thresholds.

## Object Classes

Classify every visible element before building:

- `text`: editable PPT text boxes.
- `layout_native`: page background, panels, cards, dividers, frames, tables, simple containers, and ordinary straight connectors.
- `imagegen_asset`: semantic non-text visuals such as icons, pictograms, 3D objects, chart symbols, badges, decorative UI renders, screenshots, devices, network diagrams, illustrations, and stylized arrows.
- `provided_asset`: user-supplied or approved transparent assets with documented source.
- `unresolved`: anything that still needs a decision.

If a visual carries meaning beyond being a border, divider, plain container, or text box, classify it as `imagegen_asset`. Complex arrows with gradients, curves, shadows, dashed returns, 3D depth, or brand-like styling are semantic assets, not native PPT arrows.

## Minimum Semantic Unit

The final PPT should expose the smallest useful selectable unit:

- one icon = one asset;
- one badge or risk marker = one asset;
- one decorative UI render = one asset;
- one 3D object or illustration = one asset;
- one stylized arrow = one asset;
- one text block = one text box;
- one card, panel, table frame, divider, or simple connector = one native PPT object.

Generated grids are extraction sheets only. Cut them into one transparent asset file per semantic unit before inserting anything into PPT.

## Asset Generation Rules

Every `imagegen_asset` request should use the full reference plus the relevant crop or residual crop as visual context when the image tool supports references. Text-only generation is acceptable only for synthetic fixtures or generic demos, not for reference-matched production reconstruction.

Prompt each grid like this:

```text
Create an isolated asset grid for a PowerPoint visual replica.
Use the full reference for style and the supplied crops/residuals for object identity.
Objects in order: {object list}.
Grid: {rows}x{cols}, generous margins and equal cells.
Background: uniform chroma key #00ff00 or clean white.
Style: {short style guide}.
Text: no readable text, no numbers, no labels, no watermark.
Do not include card frames, slide fragments, fake logos, QR codes, crop borders, or surrounding context.
```

After generation:

- cut with declared grid geometry;
- remove white/chroma background to alpha;
- trim transparent borders;
- reject assets with readable text, residual card frames, hard crop edges, neighboring objects, or one-axis distortion;
- record every final asset in `asset_manifest.json`.

The generated grid is never a final slide asset. It is only an extraction sheet. A production-grade v4/v5-style page should normally have:

- `prompts/assets_cycle_*.jsonl`;
- one or more files under `generated/`;
- transparent files under `assets/`;
- `asset_manifest.json` records with `source_type: imagegen_asset` or `api_generated_asset`;
- `asset_anchors.json` records for every placement.

If the manifest contains only synthetic `provided_asset` entries, the run proves the build chain but not visual replica quality.

For public examples, keep object names generic, for example `domain_icon_01`, `workflow_arrow_01`, `decorative_asset_01`.

## Required Manifests

`visual_inventory.json` should describe the page-level decomposition:

```json
{
  "slide_size_px": [1920, 1080],
  "final_deck_type": "semantic_editable_replica",
  "source_image_policy": "reference only; do not embed the full source image in the final PPTX",
  "items": [
    {
      "id": "title_main",
      "class": "text",
      "text": "Example title",
      "bbox_px": [80, 60, 900, 80]
    },
    {
      "id": "domain_icon_01",
      "class": "imagegen_asset",
      "bbox_px": [120, 220, 120, 120],
      "semantic_unit_count": 1
    }
  ]
}
```

`asset_manifest.json` should record final asset files:

```json
[
  {
    "semantic_unit_id": "domain_icon_01",
    "source_type": "imagegen_asset",
    "asset_path": "assets/domain_icon_01.png",
    "semantic_unit_count": 1,
    "generated_grid": "generated/domain_icons_grid.png",
    "grid_cell": [0, 0],
    "placement_rule": "uniform contain scaling; no one-axis stretch"
  }
]
```

Acceptable source types are `imagegen_asset`, `api_generated_asset`, and documented `provided_asset`. `raw_crop`, `reference_crop`, `screenshot_crop`, `placeholder`, and `prompt_only_asset` are not acceptable final sources.

`asset_anchors.json` should record placements independently from asset provenance:

```json
[
  {
    "semantic_unit_id": "domain_icon_01",
    "slide": 1,
    "target_bbox_px": [120, 220, 120, 120],
    "z_index": 20,
    "placement_rule": "uniform contain scaling; no one-axis stretch"
  }
]
```

`layout_rules.json` should be executable enough for QA:

```json
{
  "slide_size_px": [1920, 1080],
  "font_policy": {
    "default_font_face": "Microsoft YaHei",
    "text_box_extra_room_pct": 12
  },
  "image_fit": "uniform_contain_only",
  "allowed_source_types": ["imagegen_asset", "api_generated_asset", "provided_asset"],
  "forbidden_media": ["full_slide_reference_image", "near_full_slide_reference_image", "svg_media", "raw_crop_asset"],
  "comparison": {
    "diff_threshold": 18,
    "changed_pixel_pct_target": 0.25
  }
}
```

## Build Rules

- Use native PPT text for all readable text.
- Keep line counts deliberate; do not let PowerPoint create accidental one-character wraps.
- Use native shapes for cards, panels, frames, shadows, tables, dividers, and simple connectors.
- Insert semantic visuals as independent PNG assets.
- Fit images with uniform contain scaling.
- Never stretch images on one axis.
- Use `scripts/build_semantic_deck.py` for manifest-driven PPTX construction when the inventory fits the public schema.
- Use `scripts/validate_semantic_inputs.py` before build; do not wait for PPTX validation to discover missing assets or raw crops.
- Never insert SVG media in a path B final PPTX.
- Never insert the full reference image or near-full-slide reference media in the final deck.
- Do not use generic hand-drawn icons or low-fidelity native shapes as replacements for semantic visuals.

## v4/v5 Gates

The v4/v5 trial succeeded because it passed these gates:

- Generated visual assets were created from reference-aware grids, not drawn as generic placeholders.
- Grids were cut into one transparent PNG per semantic unit.
- Dirty assets were cleaned before insertion.
- Semantic placements were recorded separately from source provenance.
- Text/card/container layers were rebuilt as native PPT objects.
- Render comparison produced contact sheets and diff heatmaps.
- Validation rejected full-slide references, raw crops, SVG media, and manifest/object mismatches.

Do not certify a page as `semantic visual-replica` unless the same gates exist for the page being delivered.

## QA Rules

Validate before handoff:

- PPTX opens and renders.
- Slide count matches the reference.
- No full-slide or near-full-slide reference bitmap is embedded.
- Reference image hashes do not appear in PPTX media.
- No SVG media exists in the final path B PPTX.
- Every semantic image object has a manifest record.
- Every `imagegen_asset` or `provided_asset` in inventory has a real asset file.
- Picture objects in PPTX are at least enough to cover manifest placements.
- Text items have visible native PPT text boxes; hidden transparent text over a screenshot is not a completed element rebuild.
- Render previews, contact sheet, and diff heatmaps exist when reference render is available.
- Report lists unresolved regions, retained bitmap exceptions, and known limits.

Use `scripts/build_semantic_deck.py`, `scripts/validate_semantic_deck.py`, `scripts/compare_render.py`, and `scripts/audit_pptx_editability.py` together. Any failed gate means the result is not a certified element rebuild.

For a reusable run, add:

```bash
python scripts/validate_semantic_inputs.py --inventory visual_inventory.json --manifest asset_manifest.json --anchors asset_anchors.json --stage build
python scripts/build_semantic_deck.py --inventory visual_inventory.json --manifest asset_manifest.json --out-pptx output/reconstructed.pptx --report reports/build_report.json
python scripts/validate_semantic_deck.py --pptx output/reconstructed.pptx --reference reference/page-01.png --manifest asset_manifest.json --inventory visual_inventory.json --out reports/validation_report.md
```

## Practical Limits

- Use native PPT shapes for text, cards, tables, lines, connectors, and simple arrows.
- Use independent transparent assets for complex icons, pictograms, illustrations, 3D visuals, UI renders, and stylized arrows.
- Do not promise that SVG imports will remain internally editable in PowerPoint.
- Avoid decomposing one complex icon into many ungrouped shapes unless the user explicitly needs that tradeoff and accepts fragility.
- Keep 10%-15% extra room inside text boxes to absorb PowerPoint font and line-height differences.
- Open the PPTX in the target PowerPoint environment when possible. LibreOffice render is useful for fast iteration, but it is not the final source of truth for Chinese font metrics.
