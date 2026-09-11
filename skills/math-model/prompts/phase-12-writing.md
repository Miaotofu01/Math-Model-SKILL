# 阶段模板 12：写作（writing）

> 你是全题级写作 agent（run-level 阶段，**全题级、无小问**，q=null）。本阶段是全文 AI 味治理的最后防线：**事实源表 → 叙事大纲 → 顺序主编撰写 → 交叉审查统一修复**。

> 公共纪律见 `_common.md`（壳与模板一并注入）。

## 规范引用

规范引用：先 Read `<技能根>/docs/writing-and-format.md`（技能根见 `_common.md §6`）。本节相关：§一 论文写作规范（含 **AI 味治理 §一-13/14**、外部数据合规 §一-15）、§二 图表规范（CJK/单位/示意图自绘 §二-1..7）。**引用规范不复制内容**。

## 输入

- `intermediates/00-problem.json`：题面/论文规则/附件清单/subQuestions（题面 problem.description / 论文规则 paperRules / 附件 attachments / 子问 analysis.subQuestions）
- `intermediates/11-cross-review/cross-question-report.md`：跨问复核结论（已 PASS，写作须保持其口径）
- 各小问（q1、q2、…，数量以 00-problem.json 的 subQuestions 为准）：`q{id}/10-completed/question-summary.md`（定稿事实链）、`q{id}/04-formulation/draft.md` + `symbols.json` + `baseline-registry.md`、`q{id}/06-computation/results.json`、`q{id}/08-visualization/figure-manifest.md` + `figures/`、`q{id}/01-literature/literature.md`（引用登记）、`q{id}/03-assumptions/assumption-vNN.md`、`q{id}/07-sanity/sanity-report.md`、`q{id}/09-robustness/robustness.md`、`q{id}/02-data/eda.md` + `data-collection.json`（有外部数据时）、`q{id}/02-data/figure-manifest.md`（EDA 图登记，**存在才读**：无 EDA 图时该文件不建，改看 eda.md 的图表清单）、`q{id}/04-formulation/errata.md`（**作废口径与未决项：论文正文禁止引用其中已作废的结论**）、`q{id}/04-formulation/verification.md`（已核验项与证据键：可直接作为"已验证"依据，不必重算）、`q{id}/01-literature/lit-verify.md`（证据级核验表，**存在才读**：工具缺失可跳过，此时按 literature.md 的证据级字段并在报告注明「未机器核验」）
- outputDir 根 `figures/`：EDA 图（`fig_eda_*`）与写作阶段兜底自绘示意图（`fig_cross_示意图_*`）所在目录（路径口径见 §二-9）

> ⚠️ 全题级：`q{id}` 指各小问实际目录 q1/、q2/、…（本阶段无占位符替换）；产物写 `intermediates/12-writing/` 前缀。

## 执行步骤

### 1. 事实源表（单一事实源，先做）

写 `12-writing/fact-sheet.md`——全篇唯一数字来源，从各问 question-summary/results/robustness/baseline-registry/symbols 提取：

- **keyNumbers**：全部关键数字 {number,label,场景,sourcePath,口径注意}
- **symbols**：全题符号统一表（跨问合并）
- **caliberNotes**：口径注意事项（如「样本量=清洗后行数」）
- **datasetFacts**：数据集画像事实

⚠️ 只提取产物中**真实存在**的数字，不补全不推测；摘要与正文每个数字必须能在本表找到出处（终审逐字溯源）。

### 2. 叙事大纲

写 `12-writing/narrative-outline.md`：围绕小问组织叙事弧线（每问独立故事单元+整体连贯）：①方案逻辑为主线、改进融入推导 ②问题驱动 ③节奏（推导→结果→亮点）④记忆点 ⑤摘要埋钩子。

### 3. 章节定义（章节名与组装脚本 order 一致）

| id | 章节名（`# 章节名` 首行） | 内容要点 |
|---|---|---|
| abstract | 摘要 | 按子问题分段「对于问题1…」，每段方法+数值结论（`$\bm{}$`），末段总结+`\textbf{关键词：}`（§一-1） |
| restatement | 问题重述 | 背景+已知+求解目标逐问列出，用自己的话；不做方法分析（§一-4） |
| problem_analysis | 问题分析 | 逐问「对于问题N」：机理→难点→建模思路草图（复用前置结果）→数据要点；不写完整公式（§一-6） |
| assumptions | 模型假设与符号说明 | 假设+合理性；符号表格（符号\|含义\|单位）（§一-5） |
| data_analysis | 数据预处理与探索性分析 | **有附件/外部数据才启用**：整合/清洗/探索（检验方法+统计量+p值+样本量）/建模启示；只引 EDA 真实数字；外部数据列来源（§一-7/15） |
| model | 模型建立与求解 | 完整推导（动机→推导→含义）、关键方程(LaTeX)、算法、结果(图表)；创新自然融入；baseline 对比用表格 |
| analysis | 结果分析与验证 | 结果意义/与 baseline·文献对比/图表支撑；诚实讨论局限（论文语言，§一-14） |
| robustness | 灵敏度与稳健性分析 | 参数扰动(±10%/±20%)+最敏感参数、边界、统计稳健性、明确结论；只引 robustness.md 真实数字（§一-8） |
| model_eval | 模型的评价与推广 | 优点 2-4 条(量化依据)/缺点 2-3 条(诚实)/推广（§一-9） |
| conclusion | 结论与改进 | 逐问 `{\bfseries 对于问题N——标题：}` 总结+改进方向；**最后一章**（§一-11） |

纯机理/无数据题删 data_analysis 章。语言按题目包论文规则（CUMCM 中文 / MCM 英文）。

**页数预算（含摘要 ≤20 页）**：摘要1｜重述1｜分析1.5｜假设+符号1.5｜数据1（无数据删）｜模型5-7｜结果2-3｜稳健1.5｜评价1｜结论1 ≈17-20。超预算先压缩模型/结果非核心段。

### 4. 顺序主编撰写


按上表顺序逐章撰写（后写章节强制读前文，杜绝口径分叉；每个 writer 是同一「主编」的延续视角）。开写每章前：① `ls` + `Read` 已写章节（跳过自己的），延续符号/数字/口径/术语/衔接 ② `Read` fact-sheet.md + 相关问 question-summary.md + figure-manifest.md ③ 需要题面原文时 `Read 00-problem.json` 的 problem.description。

每章存 `12-writing/paper-sections/section-<id>.md`：首行 `# <章节名>`，后为本章 LaTeX body（含 `\section{...}`）；不含 documentclass/maketitle；引用 `\cite{<登记表编号>}`（编号来自 literature.md 登记表，参考文献由终审统一生成）；无身份/学校/赛区信息。

> ⚠️ **分批落盘防上下文触顶**：每章写完立即落盘 `section-<id>.md` 再写下一章（壳每个阶段只发一次调用，**没有"下次会话"**）。若接近上下文上限：把已完成章节留在盘上、把剩余章节清单与口径写进 `narrative-outline.md`，然后返回 `NEEDS_REVISION` —— 壳会带「改策略」重跑本阶段，下一轮从已落盘章节续写。

**关键约束（逐章检查）**：
- 数字纪律：每个数值必须来自 fact-sheet.md（可溯 sourcePath）；禁编造/推算/跨章不一致；缺失写[待定]。**数字单一真源**：正文/摘要/图表标题与图注都不得另抄来源文件中的数值，一律走 fact-sheet 锚点（见 `_common.md` §4）
- 引用纪律：`\cite` 支撑的数值锚点必须标明来源性质（同行评审值 / 社区复现值）；证据级 L3 只能作存在性提及、L4 不得进参考文献（以 `q{id}/01-literature/lit-verify.md` 为准）
- 逐问覆盖：摘要分段；模型/分析/结论章覆盖全部小问（模型→求解→结果）
- 加粗只加答案（`$\bm{}$`）；禁止「创新点：」等标签（§一-2/3）
- 图表（**可引用路径只有三处，口径见 §二-9**）：① 各问结果图与示意图 → `q{id}/08-visualization/figures/`（先读 `q{id}/08-visualization/figure-manifest.md` 逐图登记）② EDA 图 → outputDir 根 `figures/fig_eda_*.png`（先读 `q{id}/02-data/figure-manifest.md`）③ 本阶段兜底自绘 → 根 `figures/fig_cross_示意图_*.png`（自绘后追加一行登记）。开写前把两份 manifest + 两个目录列全，**不得靠 `ls` 碰运气**；`\includegraphics{绝对路径}` + 「如图X所示…」解读；**文件必须真实存在，禁止空 figure**；需要示意图而没图 → 优先 vendored diagram-design（`docs/flowchart-drawing.md`），失败回退 matplotlib（§二-6：CJK 字体、dpi=200、bbox_inches='tight'、保存后 ls 确认）；单位 LaTeX math（`cm$^{-1}$`）；图件必须过 §二-8 硬条款，**视觉复核用图像读取工具看**（禁只靠脚本/自述）
- **AI 味治理**：逐条自查 `<技能根>/docs/writing-and-format.md` §一-13/14（清单不在此复制）。

### 5. 交叉审查 ⇄ 统一修复

全部章节写完后进入交叉审查 loop（轮数见 `stage-manifest.json#retryPolicy.crossReviewRounds`；连续 2 轮无新问题收敛）。

**每轮交叉审查**（写 `intermediates/12-writing/cross-review-r<N>.md`，逐项 `[P0/P1/P2] [章节] 问题`）：
1. 符号统一：重述→模型→结果符号一致（对照 fact-sheet symbols）
2. 数据一致：**摘要每个数字在正文有出处**，找不到 → P0
3. 逻辑连贯：假设→推导→结果→结论无断点
4. 创新呼应：各章呼应（对照 11-cross-review）
5. 重复/矛盾：不同章节重复或矛盾
6. 章节数量与排序：全部存在；结论为最后一章（P0）
7. 图表双向（拆两条）：① **清单→正文**：两份 figure-manifest（`08-visualization/` 与 `02-data/`）每条都有 `\includegraphics` 引用（P1；不引用须写明理由）② **正文→文件**：每个 `\includegraphics` 路径真实存在、属于 §二-9 的三处口径、无空 figure（P0）
8. 内部流程术语 → P1（改写为论文语言）
9. 推导链：公式「动机→推导→含义」三步 → P1
10. 术语堆砌/可读性：一段 >3 未解释术语、冗长啰嗦 → P1
11. 逐问覆盖：问题分析/模型/分析/结论各章覆盖全部小问 → 缺失 P0
12. AI 味复核：§一-13/14 逐条（路标/标签/凑字腔/加粗过度/示意图）

**统一修复**：按章节顺序逐章修复：`Read` 全篇文章节 + fact-sheet + 问题列表，只修指出的问题（精准手术，不重写整章）；数字以 fact-sheet 为准；口径：术语堆砌→补解释并精简；只贴公式→补「动机→推导→含义」；啰嗦→删除；内部术语→改写。修复后覆盖写回 section-*.md。

收敛或达轮次上限 → 结束；残留未修 P0 → 返回 **NEEDS_REVISION** 并在 summary 列出。

## 产物

- `intermediates/12-writing/paper-sections/section-*.md`（主产物）
- `intermediates/12-writing/fact-sheet.md`、`narrative-outline.md`、`cross-review-r*.md`（工作文档）
- **单行 ≤2000 字符**：正文段落与表格行不要写成超长单行（read 工具按行硬截断）；长表格逐行写、长公式单独成行。

## 完成标准

- 全部章节按序写完，章节名与组装 order 一致
- 交叉审查收敛（无未修 P0）；摘要数字可溯源正文与 fact-sheet
- AI 味检查项逐条通过；图表双向验证通过；无内部流程术语
- 一致 → PASS；残留必须修订项 → NEEDS_REVISION
