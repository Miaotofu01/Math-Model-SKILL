# 优秀论文结构蒸馏 → skill 改造依据（2026-09）

> 来源：`/home/tofu/文档/数学建模/训练` 下 2022/2023/2024 三年 6 篇优秀论文
> （2022 A001/B035、2023 A175/C228、2024 A 国一/C038），覆盖机理题 / 物理优化题 / 数据题。
> 本文记录"优秀论文有什么、当前 pipeline 缺什么"的蒸馏结论，以及 v2.5 的改法。

## 一、优秀论文共性章节骨架

| 章节 | 出现情况 | v2.4 及以前 | v2.5 |
|---|---|---|---|
| 摘要（按子问题分段 + 加粗答案） | 6/6 | ✅ | ✅ |
| 问题重述（背景+已知+目标） | 6/6 | ✅ | ✅ |
| **问题分析（逐问机理→难点→思路草图→数据要点）** | 6/6 | ❌ 压进"重述"一句话 | ✅ 独立章 + Phase 4.0 agent |
| 模型假设 + 符号说明表 | 6/6 | ✅ | ✅ |
| 模型准备（坐标系/定义过渡） | 机理题 | ⚠️ 无 | 模型章 prompt 增加"模型准备"小节 |
| **数据预处理 / 探索性分析（整章，数据题）** | 数据题 2/2 | ❌ 只在求解时读数据 | ✅ 独立章 + Phase 4.0b EDA agent |
| 模型建立与求解（逐问） | 6/6 | ✅ | ✅ |
| **模型检验 / 灵敏度 / 稳健性分析（独立章）** | 6/6 | ⚠️ 只是验证器 1 个维度 | ✅ 独立章 + 稳健性报告 agent + statistical 验证维度 |
| **模型的评价与推广（优点/缺点/推广）** | 6/6 | ⚠️ 揉进"分析+结论" | ✅ 独立章 |
| 参考文献 + 附录（大表/代码） | 6/6 | ✅ | ✅ |

## 二、两类蒸馏发现

### A. agent 自己能想到、不用强调的（v2.5 未加大投入，保持现状）
- 图表命名规范 / CJK 字体配置：agent 天然会做，保留精简模板即可。
- 子问题分段「对于问题N」：agent 天然按子问题组织，不需要再加码。
- 创新必要性阈值机制（3 角度提案 + 评审团）：**保守保留**（用户决策），只在 prompt 内压缩表述。
- 数字溯源 / 代码对账：核心价值，非论文内容缺口，保持。

### B. 优秀论文有、当前项目做不出来的（v2.5 已补）
1. **问题分析章**：6/6 论文的标准第 2 章，是审题→建模之间的桥（2024 A 国一论文全靠 2.1~2.5 的逐问机理预演赢）。
2. **数据预处理 + 探索性分析整章**：数据题论文的建模选择是**数据探索驱动**的（FP-Growth→联合定价、ACF→时序分解）；
   旧 pipeline 由"文献+Gap"驱动、数据只在求解被读入 → 建模"凭空设计"。
3. **模型检验/灵敏度/稳健性成章**：优秀论文多方法 + 扰动表 + 明确结论（鲁棒优化/动态调参/加噪检验）。
4. **模型评价与推广章**：优点（量化依据）/缺点（诚实）/推广（迁移场景）6/6 都有。

### C. 战略发现（v3 方向，尚未实施）
2024 A 国一论文**没有文献调研、没有 baseline、没有"创新点"**——纯机理推导 + 逐问分析 + 清晰写作。
当前 skill 对 A 题（机理题）算力错配。后续（P3 分流层）按 `problemType`（机理/数据/优化/仿真）调整各 phase 权重。

## 三、v2.5 改动清单

| 文件 | 改动 |
|---|---|
| `workflows/math-model.js` | ① writing `full` preset 新增 4 章（问题分析/数据预处理与探索性分析/灵敏度与稳健性分析/模型的评价与推广），无附件时自动跳过 data_analysis；② 上下文裁剪与优先级接入 `problemAnalysis/edaReport/robustnessReport`；③ Phase 4.0 问题分析 agent + 4.0b EDA agent（清洗/统计检验/EDA 图/数据发现报告）注入建模上下文；④ 验证新增 `statistical` 维度（6 维度）；⑤ 稳健性报告 agent（聚合灵敏度/边界/统计/对抗发现）；⑥ 图表排版规范支持 `fig_eda_*`；⑦ 交叉审查质量门扩展（逐问覆盖到问题分析章）；⑧ checkpoint 持久化新字段 |
| `templates/assemble_from_template.py` | order 增加 4 个新章节名；修复 Python<3.12 的 f-string 反斜杠语法错误（预存 bug，会导致组装直接失败） |
| `SKILL.md` / `SKILL.claude.md` | Quick Reference、写作规范（新增 4 条）、创新链条、输出目录结构 |
| `README.md` | 功能亮点新增"对齐国一论文结构" |

## 四、验证计划（P5，待执行）
用 2023 C 题（数据）、2024 A 题（机理）、2023 A 题（物理优化）各跑一次 quick 模式，
对照上表检查：是否产出 4 个新章节、问题分析是否逐问、EDA 是否驱动建模选择、稳健性章是否有扰动表与明确结论。

---

## 五、工作流审计与优化（2026-09，v2.6）

对照真实运行产物（`math-model-output/`）审计全流程，发现并修复 5 类问题：

### 超限根因（全部修复）
1. **`selectContextForSection` 死代码**：按章节裁剪上下文的函数写了但从未接线 → 每个写作 agent 拿满 100k 字符预算。
   修复：改为 `SECTION_KEY_NEEDS`（每章只需的 key）+ `SECTION_BUDGETS`（模型章 40k/其余 25k）+ `buildSectionContext` 真正接入 writeOne。
2. **题目原文/数据画像/论文规则双份注入**：`problem` JSON 内嵌 `_rawDescription/_dataProfile/_paperRules`，又被 WRITING_PRIORITY 单独注入。
   修复：`problemForWriting` 剥离 `_raw*` 字段。
3. **`contextBudget=100000` 过大**（中文 1 字符≈1-2 token → 50-100k tokens）→ 降到 30000。
4. **`summarizeLongFields` 首次不截断**（第一个 writer 拿到全部长字段原文）→ 改为恒摘要 + `fullKeys` 白名单（rawDescription/finalModel/solution/edaReport/robustnessReport/problemAnalysis/dataProfile/paperRules 保留全文，由 budget 兜底）。
5. **`solution` 全量进写作上下文**（含完整源码，30-40k 字符）→ 裁剪为 {summary, keyValues, plots, concerns}。
6. **phase7 checkpoint 200k 字符经 LLM 读写** → 改为 tiny marker（writingDone+sectionIds），phase8 从磁盘 `05-writing/section-*.json` 重建；`saveCheckpoint` 加 40k 字符门禁。
7. **求解迭代 2+ 每轮重发全文** → impl 只在 iteration 1 带题目原文/数据画像，finalModel 迭代 2+ 截断到 8k。
8. **phase8 bodyText 60k/30k/20k** → 降到 30k/20k/15k/25k。

### 数据流断裂（修复）
- **求解/验证阶段拿不到 EDA 报告**（上轮 P2 引入）→ `edaCtx` 注入 algo(iter1)/impl/baseline，`edaCtxVerifiers`（2.5k）注入全部 6 个验证 agent；模型章上下文也加入 edaReport。

### 不必要环节（优化）
- **3 角度并行提案 + 综合（3-4 个 agent）→ 单一建模方案 agent**：三维自查（方法/模型/求解）内化进 prompt，评审团不变。省 3-4 个 agent + 消除提案上下文重复。

### checkpoint 瘦身（各 phase extractData）
- phase3：allSources 从全量抓取内容 → 只留 6 条 {url,title,quality}（曾 319k）；models/claims 截断 10/15。
- phase4：提案/评审只留摘要与计数；保留 finalModel/problemAnalysis/edaReport。
- phase5_6：allIssues 截 top 40、对抗/反思/重设计截近期（曾 127k）。
- phase7：不存全文（曾 200k），改磁盘重建。

