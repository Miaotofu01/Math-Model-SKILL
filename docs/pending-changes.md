# 待实施改动（run 结束后统一实施）

> 建立：2026-09-10 ｜ 来源：2025 国赛 A 题 run 实测（性能与缓存、图表链、流程图与结果图质量、文献可信度）
> 触发：当前 run 跑完后统一改，中途不动 shell
> 证据脚本（`test/perf/scratch/`，gitignore 覆盖）：`final_stats.py`（阶段耗时）、`cache_analysis.py` / `cache_by_provider.py` / `cache_series.py`（缓存命中）、`collapse.py` / `gap_test.py`（缓存丢失判别）、`make_pie.py` + `run-pie.png`（消耗饼图）、`check_flowchart_spec.py` / `verify_final.py`（流程图核对）、`verify_lit2.py` + `literature-upgrade.md`（文献核验）

## 0. 实测基线（数据截至 09-10 12:04）

| 指标 | 数值 |
|---|---|
| 总墙钟 | 17.7h（q1 1.6h / q2 8.7h / q3 4.8h / q4 进行中） |
| agent 活跃总时长 | 20.9h（116 个子会话，2674 次模型调用） |
| 阶段耗时占比 | **建模评审循环 11.0h（52.5%）**、鲁棒 2.3h、实现 1.9h、数据 1.5h、计算 0.7h |
| token | fresh 33.1M、cacheRead 203.5M、output 4.2M，**全局命中 86.0%** |
| 会话级命中 | 长会话（implementation 111 次调用）95%；短会话（boot/gate，2–5 次）36–66%；中位 74.6% |
| 缓存丢失 | **200 次**（上下文 >40K、新增 <30KB、命中 <50%），重发 **12.0M tokens = 36% of fresh** |
| 重复读 | `read` 工具共 11.0MB，97% 被 ≥2 个会话读过，重复份数 9.2MB ≈ **2.6M tokens（8% of fresh）** |

**缓存丢失排除法结论**（勿重复排查）：TTL 无区分度（丢失时 gap 中位 12.4s vs 高命中 7.6s）、与 429 无关（邻近比例 0.0%）、会话内 `request/header` 恒定（每会话仅 1 条）→ 均排除；**成立的解释是上游前缀缓存块级淘汰**（56% 的丢失紧跟"前一次命中 ≥80%"的下一次调用）。P0（换 provider）已排除：provider 是用户按价格/性能主动选择的。

---

## 0. 评审与实施记录（2026-09-10 晚，赛前落实；本节为准，下游各节只保留证据）

用户决策：**不再等全量测试 run，先落实改进方案**。以下是「全文冲突/bug 评审」结论 + 实施结果。

### 0.1 阻断级 bug（已修，含证据）

| # | 缺陷 | 后果 | 修法 / 证据 |
|---|---|---|---|
| **B1** | 壳 `loadContracts` 的模板字面量里写了 Markdown 代码围栏（`不要 \`\`\`json`），反引号提前终止模板串 | **整个 `math-model.js` 语法错误**，任何一次启动都会在解析阶段直接失败（未提交改动引入） | 删掉围栏字样；`node --check` 对 body 无效（含顶层 return），改用干跑 harness 校验 |
| **B2** | `parseProblemsText` 只读顶层 `{problemId, questions}`，而 Stage 1 实际落盘是 `{selectedProblem, problem:{id, analysis:{subQuestions:[{id}]}}}` | **小问列表解析为空 → 只跑 q1，q2–q5 静默丢失**；problemId 记成 `unknown` → resume 永久失配（拒绝覆盖） | 兼容两形态解析（`selectedProblem/problem.id/problem.analysis.subQuestions[].id`）+ 解析不到时显式 `log` 告警；干跑 `--resume-mismatch` 验证失配保护仍生效 |

> 两个 bug 都在**赛前最后一次改动**里，靠新加的干跑 harness（`test/dryrun-shell.mjs`，桩 agent，无 LLM）当场抓到：full 模式 23 阶段、resume 模式跳已完成、失配模式拒绝覆盖，三模式全绿。

### 0.2 方案内部冲突与不可执行项（评审结论）

| # | 位置 | 问题 | 处置 |
|---|---|---|---|
| **C1** | §1.1 会话复用 | **不可实现**：workflow hook 只有 `agent/pipeline/parallel/phase/log/args`；每次 `agent()` 都是新子会话（`seq`/`childId` 每次递增、settle 即结束），脚本内没有 session 句柄、没有 `send_message`。要改只能改 DSH 本体 | §1.1 移入 §5「不可实现」；**连带 §5 对 §1.2 的否决理由（"draft 整读已被评审对话复用解决"）前提不成立** → §1.2 由「已否决」改回「待裁决」；本次赛前**不动评审循环**（风险 > 收益） |
| **C2** | §1.2 vs §5 | 同一 cluster 一处列为措施 1.2、一处列为"明确不做"，自相矛盾 | 同上，状态统一为「待裁决（阻塞于 C1）」 |
| **C3** | §1.3-3 图脚本条款 | 「图脚本不得出现数值字面量」**不可执行**：figsize/dpi/fontsize/线宽/坐标范围全是字面量，照写会全图报错 | 收窄为「**关键结果数值**不得硬编码，必须从 `results.json` 读取；样式/布局参数不受限」（已写入 `_common.md` §4 与 §二-8） |
| **C4** | §1.3-3 artifact-lint | 「≥3 处即报错」照字面实现会产出 **82 条 P0** 噪声：题面常量（1800/1440）被当关键数字、实现代码与原始输出天然含数字、探针脚本与 `review-r*.md` 本身就在引用数字 | 判据收敛为：真源数字**减去题面给定常量** → 只统计**下游消费的产物品**（白名单，排除 code/outputs/results/探针/评审意见/真源）→ 报 top-8 + 「优先整改文件」表；真实 run 复测：`17280` 命中 25 份产物（可执行规模） |
| **C5** | §2.1 | 「phase-02 增产物 `02-data/figure-manifest.md`（**或**统一登记到根 `figures/figure-manifest.md`）」二选一未定 | 定为**按问登记**（字段与 08 对齐）；根 `figures/` 不设独立 manifest，新增 §二-9「图文件路径口径（唯一，勿混）」表 |
| **C6** | §3.1/§3.2 | L1 同时被定义为「全文精读」和「社区复现」，与 §3.6 指标「权威源达 L1 ≥3」互相污染 | 明确 **L 只表示可得性**（L1 全文 / L2 摘要 / L3 元数据 / L4 不可验证），权威性另用来源性质标注（同行评审 / 预印本 / 社区复现 / 命题人·教学期刊） |
| **C7** | §1.3-4 | 「shell 扫描 pool/probes manifest 注入清单」依赖 §1.3-1/2（pool/ 暂缓），本次不建 manifest | 未实施；`_common.md` 只写"先看同目录/pool/core.py 既有实现"，不引用不存在的清单 |

### 0.3 本次实施清单

| 项 | 落点 |
|---|---|
| 提示词共享块外置（§1.3-7 采纳项） | 新建 `prompts/_common.md`（统一节拍/评审节拍/工具纪律/数字单一真源/复用/工具与文档路径/环境/不编造）；13 个 phase + 3 个 reviewer 删除重复块（**1024 → 946 行，98KB → 73.5KB**）；壳只在阶段/评审/修订节点要求并列读入 `_common.md`，并注入技能根 `SD`（微节点 finalize/gate/degrade 不读，避免短会话变贵） |
| 数字单一真源（§1.3-3 采纳项） | `_common.md` §4 + `phase-06`（results.json 唯一权威、keyValues 须覆盖全部结论数字）+ `phase-07/11/13` 调用 `scripts/artifact_lint.py`（新脚本，实测真实 run 输出可读报告） |
| 图表链（§2.1/2.2/2.3） | `docs/writing-and-format.md` 新增 §二-8 结果图硬条款 12 条 + §二-9 路径口径；`phase-02` 增 `figure-manifest.md` 产物与出图自检；`phase-08` 出图自检四步（规范逐条 / `figure_lint.py` 机械 / **视觉复核** / manifest 自检节）；`docs/flowchart-drawing.md` §0 路径唯一性（只用 vendored）+ §6 三道自检 |
| 文献层（§3.2–3.5） | `phase-01` 新增 §4b（L1–L4 分级 + 来源性质 + 取文回退链 + 接口踩坑 + 检索式偏好）与 §7（`lit_verify.py` 批量核验）；引用登记补 DOI/完整标题/证据级；`phase-12` 引用纪律；`phase-13` 参考文献补齐与图表口径 |
| 技能级工具（新 `scripts/`） | `artifact_lint.py`（本次自建，已用真实 run 产物验证：`17280` 命中 25 份产物、输出可直接整改）；`figure_lint.py`、`lit_verify.py`（**交付中**：后台子代理按真实缺陷图/真实文献池做验收测试，落地后在 §0.5 补验收结果） |
| 验证资产 | `test/dryrun-shell.mjs`：桩 agent 干跑壳（full / resume / resume 失配三模式），无需真跑 run 即可回归 |

### 0.4 本轮追加落地（回答「可实现的为什么没动手」）

原「暂缓 pool/」的前提是**等 run 后重新评估**——run 已结束，故 §1.3 的 1/2/4/5/6 本轮全部落地：

| 项 | 落点 / 验证 |
|---|---|
| **§1.3-1 原语池** | 新建 `scripts/primitives.py`（点-线段距离、圆柱面采样、区间并集/求和、二分精化、bootstrap CI、DE 包装，共 8 项；**⚠ 该实现把单题个例当"题无关原语"发货，已按 §0.4c 修正**）；`--selftest` **含独立暴力对拍**（点-线段距离 vs 20 万点稠密采样、圆柱采样到轴距离/轴向范围、区间并集测度、二分 vs √2 解析根、bootstrap 可复现与覆盖、DE 收敛）；`--manifest` 输出签名/单位/返回语义/依赖/版本/对拍值/实测耗时。运行级用法：`cp <技能根>/scripts/primitives.py pool/primitives.py` + `--manifest pool/manifest.json`（产物自包含），题专用实现写 `pool/problem/<题>/` |
| **§1.3-2 探针池 + 结果缓存** | 新建 `scripts/probe_cache.py`：`probes/<角色>/<目的>.py` 固定位置 + `probes/results/<指纹>.json` 缓存 + `probes/manifest.json` 登记；指纹＝原语版本+脚本内容+输入+配置。**实测**：冷跑 2.08s → 命中 0.057s（36×），改输入/改脚本自动失效重算，命中不执行脚本 |
| **§1.3-4 可复用资产清单注入** | 壳启动时随 boot 一次性读 `pool/manifest.json` + `probes/manifest.json`（同一批 `rfMany`，不增会话），生成「可复用资产」行注入**每个阶段/评审/修订**提示词；干跑已断言注入存在（含缺 manifest 时给「尚未登记」提示）。**该实现有可见性漏洞，已由 §0.4b F1 修复**（快照只读一次 → 改为文件为权威 + 题专用核心 manifest） |
| **§1.3-5 让复用成为阻力最小的路径** | `--selftest` 一条命令验证 + manifest 带对拍值与实测耗时 + 缓存命中秒回（2.0s→0.06s）；三处提示词写明"禁止 /tmp 一次性脚本、禁止重写慢副本" |
| **§1.3-6 跨 run 边界** | skill 级：`scripts/`（primitives / probe_cache / artifact_lint / figure_lint / lit_verify）；run 级：`pool/`、`probes/`、`figures/` 随产物走；提示词写明 `cp` 规范化路径 |
| 提示词接线 | `_common.md` §5 重写（5.1 原语池 / 5.2 探针池 / 5.3 其它复用）+ §6 工具表新增两行；`phase-02/05/06/09` 各自加原语池与探针缓存条目 |

**仍不做（并说明理由）**：§1.2 draft 整读治理——它是本轮唯一"可实现但会改变评审**输入完整性**"的项（范围读/差量读必然让评审少看内容），而 §1.1 不可实现（§0.2 C1），所以该项**需要你裁决**：赛前保持现状（推荐），赛后用 A/B 数据决定。

### 0.4b 复审后补洞（F1+F4，2026-09-10 晚；零新增 agent 会话）

复审「上次 run 的共享性差 / 代码慢 / 复用率低」三项后发现：机制已就位，但**共享可见性有真漏洞、性能无人核验**。本轮只补这两处（用户批准 F1+F4，未采纳 F2「每问刷新快照」以省会话）：

| 项 | 问题（证据） | 落点 / 验证 |
|---|---|---|
| **F1 资产可见性** | `ASSETS` 只在启动赋值一次（`math-model.js` 全脚本仅 1 处赋值），q1 建好 `pool/` 后 q2–q5 收到的仍是「尚未登记（首次 cp …）」→ 重造轮子的触发器；照它 `cp` 还会覆盖 run 内已改动的 `primitives.py`（版本号不递增 → 探针缓存指纹脱钩） | 三份清单（`pool/manifest.json`、**新增 `pool/problem/manifest.json`**、`probes/manifest.json`）列进 `stagePrompt` 的「一次并列 Read」；`assetsLine(true)` 声明**以文件为权威、快照可能过期、已存在禁止 cp 覆盖**；措辞由「尚未登记」改「启动快照未见…登记」；`buildAssets` 增题专用核心段；`_common.md` §5 前言 + §5.1 增「题专用核心必须登记 `pool/problem/manifest.json`」 |
| **F4 性能可核验** | `perf.wallTime_s` 只躺在 results.json；`phase-07`/`phase-11` 模板里 `perf/耗时/wallTime` 零命中 | `phase-07-sanity.md` 新增「性能与复用核查（不阻塞，只登记）」：缺 `perf` 字段／`wallTime_s > 900`／重复重算 → warning 入 sanity-report 的性能段 |
| 验证 | | 干跑 4 模式全绿：`node test/dryrun-shell.mjs`、`--resume`、`--resume-mismatch`、`FIXTURE_MANIFESTS=1`（新夹具注入三份清单，断言列出「已登记 N 项／selftest 通过／以文件为准」分支） |

| **F3 前置：进/不进池判据** | 原 §5.1 只规定"放哪里"，未规定"什么才配进池" → 每个 agent 都能自称"我这份是本问专用"，4 份 `core.py` 因而合法共存 | `_common.md` §5.1 增三条：**进池判据**（rule of two + 口径固化 + 纯函数 + 对拍证据 + 热路径，须同时满足）、**不进池清单**（一次性脚本/单问口径/口径未定/胶水/一行包装）、**晋升阶梯**（本问目录 → `pool/problem/<题>/` → `scripts/primitives.py`，只升不降，第 2 次需要禁止再写副本）。纯提示词，0 会话 |

**仍未做**：F2（每问边界 `rfMany` 刷新快照，+4~5 会话，用户对新增会话敏感 → 省）、F3 本体（`reuse_lint.py` 重复实现检测，零会话但需新写 ~150 行脚本；判据已先落地，见上行）。

### 0.4c 去掉上一 run 的上下文污染（2026-09-10 晚；用户指正）

**问题**：`scripts/primitives.py` 以「题无关原语池」身份发货，实际 8 项里 6 项是 **2025 国赛 A 题（烟幕遮蔽/圆柱目标）的单题个例**——文件 docstring 甚至直接写着该题函数名（`missile_pos`/`drop_point`/`burst_point`/`cloud_center`）；「点-线段距离、圆柱面采样、区间并集/求和、二分精化、bootstrap CI、DE 包装」这一串描述还被复制进 `_common.md` §5.1/§6 与 `phase-02/05/06`。技能根副本会被此后每个 run 继承 → **对任何新题都是上下文污染**（题面不同却先看到一套上一次的几何采样条目，把 agent 锚到上次的建模方式）；其中二分/bootstrap/DE 还违反自家判据「不进池：一行的库函数包装」（`scipy.optimize.brentq`、`scipy.stats.bootstrap`、`scipy.optimize.differential_evolution` 已提供）。

**修正**：
1. **发货线重划**——技能根只装「库不提供 + 口径敏感 + 领域中立（纯数学定义，无建模选择）」，且需 ≥2 个不同题的复用证据；单题条目一律写 `pool/problem/<题>/`。
2. **发货池瘦身 8 → 2**（`VERSION 2.0.0`）：保留 `point_segment_distance`/`min_distance_to_segment_batch`（numpy/scipy 无此功能、截断与退化口径敏感）与 `interval_union`/`interval_total`（无区间代数、端点口径敏感）；裁掉 `cylinder_sample_points`（含该题建模选择）、`bisect_boundary`/`bootstrap_ci`/`de_minimize`（库已提供）。
3. **归档不删除**：4 项原始实现 + 判据对照 + 可复用对拍手法 → `docs/cases/2025A-primitives.md`（明确标注「案例，不作为池发货」）；再遇同类题可搬进 `pool/problem/<题>/`。
4. **提示词去枚举化**：`_common.md` §5.1/§6、`phase-02/05/06` 不再列举任何具体条目，改为「先 `--list` 查条目 + 判据 + 单题条目写 pool/problem」；`probe_cache.py` docstring 的 `purpose="圆柱边界二分精化"` 改为中性的「边界敏感性扫描」；`--list` 末尾打印「本文件不含单题内容」。
5. 验证：`primitives.py --selftest`（新增退化线段/空区间/零测集/批量一致性 4 项断言）＋ `--list` ＋ `--manifest` ＋ 干跑 4 模式。

**通用教训（写进 §5.1）**：技能级资产只装**机制与判据**，不装**某次 run 的结论**；个例的正确归宿是 `docs/cases/`（留档）或 `pool/problem/<题>/`（可复用），永远不是技能根。

### 0.4d 全仓污染排查（2026-09-10 晚；承 §0.4c）

按「技能级资产只装机制与判据，不装某次 run 的结论」逐层排查，**共 8 个文件 26 处**：

| 层 | 部位 | 类型 | 处置 |
|---|---|---|---|
| 提示词 | `phase-02/05/06` 的「遮蔽判据」示例 | 建模词汇个例 | 改为中性「判据/求解器等核心算法 + 查 manifest」 |
| 提示词 | **三份评审模板**：`grid_res.npy`、`q1 core / eda_scan`、`全量景观扫描` | 上次 run 的具体产物名/文件名（评审循环最高频提示词） | 改为契约产物（`eda.md`/`results.json`/`data-collection.json`）+ 池 manifest |
| 提示词 | **三份评审模板 + phase-04 的卫生条**：「探针写 `/tmp` 或跑完即删」 | **口径冲突**（与 §5.2「固定 `probes/<角色>/`、禁 /tmp 一次性脚本」直接矛盾） | 统一为探针池 + `probe_cache.py`，禁 `/tmp`、不留 `04-formulation/` |
| 规范文档 | `performance.md`：`q4 EDA`/`greedy`/`遮蔽判据`、`参考 q1「闭式主路径…」` | 个例引用 | 保留数量级证据（秒级→18 分钟），去掉题目词汇 |
| 规范文档 | `writing-and-format.md`：`R=10 m`、`0–4000 m`、`关键区间（遮蔽窗）`、**「优秀范例 D033/E010」** | 题面常量 + 无出处的外部论文编号 | 阈值改中性写法；范例改为「类型 + 共性」（原编号 agent 无法打开，不可执行） |
| 脚本 docstring | `artifact_lint.py`（`17280`/`1.3916`/`7.5841` + "2025 国赛"）、`probe_cache.py`（`probe_q4c.py`/「圆柱边界评估」）、`primitives.py`（题面函数名、17280 基准） | 题面常量与个例函数名 | 改为机制性描述（保留「首版曾误报 82 条」这类可复用教训）；基准规模改 20 万 |
| 脚本契约 | `lit_verify.py --cache` 帮助文本仍写 `test/perf/scratch/.litcache` | 与实现不符（默认已改 `<cwd>/.litcache`） | 修正帮助文本 |
| 根文档 | `README.md`：`遮蔽判据类函数`、`遮蔽判据核心重写…6.5×` | 建模词汇个例 | 改中性表述，保留实测倍数 |

**判定为合法、不处置**：`docs/cases/2025A-primitives.md`（明确标注的案例归档）；`test/**`（本地夹具，`.gitignore` 已整目录忽略，不注入 run 提示词）；`performance.md` 的库行为实测（numba prange+linalg 25.6s vs 4.9s）；`_common.md` §5 的数量级证据（4 份 core.py / 53 个脚本 / 231 次写入）；`figure_lint.py` 的 `plot_q{id}_figures.py` 命名示例（我方约定，非题面）；`phase-13`/`step1` 的 `/tmp` 瞬时构建文件（refs.tex、题面抽取文本）；`tools/diagram-design/**`（vendored 上游内容）。

**终检**：`grep` 建模词/题面常量在 prompts、docs、SKILL、templates、workflows、scripts、README = **0 命中**；`primitives.py --selftest` 通过；干跑 4 模式全 PASS。

### 0.4e 修共享链断点：池 import 路径（2026-09-10 晚；用户提问「run 中代码如何共享」时实测发现）

**问题**：提示词写「此后一律 `import` 复用」，但按文档布局**根本 import 不进来**——Python 把**脚本所在目录**放进 `sys.path`，不是 cwd：

```
cd <outputDir> && python probes/adversary/x.py
  → ModuleNotFoundError: No module named 'primitives'      # sys.path[0]=probes/adversary
PYTHONPATH=<outputDir>/pool python probes/adversary/x.py
  → OK
```

`probe_cache.run_script` 原先只 `subprocess.run([sys.executable, script], env=env)`，不改 cwd、不注入路径；提示词全文无 `sys.path`/`PYTHONPATH` 约定。后果 = agent 撞 ModuleNotFoundError 后**把池中代码内联抄一份** → 又造一个轮子（正是要治的病）。

**修正**（0 新增会话）：
1. `probe_cache.py`：① `run_script` 给子进程注入 `PYTHONPATH=<cwd>:<cwd>/pool`（保留原 PYTHONPATH）；② 新增 `bootstrap_sys_path()`（把 `<outputDir>/pool`、`<outputDir>` 加进 sys.path，返回实际插入路径便于日志核对），`main_with_cache` 入口自动调用 → 库方式直接执行脚本也成立；③ docstring 增「import 路径口径」段并明确「**撞 ModuleNotFoundError 一律先修路径，禁止内联抄一份**」。
2. 提示词接线：`_common.md` §5.1（新增路径口径条）与 §5.2（路径口径条补 PYTHONPATH 注入）、`phase-02/05/06`、三份评审模板的探针卫生条——统一写明 `PYTHONPATH=<outputDir>/pool:<outputDir>` 或 `pc.bootstrap_sys_path()`。

**验证（端到端，真跑一次探针池）**：
```
① 库方式：python probes/adversary/seg.py            → {"dist":1.0,"ver":"2.0.0"}（bootstrap 生效）
② 黑盒方式：probe_cache.py --run probes/adversary/cli.py --inputs '{"k":1}'  → 计算完成 0.164s
③ 二次执行同一命令                                    → 命中缓存（跳过执行）
④ 落点：<cwd>/probes/results/<指纹>.json + <cwd>/probes/manifest.json   ✓ 符合 §5.2 路径约定
```
＋ 干跑 4 模式全 PASS。

### 0.4f 补共享链的验证端：W1 登记完整性 + W2 改池未递增版本告警（2026-09-10 晚）

问题：代码进池有三条入口，但**只有探针是工具强制的**——手写登记无人校验（W1），改了池不递增版本会让探针缓存静默命中过期结论（W2）。

| 项 | 落点 | 验证（真跑） |
|---|---|---|
| **W2 版本守卫** | `primitives.py --manifest` 记 `sourceSha256`；同一 `VERSION` 而源码指纹变了 → 打印「需动作，不是工具故障」并 **退出码 1**（清单仍写入，不留陈旧状态） | ① 首次 0 ② 未改动重跑 0（无误报）③ 加注释不改版本 → **exit 1** + 指纹对比信息 ④ 递增版本 → 0 |
| **W1 登记完整性** | `artifact_lint.py` 新增 `check_pool_registration()`：`pool/`、`probes/` 下 `.py` 与 manifest 条目**双向对账** → `probes.unregistered` / `probes.ghost` / `pool.unregistered` / `pool.ghost` / `pool.manifest_missing`（全 P1，**不阻塞**）；报告增「池登记」统计行，JSON 增 `pool` 段 | 夹具 1 已登记 + 1 未登记探针 + 1 未登记题专用核心 → 精确报 2 条；幽灵夹具 → 精确报 2 条；退出码 0（不阻塞） |
| **配套** | `probe_cache.register()` 增 `script` 字段（登记的脚本路径 = 对账锚点，两个调用点都传） | 探针跑一次后 manifest 内可见 `script` |
| **提示词** | `_common.md` §5.1 增「改池必须递增版本（退出码 1 的含义）」，§6 工具表更新 artifact_lint 描述；`phase-07` 的核查段增「池登记完整性 → 未登记立即补登记」 | — |

回归：`primitives --selftest` 通过、三个脚本语法 OK、干跑 4 模式全 PASS。

### 0.4g F3 落地：reuse_lint.py（复用率机械核验）

与 W1 分工：`artifact_lint.py` 查「**进了池却没登记**」，本工具查「**该进池却没进**」——即 §5.1「rule of two」判据的机械执行者（此前只有自觉 + 人工 grep）。

| 项 | 内容 |
|---|---|
| 新脚本 | `scripts/reuse_lint.py`（stdlib，~330 行，只读）：`--scan` 把每个函数**规范化成骨架**（去 docstring + 标识符按首次出现顺序重命名、保留属性名/常量）后聚类 → 报「同形实现出现在 ≥2 个文件」的组，每组给**建议权威**（`pool/primitives.py` > `pool/problem/` > `probes/` > 更早小问）、**是否已登记**（与两份 manifest 对账）、**是否跨小问**、置信度（函数名/参数名也一致 = high，仅骨架同形 = medium）；`--pairs a.py b.py --inputs` 同输入对拍两份实现（MATCH/DIFF/ERR，DIFF 报「不得合并」） |
| 退出码 | `--scan` 恒 0（只报不阻塞）；`--scan --strict` 有跨小问重复组 → 1（供 11 阶段定 P0）；`--pairs` 有分歧/异常 → 1 |
| 接线（4 处） | `_common.md` §5.1（判据的机械验证）+ §6 工具表；`phase-05`「写完当场查重」（改不完 → 返回 `NEEDS_REVISION` 借壳现成重试通道，**自修复点**）；`phase-06` 同纪律（改 import 后重跑计算，固定种子数字不变）；`phase-07` 把**重复组数/跨小问组数/未登记数**写入 sanity-report（复用率在 run 内首次有可读数字）；`phase-11` §3b 跨小问复用核验 → 整改清单（**禁止回改已定稿小问**，否则代码与 results.json 脱钩） |
| 硬约束 | 只产报告，默认不阻塞；AST 相似 ≠ 同口径 → 合并前必须过 `--pairs` 对拍；口径不同只写差异理由并各自登记 `scope` |

**验证（真跑，用上次 run 的真实重复夹具）**：
```
--scan --root test/perf --dirs .        → 36 份文件 / 130 函数 → 20 组重复；
   G1 cylinder_sample_points 4 份（eda_scan_jit/opt/orig + scratch/eda_scan_copy）  ← 正是上次 run 的重复形态
   G2 main 4 份
run 布局夹具（pool + q1 + q2 各抄一份 point_segment_distance）
   → 1 组跨小问，建议权威 pool/primitives.py:62（pool/manifest.json，已登记）；--strict → 退出码 1
--pairs：MATCH → 0（rtol 1e-9）；DIFF → 1（A=6 B=9）；ERR → 1（ValueError: boom）；无同名函数 → 0
```
附带修正：`--dirs .` 首版把 vendored `test/perf/libs/`（numba 源码树，1217 份文件）当成产物扫出 265 组噪声 → 增 14 类第三方目录过滤（`libs`/`site-packages`/`vendor`/`node_modules`/`build`/`dist`/`__pycache__`…）。

### 0.6 全项目自洽性审计与清债（2026-09-10 晚）

**机械交叉核对**（脚本化，全绿）：13 阶段在 `stage-manifest.json` ↔ 磁盘 ↔ 壳 `T` 映射 ↔ `outputLayout` ↔ `deps` 全一致；`_common.md §N`、`docs/*.md`、`scripts/*.py` 的引用全部可解析（§N 无悬空节）；提示词里提到的 17 个工具参数在脚本中全部存在；phase 编号 01–13 连续无缺；`state-schema` 门禁键（`q*.solve-start/write-start/final-start`）与壳一致；6 个脚本 `--help` 全部可运行；`figure_lint --render`/`lit_verify`/`probe_cache` 的外部调用均有超时（600s/20s+2 重试/600s）。

**修掉的真实问题（本轮）**：

| # | 问题 | 证据 | 处置 |
|---|---|---|---|
| 1 | **`pool/` 目录位置错误**：`SKILL.md`/`SKILL.claude.md` 的目录树把 `pool/` 画在 `intermediates/` 下，且缺 `probes/`、`figures/` | 全仓其余位置（phase-01/02、壳、两个 lint）都用 `<outputDir>/pool/` | 两份 SKILL 的树改为 outputDir 根下 `pool/`（含文献池/外部数据/代码池三用）+ `probes/` + `figures/`；`_common.md` §5 增「共享区布局」防混淆 |
| 2 | **`pool` 一名两义**：文献池（`literature-pool.md`）与代码池（`primitives.py`/`problem/`）同目录却无说明 | — | 同上，在 §5 与 SKILL 树里写明三者关系 |
| 3 | **ledger 口径三处不一致**：壳给「修订」注入 `${LG}`（追加），`_common` §2 说「评审/修订都不追加」，`state-schema` 说「评审追加」 | `math-model.js` 修订提示词 vs `_common.md:21` vs `state-schema.md:52` | 统一为：**评审（并行）不写 state/ledger；修订（串行）追加 ledger、不改 state；收束节点统一记** |
| 4 | **deps 渲染不完整**：`00-problem` 无扩展名、`{id}/01-literature` 是目录 → 提示词里是半截路径 | 干跑 dump：`依赖 00-problem` | `stage-manifest.deps` 改为真实产物路径（`00-problem.json`、`{id}/01-literature/literature.md`…），壳对路径型依赖补 `intermediates/` 前缀、说明型（含中文）原样注入；干跑加两分支回归断言 |
| 5 | **`current`/`deps` 有契约无写者**：`state-schema` 要求阶段 agent 更新，但 13 个模板无一提及 → 白跑回合风险 | 全提示词 grep | 降级为**可选**字段并注明「resume 只看 gates/artifacts，不要为它额外派回合」 |
| 6 | **评审全异常时白付一轮修订**：`vs` 全 null 且未到 RND 时仍会开修订会话，而 `review-r*-*.md` 根本不存在 | `runFormulation` 分支 | 加「全部异常 → 跳过修订、重跑评审」；到 RND 仍全异常则记 FAIL |
| 7 | **未传 `resume` 时静默覆盖**：同题已有 state.json（含 gate 记录）却从头重跑 | 壳无提示 | 增警告日志（说明会覆盖、要续跑请传 `resume:true`） |
| 8 | **Claude 版安装缺工具**：`install.sh --claude` 只链 `prompts templates workflows`，缺 `docs/ scripts/ tools/` → 提示词引用的 `<技能根>/scripts/*.py`、`<技能根>/docs/*`、diagram-design 全部落空 | `install.sh` Claude 分支 | 改为链接全部子目录 |
| 9 | **Claude 版 workflow 缺 `export const meta`**：仓库正文是 DSH 薄壳（meta 作为工具参数传），而 Claude 的 `scriptPath` 需要文件自带 meta | `install.sh` 注释与实际壳不符；壳内 grep 无 meta | 安装脚本改为**生成** `~/.claude/workflows/math-model.js = meta 头 + 仓库正文`（单一事实源仍是仓库，重装即同步）；`SKILL.claude.md` 去掉写死的 `/home/tofu/...` 个人路径并说明该机制 |
| 10 | `plugin.json` 描述与实现不符（"4人评审团"、"5维验证"） | 实际 3 视角评审、6 条数值硬门禁 | 改为 3 视角 + 六条硬门禁 |
| 11 | **`.gitignore` 把壳的验证手段排除了**：`/test/` 整目录忽略 → `test/dryrun-shell.mjs` 与夹具不入库 | `git check-ignore` | 改为只保留该文件与两个夹具（`00-problem.json`/`state.json`）入库，其余仍忽略；同时忽略 `.litcache/`、`.qc_tmp/` |
| 12 | 仓库残留临时产物 | `.qc_tmp/`（1.9M，无引用）、`.litcache/`（76K） | 已删除 |

**验证**：干跑 4 模式（含新断言）全绿；`install.sh --claude` 在临时 HOME 下试装 → 6 个子目录软链齐全、生成的 workflow = meta 7 行 + 薄壳正文 249 行；`bash -n install.sh`、`plugin.json` JSON 合法。

**待用户裁决（未动）**：① `test/perf/libs/` 275MB（pip 装出来的 numba/numpy/llvmlite 树，gitignore 内、与 `performance.md` 的基准数字有关，可直接删或保留离线复测）；② `docs/refactor-plan.md`（22KB）与 `docs/paper-structure-distillation.md`（7KB）无任何在库引用（仅被 `.superpowers/` 会话状态提到）；③ 6 个必需但未入库的文件（`skills/math-model/scripts/`、`prompts/_common.md`、`docs/performance.md`、`docs/cases/`、`docs/pending-changes.md`）需要提交；④ 版本号：`plugin.json`/`install.sh` 仍是 2.4.0，本轮改动量够一个 2.5.0。

### 0.6b 独立提示词审计（30 条）的处置（2026-09-10 晚）

独立子代理对 `prompts/**` + 两个 schema 做了只读审计，产出 **30 条**（3 严重 / 13 中等 / 14 轻微），逐条核验后**修 27 条、保留 3 类**：

**严重（3/3 已修）**
1. 评审节点 ledger 口径冲突 → 已随 §0.6 第 3 条修（评审并行不写 ledger；修订串行追加）。
2. **门禁只认 PASS、枚举漏 `PASS_WITH_WARNING`** → sanity 的合法结果会被下游当失败（上次 run 两问 sanity 都是 PASS_WITH_WARNING，路径是活的）。已改：`_common §1` 前置通过条件 = `{PASS, PASS_WITH_WARNING, SKIPPED}`，status 枚举补 `PASS_WITH_WARNING`。
3. **出图自检命令指错目录/脚本名**（`--py plot_q{id}_figures.py --png figures/*.png` vs 实际 `08-visualization/figures/`）→ 等于空转。已改：phase-08/02 明确规定绘图脚本落盘位置（`08-visualization/plot_figures.py`、`02-data/plot_eda.py`）并给出完整路径命令；`_common §6` 工具表同步。

**中等（13/13 已修）**：assumption 的 `outputLayout` 硬编码 `assumption-v01.md` 与「绝不覆盖旧版」冲突 → 改为目录；crossReview「发现不一致即 NEEDS_REVISION」在壳里必然 blocked → 拆成 `PASS_WITH_WARNING`（非阻塞项）/`NEEDS_REVISION`（阻断项）并让 write-start 门禁接受 `PASS_WITH_WARNING`；phase-11「下次重跑 06 时改 import」在壳里不会发生 → 改为「留待主 agent 手工 resume」；localComplete 的散文式 deps 含 `{id}` 占位符 → 去占位符；phase-12 把可选产物（两份 figure-manifest、lit-verify.md）当必需输入 → 补「存在才读」；phase-12「分多次会话继续」不可实现 → 改为「落盘 + 返回 NEEDS_REVISION 让壳重跑」；9 处硬编码 `skills/math-model/docs/…` → `<技能根>/docs/…`；2 处硬编码 `python3` → 注入解释器；终审的 `${PD}`/`templateDir` 口径 → 技能根/templates；phase-11 谎称「壳注入小问清单」 → 改为读 `00-problem.json`；flowchart-drawing 的 `<模板目录>` → `<技能根>`（与 _common §6 统一）。

**轻微（11/14 已修）**：个例题名/口径示例中性化（板凳龙、定日镜场、A053、「30户」）；`T_eff`、付费条目 7/8 等个例细节中性化；`state-schema` 删悬空的 §4.8 并补 `degrade` 节点职责；`finalize` 补写 `current`；phase-06 的 results.json 模板去掉写死的 `solution_v2.py`/`mode:"full"`；probes 角色枚举补 `data`/`impl`；补 `standard` 严格度阈值定义；三处「前序可复用实现去哪找」清单统一；三份评审模板缺件由 FAIL 改 `NEEDS_REVISION`；`refs.tex` 由 `/tmp` 改到 `13-final/`；joblib 阈值统一 20ms；§四-8 引用错位修正。

**保留（3 类，理由）**：① 数量级证据（`_common` 的「4 份 core.py / 6 函数各 3 次 / 18 处」、phase-05 的 161 次工具调用、phase-06 的 53 份脚本/231 次写入/25s）——它们证明纪律必要，且不含题面词汇，属可复用教训；② 设计取舍：壳内每问 06 只跑一次的结构不改（改它等于给壳加阶段重入通道，风险大于收益）；③ 未机械化的 `q{id}`→实际目录替换仍靠 agent 心算（壳只替换 outputLayout/deps 里的 `{id}`）——已记入观察项。

**清债**：删 `.qc_tmp/`（1.9M）、`.litcache/`（76K）、空目录 `tools/flowchart/`（全仓 0 引用）。

### 0.6c 独立脚本审计（27 条）的处置 + 工具回归套件（2026-09-10 晚）

第二个独立子代理只读审计 6 个工具脚本，产出 **27 条**（3 严重 / 13 中等 / 11 轻微），**全部核验并逐条修复**，复现用例固化为 `test/scripts-smoke.sh`（**17 个用例，全绿**）。

**严重（3/3）**
1. **`lit_verify` 把 OpenAlex `oa_url`（落地页）当 PDF → 无全文也判 L1「有全文」**（实测：doi.org 404、池内 URL 主机不存在的条目仍判 L1）。修：`pdf_url` 只取 `best_oa_location.pdf_url`；**判 L1 前 HEAD 探测**（可达状态码 + `content-type` 含 pdf），失败写 note 不判 L1。验证：假 DOI → **L2（L1=0）**；真 OA 论文（PLOS ONE）→ 仍 **L1**（未过度抑制）。
2. **`probe_cache --run` 指纹不含原语版本/池内容 → 改池后静默命中过期结论**。修：新增 `pool_signature()`（`pool/` 全部 `.py` 内容哈希 + `primitives.py` VERSION），缺省自动探测；改池即失效（用例 10）。
3. **`reuse_lint` 的 `SKIP_PARTS` 按绝对路径任意段过滤** → run 根路径含 `outputs`/`results`/`.litcache` 时整棵树 0 文件、`--strict` 静默退 0。修：按**相对扫描根**判断 + 0 文件警告（`--strict` 退 2）（用例 1/2）。

**中等（13/13）**：`artifact_lint` 探针对账被路径段 `results` 打成幽灵条目 → 按相对 `probes/` 判断；`paper.unsourced` 误报题面给定常量 → 跳过 `givens`；**论文正文 `12-writing/paper-sections/*.md` 不计数导致漏报 P0** → 补进白名单（用例 5）；`--json` 不可写 → 先出报告再 `return 2`；**真源按文件名全域匹配** → 收紧为契约路径 `q*/06-computation/results.json` 与 `12-writing/fact-sheet.md`（用例 6b）。`figure_lint`：**单引号属性绕过全部 P0 判据** → 解析前统一引号（用例 7）；非 UTF-8 被误诊为「工具 bug」+ traceback → `errors="replace"`（用例 8）；`--json` 坏路径丢报告 → 先出报告再落盘（用例 9）。`lit_verify`：缓存键缺 `read_limit` → 2KB 小读截断 400KB 落地页抓取 → 键内加 `limit`；`--only` 无匹配的误导性报错 → 区分「池空」与「过滤后空」；池校验前建 `.litcache` → 改 `ensure_cache()` 后置。`reuse_lint --pairs` ndarray/list 混比抛 `ValueError` → 归一化（用例 3）。`probe_cache --clear` 会删 `probes/manifest.json` 与手写 json → 只删符合本工具记录结构的文件、显式跳过 manifest（用例 12）；缓存目录不可写时算完才崩 → `save/register` 包 `OSError`，结果照常输出。`primitives`：版本守卫**只报警一次**（基线写在会被覆盖的清单里）→ 基线移到清单之外的伴生文件（用例 13：1/1/0）；`--manifest` 目录不存在即 traceback → 自动 mkdir、写失败退 2（用例 14）。

**轻微（11/11）**：`figure_lint` PIL 分支去掉 numpy（`tobytes()` 逐行统计，依赖面回到「stdlib + 可选 PIL」）；`probe_cache --run` **命中缓存时不输出结果**（调用方取不到数）→ 两条路径都打 stdout（用例 11）；`--list` 遇非本工具 JSON 崩栈 → 判类型跳过；`reuse_lint --dirs` 拼错静默 0 文件 → 退 2；`--pairs` 缺文件/语法错误 → 明确结论行 + 退 2；`primitives` 空点集 `min` 抛 `ValueError` → 返回 `inf` 并加断言；指纹含脚本路径 → docstring 如实写明。

**保留（未改，含理由）**：`figure_lint` stdlib PNG 回退 0.25–0.3 s/MPx（仅缺 PIL/numpy 时命中，无超时风险，docstring 已注明）；`svg.font` 只查元素属性与 5 个 CSS 选择器（字号写在自定义 class 会漏检，docstring 已自述）；`render.legend_cover` 以图元 bbox 为分母（docstring 已自述）；`lit_verify` 父/子两套缓存键 → 记入观察项。

**新增回归资产**：`test/scripts-smoke.sh`（17 用例，覆盖上述每条修复），`.gitignore` 已放行入库（与 `dryrun-shell.mjs` 同级）。

### 0.6d 实战 run 暴露的两处「专职节点不知道自己要干什么」（2026-09-10 深夜，run 进行中修）

用户实跑 2026 国赛 A 题时点名：`q1.formulation` 阶段 agent 与 **`【收束 q1.formulation】`** 节点「似乎并不清楚自己的工作是什么」。查证 3 条（全部只改提示词/壳文案，**不新增任何 agent 会话**）：

1. **收束 / 降级两个专职状态节点的提示词只有一串状态赋值**：`【收束 q1.formulation】state.json：iter["q1.formulation"]=…`——不自述职责、不给 `state.json`/`ledger.md` 路径、不要求先读再**就地合并**，且 `iter` **不是 schema 字段**（schema 是 `iterations`，口径为「累计执行次数」而非单轮 `r+1`）。实跑旁证：该 run 的 `state.json` 出现 `gates["q1.formulation"]="PASS_WITH_WARNING"`（该键按 schema 与键约定只有 `PASS|NEEDS_REVISION|FAIL`，壳注入的也是 `PASS`）与 `iterations=5`（单轮口径推不出）——即节点自行改写了注入值。修：两节点改为「自述职责 + 只做状态收尾（不改产物/不重跑） + 一次并列 Read（state-schema / state.json / ledger 尾部） + 就地合并（其余键保留） + 精确字段与值（`iterations` 累计、`gates` 原样写入注入值） + 固定 ledger 键 + 返回契约」。ledger 键写进 `state-schema.md`：`q.formulation`（formulator）/ `q.formulation.revision-r<n>`（修订）/ `q.formulation.finalize`（收束）——此前实跑出现两条同名 `q1.formulation:` 与自拟的 `revision-rN`，审计难分辨。同类修正：常规阶段与门禁节点的 `<key>` 占位符也换成注入的具体键（`q1.literature: <status>`、`q1.solve-start: <PASS|FAIL>`），壳内 `LG` 常量随之删除。
2. **`deps.formulation` 仍硬编码 `assumption-v01.md`**（§0.6 只修了 `outputLayout` 的同类冲突）：假设阶段「绝不覆盖已存在的版本文件」→ v01 很可能正是被自检拒绝的版本（本次实跑即 v01 被拒、v02 定稿），注入依赖指向废稿，与模板「最新版本」自相矛盾。修：依赖改注入**目录** `{id}/03-assumptions/`；phase-04 与 judge 模板统一写「权威路径 = `state.json.artifacts["q{id}.assumption"]`，禁止据旧版建模」。
3. **单问 draft 的边界口径自相矛盾**：phase-04 原写「逐小问全覆盖 / 对每个子问题」，judge 判据 5 更要求「对照 00-problem.json 的小问清单，每个子问题都有对应方案」——但 draft 是**单问**产物（`q{id}/04-formulation/draft.md`），字面上要求它展开 q1–q4。修：phase-04 增「边界（只做本小问）」段与「本小问全覆盖」，judge 判据 5 改为「本小问全覆盖 + 跨问接口写清，不要求在本文档展开其它小问」。

**回归**：`test/dryrun-shell.mjs` 7 种模式全绿。新增 3 类断言——收束/降级提示词形状（职责、路径、真字段名、固定 ledger 键、注入值）、formulation 依赖渲染为假设目录（含反向断言「不得出现 `assumption-v01`」）、模板静态口径（「只做本小问」「禁止据旧版建模」「本小问全覆盖」）；新增桩开关 `FAIL_STAGES=<stage>`（走降级路径）、`REVIEW_STATUS=NEEDS_REVISION`（走修订 → 轮次用尽收束 → 二次尝试 → blocked），`DUMP_PROMPT=<label>` 可打印渲染后的提示词。

### 0.5 未做（本次赛前明确不做）

- §1.1 会话复用（**不可实现**，见 C1）、§1.2 draft 整读治理（待裁决，赛前不动评审循环）
- §1.3-1/2/4/5/6 pool/ 与探针池（用户既定暂缓）
- §2.4 存量重绘 3 张 P0：产物在 workspace 之外且在即的比赛不涉及；**改为**把这三张真实缺陷图当 `figure_lint.py` 的验收样本（比"修旧图"更能验证纪律是否可机械执行）
- §4 旧结转项（test/ smoke 全量、AI 报告 PDF、reasoningEffort、README.html、提交决策）仍待赛后再定

---

## 1. 复用与共享

三层共享对应四处改造；机制是 **固定位置 / 可见性 / 让复用比重写更省事**（不设门禁强制）。

| 共享层 | 措施 | 机制与提高点 |
|---|---|---|
| **原语（代码）** | `pool/primitives.py`（题无关）+ `pool/problem/<题>/*.py`（题专用）+ manifest —— 见 §1.3 | 固定位置 + shell 注入清单 + manifest 带对拍值与性能数据；避免每问重写同一核心 |
| **探针（脚本）** | `probes/<角色>/<目的>.py` + manifest + **结果缓存** —— 见 §1.3 | 探针不再丢 `/tmp`；缓存命中秒回，重写要 25s/次（圆柱评估），复用有直接动机 |
| **产物（数据）** | 图表登记入口（§2.1）、文献池字段（§3.2/§3.4）、机器可读摘要传递（§1.2）、图的单一真源（§1.3） | 让跨阶段/跨小问能"发现并复用"彼此的产物，而不是靠 `ls` 碰运气 |
| **规范与工具** | figure-lint（§2.2）、文献核验脚本（§3.4）、基线证据脚本集（§0） | 把隐式规范与人工判断固化成跨阶段可调用的同一份工具，可跨题移植 |

### 1.1 会话复用（P1：评审 / 修订循环同角色跨轮 continuable）

> **状态：不可实现，仅作记录（见 §0.2 C1）**——workflow 脚本 hook 只有 `agent/pipeline/parallel/phase/log/args`，每次 `agent()` 都是新子会话，脚本内无 session 句柄、无 `send_message`。下列内容保留为「若 DSH 本体开放会话复用接口」时的设计稿。

**现状**：workflow 的 `agent()` 每轮新开 one-shot 子会话，跨会话仅公共前缀（system+tools ≈ 11K）可命中（实测首轮命中 73.6% = 8K/11K）；每轮 draft.md / symbols.json / baseline-registry.md 都要重新读盘。q1–q4 共 **53 个评审/修订会话**。

**目标**：同一评审角色跨轮复用一条会话（judge r1→r2→r3、修订 r1→r2），后续轮只发增量消息（"draft 已更新至 vN，变更点：…"）。**硬约束**：一轮内的三个评审角色（judge / adversary / application）仍须各自独立会话 —— 合并会互相锚定，破坏独立复核价值。

**收益**：2–3M tokens（重复读 2.6M 的大部分）+ 少开约 26 个会话的启动开销（估 1–2h）。**不是** 52% —— 早前把"循环占 fresh 的份额 51.7%"误当成可回收量，已纠正。

**风险**：r2 被 r1 结论锚定（对抗评审最敏感）；会话变长后单点失败代价变大；需改 shell 的 agent 调用方式（one-shot → continuable + `send_message`）。

**验收（必须 A/B）**：同小问对照（复用 vs 现模式），比 ① token（fresh/cacheRead）② 墙钟 ③ 评审缺陷条数与严重度是否退化；不达标回退。

**附带事实（draft.md 读取分布实测，149 次 / 77 会话）**：评审三角色 49 次（1.3 次/会话）、修订 58 次（**7.2 次/会话**）、自查与各阶段/收束/门禁 42 次 → **循环内 112 次（75%）由本节复用覆盖**，循环外 37 次是各阶段必要的一次性读。修订会话内的"读→改→再读校验"重复整读（7.2 次/会话）属**同会话内重复**，本节复用不覆盖，仅记录待观察（不另立措施）。

### 1.2 减少整份重读（P2）

> **状态：待裁决（阻塞于 §0.2 C1）**——原否决理由「已被 §1.1 会话复用覆盖」因 §1.1 不可实现而失效；但赛前不动评审循环（改动评审行为风险 > 收益）。

- 评审/修订 agent 改为**行范围读或差量读**（只读改动段落），而非整份 `read draft.md`
- 由 shell 传递**机器可读摘要**（JSON 片段）代替让 agent 重读全文
- 收益：~0.3M tokens + 减少每轮"重新定位"的思考轮次

### 1.3 复用机制（原语池 / 探针池 / 数字单一真源 / 提示词共享块）

**本次 run 的重复实况**（作为基线，免费读出，不需额外计算）：

| 层面 | 实测 |
|---|---|
| 一次性探针脚本 | **53 个不同文件名 / 231 次写入**（`probe2.py` 9×、`probe_q4c.py` 9× …），全丢 `/tmp`，无登记无复用 |
| 核心实现 | **4 份 `core.py`**（q1 16 / q2 25 / q3 28 / q4 10 个函数）；`point_segment_distance`、`cylinder_sample_points`、`missile_pos`、`drop_point`、`burst_point`、`cloud_center` 各重复 **3 次**；判据/采样/二分实现 **18 处散在 6 个文件** |
| 图 | 06 阶段图 → 08 阶段**重画**一版（q2/q3；q1 沿用） |

**措施**：

1. **原语池分层**（题无关可跨题带走）
   - `pool/primitives.py`：**（⚠ 以下为 2025A 单题个例，已移出技能根，见 §0.4c 与 `docs/cases/2025A-primitives.md`）** 点-线段距离、圆柱面采样、区间并集与求和、二分精化、bootstrap、DE 包装
   - `pool/problem/<problemId>/*.py`：运动学、决策变量域、目标函数、判据口径（题目参数外置到 `const.json`）
   - `pool/manifest.json`：每原语 {名称, 签名, 单位约定, 返回语义, 依赖, 版本, **对拍值**, 实测耗时}
   - `pool/tests/`：**对拍值**（可直接用本次锚点：点判据 1.4055 s、圆柱 1.3621 s 等）；改原语必须过测，防"重写导致数值漂移"
2. **探针池 + 结果缓存**
   - 固定位置与命名：`probes/<角色>/<目的>.py`（如 `probes/adversary/cylinder_boundary_bisect.py`）
   - `probes/manifest.json`：{用途, 输入, 输出契约, 单次耗时, 依赖原语}
   - **结果缓存** `probes/results/<指纹>.json`（指纹 = 原语版本 + 配置 + 参数），命中即复用 —— 直接省掉重复的 25s/次圆柱评估
3. **数字单一真源**（用户采纳项）
   - 规则：**关键数字只写在 `results.json` / `fact-sheet.md`**；其他产物（draft / assumption / sanity / robustness / question-summary / figure-manifest / 图脚本）只写锚点引用（如 `T_eff 见 results.json#q2.keyValues`），不重复抄数值
   - 依据（本次实测）：`17280` 出现在 **46 份文件 / 128 处**、`1.3916` 13 份 / 60 处、`7.5841` 7 份 / 66 处 —— 抄写不仅费 token，更制造"口径分叉"，而评审循环（占 52% 墙钟）相当一部分燃料就是抓这类不一致
   - 机械检查：`artifact-lint`（与 `figure-lint` 同族）扫描所有产物，**同一关键数字（≥5 位有效数字或 ≥4 位数常量）出现在 ≥3 处即报错**，交 phase-07/11/13 处置；图脚本另由 `figure-lint` 保证"不得出现数值字面量"
   - 补充：06 的图脚本**参数化**（中文标签/规范皮肤开关），08 复用同一脚本而非重画
4. **可见性（shell 自动化）**：shell 扫描 `pool/manifest.json` + `probes/manifest.json` + 图表 manifest，把"可复用资产清单"追加进**每个阶段/评审/修订**提示词（现仅注入 state 与 python 路径）→ agent 第一个回合就看到有什么现成的
5. **让复用成为阻力最小的路径**（不靠门禁强制）：① 缓存命中秒回 vs 重写 25s/次；② manifest 里每个原语带对拍值与实测性能（重写等于自己重建置信度）；③ 原语提供 CLI `python pool/primitives.py --selftest`，一条命令验证可用
6. **跨 run 边界**：skill 级共享（`figure_lint.py`、文献核验脚本、phase-01 检索模板、探针模板 → `skills/math-model/scripts/`）vs run 级共享（`pool/problem/`、`probes/`、`figures/` 随产物走）
7. **提示词共享块外置**（用户采纳项）
   - 现状：13 份 phase 各存一份语义同构的「统一节拍」块（每份 432B，合计 5.5KB = 全部提示词的 5.6%），另有各阶段复述 `docs/` 规则
   - 改法：抽 `prompts/_common.md`（统一节拍 + 工具纪律 + 环境/资产清单回读 + ledger/state 写法），各阶段委派提示词改为"读 `_common.md` + 本阶段 phase 文件（并列一次读入）"；各 phase 文件只保留本阶段特有指令
   - 收益诚实说明：token 收益小（提示词总量 98KB，对全 run 输入 236M 只是 1% 量级）；**真正收益是一致性** —— 同一条规则不再抄 13 份而与阶段特有规则互相覆盖/漂移
   - 度量：phase 文件总行数（改动前 967 行 / 98KB），抽样 diff 确认无规则丢失

**归因更正（勿再引用旧说法）**：早前把"q4 EDA 重写慢副本、白付 1080s"当作"提示词纪律无效"的证据 —— **不成立**。"复用核心/禁重写"是 09-10 **11:37** 才写入 phase-05/06/09（phase-02 为 10:24），而 q4.data 跑于 **09:35–10:28**，纪律当时尚未生效。该纪律至今**未在生效条件下验证过**，下次 run 才是第一次。

**度量（只取免费项，不做静态聚类审计）**：manifest 条目数（新增脚本数）、`grep -c "import pool"`、探针缓存目录文件数 —— 三项均可从产物直接读出。

**状态**：用户此前明确暂缓 pool/，理由待 run 后重新评估；上述 2–6 与 §1.2 一并评估。

---

## 2. 图表

### 2.1 注入链修复（EDA 图无逐图登记入口）

写作阶段（phase-12）要引用的图有 3 类，但只有 08 类有硬索引：

| 类别 | 位置 | 索引入口 | 现状 |
|---|---|---|---|
| 各问可视化图 | `intermediates/q{id}/08-visualization/figures/` | `figure-manifest.md`（6 列：文件名/类型/作用/数据来源/绘图方式/位点） | ✓ 齐全 |
| 数据章 EDA 图 | 运行根 `figures/fig_eda_*.png` | **无** | ✗ |
| 写作兜底自绘 | `fig_cross_示意图_*.png` → 根 `figures/` | phase-12 line 73 | ✓（仅按需） |

**实测证据**（q1–q3 已完成 08）：根 `figures/` 仅 11 张 PNG、**无任何索引文件**；`02-data/eda.md` **全文含「图」的行数 = 0**，只有产物行一个通配符 `figures/fig_eda_q2_*.png 3 张`；各问 08 manifest **不含** `fig_eda_*` 行；phase-12 输入清单（line 21）**不含根 `figures/`**；line 73/95 与 phase-13 支撑材料中的 `figures/` **口径不明**（根？各问 08？）。

**结论**：数字链（fact-sheet ← results.json）是硬约束，图链只有 08 这一半是硬的。

**修法**：① phase-02 增产物 `02-data/figure-manifest.md`（或统一登记到根 `figures/figure-manifest.md`），字段与 08 对齐；② phase-12 line 73/95 写清绝对路径与口径（根 → 数据章，各问 08 → 各问小节），双向检查拆两条，并同步 phase-13 口径。

**验收**：写作阶段不靠"碰运气 ls"即可列全待引用图；双向检查可机械判定（清单 vs `\includegraphics`）。

### 2.2 出图自检：figure-lint + 视觉复核（新增环节）

**问题**：`tools/diagram-design/scripts/self_check.py` 只查无障碍/单文件安全契约，**不查本项目纪律**，所以 manifest 里写「self_check 通过」≠ 合格；matplotlib 结果图更是**只有**「无 Glyph 缺失警告」一道检查 —— 图长什么样从来没人看过。

**修法**：① 机械项脚本化为一份 `figure-lint`（建议 `skills/math-model/scripts/figure_lint.py`），规则来源 = `flowchart-drawing.md §2–§5` + §2.3 的 12 条结果图条款；检查项含配色 token 白名单、4px 整除、连线正交、遮罩–线间隙 6–10px、节点/箭头/强调数上限、图注样式、PNG=2× 画布、**墨迹贴边 ≥8px**。参考实现：`test/perf/scratch/check_flowchart_spec.py` + `verify_final.py`。
② 产图后用**视觉模型逐图读回**（phase-02 EDA 图、phase-08 结果图+示意图），按 §2.3 输出缺陷清单；P0 未清零 → 修图重出，**不通过不写 manifest**。提示词改动点：`prompts/phase-02-data.md`、`prompts/phase-08-visualization.md` 各加一节「出图自检」。

**lint 必须能抓到的实测用例**（q1–q3 三张流程图，机械核对而非采信自述）：q2/q3 的 `I(t)` 遮罩 (480,312,40×16) 中心压在竖线 x=500 上（覆盖该连线 24px 中的 16px；q1 正确侧置 8px）；q2/q3 有 8 处 y 离网（文本基线 y=46/70/478/502/814/838 + 图例色块 y=934，均 ≡2 mod 4）；q1 用了 `rgba(26,26,26,0.05)` 而非 token 的 ink@0.12。达标项：真 2×（1920×1352 / 2000×1968）、图注样式与居中（0.0/0.0/−0.5px）、svg 根契约、正交无斜线、节点≤9/箭头≤12、字号 8·12 与 CJK 回退。

**路径唯一性**：① vendored 副本 `<skill>/tools/diagram-design/`（忠实上游 commit `2724fd2`）；② 全局 skill `~/.dsh/skills/diagram-design`（软链到上游工作区，含一行未提交改动 `disable-model-invocation: false`，故对模型可见，皮肤为上游默认值）。**建议**在 `flowchart-drawing.md §0` 与 phase-08 明确"只用 vendored 路径"。

### 2.3 结果图硬条款（草稿，可直接并入 `writing-and-format.md §二`）

现状 §二 对**结果图本身**只有 6 条（CJK 字体 / LaTeX 单位 / mathtext / `[H]` / 无缺字警告 / 示意图路径），对标题、图例、刻度、标签密度、元素解释、边距、尺度**零条款**。

1. **标题**：禁止 `ax.set_title`（图意由图注承担）；确需时只允许一句话且不得含「问题N」「innov」「域外必查」等内部编号与术语
2. **图例完整性**：每种颜色/线型/标记/填充区间都必须进图例或在图内标注；禁止只在标题里解释颜色
3. **图例位置与裁切**：不得遮挡任何数据图元；文字必须完整显示（禁止被裁断）；必要时放图外右侧
4. **分类轴标签**：分类数 >10 时禁止逐条竖排全参数 —— 改横向条形图 / 只标 top-N / 按变量分组；标签字号 ≥ 轴刻度字号
5. **刻度格式**：禁止千分位逗号（`2,500`）与大数直写（`20000`）—— 用 `2.5×10³` 或统一量纲（km）；刻度必须带单位
6. **轴标签防裁切**：保存后机械检测墨迹贴边（四边 ≥8px @2x）；`bbox_inches='tight'` + 必要 padding
7. **阈值线与关键区间**：必须带文字标注（如 `R=10 m`）并进图例；关键区间（遮蔽窗等）必须可见
8. **尺度可辨性**：关键差异在所选尺度下不可辨（如 10 m 阈值 vs 0–4000 m 纵轴）→ 必须改对数轴、局部放大插图或双面板
9. **坐标范围**：不得留大面积空白；范围贴合数据支撑域（必要时说明截断）
10. **3D 图**：直接标注标签 ≤5 且必须防重叠（错位/引线/编号+图例）；轴标签留边距
11. **符号**：上下标一律 LaTeX math（`$T_{\mathrm{eff}}$`、`$P_i$`），禁止字面下划线；科学计数法写 `$2\times10^{-3}$`，禁止 `2e-3`
12. **图-文一致**：标题/图注承诺的视觉元素必须真实可见（交付前逐条核对）

### 2.4 质检证据与存量重绘（run 后执行）

| 图 | 缺陷 | 级别 |
|---|---|---|
| `fig_q2_复核竞争配置_圆柱T_eff柱状` | 图例压在红色条形上**且图例文字被裁断**；33 个 x 标签全参数竖排不可读；红条与橙色空心圆未进图例；`T_eff` 字面下划线（违反 §二-2）；标题含内部术语/缩写 | P0 |
| `fig_q3_几何态势_三弹投放起爆与云团遮蔽` | M1/FY1/投放点/起爆点标签**重叠成一团**；右侧墨迹贴边 0px（实测 x 到 1301/1302）→ **z 轴标签被裁**；x 轴千分位逗号；坐标范围失衡；5 类图元只 2 项进图例 | P0 |
| `fig_eda_q2_occlusion_envelope` | **标题写「遮蔽区间=绿色」但绿色不可见**（图-题不符）；阈值线无标注；0–4000 m 尺度使 10 m 阈值不可辨 → 信息量≈0 | P0 |
| `fig_q1_示意图_…求解流程` | `P_i`/`T_eff` 字面下划线 vs `\|T−M\|²` 真上标；`2e-3`/`1e-7`/`1e-4` 代码风格；灰色 store 节点无图例（灰度不在 token 内） | P1 |
| `fig_q2_示意图_…复核流程` | 同上（`v_c`/`t_d`/`P_d`/`O_b`/`u_F`/`M(t)P_i`）；`Δt→1e-7 s`；箭头标签 `I(t)` 压线 | P1 |

重绘：上述 3 张 P0 按 §2.3 逐条修（图例出图外、x 轴改横向/top-N、标签防重叠+编号、缩放范围、去千分位、补遮蔽区间与阈值标注、改尺度）；其余 19 张结果图逐张过一遍 §2.3。

### 2.5 环境侧（已完成，非待办）

`~/.dsh/settings.yaml` 的 `llm-deepseek.models` 中 `deepseek-v4-flash` 原只声明 `inputModalities: [text]`，导致 `read_image` 被拦（工具闸 `dsh-tool-fs:978`、请求闸 `dsh-llm-deepseek:1605` 都读该目录）。已补 `[text, image]` + `imagePixelBudget: 640000` + `imageMaxBytes: 1048576`，**立即生效、无需重启**（已实测读图成功）。备份 `test/perf/scratch/settings.yaml.bak-20260910-142637`。前提是「v4-flash 已按官方口径路由到多模态」；若上游拒绝图像会报 `UNSUPPORTED_CONTENT`。

---

## 3. 文献层：付费墙、证据分级与引用核验

**背景**：phase-01 `line 52` 已有降级规则（付费墙 → claims 留空、标 `unreliable`），run 也确实按「摘要级 / 未精读 / 标题级」诚实标注、**未编造**。但代价是：权威源被边缘化（命题专家蔡志杰 S14、同行期刊 S3 = 摘要级；IEEE/EDPEE S16/S17 = 标题级），而数值锚点（4.5420 / 4.723893 s、19–93× 加速）**全部来自 GitHub 复现与博客**且未标来源性质。文献阶段只花 **0.42h（2.0% 墙钟）**，但产出被后 11 个阶段 + 交叉审查 + 终审反复引用 → **性价比最高的一层**。

### 3.1 核验实测结果（`test/perf/scratch/verify_lit2.py` → `literature-upgrade.md`）

| 分类 | 条目 |
|---|---|
| **可升级 L1（有 OA 全文）** | **S15** TLR 2026（`is_oa=true, diamond`）、**S23** Symmetry `10.3390/sym18060980`（`gold`）、**S27** ACM `10.1145/3796731.3796859`（S2 `openAccessPdf`）、**S19**（S2 PDF 直链实测 200） |
| **上限 L2（摘要可重建）** | S7 `10.1109/icftic68075.2025.11324990`、S8/S9 `10.1109/auteee67053.2025.1132218x`、S21 `10.1109/iscait69154.2026.11477337`、S26 `10.1109/icrae67496.2025.00035`、S28 `10.1109/auteee67053.2025.11322147`、S12 `10.1117/12.2667063`（SPIE） |
| **中文源上限 L2** | S3/S14（`10.19943/j.2095-3070.jmmia.2026.01.0x`，DOI 不在 Crossref/OpenAlex，`doi.org` → chndoi）、S20（`10.12454/j.jsuese.202600356`）；期刊官网**免费给完整摘要+关键词+引用格式+参考文献表**，全文需登录 |
| **已是 L1** | S1/S2/S4/S5/S18/S24（GitHub、博客、对比文档 —— 须标「社区复现，非同行评审」） |
| **待复核** | S6（IEEE 直查 202 空响应）、S16（真 L3：`is_oa=false` 且无摘要，DOI 已补 `10.23919/edpeecps00009.2026.00083`）、S17（页面 200/200KB，实为 L2）、S10（DTIC 链接返回 1.4KB HTML，疑似失效） |

**核验顺带暴露的 3 项池数据缺陷**（写作阶段直接受害）：① **标题被截断** —— 10 条断在约 95 字符，导致按标题检索失败且 GB/T 7714 参考文献标题残缺；② **缺 DOI** —— IEEE 条目原表只有 `ieeexplore` URL，参考文献缺卷期页/DOI（不合格），本次已补 6 条权威 DOI；③ **摘要可得率被低估** —— 付费条目 **7/8** 能拿到 OpenAlex 摘要，真实下限是 L2，现状「付费墙 → 标 unreliable」过粗。

### 3.2 修法 1：证据分级 + 引用纪律

| 级别 | 定义 | 允许用途 |
|---|---|---|
| **L1** | 全文精读（OA / 预印本 / 官网 / 社区复现） | 支撑方法选择、数值锚点、结论对比 |
| **L2** | 摘要级（abstract + 元数据可读） | 可引用摘要明确陈述的内容；数值须标「摘要级」并可溯 |
| **L3** | 元数据级（仅标题/DOI/卷期页） | **只能作存在性提及**，不得支撑数值或方法 |
| **L4** | 不可验证 | 禁止进参考文献 |

附加硬规则：数值锚点必须标注**同行评审值 / 社区复现值**；规则形式是「可引用 + 标注级别」，**不是禁止引用**（否则权威源会被整体删除、参考文献变薄）。

### 3.3 修法 2：取文回退链（写进 phase-01，命中即停）

OA 优先（arXiv / OpenAlex OA / PMC / DOAJ）→ 作者版·预印本（S2 `openAccessPdf`、机构仓储）→ 摘要级（OpenAlex 重建摘要、期刊官网、SCITEPRESS）→ 元数据级（OpenAlex / Crossref 补 DOI+卷期页）→ 社区复现（GitHub/blog，标非同行评审）→ 付费全文**不硬闯**，按 §3.2 降级标注。

参数要点（本次踩坑）：OpenAlex 需带 `mailto`；Unpaywall 必须真实邮箱（`test@example.com` 会 422）；中文文献走 `doi.org` → chndoi + 期刊官网（Crossref/OpenAlex 对中文 DOI 均 404）；部分站点可达性不稳（期刊官网一次超时一次成功）→ 需重试。

### 3.4 修法 3：引用核验脚本

批量执行 `doi.org` 解析 + OpenAlex + Crossref + Semantic Scholar + URL 状态码 → 核验表（编号 / DOI / 元数据命中 / OA 状态 / 证据级 / URL 状态 / 命中标题）。本次 29 条**一次跑完（<1 分钟、0 个 agent 回合）**，对比逐条 WebFetch 是几十个回合。中英文分两条路径。产出的核验表同时是**文献池的共享字段来源**（§1 表"产物共享"）。

### 3.5 修法 4：检索策略

- **OA 优先检索式**：`open access` / `site:arxiv.org` / `filetype:pdf` / diamond-gold OA 期刊
- **综述优先**：一篇可读综述替代多篇付费原文（引用其观点并标 `[综述]`）
- **命题人·教学期刊优先**：本次实测蔡志杰文官网免费给摘要 + 引用格式 + 参考文献表，其方法框架（快速判别法 + 改进二分法）即本题标准解法

### 3.6 验收指标（下次 run 对比本次）

| 指标 | 本次 | 目标 |
|---|---|---|
| 权威源（期刊/会议/命题人）达到 L1 的数量 | 0 | ≥3 |
| 无 DOI / 核验失败条目 | ≥1 | 0 |
| 数值锚点标注来源性质 | 未标 | 100% |
| 文献阶段墙钟 / agent 回合 | 0.42h | 不增 |
| 池内标题完整（非截断） | 10 条截断 | 100% 完整 |

---

## 4. 其他结转项（本会话早前已定，等 run 后一并处理）

| 项 | 状态 / 条件 |
|---|---|
| test/ 夹具 smoke 回归（新 shell + 新 prompt 组合，quick 2 问） | run 结束后必做：验证主流程 boot、resume 防覆盖、ensureEnv、PYLINE 组合不破流程 |
| AI 使用详情报告第 6/7 章 | 用真实 run 数据回填替换位后重新导出 PDF（pandoc + ctexart 命令见会话记录） |
| reasoningEffort: high → medium | 用户决定项，未定 |
| 评审探针预算严格度 | 质量权衡，待 run 效果评估 |
| 论文侧 `ai_tool` 参考文献键 | 模板默认写 Claude，提交前须与真实模型核对 |
| README.html（402KB 未入库） | commit 或 gitignore，未决定 |
| 当前 22+ 个未提交改动 | 提交决策未做（分支 refactor-v3，已建 PR） |
| test/perf/libs（275MB numba） | 确认后删除 |

### 4.1 draft 体量治理（2026-09-10 定，**等本跑结束后一次性落地**）

实测（2026 A 题 run 进行中 vs 2025 国赛全量 run）：`draft.md` 本次 q1 = **129 KB / 77.6k 字符 / 449 行**，其中「修订记录」节 **22.8k 字符（29%）**、且**两套尝试周期的记录并存**；2025 跑 q2 = 62 KB（修订记录占 30%）、q3 19%、q4 13%；一轮过的 q1 只有 12.7 KB / 6.8k 字符 —— 即**增量的绝大部分来自修订环节，不是方案本身**。

四个原因与四条改法（**只改提示词，不新增 agent 会话**）：

| # | 原因 | 改法 | 落点 |
|---|---|---|---|
| 1 | 每轮修订「覆盖写回」整份 draft，文件只增不减；3 轮 × 2 次尝试 → 后几轮在最大文件上全量重写（总量近似平方级） | 修订改「精准手术」：只改受影响小节，未受影响小节原样保留，**禁止整篇重写**（措辞可抄 phase-12 的「精准手术，不重写整章」） | 壳 |
| 2 | 「逐条回应」被落成 draft 顶部「修订记录」节，旧轮不删（还跨尝试叠加） | 修订记录移出 draft → `04-formulation/revision-log.md`；draft 只留当前正文 + 一行「已处置意见索引」 | 壳（主）+ phase-04 一句 |
| 3 | 全仓无任何篇幅上限（只有 `summary≤200字`、ledger `≤50字`）；模板要求 9 个必填节 + 每条公式「动机→推导→含义」 | draft 篇幅预算：主方案 ≤8k 字符、全文 ≤12k 字符（一轮过时实测 6.8k 可达），超预算须在 summary 写明理由 | phase-04（阈值待用户定） |
| 4 | §5「先期验证 + 证据键表」15.3k 字符挤进 draft，与 `probes/manifest.json`、`results.json` 重复 | draft 里压成 3–5 行「已核验项 → 探针键」，明细留池；`_common.md §4` 补一句「证据清单同样只写锚点」 | phase-04 + `_common.md §4` |

**落地状态（2026-09-11）**：**模板侧已落** —— 第 3 条（draft ≤12k 字符）与第 4 条（证据键表 → `verification.md`）随 `phase-04-formulation.md` 新增的「产物与篇幅预算」节完成（台账归属表 + `wc -m` 自检进完成标准）。**壳侧待落**：第 1 条（修订改精准手术）与第 2 条的写入方（修订节点把「意见→处置」写进 `revision-log.md`）—— 因此本跑里 q2–q4 的 formulator 会按新结构产出，但修订节点仍按旧壳提示词把记录写回 draft，预算可能被撑破；评审侧的「字数核对」项也留到壳一起落（避免当前跑因"超预算"反复判必须改而空转）。

### 4.2 读入负担治理（纯提示词；2026-09-11 已落 7、1、2）

实测依据（DSH 会话记录）：43 会话 / 1781 步 / 新增输入 4.03M / 输出 2.90M / **缓存重读 252.7M**；单会话峰值上下文 395k（`contextWindow=1000000`、`config.maxTokens=256000`）；单步平均 prompt ≈144k 其中 142k 是缓存重读 —— **「几 M token」是跨会话来回复读的累计，不是窗口问题**。draft 实测 109.6k 字符，其中约 85% 是台账而非方案（方案本体 ≈16k）。

**已落（`prompts/*.md`，对尚未开始的阶段立即生效）**

| # | 改法 | 落点 |
|---|---|---|
| 7 | draft 篇幅预算 ≤12k 字符 + 台账归属表（修订记录 / 证据 / 交接 / 勘误各自归位，draft 只留行内指针）+ 完成标准加 `wc -m` 自检 | `phase-04-formulation.md`；`stage-manifest.json` 给 implementation / computation / sanity / robustness 补 `handoff.md` 依赖（壳启动时载入 → 下一跑生效） |
| 1 | 读入范围：**被评审对象必须整体读**；参考件（self-check / baseline / ledger / 上轮评审）>20KB 时先 `grep -n` 定位再 `offset/limit` 局部读；同会话已读小节不重读 | `_common.md §3` + 三份 `formulation-reviewer-*.md` |
| 2 | 评审文件瘦身：只写判定 + ≤5 条意见 + 证据索引表；**必留可机械复核三件套（结论 / 证据键 / 原文行号或哈希）**；复算叙述、命令清单、上游复述不写 | 三份 `formulation-reviewer-*.md` |

**生效边界（判断"改这个会不会影响正在跑的那一跑"时用）**：`workflows/math-model.js` 与 `prompts/stage-manifest.json` 在 run 启动时载入内存 → 改动只在**下次 run / 下一次 `resume`** 生效；`prompts/*.md` 是每个子代理执行时才 `Read` → 改动**立即影响尚未开始的阶段**。跑动中改前者=冻结无感，改后者=半途换规则（同一跑里 q1 与 q2–q4 口径分叉）。

**待落（第二批，质量风险较高，待第一批跑一轮对比后定）**：写作阶段按章最小输入集、`baseline-registry.md` ≤6k、禁止复述上游（仅约束中间产物之间，论文正文必须写全）。
**不落**：探针输出截断 —— 与 §5「明确不做：缩短对抗评审的探针深度」冲突。
**回滚判据（落地后第一跑对比）**：每问「必须改」条数、`NEEDS_REVISION` 率、05/06 返工次数、终审 P0 数；若「必须改」显著下降而返工不降 → 判为**漏判**（评审看得更少导致的沉默失败），回滚第二批。
**共性风险**：提示词是软约束，各 agent 执行松紧不一 → 同一篇论文里 q1 与 q3 的评审深度可能不一致，损害可比性；故每条都限定适用条件（文件类型 / 是否评审对象 / 大小阈值），落地后按上面的回滚判据对照。

### 4.3 嵌套核验的成本纪律（2026-09-11 已落第一批）

**触发证据（本跑 q2 `06-computation` 实测）**：空间阶梯探针（601 s 窗 × 逐级规则 `substeps_k = max(256, 256(n/3200)²)`）内步数 = 601×(256+256+256+1024) = **1,077,088**；实测单内步 1.96 ms（n=800）～3.38 ms（n=6400）⇒ 预估 **~51 min**，撞 `probe_cache --timeout 3600`；agent 41 min 时 kill ⇒ **已完成 3 档随 kill 全废**（`capture_output` + 只在成功退出时写结果缓存）。对照：生产主体全窗（10,800 s、n=3200、substeps=2）墙钟仅 **63 s** ⇒ 核验成本 ≈ **50× 求解成本**。单价与网格几乎无关（单元数 ×8 只涨 1.7×）⇒ 成本 ≈ 内步数，**唯一杠杆是减少内步数**。

**已落（第一批：只加「估 / 缩 / 落盘 / 并行」，不改任何判据含义）**

| 改法 | 落点 | 生效 |
|---|---|---|
| 「嵌套核验的成本纪律」六步（估→比→缩→落盘→并行→留档）+ ≤30 s 标定片段 + **缩窗优先**（窗长 → 档数 → 精度） | `docs/performance.md` §6.1（规则只此一处，避免读入负担） | 立即（按需 Read） |
| 预算 = min(单次 ≤15 min, **8× 同场生产主体墙钟**)；**先估后跑**；`perf` 增 `costEstimate_s/budget_s/tiers/shrink` | `phase-06-computation.md` §5 | 立即 |
| 探针成本纪律 1 行（所有探针，含评审/对抗/敏感性） | `_common.md` §5.2 | 立即 |
| 成本账进 sanity 核查（`costEstimate_s` 缺失、墙钟 > 8× 生产、未逐档落盘 ⇒ warning + 「中断即全废」风险） | `phase-07-sanity.md` | 立即 |
| **字面**注入 06/09 成本纪律（防散文漂移） | `workflows/math-model.js`（`COSTLINE`） | 下次 run / resume |
| `--budget/--estimate` 预检（超预算拒绝 rc=3 + 缩窗比例建议）+ `pc.checkpoint_put/get` 分档**原子**落盘与复用 + 超时保留已完成档并提示 | `scripts/probe_cache.py` | 立即（按调用读脚本） |
| 回归：dryrun 7 模式 + smoke 20 用例（新增 16/17/18：预检拒绝 / 分档复用 / 超时保留） | `test/` | — |

**为什么必须有机械锚点**：第 7 条（draft 篇幅预算）已实测证明纯散文会漂——prompt 里确实带了「≤12k 字符」（18 个子会话命中），q2 draft 仍写到 **94,971 字符**（`baseline-registry.md` 77 KB vs 预算 6k）。故本批把「必须成立」的部分（预检、落盘）压进脚本与壳的字面注入。

**待第二批（改评审口径，需一次对照跑）**：sanity 判据由 warning 升级为门禁项；`8×` 这个倍数定档（要数据判 5 还是 8）；把散落的 `2 min / 15 min / 900 s` 三个魔数收敛成相对值。
**不落**：把「降精度」提到「缩窗」之前（会改判据含义）；再散新的绝对数字。

---

## 5. 明确不做

- 换上游 provider / 固定单一后端（用户按价格与性能主动选择 `codingpaln`）
- 缩短对抗评审的探针深度（质量资产，只优化其成本，不降深度）
- **文献「待人工获取清单」（`gaps.md`）**：已否决 —— 不为付费全文设计人工补齐回路；付费条目止步 L2/L3，靠 §3.2 分级规则合法引用 + §3.5 OA 替代策略补足
- **门禁强制复用声明**：已否决 —— 强制门禁不必要，复用改由"让复用比重写更省事"驱动（§1.3-5）
- **重复实现静态聚类审计脚本**：已否决 —— 只增加无用计算；度量只保留免费项（§1.3 末）
- **draft.md 整读治理（增量协议 / 范围读 / 重读率指标 / 产物双轨）**：~~已否决~~ → **改为「待裁决」**（§0.2 C1：原否决理由依赖 §1.1 会话复用，而后者不可实现；赛前不动）
- **§1.1 会话复用**：**不可实现**（workflow hook 无 session 句柄，见 §0.2 C1）——不要再次尝试在壳内实现
- **§1.3-4「壳注入可复用资产清单」**：依赖已暂缓的 pool/probes manifest，本次未实施（见 §0.2 C7）
- **其余上下文瘦身措施**（规范文档分节化 / 题面切片 `00-problem.<q>.json` / 上下文预算表 / 写作阶段输入按章切分）：本次未采纳（2026-09-10 决策），如需重新评估以 §1.3 的两条采纳项实施后数据为准
