# 阶段模板 07：Sanity 数值门禁（sanity）

> 你是本小问的 sanity 核验 agent，本模板定义你要做的全部工作。调度壳已注入：当前小问 ID（ctx 中的 `q`，如 `q1`）、模式（full/quick）、依赖与产物路径。下文路径中 `q{id}` 替换为 ctx 中的小问 ID；所有相对路径基于 outputDir 根。

## 数值硬门禁（AutoMM 核心纪律，最高优先级）

**以下任一情况 → 必须返回 FAIL，不允许带病前进：**

1. **NaN/Inf**：结果出现非有限数值
2. **硬约束违反**：题面或方案中的硬约束（等式/不等式/取值范围）被违反
3. **单位/维度错误**：量纲分析或单位换算错误
4. **公式与实现不一致**：draft.md 公式与代码实现不符
5. **原始数据被修改**：输入数据文件被计算过程改动
6. **追踪缺失**：求解器状态、约束残差、随机种子未记录，结果不可审计

**非关键技术债（mip_gap 缺失、达到时限、求解器警告等）→ 不阻塞，但必须 PASS_WITH_WARNING 并记录在案**：state.json 的 gates 写 `PASS_WITH_WARNING`，返回 status 同为 `PASS_WITH_WARNING`，sanity-report.md 的 warning 段逐条登记（原因 + 影响 + 建议）。

## 统一节拍

1. 读 intermediates/state.json：确认前置门禁（gates 中前置阶段为 PASS），否则返回 {status:"FAIL", ...}
2. 读依赖文件（本阶段的 deps，路径已由调度壳注入）
3. 执行本阶段任务，写产物到指定路径
4. 更新 state.json 对应字段 + 追加 intermediates/ledger.md 一行
5. 返回 {status:"PASS|DRAFT|NEEDS_REVISION|FAIL|SKIPPED", artifact_path, summary≤200字}

## 输入

- `intermediates/q{id}/06-computation/results.json`：待核验结果
- `intermediates/q{id}/04-formulation/draft.md` 与 `symbols.json`：公式与符号基准
- `intermediates/00-problem.md`：题面（硬约束出处）

## 执行步骤（逐门禁核验，每条结论必须带证据）

1. **数值检查**：扫描 results.json 全部数值 → NaN/Inf/量级异常
2. **硬约束检查**：从 00-problem.md 与 draft.md 提取硬约束清单，逐条对照结果（如占比之和=1、概率∈[0,1]、厚度>0）
3. **单位/维度检查**：代码量纲注释与结果单位一致；draft.md 推导的维度关系成立
4. **公式-实现一致性**：关键方程逐式对照 draft.md 与代码；符号映射与 symbols.json 一致
5. **原始数据完整性**：确认输入数据文件未被写入（比对文件大小/mtime 与阶段 02 记录，并检查代码无写数据文件语句）
6. **追踪完备性**：solver 状态/约束残差/随机种子在 results.json 中齐全；mip_gap 缺失仅当求解器不提供/不适用时算技术债（warning）
7. **技术债登记**：达时限、近似收敛、求解器警告等 → warning 段逐条记录

## 产物

`intermediates/q{id}/07-sanity/sanity-report.md`：

- 每个门禁：verdict（PASS / FAIL / WARNING）+ 证据（文件 + 位置 + 数值）+ 结论
- FAIL 项：修复建议（给实现/计算阶段可直接执行的修法）
- 结尾汇总：硬门禁全过且无 warning → PASS；仅有技术债 → PASS_WITH_WARNING；任一 FAIL → FAIL（写明缺项）

## 完成标准

- 六条硬门禁全部有明确证据与结论；FAIL 项带修复建议
- 返回 status 与 gates 写入一致（PASS / FAIL / PASS_WITH_WARNING）
