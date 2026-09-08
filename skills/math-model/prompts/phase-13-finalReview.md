# 阶段模板 13：终审（finalReview）

> 你是全题级终审 agent（run-level 阶段，**全题级、无小问**，q=null）。调度壳已注入：模式（full/quick）、依赖与产物路径。所有相对路径基于 outputDir 根；先 `cd <outputDir>` 再执行组装与编译。终审流程：**摘要数字溯源 → 一致性检查 → 评委自评（按获奖标准评分）→ LaTeX 编译**。

## 统一节拍

1. 读 intermediates/state.json：确认前置门禁（gates 中前置阶段为 PASS），否则返回 {status:"FAIL", ...}
2. 读依赖文件（本阶段的 deps，路径已由调度壳注入）
3. 执行本阶段任务，写产物到指定路径
4. 更新 state.json 对应字段 + 追加 intermediates/ledger.md 一行
5. 返回 {status:"PASS|DRAFT|NEEDS_REVISION|FAIL|SKIPPED", artifact_path, summary≤200字}

## 规范引用

先 Read `skills/math-model/docs/writing-and-format.md`（不可用时按模板目录向上找 `docs/`）。本节相关：§三 CUMCM/MCM 格式（摘要页/≤20页/附录/无身份信息）、§四 论文模板要点（摘要 `\section*`、参考文献单标题、附录 A/B/C、代码附录 §四-5、`$\bm{}$` §四-6、支撑材料清单 §四-7、组装与 @占位符 §四-8）、§六 内部 Common Mistakes（摘要数字编造等）。**引用规范，不复制内容**。

## 输入

- `intermediates/12-writing/paper-sections/section-*.md`：写作产物（全部章节；缺章 → FAIL 指明，纯机理题删数据章除外）
- `intermediates/12-writing/fact-sheet.md`：事实源表（溯源基准）
- 各小问（q1、q2、…，数量以 00-problem.json 的 subQuestions 为准）：`10-completed/question-summary.md`、`06-computation/results.json`、`09-robustness/robustness.md`、`04-formulation/baseline-registry.md`、`08-visualization/figure-manifest.md` + `figures/`、`01-literature/literature.md`（引用登记）、`05-implementation/code/`
- `intermediates/11-cross-review/cross-question-report.md`：跨问复核结论（已 PASS）
- `intermediates/00-problem.json`：题面、论文规则、题号、附件清单
- 模板目录：调度壳 templateDir（绝对路径）或 `${PD}` 的父级 `templates/`，二选一自动探测（cumcm-paper.tex + assemble_from_template.py）

> ⚠️ 全题级：`q{id}` 指各小问实际目录 q1/、q2/、…（本阶段无占位符替换）；产物写 `intermediates/13-final/` 前缀。

## 执行步骤

### 1. 重建章节

按组装脚本期望顺序读 `12-writing/paper-sections/section-*.md`（首行 `# 章节名` 识别）：摘要/问题重述/问题分析/模型假设与符号说明/数据预处理与探索性分析/模型建立与求解/结果分析与验证/灵敏度与稳健性分析/模型的评价与推广/结论与改进（只取存在的；非预期缺失 → FAIL 指明，纯机理题删数据章除外）。摘要与正文分离。

### 2. 摘要数字溯源（硬门禁）

写 `intermediates/13-final/abstract-trace.md`：
1. 从摘要提取全部**具体数字**（百分比/数值/时间等），忽略序号与年份
2. 对每个数字三查：① 正文出处（章节+位置）② 溯源到**产物文件**（question-summary.md 事实链 / results.json 字段 / robustness.md / baseline-registry.md / fact-sheet.md 的 sourcePath）③ 各产物间数值一致（矛盾 → 以 results.json 真实输出为准，正文与摘要同步修正）
3. 输出溯源表：{摘要数字 | 上下文 | 正文出处 | 产物来源路径 | 结论}

**任何数字无法溯源（正文无出处或产物无来源路径）→ 直接 FAIL**（指明数字与缺失），不修复、不编造、不删除后放行。

### 3. 一致性检查

- 摘要按子问题分段（「对于问题1…」逐问方法+数值）且逐问覆盖；正文问题分析/模型/分析/结论各章覆盖全部小问
- 内部流程术语扫描（§一-14：「对抗性审查/模型重设计/adversarialFindings/验证器/重设计历史」）→ 出现即 P1 改写
- 图表反向检查：每个 `\includegraphics` 文件真实存在于 figures/；无空 figure 环境；CJK 字体无 Glyph 缺失警告（§二-1/5）
- 加粗只加答案（§一-2）；无「创新点：」等标签（§一-3）；无调试笔记/文件路径/对账清单残留（§一-12）

### 4. 评委自评（按获奖标准评分）

以评委身份（已读 100 篇同题论文）写 `intermediates/13-final/judge-self-review.md`：按国一/国二/成功参赛三档标准逐维评分（每维 0-10 + 一句理由）：摘要质量、问题分析深度、模型建立与求解、结果与验证、灵敏度与稳健性、创新真实性、写作规范与 AI 味、逐问覆盖、格式合规（§三）。结尾回答：与同题 100 篇比为什么有印象？最大弱点（具体）？修改哪一个最能提升竞争力？

**限 1 轮最小改动修复**：针对评委最大弱点与提升建议，对相关章节做最小改动（只改表述/结构/遗漏的推导；**不得新造或改写数字**——以 fact-sheet 为准）；修复后回到步骤 2 重新溯源、步骤 5 重新编译。

### 5. LaTeX 编译（CUMCM）

**第 0 步 清理**：写 .tex 前删除章节内容中的：Agent 调试笔记（「修复完成」「P0/P1/P2:」等）、文件路径引用、Markdown 表格/对账清单、重复摘要、章节内自带的 thebibliography。

**第 0.5 步 组装**（用 skill 模板，不手工拼接 preamble）：
1. 提取引用键：`grep -ho '\\cite{[^}]*}' intermediates/12-writing/paper-sections/*.md | grep -o '{[^}]*}' | tr -d '{}' | tr ',' '\n' | sort -u`
2. 生成参考文献：按 literature.md 引用登记表逐键生成 GB/T 7714 bibitem（中文：作者.题名.刊名,年份,卷(期):页码；英文同理；`ai_tool` 键固定用：AI工具使用声明：大语言模型辅助写作工具（Claude, 版本2026, Anthropic公司, 使用日期2026-08）[Z]. 使用详情见支撑材料《AI工具使用详情》。），包进 `\begin{thebibliography}{N}...\end{thebibliography}` 写入 /tmp/refs.tex
3. 章节格式转换：组装脚本读 `section-*.json`（{"section","content"}）；把 12-writing 的 section-*.md 转成该格式（首行 `# 章节名` → section 字段，其余 → content），存临时目录（如 `intermediates/13-final/sections-json/`），不改动 12-writing 的 .md 产物
4. 运行组装：
   ```
   python3 <templates>/assemble_from_template.py \
     --template <templates>/cumcm-paper.tex \
     --sections intermediates/13-final/sections-json \
     --output intermediates/13-final/final-paper.tex \
     --title "全国大学生数学建模竞赛<题号>题" \
     --paper-title "<从题目原文提取的论文题目>" \
     --subtitle "<一句话方法名副标题>" \
     --references "$(cat /tmp/refs.tex)" \
     --code-entries "问题N-<文件名>|intermediates/qN/05-implementation/code/<文件>" \
     --materials "\item 求解程序（完整可运行，位于支撑材料 code/ 目录）" \
     --materials "\item 结果数据（results.json 等，位于 data/ 目录）" \
     --materials "\item 图表文件（位于 figures/ 目录，均在正文引用）" \
     --materials "\item AI工具使用详情（AI 工具使用详情.pdf，按《全国大学生数学建模竞赛人工智能工具使用规定》第4(2)条要求）" \
     --materials "\item 赛题原始数据由竞赛提供，按规范第十一条不包含在支撑材料中；全部结果可由上述源程序直接复算"
   ```
   每个小问的每个 .py 一条 `--code-entries`；某问 results.json 含疑似名单/排序表数据 → 提取为 JSON 并追加 `--suspect-json`（无则忽略）；代码文件若含身份信息/绝对路径/Unicode 数学符号（如 θ），按 §四-5 先复制清洗副本再引用（不改原产物）。
5. 组装后检查：摘要用 `\section*{摘 要}`（无编号）；`thebibliography` 恰好 1 个；附录从 `\appendix` 开始（A/B/C 编号）；无残留 `@XXX@` 占位符（忽略 %% 注释行）；报「未找到章节」→ 按组装脚本 order 校正 section 名后重跑。

**第 6-7 步 编译**（两遍 xelatex，必须两遍都通过）：
```
cd <outputDir> && xelatex -interaction=nonstopmode -file-line-error intermediates/13-final/final-paper.tex 2>&1 | tee intermediates/13-final/compile.log | tail -60
cd <outputDir> && xelatex -interaction=nonstopmode -file-line-error intermediates/13-final/final-paper.tex 2>&1 | tee intermediates/13-final/compile.log | tail -60
```
错误 → 读 `intermediates/13-final/compile.log` 修正 .tex 后重试（最多 3 次）。常见：`Undefined control sequence`（命令拼错或缺 usepackage）、`Missing $ inserted`（数学符号出数学模式）、`File not found`（includegraphics 路径错）、中文乱码（ctexart+xelatex）、附录代码 `_ ^ % &` 特殊字符（listings `basicstyle=\ttfamily` 规避）。

**第 8 步 页数与输出**：正文（含摘要）≤20 页（§三；超标优先精简约简非核心段落）；PDF 生成 `intermediates/13-final/final-paper.pdf`；残留 warning（Overfull/未定义引用等）逐条记录。

MCM 说明：若题目包论文规则为 MCM/ICM（英文论文），按 §三 的 MCM 格式执行；CUMCM 模板与组装脚本不适用，走**手动兜底路径**——自拼英文 preamble 后两遍 xelatex 编译（cwd 规则同上），正文各章仍用写作产物。

## 产物

- `intermediates/13-final/final-paper.tex`（主产物）
- `intermediates/13-final/final-paper.pdf`、`compile.log`、`abstract-trace.md`、`judge-self-review.md`

## 完成标准

- 摘要每个数字有溯源表且全部可溯源（有正文出处 + 产物来源路径）；**任一无法溯源 → FAIL**
- 评委自评完成（逐维得分 + 最大弱点 + 提升项）；限 1 轮修复已应用并重新验证
- 组装无占位符残留；两遍 xelatex 通过；final-paper.tex / pdf / compile.log 齐全
- 编译通过且干净 → PASS；编译通过但残留 warning → PASS_WITH_WARNING（记录在案）；编译失败或溯源失败 → FAIL 指明
