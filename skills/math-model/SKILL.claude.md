---
name: math-model
description: 当用户需要完成数学建模竞赛（国赛CUMCM/美赛MCM）的完整或部分流程时使用。触发词：/math-model、数模、数学建模、国赛、美赛、建模比赛。症状：审题无从下手、数据画像缺失、求解验证脱节、摘要数字无出处、论文格式不合规。
---

# 数学建模工作流

## Overview

架构师，不是做题家。国一核心：**正确性第一 + 数据说话**，摘要一锤定音。两阶段：一审题选题，二 Workflow 全自动执行。

**触发：** `/math-model`、数模、数学建模、国赛、美赛、建模比赛。不适用纯数学推导或无竞赛格式要求的普通问题。

## 你能做什么 / 不能做什么

| 阶段 | 你（主 agent）的角色 | 说明 |
|------|------|------|
| 阶段一 审题+选题 | **可干预**：并行提纯→审题→选题→等用户选 | 你只编排，机械透传原文/数据，不解读不润色 |
| 阶段二 执行 Workflow（phase3-8） | **不干预**：用 Workflow 工具发起 | 内部 agent 全由脚本编排，行为规范硬编码在 `workflows/math-model.js` |
| 阶段三 汇报+兜底 | **可干预**：汇报、必要时手动兜底 | 见下 |

> **关键**：阶段二 Workflow 运行时你**看不到也管不了**内部 agent。内部执行规范在 `docs/writing-and-format.md`（你仅在**失败手动兜底**或**审查产物**时参考）。

## 阶段一：审题 + 选题

**Step 1: 输入提纯（每道题一个 Agent，并行）** — 提取题目文字 + 侦察附件数据 + 论文规则。Prompt: [`prompts/step1-extraction.md`](prompts/step1-extraction.md)。主 agent **不解读、不润色**提纯结果，直接传给 Step 2。

**Step 2: 并行审题（每道题一个 Agent）** — 输入 Step 1 原始输出。Prompt: [`prompts/step2-analysis.md`](prompts/step2-analysis.md)。`dataSufficiency` 必须基于数据画像**实际内容**判断。

**Step 3: 选题推荐（1 个 Agent）** — 所有审题结果喂给选题 agent。Prompt: [`prompts/step3-selection.md`](prompts/step3-selection.md)。

**Step 4: 等用户选择** — 列出利弊、子问题数量和复杂度。**停在这里，等用户选择。**

**Step 5: 落盘 Stage 1 产物（文档即共享的唯一权威）** — 用户选定后、发起 workflow 前，把该题的 Stage 1 产物写入 `<outputDir>/intermediates/00-problem.json`（`intermediates` 目录需先 `mkdir -p`）。结构：

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

## 阶段二：执行 Workflow

用户选定后，**必须用 Workflow 工具**执行 Phase 3~8。**禁止手动编排 agent**——Workflow 脚本包含收敛控制、评审⇄修订 loop、趋势退出、数字溯源，手动跑会丢失。

```js
Workflow({
  scriptPath: '/home/tofu/.claude/workflows/math-model.js',
  args: {
    selectedProblem: 'A',
    problem: {
      id: 'A',
      description: '<Step 1 "=== 题目原文 ===" 机械提取>',
      dataProfile: '<Step 1 "=== 附件清单 ===" + "=== 附件数据画像 ===">',
      paperRules: '<Step 1 "=== 论文规则 ===">',
      analysis: '<Step 2 完整 JSON>',
    },
    outputDir: './math-model-output',
    attachments: ['<从 Step 1 附件清单逐行复制的绝对路径>'],
  }
})
```

参数要点：
- `problem.description/dataProfile/paperRules/analysis`：从 Step 1/Step 2 结果机械提取，不读内容直接粘贴。**workflow 优先读 `<outputDir>/intermediates/00-problem.json`（Step 5 落盘），此字段仅作 fallback**——建议仍传入（与落盘一致）
- `attachments`：从 Step 1 附件清单逐行复制绝对路径，**不做任何路径拼接或改写**。传参前逐文件验证：`for f in <路径1> <路径2>; do test -f "$f" || echo "MISSING: $f"; done`
- `outputDir`：**必须与 Step 5 落盘的 outputDir 一致**（00-problem.json 就在它的 intermediates/ 下）
- Workflow 跑在前台/后台，不要打断；结束后返回结果。若中断，用 `resumeFrom`（如 `"phase4-modeling"`）跳过已完成 phase 续跑；`mode` 支持 `quick`（约 30~40 子 agent）与 `full`（默认）

## 阶段三：汇报 + 阶段二失败备用

Workflow 返回后汇报：建模概要+创新、baseline 对比、迭代轮数、PDF 路径、**代码-论文数字对账**（运行最终代码，逐数字对比 stdout；重点：R²、窗口函数、零填充、AIC、不确定度）。

若 Workflow 失败但核心产出已生成，手动兜底：摘要数字溯源→逐问标注检查→拼接 LaTeX（`intermediates/05-writing/section-*.json`，清理内部引用）→`xelatex` 两遍。**此时按 `docs/writing-and-format.md` 的"论文模板要点/组装方式/内部规范"操作**。

## 结果解读（workflow 返回的三个层面）

- **metadata**：`approach`（方案概要）、`iterations`（求解轮数）、`totalIssues/criticalIssues`（验证发现问题数）、`sections`（章节数）、`baselineComparison`（创新 vs 基线）
- **stats**：`problemsAnalyzed`、`sourcesFetched`、`modelsReferenced`、`solveIterations`、`issuesFound`、`sectionsWritten`
- **details**：`analyses/selection/finalModel/solution/limitationAnalysis/baselineResult/narrativeOutline/crossSectionReview/judgeReview`

常见"非报错但要解释"的信号：**适配性预检 STOP**（返回 error，提示换方向）、**求解未收敛退出**（结果可用但保守）、**摘要数字修复**（phase8 自动删/替换不可溯源数字）、**checkpoint 跳过**（该 phase 续跑需重跑）。完整内部规范在 `docs/writing-and-format.md`。

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

- PDF 用 pdftotext，不用 Read；阶段一等确认，阶段二不打断
- Workflow 内 agent 失败 → 降级继续；**不要编辑 `workflow` 脚本**（Claude 版从 `scriptPath` 加载，改文件才生效）
- 各 phase 中间产物存 `outputDir/intermediates/`；摘要数字需正文出处
- **文档即共享**：各 phase 落盘的中间文档是下游环节的**唯一权威真源**——下游 agent **必须 `Read` 这些文档**拿完整内容，prompt 不再注入摘要备份。落盘须成功并确认（`SAVE_FAILED` 标记即缺失）
- **REQUIRED BACKGROUND:** You MUST understand `superpowers:dispatching-parallel-agents` —— 阶段一大量使用并行 sub-agent 编排
