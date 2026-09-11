# 示意图绘制：diagram-design skill 路径（HTML→PNG）

> 适用：可视化阶段（phase-08）与写作阶段补画的「示意图」（方法流程图/几何示意/方案示意图/结构图）。
> **优先走本路径**；skill 缺失或渲染失败 → 回退 matplotlib（§2-6）。

## §0 依赖与回退

- skill 位置：**vendored 于本 skill 内** `tools/diagram-design/`（与 <技能根>/prompts/、<技能根>/docs/ 同级；完整路径 = `<技能根>/tools/diagram-design`，下同）
- **路径唯一性（硬规则）**：只用上述 vendored 路径的 SKILL.md / references / assets / scripts。全局 skill `~/.dsh/skills/diagram-design` **不得使用**——它是上游默认皮肤（与本文件 §2 的论文中性色 token 不同），且版本可能漂移；两者混用会造成同一篇论文里示意图皮肤不一致
- 不可用判定：`ls` 失败，或 self_check / Chrome 截图失败且重试 1 次仍失败
- 回退后：在 figure-manifest 与 ledger 注明「回退 matplotlib + 原因」

## §1 读取（按序）

1. Read `<技能根>/tools/diagram-design/SKILL.md`，按 §3 选型（过程/决策类 → **flowchart**）
2. Read `<技能根>/tools/diagram-design/references/type-flowchart.md` 与 `references/style-guide.md`（**皮肤 token 用下方 §2 的论文中性色，忽略其默认值**）
3. 复制 `<技能根>/tools/diagram-design/assets/example-flowchart.html` 为基线，替换内容（不搬示例的样式之外的文案）
4. **优先级**：本文档纪律优先于 skill 示例/SKILL.md 默认——SKILL §0 风格门直接跳过（按 §2 token 执行）；示例中非 4px 字号（9/8.5/11px）一律不采用

## §2 皮肤 token（论文中性色，写死进 HTML）

| token | 值 |
|---|---|
| paper | `#ffffff` |
| ink | `#1a1a1a` |
| muted | `#4f5d75` |
| rule | ink @ 0.12 |
| accent | `#2e5aa8`（全图 ≤2 处强调）|
| accent-tint | `rgba(46,90,168,0.08)` |
| link | 同 accent |

## §3 硬性设计纪律（违反即返工）

- **4px 网格**：所有坐标/字号/尺寸整除 4（字号 8/12/16/20/24…，x/y 倍数 4）
- ≤9 节点、≤12 箭头、≤2 强调元素；目标密度 4/10（能删就删）
- 连线**正交直角**（弯角 r=6–8），禁止斜线；连线先于节点绘制（z 序）
- 箭头标签：不透明遮罩 + 与线 **6–10px 间隙**；标签遮罩不得压到后画的节点；CJK 标签**字号 12px**（无衬线 500，遮罩高 16px），不缩 9px
- 图例：底部横条（不放图区内部），viewBox 高度为其扩展 ~60px
- **页面无大标题**：SVG 从页面顶部开始，body 无 padding；图注放图下方（§4 样式）
- svg 根：`role="img"` + `aria-labelledby` → 前缀化 `title`/`desc` id（如 `slug-title`/`slug-desc`），`<title>` 为 svg 首子元素
- 无阴影、无 `box-shadow`；边框代替阴影

## §4 图注样式（图下方，小字浅色）

- 文字 = 图表名（如「模型选取与区间外推流程」），**不加「图N」编号**（编号由论文排版决定）
- 12px / `#6b7280` / font-weight 400 / 居中 / 与图间距 8px / 无背景块 / 行高 16px
- 页面总高 = SVG 高 + 8 + 16（可再 +8 底边距），全部整除 4

## §5 字体（沙箱 Chrome 无网络，离线必须可用）

- Google Fonts 引用可保留（有网时生效），但字体栈**必须**带本机回退，例如：
  - 无衬线：`'Geist', 'Noto Sans CJK SC', 'PingFang SC', 'Microsoft YaHei', sans-serif`
  - 等宽：`'Geist Mono', 'Noto Sans Mono CJK SC', monospace`
  - 衬线（标题/旁注）：`'Instrument Serif', 'Noto Serif CJK SC', serif`
- CJK 文字 ≥12px；不依赖 Google Fonts 加载成功

## §6 自检（两道机械 + 一道视觉，缺一不可；另附兜底手工抽查）

> 本节 4 条 = **3 道必做**（①② 两道机械脚本、③ 一道视觉复核）＋ **1 条兜底**（④，脚本或图像工具不可用时使用）；**①② 通过 ≠ 合格**。

1. **上游契约**：运行 `<技能根>/tools/diagram-design/scripts/self_check.py <html>`，失败 → 修复后重跑，仍失败 → 回退。注意它**只查无障碍/单文件安全契约，不查本文件的排版纪律**——通过它 ≠ 合格。
2. **本文件纪律（机械）**：运行 `<技能根>/scripts/figure_lint.py --svg <html> --png <png>`，P0 必须清零（4px 网格、连线正交、标签遮罩与线 6–10px 间隙、皮肤 token 白名单、墨迹贴边 ≥8px、2× 画布）。已知历史事故：`I(t)` 标签遮罩压在竖线上（覆盖 24px 连线中的 16px）、文本基线离网 2px、用了非 token 的 `rgba(26,26,26,0.05)`。
3. **视觉复核（人眼级）**：用图像读取工具逐张看 PNG，核对 ①标签有无重叠/被裁 ②图例是否压住图元 ③文字是否完整 ④图注与图形是否都在画布内。机械项全过但视觉上重叠/裁切 → 仍须重画。
4. 手工抽查（兜底）：坐标整除 4、无斜线连线、标签遮罩与线有间隙、图注在 SVG 下方且居中

## §7 截图（Chrome headless，命令模板）

```bash
google-chrome --headless=new --no-sandbox --disable-gpu \
  --user-data-dir=<outputDir>/.chrome-tmp \
  --hide-scrollbars --virtual-time-budget=3000 \
  --force-device-scale-factor=2 \
  --window-size=<画布宽1x>,<画布高1x> \
  --screenshot=<PNG 绝对路径> "file://<HTML 绝对路径>"
```

- **`--window-size` 用画布 1x（CSS 像素），配合 `--force-device-scale-factor=2` 输出真 2x**——窗口设成 2x 会把内容以 1x 留白在左上角、图注错位，且 `file` 无法区分，务必避免
- 例：HTML 画布 1040×752 → `--window-size=1040,752 --force-device-scale-factor=2` → PNG 2080×1504
- 截图后 `file <png>` 确认 "PNG image data" 且**尺寸 = 画布 2x**；再抽查图注在 PNG 中水平居中（可用 python3+PIL 查墨迹像素 x 范围中心 ≈ 宽度/2）
- 无效则重试 1 次，仍失败 → 回退 matplotlib

## §8 产物与登记

- PNG：`intermediates/q{id}/08-visualization/figures/fig_{q{id}}_示意图_{内容}.png`
- HTML 源文件**同名**：`.../figures/fig_{q{id}}_示意图_{内容}.html`（复审/修改用）
- figure-manifest 示意图行：「绘图方式」= `diagram-design`（回退时 = `matplotlib`）；数据来源列注明 results.json 字段
- 论文 `\caption` 由写作阶段写解读句（如「…流程（数据核验→外推限 1 年）」），避免与图注逐字重复
