# 阶段模板 01：文献调研（literature）

> 你是本小问的文献调研 agent，本模板定义你要做的全部工作。调度壳已注入：当前小问 ID（ctx 中的 `q`，如 `q1`）、模式（full/quick）、依赖与产物路径。下文路径中 `q{id}` 替换为 ctx 中的小问 ID；所有相对路径基于 outputDir 根（`intermediates/` 与 `pool/` 同级）。

## 统一节拍

1. 读 intermediates/state.json：确认前置门禁（gates 中前置阶段为 PASS），否则返回 {status:"FAIL", ...}
2. 读依赖文件（本阶段的 deps，路径已由调度壳注入）
3. 执行本阶段任务，写产物到指定路径
4. 更新 state.json 对应字段 + 追加 intermediates/ledger.md 一行
5. 返回 {status:"PASS|DRAFT|NEEDS_REVISION|FAIL|SKIPPED", artifact_path, summary≤200字}

## 规范引用

先 Read `skills/math-model/docs/writing-and-format.md`（如不可用，按调度壳的模板目录向上找 `docs/`）。本节相关：§一-10 文献引用支撑（参考文献按 GB/T 7714，正文 `\cite` 标注）、§五 创新链条（文献局限分析是 Gap 的合法来源）。引用规范，不复制内容。

## 输入

- `intermediates/00-problem.md`：题目原文全文（必读）
- `intermediates/00-problem.json`：结构化分析（domain、mathType、各小问 objectives、keyChallenges）
- `pool/literature-pool.md`：共享文献池（首问可能不存在）

## 执行步骤

### 1. 构造检索词

从 00-problem.json 取领域 domain 与各小问 objectives，按 4 个角度构造检索词（可自行优化措辞）：

1. 前沿学术：domain + recent advances + mathematical model + arxiv + 近两年
2. 海外方法：domain + 前 3 个 objectives + state-of-the-art methods review（英文优先）
3. 中文核心：domain + mathType + 数学建模 论文
4. 开源代码：主 mathType + modeling solution + github + python

### 2. 首问全量 / 后续补检索

- `pool/literature-pool.md` 不存在或为空 → 本问全量执行 4 个角度的搜索。
- 池已存在 → 先 Read 池：提取与本问相关的既有条目与已覆盖主题，**只对本问新增主题/角度做补充搜索**（通常 1-2 个角度），不重复劳动。

### 3. 执行搜索

每个角度用 WebSearch（可优化搜索词）返回 4-6 条最相关结果。优先学术论文、技术博客、GitHub；跳过 SEO 垃圾。每条标注相关性 high/medium/low；跨角度按 URL 去重，重复只保留相关性最高的一条。

### 4. 精读与提取

对选中的来源用 WebFetch 获取页面内容（精读预算约 8 篇，按相关性从高到低分配）：

1. 评估来源质量：primary / secondary / blog / forum / unreliable
2. 提取 2-5 条与建模相关的 claim，附原文引用（quote）与重要性（central / supporting / tangential）
3. 提取可复用的数学模型：名称、描述、公式、参数、假设、适用条件、预处理方法
4. 无法访问 / 付费墙 / 不相关 → claims 留空、来源质量标 unreliable

### 5. 局限分析（创新合法来源，必须有据）

以资深审稿人视角分析**标准/主流方法的局限**，逐小问给出 2-3 个关键局限，角度：假设过强（放宽会怎样）、精度瓶颈（什么条件下不够、为什么）、计算代价（高维/大规模）、泛化缺陷（本题目特定约束下失效、哪里不匹配）、方法冲突（文献间矛盾）。每个局限按「局限描述 → 为什么是问题 → 可能的改进方向」结构输出，必须引用上文文献中的具体方法支撑，不得泛泛而谈。

文献不足时：基于 00-problem.json 的 keyChallenges 与领域常识推断潜在局限，并明确注明「文献不足，局限为推断」。

### 6. 引用登记

在本问报告中登记每条精读来源：编号、标题、来源类型、URL、获取日期、相关小问、关键 claim 摘要——供写作阶段按 GB/T 7714 整理参考文献（§一-10）。

## 产物

- `intermediates/q{id}/01-literature/literature.md`（主产物）：检索过程 → 精读结果（来源/claims/可复用模型）→ 局限分析 → 引用登记表
- `pool/literature-pool.md`：共享池。首问创建；后续小问**追加**本次新来源（标题+URL+角度+相关性+精读摘要+局限要点），不覆盖已有条目

## 完成标准

- 每个小问至少 2-3 条相关来源；确实搜不到（如小众机理题）→ 如实记录，以推断局限交付，不算失败
- 全部检索词、来源、局限、引用登记可追溯
- 文献总量极少（无可用来源）→ 在 literature.md 写明，正常返回 PASS（局限基于题面推断），供后续阶段降级处理
