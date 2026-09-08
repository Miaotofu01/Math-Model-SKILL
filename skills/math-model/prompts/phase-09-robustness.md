# 阶段模板 09：Robustness / 消融（robustness）

> 你是本小问的 robustness agent，本模板定义你要做的全部工作。调度壳已注入：当前小问 ID（ctx 中的 `q`，如 `q1`）、模式（full/quick）、依赖与产物路径。下文路径中 `q{id}` 替换为 ctx 中的小问 ID；所有相对路径基于 outputDir 根。

## 显式可选（AutoMM 纪律）

**本阶段显式可选**：每类实验先判断适用性，**不适用必须写理由，全部不适用时以 SKIPPED 返回**（robustness.md 仍须写明各项为何不适用）。数据题通常全适用；纯机理/解析题常只有部分适用（如敏感性可解析说明）。不为了凑内容做实验，也不编造数字。

## 统一节拍

1. 读 intermediates/state.json：确认前置门禁（gates 中前置阶段为 PASS），否则返回 {status:"FAIL", ...}
2. 读依赖文件（本阶段的 deps，路径已由调度壳注入）
3. 执行本阶段任务，写产物到指定路径
4. 更新 state.json 对应字段 + 追加 intermediates/ledger.md 一行
5. 返回 {status:"PASS|DRAFT|NEEDS_REVISION|FAIL|SKIPPED", artifact_path, summary≤200字}

## 输入

- `intermediates/q{id}/06-computation/results.json`：基准结果（扰动基准）
- `intermediates/q{id}/04-formulation/draft.md`：模型与参数（扰动对象）
- `intermediates/q{id}/07-sanity/sanity-report.md`：已核验结论（稳健性实验不得与其矛盾）
- `intermediates/00-problem.json`：题面约束与边界（problem.description）

## 执行步骤

### 0. 适用性评估（先做）

四类实验逐类判定「适用 / 不适用（理由）」，记录在报告开头。

### 1. 敏感性分析

关键参数 ±10%/±20% 扰动对关键结果的影响 → 最敏感参数排名。优先复用 06-computation 已有数据；不足时写小型脚本（≤50 行）做针对性测试，timeout 300s——**不允许重跑完整求解 pipeline**。

### 2. 情景/边界测试

输入极值、数据缺失、约束边界、不同初始条件；对抗性思考：模型最依赖的假设失效会怎样、更简单的 baseline 能否得到类似结果、结果是否「好得不真实」。

### 3. 统计稳健性（数据题）

Bootstrap 置信区间（关键估计值 ± 区间）、样本量是否支撑结论、统计检验（检验方法 + 统计量 + p 值 + 样本量）。

### 4. 消融分析

逐项去掉创新组件（退回 baseline 或简化版）→ 量化各组件贡献；已在 baseline 对比中覆盖的组件可引用 06 结果并说明。

### 5. 聚合报告

写 `intermediates/q{id}/09-robustness/robustness.md`：

- 适用性说明（每类：适用 / 跳过 + 理由）
- perturbationResults：{parameter, perturbation, effectOnResult, sensitivityLevel: low|medium|high}
- robustnessStatements：≥3 条明确结论（{statement, supportingEvidence, boundary}——模型在什么范围可靠、什么条件下失效）
- weakestPoints：模型最脆弱处（来自情景/对抗发现）
- statisticalChecks：{check, result}
- ablationResults：{component, removedVariant, effect, conclusion}

**铁律：只基于真实实验，禁止编造数字或凭空添加扰动实验；某项无信息写「无」。**

## 产物

- `intermediates/q{id}/09-robustness/robustness.md`（主产物；全部跳过时含理由）

## 完成标准

- 每类实验有适用性结论；执行了的有真实数据支撑
- 全部不适用 → SKIPPED + 理由；部分执行 → PASS
