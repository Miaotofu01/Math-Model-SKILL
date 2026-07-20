<p align="center">
  <img src="icon.svg" alt="math-model icon" width="160">
</p>

# math-model — 数学建模竞赛 AI 全流程编排插件

<p align="center">
  <strong>正确性第一 · 数据说话 · 摘要一锤定音</strong>
</p>

> **v2.2.0** · 基于 Claude Code 的 Agent 编排插件 · 国赛 CUMCM / 美赛 MCM

一个为**数学建模竞赛**提供端到端全自动支持的 Claude Code 插件：给题目，选一道，剩下的——审题、文献、建模、求解、验证、写论文、LaTeX 排版——由数百个 AI Agent 按预设流程协作完成，最终直接产出 PDF。

它不是聊天助手，也不是"生成一篇论文就行"。论文不是一次写出来的：建模方案要过评审团审查，求解要 baseline 对比和五维验证，摘要里每个数字都要能在正文找到推导出处。每一轮都是审查 + 修订，直到收敛。

---

## 工作流程

两阶段架构。

### 阶段一：审题 + 选题（主 agent 编排，约 5 分钟）

主 agent 不读题、不读数据，只做编排——每道题的输入由独立 agent 提纯，主 agent 没机会"润色"原文。

1. **输入提纯**（每道题并行一个 agent）：提取题目原文 + 侦察附件数据画像 + 论文规则
2. **并行审题**（每道题一个 agent）：结构化分析领域、目标、约束、数据充分性、子问题、难点
3. **选题推荐**（一个 agent）：综合模型匹配度 / 数据充分性 / 求解可行性 / 风险 / 创新空间打分排名
4. **你选一道题**——全程唯一需要你做的决策

### 阶段二：Workflow 全自动执行（约 30–90 分钟）

选定后，主 agent 调用 Workflow 工具，以下流程确定性执行，收敛控制 + 趋势退出 + 数字溯源全部内置：

| Phase | 做什么 | 关键机制 |
|-------|--------|----------|
| 3. 文献调研 | 多角度搜索 → 精读 → 提取模型/claim → 局限分析 | 为创新提供合法来源 |
| 4. 建模方案 | Gap 分析 → 多角度创新提案 → 4 人评审团 ⇄ 修订（max 6 轮）→ 适配性预检 | 适配性 STOP 真打回重设计 |
| 5 ⇄ 6. 求解 ⇄ 验证 | 算法 → 实现 → baseline 对比 → 5 维验证 → 投票 → 反思 | 趋势退出 + dry 收敛；根基问题自动回溯（max 2 次重设计） |
| 7. 写作 | 叙事大纲 → 并行撰写 → 交叉审查 + 评委审查 ⇄ 修复（max 3 轮） | 质量门：章节 / 排序 / 溯源 / 图表 / P0 |
| 8. 终审 | 摘要数字溯源 → 验证 → LaTeX 编译 → 评委自评 | 摘要每个数字需正文出处 |

---

## 学术质控机制

这是它和"一把生成论文"的本质区别：

- **4 人评审团**：建模方案进入求解前由 4 个 AI 评委审查，最多 6 轮修订才放行。
- **适配性预检**：模型结构性不适合这道题（STOP 判定）→ 直接打回 Phase 4 重新设计，不浪费 agent 硬跑废方案。
- **Baseline 对比**：每个创新点必须量化证明比标准方法好，不空谈"有改进"。
- **5 维验证**：灵敏度 / 边界 / 对抗 / 数据验证 / 魔鬼代言人。
- **数字溯源**：摘要里的每个数字都必须能在正文找到推导出处，找不到标 P0 强制修复。
- **收敛控制**：求解趋势恶化（新问题连续 2 轮超上轮 1.1×）自动退出；写作交叉审查 dry 收敛。
- **根基问题回溯**：求解触发 FUNDAMENTAL_FLAW → 自动打回 Phase 4 重新建模（max 2 次）。

---

## 安装

```bash
git clone https://github.com/Miaotofu01/Math-Model-SKILL.git
cd Math-Model-SKILL
./install.sh
```

`install.sh` 会检查依赖，并把插件装到 `~/.claude/skills/math-model/` 和 `~/.claude/workflows/math-model.js`。

### 依赖

| 依赖 | 用途 | 缺失影响 |
|------|------|----------|
| `pdftotext` (poppler-utils) | 从 PDF 提取题目文字 | 需手动粘贴题目 |
| `xelatex` + `ctex` | LaTeX 论文排版 → PDF | 只产出 Markdown，不编译 PDF |
| `python3` + numpy/scipy/pandas/matplotlib/openpyxl | 求解代码执行、数据处理、图表 | 无法求解，只出算法方案 |

`bash env-check.sh` 一键检测所有依赖。

---

## 使用

1. 在 Claude Code 里说"用 math-model"或 `/math-model`，给题目文件路径（PDF/docx）和附件目录
2. 阶段一跑完（约 5 分钟）会列出各题分析 + 选题推荐——**选一道**
3. 阶段二自动跑（约 30–90 分钟），等 PDF 产出

产出在 `./math-model-output/`。

### 可选参数

| 参数 | 默认 | 说明 |
|------|------|------|
| `outputDir` | `./math-model-output` | 产出目录 |
| `competition` | `cumcm` | `cumcm` 国赛 / `mcm` 美赛（调整论文格式与语言） |
| `innovationStrictness` | `standard` | `strict`(≥10%) / `standard`(≥5%) / `loose`(≥2%) 创新必要性阈值 |
| `skipPhases` | `[]` | 跳过阶段，如 `['literature']`（需有 checkpoint） |
| `resumeFrom` | — | 断点续跑，如 `phase4-modeling` |
| `userFeedback` | `""` | 注入到每个 prompt 的用户特别指示 |
| `userIntervention` | `false` | 写中间产物摘要，便于跟进进度 |
| `dryRun` | `false` | 只生成执行计划后停止，不消耗 agent |

---

## 产出结构

```
outputDir/
├── paper/          # paper.tex + paper.pdf
├── code/           # solution_v*.py
├── figures/        # fig_v*_*.png
├── data/           # sip_v*_*.csv / .json
├── logs/           # solution_v*.log + MODEL_RETHINK_ALERT.txt
└── intermediates/  # 03-search / 04-proposal / 05-writing / 06-final / ...
```

---

## 已知限制

- **`mode` 参数已接受但未实现差异化**：无论传什么 mode，workflow 都跑同一套完整流程（cfg 硬编码）。三种深度（quick/standard/thorough）是规划中能力，当前不是真实行为。
- **运行时间长**：完整流程约 30–90 分钟，消耗数百个 agent。
- **依赖较重**：xelatex + ctex 约 500MB；缺失则降级为 Markdown 产出。
- **模型适配性预检 STOP 会中止流程**：预检判定模型结构性缺陷时，workflow 中止并提示重新设计，不强行产出废论文。

---

## License

MIT
