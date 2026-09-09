# 阶段模板 06：计算（computation）

> 你是本小问的计算 agent，本模板定义你要做的全部工作。调度壳已注入：当前小问 ID（ctx 中的 `q`，如 `q1`）、模式（full/quick）、依赖与产物路径。下文路径中 `q{id}` 替换为 ctx 中的小问 ID；所有相对路径基于 outputDir 根。

## 统一节拍

1. 读 intermediates/state.json：确认前置门禁（gates 中前置阶段为 PASS），否则返回 {status:"FAIL", ...}
2. 读依赖文件（本阶段的 deps，路径已由调度壳注入）
3. 执行本阶段任务，写产物到指定路径
4. 更新 state.json 对应字段 + 追加 intermediates/ledger.md 一行
5. 返回 {status:"PASS|DRAFT|NEEDS_REVISION|FAIL|SKIPPED", artifact_path, summary≤200字}

## 规范引用

先 Read `skills/math-model/docs/writing-and-format.md`（如不可用，按调度壳的模板目录向上找 `docs/`）。本节相关：§二 图表生成规范（代码含绘图语句时按 §二-1/2/3/5 配置 CJK 字体与单位写法）。引用规范，不复制内容。

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
  "runs": {"finalScript": "solution_v2.py", "mode": "full"},
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
- 代码含绘图语句 → 图保存到 `intermediates/q{id}/06-computation/figures/`（结果图原始输出，可视化阶段复用/重画），本阶段不要求出图

## 产物

- `intermediates/q{id}/06-computation/results.json`（主产物）；可能含 `figures/`

## 完成标准

- results.json 全部为真实运行数字；求解器状态/约束残差/随机种子已记录
- baseline 同场完成（或按 registry 理由跳过并注明）
- 跑不通/不收敛 → FAIL 如实上报，不伪造
