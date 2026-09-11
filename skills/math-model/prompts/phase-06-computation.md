# 阶段模板 06：计算（computation）

> 你是本小问的计算 agent，本模板定义你要做的全部工作。调度壳已注入：当前小问 ID（ctx 中的 `q`，如 `q1`）、模式（full/quick）、依赖与产物路径。下文路径中 `q{id}` 替换为 ctx 中的小问 ID；所有相对路径基于 outputDir 根。

> 公共纪律（统一节拍 / 工具纪律 / 数字单一真源 / 复用 / 工具与文档路径）见 `_common.md`——**与本模板同一次并列 Read 读入**。

## 规范引用

先 Read `<技能根>/docs/writing-and-format.md`（`<技能根>` = 阶段指令里给出的技能根；该文件缺失时按技能根向上/向下探测 `docs/`）。本节相关：§二 图表生成规范（代码含绘图语句时按 §二-1/2/3/5 配置 CJK 字体与单位写法）。性能纪律见 `docs/performance.md`（可选加速、禁硬依赖）。引用规范，不复制内容。

## 输入

- `intermediates/q{id}/05-implementation/code/`：可运行代码与 README 运行说明
- `intermediates/q{id}/04-formulation/draft.md`：求解策略（运行口径复核）
- `intermediates/q{id}/04-formulation/baseline-registry.md`：**baseline 预注册——同场对比的指标依据**
- `intermediates/q{id}/04-formulation/symbols.json`：符号（结果字段命名对齐）
- 附件数据与 `pool/external-data/`：只读

## 执行步骤

### 1. 运行主模型

按 README 运行（`METHOD=innovative`）：先确认脚本与数据存在；后台运行 + 定时查日志（最长 15 分钟）；完成后读日志取**真实输出**。**必须实际运行并报告真实结果——只写代码不运行即失败；summary 禁止「待实现」「见代码」。**

### 2. 运行错误 → 迭代修复循环

报错 → 读错误信息 → 修改代码（code/ 下写新版本 `solution_v2.py`…，保留版本链）→ 重跑，直到跑通；每轮错误与修复记入 results.json 的 fixHistory。修复轮数上限：full 3 轮 / quick 1 轮；仍失败 → 返回 FAIL 写明原因，**不伪造结果**。

### 3. baseline 同场计算（必须）

`METHOD=baseline` 运行**同一脚本**（同场 = 同一代码、同一数据加载/预处理/后处理/评价流程，公平性由 dual-path 结构保证），提取 baseline 指标；对照 baseline-registry.md 预注册的指标口径计算对比。registry 写了「无 baseline 理由」→ baselineComparison 记「无」并引用理由，不做假对比。

### 4. 结果落盘 intermediates/q{id}/06-computation/results.json

```json
{
  "runs": {"finalScript": "<本次最终实际执行的脚本文件名>", "mode": "<ctx 的 full|quick，按实际填>"},
  "results": {
    "<分点>": {
      "summary": "具体数值结论（禁「待实现」「见代码」）",
      "keyValues": [{"label": "...", "value": "..."}]
    }
  },
  "solver": {"status": "...", "iterations": 123, "mip_gap": null,
             "constraintResiduals": {}, "timeLimitHit": false},
  "seeds": {"randomState": 42, "numpySeed": "...", "pythonSeed": "..."},
  "baselineComparison": {
    "metrics": [{"name": "RMSE", "baseline": "0.047", "improved": "0.023",
                 "improvement": "51.1% ↓", "isLowerIsBetter": true}],
    "summary": "一句话总结创新提升（供摘要）",
    "significance": "high|medium|low|marginal",
    "weaknessExposed": "对比暴露的弱点（诚实，论文也要讨论）"
  },
  "fixHistory": [{"round": 1, "error": "...", "fix": "..."}]
}
```

- `results`：按本问各分点组织，summary 必须含具体数值；keyValues 含关键中间值（可审计）
- `solver`：求解器状态/迭代数；MILP 求解器给出 mip_gap；约束残差（硬约束违反量）；达时限标记
- `seeds`：固定并记录全部随机种子；未固定 → 如实记录缺失（sanity 阶段核验）
- `baselineComparison`：≥3 个对比维度（精度/效率/稳定性等）；每指标给 baseline 值、improved 值、improvement 百分比、isLowerIsBetter；summary 一句话总结提升；significance 显著程度；weaknessExposed 诚实写弱点
- **数字单一真源**：`results.json` 是本问**唯一数字权威**（下游 draft/sanity/robustness/question-summary/figure-manifest/绘图脚本/论文只写锚点引用，不重复抄数值，见 `_common.md` §4）；keyValues 必须覆盖论文会出现的**全部**关键数字并带口径注记，漏登记会让下游无源可引
- 代码含绘图语句 → 图保存到 `intermediates/q{id}/06-computation/figures/`（结果图原始输出，可视化阶段复用/重画），本阶段不要求出图

### 5. 性能与耗时记录（按 docs/performance.md，可选加速）

- **Python 环境**：所有 python 执行一律用调度壳注入的环境路径（`intermediates/env-report.json` 为准（文件不存在 → 用系统 python3））；依赖缺失 → 优先 venv 安装、失败降级纯 numpy/scipy，绝不因缺库 FAIL。
- **复用核心实现（禁止重写）**：若 `pool/` 或前序小问已有同口径核心实现（如判据/求解器等核心算法；先查 `pool/manifest.json` 与 `pool/problem/manifest.json`），必须 import 复用，禁止重写慢副本；**复用前核对常量/维度/场景作用域与本问一致，不一致禁止复用**；结果与已有数值一致性核对。通用原语（`--list` 查条目）从 `pool/primitives.py` import（首次 `cp <技能根>/scripts/primitives.py pool/primitives.py`，`--manifest` 生成 `pool/manifest.json`）；单题条目见 `pool/problem/`。**写完/跑通后自查重复实现**：`python <技能根>/scripts/reuse_lint.py --scan --root <outputDir>` → 同形且同口径的改 import（重跑计算，固定种子数字不变），口径不同则写差异理由；改不完 → 返回 `NEEDS_REVISION` 让调度壳重跑本阶段。**import 路径口径**：`PYTHONPATH=<outputDir>/pool:<outputDir>`（或 `pc.bootstrap_sys_path()`）——直接 `python` 跑脚本时默认 `import primitives` 会失败，撞到先修路径、禁止内联抄代码。
- **重计算走探针池**：单次 >1s 的评估/扫描/敏感性实验写成 `probes/<角色>/<目的>.py` 并用 `probe_cache.py` 缓存（指纹含原语版本+输入+配置，命中秒回），结果登记 `probes/manifest.json`；**禁止每轮重写重算**（上次 run 同类脚本重写 53 份 / 231 次写入，单次重算白付约 25s）。
- 运行前探测可用加速（numba/joblib/cupy/torch，**可选**；缺失自动回退纯 numpy/scipy，绝不因依赖缺失 FAIL）。
- 重计算选型：向量化 → numba jit（纯循环核，禁 prange 内 linalg）→ joblib 并行（单任务 ≥20ms 的独立任务，n_jobs=min(核数,8)）→ GPU（大矩阵且驱动/库可用）。
- **单次求解/核验预算**：≤15 分钟**且** ≤8× 本问生产主体墙钟（取小）；**先估后跑**（估算式 + ≤30 s 标定片段见 `<技能根>/docs/performance.md` §6.1），预估超预算 → 按 **缩窗 → 减档 → 降精度** 固定顺序缩，禁止「先跑再看」；确实超时 → 如实记录（不伪造、不无限等待）。
- **阶梯/扫参/对拍类核验**：**逐档落盘**（`probe_cache.py` 的 `pc.checkpoint_put/get`，重跑自动跳过已完成档 ⇒ kill 不作废）+ 档间并行；窗长/档数变更回写 draft / `baseline-registry.md` 的预注册条目。
- **耗时留档**：results.json 增加 `perf: {wallTime_s, method, parallel, costEstimate_s, budget_s, tiers, shrink, notes}`（真实测量值），供 sanity 核验与论文如实披露。

## 产物

- `intermediates/q{id}/06-computation/results.json`（主产物）；可能含 `figures/`

## 完成标准

- results.json 全部为真实运行数字；求解器状态/约束残差/随机种子已记录
- baseline 同场完成（或按 registry 理由跳过并注明）
- 跑不通/不收敛 → FAIL 如实上报，不伪造
