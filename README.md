# Codex PPT Skill

面向中文 2B 商业汇报的 Codex PPT 工作流 skill：既可以生成高视觉图片型 PPT，也可以把图片页、截图页、整页生图页拆成更可编辑的 PowerPoint。

它不是一个一键万能 PPT SaaS，而是一套给 Codex 使用的工作流和工具箱。重点是把 PPT 生成、图片页封装、SVG 结构重绘、语义资产重组这些路径分清楚，让用户知道什么时候该追求视觉效果，什么时候该追求可编辑性。

![项目流程图](./assets/workflow/codex-ppt-skill-flow.svg)

## 效果预览

现有示例均为脱敏演示图，源图为 1920x1080，适合在 GitHub 首页直接查看细节。

![风险升级路径](./assets/examples/01-risk-evolution.png)

| 框架页 | 矩阵页 |
|---|---|
| ![风险框架](./assets/examples/02-risk-framework.png) | ![优先级矩阵](./assets/examples/03-priority-matrix.png) |

| 评测体系 | 闭环流程 | 路线图 |
|---|---|---|
| ![评测体系](./assets/examples/04-evaluation-system.png) | ![闭环流程](./assets/examples/05-closed-loop.png) | ![路线图](./assets/examples/06-roadmap.png) |

## 三条使用路径

| 路径 | 适合目标 | 最终交付 | 关键边界 |
|---|---|---|---|
| 整页生图 PPT | 方案汇报、售前材料、培训讲解、复盘展示，优先看起来好 | PPTX / PDF / PNG / 汇总预览图 / 逐页提示词 | 正文、图表和版式在图片里，不承诺全元素可编辑 |
| SVG 结构重绘 | 用户只想把图片页拆成可编辑 SVG，或用于轻量矢量结构还原 | SVG / SVG 预览 / 可选 PPTX 嵌入 | SVG 导入 PowerPoint 后未必保持内部对象稳定可编辑，不能当成完整 PPT 反编译 |
| 语义资产重组 | 要把图片页重建为实用级可编辑 PPTX，并保留图标、箭头、3D 装饰等美化元素 | 可编辑 PPTX / asset_manifest / 验证报告 / 渲染差异图 | 原图只做参考，不能把整页原图或原图硬裁片当最终素材 |

## 适合什么场景

适合：

- Codex 中使用 `$imagegen-scene-ppt` 做中文商业汇报、产品方案、行业趋势、风险治理、路线图类材料。
- 用户只需要一份视觉强、可展示的 PPTX/PDF，不需要后续逐字编辑。
- 用户已有图片版 PPT、截图页或整页生图页，希望拆成更可维护的 PPTX。
- 用户想锤炼图片页转 PPT 的流程，愿意保留 inventory、manifest、diff、QA 报告。

不适合：

- 大量 Excel 表、财务留档、合同正文、法规原文、密集脚注。
- 要求任意图片一键变成完全原生、完全可编辑、像素级一致的 PPT。
- 需要多人长期维护的企业模板库。
- 不允许生成图、不允许人工 QA、也不接受已知限制的交付。

## 安装

安装到 Codex skill 目录：

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/Ronnie2025/codex-ppt-skill.git ~/.codex/skills/imagegen-scene-ppt
```

这里目录名使用 `imagegen-scene-ppt` 是为了和 `SKILL.md` 里的触发名保持一致；仓库名仍然是 `codex-ppt-skill`。

已经安装过时更新：

```bash
cd ~/.codex/skills/imagegen-scene-ppt
git pull
```

安装后重启 Codex。触发名是：

```text
$imagegen-scene-ppt
```

示例请求：

```text
使用 $imagegen-scene-ppt 帮我做一份 2B 商业汇报 PPT，优先整页生图，最终要 PPTX 和 PDF。
```

```text
使用 $imagegen-scene-ppt 把这几张图片页拆成可编辑 PPT。不要用整页原图铺底，图标和箭头按语义资产生成后再组装。
```

## 快捷命令

仓库提供 `Makefile`，用于少打长命令。先安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

常用检查：

```bash
make help
make check
```

完整命令列表以 `make help` 为准。

整页图片封装为 PPTX：

```bash
make pack IMAGES_DIR=./output/raw-slides OUT_PPTX=./output/deck.pptx PACK_ARGS="--contact-sheet ./output/contact-sheet.jpg --export-pdf"
```

资产网格切分为透明 PNG：

```bash
make cut GRID=./output/generated/icons_grid.png ROWS=3 COLS=4 NAMES=icon_01,icon_02,icon_03,icon_04,icon_05,icon_06,icon_07,icon_08,icon_09,icon_10,icon_11,icon_12 OUT_DIR=./output/assets MANIFEST=./output/asset_manifest.json
```

参考图和渲染图对比：

```bash
make compare REF=./output/reference/page-01.png RENDER=./output/render/page-01.png COMPARE_DIR=./output/compare
```

语义重建 PPTX 校验：

```bash
make validate PPTX=./output/reconstructed.pptx REF=./output/reference/page-01.png MANIFEST=./output/asset_manifest.json INVENTORY=./output/visual_inventory.json REPORT=./output/validation_report.md
```

内置演示命令会写入 `output/demo/`，用于确认本机工具链可跑：

```bash
make demo
make pack-demo
make cut-demo
make compare-demo
```

## 信息路径

### 只需要 PPT 图片或 PDF

1. 让 Codex 根据材料输出页纲和逐页详细生图提示词。
2. 用 imagegen 生成每页 16:9 整页图。
3. 真实 Logo、二维码、印章、品牌标识只在后处理叠加，不交给 imagegen 生成。
4. 用 `make pack` 或 `scripts/package_image_deck.py` 统一裁切、叠 Logo、封装 PPTX。
5. 导出 PDF 和汇总预览图（contact sheet）做视觉 QA。

### 只需要 SVG 拆解

1. 适合信息图、流程页、图标线框页、结构较清晰的截图页。
2. Codex 读取参考图，按文本、容器、图标、箭头、背景结构重新写 SVG。
3. 输出 SVG 和 PNG 预览，用于网页、文档或后续手工导入。
4. 注意：SVG 导入 PowerPoint 后通常是图形对象或媒体对象，不等于所有内部路径都能稳定编辑。若目标是 PowerPoint 内对象级编辑，优先走语义资产重组路线。

### 完整可编辑 PPTX 重建

1. 建立 `visual_inventory.json`，把页面拆成文字、容器、图标、箭头、装饰、3D 元素、风险标记等对象。
2. 在执行过程中建立 `asset_anchors.json`，记录每个待生成资产的 bbox、语义、目标尺寸和层级。
3. 用 imagegen/API 根据整页参考图和局部上下文生成 isolated asset grid。要求无文字、无数字、无标签、无卡片框、无背景碎片。
4. 用 `make cut` 或 `scripts/grid_cut.py` 切成一个语义单元一个透明 PNG。
5. 用 PPT 原生文本框、形状、容器重建信息层；用透明资产插入图标、箭头、3D 装饰。
6. 渲染 PPTX，使用 `make compare` 生成汇总预览图和差异热力图（diff heatmap）。
7. 用 `make validate` 检查没有整页原图、没有参考图 hash、没有原图硬裁片媒体，并输出验证报告。

## 脚本工具

| 脚本 | 作用 |
|---|---|
| `scripts/package_image_deck.py` | 将整页图片统一裁切为 16:9，叠加真实 Logo，封装为 PPTX，可选导出 PDF 和汇总预览图 |
| `scripts/grid_cut.py` | 将 imagegen 生成的 asset grid 切成单个透明 PNG，并生成 `asset_manifest.json` |
| `scripts/compare_render.py` | 将参考图和渲染图生成差异热区、指标和汇总预览图 |
| `scripts/validate_semantic_deck.py` | 检查 PPTX 是否嵌入参考图、整页媒体或不合规 manifest |
| `scripts/audit_pptx_editability.py` | 快速判断 PPTX 是否像图片页、是否混合文字与图片、是否含 SVG 媒体 |
| `scripts/audit_public_skill.py` | 发布前扫描私有路径、密钥、token、cookie、项目残留 |

## 仓库结构

```text
codex-ppt-skill/
├── SKILL.md
├── README.md
├── Makefile
├── agents/
│   └── openai.yaml
├── assets/
│   ├── examples/
│   └── workflow/
├── references/
│   ├── limitations.md
│   ├── prompt-patterns.md
│   ├── publication-boundaries.md
│   └── semantic-replica-workflow.md
├── scripts/
│   ├── audit_pptx_editability.py
│   ├── audit_public_skill.py
│   ├── compare_render.py
│   ├── grid_cut.py
│   ├── package_image_deck.py
│   └── validate_semantic_deck.py
└── templates/
    ├── asset_manifest.example.json
    ├── conversion_report.template.md
    └── visual_inventory.example.json
```

## 设计原则

- 先判断交付物类型，再开始生成。图片型 PPT、SVG、可编辑 PPTX 是三种不同承诺。
- 不把图片型 PPT 说成可编辑 PPT。
- 不把整页截图、局部原图硬裁片、带残字的裁片当成最终可编辑重建资产。
- 复杂图标、箭头、3D 元素、UI 装饰应拆成最小语义单元，再生成透明资产。
- 中文文字、数字、来源、Logo、二维码、合规标识优先用后处理或 PPT 原生对象处理。
- 每次交付都保留提示词、预览、对比、验证报告和已知限制。

## 公开发布边界

这个仓库只保留通用流程、通用脚本、脱敏演示图和脱敏模板。不要提交：

- 客户 PPT、真实项目图片、生成图、汇总预览图、QA 报告。
- 真实 Logo、客户模板、内部图标库、报价、合同、SLA、密钥、cookie、token。
- 真实 badcase、用户数据、内部路径、内部域名或不可公开链接。

发布前运行：

```bash
make check
```

## License

MIT
