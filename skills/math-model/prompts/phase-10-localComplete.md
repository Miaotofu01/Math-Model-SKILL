# 阶段模板 10：小问完成门禁（localComplete）

> 你是本小问的完成核验 agent，本模板定义你要做的全部工作。

> 工具纪律（减回合）：9 项产物清单用一次 bash `ls` 全量核对 + 一次并列读，不逐项往返。

> 公共纪律见 `_common.md`（壳与模板一并注入）。

## 输入

本问全部阶段产物（01..09 清单见下；目录或文件不存在即缺项）。

## 执行步骤

### 1. 产物清单核验（逐项，缺一即 FAIL 并指明缺项路径）

| # | 路径 | 必须存在 |
|---|---|---|
| 01 | `intermediates/q{id}/01-literature/literature.md` | 文件 |
| 02 | `intermediates/q{id}/02-data/eda.md` | 文件 |
| 03 | `intermediates/q{id}/03-assumptions/assumption-vNN.md` | 最新版本文件 |
| 04 | `intermediates/q{id}/04-formulation/draft.md`、`baseline-registry.md`、`symbols.json`、`revision-log.md`、`handoff.md` | 5 个文件（与阶段 04 完成标准的「4 台账」对齐） |
| 05 | `intermediates/q{id}/05-implementation/code/` | 目录含 .py |
| 06 | `intermediates/q{id}/06-computation/results.json` | 文件且字段齐（断言见 `prompts/artifact-schemas.md` §1.2） |
| 07 | `intermediates/q{id}/07-sanity/sanity-report.md` | 文件 |
| 08 | `intermediates/q{id}/08-visualization/figure-manifest.md` + `figures/` | 2 项 |
| 09 | `intermediates/q{id}/09-robustness/robustness.md` | 文件（SKIPPED 也须有理由文件） |

核验以**产物文件**为准，不以 state.json 的 gates 为准——即使某阶段 gates 已是 PASS，产物缺失依然算缺项（防「门禁过但产物丢」）。

### 2. 交叉一致性快检（轻量）

- results.json 数值与 sanity-report 结论一致（矛盾 → 严重不一致）
- figure-manifest 引用的图文件真实存在
- robustness 结论不与之矛盾
- 发现严重不一致 → 同样返回 FAIL 并指明问题所在

### 3. 写 question-summary.md

写 `intermediates/q{id}/10-completed/question-summary.md`：

- **事实链**：题面 → 数据 → 假设 → 方案 → 实现 → 计算 → 核验 → 图表的证据链，每个关键结论标注来源文件与位置（如「结论 X ← results.json results.<分点>.summary；公式 ← draft.md 式(N)」）
- **结论**：逐分点具体数值结论（来自 results.json，禁止编造）
- **引用**：文献引用编号（literature.md 引用登记）+ 外部数据来源（如有）
- **图表清单**：figure-manifest 摘要（图名 → 作用 → 论文位点）
- **遗留问题**：sanity warning、robustness 弱点、未解决项（供写作阶段处理）

## 产物

- `intermediates/q{id}/10-completed/question-summary.md`（主产物）

## 完成标准

- 清单全过且 summary 写完 → PASS
- 缺项或严重不一致 → FAIL 指明缺项；不修产物、不伪造
