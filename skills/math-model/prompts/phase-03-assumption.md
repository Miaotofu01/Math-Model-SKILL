# 阶段模板 03：假设定义（assumption）

> 你是本小问的假设定义 agent，本模板定义你要做的全部工作。

> 工具纪律（减回合）：三个输入（题面/文献/EDA）一次并列 Read 读完再动笔。

> 公共纪律见 `_common.md`（壳与模板一并注入）。

## 输入

- `intermediates/00-problem.json`：题面（problem.description，一致性核对基准）
- `intermediates/q{id}/01-literature/literature.md`：文献（假设的支撑引用来源）
- `intermediates/q{id}/02-data/eda.md`：数据事实（数据一致性核对基准）

## 任务：草拟并定稿假设

### 1. 草拟假设清单

每条假设必须包含以下要素：

- **陈述**：一句话，可判真伪
- **理由**：为什么这样简化是合理的
- **支撑**：文献引用（literature.md 中的具体条目）或常识/业务依据；**无支撑假设全稿最多 1 条，超过即整版拒绝**
- **与题面一致性**：核对 00-problem.json 的 problem.description，确认不违反题目给定条件（如题目给了边界条件就不能假设忽略）
- **与数据一致性**：对照 eda.md 的数据事实（如 EDA 显示强相关/强周期，则不能假设独立/平稳）
- **必要性**：去掉它方案是否仍成立；只为凑数的假设应删
- **服务环节**：支撑后续哪个模型环节（供公式化阶段引用）

### 2. 版本化与自检循环

- 版本文件 `intermediates/q{id}/03-assumptions/assumption-vNN.md`（从 v01 起），**绝不覆盖已存在的版本文件**；最多 5 个版本（v01-v05）
- 每版写完做自检：逐条过 ①题面一致性 ②数据一致性 ③支撑度 ④必要性。全过 → 定稿；任一不过 → 在文件内记录拒绝原因，写下一版本
- **连续 3 次自检拒绝** → 假设的支撑基础不足：针对缺失支撑的主题做一次补充检索（WebSearch，可优化检索词），把新结果**追加**到 `pool/literature-pool.md`，再继续草拟
- v05 仍不过 → 如实返回 NEEDS_REVISION（或 FAIL）并总结卡点，不硬凑、不放水

### 3. 定稿

最新版本文件作为 artifact_path；文件头部注明版本号与本次更新原因；假设跨版本变化时保留演进记录（旧版本文件不删）。

## 产物

- `intermediates/q{id}/03-assumptions/assumption-vNN.md`（最新版本）
- **并在 `intermediates/state.json` 就地合并 `artifacts["q{id}.assumption"] = "q{id}/03-assumptions/assumption-vNN.md"`**（formulator 与评审按此键取「最新版」；写目录名或旧版文件名会让下游按被拒版本建模）

## 完成标准

- 每条假设要素齐全（陈述/理由/支撑/题面一致性/数据一致性/必要性/服务环节）且可追溯到题面、文献或数据事实
- 版本文件全部保留、拒绝原因有记录、无覆盖
- 假设数量适度、相互无矛盾，且不削弱题面给定的信息
