---
name: math-model
description: 当用户需要完成数学建模竞赛（国赛CUMCM/美赛MCM）的完整或部分流程时使用。触发词：/math-model、数模、数学建模、国赛、美赛、建模比赛。症状：审题无从下手、数据画像缺失、求解验证脱节、摘要数字无出处、论文格式不合规。
---

# 数学建模工作流

## Overview

架构师，不是做题家。国一核心：**正确性第一 + 数据说话**，创新有根有据、摘要一锤定音。两阶段：一审题选题（主 agent 只编排不读题），二 Workflow 全自动执行。

**触发：** `/math-model`、数模、数学建模、国赛、美赛、建模比赛。不适用纯数学推导或无竞赛格式要求的普通问题。

## Quick Reference

| Phase | 内容 | 关键机制 |
|-------|------|----------|
| 1-2. 审题+选题 | 并行提取原文→审题→选题推荐→等用户确认 | 主 agent 不读题，只做编排 |
| 3. 文献调研 | 多角度搜索→精读→提取模型/claim→局限分析 | 为创新提供合法来源 |
| 4. 建模方案 | Gap分析→多角度创新提案→评委评审⇄修订(max 6轮)→适配性预检 | 低于阈值打回重设计 |
| 5⇄6. 求解⇄验证 | 算法→实现→baseline对比→验证(5维度)→投票→反思checkpoint | 趋势退出+dry收敛；根基问题自动回溯 |
| 7. 写作 | 事实源表→叙事大纲→顺序主编撰写→交叉审查统一修复(max 3轮 dry=2) | 质量门：章节/排序/溯源/图表/P0；全篇数字以事实源表为唯一权威 |
| 8. 终审 | 摘要数字溯源→验证→(LaTeX编译)→评委自评 | 摘要定生死；每个数字需正文出处 |

## Core Pattern

**架构原则：主 agent 不读题、不读数据、不跑命令——只分派 sub-agent、传递结果、汇总呈现。** 每道题的输入由一个 sub-agent 提纯，主 agent 没有机会"润色"原文。

阶段一（主 agent 编排）：Step 1 并行提纯 → Step 2 并行审题 → Step 3 选题推荐 → Step 4 等用户选择。
阶段二（Workflow 全自动）：Phase 3-8 文献→建模→求解⇄验证→写作→终审，收敛控制+趋势退出+数字溯源全部内置。

## Implementation

### 阶段一：审题 + 选题

**Step 1: 输入提纯（每道题一个 Agent，并行）** — 提取题目文字 + 侦察附件数据 + 论文规则。Prompt: [`prompts/step1-extraction.md`](prompts/step1-extraction.md)。主 agent **不读**提纯结果，直接传给 Step 2。

**Step 2: 并行审题（每道题一个 Agent）** — 输入 Step 1 原始输出。Prompt: [`prompts/step2-analysis.md`](prompts/step2-analysis.md)。`dataSufficiency` 必须基于数据画像**实际内容**判断，不能基于题目文字猜测。

**Step 3: 选题推荐（1 个 Agent）** — 所有审题结果喂给选题 agent。Prompt: [`prompts/step3-selection.md`](prompts/step3-selection.md)。

**Step 4: 等用户选择** — 列出利弊、子问题数量和复杂度。**停在这里，等用户选择。**

### 阶段二：执行 Workflow

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
- `problem.description`：从 Step 1 `=== 题目原文 ===` 标记段机械提取，不读内容直接粘贴
- `problem.dataProfile`：从 Step 1 `=== 附件清单 ===` + `=== 附件数据画像 ===` 提取，无附件则 `"无附件"`
- `problem.paperRules`：从 Step 1 `=== 论文规则 ===` 提取，无则 `"无单独论文规则"`
- `problem.analysis`：Step 2 完整 JSON（含 `subQuestions` 数组——后续所有 phase 从该数组获取子问题列表）
- `attachments`：从 Step 1 附件清单逐行复制绝对路径，**不做任何路径拼接或改写**（路径含空格保持原样）。传参前逐文件验证：`for f in <路径1> <路径2>; do test -f "$f" || echo "MISSING: $f"; done`
- Workflow 跑在后台，不要打断；结束后返回结果

### 阶段三：汇报 + 阶段二失败备用

Workflow 返回后汇报：建模概要+创新、baseline 对比、迭代轮数、PDF 路径、**代码-论文数字对账**（运行最终代码，逐数字对比 stdout；重点：R²、窗口函数、零填充、AIC、不确定度）。

若 Workflow 失败但核心产出已生成，手动：摘要数字溯源→逐问标注检查→拼接 LaTeX（`intermediates/05-writing/section-*.json`，清理内部引用）→`xelatex` 两遍。

## Common Mistakes

### 致命级

| 失败模式 | 症状 | 防护 |
|----------|------|------|
| 内容缺失/结构倒置 | 章节少、空白、"结论"在第1节 | Phase 7 质量门 |
| 摘要数字编造 | 声称结果正文无推导 | Phase 8 数字溯源 |
| 数据流断裂 | 重设计/评审未进入写作上下文 | allContext 优先级截断 |
| 交叉审查P0未修 | 符号不一致(Λ=60.6 vs 74.61) | Phase 7 loop 逐轮验证 |
| 逐问标注缺失 | 章节按方法论而非子问题组织 | 写作 prompt 要求"对于问题N" |
| 代码-论文数字矛盾 | 摘要 Hann 窗/代码 Blackman 窗 | 阶段三代码对账 |
| 摘要未按子问题分段 | 评委找不到每个子问题解答 | 摘要 prompt 结构化分段 |
| 加粗过度 | 大段加粗分不清重点 | 只加粗答案关键词+数值 |
| 图表CJK字体缺失 | 中文标签渲染为方框 | Noto Sans CJK SC；中文测试字体 |

### 严重级

| 失败模式 | 症状 | 防护 |
|----------|------|------|
| 求解loop不收敛 | dry 永远=0 | 趋势退出：新问题数连续2轮超上轮1.1×→退出 |
| 模型全是FLAW | 11/11 次反思 FUNDAMENTAL_FLAW | Phase 4.5 预检打回 |
| 图表未引用 | 生成图但论文没用 | Phase 7 图表引用检查 |
| 创新矩阵闲置 | innovationMatrix 未喂给写作 | allContext 含 innovationMatrix |
| 标签式强调 | 「创新点：」等使论文像技术报告 | 禁止标签；创新自然融入描述 |
| 图表Unicode上下标 | `cm⁻¹` 渲染方框 | LaTeX math: `cm$^{-1}$` |
| 附录浮动体堆积 | 图片消失/堆积末尾 | 附录 `[H]`，正文 `[htbp]` |

## 论文写作规范

1. **摘要按子问题分段**：「对于问题1，…对于问题2，…」每个子问题方法+核心结果（`$\bm{...}$` 加粗）。末段总结。末尾 `\textbf{关键词：}...`。
2. **加粗只加答案**：只加粗答案关键词和核心数值，不加粗整句叙述。
3. **禁止标签式强调**：不得使用「创新点：」「关键发现：」等标签。
4. **问题重述必须有**：摘要后 `\section{问题重述}`，按问题逐一列出。
5. **结论逐问总结**：`{\bfseries 对于问题N——标题：}` 格式，每个子问题一段。
6. **清理 Agent 笔记**：最终 paper.tex 不得出现调试笔记。

## 图表生成规范

1. **CJK 字体**：`font.sans-serif = ['Noto Sans CJK SC', 'DejaVu Sans']` + `font.family = 'sans-serif'` + `axes.unicode_minus = False`。测试用中文文本。
2. **LaTeX math 单位**：`cm$^{-1}$`、`A$_2$/A$_1$`，禁止 Unicode 上下标。
3. **mathtext 启用**：`mathtext.default = 'regular'`。
4. **附录浮动体 `[H]`**：附录图表用 `[H]`（`\usepackage{float}`），正文用 `[htbp]`。
5. **验证**：检查无 `Glyph.*missing from font` 警告。

## CUMCM 格式

- 摘要专用页，**禁止 `\maketitle`**；正文从下页开始，**禁止目录**，≤20页
- A4/2.5cm 页边距，页码从摘要页阿拉伯数字连续编号，页脚中部
- 附录含支撑材料列表 + 全部可运行源代码（缺失可能取消评奖资格）
- 任何地方不得有参赛者身份/学校/赛区信息；引用按科技论文规范

## 论文模板（2026-08 实战经验固化）

**模板文件：** `templates/cumcm-paper.tex` + `templates/assemble_from_template.py`（skill 自带）

**模板要点（踩坑教训固化）：**
1. **摘要用 `\section*{摘 要}`**（章节式标题、无编号）——**禁止用 `abstract` 环境**（环境自动标题与章节标题重复 = "双摘要"事故）
2. **章节标题居中**：article+ctex 组合用 titlesec（`\ctexset` 在该组合下无效，ctexart 类才可用）
3. **参考文献**：thebibliography 环境**自带"参考文献"标题**——前面不要再加 `\section*{参考文献}`（"参考文献双标题"事故）
4. **附录用 `\appendix` + 全部计数器独立**：附录节自动编号 A/B/C，且表/图/公式编号也独立（`\setcounter{table}{0}` 等重置 + `\renewcommand{\thetable}{\Alph{section}.\arabic{table}}`，显示为 B.1/B.2——注意计数器须置 0 而非 1，`\caption` 会先 step 再显示）；附录图表用 `[H]`，正文用 `[htbp]`
5. **代码附录**：`\lstinputlisting[style=pythonstyle]` 彩色高亮直接引用 code/ 文件；代码文件必须清理身份信息（校名/绝对路径→`~`展开）和 Unicode 数学符号（θ→theta 等，缺失字符渲染为空白）
6. **关键答案加粗**：摘要/正文关键数值用 `$\bm{...}$`（需 `\usepackage{bm}`）；只加粗答案，不加粗整句
7. **支撑材料清单为真实交付物模板**（非占位式："共若干张"类表述会被合规审查抓为 P2）
8. **名单表 caption 中下划线必须转义**（`数据1_Q1` → `数据1\_Q1`，否则 "Missing $ inserted"）

**组装方式：** `python3 templates/assemble_from_template.py --template templates/cumcm-paper.tex --sections <sections目录> --output paper/paper.tex [--references ...] [--suspect-json ...] [--code-dir ...] [--materials ...]`
占位符：`@TITLE@/@PAPER_TITLE@/@SUBTITLE@/@ABSTRACT@/@BODY@/@REFERENCES@/@MATERIALS@/@SUSPECT_LISTS@/@CODE_ENTRIES@`；模板头部注释中的说明文字**不得含 @ 包裹的占位符**（replace 会污染注释区）。

## 创新链条

文献局限分析 → Gap分析 → 多角度方案提案 → 评委评审⇄修订loop → 模型适配性预检 → baseline对比(量化证明) → 求解验证(趋势收敛) → 创新追溯矩阵 → 叙事大纲 → 交叉审查⇄修复loop → 终审。**每步喂给下一步，创新贯穿始终而非 Phase 7 硬贴。**

## 输出目录结构

```
outputDir/
├── paper/          # paper.tex + paper.pdf
├── code/           # solution_v*.py
├── figures/        # fig_v*_*.png
├── data/           # sip_v*_*.csv/json
├── logs/           # solution_v*.log + MODEL_RETHINK_ALERT.txt
└── intermediates/  # 03-search, 04-proposal, 05-writing, 06-final, ...
```

## 注意事项

- PDF 用 pdftotext，不用 Read；阶段一等确认，阶段二不打断
- Workflow 内 agent 失败 → 降级继续；**不要编辑 workflow 脚本**（缓存失效）
- 各 phase 中间产物存 `outputDir/intermediates/`；摘要数字需正文出处
- **REQUIRED BACKGROUND:** You MUST understand superpowers:dispatching-parallel-agents —— 阶段一大量使用并行 sub-agent 编排
