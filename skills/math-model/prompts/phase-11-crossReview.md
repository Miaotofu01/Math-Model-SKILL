# 阶段模板 11：跨问复核（crossReview）

> 你是全题级的跨问复核 agent（run-level 阶段，**全题级、无小问**，q=null），本模板定义你要做的全部工作。本阶段在所有小问完成后执行，只做核验与报告，**不修改任何小问产物**。


> 公共纪律见 `_common.md`（壳与模板一并注入）。

## 输入

- `intermediates/00-problem.json`：subQuestions 清单（id/label/**dependsOn**——依赖链核验依据）
- `intermediates/00-problem.json`：题面原文（problem.description，术语与口径权威）
- 各小问（q1、q2、…，数量以 00-problem.json 的 subQuestions 为准，下同）的定稿产物：
  - `intermediates/q{id}/10-completed/question-summary.md`：小问定稿事实链（主依据，含来源标注）
  - `intermediates/q{id}/04-formulation/symbols.json`：符号登记（跨问符号一致性基准）
  - `intermediates/q{id}/04-formulation/draft.md`：方案与公式（符号/假设出处）
  - `intermediates/q{id}/03-assumptions/assumption-vNN.md`：最新版本假设
  - `intermediates/q{id}/06-computation/results.json`：关键参数与结论数值
  - `intermediates/q{id}/09-robustness/robustness.md`：稳健性边界（如有）
  - `intermediates/q{id}/04-formulation/errata.md`：**作废口径与未决项**（核验别问是否引用了已作废口径；文件缺失则该核对项注明"无勘误登记"）
- `intermediates/state.json`：确认所有小问 `q*.localComplete` 已 PASS（未全过 → 返回 FAIL）

> ⚠️ 全题级约定：本 prompt 中 `q{id}` 指各小问实际目录 q1/、q2/、…，**本阶段不使用占位符替换**；小问清单以 `intermediates/00-problem.json` 的 `problem.analysis.subQuestions[].id` 为准（阶段指令只注入 `ctx q=全题`，不含清单）。

## 执行步骤

### 1. 建立全题事实索引

列出全部小问，每问抽取：符号集（symbols.json）、假设（版本 + 关键取值）、关键参数、定稿结论（question-summary.md 的「结论」段，保留其来源标注）。汇总为全题事实表，写入报告第 1 节——此表同时是写作阶段的跨问口径基准。

### 2. 跨问一致性核验（逐维，每项结论必须带证据：文件 + 位置）

1. **符号一致**：同名符号跨问是否同义、LaTeX 写法是否一致；发现「同义不同名」或「同名不同义」（如同一量在两问取值不同）→ 不一致
2. **假设一致**：跨问共用的假设是否取同一版本、同一取值；后问假设与前置小问定稿假设相矛盾 → 不一致
3. **参数一致**：跨问共用的参数（阈值/系数/权重/时间点/口径）在各问 question-summary、results.json 中的取值是否一致；另跑 `python <技能根>/scripts/artifact_lint.py --root <outputDir>`（见 `_common.md` §6）核对关键数字是否有跨问抄写分叉，有 → P1 并列出源头
4. **结论引用**：后问结论与前置小问定稿结论是否相互印证（数值、口径、方向）；互相矛盾 → 不一致
5. **口径一致**：同一数据/同一符号在不同问的描述口径是否一致（如「样本量=清洗后行数」「成本=含税单价×数量」这类口径备注是否全篇统一）

### 3. 依赖链核验

按 00-problem.json 的 subQuestions[].dependsOn，核验后问**是否真正使用**前问定稿结论（在 question-summary / draft.md / results.json 中找引用证据）：

- 声明依赖但全文未见使用 → P2（提示写作阶段补衔接）
- 使用了但取值/口径与前置定稿不符 → P0（必须修订）

### 3b. 跨小问复用核验

- 跑 `python <技能根>/scripts/reuse_lint.py --scan --root <outputDir> --strict --json <report.json>`：`--strict` 下**跨小问重复组 = 退出码 1**
- 每个跨小问重复组按「建议权威 + 成员」列入整改清单：同口径 → 指定唯一权威实现，留待**主 agent 手工 resume 重跑该问 06+07** 时改 import（壳内每问 06 只跑一次，本阶段不会自动重跑）；**本轮禁止回改已定稿小问**（改了会让代码与 `results.json` 脱钩、数字失去可审计性）
- 口径不同 → 不合并，在 cross-question-report.md 写明差异与作用域

### 4. 定级与修订项清单

| 级别 | 含义 | 处理 |
|---|---|---|
| P0 | 结论/数值/符号矛盾（影响正确性） | 必须修订 |
| P1 | 口径/表述不一致（影响可读性） | 应修订 |
| P2 | 建议（衔接/说明可增强） | 可选 |

每项写：涉及小问与文件路径、问题描述、建议修法、严重度。修订项**只列出，不代改**其他阶段产物。

### 5. 写报告

写 `intermediates/11-cross-review/cross-question-report.md`（主产物）：

1. 全题事实索引表（小问 → 符号/假设/参数/定稿结论 + 来源路径）
2. 逐维核验结果（符号/假设/参数/结论引用/口径，逐条带证据）
3. 依赖链核验结果（按 dependsOn 逐问）
4. 修订项清单（无不一致 → 写「无」）

## 产物

- `intermediates/11-cross-review/cross-question-report.md`（主产物）

## 完成标准

- 覆盖全部小问；每个核验结论带来源路径；五个维度逐项有结果
- 全部一致 → **PASS**（报告写「无不一致项」）
- 有**非阻塞**不一致（口径备注不统一、可后补的图表/引用问题）→ **PASS_WITH_WARNING**：整改清单写入报告，写作阶段照单处理，不阻塞流程
- 有**阻断写作**的 P0（同题数字/口径互相矛盾、方法链断裂、复现失败）→ **NEEDS_REVISION**：summary 指明位置，整改清单入报告；**不得自行修改任何小问产物**（改代码/数字必须重跑该问 06 与 07，由主 agent 决定是否 resume 重跑）
- 关键输入缺失（某问缺 question-summary.md 或 symbols.json）→ FAIL 指明缺项
