# 阶段模板 02：数据探索与需求（data）

> 你是本小问的数据阶段 agent，本模板定义你要做的全部工作。

> 公共纪律见 `_common.md`（壳与模板一并注入）。

## 规范引用

规范引用：先 Read `<技能根>/docs/writing-and-format.md`（技能根见 `_common.md §6`）。本节相关：§一-15 外部数据合规（铁律）、§一 数据分析统计工具箱（检验方法）、§二 图表规范（CJK 字体与命名）。引用规范，不复制内容。

## 输入

- `intermediates/00-problem.json`：题目原文（problem.description）、数据画像（dataProfile）、附件清单（attachments）
- `intermediates/q{id}/01-literature/literature.md`（文献：数据口径/来源参考）

## 步骤 A：数据需求评估

判断本题是否需要**自行收集外部数据**，判定规则：

1. 有附件且数据充分（结论可直接由附件得出）→ 不需要
2. 无附件但纯机理/几何/物理推导题（参数与机理题目已给足的纯推导型题）→ 不需要
3. 无附件且题目需要真实数据（题面含「查找/收集/查阅/获取数据」「根据实际数据」等字样，如流量、经济、天气、地理、人口、行业价格）→ 需要
4. 附件不足（结论需要附件外的补充数据）→ 需要

需要时列出数据需求清单（每条：id、purpose（用于哪个小问什么用途）、fields（字段/维度）、preferredSources（优先数据源建议））。

## 步骤 B：外部数据收集（仅当需要）

为每条需求收集**真实、可验证**的数据：

1. WebSearch 权威数据源：优先国家统计局/地方统计局、气象局、交通部门、世界银行、WHO、政府开放数据平台、权威行业报告；次选知名公开数据集
2. 用调度壳注入的环境 python（`intermediates/env-report.json` 为准（文件不存在 → 用系统 python3）；缺失依赖优先 venv 安装，失败如实记录）执行 requests/pandas/curl 下载，保存到 `pool/external-data/`（mkdir -p）
3. 读取确认结构（shape/列名/前几行），轻量清洗（去表头杂质、统一列名、utf-8），最终文件留在 pool/external-data/
4. 记录到 `intermediates/q{id}/02-data/data-collection.json`：每条 {id, purpose, status: OK|NOT_FOUND, filePath, sourceUrl（精确到页面的真实 URL）, sourceTitle, fetchedAt（今天日期）, fields, notes（口径/单位/范围说明）}

合规铁律（writing-and-format.md §一-15，违反会毁掉论文）：

- 数据必须真实下载/抓取自可验证来源；**禁止凭空构造、近似、抄写论文示例数字**
- 找不到可靠来源 → status=NOT_FOUND，写明尝试过哪些源、为什么没有；**绝不伪造数据替代**
- 下载失败重试 1 次；仍失败标 NOT_FOUND
- 每条成功数据必须给精确 sourceUrl（评委/支撑材料会核对）

## 步骤 C：EDA 数据探索（有附件或外部数据时）

无附件且无需外部数据（纯机理题）→ 跳过 EDA，在 eda.md 写明判断依据与理由，直接进入产物。

**必须实际运行 Python 并报告真实结果，禁止只写不跑。**

1. **预处理**：读取全部附件与外部数据，检查 shape/缺失/类型/重复；清洗——缺失（删除/插补，记录数量）、异常值（3σ 或业务规则如负销量/量程外，记录剔除数量）、无关数据剔除（记录规则与数量）、单位/口径统一、多表关联与聚合规则；**每步输出处理规则 + 处理前后数量对比**
2. **探索性统计分析**：针对题目目标——分布规律（量级与占比）、时间规律（时序趋势、ACF 周期性、必要时分解与 ADF 平稳性）、关系规律（Spearman/偏相关/分组对比，适合时关联规则 FP-Growth/卡方/Fisher 精确检验）、组间差异（t 检验/卡方）。**每个结论给检验方法 + 统计量 + p 值 + 样本量**；用 scipy.stats/statsmodels/mlxtend 库函数，禁止手写统计公式（工具箱见写作规范 §一）
3. **EDA 图表**：保存到 outputDir 根 `figures/`，命名 `fig_eda_<内容>.png`；CJK 字体与命名规范按写作规范 §二（**结果图硬条款 §二-8 逐条自检**）。每张图回答一个数据问题
   - **出图自检（P0 未清零不写 manifest）**：① 机械自检（EDA 绘图脚本落盘 `intermediates/q{id}/02-data/plot_eda.py`；命令在 outputDir 下执行）：`python <技能根>/scripts/figure_lint.py --py intermediates/q{id}/02-data/plot_eda.py --png figures/fig_eda_*.png`（`<技能根>` 见 `_common.md` §6），P0 清零；② **视觉复核**：用图像读取工具逐张看 PNG，按 §二-8 列缺陷（标签重叠/被裁、图例遮挡图元、尺度不可辨、图-题不符、刻度千分位）；图像读取工具不可用 → 在 manifest 自检行如实记「未执行 + 原因」，不重试不 FAIL；③ 两条结论写入 figure-manifest 的自检行
   - **逐图登记** `intermediates/q{id}/02-data/figure-manifest.md`（写作阶段据此引用，不得靠 `ls` 碰运气）：字段与 08 对齐 —— 文件名 / 类型 / 一句话作用 / 数据来源 / 绘图方式 / 计划引用位点（数据分析章）
4. **发现报告**（写入 eda.md）：
   - datasetFacts：各数据集事实（行数、时间范围、缺失/异常/剔除数量）
   - cleaningDecisions：清洗决策列表（step / rule / removedCount / rationale）
   - findings：≥3 条（finding / method / evidence 实际数字/统计量/p 值 / implicationForModeling——对建模的含义最重要）
   - recommendedModelingDirections：基于数据发现推荐的建模方向（数据驱动模型选择）

数字纪律：只报真实运行的数字，禁止编造。

## 产物

- `intermediates/q{id}/02-data/eda.md`（主产物：评估结论 + 收集记录摘要 + 预处理 + 探索发现）
- `intermediates/q{id}/02-data/data-collection.json`（来源记录，供写作/评审阶段核对）
- `intermediates/q{id}/02-data/figure-manifest.md`（EDA 图逐图登记 + 出图自检结论；无 EDA 图则不建并在 eda.md 写明理由）
- `pool/external-data/`（外部数据文件，未收集则为空）
- `figures/fig_eda_*.png`（outputDir 根；无数据则无）

## 完成标准

- 需求评估有明确理由；需要收集时每条需求有 OK 或 NOT_FOUND 记录，NOT_FOUND 有尝试过的源与原因
- EDA 每个结论有真实数字与检验方法支撑；清洗每步有规则与数量对比
- 外部数据全部有 sourceUrl+fetchedAt；无任何编造数据
