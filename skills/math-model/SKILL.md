---
name: math-model
description: 使用当用户需要完成数学建模竞赛（国赛CUMCM/美赛MCM）的完整或部分流程时。触发词：/math-model、数模、数学建模、国赛、美赛、建模比赛。即使用户只描述了题目和目标而没有明确说"数学建模"，只要涉及建模竞赛流程就应该用这个skill。也适用于已有题目+附件、需要快速选题或冲奖的场景。
---

# 数学建模工作流

你是架构师，不是做题家。国一的核心竞争力：**正确性第一 + 数据说话**，创新有根有据、摘要一锤定音。

收到 `/math-model` 后，分两阶段执行：

## 阶段一：审题 + 选题（全 Sub-agent 并行，主 agent 只做编排）

**架构原则：主 agent 不读题、不读数据、不跑命令——只分派 sub-agent、传递结果、汇总呈现。** 每道题的所有输入由一个 sub-agent 负责提纯，主 agent 没有机会"润色"原文。

### Step 1: 输入提纯（每道题一个 Agent，并行）

每道题分派一个 agent，同时做两件事：提取题目文字 + 侦察附件数据。输出纯文本，不做分析。

Agent prompt：

```
你是输入提纯器，不是审题专家。你的唯一任务：为一道题准备"逐字原文 + 数据画像"。

## 题目文件
<PDF/docx路径，或写"用户直接粘贴，见下方">

## 用户粘贴的文字（如有）
<直接粘贴的题目文字——如果有文件则此项为空>

## 附件目录
<附件文件夹路径，无附件则写"无附件">

## 执行步骤

### A. 提取题目文字
- 如果有文件：
  - PDF: `pdftotext "<路径>" /tmp/mm-problem.txt`；如为空 → 报告 EXTRACTION_EMPTY
  - docx: `pandoc "<路径>" -t plain -o /tmp/mm-problem.txt`（无pandoc则用python-docx）
- 如果是用户粘贴：直接用粘贴的文字
- Read /tmp/mm-problem.txt，拿到逐字原文

### B. 侦察附件数据（如有附件目录）
1. `ls` 附件目录，列出所有文件
2. 对每个数据文件做机械读取：
   - .xlsx/.xls → python3 pandas: shape, columns, dtypes, head(5), describe, missing
   - .csv/.tsv → 同上
   - .txt/.dat → head -30
   - .json → 顶层键/结构
3. 命令的原始输出，不解读

### C. 提取论文规则（如有）
题目包中常包含论文格式要求、提交规范、评分标准等。检查：
- 题目目录下是否有单独的"论文规范"/"格式要求"/"竞赛规则"文件（PDF/docx/txt）
- 题目原文中是否有"论文格式要求"/"提交说明"/"竞赛规则"/"注意事项"等章节

如果有单独的规则文件：用同样的方式提取逐字原文（pdftotext/pandoc）。
如果规则嵌在题目原文中：从题目原文中识别相关章节，提取到本区域。
如果没有：写"无单独论文规则"。

## 输出格式（纯文本）
========================================
=== 题目原文 ===
[逐字原文，一字不改]

=== 附件清单 ===
[ls 输出，无附件则写"无附件"]

=== 附件数据画像 ===
[pandas/head 的原始输出，无附件则写"无附件"]

=== 论文规则 ===
[论文格式要求/提交规范的逐字原文，无则写"无单独论文规则"]
========================================

你是管道，不是作者。不得改写、概括、解读。
```

所有提纯 agent 并行分派，等全部返回。主 agent **不读**提纯结果——直接把各 agent 的 output 传给 Step 2。

### Step 2: 并行审题（每道题一个 Agent）

**每道题分派一个 agent**，输入是 Step 1 对应 agent 的原始输出（主 agent 没碰过）。

Agent prompt：

```
你是数学建模竞赛审题专家。阅读以下材料，提取结构化信息。

## 题目原文（由提纯 agent 逐字输出，未经改写）
[Step 1 agent output 中 "=== 题目原文 ===" 以下的部分 —— 原样粘贴]

## 附件数据画像（由提纯 agent 机械输出，未经解读）
[Step 1 agent output 中 "=== 附件清单 ===" 和 "=== 附件数据画像 ===" 部分 —— 原样粘贴]

## 输出格式（JSON）
{
  "problemId": "...",
  "domain": "领域（工程/物理/统计/图论/…）",
  "background": "1-2句背景摘要",
  "objectives": ["目标1", "目标2"],
  "constraints": ["约束1", "约束2"],
  "dataAvailable": "基于数据画像的事实描述：几行几列、哪些字段、有无明显缺失",
  "dataSufficiency": "high/medium/low/insufficient — 基于数据画像判断，不是基于题目文字猜测",
  "mathType": ["涉及的数学类型"],
  "difficulty": "low/medium/high",
  "keyChallenges": ["难点1", "难点2"],
  "modelFit": "已有框架匹配度评估（高/中/低 + 一句话说明）",
  "innovationSpace": "创新空间评估（高/中/低 + 一句话说明）"
}
```

`dataAvailable` 和 `dataSufficiency` 必须基于附件数据画像的**实际内容**判断。附件只有 10 行数据但题目要求预测未来趋势 → `dataSufficiency` = `low`。

所有审题 agent 并行分派，等全部返回后汇总。

### Step 3: 选题推荐（1 个 Agent 综合对比）

将所有审题结果（含 `dataSufficiency` 评分）喂给选题 agent：

```
你是数学建模竞赛教练。根据以下题目分析，给出选题推荐。

## 题目分析
[所有 Step 2 agent 的审题结果 JSON——包含 dataSufficiency 字段]

## 任务
为每道题打分（每项 1-5 分），并给出推荐排名：

1. **模型匹配度**：有没有成熟的数学框架？已有方法能否直接套用？
2. **数据充分性**：基于 dataSufficiency 字段——附件数据是否足以支撑建模？需要外找数据的难度有多大？
3. **求解可行性**：算法复杂度可控？代码量在三天内可实现？
4. **风险**：数据陷阱、模型坑、计算瓶颈。
5. **创新空间**：标准方法有没有明显局限可以利用？能不能做出差异化？

每道题输出一个评分表 + 一句话综合判断。

最后给出：
- 推荐题目 + 理由（引用评分表中的硬数据，不要泛泛而谈）
- 推荐模式 (quick/standard/thorough)
- 三种模式的预估 agent 用量
- 备选题目 + 什么情况下应该换
```

### Step 4: 呈现并等用户选择

将选题 agent 的输出清晰呈现给用户，列出每道题的利弊和 agent 用量估算。

**关键：停在这里，等用户选择题目和模式。** 不要自作主张进入下一阶段。

---

## 阶段二：执行（用户选定后，调 Workflow）

用户选好题目 + 模式后，**必须用 Workflow 工具**执行 Phase 3~8。

**绝对禁止手动编排 agent 跑 Phase 3~8。** Phase 3~8 的唯一执行路径是 Workflow 工具——Workflow 脚本里包含收敛控制、评审团 ⇄ 修订 loop、趋势退出、数字溯源等复杂编排逻辑，手动跑 agent 会丢失所有这些机制。

```js
Workflow({
  scriptPath: '/home/tofu/.claude/workflows/math-model.js',
  args: {
    mode: 'standard',          // 用户选的模式 (quick/standard/thorough)
    selectedProblem: 'A',      // 用户选的题号
    problem: {                 // 选定题目的完整信息
      id: 'A',
      description: '<Step 1 agent output 中 "=== 题目原文 ===" 部分，机械提取原文>',
      dataProfile: '<Step 1 agent output 中 "=== 附件清单 ===" + "=== 附件数据画像 ===" 部分，无附件则 "无附件">',
      paperRules: '<Step 1 agent output 中 "=== 论文规则 ===" 部分，无则 "无单独论文规则">',
      analysis: '<Step 2 agent 返回的完整 JSON>',
    },
    outputDir: '/home/tofu/math-model-output',
    attachments: ['<附件绝对路径列表>'],
  }
})
```

关于 Workflow 参数：
- `scriptPath` 用绝对路径，避免名称解析失败
- `problem.description`：从 Step 1 agent 的 `=== 题目原文 ===` 标记段**机械提取**，不读内容直接粘贴
- `problem.dataProfile`：从 Step 1 agent 的 `=== 附件清单 ===` + `=== 附件数据画像 ===` 标记段提取，原始输出不加工
- `problem.analysis`：Step 2 agent 返回的完整 JSON（P0 字段：domain/objectives/constraints/mathType/difficulty/keyChallenges）
- `args.attachments`：字符串数组，附件绝对路径，从 Step 1 agent 的 ls 输出中提取
- Workflow 跑在后台，期间不要打断；结束后 Workflow 返回结果，你汇报给用户

（以下为 Workflow 脚本内部流程的参考文档——**你不需要手动执行这些**，Workflow 会自动完成。）

| Phase | 内容 | 关键机制 |
|-------|------|----------|
| 3. 文献调研 | 多角度搜索 → 精读 → 提取模型/claim → **局限分析** | 找出标准方法的共同局限，为创新提供合法来源 |
| 4. 建模方案 | Gap分析 → 多角度创新提案 → 综合 → **评委评审 ⇄ 修订 loop**(max 6轮) → **模型适配性预检**(Phase 4.5) | 正确性第一、创新锦上添花；低于阈值打回重设计 |
| 5⇄6. 求解⇄验证 | 算法→实现→**baseline对比**→验证(5维度)→投票→模型反思checkpoint→迭代修复 → **趋势退出**+dry收敛 | 数据说话；根基问题自动回溯重新建模；趋势恶化自动退出 |
| 7. 写作 | **叙事大纲** → 并行写作 → **交叉审查+评委审查 ⇄ 修复 loop**(max 3轮 dry=2) | 质量门：章节数量、排序、摘要数字溯源、图表引用、section长度、P0修复验证 |
| 8. 终审 | **摘要数字溯源** → 摘要数字溯源验证 → (LaTeX编译) → 评委自评 | 摘要定生死；每个数字需正文出处；附录含全部源代码（CUMC 第5条） |

---

## 输出目录结构

```
outputDir/
├── paper/
│   ├── paper.tex
│   └── paper.pdf
├── code/
│   ├── solution_v1.py
│   └── ...
├── figures/
│   └── fig_v*_*.png
├── data/
│   └── sip_v*_*.csv/json
├── logs/
│   ├── solution_v*.log
│   └── MODEL_RETHINK_ALERT.txt
└── intermediates/
    ├── 03-search-*.json         (文献搜索结果)
    ├── 03-fetch-*.json          (文献精读)
    ├── 03-limitation-analysis.txt
    ├── 04-gap-analysis.txt
    ├── 04-proposal-*.json
    ├── 04-final-model.json
    ├── 04-critique-*.txt
    ├── 04-revised-model-*.json
    ├── 04-redesign-*.json
    ├── 05-baseline-*.txt/json
    ├── 05-writing/              (子目录，agent 按需创建)
    │   ├── section-*.json
    │   ├── cross-review-*.txt
    │   └── judge-review-*.txt
    └── 06-final/
        ├── abstract-*.txt
        ├── compile-result.txt
        └── abstract-fixed.txt
```

---

## 方案演进与创新链条

整个流程确保创新**贯穿始终**，而不是 Phase 7 硬贴一段：

```
文献局限分析 → Gap分析(具体切入点) → 多角度方案提案 → 评委评审⇄修订loop
    → 模型适配性预检 → baseline对比(量化证明) → 求解验证(趋势收敛)
    → 创新追溯矩阵 → 叙事大纲 → 交叉审查⇄修复loop(含摘要数字溯源) → 终审
```

每一步的输出都喂给下一步，形成完整的证据链。

---

## 三种模式

| 功能 | quick | standard | thorough |
|------|-------|----------|----------|
| 触发词 | 练习/试试/快速 | （默认） | 正式/冲奖/仔细 |
| 文献局限分析 (Phase 3) | ✓ | ✓ | ✓ |
| 4人评审团 (Phase 4) | ✗ | ✓ (max 6轮) | ✓ (max 6轮) |
| 模型适配性预检 (Phase 4.5) | ✓ | ✓ | ✓ |
| baseline对比 | ✗ | ✓ | ✓ |
| 验证投票 | ✗ | 3票×2否 | 5票×3否 |
| 魔鬼代言人 | ✗ | ✓ | ✓ |
| 求解迭代收敛 | max 2轮 + 趋势退出 | dry≥2 + 趋势退出 | dry≥3 + 趋势退出 |
| 叙事大纲 | ✗ | ✓ | ✓ |
| 交叉审查 loop | ✗ | 1轮 | max 3轮 dry=2 |
| 摘要打磨 | 1轮 | 2轮 | 2轮 |
| 摘要数字溯源验证 | ✗ | ✓ | ✓ |
| 附录含全部源代码 | ✓ | ✓ | ✓ |
| LaTeX编译 | ✗ | ✓ | ✓ |
| 预估 agents | ~20 | ~250 | ~600-1000 |

---

## 常见失败模式（从 run4 测试中提取）

### 致命级（直接导致论文不合格）

| 失败模式 | 症状 | 防护机制 |
|----------|------|----------|
| **内容缺失** | 章节数量不对、某些章节截断或空白 | Phase 7 质量门：章节数量验证 + section最小长度检查 |
| **结构倒置** | "结论"放在第1节，或章节顺序混乱 | Phase 7 质量门：章节排序检查 |
| **摘要数字编造** | 摘要声称"覆盖率提升0%→100%"但正文无推导 | Phase 8 摘要数字溯源验证：逐数字在body中搜索出处 |
| **数据流断裂** | 重设计历史、评审反馈、对抗发现未进入写作上下文 | allContext优先级截断：adversarialFindings/redesignHistory排最前 |
| **交叉审查P0未修** | 符号不一致(Λ=60.6 vs 74.61)、数据矛盾 | Phase 7 loop中逐轮验证P0修复状态 |

### 严重级（影响论文质量）

| 失败模式 | 症状 | 防护机制 |
|----------|------|----------|
| **求解loop不收敛** | 每轮都出新问题，dry永远=0，跑满maxIterations | 趋势退出：连续2轮不降→退出；issues>50→取top20退出 |
| **模型全是FLAW** | 11/11次模型反思都是FUNDAMENTAL_FLAW | Phase 4.5 模型适配性预检：低分打回Phase 4 |
| **图表未引用** | 目录下生成了图但论文一张没用 | Phase 7 质量门：图表引用检查；写作prompt指示ls figures/ |
| **创新矩阵闲置** | innovationMatrix产出但未喂给写作agent | allContext包含innovationMatrix，优先级截断第4位 |

---

## 阶段三：汇报

Workflow 返回后，汇报：
- 建模方案概要 + 创新亮点
- baseline 对比结果（创新 vs 标准方法的量化提升）
- 求解迭代轮数 + 发现/修复的问题数
- 论文正文（markdown 或 PDF 路径）
- 输出文件路径（代码 + 论文）
- 模型适配性预检评分

---

## 注意事项

- **PDF 用 pdftotext 预处理**，不用 Read 工具（这台机器不支持）
- 阶段一等用户确认，阶段二不要打断
- Workflow 内 agent 失败 → 降级继续，不中断
- 论文产出 PDF（standard/thorough 模式自动尝试 xelatex 编译）
- **如有改进点，确保贯穿全文而非硬贴**：局限分析→方案提案→baseline对比→写作叙事→摘要——形成完整闭环
- 各 phase 中间产物存到 `outputDir/intermediates/`（按 phase 分子目录），方便 debug 和追溯
- **摘要每个数字必须有正文出处**：Phase 8 自动验证，不可溯源→删除或补推导
- **写作阶段是收敛 loop，不是一次性**：交叉审查+评委视角并行 → 修复 → re-review → dry 收敛
- **CUMC 2025 格式规范内建**：A4/2.5cm页边距/摘要第一页/关键词/附录含源码/匿名性/参考文献规范——均自动注入写作 prompt，不依赖题目包附带规则文件
- **附录包含全部源代码**（CUMC 第5条）：LaTeX 编译 agent 自动读取 `code/` 目录嵌入附录，缺失程序可能取消评奖资格
