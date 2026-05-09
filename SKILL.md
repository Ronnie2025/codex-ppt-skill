---
name: imagegen-scene-ppt
description: "用于中文 ToB 商业汇报的 PPT 视觉生成与图片页重建工作流：支持整页生图 PPT、按语义资产拆解并重建为可编辑 PPTX，以及图片页 SVG 结构重绘。"
---

# Codex PPT Skill

这个 skill 有三条路径：

1. **整页生图 PPT**：适合单点沟通、重视觉、接受图片化交付的演示材料。
2. **语义可编辑重组**：适合用户给出图片页、截图页或图片型 PPT，并要求将其拆成可编辑 PPTX。
3. **SVG 结构重绘**：适合用户只要求把图片页拆成可编辑 SVG，或要先做轻量矢量结构样板。

先判断用户真实目标，再选择路径。不要把图片型 PPT 说成可编辑 PPT；不要把 SVG 导入 PowerPoint 的媒体对象说成完整可编辑 PPT；也不要把整页截图当成可编辑重建的最终交付。

三条路径不是互斥关系。可以先走 **整页生图 PPT** 形成视觉方向和可汇报版本，再把生成的单页 PNG 交给 **语义可编辑重组** 或 **SVG 结构重绘**。这种串联适合用户先要效果，再追加结构化或可编辑诉求。默认优先考虑语义可编辑重组，只有用户明确只要 SVG、网页/文档复用，或要低成本结构样板时，再选 SVG。

## 模式选择

使用 **整页生图 PPT**，当用户重视整体观感、现场讲解效果、缩略图节奏，并接受正文和图表是图片。

使用 **语义可编辑重组**，当用户提出这些目标：

- 图片版 PPT 转可编辑 PPT；
- 截图页/整页生图拆成可编辑对象；
- 需要锤炼图片转 PPT 的 skill；
- 要保留美化元素，但不能用硬裁 crop；
- 要让图标、箭头、装饰、3D 元素可单独选中、移动、替换。

使用 **SVG 结构重绘**，当用户明确要 SVG、网页/文档可复用矢量图，或只需要把页面结构拆成可编辑 SVG。SVG 路线不是默认 PPTX 可编辑重建路线。

### B/C 路径取舍

| 维度 | 语义可编辑重组 | SVG 结构重绘 |
|---|---|---|
| 输入 | 原图、截图、图片页、A 生成的单页 PNG | 原图、截图、图片页、A 生成的单页 PNG |
| 时间 | 较长，需要资产化、组装和验证 | 较短，适合快速试探结构 |
| token | 高，需要 inventory、资产提示词、布局和 QA | 中低，主要用于理解页面和生成 SVG |
| 效果 | 更能保留图标、箭头、3D 装饰和视觉层次 | 结构清楚，但复杂视觉容易简化 |
| PowerPoint 可编辑性 | 更高，文字、容器和语义资产可分别编辑 | 不稳定，通常只能作为 SVG/媒体嵌入 |

不适配这三条路径时，直接说明原因，并建议使用文档、数据报表、原生可编辑 PPT 或设计工具流程。

## 模式一：整页生图 PPT

### 适配条件

- 材料围绕一个明确沟通目标展开，不是多主题资料合集。
- 用户重视整体观感、统一风格、缩略图效果和现场讲解体验。
- 用户接受正文和图表以图片形式存在，不要求所有元素可编辑。
- 材料用于正式汇报、售前交流、内部同步、方案介绍、培训讲解、复盘展示等场景。
- 用户希望保留逐页提示词，便于重抽、迁移和复用。

### 标准流程

1. 判断是否适合图片型 PPT。
2. 澄清使用场景、沟通目标、受众、页数、详略、风格、模板、Logo、输出格式和禁止内容。
3. 读取用户材料，整理逐页大纲：标题、页面目标、2-4 条核心信息。
4. 按 [references/prompt-patterns.md](references/prompt-patterns.md) 写逐页详细提示词。
5. 调用 imagegen 生成 16:9 整页图。不要让 imagegen 生成真实 Logo、二维码、印章或品牌标识。
6. 裁切/缩放到统一 16:9，遮盖 Logo 占位区，叠加真实 Logo。
7. 使用 `scripts/package_image_deck.py` 封装为 PPTX，可选导出 PDF 和每页 PNG。
8. 生成汇总预览图（contact sheet）和 QA 记录。

### 默认交付物

- 图片型 `.pptx`
- 逐页详细提示词
- 汇总预览图（contact sheet）
- QA 检查记录

可选交付 PDF、每页 PNG、来源与证据清单。

## 模式二：语义可编辑重组

这个模式从参考图重建 PPT，但最终 PPT 不能插入整页原图，也不能用带硬边、残字、残框的原始 crop 作为最终素材。

### 核心规则

- 原图只作为参考和定位来源，不进入最终 PPT。
- 每个非文字视觉元素先拆成最小语义单元，再生成或清理为独立透明资产。
- 一个图标、一个装饰件、一个风险徽章、一个 3D 物体、一个流程符号、一个箭头，就是一个独立资产和一个 PPT 图片对象。
- 文本全部用可编辑文本框；卡片、容器、底板、分隔线、普通结构形状用 PPT 原生对象。
- 图片资产只允许等比例 contain，不允许横纵拉伸。
- 不能把多个语义视觉合并成一张最终图片，除非它是明确批准的无文字场景背景。

### 工作流

1. 建立输出目录，保存 `reference_page_*.png` 作为参考。
2. 建立 `visual_inventory.json`：列出文字、容器、图标、箭头、装饰、3D 元素和风险标记。
3. 建立 `asset_anchors.json`：为每个待生成资产记录 bbox、语义、目标尺寸、层级。
4. 为资产写 imagegen/API 提示词。提示词要求 isolated asset grid、无文字、无数字、无卡片框、无背景、可透明化。
5. 使用 `scripts/grid_cut.py` 切分资产网格，去背景、alpha trim，并生成 `asset_manifest.json`。
6. 用 PPT 原生对象重建文字、卡片、容器和结构；用透明资产插入语义视觉。
7. 渲染 PPTX 为 PNG/PDF，使用 `scripts/compare_render.py` 生成汇总预览图和差异热力图（diff heatmap）。
8. 使用 `scripts/validate_semantic_deck.py` 检查没有整页原图、没有参考图 hash、没有原图硬裁片媒体，并输出验证报告。

详细执行规则见 [references/semantic-replica-workflow.md](references/semantic-replica-workflow.md)。
局限性和验收口径见 [references/limitations.md](references/limitations.md)。

### 必要工作文件

```text
reference_page_*.png
visual_inventory.json
asset_anchors.json
prompts/assets_cycle_*.jsonl
generated/
assets/
asset_manifest.json
layout_rules.json
build_deck.*
render/
compare/
validation_report.md
```

### 验收标准

- PPTX 可以打开并正常渲染。
- 最终 PPTX 不包含整页参考图作为媒体。
- 参考图 hash 没有出现在 PPTX 媒体中。
- 每个语义资产都有 `semantic_unit_id`、`source_type`、`asset_path`、`semantic_unit_count: 1`。
- 文字可选中、可编辑，且不是隐藏透明文本冒充可编辑。
- 重要图标、箭头、3D 元素、角落装饰没有矩形硬边、残字、截断或邻近卡片碎片。
- 输出汇总预览图、差异热力图、对象计数和验证报告。
- 字号、换行和图标位置以目标用户实际 PowerPoint 打开结果为最终准线。

## 模式三：SVG 结构重绘

这个模式从参考图重新搭建 SVG 结构，适合用户只要 SVG，或要验证页面能否拆成矢量结构。它不是 PowerPoint 对象级重建的充分条件。

### 适配条件

- 用户明确要求输出 `.svg`。
- 页面主要由文本、容器、线条、简单图标、流程箭头和信息图结构组成。
- 用户接受 SVG 与原图存在样式差异，并以可编辑结构和清晰预览为优先。

### 工作流

1. 读取参考图，拆分文本、容器、背景、图标、箭头、装饰层。
2. 用原生 SVG 重建页面层级，文本、色块、线条和图形都要成为独立 SVG 对象。
3. 输出 SVG 和 PNG 预览，检查文字、层级、比例和主要视觉元素。
4. 如果用户要 PPTX，只能作为可选嵌入或继续进入语义可编辑重组模式。不要承诺 SVG 导入 PowerPoint 后所有内部路径都稳定可编辑。

### 交付物

- `.svg`
- PNG 预览
- 简短说明：哪些对象是 SVG 原生对象，哪些元素做了简化，是否适合继续转 PPTX

## 安全与脱敏

- 公开仓库和可复用 skill 不能包含客户材料、内部项目路径、真实样例、真实 Logo、报价、合同、密钥、cookie、token 或未脱敏坏例。
- 示例必须是脱敏演示图或抽象占位，不要从真实客户项目复制图片、PPT、生成资产、提示词或报告。
- 公开发布边界见 [references/publication-boundaries.md](references/publication-boundaries.md)。
- 发布前运行敏感扫描：

```bash
python scripts/audit_public_skill.py --root .
```

## 硬性规则

- 不编造数字、来源、标准、客户名或证据。
- 真实 Logo 一律后处理叠加，不交给 imagegen。
- 图片型 PPT 和可编辑 PPT 要明确区分。
- 语义可编辑重组模式下，原图 crop 只能是中间参考，不是最终资产。
- 每次交付都保留提示词、渲染预览、QA 记录和已知限制。
