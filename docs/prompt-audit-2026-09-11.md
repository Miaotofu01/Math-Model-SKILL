# 提示词技术债审计（2026-09-11）

> 对象：`skills/math-model/prompts/`（21 个 `.md` + 2 个 JSON）+ 调度壳 `workflows/math-model.js` 注入的提示词片段。
> 方法：机械统计（体量／跨文件逐字重复／阈值散落／引用密度）+ 逐节点职责与信息流核对（壳 `ca(...)` 调用点 vs 模板 `§输入`）。
> 状态：§1–§5 已完成；§8 已并入两路深读（公共件+评审件行级废话、跨文件规则图谱）；阶段模板行级废话一路仍在跑。

> **对 §3 的修正（来自深读）**：评审三家的共享块（「验证探针纪律」≈950 字符/份）**不要整块抽进 `_common.md`**。`_common` 每 run 被 ~90 个 agent 会话读，三份 reviewer 模板合计只被 ~36 次读 → 抽公共会把读入成本放大 2.5×。正确做法是**删掉与 `_common` 重复的部分**（≈708 字符/份），视角特有内容各留一份。

## 1. 底账

| 组 | 文件数 | 行 | 字符 | 占比 |
|---|---|---|---|---|
| 阶段模板 `phase-01..13` | 13 | 1,082 | 52,077 | 69% |
| 公共件 `_common.md` + `state-schema.md` | 2 | 157 | 11,427 | 15% |
| 评审三家 `formulation-reviewer-*` | 3 | 136 | 9,167 | 12% |
| 选题三步 `step1/2/3` | 3 | 132 | 3,240 | 4% |
| JSON：`stage-manifest.json` / `response-schema.json` | 2 | 135 | 3,716 | — |
| **合计** | **23** | **1,594** | **79,137** | |

最大单件：`_common.md` 8,379 字符（被每个阶段/评审/修订 agent 每次都读）；最长单文件 `phase-12-writing.md` 112 行。

## 2. 废话与重复

**结论：没有"注水型废话"**——全库态度词只有 3 处（`务必`×1、`充分`×2）。真正的浪费是**同一规则被逐字复制到多个文件**：

| 重复块 | 命中 | 字符 | 性质 |
|---|---|---|---|
| 「公共纪律…见 `_common.md`，同一次并列 Read」头 | 16 文件 | 1,252 | 多余（每个 agent 都读 `_common`） |
| 「调度壳已注入：当前小问 ID…模式…依赖与产物路径」 | 13 文件 | 1,598 | 多余（壳本就注入，无需告知） |
| `writing-and-format.md` 指针两句话（含「缺失时向上/向下探测」） | 9 文件 | 1,851 | 多余（应进 `_common §6`） |
| 评审三家「验证探针纪律」块（5 条） | 3 文件 | 2,842 | **逐字相同**（`diff` 仅 1–2 行差异） |
| 「所有相对路径基于 outputDir 根。」 | 12 文件 | 252 | 多余 |
| 探针卫生（固定位置 + 禁 `/tmp`） | **6 文件** | ~700 | 多余（`_common:63`、三评审、`phase-04:60`、`phase-05:65`） |
| 「53 个脚本 / 231 次写入」历史依据 | 2 文件（`_common:63`、`phase-06:69`） | 一段 | 同一历史复述两次 |

**合计 ≈8.5k 字符（占语料 11%）是复制的规则。** 探针类规则（卫生／预算／缓存）散在 4–6 处；`phase-04:60` 与三家评审块讲的是同一条纪律。

元叙述/历史依据共 5 处 ≈900 字符（最长 `phase-04:85` 314 字）——**建议压缩并指向 `docs/pending-changes.md`**，不删（防复发证据）。

## 3. 耦合与内聚

**编辑耦合（最贵）**：本轮为加「探针成本纪律 + 台账零容差」共改 9 处（`_common`、`phase-04/06/07`、三份 reviewer、壳、2 个脚本），其中 4–6 处是旧副本。

| 规则 | 改一处要记得改 | 建议权威位置 |
|---|---|---|
| 探针卫生 + 禁 `/tmp` | 6 | `_common §5.2`，其余改引用 |
| 探针验证纪律（环境/预算/性能） | 4 | 抽进 `_common §5.2`（净减 1,885 字符，3→1 处） |
| 文档指针（`writing-and-format.md`） | 9 | `_common §6` |
| 壳注入说明 / 公共纪律头 / 相对路径 | 13 / 16 / 12 | 各压半句或整句删 |

**内聚**：`_common.md` 一个文件扛 8 件事，其中 **§5 复用/池 ≈3.4 KB（占 40%）只在写代码阶段用得上**，却让 13 阶段 + 评审 + 修订的每个 agent 每次都读。建议 `§5.1 原语池`（cp／`--selftest`／`--manifest`／VERSION／`PYTHONPATH`）迁 `docs/asset-pool.md`；`§5.2 探针池`留在 `_common`（评审也需要）。

**收益要诚实**：语料可净减 ~10%；但**读入成本收益有限**（每 run 的重读大头是 draft，实测 q1+q2 已 95k 字符，提示词全库才 79k）。真正的收益是**维护性**——不再"改一处必须记得改六处"。

## 4. 节点职责自述审计（防"agent 不知道干啥"）

| 节点（壳内调用点） | 标签 | 角色自述 | 读入（谁给） | 写 | 返回契约 | 缺口 |
|---|---|---|---|---|---|---|
| 契约读取 `loadContracts` | `contracts` | ✗ 无角色句 | 两份 JSON（自读） | — | JSON 包 | 任务具体；缺"只搬运不分析"一句（低风险） |
| 启动批量读 `rfMany` | `read-many` | ✗ 无角色句 | 5 件（自读） | — | 摘要 JSON | `BOOT_SPEC` 已写明字段与禁区，可接受 |
| 环境 `ensureEnv` | `env` | ✓ 标题即角色 | — | `env-report.json` | `{status,artifact_path,summary}` | 完整 |
| 初始化 `initState` | `init` | ✓ | — | `state.json`、`ledger.md` | 同上 | 完整 |
| 阶段 `stagePrompt` | `run:q.s` | ✓「## 阶段 …」+ 执行/产物/state/ledger | `_common`+模板+state+deps+三清单（壳注入） | 模板指定 | `status` | 见 §5（无关注入） |
| 门禁 `gatePrompt` | `gate:gk` | ✓「## 门禁 gk→before：验证 …」 | 「所需文件」（**未列路径**） | `gates`+ledger | `PASS/FAIL` | 读入路径未给（弱，但门禁核对项由 manifest 提供文本） |
| formulator | `formulator` | ✓「【节点1 · formulator】按阶段模板产…」 | 阶段注入 + 自己读 | `draft.md`+`baseline-registry.md`+`symbols.json`+state+ledger | `status` | 完整 |
| 三维自查 | `selfcheck` | ✓「【节点2 · 三维自查】」 | `draft.md` | `self-check.md` | `status` | **未注入 `_common.md`**（拿不到数字单一真源/工具纪律） |
| 评审 ×3 | `review:judge/adversary/application` | ✓（模板首行角色） | `_common`+模板+`draft.md`+`self-check.md`+上轮评审 | `review-rN-p.md` | `PASS/NEEDS_REVISION` | **未给 `baseline-registry.md`、`symbols.json` 路径**（模板却要求核对） |
| 修订 | `revise` | ✓「精准手术…」 | `_common`+`draft.md`+`review-r*.md` | `draft.md`+`revision-log.md`+（必要时 baseline/symbols） | `status` | 完整（baseline/symbols 路径写在提示词里） |
| 收束 | `finalize` | ✓「专职状态节点…唯一职责…」 | `state-schema.md`+`state.json`+`ledger.md` 尾 | `state.json`+ledger | `status` | 完整 |
| 降级 | `degrade:k` | ✓「专职状态节点…唯一职责…」 | 同上 | `state.json`（`SKIPPED`）+ledger | `SKIPPED` | 完整 |
| 单件读 `rf` | `mm` | ✗（一句话任务） | 1 件 | — | 原文/`NOT_FOUND` | 任务明确，可接受 |

**结论**：曾出过问题的"不知道自己职责"类，现在只剩 3 处薄弱（`contracts`／`read-many`／`rf` 无角色句，但任务本身自明）+ 2 处实质缺口（`selfcheck` 缺 `_common`、评审缺 2 个被要求核对的输入）。

## 5. 信息流缺口

### 5.1 该得到的信息没得到（壳 `deps` 未给，但模板 `§输入` 要求读）

| 阶段 | 模板要求读但壳未注入 | 风险 |
|---|---|---|
| `implementation` | `00-problem.json`、`04-formulation/symbols.json`、`baseline-registry.md` | **附件路径唯一来源是 `00-problem.json`**（模板原话）→ 实现可能拿不到附件路径；符号表缺失 → 变量命名漂移 |
| `computation` | `baseline-registry.md`、`symbols.json` | 计算不按预注册判据 → 结果与预注册口径脱钩 |
| `sanity` | `00-problem.json`、`symbols.json` | 核验缺题面常量基准与符号对照 |
| `visualization` | `00-problem.json`、`symbols.json` | 图题/单位/符号与题面不一致 |
| `robustness` | `00-problem.json` | 扰动范围缺题面依据 |
| `literature` | `pool/literature-pool.md` | 跨问文献池不知道存在（`_common:44` 有布局说明，可发现性弱） |
| 评审 ×3 | `baseline-registry.md`、`symbols.json` | **评审被判据架空**：adversary 模板第 24 行要求核对"draft 声称的提升 vs 预注册指标/口径"，judge 要求对照文献——但壳的评审 Read 清单不含这两个文件的路径 |

### 5.2 没用的信息得到了

| 注入 | 出现在 | 问题 |
|---|---|---|
| `{id}/06-computation/results.json` | **`computation` 的 deps** | 那是**本阶段产物**，被当作输入注入 → agent 可能去读旧结果 |
| `handoff.md` | implementation/computation/sanity/robustness 的 deps | 4 个模板的 `§输入` 都没提它：**信息到了但角色没说明**（应写进模板"先读 P0 检验项"） |
| Python 环境行 `PYLINE` | 全部 13 阶段 | 03/10/11/12/13 基本不跑 python（12/13 用 xelatex/pandoc） |
| 可复用资产清单行 | 全部阶段 + 评审 | 03/10/11/12/13 不复用代码 |
| `_common.md §5.1` 原语池规则 | 全部读者 | 只对 02/05/06/08/09 有用（见 §3） |

## 6. 建议分批

**A. 立即落（零语义变化）**：§5.1 的 `deps` 补齐（7 个阶段 + 评审）；§5.2 删 `results.json` 误注入；`handoff.md` 写进 4 个模板 `§输入`；`selfcheck` 注入 `_common.md`；评审 Read 清单补两个路径。
**B. 立即落（纯瘦身，~4.9k 字符）**：§2 表中的样板句（公共纪律头／壳注入说明／文档指针／相对路径）压半句或抽 `_common`。
**C. 需你定**：`_common §5.1` 拆出 `docs/asset-pool.md`；三家评审共享块抽进 `_common §5.2`；`PYLINE`／资产清单按阶段条件注入（壳侧）。
**D. 待并入**：三路深读的行级清单（阶段模板／公共件+评审件／跨文件规则图谱）。

## 7. 复现命令

```bash
cd skills/math-model/prompts
python3 -c "...跨文件重复句统计..."   # 见本文件 §2（脚本在会话记录）
grep -rn '53 个\|231 次' *.md                    # 历史依据重复
python3 - <<'EOF'                                # deps vs §输入 对照（脚本见会话记录）
EOF
```


## 8. 深读审计并入（2026-09-11）

### 8.1 行级废话（公共件 + 评审件，按省字符降序前 12）

| # | 文件:行号 | 类别 | 原文摘录 | 建议 |
|---|---|---|---|---|
| 1 | `judge:24-32` / `adversary:26-34` / `application:23-31` | 重复 | 「验证探针纪律（性能与卫生…）」 | 三份删与 `_common §5.2/§7` 逐字重复的 ≈708 字符，只留「预算 ≤2 min / ≤10 min」+「性能」两行（省 2,124） |
| 2 | `judge:45` / `adversary:47` / `application:44` | 重复 | 「参考件单个 >20KB 时先 `grep -n`…」 | 逐字抄自 `_common §3` → 删，改一行指针（省 591） |
| 3 | `_common:21` | 重复 | 「只从本视角评审，不代演其他视角」 | 三份 L11 与 `state-schema:52` 已同述 → 删尾句（省 296） |
| 4 | `judge:9-10` / `adversary:9-10` / `application:9-10` | 重复 | 「不修改 state.json / draft.md」 | `_common:21` 已同述 → 删（省 246） |
| 5 | `step1:48,60` | 冗余修饰 | `======` 装饰线 | 删（省 80） |
| 6 | `judge:35` / `adversary:37` / `application:34` | 自明 | 「不要列一堆小毛病——评委时间宝贵」 | 删态度句（省 74） |
| 7 | `_common:59` | 重复 | 「背景（勿重演）…」 | 与 L58 同段旧事 → 整行删（省 71） |
| 8 | `state-schema:54` | 重复 | 「原样写入调度壳注入的结论值」 | L34 表已列值域 → 删（省 65） |
| 9 | `step1:30` | **失效引用** | `args.attachments` | 壳参数表无此项 → 删（省 60） |
| 10 | `step2:43,45` | 重复 | 字段定义/判据与 JSON 模板重复 | 合并（省 119） |
| 11 | `judge:42` / `adversary:44` / `application:41` | 冗余修饰 | 「——下一轮据此核对…」 | 删破折号后半句（省 57） |
| 12 | `_common:50,54,58,63,64,79` | 重复/冗余 | `--selftest` 三处、「53 个脚本」广告、Python 常识解释 | 各压一句（省 ~160） |

另有 `state-schema`/`step*` 共 18 条小项（每条 19–45 字符），合计可省 ≈4.5k 字符。

### 8.2 深读新发现的**真缺陷**（不是文风问题）

| # | 类型 | 证据 | 风险 |
|---|---|---|---|
| 1 | **自依赖** | `stage-manifest.json:62` 把 `{id}/06-computation/results.json` 列进 `computation` **自己的 deps** | 壳据此拼注入串 → 阶段 06 提示词把"自己的产物"列为必须存在的依赖，首次运行时不存在，agent 可能直接判 FAIL |
| 2 | **门禁漏检** | `phase-04:92` 要求 4 个台账存在 vs `phase-10:22` 只核 3 个文件 | 04 少写 `revision-log.md`/`handoff.md` 时阶段 10 仍 PASS；而评审三家按 `revision-log.md` 核对 |
| 3 | **孤儿产物（本次手术造成）** | `verification.md`、`errata.md` 不在任何 deps、无任何下游读取点 | 台账外移后它们"写了没人读"；`P04:70,72,92` 要求写、下游不读 → 白写且丢失无人发现 |
| 4 | **漏改残留** | `phase-13:59` 要求写 `13-final/refs.tex` vs `phase-13:70` `--references "$(cat /tmp/refs.tex)"` | 组装读 `/tmp` → cat 失败或装到上一次 run 的陈旧参考文献 |
| 5 | **自相矛盾** | `phase-05:56`「见提示词末尾」 vs `phase-05:62`「阶段指令首行 `## Python 环境`」 | 壳实际追加在**末尾** → 按"首行"找的 agent 找不到 |
| 6 | **死值域** | `response-schema.json:4` 含 `DRAFT`，但壳无任何生产者（`sh:150` 写 `NEEDS_REVISION`） | 4 处消费点仍校验它 → 改/删要同步 4 处，留着永远验证不到 |
| 7 | **隐式契约** | `P04:19` 以 `artifacts["q{id}.assumption"]` 为权威路径，但 `phase-03` 通篇未规定写哪个键 | assumption agent 可能写目录名或旧版文件名 → formulator/judge 取到被拒的旧版建模 |
| 8 | **孤儿上限** | `phase-12:82`（交叉审查 full3/quick1）、`phase-06:27`（修复 3/1）、`phase-03:31`（假设 5 版） | 壳对这些阶段都是**一次 `ca()` 调用**，无轮次控制 → "上限"字面永不生效（改提示词永远不生效） |
| 9 | **三处对齐** | 章节 id/名/顺序散在 `phase-12:39` 表、`phase-13:28` 列表、`templates/assemble_from_template.py` 的 order | 改名漏改 `P13` → 终审按旧名找章「未找到章节」并 FAIL |
| 10 | **黑名单不同步** | `phase-12:77`（8 条）与 `phase-12:89-96`（12 条）两套清单 + `phase-13:42`，权威却在**未被注入**的 `writing-and-format.md §一-14` | 增删术语要改 3 处提示词 + docs，已不同步 |

### 8.3 权威归属（22 条，收敛后"改一处"清单）

| 规则 | 现状副本数 | 建议唯一权威 |
|---|---|---|
| 返回三件套 + `status` 值域 | 8 | `response-schema.json` |
| `gates` 值域 / 恢复跳过集 | 5 | `state-schema.md`（壳读 manifest 常量） |
| ledger 行格式 / 键名 | 7 / 3 | `state-schema.md`；壳抽 `LEDGER_FMT` 常量 |
| `iterations` 语义与增量式 | 2（`SS:24` vs `sh:137`） | `state-schema.md`（写明壳注入式 `旧值+1+r`） |
| 重试/轮次上限（TRY、full3/quick2、修复3/1、假设5版、交叉审查3/1） | 6 | `stage-manifest.json` 新增 `retryPolicy`，壳与提示词都读它 |
| `results.json` 键清单（含 `perf` 8 键） | 2 处正文 + 4 处下游断言 | 新 `prompts/results-schema.md`（06/07/10/11/13 引用） |
| `figure-manifest` 字段集 | 4 | 新 `prompts/figure-manifest.schema.md` |
| 章节 id/名/顺序 | 3 | `templates/assemble_from_template.py` order |
| 数字单一真源 + ≥3 处阈值 | 7 | `_common §4` + `artifact_lint.py` |
| 核验成本预算（≤15 min / ≤8× / 缩窗） | 5 | `docs/performance.md §6.1`（`_common:69` 一句指针） |
| **探针预算（≤2 min / ≤10 min）** | 4（`P04:60` + 三 reviewer，**当前无权威**） | `_common §5.2`（一行数字） |
| 探针位置 / 缓存 / 禁 `/tmp` | 7 | `_common §5.2` |
| 代码池治理（进池判据/晋升/`PYTHONPATH`） | 8 | 拆出 `_pool.md`（只对 02/04/05/06/07/09/11 注入） |
| 技能级脚本 CLI 命令串 | 8 | `_common §6` 表（阶段只写参数） |
| 技能根定义 + 缺失探测 | 10 | `_common:77`（壳 `SD` 是运行时事实源） |
| AI 味清单 + 术语黑名单 + 证据分级 L1–L4 | 3 + docs | `_common` 新增 §9 |
| P0/P1/P2 定级语义 | 3 | `_common` 新增 §9 |
| 「同一次并列 Read」契约 | 16 | 只在壳 `sh:107/158`（`_common:3` 与模板行改陈述句） |
| `00-problem.json` 结构与壳兼容形态 | 4 | `SKILL.md` Step 5 + 声明壳兼容旧形态 |
| 池/探针目录布局 | 5 | `_common §5` 布局段 |
| 示意图 vendored 规则 | 4 | `docs/flowchart-drawing.md` 开头 |
| env python 口径 | 9 | 壳 `PYLINE` 产事实 + `_common:92` |
