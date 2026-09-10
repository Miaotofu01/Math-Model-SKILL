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
4. 返回 {status:"PASS"|"NEEDS_REVISION", artifact_path, summary≤200字}；**PASS = 没有「必须改」意见**；建议级意见不阻塞

**评审节点**（三个视角并行）**不修改 state.json、不追加 ledger.md**（并行写竞态，收束节点统一写）；**修订节点**（在并行块之后串行执行）**追加 ledger 一行、但不改 state.json**。评审 agent **不直接改 draft.md**（修订由调度壳的修订节点完成），只从本视角评审，不代演其他视角。

## 3. 工具纪律（减回合——会话耗时主因）

- **并列读**：一次 `Read` 把所有需要的文件一起读入（`Read a.md、b.md、c.md`），禁止逐文件往返、禁止同文件反复重读。
- **一次跑完**：一组命令一次 bash 执行并统一 `ls` 校验；禁止逐图/逐文件微循环。
- **落盘即验证**：产物写完后 `ls` 确认真实存在，再在报告里写路径。

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

- 规范源：`<技能根>/scripts/primitives.py`——**只装机制与判据，不装任何单题内容**（条目以 `--list` 为准）。可进本文件者须同时满足「库不提供 + 口径敏感 + 领域中立（纯数学定义，不含题目建模选择）」，且已有 ≥2 个不同题的复用证据；单题条目写 `pool/problem/<题>/`。`--selftest` 自带**暴力对拍**，`--manifest` 出对拍值与实测耗时
- 首次使用：`cp <技能根>/scripts/primitives.py pool/primitives.py`，此后 run 内一律 `import` 复用（run 级副本保证产物自包含）；`python pool/primitives.py --manifest pool/manifest.json` 生成清单（签名/单位约定/返回语义/依赖/版本/对拍值/实测耗时）
- 改原语必须 `--selftest` 全绿 + 在 manifest 递增版本号（版本参与探针缓存指纹）
- 题专用实现（运动学、决策变量域、目标函数、判据口径）写 `pool/problem/<题>/*.py`，题目参数外置 `const.json`；**不要**塞进题无关原语
- 题专用核心**必须登记** `pool/problem/manifest.json`（手写，无工具生成）：`{"entries":{"<模块.函数>":{"口径":"<一句话>","单位":"…","被复用":["q1","q4"],"对拍值":"<可选>"}}}`——它是后问发现「已有同口径实现」的唯一入口
- **改池必须递增版本**：编辑 `pool/primitives.py` 后重跑 `--manifest`，**退出码 1 表示「内容变了但 VERSION 未递增」**（会让探针缓存静默命中过期结论）→ 递增 VERSION 后重跑，**不是工具故障、不要跳过**
- **import 路径口径**：脚本不在 `pool/` 里时 `import primitives` 默认会失败（Python 只把**脚本所在目录**放进 `sys.path`，不是 cwd）→ 用 `PYTHONPATH=<outputDir>/pool:<outputDir> python …`，或脚本首行 `import probe_cache as pc; pc.bootstrap_sys_path()` 后再 import 池；走 `probe_cache.py --run` 时已自动注入。**撞到 ModuleNotFoundError 一律先修路径，禁止把池中实现内联抄一份**
- **进池判据（rule of two：同一口径出现第二次就提升，禁止再写副本）**——须同时满足：① 会被 ≥2 个小问/阶段调用；② 口径已固化（单位/坐标系/场景作用域明确，题目参数外置 `const.json`）；③ 纯函数优先（输入→输出、无副作用、不依赖某问私有中间产物）；④ 有对拍值或库函数交叉核对能证明"同一口径"；⑤ 是性能敏感热路径（慢副本代价 > import 代价）
- **判据的机械验证**：写完核心代码后跑 `python <技能根>/scripts/reuse_lint.py --scan --root <outputDir>` —— 它把函数规范化成骨架聚类，报出「同形实现出现在 ≥2 个文件」的组（含建议权威、是否已登记、是否跨小问）；扫出的组就是对「该进池」的客观候选，**后写份一律改 import**，口径不一致则在产物里写明差异并各自登记 `scope`
- **不进池（避免池变成垃圾场）**：一次性 EDA/画图/表格脚本（留本问阶段目录）；只服务单个小问的口径（留本问目录并在 manifest 标 `"scope":"q3"`）；口径仍在探索、还会改动者（**固化后再 promote**，提前进池会让下一个人复用到一个还在变的实现）；依赖某问私有数据路径/中间产物的胶水；一行的库函数包装（如 `np.clip`）
- **晋升阶梯（只升不降；新写任何核心前先自问"这是第几次需要它"）**：本问阶段目录 →（第二次需要）→ `pool/problem/<题>/` 并登记 manifest 的 `口径/单位/被复用/对拍值` →（去掉题目参数仍成立）→ `<技能根>/scripts/primitives.py`（走 `--selftest` 全绿 + 版本号递增）。**第 2 次需要某口径时不得再写新副本**——这是上次 4 份 `core.py` 复现的唯一入口
- 背景（勿重演）：上次 run 出现 4 份同类 `core.py`、6 个核心函数各重复 3 次、同一口径的实现散在 6 个文件 18 处

### 5.2 探针池（评审/对抗/敏感性的重计算）

- 固定位置 `probes/<角色>/<目的>.py`（角色：judge / adversary / application / sanity / robustness / data（02 阶段）/ impl（05 阶段）；其它情形用 `other`）；**禁止**再往 `/tmp` 写一次性脚本后重写（上次 run：53 个一次性脚本 / 231 次写入）
- 结果缓存：`python <技能根>/scripts/probe_cache.py --run probes/<角色>/<目的>.py --inputs '{...}' --purpose <用途> --role <角色>`；指纹 = 原语版本 + 脚本内容 + 输入 + 配置 → 命中秒回（实测 2.0s → 0.06s），改脚本或改输入自动失效，不会读到过期结论
- 脚本内用：`import probe_cache as pc` → `pc.main_with_cache(compute, purpose=..., inputs=..., primitives_version=P.VERSION)`（`compute` 是纯函数，返回可 JSON 序列化的 dict）
- **路径口径（重要）**：探针脚本与缓存都在 **outputDir 根**下（`<outputDir>/probes/…`），而你的 shell cwd 未必是 outputDir → 命令前先 `cd <outputDir>`，或显式设 `PROBE_CACHE_DIR=<outputDir>/probes/results`、`PROBE_MANIFEST=<outputDir>/probes/manifest.json`；`--run` 已自动注入 `PYTHONPATH=<outputDir>:<outputDir>/pool`（探针可直接 `import primitives`），直接 `python probes/…` 时需自行加前缀或调 `pc.bootstrap_sys_path()`
- 探针 **stdout 只输出 JSON**；每跑一次自动登记 `probes/manifest.json`（用途/输入/输出契约/耗时/依赖原语）

### 5.3 其它复用

同小问前序产物、`pool/problem/<题>/`（题专用核心）、前序小问的 `02-data/`、`05-implementation/code/` 与 `06-computation/` 里已有的同口径实现 → import 复用；复用前核对常量/维度/场景作用域一致，不一致**禁止**复用并在产物里写明差异。

## 6. 技能级工具与文档路径

**技能根** = 你读到的阶段模板文件（`.../prompts/phase-XX-*.md`）所在目录的**上一级**。规范文档在 `<技能根>/docs/`（`writing-and-format.md`、`flowchart-drawing.md`、`performance.md`），工具在 `<技能根>/scripts/`：

| 脚本 | 用途 | 用法（python 用调度壳注入的解释器） |
|---|---|---|
| `scripts/figure_lint.py` | 出图机械自检：流程图 HTML/SVG 规范（网格/正交/遮罩间隙/皮肤 token）、绘图脚本 AST（下划线字面量/科学计数法/标题/硬编码数字/图例缺失）、PNG（墨迹贴边 ≥8px、尺寸、空图）；`--render` 额外执行脚本做渲染内省（刻度千分位、图例遮挡/裁切） | `python <技能根>/scripts/figure_lint.py --py intermediates/q{id}/08-visualization/plot_figures.py --png intermediates/q{id}/08-visualization/figures/*.png --svg …/*.html [--render] [--json lint.json]` |
| `scripts/primitives.py` | 通用原语池 + 登记/自检框架（条目用 `--list` 查；**单题条目不入池**，写 `pool/problem/<题>/`） | `python <技能根>/scripts/primitives.py --selftest` ／ `--manifest pool/manifest.json` ／ `--list` |
| `scripts/probe_cache.py` | 探针池结果缓存（指纹＝原语版本+脚本+输入+配置，命中秒回）并自动登记 `probes/manifest.json` | `python <技能根>/scripts/probe_cache.py --run probes/adversary/x.py --inputs '{"R":10}' --purpose <用途> --role adversary`；`--list` / `--show <key>` / `--clear` |
| `scripts/reuse_lint.py` | 复用率机械核验：`--scan` 检测同形重复实现（骨架聚类 + 建议权威 + 是否已登记/跨小问；`--strict` 时跨小问重复 → 退出码 1）；`--pairs a.py b.py --inputs '{…}'` 同输入对拍两份实现（一致才允许合并） | `python <技能根>/scripts/reuse_lint.py --scan --root <outputDir>` |
| `scripts/artifact_lint.py` | 数字单一真源检查（关键数字散落 ≥3 处即报错）＋**池登记完整性**（`pool/`、`probes/` 下的 .py 与 manifest 条目双向对账，未登记/幽灵条目各报一条 P1） | `python <技能根>/scripts/artifact_lint.py --root <outputDir> [--json lint.json]` |
| `scripts/lit_verify.py` | 文献池批量核验：DOI 解析 / OpenAlex / Crossref / Semantic Scholar / arXiv / URL 状态 + OA 与证据级建议 + 池数据缺陷（标题截断、缺 DOI） | `python <技能根>/scripts/lit_verify.py --pool pool/literature-pool.md --out <report.md> --json <report.json> --mailto <真实邮箱>` |

> **工具缺失不阻塞**：执行前先 `ls <技能根>/scripts/`。某脚本不存在或运行报错 → 跳过该步、在产物里注明「工具缺失/失败 + 原命令与报错」，并改用人工核对方式完成同样检查；**绝不因工具问题 FAIL 或反复重试**。

## 7. 环境与产物

- 所有 python 执行一律使用调度壳注入的 PYLINE 给出的解释器路径（以 `intermediates/env-report.json` 为准）。
- 所有相对路径基于 outputDir 根；写文件前 `mkdir -p`。
- state.json 的 artifacts 一律用相对 `intermediates/` 的路径；ledger 行格式：`<key>: <status> <产物> <50字内说明>`。

## 8. 不编造

拿不到的数值、文献、数据一律**如实标注可得级别/缺口**（数值缺口→FAIL 并说明；文献→标证据级），禁止填充、近似替代或抄写示例数字。
