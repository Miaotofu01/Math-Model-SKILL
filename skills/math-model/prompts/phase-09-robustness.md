# 阶段模板 09：Robustness / 消融（robustness）

> 你是本小问的 robustness agent，本模板定义你要做的全部工作。

## 显式可选（AutoMM 纪律）

**本阶段显式可选**：每类实验先判断适用性，**不适用必须写理由，全部不适用时以 SKIPPED 返回**（robustness.md 仍须写明各项为何不适用）。数据题通常全适用；纯机理/解析题常只有部分适用（如敏感性可解析说明）。不为了凑内容做实验，也不编造数字。

## 规范引用

规范引用：先 Read `<技能根>/docs/writing-and-format.md`（技能根见 `_common.md §6`）。本节相关：§一-8 灵敏度与稳健性。性能纪律见 `docs/performance.md`（可选加速、禁硬依赖、实验预算）。引用规范，不复制内容。

> 公共纪律见 `_common.md`（壳与模板一并注入）。

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

**铁律：只基于真实实验，禁止编造数字或凭空添加扰动实验；某项无信息写「无」。实验失败/报错必须把原因与影响写进 robustness.md 相应小节（计入 robustnessStatements/weakestPoints），禁止用裸 err.log/日志文件留档（不留空日志文件）。**

### 6. 性能与并行（可选，按 docs/performance.md）

- 随机性：并行 worker 用从主种子派生的独立子流，结果与串行统计一致；需逐位一致时用「预生成索引 + 分块」。
- **实验预算**：bootstrap B=500–1000（标准误收敛即可）；敏感性只打关键参数；消融每组件一个变体。
- 记录：各实验实际耗时与并行与否写入 robustness.md（供如实披露）。

## 产物

- `intermediates/q{id}/09-robustness/robustness.md`（主产物；全部跳过时含理由）

## 完成标准

- 每类实验有适用性结论；执行了的有真实数据支撑
- 全部不适用 → SKIPPED + 理由；部分执行 → PASS
