# 阶段模板 06：计算（computation）

> 你是本小问的计算 agent，本模板定义你要做的全部工作。

> 公共纪律见 `_common.md`（壳与模板一并注入）。

## 规范引用

先 Read `<技能根>/prompts/artifact-schemas.md`（results.json 契约，本阶段产物按它写）。

规范引用：先 Read `<技能根>/docs/writing-and-format.md`（技能根见 `_common.md §6`）。本节相关：§二 图表生成规范（代码含绘图语句时按 §二-1/2/3/5 配置 CJK 字体与单位写法）。性能纪律见 `docs/performance.md`（可选加速、禁硬依赖）。引用规范，不复制内容。

## 输入

- `intermediates/q{id}/05-implementation/code/`：可运行代码与 README 运行说明
- `intermediates/q{id}/04-formulation/draft.md`：求解策略（运行口径复核）
- `intermediates/q{id}/04-formulation/baseline-registry.md`：**baseline 预注册——同场对比的指标依据**
- `intermediates/q{id}/04-formulation/symbols.json`：符号（结果字段命名对齐）
- `intermediates/q{id}/04-formulation/handoff.md`：**交本阶段的检验项与 P0**（预注册的生产配置/验收对象/成本上限）——运行口径与它在冲突时以它为准
- `intermediates/q{id}/04-formulation/errata.md`：**作废口径与未决项**——不得据已作废口径出数；未决项按其中写明的处理方式执行
- 附件数据与 `pool/external-data/`：只读

## 执行步骤

### 1. 运行主模型

按 README 运行（`METHOD=innovative`）：先确认脚本与数据存在；后台运行 + 定时查日志（最长 15 分钟）；完成后读日志取**真实输出**。**必须实际运行并报告真实结果——只写代码不运行即失败；summary 禁止「待实现」「见代码」。**

### 2. 运行错误 → 迭代修复循环

报错 → 读错误信息 → 修改代码（code/ 下写新版本 `solution_v2.py`…，保留版本链）→ 重跑，直到跑通；每轮错误与修复记入 results.json 的 fixHistory。修复轮数上限见 `stage-manifest.json#retryPolicy.repairRounds`（当前由你在单次调用内自行控制，壳不强制）；仍失败 → 返回 FAIL 写明原因，**不伪造结果**。

### 3. baseline 同场计算（必须）

`METHOD=baseline` 运行**同一脚本**（同场 = 同一代码、同一数据加载/预处理/后处理/评价流程，公平性由 dual-path 结构保证），提取 baseline 指标；对照 baseline-registry.md 预注册的指标口径计算对比。registry 写了「无 baseline 理由」→ baselineComparison 记「无」并引用理由，不做假对比。

### 4. 结果落盘 intermediates/q{id}/06-computation/results.json

```json
（**schema 见 `<技能根>/prompts/artifact-schemas.md` §1**——本阶段按该契约写；字段名/结构以那份为准）
```

### 5. 性能与耗时记录（按 docs/performance.md，可选加速）
### 5. 性能与耗时记录（按 docs/performance.md，可选加速）

- 运行前探测可用加速（numba/joblib/cupy/torch，**可选**；缺失自动回退纯 numpy/scipy，绝不因依赖缺失 FAIL）。
- **单次求解/核验预算**：≤15 分钟**且** ≤8× 本问生产主体墙钟（取小）；**先估后跑**（估算式 + ≤30 s 标定片段见 `<技能根>/docs/performance.md` §6.1），预估超预算 → 按 **缩窗 → 减档 → 降精度** 固定顺序缩，禁止「先跑再看」；确实超时 → 如实记录（不伪造、不无限等待）。
- **阶梯/扫参/对拍类核验**：**逐档落盘**（`probe_cache.py` 的 `pc.checkpoint_put/get`，重跑自动跳过已完成档 ⇒ kill 不作废）+ 档间并行；窗长/档数变更回写 draft / `baseline-registry.md` 的预注册条目。
- **耗时留档**：results.json 增加 `perf: {wallTime_s, method, parallel, costEstimate_s, budget_s, tiers, shrink, notes}`（真实测量值），供 sanity 核验与论文如实披露。

## 产物

- `intermediates/q{id}/06-computation/results.json`（主产物）；可能含 `figures/`
- **单行 ≤2000 字符**：长条目逐项换行（`keyValues` 一行一条）、长表/长文本外置 `.md` 并留指针——否则评审与下游读到的该行会被**静默截断**（read 工具硬限）。

## 完成标准

- results.json 全部为真实运行数字；求解器状态/约束残差/随机种子已记录
- baseline 同场完成（或按 registry 理由跳过并注明）
- 跑不通/不收敛 → FAIL 如实上报，不伪造
