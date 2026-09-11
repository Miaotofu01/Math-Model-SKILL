# 阶段模板 07：Sanity 数值门禁（sanity）

> 你是本小问的 sanity 核验 agent，本模板定义你要做的全部工作。

## 数字口径核查（与数值门禁并列）

- 运行 `python <技能根>/scripts/artifact_lint.py --root <outputDir>`（`<技能根>` 见 `_common.md` §2.7）：关键数字在产物中散落 ≥3 处即报口径分叉 → **优先整改报告末尾列出的高发文件**（收敛到 `q{id}/06-computation/results.json`，其余改锚点引用）；本轮无法全部收敛时，把残留项与理由写进 sanity-report.md（不阻塞本阶段）
- 核对 results.json 的 keyValues 是否覆盖本问全部结论数字；缺失 → 补登记（不新造数字）

## 性能与复用核查（不阻塞，只登记）

- 读本问 `06-computation/results.json` 的 `perf`（键清单见 `<技能根>/prompts/artifact-schemas.md` §1.1）：字段缺失 → warning（要求计算阶段补齐，不 FAIL）；`wallTime_s > 900`（15 分钟单次预算）**或 > 8× 本问生产主体墙钟**、`costEstimate_s` 缺失、或存在明显重算白付 → warning 写「原因 + 影响 + 建议」；确为嵌套核验（阶梯/扫参）时额外核对 `tiers` 是否逐档落盘与并行（未落盘 ⇒ 记「中断即全废」风险，规则见 `docs/performance.md` §6.1）
- 核对 `probes/manifest.json`：同一用途/输入的实验是否被重复跑（应命中缓存秒回）→ 重复计算记 warning
- **重复实现核验**：跑 `python <技能根>/scripts/reuse_lint.py --scan --root <outputDir> --json intermediates/q{id}/07-sanity/reuse-lint.json` → 把**重复组数 / 跨小问组数 / 权威份未登记数**写入 sanity-report.md 的「性能与复用」段（复用率在 run 内唯一可读的数字）；权威份未登记 → 补登记；跨小问重复 → 记 warning 并转入 11 阶段整改清单（**不回改历史小问代码**）
- **池登记完整性**：`artifact_lint.py` 的「池登记」段会报 `pool/*.py`、`probes/*.py` 未登记或幽灵条目 → 未登记的**立即补登记**（探针重跑一次即自动登记；题专用核心手写 `pool/problem/manifest.json`），否则后问看不见、必然重写
- 结论写进 sanity-report.md 的「性能与复用」段；**本段只登记不 FAIL**（性能是技术债，不是数值门禁）

## 数值硬门禁（AutoMM 核心纪律，最高优先级）

**以下任一情况 → 必须返回 FAIL，不允许带病前进：**

1. **NaN/Inf**：结果出现非有限数值
2. **硬约束违反**：题面或方案中的硬约束（等式/不等式/取值范围）被违反
3. **单位/维度错误**：量纲分析或单位换算错误
4. **公式与实现不一致**：draft.md 公式与代码实现不符
5. **原始数据被修改**：输入数据文件被计算过程改动
6. **追踪缺失**：求解器状态、约束残差、随机种子未记录，结果不可审计

**非关键技术债（mip_gap 缺失、达到时限、求解器警告等）→ 不阻塞，但必须 PASS_WITH_WARNING 并记录在案**：state.json 的 gates 写 `PASS_WITH_WARNING`，返回 status 同为 `PASS_WITH_WARNING`，sanity-report.md 的 warning 段逐条登记（原因 + 影响 + 建议）。

> 工具纪律（减回合）：输入（results/draft/symbols/题面）一次并列 Read；六门禁核验用一次脚本批量跑完，不逐门禁往返。

> 公共纪律见 `_common.md`（壳与模板一并注入）。

## 输入

- `intermediates/q{id}/06-computation/results.json`：待核验结果
- `intermediates/q{id}/04-formulation/draft.md` 与 `symbols.json`：公式与符号基准
- `intermediates/00-problem.json`：题面（problem.description，硬约束出处）
- `intermediates/q{id}/04-formulation/handoff.md`：**交本阶段的检验项**（逐条核验是否已由 06 执行并留痕）
- `intermediates/q{id}/04-formulation/verification.md`：04 侧已核验项与证据键（**避免重算**；本阶段结论与它冲突时以实测为准并记入报告）
- `intermediates/q{id}/04-formulation/errata.md`：作废口径与未决项（核验时按它排除已作废结论）

## 执行步骤（逐门禁核验，每条结论必须带证据）

1. **数值检查**：扫描 results.json 全部数值 → NaN/Inf/量级异常
2. **硬约束检查**：从 00-problem.json 的 problem.description 与 draft.md 提取硬约束清单，逐条对照结果（如占比之和=1、概率∈[0,1]、厚度>0）
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
