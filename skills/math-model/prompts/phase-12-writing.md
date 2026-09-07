# 阶段模板 12：写作（writing）

> 你是全题级写作 agent（run-level 阶段，**全题级、无小问**，q=null），本模板定义你要做的全部工作。调度壳已注入：模式（full/quick）、依赖与产物路径。所有相对路径基于 outputDir 根。本阶段是全文 AI 味治理的最后防线，保留完整机制：**事实源表 → 叙事大纲 → 顺序主编撰写 → 交叉审查统一修复**。

## 统一节拍

1. 读 intermediates/state.json：确认前置门禁（gates 中前置阶段为 PASS），否则返回 {status:"FAIL", ...}
2. 读依赖文件（本阶段的 deps，路径已由调度壳注入）
3. 执行本阶段任务，写产物到指定路径
4. 更新 state.json 对应字段 + 追加 intermediates/ledger.md 一行
5. 返回 {status:"PASS|DRAFT|NEEDS_REVISION|FAIL|SKIPPED", artifact_path, summary≤200字}

## 规范引用

先 Read `skills/math-model/docs/writing-and-format.md`（不可用时按模板目录向上找 `docs/`）。本节相关：§一 论文写作规范（含 **AI 味治理 §一-13/14**、外部数据合规 §一-15）、§二 图表规范（CJK/单位/示意图自绘 §二-1..7）。**引用规范不复制内容**；AI 味检查项即 §一-13/14 与 §二-6 的落实清单。

## 输入

- `intermediates/00-problem.md` / `00-problem.json`：题面/论文规则/附件清单/subQuestions
- `intermediates/11-cross-review/cross-question-report.md`：跨问复核结论（已 PASS，写作须保持其口径）
- 各小问（q1、q2、…，数量以 00-problem.json 的 subQuestions 为准）：`q{id}/10-completed/question-summary.md`（定稿事实链）、`q{id}/04-formulation/draft.md` + `symbols.json` + `baseline-registry.md`、`q{id}/06-computation/results.json`、`q{id}/08-visualization/figure-manifest.md` + `figures/`、`q{id}/01-literature/literature.md`（引用登记）、`q{id}/03-assumptions/assumption-vNN.md`、`07-sanity/sanity-report.md`、`09-robustness/robustness.md`、`02-data/eda.md` + `data-collection.json`（有外部数据时）

> ⚠️ 全题级：`q{id}` 指各小问实际目录 q1/、q2/、…（本阶段无占位符替换）；产物写 `intermediates/12-writing/` 前缀。

## 执行步骤

### 1. 事实源表（单一事实源，先做）

写 `intermediates/12-writing/fact-sheet.md`——全篇唯一数字来源，从各问 question-summary.md、results.json、robustness.md、baseline-registry.md、symbols.json 提取：

- **keyNumbers**：全部关键数字 {number, label, 场景, sourcePath(产物文件+字段), 口径注意}
- **symbols**：全题符号统一表（跨问合并）
- **caliberNotes**：口径注意事项（如「名单=预算定容30户」）
- **datasetFacts**：数据集画像事实

⚠️ 只提取产物中**真实存在**的数字，不补全不推测；摘要与正文每个数字必须能在本表找到出处（终审逐字溯源）。

### 2. 叙事大纲

写 `intermediates/12-writing/narrative-outline.md`：围绕小问组织叙事弧线（每问独立故事单元 + 整体连贯）：① 方案逻辑为主线、改进融入推导 ② 问题驱动（每章回答什么问题）③ 节奏控制（推导→结果→亮点）④ 记忆点 ⑤ 摘要埋钩子。

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

### 4. 顺序主编撰写

按上表顺序逐章撰写（后写章节强制读前文，杜绝口径分叉；每个 writer 是同一「主编」的延续视角）。开写每章前：① `ls` + `Read` 已写章节（跳过自己的），延续符号/数字/口径/术语/衔接 ② `Read` fact-sheet.md + 相关问 question-summary.md + figure-manifest.md ③ 需要时 `Read 00-problem.md`。

每章保存为 `intermediates/12-writing/paper-sections/section-<id>.md`：首行 `# <章节名>`，其后为本章 LaTeX body（含章节标题 `\section{...}`）；**不含** `\documentclass`/`\begin{document}`/`\maketitle`；引用用 `\cite{<登记表编号>}`（编号来自 literature.md 引用登记表；参考文献由终审统一生成，章节内不写 thebibliography）；无身份/学校/赛区信息。

**关键约束（逐章检查）**：
- 数字纪律：每个数值必须来自 fact-sheet.md（可溯 sourcePath）；禁编造/推算/跨章不一致；缺失写[待定]
- 逐问覆盖：摘要分段；模型/分析/结论章覆盖全部小问（模型→求解→结果）
- 加粗只加答案（`$\bm{}$`）；禁止「创新点：」等标签（§一-2/3）
- 图表：读 figure-manifest.md 并 `ls` figures/ 确认真实文件；按「对于问题N」位点分配（`fig_eda_*` 进数据章、`fig_cross_*` 进综合分析）；`\includegraphics{绝对路径}` + 「如图X所示…」解读；**includegraphics 文件必须真实存在，禁止空 figure**；需要示意图而没图 → matplotlib 自绘（§二-6：CJK 字体、dpi=200、bbox_inches='tight'、保存后 ls 确认）`fig_cross_示意图_<内容>.png` 存 `figures/` 根目录；单位 LaTeX math（`cm$^{-1}$`）
- **AI 味治理检查项（逐条自查，§一-13/14 + §二-6）**：
  1. 一段一意：每段先答「这一小步解决什么问题」，一段只讲一件事
  2. 公式三步走：关键公式按「动机→推导→含义」给中间步骤、说明式子含义，**禁止只贴最终式加一句说明**
  3. 术语首次出现用一句大白话解释，一段内未解释术语 ≤3 个
  4. 句子短、段落短（3-6 行），删「值得注意的是/综上所述/本文系统地」等凑字腔
  5. 摘要/每节开头给「路标」（「针对问题N，我们建立X模型：先…接着…然后…」）
  6. 禁止标签/目录腔（「创新点：」「本模型具有以下优势：(1)(2)(3)」）
  7. **禁止内部流程术语**：「对抗性审查/模型重设计/adversarialFindings/验证器/重设计历史」不得出现（§一-14）；局限转述成论文语言（「进一步分析表明当X时模型失效」）
  8. 范文基准：2024 板凳龙国一（A053）——摘要逐问分段、推导一步步来

### 5. 交叉审查 ⇄ 统一修复

全部章节写完后进入交叉审查 loop（full 3 轮 / quick 1 轮；连续 2 轮无新问题收敛）。

**每轮交叉审查**（写 `intermediates/12-writing/cross-review-r<N>.md`，逐项 `[P0/P1/P2] [章节] 问题 | 修复建议`）：
1. 符号统一：重述→模型→结果符号一致（对照 fact-sheet symbols）
2. 数据一致：**摘要每个数字在正文有出处**，找不到 → P0
3. 逻辑连贯：假设→推导→结果→结论无断点
4. 创新呼应：创新点各章呼应（对照 11-cross-review）
5. 重复/矛盾：不同章节重复或矛盾
6. 章节数量与排序：全部存在；结论为最后一章（P0）
7. 图表双向：figures/ 文件都被引用（P1）；includegraphics 文件真实存在、无空 figure（P0）
8. 内部流程术语 → P1（改写为论文语言）
9. 推导链：公式是否「动机→推导→含义」三步 → P1
10. 术语堆砌/可读性：一段 >3 未解释术语、冗长啰嗦 → P1
11. 逐问覆盖：问题分析/模型/分析/结论各章覆盖全部小问 → 缺失 P0
12. AI 味复核：§一-13/14 逐条（路标/标签/凑字腔/加粗过度/示意图）

**统一修复**：按章节顺序逐章修复：`Read` 全篇文章节 + fact-sheet + 问题列表，只修指出的问题（精准手术，不重写整章）；数字以 fact-sheet 为准；口径：术语堆砌→补解释并精简；只贴公式→补「动机→推导→含义」；啰嗦→删除；内部术语→改写。修复后覆盖写回 section-*.md。

收敛或达轮次上限 → 结束；残留未修 P0 → 返回 **NEEDS_REVISION** 并在 summary 列出。

## 产物

- `intermediates/12-writing/paper-sections/section-*.md`（主产物）
- `intermediates/12-writing/fact-sheet.md`、`narrative-outline.md`、`cross-review-r*.md`（工作文档）

## 完成标准

- 全部章节按序写完，章节名与组装脚本 order 一致
- 交叉审查收敛（无未修 P0）；摘要数字可溯源到正文与 fact-sheet.md
- AI 味检查项逐条通过；图表双向验证通过；无内部流程术语
- 一致 → PASS；残留必须修订项 → NEEDS_REVISION
