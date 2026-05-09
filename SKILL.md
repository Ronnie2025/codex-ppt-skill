---
name: imagegen-scene-ppt
description: "面向中文 toB 商业汇报的 PPT 工作流路由：新做汇报先生成图片型 PPT；已有图片页或生成后的页图，再按目标拆解为元素重组 PPTX、semantic visual-replica 或 SVG。适用于图片页转可编辑 PPT、v4/v5 元素重组、图片型 PPT 结构重建。"
---

# Codex PPT Skill

本文件是给 Codex 执行用的路由和操作规程。面向用户的项目说明、效果图和安装命令见 `README.md`。

先判断输入来源和最终目标：

1. **新做 PPT 汇报**：先走整页生图 PPT，生成图片型 PPTX / PDF / PNG。
2. **已有图片页、截图页、旧 PPT 渲染页，或整页生图页**：再根据目标进入拆解。
3. **要 PowerPoint 内继续改字、移元素、换图标**：走元素重组。
4. **只要 SVG、网页/文档复用，或低成本看结构**：走 SVG 拆解。

路径可以串联：先用整页生图 PPT 形成视觉页；如果后续需要编辑或复用，再把单页 PNG 交给元素重组或 SVG 拆解继续处理。只要目标是可编辑 PPTX，默认优先元素重组；SVG 拆解不是默认的 PPT 可编辑路线。

## 路由判断

先问或确认这四件事：

- 最终交付：PPTX / PDF / PNG / SVG / 可编辑 PPTX。
- 是否需要后续编辑：不编辑、少量替换、还是对象级编辑。
- 输入材料：文档、旧 PPT、截图、图片页、整页生图页、参考模板。
- 质量优先级：视觉观感、可编辑性、速度、token 成本、结构复用。

直接选择：

- 用户要新做汇报、方案页或展示页：先选择 **整页生图 PPT**。
- 用户已有图片页，且明确要可编辑 PPTX、PowerPoint 内改字、移动元素、替换图标、元素化重建或图片页转可编辑：强制选择 **元素重组**。
- 用户已有图片页，且明确要 SVG、网页/文档复用，或明确接受低成本结构样板：选择 **SVG 拆解**。
- 用户既想先看效果又可能后续编辑：先生成图片型 PPT；确认后再把页图作为拆解输入。

成本提示：元素重组通常更耗时、token 更高，但 PPTX 可编辑性更强；SVG 拆解通常更快更省，但复杂视觉会被简化，导入 PowerPoint 后不承诺对象级稳定可编辑。

如果用户目标是可编辑 PPTX，但当前时间、token、图像生成能力或资产素材不足以完成元素重组，必须明确说明只能交付降级草稿或改走 SVG 结构预览；不要自动把 SVG 拆解、原生形状重画或通用图标拼装称为元素重组完成。

不适配时直接说明原因，并建议改用原生可编辑 PPT、数据报表、文档或设计工具流程。

## 路径 A：整页生图 PPT

适合单点沟通、重视觉、接受图片化交付的材料，例如方案汇报、售前交流、内部同步、培训讲解、复盘展示。

执行步骤：

1. 澄清使用场景、受众、页数、详略、风格、模板、Logo、输出格式和禁止内容。
2. 读取用户材料，生成逐页大纲：标题、页面目标、2-4 条核心信息。
3. 按 [references/prompt-patterns.md](references/prompt-patterns.md) 写逐页详细生图提示词。
4. 调用 imagegen 生成 16:9 整页图。中文少而大，避免密集表格和小字号脚注。
5. 真实 Logo、二维码、印章、品牌标识只做后处理叠加，不交给 imagegen 生成。
6. 用 `scripts/package_image_deck.py` 或 `make pack` 封装 PPTX，可选导出 PDF、每页 PNG 和 contact sheet。
7. 检查页数、尺寸、文字可读性、Logo 位置、伪 Logo、敏感信息和明显错字。

默认交付：

- 图片型 PPTX
- PDF 或每页 PNG，按用户要求
- contact sheet
- 逐页提示词和 QA 记录

边界：图片型 PPT 不等于可编辑 PPT。正文、图表和版式在图片里，不能承诺 PowerPoint 内逐字逐对象编辑。

## 路径 B：元素重组

适合用户已经有图片页、截图页、图片型 PPT，或路径 A 生成的页图，并且希望重建为实用级可编辑 PPTX。

路径 B 是参考图驱动的语义资产重组，不是 SVG 反编译，也不是只用 PPT 原生形状画一张可编辑草稿。

核心判断：

- 文本、标题、卡片、容器、分隔线、普通结构箭头：优先做 PPT 原生对象。
- 图标、徽章、3D 装饰、复杂箭头、插画、设备图、UI 装饰：必须用 Codex 的 `imagegen` 技能生成独立透明资产。
- 原图、截图、硬裁 crop 只能作为参考和中间素材，不能作为最终整页背景或带残边的最终对象。
- 生产级元素重组默认只接受 `imagegen_asset`。`api_generated_asset` 仅在用户明确指定外部图像 API 时使用；`provided_asset` 只用于用户已提供素材、合规素材库或明确标注的 synthetic/demo 试跑。
- 只有在资产有合规来源记录，并且一语义单元一透明 PNG 插入 PPT 后，才算元素重组资产；不能把程序化近似图标、通用图标库、原图 crop 或提示词占位图当成正式元素重组资产。

完整跑触发规则：

- 用户说“完整跑”“正式跑”“完整 imagegen 元素重组”“不要试跑版”“不要 provided_asset”“高保真元素拆解”等表达时，必须进入完整元素重组模式。
- 完整元素重组模式下，所有语义视觉资产必须通过 Codex `imagegen` 基于整页参考图 + 局部 crop/residual crop 生成，并在 `asset_manifest.json` 中标记为 `imagegen_asset`。
- 完整元素重组模式下，禁止静默降级为 `provided_asset`、程序画图、SVG 重画、图标库拼装或原图 crop。若 imagegen 调用失败、资产不合格、切图失败或无法继续，直接报告阻塞点、已完成文件和下一步，不要把降级版说成完整完成。
- 如果用户只是说“试试”“验证链路”“跑通工具链”“先看结构”，可以交付明确标注的结构预览或 synthetic demo；报告里必须写清它不是完整 imagegen 元素重组。

图片生成硬规则：

- 所有涉及图片生成、视觉资产生成、透明资产生成的步骤，默认且优先使用 Codex 的 `imagegen` 技能；不要用 LibreOffice、SVG 重画、程序画图、图标库拼装或其他渲染工具冒充生图。
- `api_generated_asset` 只保留为兼容字段，除非用户明确要求指定外部 API，否则不要主动选择。
- `provided_asset` 只适合用户已提供的合规素材、明确授权素材库或 synthetic demo；不能把程序化图标、通用图标库或原图硬裁片当作生产级视觉复刻资产。
- LibreOffice / PowerPoint / soffice 这类工具只能用于把已生成的 PPTX 渲染成 PDF/PNG 做验收预览，不能用于生成图片资产。使用时要明确标记为“渲染 QA”，不是“图片生成”。
- 大尺寸中心视觉、跨格 3D 元素、复杂箭头、装饰性底座和高风险关键资产必须单独调用 `imagegen` 生成；不要塞进一个大 asset grid 再等分切。

执行步骤采用 v4/v5 验证过的生产链路：

1. 建立项目目录，保存参考图为 `reference_page_*.png`。
2. 建立 `visual_inventory.json`，按文本、容器、图标、箭头、装饰、3D 元素等对象做页面清单。
3. 建立 `asset_anchors.json` 和 `layout_rules.json`，记录每个待生成资产的 bbox、含义、目标尺寸、层级、字体策略、禁用媒体和 diff 阈值。
4. 为资产写 `prompts/assets_cycle_*.jsonl` 或 prompt pack。每条 prompt 必须绑定整页 reference 和相关 crop/residual crop，明确对象顺序、grid 行列、纯色背景、无文字、无数字、无标签、无水印、无卡片框、无周边页面碎片；完整元素重组时必须实际调用 Codex `imagegen` 生成独立资产或 isolated asset grid。小图标可以成组生成；中心大视觉和复杂元素必须单独生成。
5. 用 `scripts/grid_cut.py` 或 `make cut` 从合格 generated grid 切成一个元素一个透明 PNG，并生成 `asset_manifest.json`。如果切出的资产贴边、被截断、带绿边、含相邻元素，必须废弃并重新用 `imagegen` 单独生成。
6. 必要时用 `scripts/clean_assets.py` 清理透明边缘、小碎片和残留底色。不能把带残字、残框、硬边的 crop 直接插入 PPT。
7. 用 `scripts/validate_semantic_inputs.py` 或 `make semantic-preflight` 做 build 前校验，确认 inventory、manifest、anchors 和资产文件对齐。
8. 用 `scripts/build_semantic_deck.py` 从 `visual_inventory.json` 和 `asset_manifest.json` 构建 PPTX：文本、卡片、容器和结构走 PPT 原生对象；图标、箭头和装饰元素走独立透明资产。构建时必须输出 `build_report.json`，其中包含每个文本框的原始字号、自动适配后字号、估算溢出比例、bbox、父容器、z-index 和图片 fit 结果。
9. 渲染 PPTX，再用 `scripts/compare_render.py` 或 `make compare` 输出 contact sheet / diff heatmap。
10. 用 `scripts/validate_semantic_deck.py` 或 `make validate` 检查没有整页原图、参考图 hash、SVG 和不合规媒体，并传入 `--build-report` 做文字适配、碰撞检测和布局 QA。
11. 如果出现标题断行、文字溢出、文本互相覆盖、文字压住非装饰图片，先调 `visual_inventory.json` 的 bbox/role/parent_id/fit_mode，或调整 `layout_rules.json` 的字体策略，再重建、重渲染、重对比。不能只看 PPTX 对象数就宣布完成。

验收标准：

- PPTX 可以打开并正常渲染。
- 文本可选中、可编辑，不用隐藏透明文本冒充可编辑。
- 重要图标、箭头、装饰元素可单独选中、移动、替换。
- 没有整页参考图作为最终媒体。
- 没有带残字、残框、硬边的原图裁片。
- 没有用非 Codex imagegen 的方式生成生产级图片资产；LibreOffice 等仅可作为渲染验收工具。
- 输出 manifest、渲染预览、对比图和验证报告。
- `visual_inventory.json` 与 `asset_manifest.json` 对齐：每个语义视觉资产都有合规来源、真实文件和 PPT 插入对象。
- 完整元素重组模式下，`asset_manifest.json` 中的语义视觉资产应为 `imagegen_asset`；除用户显式提供素材外，出现 `provided_asset` 必须降级标注为结构预览或 demo。
- `build_report.json` 中 `layout_qa.error_count = 0`；可接受少量 micro label 字号或设计性文字压图 warning，但必须人工看过预览。
- `compare_render.py` 输出的视觉回归状态为 `PASS` 或明确标记为需要人工复核；contact sheet 要能直接看出标题、卡片和关键流程没有重叠。
- 最终 PPTX 不包含 SVG 媒体、整页或近整页参考图、raw crop、prompt-only 占位图或手绘低保真语义视觉。
- 生产级复刻必须有 `generated/`、`assets/`、`prompts/`、`asset_anchors.json`、`layout_rules.json`、渲染对比和验证报告；只有 synthetic `provided_asset` 的样例只能证明闭环可运行，不能当作视觉复刻效果验收。

不满足以上条件时，只能标记为“可编辑草稿”或“结构预览”，不能标记为元素重组合格。

详细执行规则见 [references/semantic-replica-workflow.md](references/semantic-replica-workflow.md)；局限性见 [references/limitations.md](references/limitations.md)。

## 路径 C：SVG 拆解

适合用户明确要 `.svg`，或要把图片页转换成网页/文档可复用的轻量结构。它可以接收原图、截图、图片页，也可以接收路径 A 生成的单页 PNG。

执行步骤：

1. 读取参考图，识别文本、容器、背景、线条、箭头、简单图标和装饰层。
2. 用原生 SVG 重建页面结构，文本、色块、线条和图形尽量成为独立 SVG 对象。
3. 输出 `.svg` 和 PNG 预览。
4. 简短说明哪些对象是 SVG 原生对象，哪些复杂视觉被简化，是否适合继续进入元素重组。

边界：SVG 适合结构复用，但导入 PowerPoint 后不保证内部对象稳定可编辑。用户要对象级 PPTX 编辑时，转回路径 B。

## 输出纪律

- 先确定输入来源：新做汇报先生成；已有图片页或生成后的页图再拆解。
- 再确定路径和交付承诺，不把生成、元素重组和 SVG 拆解混成同一种能力。
- 每次交付都说明最终文件、可编辑范围、已知限制和 QA 结果。
- 能运行脚本时优先运行脚本并保留输出；不能运行时说明环境缺口。
- 公开复用或发布仓库前，按 [references/publication-boundaries.md](references/publication-boundaries.md) 检查边界，并运行：

```bash
python scripts/audit_public_skill.py --root .
```

## 硬性规则

- 不编造数字、来源、标准、客户名或证据。
- 不把图片型 PPT 说成可编辑 PPT。
- 不把 SVG 嵌入说成 PowerPoint 对象级可编辑。
- 不让 imagegen 生成真实 Logo、二维码、证书、印章或品牌标识。
- 元素重组模式下，原图 crop 只能是中间参考，不是最终资产。
