<p align="center">
  <img src="icon.svg" alt="math-model icon" width="160">
</p>

# math-model — 数学建模竞赛 AI 全流程编排技能

<p align="center">
  <strong>正确性第一 · 数据说话 · 摘要一锤定音</strong>
</p>

> **v2.4.0** · DeepSeek Harness（DSH）+ Claude Code 双平台 · 国赛 CUMCM / 美赛 MCM

为**数学建模竞赛**提供端到端全自动支持的 Agent 技能：给题目，选一道，剩下的——审题、文献、建模、求解、验证、写论文、LaTeX 排版——由大量 AI Agent 按预设流程协作完成，最终直接产出 PDF。

论文不是一次写出来的：建模方案要过 4 人评审团审查，求解要 baseline 对比和五维验证，摘要里每个数字都要能在正文找到出处。每一轮都是审查 + 修订，直到收敛。

---

## 工作流程（两阶段）

### 阶段一：审题 + 选题（主 agent 编排）

主 agent 不解读、不润色题目与数据——只机械透传、分派 sub-agent、汇总呈现（附件验证与代码对账除外）。

1. **输入提纯**（每道题并行一个 agent）：提取题目原文 + 侦察附件数据画像 + 论文规则
2. **并行审题**（每道题一个 agent）：结构化分析领域、目标、约束、数据充分性、子问题、难点
3. **选题推荐**（一个 agent）：综合打分排名
4. **你选一道题**——全程唯一需要你做的决策

### 阶段二：Workflow 全自动执行

选定后调用 workflow 工具，以下流程确定性执行，收敛控制 + 趋势退出 + 数字溯源全部内置：

| Phase | 做什么 | 关键机制 |
|-------|--------|----------|
| 3. 文献调研 | 多角度搜索 → 精读 → 提取模型/claim → 局限分析 | 为创新提供合法来源 |
| 4. 建模方案 | Gap 分析 → 多角度创新提案 → 4 人评审团 ⇄ 修订（max 6 轮）→ 适配性预检 | 低于阈值 → 预检终止并提示（换方向/放宽严格度后重跑） |
| 5 ⇄ 6. 求解 ⇄ 验证 | 算法 → 实现 → baseline 对比 → 5 维验证 → 投票 → 反思 | 趋势退出 + dry 收敛；根基问题自动回溯（max 2 次重设计） |
| 7. 写作 | 事实源表 → 叙事大纲 → 顺序主编撰写 → 交叉审查 ⇄ 修复 | 全篇数字以事实源表为唯一权威；修复后落盘进最终 PDF |
| 8. 终审 | 摘要数字溯源 → 代码-论文数字对账 → 评委意见 → 一次限定修复 → LaTeX 编译 | 摘要定生死；每个数字需正文出处 |

---

## 安装

### DeepSeek Harness（推荐，符号链接享受热更新）

```bash
git clone git@github.com:Miaotofu01/Math-Model-SKILL.git ~/math-model-skill
bash ~/math-model-skill/install.sh --dsh
# 或手动：
ln -sfn ~/math-model-skill/skills/math-model ~/.dsh/skills/math-model
```

安装后技能目录实时生效（DSH 监听 `~/.dsh/skills`），输入 `/math-model` 即可触发。

### Claude Code

```bash
bash ~/math-model-skill/install.sh --claude
```

将 `SKILL.md`（DSH 版）+ `SKILL.claude.md`（Claude 版）与 workflow 脚本按需安装到 `~/.claude/skills` 与 `~/.claude/workflows`。

### 环境依赖

- `pdftotext`（poppler-utils）— PDF 题目文字提取
- `xelatex` + ctex — LaTeX 排版（`texlive-xetex texlive-lang-chinese`，约 500MB）
- `python3` + numpy/scipy/pandas/matplotlib/openpyxl — 求解代码执行
- 中文字体：Noto Sans CJK SC（图表中文渲染）

`install.sh` 会逐项检测并给出缺失提示。

---

## 使用

任意会话输入 `/math-model`（或直接描述数模任务），按引导完成阶段一后，workflow 的 `args` 支持：

| 参数 | 说明 |
|------|------|
| `competition` | `"cumcm"`（国赛，默认）或 `"mcm"`（美赛：英文、Summary Sheet、letterpaper） |
| `mode` | `"full"`（默认，110~160+ agents）或 `"quick"`（评审1轮/求解dry=1/写作1轮，~30-40 agents） |
| `templateDir` | 模板目录绝对路径；不传则自动探测 `~/.dsh`/`~/.claude` 下的技能副本 |
| `outputDir` | 输出目录（默认 `./math-model-output`） |
| `resumeFrom` / `skipPhases` | 断点续跑 / 跳过已完成的 phase（依赖 checkpoint） |
| `innovationStrictness` | `"strict"` / `"standard"` / `"loose"`（创新必要性阈值） |

**运行预期**：30 分钟 ~ 10 小时不等，主要取决于建模评审 loop 与代码求解阶段的时间复杂度。workflow 前台阻塞，期间勿打断；中断后用 `resumeFrom` 续跑（checkpoint 含运行指纹，换题目/换参数会自动拒绝旧 checkpoint）。

---

## 目录结构

```
math-model/
├── skills/math-model/            # 技能本体（单一事实源）
│   ├── SKILL.md                  # DSH 版主文档
│   ├── SKILL.claude.md           # Claude Code 版（Workflow scriptPath 语法）
│   ├── prompts/                  # 审题阶段 step1~3 提示词
│   ├── templates/                # cumcm-paper.tex + 通用组装脚本（附录B 可选）
│   └── workflows/
│       ├── math-model.js         # 主编排脚本（含 export const meta，双平台共用）
│       └── meta.json             # workflow meta（DSH 运行时单独传参）
├── install.sh                    # 一键安装（DSH symlink / Claude 拷贝）
├── env-check.sh                  # 环境依赖检测
├── .claude-plugin/plugin.json    # Claude 插件元数据
└── icon.svg
```

## 变更历史

- **v2.4.0（本次重构）**
  - 修复 P0：CUMCM 默认路径 TDZ 崩溃（此前 phase8 必崩）；交叉审查/摘要溯源/代码对账修复落盘进最终 PDF；checkpoint 增加运行指纹防跨题目脏数据
  - 修复 A：模板路径参数化（`templateDir` 或自动探测）；模板去赛题化（附录 B 可选、名单渲染通用化）；xelatex 两遍编译；SKILL.md 指令修正
  - 新增 B：`mode: "quick"` 快速模式；文档化 token 成本与耗时预期
  - 修复 C：摘要溯源切片扩大（15K→60K）；堵三处假收敛（投票/dry/写作 dry）；评审 persona 索引错位；砍掉国一/国二自评转一次限定修复轮；适配性 STOP 诚实化
- v2.3.0：写作阶段重构（事实源表 + 顺序主编撰写 + 交叉审查）
- v2.2.0：同步部署态、修 doc↔code 不一致、删死代码

## License

MIT
