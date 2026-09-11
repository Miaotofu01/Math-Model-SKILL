# 公共执行纪律（所有阶段 / 评审 / 修订 agent 共用）

> 本文件与你的阶段模板（`phase-*.md` / `formulation-reviewer-*.md`）**必须同一次并列 Read 读入**；两者冲突时**以阶段模板为准**。
> 这里只写「每个 agent 都要守」的规则；阶段特有规则一律留在阶段模板，不再各抄一份。

## 1. 统一节拍（阶段节点）

1. 读 intermediates/state.json：确认前置阶段已通过（`gates` 中为 `PASS`／`PASS_WITH_WARNING`／`SKIPPED` 三者之一即视为通过），否则返回 {status:"FAIL", ...}
2. 读依赖文件（本阶段的 deps，路径已由调度壳注入）
3. 执行本阶段任务，写产物到指定路径
4. 更新 state.json 对应字段 + 追加 intermediates/ledger.md 一行
5. 返回 {status:"PASS|DRAFT|NEEDS_REVISION|FAIL|SKIPPED|PASS_WITH_WARNING", artifact_path, summary≤200字}

## 2. 统一节拍（评审 / 修订节点）

1. 读依赖文件（评审模板、待评审产物，以及上轮同视角评审文件——若存在）
2. 独立完成本视角工作（self-check 与其它视角意见仅供参考，须独立核验）
3. 意见/修订写入调度壳指定的路径
4. 返回 {status:"PASS"|"NEEDS_REVISION", artifact_path, summary≤200字}；**PASS = 没有「必须改」意见**；登记级/建议级意见不阻塞（三视角共用的分层判据见 §9）

**评审节点**（三个视角并行）**不修改 state.json、不追加 ledger.md**（并行写竞态，收束节点统一写）；**修订节点**（在并行块之后串行执行）**追加 ledger 一行、但不改 state.json**。评审 agent **不直接改 draft.md**（修订由调度壳的修订节点完成），只从本视角评审，不代演其他视角。

## 3. 工具纪律（减回合——会话耗时主因）

- **并列读**：一次 `Read` 把所有需要的文件一起读入（`Read a.md、b.md、c.md`），禁止逐文件往返、禁止同文件反复重读。
- **只读需要的小节**（与上一条配套，不是相反）：并列读入的是**本次判断真正需要的文件与小节**，不是"目录里所有文件"。判定条件：
  - **被评审/被核验/被修订的对象**（`draft.md` 等）**必须整体读**——局部读会漏掉跨节矛盾，禁止对评审对象做局部读；
  - **参考件**（上游产物、`self-check.md`、`baseline-registry.md`、`ledger.md`、cross-review 报告、上一轮评审文件）单个 >20KB 时：先 `grep -n` 定位相关小节，再用 `Read` 的 `offset/limit` 局部读；
  - 确需整读的参考件（例如本视角的上一轮意见要逐条核对），整读并在产物里说明理由。
- **一次跑完**：一组命令一次 bash 执行并统一 `ls` 校验；禁止逐图/逐文件微循环。
- **长任务后台化（禁空转）**：>60 s 的命令（求解/探针/分片/渲染）一律后台起（`run_in_background: true`，或 `nohup … > <日志> 2>&1 &`），启动后**立刻做不依赖它的工作**（并列读、写报告骨架/表格、备下一批脚本），再用 `job_output`/日志尾部收结果；**禁止 `sleep` 空转轮询**。细则与"一次规划、一批启动""先小样后整批"见 `<技能根>/docs/performance.md §2.1`（案例依据见仓库 `docs/prompt-audit-2026-09-11.md` §16）。
- **落盘即验证**：产物写完后 `ls` 确认真实存在，再在报告里写路径。
- **单行 ≤2000 字符（写侧纪律）**：read 工具**按行硬截断**，超限时读者只看到前 2000 字符，行末的 `(line truncated to 2000 chars)` 极易被忽略 ⇒ 长表逐行、长 JSON 逐项换行、长文本分段；确需超长内容**外置同名 `.md` + 键内留「摘要 + 指针」**（例：`intermediates/00-problem.description.md`）。boot 五件更严：单行 ≤1500 且单文件 <50 KiB。

## 4. 数字单一真源（硬纪律）

- 关键结果数字**只写在** `intermediates/q{id}/06-computation/results.json`（各问数值权威）与 `intermediates/12-writing/fact-sheet.md`（全篇唯一数字来源）。
- 其它产物（draft.md / assumption / sanity-report / robustness / question-summary / figure-manifest / 绘图脚本 / 论文正文）**只写锚点引用**，不重复抄数值，例：`<关键符号> 见 results.json#q2.results.<分点>.keyValues`。
- 例外（不算分叉）：题面给定常量与参数、年份、代码内部可控参数（迭代数/网格分辨率/随机种子）——但**引用时仍须写明出处**（`00-problem.json` 或代码常量名）。
- 同一关键数字（≥5 位有效数字，或 ≥4 位整数）在产物中出现 ≥3 处 → 视为口径分叉风险，必须收敛到 results.json（机械检出用 `artifact_lint.py`，见 §6）。
- 绘图脚本**不得硬编码关键结果数值**：一律从 results.json 读取；样式/布局参数（figsize/dpi/fontsize/坐标范围）不受此限。

## 5. 复用纪律（禁止重写同口径核心）

**可复用资产清单**：壳把 `pool/manifest.json`、`pool/problem/manifest.json`、`probes/manifest.json` 列进每个阶段的并列 Read，并给评审/修订注入启动快照。**以清单文件为唯一权威**（快照可能已过期，尤其本 run 前段新建的资产）；文件已存在 → 直接 import 复用，**禁止再 `cp` 覆盖**（会丢掉 run 内改动、版本号与探针缓存指纹脱钩）；确未建立时才按下面就地建立。
**共享区布局（勿混）**：`<outputDir>/pool/` 是 run 级共享池——顶层 `literature-pool.md`（文献池）、`external-data/`（外部数据）、`primitives.py` + `problem/`（**代码池**，各带 manifest）；`<outputDir>/probes/` 是探针池（`<角色>/<目的>.py` + `results/` 指纹缓存 + `manifest.json`）。两者都在 **outputDir 根**下，不在 `intermediates/` 里。

### 5.1 原语池（题无关，可跨题带走）

- **见 `_pool.md`**（规范源 `primitives.py` 的进池判据、首次 `cp` 与 `--manifest`、VERSION 递增守卫、题专用核心登记、`PYTHONPATH` 口径）——壳对写代码的阶段（02/04/05/06/07/08/09）一并注入该文件。

### 5.2 探针池（评审/对抗/敏感性的重计算）

- 固定位置 `probes/<角色>/<目的>.py`（角色：judge / adversary / application / sanity / robustness / data（02 阶段）/ impl（05 阶段）；其它情形用 `other`）；**禁止**再往 `/tmp` 写一次性脚本后重写
- 结果缓存：`python <技能根>/scripts/probe_cache.py --run probes/<角色>/<目的>.py --inputs '{...}' --purpose <用途> --role <角色>`；指纹 = 原语版本 + 脚本内容 + 输入 + 配置 → 命中秒回，改脚本或改输入自动失效，不会读到过期结论
- 脚本内用：`import probe_cache as pc` → `pc.main_with_cache(compute, purpose=..., inputs=..., primitives_version=P.VERSION)`（`compute` 是纯函数，返回可 JSON 序列化的 dict）
- **路径与环境四律（硬约束；违反的后果是报错或"静默写到别处"；依据见仓库 `docs/prompt-audit-2026-09-11.md` §16）**：
  - **① 绝对路径**：本 run 根 = 壳注入的 `<outputDir 绝对路径>`。**一切工具调用**的文件参数（`present` / Read / Write / Edit / Bash 参数）**一律写绝对路径**；**尤其 `present`**——它按**会话 cwd** 解析，而会话 cwd 未必是 run 根。**禁止**用相对路径 `mkdir`/写文件（会在会话 cwd 下留**影子目录**，无任何报错）。
  - **② 解释器**：一律 `"$PY"=<outputDir>/.venv/bin/python`（以 `intermediates/env-report.json` 为准，缺失才退系统 python3）；**禁止裸 `python3`**。
  - **③ 池导入**：直接跑脚本时加 `PYTHONPATH=<outputDir>:<outputDir>/pool`，或脚本首行 `import probe_cache as pc; pc.bootstrap_sys_path()`（`probe_cache.py --run` 已自动注入）。撞 `ModuleNotFoundError: problem/properties/probe_cache` **先修路径，禁止把池实现内联抄一份**。
  - **④ 临时文件**：一律 `<outputDir>/.mm-tmp/`（用完即删）；**不要 `/tmp`**（本环境 `/tmp` 只读、`/dev/shm` 跨调用重置）。
- **探针路径口径**：探针脚本与缓存都在 **outputDir 根**下（`<outputDir>/probes/…`），shell 命令前先 `cd <outputDir>`，或显式设 `PROBE_CACHE_DIR=<outputDir>/probes/results`、`PROBE_MANIFEST=<outputDir>/probes/manifest.json`
- 探针 **stdout 只输出 JSON**；每跑一次自动登记 `probes/manifest.json`（用途/输入/输出契约/耗时/依赖原语）
- **探针预算（权威处）**：单探针 ≤2 分钟、整轮验证 ≤10 分钟（评审/修订的验证探针同此限）；确需大计算 → 粗采样/解析核验代替穷举
- **清单体积纪律**：`probes/manifest.json` 一行一条目、单文件 ≤48 KiB、条目 ≤200（超出自动移入 `probes/manifest.archive.json`）；查复用/查重时**两份都要看**（`artifact_lint` / `reuse_lint` 已把归档条目算作已登记）
- **成本纪律（所有探针，含评审/对抗/敏感性探针）**：嵌套核验（阶梯/扫参/对拍/bootstrap）**先估后跑 + 逐档落盘 + 档间并行**——估算式与缩窗优先级见 `docs/performance.md` §6.1；`--run` 前带 `--budget <秒> --estimate <预估秒>` 预检（超预算会拒绝执行并给缩窗建议）；长任务分档用 `pc.checkpoint_put/get`（kill 后已完成档仍可复用）

### 5.3 其它复用

同小问前序产物、`pool/problem/<题>/`（题专用核心）、前序小问的 `02-data/`、`05-implementation/code/` 与 `06-computation/` 里已有的同口径实现 → import 复用；复用前核对常量/维度/场景作用域一致，不一致**禁止**复用并在产物里写明差异。

## 6. 技能级工具与文档路径

**技能根** = 你读到的阶段模板文件（`.../prompts/phase-XX-*.md`）所在目录的**上一级**。规范文档在 `<技能根>/docs/`（`writing-and-format.md`、`flowchart-drawing.md`、`performance.md`），工具在 `<技能根>/scripts/`：

| 脚本 | 用途 | 用法（python 用调度壳注入的解释器） |
|---|---|---|
| `scripts/figure_lint.py` | 出图机械自检：流程图 HTML/SVG 规范（网格/正交/遮罩间隙/皮肤 token）、绘图脚本 AST（下划线字面量/科学计数法/标题/硬编码数字/图例缺失）、PNG（墨迹贴边 ≥8px、尺寸、空图）；`--render` 额外执行脚本做渲染内省（刻度千分位、图例遮挡/裁切） | `python <技能根>/scripts/figure_lint.py --py intermediates/q{id}/08-visualization/plot_figures.py --png intermediates/q{id}/08-visualization/figures/*.png --svg …/*.html [--render] [--json lint.json]` |
| `scripts/primitives.py` | 通用原语池 + 登记/自检框架（条目用 `--list` 查；**单题条目不入池**，写 `pool/problem/<题>/`） | `python <技能根>/scripts/primitives.py --selftest` ／ `--manifest pool/manifest.json` ／ `--list` |
| `scripts/probe_cache.py` | 探针池结果缓存（指纹＝原语版本+脚本+输入+配置，命中秒回）并自动登记 `probes/manifest.json` | `python <技能根>/scripts/probe_cache.py --run probes/adversary/x.py --inputs '{"R":10}' --purpose <用途> --role adversary`；`--list` / `--show <key>` / `--clear` |
| `scripts/reuse_lint.py` | 复用率机械核验：`--scan` 检测同形重复实现（骨架聚类 + 建议权威 + 是否已登记/跨小问；`--strict` 时跨小问重复 → 退出码 1）**＋第二判据「跨问同名同签名」**（骨架不同但同职责重写：名相同 + 参数个数相同，跨小问即候选；**默认只报不阻塞**，`--strict-samesig` 才升为退出码 1；通用名白名单除外）；`--pairs a.py b.py --inputs '{…}'` 同输入对拍两份实现（一致才允许合并） | `python <技能根>/scripts/reuse_lint.py --scan --root <outputDir>` |
| `scripts/artifact_lint.py` | 数字单一真源检查（关键数字散落 ≥3 处即报错）＋**池登记完整性**（`pool/`、`probes/` 下的 .py 与 manifest 条目双向对账，未登记/幽灵条目各报一条 P1） | `python <技能根>/scripts/artifact_lint.py --root <outputDir> [--json lint.json]` |
| `scripts/lit_verify.py` | 文献池批量核验：DOI 解析 / OpenAlex / Crossref / Semantic Scholar / arXiv / URL 状态 + OA 与证据级建议 + 池数据缺陷（标题截断、缺 DOI） | `python <技能根>/scripts/lit_verify.py --pool pool/literature-pool.md --out <report.md> --json <report.json> --mailto <真实邮箱>` |

> **工具缺失不阻塞**：执行前先 `ls <技能根>/scripts/`。某脚本不存在或运行报错 → 跳过该步、在产物里注明「工具缺失/失败 + 原命令与报错」，并改用人工核对方式完成同样检查；**绝不因工具问题 FAIL 或反复重试**。

## 7. 环境与产物

- 所有 python 执行一律使用调度壳注入的 PYLINE 给出的解释器路径（以 `intermediates/env-report.json` 为准）。
- 所有相对路径基于 outputDir 根；写文件前 `mkdir -p`。阶段模板里的 `q{id}` 与 `q1` 均指 ctx 中的小问 ID（run 级阶段 q=null）。
- state.json 的 artifacts 一律用相对 `intermediates/` 的路径；ledger 行格式：`<key>: <status> <产物> <50字内说明>`。

## 8. 不编造

拿不到的数值、文献、数据一律**如实标注可得级别/缺口**（数值缺口→FAIL 并说明；文献→标证据级），禁止填充、近似替代或抄写示例数字。

## 9. 评审通用规则（评审 / 修订节点共用；其它节点可跳过）

> 三份 `formulation-reviewer-*.md` 只写**视角特有**标准与判据，通用规则以本节为唯一真源；冲突时以本视角模板为准。读入范围见 §3，探针预算/卫生见 §5.2。

### 9.1 边界与判定分层

- **只从本视角评审**，不代演其它视角；**不直接改 `draft.md`**、不改 state.json/ledger.md（修订与收束由壳的专职节点做，见 §2）。
- 依赖文件缺失 → **NEEDS_REVISION** + summary 说明缺什么；返回值只有 `PASS`/`NEEDS_REVISION`（§2）。
- **必须改（唯一阻塞级）** = 会改变**结论**的问题（各视角判据见本视角模板），或**按 draft 字面落码会得到错结论/错实现**的协议·口径项（须给出「照字面执行会得到什么」的后果）。
- **登记级（不阻塞）** = 不影响结论、只需文本或登记同步：引用键/报告口径错、版本号未递增、台账或表格未同步、作废标记缺失、符号表与正文不一致、措辞歧义、交叉引用失效。**另列，不占必须改额度。**
- **建议级（不阻塞）** = 可改进空间，不影响方案成立。
- **判定规则**：必须改 **0 条 → 返回 PASS**（登记级/建议级各有若干条也判 PASS）；≥1 条必须改 → NEEDS_REVISION。**禁止**为凑条数升格等级——只列会改变结论/会卡住下游的点。
- 上限：**必须改 ≤5 条**（按严重度排序）+ **登记级 ≤5 条**（写成可直接机械执行的补丁：`旧键/旧文本` → `正确键/新文本` + 文件行号，注明「→ 修订节点本轮一并落地」）；每条意见给位置（文件 + 行号/式号）+ 一句「为什么这是问题」；末尾一句话总结（总结什么见本视角模板）。

### 9.2 r≥2 的举证责任与逐条闭环

- **r≥2 新增的必须改负举证责任**（不满足 → 只能标登记级）：① **回归**——上轮修订**引入**的问题（引 `revision-log.md` 轮次小节 + draft 现行行号，并写明上轮文本原样）；② **致命项**——本视角独立核验发现的、会改变结论的错误（给出按现状落码/推导得到的错结论，或可击溃方案的反例/数字）。
- **r≥2 先逐条闭环**：对本视角上轮每条必须改标 `已闭环`（附 draft 现行行号或内容哈希）/`未闭环`；未闭环的**沿用原条目号**（如 R2-1），不得换措辞重新编号；已照改而仍不成立的，须给出**新证据**（改后原文/新探针键）才可继续标必须改。

### 9.3 产物体量与读入范围（三视角同受约束）

- **评审文件结构上限（硬·L1-B）**——把"该短"从形容词变成**可数的形状**：
  - ① 判定 **1 行**（`PASS`/`NEEDS_REVISION` + `必须改 n 条 / 登记级 m 条`）。
  - ② **必须改 ≤5 条**，每条**恰好 4 行**：`- **<ID>【必须改】**<一句话结论>` ／ `  - 位置：<文件>:<行号/式号>` ／ `  - 为什么是问题：≤2 句（含照字面落码的后果或反例）` ／ `  - 怎么改：≤2 句`。
  - ③ **登记级 ≤5 条**，每条 **1 行**（`旧 → 新` 或 `键/行号 → 处置`）。
  - ④ **证据索引表 ≤10 行**（`键 | 一行结论`）。
  - ⑤ r≥2 另附**闭环表**：上轮条目 **1 行/条**（`ID | 已闭环/未闭环 | draft 行号或内容哈希`）。
  - **禁**：复算过程叙述、命令行清单、逐条闭环完整推演、上游复述、代码块/复算表。**例外**：r≥2 的回归/致命举证可写 **≤5 行**最短复现路径。
  - **必留三件套**：结论、证据键、原文行号或内容哈希。
  - **软限**：单份 >15 KB 须在**首行**写一行「超限原因」（warning 级，不阻塞）。
  - 机械核验：`artifact_lint.py` 的 `review.format`（P1）：必须改 ≤5 / 登记级 ≤5 / 无命令行行 / 单份 ≤15 KB（超限须首行给原因）；证据表行数由评审自查（暂不机检，避免误伤）。

- **只写**：① 判定（`PASS`/`NEEDS_REVISION` + `必须改 n 条 / 登记级 m 条`，一句话）；② 必须改 ≤5 + 登记级 ≤5（每条【级别】【位置 = 文件 + 行号/式号】【为什么是问题】【怎么改】，各 ≤2 句）；③ **证据索引表**（探针键 → 一行结论）。**必留可机械复核三件套：结论、证据键、原文行号或内容哈希**——下一轮据此核对「声称已改」是否真改。
- **不写**：复算过程叙述、命令行清单、逐条闭环的完整推演、上游内容复述（留在 `probes/results/` 与探针脚本里，按键取回；出现大段复算表/命令清单即超范围）。**例外（B2）**：r≥2 的回归/致命举证允许 ≤5 行最短复现路径（键 + 输入摘要 + 关键数字，或一条命令）。
- **逐条处置表不在 draft**：每轮「评审意见 → 处置」写 `04-formulation/revision-log.md`（格式见 `phase-04-formulation.md` 产物契约：每轮 `## rN 处置` 一张表 + 条件节），draft 只留 1 行指针。核对「上轮是否真改」读对应轮次小节 + 比对 `draft.md` 原文，**不得因为 draft 里没有处置表就判「未回应」**。
- **读入范围（§3）**：`draft.md` 是评审对象 → **必须整体读**；参考件（`self-check.md`/`baseline-registry.md`/`ledger.md`/上轮评审文件）单个 >20KB 先 `grep -n` 定位再 `offset/limit` 局部读，确需整读说明理由。
- **r≥2 的读法（B4）**：首轮必须整体读 `draft.md`；r2 起可按上轮条目行号（`revision-log.md` 当轮小节）精读，但**必须另做一次跨节一致性抽查**（同一量/阈值/量级/符号在全文各处是否一致），**不得省**。
- **量纲/作用域检查（A5）**：新增或修改的公式/系数/边界项须同时给出**单位**与**适用域**，缺任一 ⇒ 按「会改变结论」判必须改（案例依据见仓库 `docs/prompt-audit-2026-09-11.md` §16）。

### 9.4 评审探针纪律

**复用优先、只做增量核验**（先读 `02-data/eda.md`、`06-computation/results.json`、`data-collection.json` 与 `pool*` manifest/前序产物；**禁止重跑完整求解管线或全量扫描**）；预算与卫生（单探针 ≤2 分钟、整轮 ≤10 分钟；探针写 `probes/<本视角角色>/<目的>.py` + `probe_cache` 缓存、禁 `/tmp`）**见 §5.2**；性能纪律见 `<技能根>/docs/performance.md`（技能根见 §6）。
