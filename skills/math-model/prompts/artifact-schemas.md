# 产物 schema 契约（results.json / figure-manifest.md）

> **本文件是写入者与读者的唯一契约**：字段名与结构只在此定义；各阶段模板只写"本阶段的写入要求"与指针。
> 读者：`phase-06`（写 §1）、`phase-07`（核验 §1.1）、`phase-08`（写 §2）、`phase-10`（核验 §1.2/§2）、`phase-11/12/13`（引用数值与图）。

## 1. `intermediates/q{id}/06-computation/results.json`（写入者：阶段 06）

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

**字段口径**：

- `results`：按本问各分点组织，summary 必须含具体数值；keyValues 含关键中间值（可审计）
- `solver`：求解器状态/迭代数；MILP 求解器给出 mip_gap；约束残差（硬约束违反量）；达时限标记
- `seeds`：固定并记录全部随机种子；未固定 → 如实记录缺失（sanity 阶段核验）
- `baselineComparison`：≥3 个对比维度（精度/效率/稳定性等）；每指标给 baseline 值、improved 值、improvement 百分比、isLowerIsBetter；summary 一句话总结提升；significance 显著程度；weaknessExposed 诚实写弱点
- 代码含绘图语句 → 图保存到 `intermediates/q{id}/06-computation/figures/`（结果图原始输出，可视化阶段复用/重画），本阶段不要求出图

### 1.1 `perf`（阶段 06 写、阶段 07 核验）

`perf: {wallTime_s, method, parallel, costEstimate_s, budget_s, tiers, shrink, notes}` —— 真实测量值；`costEstimate_s/budget_s/tiers/shrink` 见 `docs/performance.md` §6.1。

### 1.2 阶段 10 的必需字段断言

`runs`（含 finalScript）／`results`（非空，summary 含具体数值）／`solver`／`seeds`（标明是否固定）四项齐备，缺一即门禁 FAIL。

## 2. `figure-manifest.md`（写入者：阶段 02 = EDA 图、阶段 08 = 结果图/示意图）

每张图一行：`文件名 | 类型 | 作用 | 来源（results.json 键或探针键） | 绘图方式（diagram-design|matplotlib） | 引用位点`；文档末尾「自检」一节记录 lint 结果 + 视觉复核缺陷与处置。
**反向校验（P0）**：每条引用必须对应真实存在的图文件；空 figure 环境一律 P0。
读者：阶段 10（核验 2 项）、阶段 12（据 manifest 引用，不得靠 `ls`）、阶段 13（图文一致）。
