---
name: imagegen-scene-ppt
description: "面向中文 toB 商业汇报的 PPT 工作流路由：新做汇报先生成图片型 PPT；已有图片页或生成后的页图，再按目标拆解为元素重组 PPTX 或 SVG。"
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
- 用户已有图片页，且明确要可编辑 PPTX：选择 **元素重组**。
- 用户已有图片页，且明确要 SVG 或网页/文档复用：选择 **SVG 拆解**。
- 用户既想先看效果又可能后续编辑：先生成图片型 PPT；确认后再把页图作为拆解输入。

成本提示：元素重组通常更耗时、token 更高，但 PPTX 可编辑性更强；SVG 拆解通常更快更省，但复杂视觉会被简化，导入 PowerPoint 后不承诺对象级稳定可编辑。

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

核心判断：

- 文本、标题、卡片、容器、分隔线、普通结构箭头：优先做 PPT 原生对象。
- 图标、徽章、3D 装饰、复杂箭头、插画、设备图、UI 装饰：做独立透明资产。
- 原图、截图、硬裁 crop 只能作为参考和中间素材，不能作为最终整页背景或带残边的最终对象。

执行步骤：

1. 建立项目目录，保存参考图为 `reference_page_*.png`。
2. 建立 `visual_inventory.json`，按文本、容器、图标、箭头、装饰、3D 元素等对象做页面清单。
3. 建立 `asset_anchors.json`，记录每个待生成资产的 bbox、含义、目标尺寸和层级。
4. 为资产写 imagegen/API 提示词，生成 isolated asset grid。要求无文字、无数字、无标签、无卡片框、无背景碎片。
5. 用 `scripts/grid_cut.py` 或 `make cut` 切成一个元素一个透明 PNG，并生成 `asset_manifest.json`。
6. 用 PPT 原生对象重建文本、卡片、容器和结构；用透明资产插入图标、箭头和装饰元素。
7. 渲染 PPTX，再用 `scripts/compare_render.py` 或 `make compare` 输出 contact sheet / diff heatmap。
8. 用 `scripts/validate_semantic_deck.py` 或 `make validate` 检查没有整页原图、参考图 hash 和不合规媒体。

验收标准：

- PPTX 可以打开并正常渲染。
- 文本可选中、可编辑，不用隐藏透明文本冒充可编辑。
- 重要图标、箭头、装饰元素可单独选中、移动、替换。
- 没有整页参考图作为最终媒体。
- 没有带残字、残框、硬边的原图裁片。
- 输出 manifest、渲染预览、对比图和验证报告。

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
