# 阶段模板 08：可视化（visualization）

> 你是本小问的可视化 agent，本模板定义你要做的全部工作。调度壳已注入：当前小问 ID（ctx 中的 `q`，如 `q1`）、模式（full/quick）、依赖与产物路径。下文路径中 `q{id}` 替换为 ctx 中的小问 ID；所有相对路径基于 outputDir 根。

## 统一节拍

1. 读 intermediates/state.json：确认前置门禁（gates 中前置阶段为 PASS），否则返回 {status:"FAIL", ...}
2. 读依赖文件（本阶段的 deps，路径已由调度壳注入）
3. 执行本阶段任务，写产物到指定路径
4. 更新 state.json 对应字段 + 追加 intermediates/ledger.md 一行
5. 返回 {status:"PASS|DRAFT|NEEDS_REVISION|FAIL|SKIPPED", artifact_path, summary≤200字}

## 规范引用

先 Read `skills/math-model/docs/writing-and-format.md`（如不可用，按调度壳的模板目录向上找 `docs/`）。本节相关：**§二 图表生成规范**（CJK 字体 §二-1、LaTeX math 单位 §二-2/3、Glyph 验证 §二-5、示意图自绘 §二-6、结果图/示意图分工 §二-7）；示意图 HTML→PNG 路径另见 `docs/flowchart-drawing.md`。引用规范，不复制内容。

## 输入

- `intermediates/q{id}/06-computation/results.json`：结果与数值（图的数据源）
- `intermediates/q{id}/07-sanity/sanity-report.md`：已核验结论（图必须与之一致）
- `intermediates/00-problem.json`：题面（problem.description，示意图内容依据）
- 需要时：`intermediates/q{id}/04-formulation/symbols.json`（坐标轴符号统一）、`06-computation/figures/`（已有图复用或重画）

## 执行步骤

### 1. 规划每问图表

本问至少 **3 张图**：结果图 ≥2（曲线/对比/分布/热力图等，数据驱动）+ 示意图 ≥1（几何示意/方法流程图/方案示意图/结构图，帮助读者理解思路；确无必要 → 在 manifest 写明理由）。结果中的关键结论（results.json 的 summary）必须有图支撑。

### 2. 生成结果图

- 数据源优先 results.json 的 keyValues/数组；需要原始数据时读 `06-computation/figures/`，或写 ≤50 行轻量绘图脚本（timeout 300s，不重跑完整计算）
- 命名：`fig_{q{id}}_{内容具体描述}.png`——**命名即 caption**，文件名要让人不看图就知道图里有什么（如 `fig_q1_去趋势振荡随波数变化.png`）；禁止 `fig_q1_result.png`、`fig_q1_plot1.png` 这类

### 3. 自绘示意图

需要而现有图没有的示意图 → **优先用 diagram-design skill 画**（HTML→PNG，完整配方 Read `docs/flowchart-drawing.md`）；skill 缺失或渲染失败（重试 1 次后）→ **回退 python3 + matplotlib**（§二-6，dpi=200、bbox_inches='tight'）。两种路径都**禁止留空**：命名 `fig_{q{id}}_示意图_{内容}.png`，保存后 `ls` 确认真实存在；diagram-design 路径**另存同名 `.html` 源文件**，figure-manifest 示意图行加「绘图方式」（diagram-design|matplotlib）。**分工调和**：本阶段按任务书强制自绘示意图（写作阶段可复用，不冲突 writing-and-format.md §二-7 的分工说明——本阶段产出先行，写作阶段负责最终编排）。

### 4. 图表规范自检

按 §二 逐张检查：CJK 字体生效（无 Glyph 警告）、单位用 LaTeX math（`cm$^{-1}$` 而非 `cm⁻¹`）、下标用 LaTeX math（`A$_2$/A$_1$` 而非 `A₂/A₁`）；每张图必须能被一句话解释作用。

### 5. 产出 figure-manifest.md 与图文件

- 图文件保存到 `intermediates/q{id}/08-visualization/figures/`
- `intermediates/q{id}/08-visualization/figure-manifest.md`（主产物），每张图一行：文件名 / 类型（结果|示意图）/ 一句话作用 / 数据来源（results.json 字段或脚本）/ 计划引用位点（论文章节与位置）
- **反向校验（P0）**：manifest 每条引用必须对应 figures/ 真实存在的文件；**空 figure 环境（有 caption 无图）是 P0 事故**——本阶段宁画示意图也不留空

## 产物

- `intermediates/q{id}/08-visualization/figure-manifest.md`（主产物）+ `figures/` 目录

## 完成标准

- 本问 ≥3 图（结果 ≥2 + 示意图 ≥1，或注明理由）；命名即 caption；CJK/单位规范通过
- manifest 完整且与文件一一对应（反向校验通过）
- 图中数值与 results.json、sanity-report 一致，不出现新数字
