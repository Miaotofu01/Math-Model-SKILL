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
| 阶段二 执行 Workflow（13 阶段） | **不干预**：用 Workflow 工具发起 | 内部 agent 全由脚本编排；调度壳只做路由/门禁/收敛，业务规范在 `prompts/phase-*.md` 与 `docs/writing-and-format.md` |
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

> **强制（新架构无兜底）**：`intermediates/00-problem.json` 是小问列表与题面的**唯一来源**——壳启动只读它（`args.problem` 不再作为 fallback 被读取）。**必须真实写入并 `ls` 确认存在**；缺失则 workflow 直接返回 error（`未找到 <outputDir>/intermediates/00-problem.json`），不会自动补写。本步的价值：让你（或用户）在 workflow 启动前就能审查/修正 Stage 1 产物（此时文件是权威）。壳取 `analysis.subQuestions` 的 id 数组作为小问列表（缺失时按 1 个小问 q1 处理）。

## 阶段二：执行 Workflow（Claude 版）

用户选定后，**必须用 Workflow 工具**执行 13 阶段工作流（薄壳）。**禁止手动编排 agent**——调度壳包含门禁/失败收敛/评审⇄修订 loop，手动跑会丢失。

```js
Workflow({
  scriptPath: '/home/tofu/.claude/workflows/math-model.js',
  args: {
    outputDir: './math-model-output',
    templateDir: '<本 skill 根目录或 templates/ 目录的绝对路径>',
    mode: 'full',
    innovationStrictness: 'strict',
    resume: false,
  }
})
```

参数要点：
- `outputDir`：**必须与 Step 5 落盘的 outputDir 一致**（00-problem.json 就在它的 intermediates/ 下）
- `templateDir`：本 skill 根目录或 `templates/` 目录的绝对路径；壳据此定位 `prompts/`（传 `templates/` 时自动去掉尾缀）；不传则用默认 `skills/math-model/prompts`
- `mode`：`"full"`（默认）或 `"quick"`（评审最多 2 轮，适合赶时间或初步验证）
- `innovationStrictness`：`"strict"`（默认）／`"standard"`／`"loose"`
- `resume`：`true` 时按 `intermediates/state.json` 的 problemId 匹配续跑（gates 为 PASS/PASS_WITH_WARNING/SKIPPED 的阶段自动跳过；匹配不上则全新开始）；默认 `false`
- `problem`：壳不再读取（无兜底）——小问列表唯一来源是 Step 5 落盘的 `intermediates/00-problem.json`

> ⚠️ **仓库外脚本同步是合并后部署步骤**：本 skill 的仓库内脚本是 `skills/math-model/workflows/math-model.js`（约 10KB 薄壳，业务逻辑全在 `prompts/` 与 `docs/`），`scriptPath` 指向的 `~/.claude/workflows/math-model.js` 是仓库外副本——**合并后需把新薄壳同步到 `~/.claude/workflows/`**，否则 Claude 版会加载旧脚本。

**运行预期（务必转告用户）：**
- **耗时 30 分钟 ~ 10 小时不等**，主要看建模评审 loop 与代码求解的时间复杂度，full 模式以小时计
- Workflow 跑在前台，不要打断；结束后返回结果
- **薄壳脚本约 10KB**（旧 244KB 的 1/24）：`scriptPath` 引用文件，无内联体积问题；业务逻辑全在磁盘（`prompts/` 模板 + `docs/` 规范），子代理自行 Read
- **逐问串行**：每小问跑 10 个 per-question 阶段（文献调研→数据探索→假设定义→公式化→实现→计算→Sanity→可视化→鲁棒性→小问完成），全部小问完成后跑 3 个 run-level 阶段（跨问复核→写作→终审）
- **公式化子流程**（壳内独立编排）：formulator 产出方案 + baseline 预注册 → 三维自查 → 3 视角评审（judge/adversary/application，并行）⇄ 修订——full 最多 3 轮 / quick 最多 2 轮，评审全 PASS（无必须改）即收束
- **中途中断**：已完成的阶段由 `intermediates/state.json` 记录（门禁/产物/位置）；恢复时 args 加 `resume: true`，壳按 state.json 的 problemId 匹配续跑（不再有 `resumeFrom`/`skipPhases` 机制）
- **门禁边界**：3 处——求解前（该问 04-formulation PASS）、写作前（所有小问 localComplete 且跨问复核 PASS）、终审前（writing 产物完整）；门禁 FAIL 时整体返回 blocked（含 detail），修正后 `resume: true` 续跑
- **失败收敛**：阶段连续 2 次失败 → 降级 SKIPPED（整体 status=degraded）；公式化未收敛（full max3 轮 / quick max2 轮）→ blocked

## 阶段三：汇报 + 阶段二失败备用

Workflow 返回后汇报：状态与各阶段产物摘要（artifactSummary）、最近 ledger 行（ledgerTail）、state 路径、PDF 路径、**代码-论文数字对账**（运行最终代码，逐数字对比 stdout；重点：R²、窗口函数、零填充、AIC、不确定度）。

若 Workflow 失败但核心产出已生成，手动兜底：摘要数字溯源→逐问标注检查→把 `intermediates/12-writing/paper-sections/section-*.md` 转成组装脚本读取的 `section-*.json`（首行 `# 章节名` → section，其余 → content；存 `13-final/sections-json/`，不改 12-writing 原产物）→`templates/assemble_from_template.py` 组装→`xelatex` 两遍。**此时按 `docs/writing-and-format.md` 的"论文模板要点/组装方式/内部规范"操作**。

## 结果解读（workflow 返回）

Workflow 返回 `{ status, statePath, artifactSummary, ledgerTail, blocked? }`：

- **status**：`"ok"`（全部阶段完成）／`"degraded"`（仅**显式可选**阶段 SKIPPED 时产出可用结果，如鲁棒性不适用；**实质阶段** 2 次失败降级后会被下游门禁拦下 → 最终 blocked，非"仍可用"）／`"blocked"`（门禁未过或公式化未收敛）／`"error"`（启动错误：缺 00-problem.json 或契约读不到）
- **statePath**：`<outputDir>/intermediates/state.json`（中断恢复依据）
- **artifactSummary**：各阶段状态与产物路径摘要（如 `q1.literature[PASS] intermediates/q1/01-literature/literature.md`，`；` 分隔）
- **ledgerTail**：`intermediates/ledger.md` 最近 10 行（决策日志）
- **blocked**：`status="blocked"` 时的阻塞详情 `{gate, key, detail}`

常见"非报错但你要解释给用户的信号"：**blocked（门禁）**——求解前/写作前/终审前门禁 FAIL 或公式化未收敛，按 `blocked.detail` 修正后 `resume: true` 续跑；**degraded**——仅显式可选阶段降级 SKIPPED（如鲁棒性不适用）时结果可用、汇报时说明；实质阶段 2 次失败降级后 localComplete 产物核验 FAIL → write-start 门禁 FAIL → 整体 blocked（不是"仍可用但保守"）；**error**——`00-problem.json` 缺失或契约读不到，补 Step 5 落盘后重跑。完整内部规范在 `docs/writing-and-format.md`。

## 输出目录结构

```
outputDir/
└── intermediates/              # 全部中间产物（壳只路由，不搬运内容）
    ├── 00-problem.json         # Stage 1 落盘：题面/数据画像/论文规则/审题JSON/附件清单（小问列表唯一来源）
    ├── state.json              # 状态契约：current/gates/iterations/artifacts/deps（中断恢复 + 审计）
    ├── ledger.md               # 追加式决策日志（每节点一行）
    ├── pool/                   # 共享池：literature-pool.md（文献池）、external-data/（外部数据）
    ├── q1/                     # 每小问独立目录（串行天然隔离）——10 个 per-question 阶段产物
    │   ├── 01-literature/literature.md            # 文献调研（含引用登记）
    │   ├── 02-data/eda.md + data-collection.json  # 数据探索（外部数据来源记录）
    │   ├── 03-assumptions/assumption-vNN.md       # 假设定义（版本不可覆盖）
    │   ├── 04-formulation/                        # 公式化：draft.md + baseline-registry.md
    │   │                                          #   + symbols.json + self-check.md + review-r*.md
    │   ├── 05-implementation/code/                # 实现（可运行代码）
    │   ├── 06-computation/results.json            # 计算（含 baseline 同场对比）
    │   ├── 07-sanity/sanity-report.md             # Sanity 数值门禁
    │   ├── 08-visualization/figure-manifest.md + figures/   # 可视化（示意图另有同名 .html 源文件）
    │   ├── 09-robustness/robustness.md            # 鲁棒性（显式可选）
    │   └── 10-completed/question-summary.md       # 小问完成（定稿事实链）
    ├── q2/ … qn/               # 其余小问，逐问串行
    ├── 11-cross-review/cross-question-report.md   # 跨问复核（run-level）
    ├── 12-writing/paper-sections/section-*.md     # 写作（run-level；另有 fact-sheet.md / narrative-outline.md / cross-review-r*.md）
    └── 13-final/               # 终审（run-level）：final-paper.tex / final-paper.pdf / compile.log
                                #   + abstract-trace.md / judge-self-review.md / sections-json/
```

> 说明：EDA 图存 `outputDir/figures/`（`fig_eda_*`）；求解/示意图在 `q{id}/08-visualization/figures/`；写作阶段按 figure-manifest 反向校验图文件真实存在（空 figure 是 P0 事故，详见 docs §二）。

## 注意事项

- PDF 用 pdftotext，不用 Read；阶段一等确认，阶段二不打断
- Workflow 内 agent 失败 → 降级继续；**不要编辑 `workflow` 脚本**（薄壳只做路由/门禁/收敛，业务逻辑在 `prompts/phase-*.md` 与 `docs/writing-and-format.md`——改这些才生效；Claude 版从 `scriptPath` 加载，改仓库内文件后需同步到 `~/.claude/workflows/`）
- **中断恢复**：args 加 `resume: true`，壳按 `intermediates/state.json` 的 problemId 匹配续跑（gates∈{PASS, PASS_WITH_WARNING, SKIPPED} 自动跳过）；已无 `resumeFrom`/`skipPhases` 机制
- **3 处门禁边界**：求解前（`q{id}.solve-start`：该问 04-formulation PASS）／写作前（`write-start`：所有小问 localComplete 且跨问复核 PASS）／终审前（`final-start`：writing 产物完整）；门禁 FAIL → 整体 blocked（含 detail），修正后 resume 续跑
- **公式化子流程**：formulator → 三维自查 → 3 视角评审（judge/adversary/application，并行）⇄ 修订（full max3 轮 / quick max2 轮），评审全 PASS 即收束；未收敛 → blocked
- 各阶段中间产物存 `outputDir/intermediates/`；摘要数字需正文出处（终审硬门禁：任一数字无法溯源 → FAIL）
- **示意图依赖 diagram-design skill**（`~/.dsh/skills/diagram-design`）：可视化/写作阶段优先用它画示意图（HTML→PNG，配方 `docs/flowchart-drawing.md`）；skill 缺失自动回退 matplotlib，不阻断
- **文档即共享**：各阶段落盘的中间文档（各问 `question-summary.md` / `results.json` / `robustness.md`、写作的 `fact-sheet.md` 等）是下游环节的**唯一权威真源**——下游 agent **必须 `Read` 这些文档**拿完整内容，prompt 不再注入摘要备份。落盘须成功并确认（缺失即 FAIL/阻塞）
- **REQUIRED BACKGROUND:** You MUST understand `superpowers:dispatching-parallel-agents` —— 阶段一大量使用并行 sub-agent 编排
