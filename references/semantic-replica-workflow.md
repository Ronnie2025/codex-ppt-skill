# Semantic Editable Replica Workflow

Use this reference when the user wants an image-only slide, screenshot, or rendered page rebuilt as a practical editable PPTX.

## Object Classes

Classify every visible element before building:

- `text`: editable PPT text boxes.
- `layout_native`: page background, panels, cards, dividers, frames, ordinary connectors, tables, and simple containers.
- `imagegen_asset`: semantic non-text visuals such as icons, pictograms, 3D objects, chart symbols, badges, decorative UI renders, screenshots, devices, network diagrams, and stylized arrows.
- `provided_asset`: user-supplied transparent assets with documented source.
- `unresolved`: anything that still needs a decision.

If a visual carries meaning beyond being a simple border, divider, or text container, classify it as `imagegen_asset`.

## Minimum Semantic Unit

The final PPT should expose the smallest useful selectable unit:

- one icon = one asset;
- one arrow = one asset when it has distinctive style or when the user asks for generated arrows;
- one risk badge = one asset;
- one decorative corner render = one asset;
- one 3D object = one asset;
- one text block = one text box;
- one card or panel = one native shape.

Generated grids are extraction sheets only. Cut them into one asset file per semantic unit before inserting them into PPT.

## Prompt Pattern For Asset Grids

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

For public examples, keep object names generic, for example `domain_icon_01`, `workflow_arrow_01`, `decorative_asset_01`.

## Required Manifests

`visual_inventory.json` should describe the page-level decomposition:

```json
{
  "slide_size_px": [1920, 1080],
  "final_deck_type": "semantic_editable_replica",
  "source_image_policy": "reference only",
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
    "grid_source": "generated/domain_icons_grid.png",
    "grid_cell": [0, 0]
  }
]
```

## Build Rules

- Use native PPT text for all readable text.
- Keep line counts deliberate. Do not let PowerPoint create accidental one-character wraps.
- Use native shapes for cards, panels, frames, shadows when they are simple enough.
- Insert semantic visuals as independent PNG assets.
- Fit images with uniform contain scaling.
- Never stretch images on one axis.
- Never insert the full reference image in the final deck unless the user explicitly asks for a non-editable fallback.

## QA Rules

Validate before handoff:

- PPTX opens and renders.
- Slide count matches the reference.
- No full-slide reference bitmap is embedded.
- Reference image hashes do not appear in PPTX media.
- Every semantic image object has a manifest record.
- Render previews and contact sheet exist.
- Diff heatmaps exist when reference render is available.
- Report lists unresolved regions, retained bitmap exceptions, and known limits.
- Open the PPTX in the target PowerPoint environment when possible. LibreOffice render is useful for fast iteration, but it is not the final source of truth for Chinese font metrics.

Use `scripts/validate_semantic_deck.py` and `scripts/compare_render.py` when possible.

## Practical Limits

- Use native PPT shapes for text, cards, tables, lines, connectors, and simple arrows.
- Use independent transparent assets for complex icons, pictograms, illustrations, and 3D visuals.
- Do not promise that SVG imports will remain internally editable in PowerPoint.
- Avoid decomposing one complex icon into many ungrouped shapes unless the user explicitly needs that tradeoff and accepts fragility.
- Keep 10%-15% extra room inside text boxes to absorb PowerPoint font and line-height differences.
