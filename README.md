<p align="center">
  <img src="icon.svg" alt="math-model icon" width="140">
</p>

# math-model — 数学建模竞赛 AI 全流程编排

<p align="center">
  <strong>给题 → 选一道 → 论文 PDF 自己出来</strong>
</p>

> **审题、文献、建模、求解、验证、写作、LaTeX 排版——数百个 Agent 按预设流程协作，最终直接产出可提交的 PDF。**
>
> 它不会"写一篇论文给你"——它像一支纪律严明的参赛队：方案要过 4 人评审团，求解要做五维验证，摘要里**每一个数字都要能在正文找到出处**。每一轮都是审查 + 修订，直到收敛。

<p align="center">
  <a href="#-快速开始"><img alt="Quickstart" src="https://img.shields.io/badge/快速开始-30s-4c6ef5"></a>
  <img alt="Version" src="https://img.shields.io/badge/version-2.4.0-1c1a17">
  <img alt="Platform" src="https://img.shields.io/badge/platform-DSH%20%7C%20Claude%20Code-6d5a9e">
  <img alt="Competition" src="https://img.shields.io/badge/CUMCM%20%7C%20MCM-2f7d4f">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-8a857d">
</p>

---

## 它解决什么问题

直接问 AI"帮我做一道数模题"时，你会得到：一篇泛泛而谈的思路、**无法验证的数字**、靠猜的论文格式。而数模竞赛的评分逻辑是——**正确性第一，数据说话，摘要一锤定音**。

math-model 把"一个人 + 一个模型"变成"**一支编排严密的 agent 参赛队**"：

| 直接问 AI | 用 math-model |
|---|---|
| 一篇"看起来对"的思路 | 结构化审题 → 选题推荐 → 你拍板 |
| 数字可能是编的 | **每个数字都有正文出处 + 代码 stdout 对账** |
| 方法自说自话 | 4 人评审团 ⇄ 修订（max 6 轮）后才动笔 |
| 论文格式靠猜 | CUMCM 模板 + LaTeX 两遍编译闭环 |
| 跑一半断掉就白干 | checkpoint 断点续跑，换题自动拒脏数据 |

---

## 工作流程一览

![math-model 工作流总览](docs/workflow-v2.png)

**两阶段**：阶段一**审题 + 选题**（主 agent 纯编排，全程唯一人工决策 = 你选一道题）；阶段二 **Workflow 全自动**（文献 → 建模 → 求解⇄验证 → 写作 → 终审，三大迭代 loop 内置收敛控制）。

---

## 快速开始（30 秒）

```bash
git clone git@github.com:Miaotofu01/Math-Model-SKILL.git ~/math-model-skill
bash ~/math-model-skill/install.sh        # DSH 符号链接安装，立即生效
```

然后在任意会话里输入：

```
/math-model
```

完事。剩下的由 agent 队接管。

---

## 功能亮点

- **审题选题自动化**：输入提纯 → 并行审题 → 选题推荐，每道题由独立 agent 处理，主 agent 不"润色"原文
- **4 人评审团 ⇄ 修订**（max 6 轮）：理论数学家、工程师、领域专家、魔鬼代言人——不 PASS 不进入求解
- **求解 ⇄ 五维验证 + 投票**：baseline 对比、灵敏度/边界/对抗/硬数据验证，dry≥3 才收敛，趋势退出防死循环
- **事实源表数字纪律**：全篇数字以事实源表为唯一权威，写作阶段顺序主编保证跨章口径一致
- **摘要数字溯源 + 代码-论文对账**：摘要每个数字必须在正文有出处，且与代码 stdout 一致
- **修复落盘进最终 PDF**：交叉审查/数字溯源/评委意见的修复全部写回磁盘（P0-2 机制）
- **checkpoint 断点续跑**：runFingerprint 防跨题目脏数据，中断后 `resumeFrom` 接着跑
- **双平台**：DeepSeek Harness + Claude Code，一个仓库单一事实源
- **`quick` 模式**：赶时间用（评审 1 轮 / dry=1 / 写作 1 轮，约 30-40 agents）

---

## 使用示例

```
你:   /math-model
      （拖入 2025 年 C 题 PDF + 附件目录）

Agent: 已并行提纯 3 道题、完成审题。
       推荐选题：C 题（数据充分、求解可行、创新空间大）
       请选择题目（A / B / C）……

你:   C

Agent: 已启动 Workflow（full 模式，预计 1-3 小时，期间请勿打断）。
       完成后你会得到：paper.pdf + 可复现代码 + 中间产物。
       （Progress: 文献调研 → 建模评审 …）
```

跑完后汇报：建模概要 + 创新点、baseline 对比、迭代轮数、PDF 路径，以及**代码-论文数字对账结果**。

---

## 安装（详细）

### DeepSeek Harness（推荐）

```bash
bash ~/math-model-skill/install.sh --dsh
# 或手动：ln -sfn ~/math-model-skill/skills/math-model ~/.dsh/skills/math-model
```

符号链接安装 → 仓库即事实源，改仓库即时热更新。

### Claude Code

```bash
bash ~/math-model-skill/install.sh --claude
```

### 环境依赖

| 依赖 | 用途 | 缺失影响 |
|---|---|---|
| `pdftotext`（poppler-utils） | PDF 题目文字提取 | 需手动粘贴题目 |
| `xelatex` + ctex（TeX Live） | LaTeX 论文排版 | 无法产出 PDF |
| `python3` + numpy/scipy/pandas/matplotlib/openpyxl | 求解代码执行 | 无法运行建模代码 |
| Noto Sans CJK SC 字体 | 图表中文渲染 | 中文显示为方框 |

`install.sh` 会逐项检测并给出安装提示。

---

## 配置

Workflow 的 `args` 支持：

| 参数 | 说明 |
|---|---|
| `competition` | `"cumcm"`（国赛，默认）／ `"mcm"`（美赛：英文、Summary Sheet） |
| `mode` | `"full"`（默认，110~160+ agents）／ `"quick"`（~30-40 agents） |
| `templateDir` | 模板目录路径；不传自动探测 |
| `outputDir` | 输出目录（默认 `./math-model-output`） |
| `resumeFrom` / `skipPhases` | 断点续跑 / 跳过已完成 phase |
| `innovationStrictness` | `strict` / `standard` / `loose`（创新阈值） |

**运行预期**：30 分钟 ~ 10 小时，取决于建模评审 loop 与代码求解的时间复杂度。workflow 前台阻塞，勿打断；中断后 `resumeFrom` 续跑。

---

## 目录结构

```
math-model/
├── skills/math-model/            # 技能本体（单一事实源）
│   ├── SKILL.md                  # DSH 版主文档
│   ├── SKILL.claude.md           # Claude Code 版
│   ├── prompts/                  # 审题阶段 step1~3 提示词
│   ├── templates/                # cumcm-paper.tex + 通用组装脚本
│   └── workflows/                # 主编排脚本（双平台共用）+ meta.json
├── install.sh                    # 一键安装（--dsh / --claude / --both）
├── env-check.sh                  # 环境依赖检测
├── docs/                         # 工作流总览图（PNG / Mermaid / HTML）
└── .claude-plugin/plugin.json
```

---

## FAQ

**跑一次要多久？多少钱？**
30 分钟 ~ 10 小时（full 模式通常以小时计）。full 一次 110~160+ 个 subagent、约数百万 token；`quick` 模式压到 30-40 个 agent，适合初稿与验证。成本大头在求解⇄验证 loop——问题越难越贵。

**和"直接让 AI 做一道题"到底有什么区别？**
结构化的评审/验证/溯源质量门。直接问会得到"看起来对"的结果；这套流程把**正确性**变成可检查的流程：数字必须有出处、方案必须过评审、代码必须真跑、论文必须编译通过。

**中途失败了怎么办？**
每个 phase 完成即落 checkpoint（含运行指纹），`resumeFrom` 从失败处续跑，不重头再来。换题目/换参数会自动拒绝旧 checkpoint，不会串数据。

**论文格式合规吗？**
CUMCM 模板内置 2026 实战教训：摘要专用页、≤20 页、无参赛身份信息、支撑材料清单、AI 工具使用声明，LaTeX 两遍编译出 PDF。

**支持美赛吗？**
支持（`competition: "mcm"`）：英文写作、Summary Sheet、letterpaper 版式、APA 风格引用。

---

## 变更历史

- **v2.4.0**：P0 修复（CUMCM 路径 TDZ 崩溃、修复落盘进 PDF、checkpoint 指纹）；A 修复（路径参数化、模板去赛题化、两遍编译）；B 新增 `quick` 模式；C 修复（切片扩大、堵三处假收敛、persona 索引、自评转修复轮）
- v2.3.0：写作阶段重构（事实源表 + 顺序主编 + 交叉审查）
- v2.2.0：同步部署态、修 doc↔code 不一致、删死代码

## License

MIT
