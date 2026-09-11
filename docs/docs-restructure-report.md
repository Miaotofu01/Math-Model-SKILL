# 技能根 `docs/` 排版与逻辑归一（批 2）——现状证据 · 归一方案 · 迁移映射

> 范围：`skills/math-model/docs/`（4 份文档）+ 其全部活引用（`prompts/**`、`workflows/**`、`SKILL.md`、`SKILL.claude.md`、`scripts/*.py`）+ 仓库根 `docs/prompt-audit-2026-09-11.md` 的 §9 失效定位指针。
> 前置：批 1 已把 `prompts/_common.md` 重排为 §1–§5。批 2 只做**编号/层级/指针/位置**，**不动任何数字、阈值、预算、命令**。
> **声明：规则语义不变**——本批未增删任何规则，只改编号形态、指针限定与内容位置。

---

## 0. 结论摘要

最初提出的 5 类病是**假设**，本批逐条实测，结果为 **2 类确证 / 1 类部分确证 / 2 类证伪**：

| # | 假设病 | 判定 | 一句话证据 |
|---|---|---|---|
| 1 | 编号与层级混乱 | **部分确证** | `writing-and-format.md` 用 `§〇/§一..§六` + 1 个未编号 `###`；其余 3 份用 `§N`/`§N.M`。**但每份文档内部自洽**，不是"混乱"而是"两套记法并存" |
| 2 | 同一类信息多处重复 | **部分确证** | docs↔prompts **逐字重复 = 0 行**（≥40 字符行交集为空）；概念级重复确证 1 处（图注 token 双写）+ 1 组（成本纪律 5 处，属批 1 已记录的待决） |
| 3 | 失效/不一致指针 | **确证（范围很小）** | `docs/` 内部 14 处指针**全部有效**；失效的是 `prompt-audit` 里 **3 处 `_common.md §9`**（§9 已迁 `prompts/_review-common.md`）；另发现 **1 处 orphan 锚点**（`_pool.md` 的 `§5.1` 无父 §5） |
| 4 | 超长单行（>2000 字符） | **证伪** | 全仓 docs 面（含 prompts、仓库根 docs/）**最长单行 1595 B**（`docs/pending-changes.md:232`）；4 份技能 docs 最长 399 B ⇒ **拆行 0 条** |
| 5 | 审计语言与规则混排 | **部分确证** | `performance.md` §2.1/§6.1/§8 共 3 处可整体搬移的实测依据；`writing-and-format.md` §0 有 1 处；其余 4 处事故字样**嵌在规则句内**，搬移须改写散文（见 §7 待决） |

**改动量（第一轮）**：23 个文件，合计 353 825 → 355 114 B（**+1 289 B**）。所有增量来自「`§` 号 / `<技能根>` 限定 / 附录标题 / 时效说明」，无规则增删。
**三套件**：`dryrun` rc=0 ✅ ｜ `REVIEW_STATUS=NEEDS_REVISION` rc=0 ✅ ｜ `scripts-smoke` 30/30 ✅
第一轮已由父 agent 核验并提交为 **`9c6ca83`**；第二轮（本文 §0.5）在其之上进行，**未提交 git**。

---

## 0.5 第二轮：父 agent 裁决落地（基线 `9c6ca83`）

父 agent 对第一轮 6 项待决的裁决：**①③④⑤ 做、②⑥ 不做**。逐项结果：

### ① `docs/ai-usage-report.md` 旧号全部改正（活引用）

**实测计数修正**：不是「36 处」而是 **36 行 / 60 处**（`grep -c` 计行、`grep -o | wc -l` 计处）。分布：`§一` 27、`§二` 19、`§四` 6、`§三` 4、`§五` 3、`§六` 1（无 `§〇`）。

按已验证映射 `§一..§六 → §1..§6`（条内号 M 不动）全量替换，并顺手把该文件 2 处**裸 `docs/`** 限定为 `<技能根>/docs/`（L334、L1048 的 `docs/flowchart-drawing.md`）。
**自证**：`grep -cE '§[〇一二三四五六]' docs/ai-usage-report.md` → **0**；`grep -cE '§[0-9]'` → **36**（全部转成新记法）。
**新指针有效性**：对该文件 60 处新 § 引用逐条比对 `writing-and-format.md` 的真实锚点（节 + 条内序号）→ **解析成功 60 / 失效 0**。
字节：133 328 → 133 232（**−96**，中文数字 3 B → 阿拉伯 1 B 的净减，减去 2 处 `<技能根>` 增量）。
> 保留未改：`向上找 \`docs/\``（8 处）是「按模板目录向上找 docs 目录」的**通用兜底措辞**，不指向具体文档，不属歧义。

### ③ `flowchart-drawing.md §6` 标题「两道」不符 —— 判定依据

**先数正文实际条数（4 条，列标题）**：
1. **上游契约**（运行 `self_check.py`）——机械
2. **本文件纪律（机械）**（运行 `figure_lint.py`，P0 清零）——机械
3. **视觉复核（人眼级）**——人工
4. 手工抽查（**兜底**）——人工兜底，条目标签自带「兜底」二字

**判定：不是「4 条 = 2 组」，而是「3 道必做（2 机械 + 1 视觉）＋ 1 条兜底」**。两处独立外部证据支持：
- `prompts/phase-08-visualization.md:37` 标题：`### 4. 出图自检（**两道机械 + 一道视觉**，P0 未清零不写 manifest）`——其正文同样是这 4 条；
- `prompts/phase-08-visualization.md:54`：「记录 §4 的**两道机械 + 一道视觉**结论」。

故**不按条数写「四道」**（第 4 条自标兜底，称其「缺一不可」会失真），改为按**组数/道数**改写并在原位加半句说明：

```
## §6 自检（两道机械 + 一道视觉，缺一不可；另附兜底手工抽查）

> 本节 4 条 = **3 道必做**（①② 两道机械脚本、③ 一道视觉复核）＋ **1 条兜底**（④，脚本或图像工具不可用时使用）；**①② 通过 ≠ 合格**。
```
字节：6 232 → 6 474（**+242**）。
> 若父 agent 更希望纯按条数，替换串为：`## §6 自检（四道，缺一不可）`（**未采用**，理由如上）。

### ④ `_pool.md` orphan `### 5.1` —— 补父级（零重编号方案）

采用裁决首选方案「补一个 `## §5 复用与池`」，而非把 `5.1` 重编为与 `_common.md §4` 对齐——后者会**引入编号漂移**（5.1 是 `reuse_lint.py` 4 处引用的锚点），与前几轮「避免再次漂移」的目标冲突。

```
# 代码池手册（原语池 / 题专用核心）
## §5 复用与池（原语池 / 题专用核心）
> 通用复用纪律（资产清单 / 探针池 / 其它复用）见 `_common.md` §4；本节只写**原语池**细则。
### §5.1 原语池（题无关，可跨题带走）      ← 仅加 `§` 号，数字 5.1 不动
```
`scripts/reuse_lint.py` 4 处随之对齐为 `` `_pool.md` §5.1 ``（L10/L13/L153/L462）；L10 的 docstring 小节下划线同步加长到 32 字符（原 18，避免 RST 下划线短于标题）。
字节：`_pool.md` 4 741 → 4 921（**+180**）；`reuse_lint.py` 26 454 → 26 512（**+58**）。

### ⑤ 同行多文档时的裸 `§N-M` —— 判据收紧后实际是 **4 行 / 7 处**（不是 ~40）

第一轮我写的「约 40 处」是**未经判据过滤的粗估**（当时统计的是"§引用前无任何文档名"共 78 处，未加"同行 ≥2 文档名"这一条）。本轮严格按裁决口径重算，并按**可判定性**分两层：

| 判据 | 命中 | 说明 |
|---|---|---|
| **父 agent 口径**：同行 ≥2 份文档名，且该 § 引用之前未出现任何文档名 | **1 行 / 2 处** | `phase-13-finalReview.md:45` |
| **加严口径（实际治理集）**：`§N-M` 是 `writing-and-format.md` **独有记法**（已核：`_common`/`_review-common`/`performance`/`_pool`/`artifact-schemas`/`state-schema` 中 `§N-M` 出现次数均为 **0**，仅 `flowchart-drawing` 有 1 处是"§2-6 指向本文档"），故只要同行出现**非 writing-and-format 的文档名**而 `§N-M` 未被前置限定，读者即可误挂 | **4 行 / 7 处** | 见下表 |

> 收紧过程：先用 25 字符回看窗口，误报 13 行/28 处；改为**全行前置**判定后降到 1 行/2 处；再加"`§N-M` 独有记法 + 非 owner 文档名同行"这一真正会误读的条件，定为 4 行/7 处。**不做**在只有单一文档名的行上补限定（那些引用本无歧义）。

**逐行计数（已补限定，形式 `<doc> §N-M`）**：

| 文件:行 | 同行出现的非 W&F 文档 | 补限定的引用 | 处数 |
|---|---|---|---|
| `phase-02-data.md:52` | `_common.md`、`figure_lint.py` | `§2-8` | 1 |
| `phase-08-visualization.md:35` | `flowchart-drawing.md` | `§2-6` | 1 |
| `phase-12-writing.md:71` | `flowchart-drawing.md` | `§2-9`、`§2-6`、`§2-8` | 3 |
| `phase-13-finalReview.md:45` | `_common.md`、`figure_lint.py` | `§2-9`、`§2-1/5` | 2 |
| **合计** | | | **7** |

限定用**文件名短形式** `` `writing-and-format.md` ``（与 `phase-02-data.md:36` 既有先例「合规铁律（writing-and-format.md §1-15…）」一致），而非 `<技能根>/docs/…` 全路径——后者在一行内重复 3 次会显著伤害可读性；`<技能根>` 限定规则适用于**路径式**引用（任务 A），不适用于行内**文档名**限定。
字节：`phase-02` +24、`phase-08` +24、`phase-12` +72、`phase-13` +48。

### ②⑥ 不做（列待决）

见 §7 待决-1（成本纪律 5 处正文复述）与待决-6（`writing-and-format §4` 嵌句事故字样）——按裁决留待批 3。§7 待决-2（图注 token 双写）不在本轮裁决清单内，**维持待决**。

### 第二轮字节表

| 文件 | before | after | Δ |
|---|---:|---:|---:|
| `docs/ai-usage-report.md`（仓库根） | 133 328 | 133 232 | −96 |
| `skills/math-model/docs/flowchart-drawing.md` | 6 232 | 6 474 | +242 |
| `skills/math-model/prompts/_pool.md` | 4 741 | 4 921 | +180 |
| `skills/math-model/prompts/phase-02-data.md` | 6 647 | 6 671 | +24 |
| `skills/math-model/prompts/phase-08-visualization.md` | 5 458 | 5 482 | +24 |
| `skills/math-model/prompts/phase-12-writing.md` | 11 608 | 11 680 | +72 |
| `skills/math-model/prompts/phase-13-finalReview.md` | 11 722 | 11 770 | +48 |
| `skills/math-model/scripts/reuse_lint.py` | 26 454 | 26 512 | +58 |
| **合计（8 文件）** | **206 190** | **206 742** | **+552** |

> 本报告自身（`docs/docs-restructure-report.md`）也在本轮被修改（新增 §0.5），但**不计入上表**——文件无法记录自己写完之后的大小。上表 8 行已用脚本逐行比对 `git diff`，字节与 Δ 全部一致。

### 第二轮验证

- 三套件：`dryrun` **rc=0** ｜ `REVIEW_STATUS=NEEDS_REVISION` **rc=0** ｜ `scripts-smoke` **30/30** ✅
- 临界字面量：**34 项**阈值/预算/命令在**8 个改动文件中出现次数完全不变** ✅
- `§[〇一二三四五六]` 残留：**仅** `docs/docs-restructure-report.md`（本报告自身引述旧形）与 3 份**历史留痕**（`pending-changes.md`、`prompt-audit-2026-09-11.md`、`template-restructure-plan.md`）✅
- `ai-usage-report.md` 60 处新指针解析 **60/0**（成功/失效）✅

---

## 1. 现状清单（改动前基线）

`ls skills/math-model/docs/`：`cases/`（子目录）、`flowchart-drawing.md`、`performance.md`、`writing-and-format.md`

| 文件 | 字节 | 行 | 顶层标题 | >2000 字符单行 | 被引用（活 / 历史） |
|---|---|---|---|---|---|
| `docs/writing-and-format.md` | 19 807 | 154 | `§〇 文档即共享` `§一 论文写作规范` `§二 图表生成规范` `§三 CUMCM 格式` `§四 论文模板要点` `§五 创新链条` `§六 内部 Common Mistakes`（+ 未编号 `### 数据分析统计工具箱` / `### 致命级` / `### 严重级`） | **无**（最长 399 B） | 25 / 19 |
| `docs/performance.md` | 10 658 | 112 | `0. 环境与 venv` `1. 选型规则` `2. 通用纪律`（+`2.1`）`3. 并行` `4. numba` `5. GPU` `6. 实验预算`（+`6.1`）`7. 记录` `8. 反面教训（实测）` | **无**（最长 274 B） | 21 / 12 |
| `docs/flowchart-drawing.md` | 6 199 | 85 | `0. 依赖与回退` … `8. 产物与登记`（§0–§8 连续） | **无**（最长 231 B） | 9 / 7 |
| `docs/cases/2025A-primitives.md` | 7 112 | 119 | `1. 判据对照` `2. 可复用的对拍手法` `3. 归档实现` `4. 若再遇同类题的用法` | **无**（最长 251 B） | 0 / 3 |

注：`cases/2025A-primitives.md` 的 `# ─── 数值 ───`（L61）与 `# 登记：…`（L118）位于 ```python 围栏内，**不是真标题**，文件本身层级已整齐。

---

## 2. 迁移映射表（旧 → 新）

### 2.1 统一编号约定（本次确立）

- `## §0`＝**总则 / 前置条件**（有则用，`performance.md`、`flowchart-drawing.md`、`writing-and-format.md` 三份一致）
- `## §N`＝正文规则（N 从 1 起连续）；`### §N.M`＝子节
- 条内序号沿用 `§N-M`（M 不动）
- `## 附录：依据与案例`＝历史事故与实测依据（不编号，置于文末）

**关键决策**：`§〇 → §0`（**同值改写 / bijection**），不采用 `§〇 → §1` 的 +1 位移。理由：① 三份文档统一为「§0 总则 + §N 正文」；② `performance.md` 的 `§2.1`/`§6.1` 被 `test/dryrun-shell.mjs` 字面断言锁死（`includes("2.1 长任务后台化")`、`includes("6.1 嵌套核验的成本纪律")`），位移即红；③ 同值改写使 `§一-13 → §1-13` 全部等值，**零编号漂移**。

### 2.2 `writing-and-format.md`

| 旧 | 新 | 数字 |
|---|---|---|
| `## §〇 文档即共享（数据流总则）` | `## §0 文档即共享（数据流总则）` | 同值 |
| `## §一 论文写作规范` | `## §1 论文写作规范` | 同值 |
| `### 数据分析统计工具箱（数据题常用）`（未编号） | `### §1.1 数据分析统计工具箱（数据题常用）` | 新增子号 |
| `## §二 图表生成规范` | `## §2 图表生成规范` | 同值 |
| `## §三 CUMCM 格式` | `## §3 CUMCM 格式` | 同值 |
| `## §四 论文模板要点（2026-08 实战经验固化）` | `## §4 论文模板要点（2026-08 实战经验固化）` | 同值（括注照抄） |
| `## §五 创新链条` | `## §5 创新链条` | 同值 |
| `## §六 内部 Common Mistakes（…）` | `## §6 内部 Common Mistakes（…）` | 同值 |
| `### 致命级` | `### §6.1 致命级` | 新增子号 |
| `### 严重级` | `### §6.2 严重级` | 新增子号 |

条内序号同步：`§一-13 → §1-13`、`§二-6 → §2-6`、`§二-9 → §2-9`、`§四-5 → §4-5` …（M 不动）。

### 2.3 `performance.md`（**数字一个不动，只加 `§` 号**）

`## 0.`→`## §0`、`## 1.`→`## §1`、`## 2.`→`## §2`、`### 2.1`→`### §2.1`、`## 3.`→`## §3`、`## 4.`→`## §4`、`## 5.`→`## §5`、`## 6.`→`## §6`、`### 6.1`→`### §6.1`、`## 7.`→`## §7`、`## 8. 反面教训（实测）`→ 降为 `### 8. 反面教训（实测）`，整体归入 `## 附录：依据与案例`（**标题里的数字与句子照抄**）。

### 2.4 `flowchart-drawing.md` / `cases/2025A-primitives.md`（同样只加 `§` 号）

`## 0.`→`## §0` … `## 8.`→`## §8`；`## 1.`→`## §1` … `## 4.`→`## §4`。

---

## 3. 任务 A：指针限定化（裸写 `docs/` 归零）

`grep -rn 'docs/' skills/math-model/prompts skills/math-model/workflows` = **35 行**，逐行判定后：

| 限定形态 | 行数 |
|---|---|
| `` `<技能根>/docs/…` `` | 25 |
| `` 仓库 `docs/…` `` | 7 |
| `` `${SD}/docs/…` ``（JS 模板串运行时插值，SD＝技能根） | 2 |
| **裸写** | **0** ✅ |

**本批实际改写的 17 行**（其余 18 行原已合格）：
`phase-08:11/35`、`phase-04:60`、`phase-06:11/43/44`、`artifact-schemas:41`、`phase-07:12`、`_common:60`、`phase-09:11/58`、`phase-05:9/62`、`phase-12:71`、`workflows/math-model.js:10/33/99`。

一致性地外延到同一歧义类的其它文件（同属活引用）：`SKILL.md` 7 行、`SKILL.claude.md` 7 行、`scripts/figure_lint.py` 2 行、`scripts/probe_cache.py` 3 行、`scripts/primitives.py` 1 行、技能根 `docs/writing-and-format.md` 2 行、`docs/flowchart-drawing.md` 1 行。
`${SD}/docs/…`（`math-model.js:101/116`）**刻意保留**：它注入的是**运行时的真实绝对路径**，改成字面 `<技能根>` 会让注入文本失去实际路径。

---

## 4. 单源化决策（哪份是权威 / 哪些改为指针）

| 规则 | 权威（正文只此一处） | 其它处 | 本批动作 |
|---|---|---|---|
| 性能/成本纪律全文（先估后跑、缩窗→减档→降精度、`costEstimate_s`） | `docs/performance.md §2.1 / §6.1` | `_common.md §2.3/§2.6`、`phase-06` L46-49、`phase-09`、`_review-common.md §9.4`、壳 `COSTLINE` | **未改**（见待决-1） |
| 图注样式 token（12px / `#6b7280` / 图下居中） | `docs/flowchart-drawing.md §4` | `writing-and-format.md §2-6` 括注、`figure_lint.py` docstring | **未改**（见待决-2） |
| 示意图 HTML→PNG 完整配方 | `docs/flowchart-drawing.md` | `writing-and-format.md §2-6/§2-7`、`phase-08`、`phase-12`、`SKILL*.md` | ✅ 已是纯指针（仅补 `<技能根>` 限定） |
| 图文件路径口径 | `docs/writing-and-format.md §2-9` | `phase-08`、`phase-12`、`SKILL*.md` | ✅ 已是纯指针 |
| 论文写作/格式/模板规范 | `docs/writing-and-format.md §1–§6` | `phase-*.md` 的「规范引用」行 | ✅ 已是「引用规范，不复制内容」 |

**关键量化证据**：技能 docs 与 `prompts/*.md` 之间，**≥40 字符的行交集为 0**。即批 1 记录的「跨文件逐字重复仅剩 1 处 / 357 B」在 docs 面上是 **0**——本批**没有做任何"去重"**，因为无逐字重复可去。

---

## 5. 审计语言分区（病灶 5）

已集中到文末 `## 附录：依据与案例`（内容**原文照抄**，只挪位置）：

- `performance.md`：§2.1 的「问题（2026国赛 q2 robustness 实测…）」整段 → 附录「依据：长任务并行的实测（原 §2.1）」；§6.1 的「（反面实测：601 s 窗空间阶梯…）」→ 附录「依据：嵌套核验的反面实测（原 §6.1）」；原 §8「反面教训（实测）」3 条 → 附录 `### 8. 反面教训（实测）`。原位各留 **≤1 行指针**。
- `writing-and-format.md`：§0 的「**为什么 Stage 1 也落盘**」整段 → 附录「依据：Stage 1 也落盘的原因与已移除机制（原 §0）」；原位留 1 行指针（可执行结论仍留在 §0 表格行的「唯一写入方，无兜底…缺失即 workflow error」中，**规则未丢**）。

---

## 6. 指针修复计数

| 类别 | 条数 | 说明 |
|---|---|---|
| `prompt-audit` 的 `_common.md §9` **失效定位指针** → `prompts/_review-common.md §9` | **3** | L420「现集中在 `_common.md` §9.3 A5」；L439 小节标题「原文留存于 `_common.md` §9」；L441「已抽到 `_common.md` §9 评审通用规则」 |
| 新增「时效」说明（不改历史叙述） | 1 | §16.3 下注明 §9 已随注入面拆分迁出；L172/173/302/468/475 的「`_common` 新增 §9」属**审计留痕，保留原样** |
| `docs/` 内部编号漂移 | **0** | `writing-and-format.md` 14 处内部互引（`§2-6/§1-13/§1-15/§1-3/§1-14` 等）+ `flowchart-drawing.md §2-6` 全部指向真实存在的节/条 ✅ |
| 活引用 §编号替换总量 | **88 处** | `prompts/**` 71、`SKILL.md`+`SKILL.claude.md` 2、`scripts/figure_lint.py` 1、`writing-and-format.md` 13、`flowchart-drawing.md` 1 |
| 新形态生效证明 | — | `§1-13`、`§2-6`、`§4-5` 等新形态已就位；`skills/math-model` 内 `§[〇一二三四五六]` **残留 0 处** |

**指针自检结论**：`docs/<file>.md §…` 全量枚举后用**锚点解析器**逐条比对目标文件的真实标题与条内序号——**解析成功 89+ 处，失效 0 处**。
（枚举期间一度报出 25 条"失效"，逐条人工复核后确认**全部是解析器归属错误**：这些行的 `§N-M` 属 `writing-and-format.md`，而同行还提到 `_common.md`/`flowchart-drawing.md`，被误判为目标。已按"最近前置具名目标"重解析并人工确认。`phase-08:54` 的 `§4` 是**该文件自身的 `### 4. 出图自检`**，亦有效。）

---

## 7. 待决清单（裁决后状态）

| # | 事项 | 证据 | 状态 |
|---|---|---|---|
| **待决-1** | 成本纪律在 5 处有正文复述（`_common.md §2.6`、`phase-06` L46-49、`phase-09`、`_review-common.md §9.4`、壳 `COSTLINE`） | 批 1 报告 §残余-1；`dryrun` 对这些字面量有断言（`先估后跑`/`costEstimate_s`/`checkpoint_put`/`8×`/`成本纪律（所有探针`） | **不做（父裁决）** — 删正文须放松断言并迁移阶段门槛数字，与「不动数字」冲突，留批 3 与契约收敛一起做 |
| **待决-2** | 图注 token（`12px` / `#6b7280` / 图下居中）在 `writing-and-format.md §2-6` 与 `flowchart-drawing.md §4` **双写** | 二者都给出 token；`writing-and-format` 自己已称后者为「完整配方」 | **维持待决**（不在本轮裁决清单内）。若单源化：`§2-6` 的「（HTML→PNG，图注放图下方小字浅色 12px #6b7280 居中，完整配方 `<技能根>/docs/flowchart-drawing.md`）」→「（HTML→PNG；图注样式与完整配方见 `<技能根>/docs/flowchart-drawing.md` §4）」。**该改动会删掉 2 个设计数字**，故不自改 |
| **待决-3** | ~~`flowchart-drawing.md §6` 标题「两道」vs 正文 4 条~~ | 见 §0.5③ | ✅ **已改**（`两道机械 + 一道视觉，缺一不可；另附兜底手工抽查` + 原位半句说明） |
| **待决-4** | ~~`_pool.md` 的 `### 5.1` 无父 §5（orphan）~~ | 见 §0.5④ | ✅ **已改**（补 `## §5 复用与池`；`reuse_lint` 4 处对齐为 `` `_pool.md` §5.1 ``） |
| **待决-5** | ~~仓库根 `docs/ai-usage-report.md` 的旧号指向~~ | 见 §0.5① | ✅ **已改**（36 行 / 60 处全量替换；自证归零；60 处新指针 0 失效） |
| **待决-6** | `writing-and-format.md §4` 标题括注「（2026-08 实战经验固化）」、L106「**模板要点（踩坑教训固化）**」、L107/L109 的「双摘要事故 / 参考文献双标题事故」 | 事故字样**嵌在规则句内**，搬移须改写散文 | **不做（父裁决）** — 纯措辞，留批 3 |
| **待决-7（新）** | 4 份技能 docs 的 `# H1` 标题与 `docs/` 目录名不一一对应（如 `writing-and-format.md` 的 H1 是「math-model 内部执行规范（写作 / 图表 / 格式 / 模板 / 创新）」） | 本次未发现因此产生的失效引用 | 仅记录，不建议改（H1 承担主题说明功能） |

---

## 8. 逐文件字节表（before → after）

| 文件 | before | after | Δ |
|---|---:|---:|---:|
| `docs/prompt-audit-2026-09-11.md`（仓库根） | 50 088 | 50 433 | +345 |
| `skills/math-model/docs/writing-and-format.md` | 19 807 | 20 034 | +227 |
| `skills/math-model/docs/performance.md` | 10 658 | 11 000 | +342 |
| `skills/math-model/docs/flowchart-drawing.md` | 6 199 | 6 232 | +33 |
| `skills/math-model/docs/cases/2025A-primitives.md` | 7 112 | 7 116 | +4 |
| `skills/math-model/prompts/_common.md` | 14 840 | 14 852 | +12 |
| `skills/math-model/prompts/artifact-schemas.md` | 3 229 | 3 241 | +12 |
| `skills/math-model/prompts/phase-01-literature.md` | 8 128 | 8 122 | −6 |
| `skills/math-model/prompts/phase-02-data.md` | 6 663 | 6 647 | −16 |
| `skills/math-model/prompts/phase-04-formulation.md` | 11 449 | 11 453 | +4 |
| `skills/math-model/prompts/phase-05-implementation.md` | 6 740 | 6 760 | +20 |
| `skills/math-model/prompts/phase-06-computation.md` | 4 510 | 4 457 | −53 |
| `skills/math-model/prompts/phase-07-sanity.md` | 5 663 | 5 675 | +12 |
| `skills/math-model/prompts/phase-08-visualization.md` | 5 458 | 5 458 | 0 |
| `skills/math-model/prompts/phase-09-robustness.md` | 3 973 | 3 995 | +22 |
| `skills/math-model/prompts/phase-12-writing.md` | 11 640 | 11 608 | −32 |
| `skills/math-model/prompts/phase-13-finalReview.md` | 11 756 | 11 722 | −34 |
| `skills/math-model/SKILL.md` | 15 462 | 15 592 | +130 |
| `skills/math-model/SKILL.claude.md` | 14 684 | 14 814 | +130 |
| `skills/math-model/scripts/figure_lint.py` | 59 741 | 59 763 | +22 |
| `skills/math-model/scripts/probe_cache.py` | 22 884 | 22 926 | +42 |
| `skills/math-model/scripts/primitives.py` | 23 099 | 23 111 | +12 |
| `skills/math-model/workflows/math-model.js` | 30 042 | 30 103 | +61 |
| **合计（23 文件）** | **353 825** | **355 114** | **+1 289** |

`phase-06` 的 −53 B 含**去掉一行重复标题**（原 L43/L44 是完全相同的 `### 5. 性能与耗时记录（按 docs/performance.md，可选加速）`，两行连排）——这是本批唯一发现的**真·排版缺陷**，已合并为一行。

> `prompts/_review-common.md` 与 `prompts/_pool.md`、`state-schema.md`、`step1/2/3-*.md` **未改动**（其 §9 本就是数字式，`docs/` 引用本已带 `<技能根>` 或「仓库」限定），故不计入上表 23 个文件。

---

## 9. 验证

### 9.1 三套件（改动后实测）

```
node test/dryrun-shell.mjs                                  → rc=0  ✓ 干跑通过（路由/门禁/收敛/桩注入断言全过）
REVIEW_STATUS=NEEDS_REVISION node test/dryrun-shell.mjs      → rc=0  ✓ 干跑通过
TMPDIR=/dev/shm bash test/scripts-smoke.sh                   → rc=0  结果：通过 30 ／ 失败 0
```

`performance.md` 被 `dryrun` 字面断言锁死的 `2.1 长任务后台化`、`6.1 嵌套核验的成本纪律`、`先小样后整批`、`先估后跑`、`8× 同场生产主体墙钟`、`checkpoint_put`、`缩窗 → 减档 → 降精度` **全部仍在且各出现 1 次**（唯一 `先估后跑`/`8×` 各 2 次者为文内另有引用，改动前后一致）。

### 9.2 数字零变化自证（逐文件）

- **临界字面量核对**：34 项（`≤15 分钟`/`≤8×`/`≤2 分钟`/`B=500–1000`/`231×`/`195×`/`785 s`/`4.8 min/次`/`--timeout 3600`/`601 s`/`12px`/`#6b7280`/`dpi=200`/`≤20页`/`2.5cm`/`n_theta=64`/`1e-9`/`seed=42` …）在 **23 个改动文件中出现次数完全不变** ✅
- **数字多重集核对**：全部 `\d+(\.\d+)?` token 逐一对比 HEAD vs 工作区，差异仅三类且全部可解释——① 中文数字→阿拉伯数字**转换新增**的 token（如 `§一-13→§1-13` 新增一个 `1`）；② `phase-06` 去重标题**移除 1 个 `5`**；③ 附录/时效说明**新增文本**带来的 token（`原 §2.1`、`原 §6.1`、`2026-09-12` 等）。
- 未出现任何阈值、预算、超时、库版本、实测增益数字的**值变化**。

### 9.3 形态自证

- `§[〇一二三四五六]` 在 `skills/math-model/**`（除 vendored `tools/diagram-design/`）**残留 0 处**；历史留痕仅存在于仓库根 `docs/prompt-audit-2026-09-11.md`、`docs/pending-changes.md`、`docs/template-restructure-plan.md`、`docs/ai-usage-report.md`（按规则不动）。
- 裸写 `docs/`：`prompts/**` + `workflows/**` = **0**；全技能（含 `SKILL*.md`、`scripts/*.py`、技能根 `docs/**`）= **0**（仅余 2 处 `${SD}/docs/` 运行时插值）。
- 新形态生效：`grep -c` 证实 `§1-13`（`phase-12:72`）、`§2-6`（`writing-and-format.md §6` 表内）、`§4-5`（`phase-13:81`）等均为新记法。

---

## 10. 残余风险

1. ~~**`ai-usage-report.md` 的 36 处旧号已成死指针**~~ → ✅ **第二轮已消除**（60 处全量替换，新指针 60/0 解析通过）。
2. ~~**裸 `§N-M` 在多文档同行的行内有歧义**（约 40 处）~~ → ✅ **第二轮已收紧并治理**：判据收紧后实际 **4 行 / 7 处**（见 §0.5⑤），全部补上 `` `writing-and-format.md` `` 限定。第一轮的「约 40」是未经判据过滤的粗估。
3. **`test/intermediates/**` 的 4 处旧号**（如 `flowchart-skill-test/smoke/notes.md:4` 的 `§二`）是**测试运行留下的 agent 笔记产物**，非活引用，未改；下次跑测试若重新生成会自然消失。这是**全仓仅存的活目录内旧号**。
4. **历史留痕内的旧号**（`pending-changes.md` 7 处、`prompt-audit-2026-09-11.md` 4 处、`template-restructure-plan.md` 1 处）**按裁决永久保留**——它们记录的是各自写作时点的编号事实，改写即伪史。读者若从这些文件跳到技能 docs，需自行按 §2 映射表换算。
5. **两轮均未提交 git**：第一轮已由父 agent 提交为 `9c6ca83`；**第二轮 8 个改动文件 + 本报告仍在工作区**，需父 agent 统一提交。
