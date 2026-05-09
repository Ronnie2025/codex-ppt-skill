PYTHON ?= python3
DEMO_DIR ?= output/demo

.PHONY: help check pycheck deps-check audit pack cut compare validate demo pack-demo cut-demo compare-demo clean-demo

help:
	@echo "Codex PPT Skill shortcuts"
	@echo ""
	@echo "Quality:"
	@echo "  make check"
	@echo "  make pycheck"
	@echo "  make deps-check"
	@echo "  make audit"
	@echo ""
	@echo "Image deck packaging:"
	@echo "  make pack IMAGES_DIR=./slides OUT_PPTX=./output/deck.pptx PACK_ARGS=\"--contact-sheet ./output/contact-sheet.jpg --export-pdf\""
	@echo ""
	@echo "Semantic asset tools:"
	@echo "  make cut GRID=./output/generated/icons_grid.png ROWS=3 COLS=4 NAMES=a,b,c,d OUT_DIR=./output/assets MANIFEST=./output/asset_manifest.json"
	@echo "  make compare REF=./output/reference/page-01.png RENDER=./output/render/page-01.png COMPARE_DIR=./output/compare"
	@echo "  make validate PPTX=./output/reconstructed.pptx REF=./output/reference/page-01.png MANIFEST=./output/asset_manifest.json INVENTORY=./output/visual_inventory.json REPORT=./output/validation_report.md"
	@echo ""
	@echo "Local demos:"
	@echo "  make demo"
	@echo "  make pack-demo"
	@echo "  make cut-demo"
	@echo "  make compare-demo"

pycheck:
	$(PYTHON) -m py_compile scripts/*.py

deps-check:
	$(PYTHON) -c "import PIL, pptx; print('Runtime dependencies available.')"

audit:
	$(PYTHON) scripts/audit_public_skill.py --root .

check: pycheck deps-check audit

pack:
	@test -n "$(IMAGES_DIR)" || (echo "IMAGES_DIR is required" && exit 2)
	@test -n "$(OUT_PPTX)" || (echo "OUT_PPTX is required" && exit 2)
	$(PYTHON) scripts/package_image_deck.py --images-dir "$(IMAGES_DIR)" --out-pptx "$(OUT_PPTX)" $(PACK_ARGS)

cut:
	@test -n "$(GRID)" || (echo "GRID is required" && exit 2)
	@test -n "$(ROWS)" || (echo "ROWS is required" && exit 2)
	@test -n "$(COLS)" || (echo "COLS is required" && exit 2)
	@test -n "$(NAMES)" || (echo "NAMES is required" && exit 2)
	@test -n "$(OUT_DIR)" || (echo "OUT_DIR is required" && exit 2)
	$(PYTHON) scripts/grid_cut.py --grid "$(GRID)" --rows "$(ROWS)" --cols "$(COLS)" --names "$(NAMES)" --out-dir "$(OUT_DIR)" $(if $(MANIFEST),--manifest-out "$(MANIFEST)",)

compare:
	@test -n "$(REF)" || (echo "REF is required" && exit 2)
	@test -n "$(RENDER)" || (echo "RENDER is required" && exit 2)
	@test -n "$(COMPARE_DIR)" || (echo "COMPARE_DIR is required" && exit 2)
	$(PYTHON) scripts/compare_render.py --reference "$(REF)" --render "$(RENDER)" --out-dir "$(COMPARE_DIR)"

validate:
	@test -n "$(PPTX)" || (echo "PPTX is required" && exit 2)
	@test -n "$(REPORT)" || (echo "REPORT is required" && exit 2)
	$(PYTHON) scripts/validate_semantic_deck.py --pptx "$(PPTX)" $(if $(REF),--reference "$(REF)",) $(if $(MANIFEST),--manifest "$(MANIFEST)",) $(if $(INVENTORY),--inventory "$(INVENTORY)",) $(if $(FULL_SLIDE_SIZE),--full-slide-size "$(FULL_SLIDE_SIZE)",) --out "$(REPORT)"

demo: pack-demo cut-demo compare-demo

pack-demo:
	rm -rf "$(DEMO_DIR)/pack"
	mkdir -p "$(DEMO_DIR)/pack/input"
	cp assets/examples/01-risk-evolution.png "$(DEMO_DIR)/pack/input/slide-01.png"
	cp assets/examples/04-evaluation-system.png "$(DEMO_DIR)/pack/input/slide-02.png"
	$(PYTHON) scripts/package_image_deck.py --images-dir "$(DEMO_DIR)/pack/input" --out-pptx "$(DEMO_DIR)/pack/demo-image-deck.pptx" --contact-sheet "$(DEMO_DIR)/pack/contact-sheet.jpg" --slide-count 2

cut-demo:
	rm -rf "$(DEMO_DIR)/cut"
	mkdir -p "$(DEMO_DIR)/cut"
	$(PYTHON) -c "from PIL import Image, ImageDraw; p='$(DEMO_DIR)/cut/demo-grid.png'; img=Image.new('RGBA',(800,400),(0,255,0,255)); d=ImageDraw.Draw(img); d.ellipse((90,70,250,230),fill=(25,112,210,255)); d.rounded_rectangle((500,70,660,230),radius=28,fill=(235,64,52,255)); d.polygon([(180,305),(255,345),(180,385)],fill=(25,112,210,255)); d.rounded_rectangle((510,300,650,380),radius=18,fill=(35,190,120,255)); img.save(p)"
	$(PYTHON) scripts/grid_cut.py --grid "$(DEMO_DIR)/cut/demo-grid.png" --rows 2 --cols 2 --names demo_circle,demo_square,demo_arrow,demo_pill --out-dir "$(DEMO_DIR)/cut/assets" --manifest-out "$(DEMO_DIR)/cut/asset_manifest.json"

compare-demo:
	rm -rf "$(DEMO_DIR)/compare"
	$(PYTHON) scripts/compare_render.py --reference assets/examples/01-risk-evolution.png --render assets/examples/01-risk-evolution.png --out-dir "$(DEMO_DIR)/compare"

clean-demo:
	rm -rf "$(DEMO_DIR)"
