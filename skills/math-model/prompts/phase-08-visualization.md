# 阶段模板 08：可视化（visualization）

> 你是本小问的可视化 agent，本模板定义你要做的全部工作。

> 工具纪律（减回合）：全部图集中为一个绘图脚本、一次 bash 跑完并统一 `ls` 校验，禁止逐图微循环。

> 公共纪律见 `_common.md`（壳与模板一并注入）。

## 规范引用

规范引用：先 Read `<技能根>/docs/writing-and-format.md`（技能根见 `_common.md` §2.7）。本节相关：**§二 图表生成规范**（CJK 字体 §二-1、LaTeX math 单位 §二-2/3、Glyph 验证 §二-5、示意图自绘 §二-6、结果图/示意图分工 §二-7、**结果图硬条款 §二-8、图文件路径口径 §二-9**）；示意图 HTML→PNG 路径另见 `docs/flowchart-drawing.md`。引用规范，不复制内容。

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
- 命名：`fig_{q{id}}_{内容具体描述}.png`——**命名即 caption**，文件名要让人不看图就知道图里有什么（如 `fig_qX_<被测量>随<自变量>变化.png`、`fig_qX_<方案A>与<方案B>对比.png`）；禁止 `fig_q1_result.png`、`fig_q1_plot1.png` 这类
- **绘图脚本落盘**：`intermediates/q{id}/08-visualization/plot_figures.py`（同目录，可重跑；脚本内路径用绝对/相对 outputDir，**从 results.json 读数值，不硬编码**）

### 3. 自绘示意图


需要而现有图没有的示意图 → **优先用 vendored diagram-design 画**（HTML→PNG，完整配方 Read `docs/flowchart-drawing.md`；**只用** `<技能根>/tools/diagram-design/`，不得用全局 skill）；skill 缺失或渲染失败（重试 1 次后）→ **回退 python3 + matplotlib**（§二-6，dpi=200、bbox_inches='tight'）。两种路径都**禁止留空**：命名 `fig_{q{id}}_示意图_{内容}.png`，保存后 `ls` 确认真实存在；diagram-design 路径**另存同名 `.html` 源文件**，figure-manifest 示意图行加「绘图方式」（diagram-design|matplotlib）。

### 4. 出图自检（两道机械 + 一道视觉，P0 未清零不写 manifest）

1. **规范逐条**：按 §二-1..7 检查（CJK 字体生效、无 Glyph 警告、单位/下标用 LaTeX math）；按 **§二-8 结果图硬条款 12 条**逐条自查。
2. **机械自检**（在 outputDir 下执行；路径按上述落盘约定）：
   ```bash
   python <技能根>/scripts/figure_lint.py \
     --py intermediates/q{id}/08-visualization/plot_figures.py \
     --png intermediates/q{id}/08-visualization/figures/*.png \
     --svg intermediates/q{id}/08-visualization/figures/*.html --render
   ```
   P0 清零（`<技能根>` 见 `_common.md` §2.7）。
3. **视觉复核（人眼级，必须有）**：用图像读取工具逐张看 PNG，列出缺陷清单（标签重叠/被裁、图例遮挡图元、尺度不可辨、坐标范围失衡、图-题不符、颜色/标记未进图例）；P0 修完重出并复看。若图像读取工具不可用（报不支持图像输入/权限拒绝）→ 在 manifest 自检节如实记录「视觉复核未执行 + 原因」，并按 §二-8 逐条自查代码，**不得因此 FAIL 或反复重试**。
4. 自检结论（lint 结果 + 视觉复核缺陷与处置）写入 figure-manifest 的「自检」一节；**禁止在 manifest 里写「self_check 通过」代替上述检查**（上游 self_check 只查无障碍契约，不查本项目纪律）。

### 5. 产出 figure-manifest.md 与图文件

- 图文件保存到 `intermediates/q{id}/08-visualization/figures/`
- `intermediates/q{id}/08-visualization/figure-manifest.md`（主产物；字段集见 `<技能根>/prompts/artifact-schemas.md` §2），每张图一行：文件名 / 类型（结果|示意图）/ 一句话作用 / 数据来源（results.json 字段名，**不抄数值**）/ 绘图方式 / 计划引用位点（论文章节与位置）；另设「自检」一节记录 §4 的两道机械 + 一道视觉结论
- **反向校验（P0）**：manifest 每条引用必须对应 figures/ 真实存在的文件；**空 figure 环境（有 caption 无图）是 P0 事故**——本阶段宁画示意图也不留空

## 产物

- `intermediates/q{id}/08-visualization/figure-manifest.md`（主产物）+ `figures/` 目录

## 完成标准

- 本问 ≥3 图（结果 ≥2 + 示意图 ≥1，或注明理由）；命名即 caption；CJK/单位规范通过
- manifest 完整且与文件一一对应（反向校验通过）
- 图中数值与 results.json、sanity-report 一致，不出现新数字
