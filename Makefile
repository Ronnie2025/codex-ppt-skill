PYTHON ?= python3
DEMO_DIR ?= output/demo

.PHONY: help check pycheck deps-check audit pack cut compare validate semantic-init semantic-preflight build-semantic semantic-test demo pack-demo cut-demo compare-demo semantic-demo clean-demo

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
	@echo "  make semantic-init OUT_DIR=./work/semantic REF=./slides/page-01.png"
	@echo "  make semantic-preflight INVENTORY=./visual_inventory.json MANIFEST=./asset_manifest.json ANCHORS=./asset_anchors.json"
	@echo "  make build-semantic INVENTORY=./visual_inventory.json MANIFEST=./asset_manifest.json OUT_PPTX=./output/reconstructed.pptx LAYOUT_RULES=./layout_rules.json BUILD_REPORT=./reports/build_report.json"
	@echo "  make cut GRID=./output/generated/icons_grid.png ROWS=3 COLS=4 NAMES=a,b,c,d OUT_DIR=./output/assets MANIFEST=./output/asset_manifest.json"
	@echo "  make cut GRID_MANIFEST=./prompts/assets_cycle_1.json OUT_DIR=./assets MANIFEST=./asset_manifest.json"
	@echo "  make compare REF=./output/reference/page-01.png RENDER=./output/render/page-01.png COMPARE_DIR=./output/compare"
	@echo "  make validate PPTX=./output/reconstructed.pptx REF=./output/reference/page-01.png MANIFEST=./output/asset_manifest.json INVENTORY=./output/visual_inventory.json BUILD_REPORT=./reports/build_report.json REPORT=./output/validation_report.md"
	@echo ""
	@echo "Local demos:"
	@echo "  make demo"
	@echo "  make pack-demo"
	@echo "  make cut-demo"
	@echo "  make compare-demo"
	@echo "  make semantic-test"

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

semantic-init:
	@test -n "$(OUT_DIR)" || (echo "OUT_DIR is required" && exit 2)
	$(PYTHON) scripts/init_semantic_project.py --out-dir "$(OUT_DIR)" $(if $(REF),--reference "$(REF)",) $(if $(FORCE),--force,)

semantic-preflight:
	@test -n "$(INVENTORY)" || (echo "INVENTORY is required" && exit 2)
	$(PYTHON) scripts/validate_semantic_inputs.py --inventory "$(INVENTORY)" $(if $(MANIFEST),--manifest "$(MANIFEST)",) $(if $(ANCHORS),--anchors "$(ANCHORS)",) $(if $(REQUIRE_ANCHORS),--require-anchors,) $(if $(STAGE),--stage "$(STAGE)",--stage build) $(if $(PREFLIGHT_REPORT),--out "$(PREFLIGHT_REPORT)",)

build-semantic:
	@test -n "$(INVENTORY)" || (echo "INVENTORY is required" && exit 2)
	@test -n "$(MANIFEST)" || (echo "MANIFEST is required" && exit 2)
	@test -n "$(OUT_PPTX)" || (echo "OUT_PPTX is required" && exit 2)
	$(PYTHON) scripts/build_semantic_deck.py --inventory "$(INVENTORY)" --manifest "$(MANIFEST)" --out-pptx "$(OUT_PPTX)" $(if $(BASE_DIR),--base-dir "$(BASE_DIR)",) $(if $(LAYOUT_RULES),--layout-rules "$(LAYOUT_RULES)",) $(if $(BUILD_REPORT),--report "$(BUILD_REPORT)",)

cut:
	@test -n "$(OUT_DIR)" || (echo "OUT_DIR is required" && exit 2)
	@if [ -n "$(GRID_MANIFEST)" ]; then \
		$(PYTHON) scripts/grid_cut.py --grid-manifest "$(GRID_MANIFEST)" --out-dir "$(OUT_DIR)" $(if $(MANIFEST),--manifest-out "$(MANIFEST)",); \
	else \
		test -n "$(GRID)" || (echo "GRID is required" && exit 2); \
		test -n "$(ROWS)" || (echo "ROWS is required" && exit 2); \
		test -n "$(COLS)" || (echo "COLS is required" && exit 2); \
		test -n "$(NAMES)" || (echo "NAMES is required" && exit 2); \
		$(PYTHON) scripts/grid_cut.py --grid "$(GRID)" --rows "$(ROWS)" --cols "$(COLS)" --names "$(NAMES)" --out-dir "$(OUT_DIR)" $(if $(MANIFEST),--manifest-out "$(MANIFEST)",); \
	fi

compare:
	@test -n "$(REF)" || (echo "REF is required" && exit 2)
	@test -n "$(RENDER)" || (echo "RENDER is required" && exit 2)
	@test -n "$(COMPARE_DIR)" || (echo "COMPARE_DIR is required" && exit 2)
	$(PYTHON) scripts/compare_render.py --reference "$(REF)" --render "$(RENDER)" --out-dir "$(COMPARE_DIR)"

validate:
	@test -n "$(PPTX)" || (echo "PPTX is required" && exit 2)
	@test -n "$(REPORT)" || (echo "REPORT is required" && exit 2)
	$(PYTHON) scripts/validate_semantic_deck.py --pptx "$(PPTX)" $(if $(REF),--reference "$(REF)",) $(if $(MANIFEST),--manifest "$(MANIFEST)",) $(if $(INVENTORY),--inventory "$(INVENTORY)",) $(if $(BUILD_REPORT),--build-report "$(BUILD_REPORT)",) $(if $(FULL_SLIDE_SIZE),--full-slide-size "$(FULL_SLIDE_SIZE)",) --out "$(REPORT)"

semantic-test:
	$(PYTHON) tests/test_semantic_workflow.py

demo: pack-demo cut-demo compare-demo semantic-demo

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

semantic-demo:
	rm -rf "$(DEMO_DIR)/semantic"
	mkdir -p "$(DEMO_DIR)/semantic"
	$(PYTHON) scripts/validate_semantic_inputs.py --inventory tests/fixtures/semantic_minimal/visual_inventory.json --manifest tests/fixtures/semantic_minimal/asset_manifest.json --stage build --out "$(DEMO_DIR)/semantic/preflight.json"
	$(PYTHON) scripts/build_semantic_deck.py --inventory tests/fixtures/semantic_minimal/visual_inventory.json --manifest tests/fixtures/semantic_minimal/asset_manifest.json --base-dir tests/fixtures/semantic_minimal --out-pptx "$(DEMO_DIR)/semantic/reconstructed.pptx" --report "$(DEMO_DIR)/semantic/build_report.json"
	$(PYTHON) scripts/audit_pptx_editability.py "$(DEMO_DIR)/semantic/reconstructed.pptx" --json "$(DEMO_DIR)/semantic/editability_audit.json"
	$(PYTHON) scripts/validate_semantic_deck.py --pptx "$(DEMO_DIR)/semantic/reconstructed.pptx" --reference tests/fixtures/semantic_minimal/reference/page-01.png --manifest tests/fixtures/semantic_minimal/asset_manifest.json --inventory tests/fixtures/semantic_minimal/visual_inventory.json --full-slide-size 1920x1080 --out "$(DEMO_DIR)/semantic/validation_report.md"

clean-demo:
	rm -rf "$(DEMO_DIR)"
