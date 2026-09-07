---
name: math-model
description: 当用户需要完成数学建模竞赛（国赛CUMCM/美赛MCM）的完整或部分流程时使用。触发词：/math-model、数模、数学建模、国赛、美赛、建模比赛。症状：审题无从下手、数据画像缺失、求解验证脱节、摘要数字无出处、论文格式不合规。
disable-model-invocation: true
---

# 数学建模工作流

## Overview

架构师，不是做题家。国一核心：**正确性第一 + 数据说话**，摘要一锤定音。两阶段：一审题选题，二 Workflow 全自动执行。

**触发：** `/math-model`、数模、数学建模、国赛、美赛、建模比赛。不适用纯数学推导或无竞赛格式要求的普通问题。

## 你能做什么 / 不能做什么

| 阶段 | 你（主 agent）的角色 | 说明 |
|------|------|------|
| 阶段一 审题+选题 | **可干预**：并行提纯→审题→选题→等用户选 | 你只编排，机械透传原文/数据，不解读不润色 |
| 阶段二 执行 Workflow（phase3-8） | **不干预**：用 `workflow` 工具发起，前台阻塞等结算 | 内部 agent 全由脚本编排，行为规范硬编码在 `workflows/math-model.js`。你正常流程不了解内部细节 |
| 阶段三 汇报+兜底 | **可干预**：汇报、必要时手动兜底 | 见下 |

> **关键**：阶段二 Workflow 运行时你**看不到也管不了**内部 agent。别在 SKILL.md 里去找"该怎么让内部 agent 做 X"——它不读这里。内部执行规范在 `docs/writing-and-format.md`（你仅在**失败手动兜底**或**审查产物**时参考）。

## 阶段一：审题 + 选题

**Step 1: 输入提纯（每道题一个 Agent，并行）** — 提取题目文字 + 侦察附件数据 + 论文规则。Prompt: [`prompts/step1-extraction.md`](prompts/step1-extraction.md)。主 agent **不解读、不润色**提纯结果，直接传给 Step 2。

**Step 2: 并行审题（每道题一个 Agent）** — 输入 Step 1 原始输出。Prompt: [`prompts/step2-analysis.md`](prompts/step2-analysis.md)。`dataSufficiency` 必须基于数据画像**实际内容**判断，不能基于题目文字猜测。

**Step 3: 选题推荐（1 个 Agent）** — 所有审题结果喂给选题 agent。Prompt: [`prompts/step3-selection.md`](prompts/step3-selection.md)。

**Step 4: 等用户选择** — 列出利弊、子问题数量和复杂度。**停在这里，等用户选择。**

**Step 5: 落盘 Stage 1 产物（文档即共享的唯一权威）** — 用户选定后、发起 workflow 前，把该题的 Stage 1 产物写入 `<outputDir>/intermediates/00-problem.json`（`intermediates` 目录需先 `mkdir -p`）。文件结构：

```json
{
  "selectedProblem": "A",
  "problem": {
    "id": "A",
    "description": "<Step 1 \"=== 题目原文 ===\" 机械提取>",
    "dataProfile": "<Step 1 \"=== 附件清单 ===\" + \"=== 附件数据画像 ===\">",
    "paperRules": "<Step 1 \"=== 论文规则 ===\">",
    "analysis": "<Step 2 完整 JSON>"
  },
  "attachments": ["<Step 1 附件清单中的绝对路径>"]
}
```

> **分工**：workflow 启动时优先 `Read` 这个文件作为 Stage 1 产物（文档即共享）。**即使本步失败或忘记，workflow 也会从 args.problem 补写该文件（`ensure-stage1-doc` 机制兜底）——文件最终一定存在**。本步的价值是**预先落盘**：让你（或用户）在 workflow 启动前就能审查/修正 Stage 1 产物（此时文件是权威），而不是依赖 workflow 的补写。**必须真实写入并 `ls` 确认存在**；忘写不致命，但会失去"启动前可审查"的价值。

## 阶段二：执行 Workflow（DSH 版）

用户选定后，**必须用 `workflow` 工具**执行 Phase 3~8。**禁止手动编排 agent**——Workflow 脚本包含收敛控制、评审⇄修订 loop、趋势退出、数字溯源，手动跑会丢失。

DSH 的 `workflow` 工具参数为 `meta`（身份数据）+ `script`（纯 JS 脚本正文，**不含** `export const meta`）+ `args`（JSON 对象）：

- **script**：用 `read` 读取本 skill 目录下 `workflows/math-model.js` 的**完整正文**（约 3700 行，`read` 默认 limit 2000，需**分三次**：`offset 1`、`offset 2001`、`offset 3001`）。**注意**：文件开头含 `export const meta = {...}` 块（约第 5~19 行，供 Claude Code 安装直接使用）——DSH 运行时**跳过该块**（从 `export const meta = {` 到其闭合的 `}`），只把其余正文作为 `script` 传入
- **meta**：读取 `workflows/meta.json`（含 `name`/`description`/`whenToUse`/`phases`）作为 `meta` 传入
- **args**：

```json
{
  "selectedProblem": "A",
  "competition": "cumcm",
  "mode": "full",
  "templateDir": "<本 skill 的 templates 目录绝对路径>",
  "problem": {
    "id": "A",
    "description": "<Step 1 \"=== 题目原文 ===\" 机械提取>",
    "dataProfile": "<Step 1 \"=== 附件清单 ===\" + \"=== 附件数据画像 ===\">",
    "paperRules": "<Step 1 \"=== 论文规则 ===\">",
    "analysis": "<Step 2 完整 JSON>"
  },
  "outputDir": "./math-model-output",
  "attachments": ["<从 Step 1 附件清单逐行复制的绝对路径>"]
}
```

参数要点：
- `competition`：`"cumcm"`（国赛，默认）或 `"mcm"`（美赛——英文写作、Summary Sheet、letterpaper 版式、APA 风格引用）
- `mode`：`"full"`（默认，评审/求解/写作完整迭代）或 `"quick"`（评审 1 轮、求解 dry=1、写作 1 轮，约 30~40 个子 agent，适合赶时间或初步验证）
- `templateDir`：本 skill 的 `templates/` 目录绝对路径；不传则编译 agent 自动探测
- `problem.description/dataProfile/paperRules/analysis`：从 Step 1/Step 2 结果机械提取，不解读内容。**workflow 优先读 `<outputDir>/intermediates/00-problem.json`（Step 5 落盘），此字段仅作 fallback**——但建议仍传入（与落盘内容一致），保证任何情况可用
- `attachments`：从 Step 1 附件清单逐行复制绝对路径，**不做任何路径拼接或改写**。传参前逐文件验证：`for f in <路径1> <路径2>; do test -f "$f" || echo "MISSING: $f"; done`
- `outputDir`：**必须与 Step 5 落盘的 outputDir 一致**（00-problem.json 就在它的 intermediates/ 下）

**运行预期（务必转告用户）：**
- **耗时 30 分钟 ~ 10 小时不等**，主要看建模评审 loop 与代码求解的时间复杂度，full 模式以小时计
- Workflow 在前台运行，父级轮次阻塞到结算——**期间不要打断、不要刷新页面**；结束后返回结果
- **脚本全文（约 5 万 token）会注入主 agent 历史并随每次请求重放**，这是固定编排开销
- **中途中断**：checkpoint 保证已完成的 phase 落盘；恢复时在 args 加 `resumeFrom: "<已完成的最新 phase 名>"`（如 `"phase4-modeling"`）跳过已完成阶段（也可配合 `skipPhases`）
- **可选拆段运行**：把大 workflow 拆成多次调用（每段 `resumeFrom` 衔接），每段阻塞 5~15 分钟，段间可检查 `outputDir/intermediates/` 并人工干预；代价是每段都要重新传脚本

## 阶段三：汇报 + 阶段二失败备用

Workflow 返回后汇报：建模概要+创新、baseline 对比、迭代轮数、PDF 路径、**代码-论文数字对账**（运行最终代码，逐数字对比 stdout；重点：R²、窗口函数、零填充、AIC、不确定度）。

若 Workflow 失败但核心产出已生成，手动兜底：摘要数字溯源→逐问标注检查→拼接 LaTeX（`intermediates/05-writing/section-*.json`，清理内部引用）→`xelatex` 两遍。**此时按 `docs/writing-and-format.md` 的"论文模板要点/组装方式/内部规范"操作**——这部分内容只在失败手动兜底/审查产物时才需要，平时不用读。

## 结果解读（workflow 返回的三个层面）

Workflow 返回 `{ metadata, details, stats, ... }`，用这三个层面给用户汇报：

- **metadata**：`approach`（方案概要）、`iterations`（求解迭代轮数）、`totalIssues/criticalIssues`（验证发现问题数）、`sections`（章节数）、`baselineComparison`（创新 vs 标准基线）
- **stats**：`problemsAnalyzed`、`sourcesFetched`、`modelsReferenced`、`solveIterations`、`issuesFound`、`sectionsWritten`
- **details**：`analyses/selection/finalModel/solution/limitationAnalysis/baselineResult/narrativeOutline/crossSectionReview/judgeReview`（如 JSON 片段太大，汇报关键字段即可）

常见"非报错但你要解释给用户的信号"：
- **预留**：模型适配性预检 `STOP` → workflow 直接返回 error（提示换方向/放宽严格度），非 bug
- **求解未收敛退出**（趋势恶化）→ 结果仍可用，但更保守（汇报时说明）
- **摘要数字修复** → phase8 会删/替换不可溯源数字，最终 PDF 数字安全
- **checkpoint 跳过/写盘告警** → 该 phase 断点续跑需重跑，非内容问题

完整错误规范、写作/图表/格式/模板要求、内部 Common Mistakes 全部在 **`docs/writing-and-format.md`**。

## 输出目录结构

```
outputDir/
├── paper/          # paper.tex + paper.pdf
├── code/           # solution_v*.py
├── figures/        # fig_v*_*.png（求解）+ fig_eda_*.png（EDA，数据题）
├── data/           # sip_v*_*.csv/json + external/（自行收集的外部数据，需查数据的题）
├── logs/           # solution_v*.log + MODEL_RETHINK_ALERT.txt
└── intermediates/  # 00-problem(题面/画像/规则真源), 03-search, 04-data-needs, 04-data-collection, 04-problem-analysis, 04-eda-report, 05-writing, 06-robustness-report, 06-final, ...
```

## 注意事项

- PDF 用 `pdftotext`，不用 `read` 工具；阶段一等确认，阶段二不打断
- Workflow 内 agent 失败 → 降级继续；**不要编辑 `workflow` 脚本**（脚本内容以文件为准，DSH 运行不吃 SKILL.md；改了脚本要同步 docs/writing-and-format.md）
- 各 phase 中间产物存 `outputDir/intermediates/`；摘要数字需正文出处
- **文档即共享**：各 phase 落盘的中间文档（`04-problem-analysis` / `04-eda-report` / `06-robustness-report` / `07-fact-sheet`、写作的 `05-writing/section-*.json`）是下游环节的**唯一权威真源**——下游 agent **必须 `Read` 这些文档**拿完整内容，prompt 不再注入摘要备份。落盘须成功并确认（`SAVE_FAILED` 标记即缺失）
- 阶段一大量使用并行 sub-agent 编排（DSH subagent 工具支持后台并行）；主 agent 只编排、不读题
