# 批 1 交付报告：提示词排版重构（零语义影响批）

> 范围：`skills/math-model/prompts/**`、`skills/math-model/workflows/math-model.js`、4 个 `scripts/*.py`（仅注释/docstring 串）、`test/dryrun-shell.mjs`
> 基线：HEAD `5bac956`（工作树干净）。**未提交 git**；**未写跑批产物** `/home/tofu/文档/数学建模/2026国赛/math-model-output`（只读）。
> 回滚：`git checkout -- <下表 20 个文件>`。

## 1. 验证（全绿）

| 命令 | 结果 |
|---|---|
| `node test/dryrun-shell.mjs` | **rc=0**（断言全过；方案记 112 条） |
| `REVIEW_STATUS=NEEDS_REVISION node test/dryrun-shell.mjs` | **rc=0**（修订/轮次用尽/收束路径全过） |
| `TMPDIR=/dev/shm bash test/scripts-smoke.sh` | **30 通过 / 0 失败** |

**语法自证**：`workflows/math-model.js` 由 dryrun 的 `new AsyncFunction("agent","parallel","phase","log","args", body)` **构造步骤验证通过**（无 SyntaxError ⇒ 模板串无提前闭合，等同于历史两次事故的回归门）。另跑同构构造自证：

```
✓ AsyncFunction 构造通过：无 SyntaxError（模板串全部正确闭合）
【修订r】块区（源 14 行）：未转义反引号 22 个（= 11 个元素 × 2 定界）、字面反引号 18 个（全部转义）、${ 插值 17 个
源文件最长行 = 465 字符（原【修订r】行为 1165）
```

## 2. 改动文件与字节 before→after

| 文件 | before | after | Δ |
|---|---|---|---|
| `skills/math-model/prompts/_common.md` | 13922 | 14840 | +918 |
| `skills/math-model/prompts/_pool.md` | 4741 | 4741 | +0 |
| `skills/math-model/prompts/_review-common.md` | 6687 | 6806 | +119 |
| `skills/math-model/prompts/phase-01-literature.md` | 8124 | 8128 | +4 |
| `skills/math-model/prompts/phase-02-data.md` | 6659 | 6663 | +4 |
| `skills/math-model/prompts/phase-04-formulation.md` | 11447 | 11449 | +2 |
| `skills/math-model/prompts/phase-05-implementation.md` | 6738 | 6740 | +2 |
| `skills/math-model/prompts/phase-06-computation.md` | 4508 | 4510 | +2 |
| `skills/math-model/prompts/phase-07-sanity.md` | 5661 | 5663 | +2 |
| `skills/math-model/prompts/phase-08-visualization.md` | 5454 | 5458 | +4 |
| `skills/math-model/prompts/phase-09-robustness.md` | 3971 | 3973 | +2 |
| `skills/math-model/prompts/phase-11-crossReview.md` | 5892 | 5894 | +2 |
| `skills/math-model/prompts/phase-12-writing.md` | 10934 | 10936 | +2 |
| `skills/math-model/prompts/phase-13-finalReview.md` | 11037 | 11041 | +4 |
| `skills/math-model/scripts/artifact_lint.py` | 26505 | 26505 | +0 |
| `skills/math-model/scripts/primitives.py` | 23099 | 23099 | +0 |
| `skills/math-model/scripts/probe_cache.py` | 22884 | 22884 | +0 |
| `skills/math-model/scripts/reuse_lint.py` | 26454 | 26454 | +0 |
| `skills/math-model/workflows/math-model.js` | 29417 | 30042 | +625 |
| `test/dryrun-shell.mjs` | 30442 | 30600 | +158 |
| **合计** | **264576** | **266426** | **+1850** |

## 3. 已拍板 6 条决策的落点

| # | 决策 | 落点 |
|---|---|---|
| 1 | 原 §6 工具表 → §2 末 | **§2.7 工具清单（技能根 / 技能级工具与文档路径）**：技能根定义 + 6 行脚本表 + 「工具缺失不阻塞」原样搬入，12 处技能根指针同步指 §2.7 |
| 2 | 原 §7（环境/python 口径）→ §2；产物清单 → §5 | python 解释器与「相对路径基于 outputDir 根／q{id} 口径」→ **§2.4 环境与解释器**；产物侧 → **§5.1 产物字段契约（唯一权威→`artifact-schemas.md`）+ §5.2 产物记账（artifacts 相对路径 + ledger 行格式）** |
| 3 | 原 §8（不编造/可得级别）→ §3 | **§3.2 不编造（可得级别）**（挂在 §3 数字与真源下，规则句逐字保留） |
| 4 | 原 §5 复用纪律 → §4 | **§4 复用纪律**：§4.1 资产清单与共享区／§4.2 原语池（指针 `_pool.md`）／§4.3 探针池／§4.4 其它复用 |
| 5 | 成本纪律收敛到 §2 | **§2.6 成本纪律（嵌套核验）** 收全文（原 §5.2 末条逐字搬入）；§4.3 只留 1 行指针。phase-06/phase-09/`_review-common.md §9.4`/壳 `COSTLINE` 四处**未删正文**（见 §7 残余-1） |
| 6 | `_review-common.md` §9 保留原编号；step1/2/3 不改骨架 | §9 及其 9.1–9.4 一字未动（10 处 `_review-common.md` §9 指针原样，dryrun L222/L229 原样通过）；`step1/2/3-*.md` **0 改动** |

## 4. dryrun 断言同步

- **期望字符串（判定实参）0 条需要改**：本批保留了全部 112 条断言的判定表达式与其断言的提示词字面量（`长任务后台化`/`禁止 sleep（反引号形式）`/`单行 ≤2000 字符`/`必须整体读`/`20KB`/`登记级/建议级意见不阻塞`/`成本纪律（所有探针`/`路径与环境四律`+6 要素/`## 9. 评审通用规则`/`_review-common.md\` §9`/`本视角`/`精准手术`/`revision-log.md`/`q1.formulation.revision-r1`/`以文件为准`/`## 阶段 q1.` …）。
- 只同步 **5 条断言失败消息串**（不参与判定；未删断言、未放松判定）：L219 `_common §3→§1.2`、L241 `§2→§2.2`、L242 `§3→§2.3`、L245 `§3→§2.3`、L319 `§5.2→§2.6`；另加 1 行注释标注批 1 已重排。`git diff test/dryrun-shell.mjs` = 5 行消息 + 1 行注释（+158 B）。

## 5. 规则行清单比对（`_common.md`，含 禁止/必须/不得/≤/≥/上限/例外）

改前 **23 行** / 改后 **23 行**；逐字节相同 **21 行**；归一化（仅节号）后 **丢失 0 / 新增 0** ⇒ **内容 0 丢失**。
（另 2 行的差异仅为所在标题编号 §1→§2.1 及行内 `见 §6`→`见 §2.7`；脚本同时验证「按原行顺序回排块后逐字复原」，且 `\${` 插值 17→17、量化串 9→9。）

| 改前所在节 | 改后所在节 | 规则行（节选） |
|---|---|---|
| （文件头） | （文件头） | > 本文件与你的阶段模板（`phase-*.md` / `formulation-reviewer-*.md`）**必须同一次并列 Read 读入**；两者冲突时**以阶段模板为准**。 |
| 1. 统一节拍（阶段节点） | 2.1 执行节拍（阶段节点） | 5. 返回 {status:"PASS\|DRAFT\|NEEDS_REVISION\|FAIL\|SKIPPED\|PASS_WITH_WARNING", artifact_path, summary≤200字} |
| 2. 统一节拍（评审 / 修订节点） | 2.2 评审节拍（评审 / 修订节点） | 4. 返回 {status:"PASS"\|"NEEDS_REVISION", artifact_path, summary≤200字}；**PASS = 没有「必须改」意见**；登记级/建议级意见不阻塞（三视角共用的分 |
| 3. 工具纪律（减回合——会话耗时主因） | 1.1 读入面（并列读） | - **并列读**：一次 `Read` 把所有需要的文件一起读入（`Read a.md、b.md、c.md`），禁止逐文件往返、禁止同文件反复重读。 |
| 3. 工具纪律（减回合——会话耗时主因） | 1.2 只读需要的小节 |   - **被评审/被核验/被修订的对象**（`draft.md` 等）**必须整体读**——局部读会漏掉跨节矛盾，禁止对评审对象做局部读； |
| 3. 工具纪律（减回合——会话耗时主因） | 2.3 批量与后台化（减回合——会话耗时主因） | - **一次跑完**：一组命令一次 bash 执行并统一 `ls` 校验；禁止逐图/逐文件微循环。 |
| 3. 工具纪律（减回合——会话耗时主因） | 2.3 批量与后台化（减回合——会话耗时主因） | - **长任务后台化（禁空转）**：>60 s 的命令（求解/探针/分片/渲染）一律后台起（`run_in_background: true`，或 `nohup … > <日志> 2>&1 &`），启动后**立刻做不依赖 |
| 3. 工具纪律（减回合——会话耗时主因） | 2.3 批量与后台化（减回合——会话耗时主因） | - **单行 ≤2000 字符（写侧纪律）**：read 工具**按行硬截断**，超限时读者只看到前 2000 字符，行末的 `(line truncated to 2000 chars)` 极易被忽略 ⇒ 长表逐行、长 |
| 4. 数字单一真源（硬纪律） | 3.1 数字单一真源（硬纪律） | - 例外（不算分叉）：题面给定常量与参数、年份、代码内部可控参数（迭代数/网格分辨率/随机种子）——但**引用时仍须写明出处**（`00-problem.json` 或代码常量名）。 |
| 4. 数字单一真源（硬纪律） | 3.1 数字单一真源（硬纪律） | - 同一关键数字（≥5 位有效数字，或 ≥4 位整数）在产物中出现 ≥3 处 → 视为口径分叉风险，必须收敛到 results.json（机械检出用 `artifact_lint.py`，见 §6）。 |
| 4. 数字单一真源（硬纪律） | 3.1 数字单一真源（硬纪律） | - 绘图脚本**不得硬编码关键结果数值**：一律从 results.json 读取；样式/布局参数（figsize/dpi/fontsize/坐标范围）不受此限。 |
| 5. 复用纪律（禁止重写同口径核心） | 4. 复用纪律（禁止重写同口径核心） | ## 5. 复用纪律（禁止重写同口径核心） |
| 5. 复用纪律（禁止重写同口径核心） | 4.1 资产清单与共享区 | **可复用资产清单**：壳把 `pool/manifest.json`、`pool/problem/manifest.json`、`probes/manifest.json` 列进每个阶段的并列 Read，并给评审/修订 |
| 5.2 探针池（评审/对抗/敏感性的重计算） | 4.3 探针池（评审/对抗/敏感性的重计算） | - 固定位置 `probes/<角色>/<目的>.py`（角色：judge / adversary / application / sanity / robustness / data（02 阶段）/ impl（05 阶 |
| 5.2 探针池（评审/对抗/敏感性的重计算） | 2.5 路径与环境四律 |   - **① 绝对路径**：本 run 根 = 壳注入的 `<outputDir 绝对路径>`。**一切工具调用**的文件参数（`present` / Read / Write / Edit / Bash 参数）**一 |
| 5.2 探针池（评审/对抗/敏感性的重计算） | 2.5 路径与环境四律 |   - **② 解释器**：一律 `"$PY"=<outputDir>/.venv/bin/python`（以 `intermediates/env-report.json` 为准，缺失才退系统 python3）；**禁 |
| 5.2 探针池（评审/对抗/敏感性的重计算） | 2.5 路径与环境四律 |   - **③ 池导入**：直接跑脚本时加 `PYTHONPATH=<outputDir>:<outputDir>/pool`，或脚本首行 `import probe_cache as pc; pc.bootstrap_ |
| 5.2 探针池（评审/对抗/敏感性的重计算） | 4.3 探针池（评审/对抗/敏感性的重计算） | - **探针预算（权威处）**：单探针 ≤2 分钟、整轮验证 ≤10 分钟（评审/修订的验证探针同此限）；确需大计算 → 粗采样/解析核验代替穷举 |
| 5.2 探针池（评审/对抗/敏感性的重计算） | 4.3 探针池（评审/对抗/敏感性的重计算） | - **清单体积纪律**：`probes/manifest.json` 一行一条目、单文件 ≤48 KiB、条目 ≤200（超出自动移入 `probes/manifest.archive.json`）；查复用/查重时** |
| 5.3 其它复用 | 4.4 其它复用 | 同小问前序产物、`pool/problem/<题>/`（题专用核心）、前序小问的 `02-data/`、`05-implementation/code/` 与 `06-computation/` 里已有的同口径实现 →  |
| 6. 技能级工具与文档路径 | 2.7 工具清单（技能根 / 技能级工具与文档路径） | \| `scripts/figure_lint.py` \| 出图机械自检：流程图 HTML/SVG 规范（网格/正交/遮罩间隙/皮肤 token）、绘图脚本 AST（下划线字面量/科学计数法/标题/硬编码数字/图例缺失 |
| 6. 技能级工具与文档路径 | 2.7 工具清单（技能根 / 技能级工具与文档路径） | \| `scripts/artifact_lint.py` \| 数字单一真源检查（关键数字散落 ≥3 处即报错）＋**池登记完整性**（`pool/`、`probes/` 下的 .py 与 manifest 条目双向对 |
| 8. 不编造 | 3.2 不编造（可得级别） | 拿不到的数值、文献、数据一律**如实标注可得级别/缺口**（数值缺口→FAIL 并说明；文献→标证据级），禁止填充、近似替代或抄写示例数字。 |

## 6. 指针同步（B 项）

- 全库 `_common.md §N` 指针 **33 处**，全部解析到新节号，**旧编号残留 0 处**；`grep -rn '_common.md §' skills/math-model` 仅剩 `§4、§2.6`/`§4.2`/`§2.6`。
- 风格统一为 `` 见 `_common.md` §N ``：12 处 `（技能根见 \`_common.md §6\`）` → `` （技能根见 `_common.md` §2.6） ``；`_review-common.md` 5 处裸 `§2/§3/§5.2/§6` 补全为 `` 见 `_common.md` §N ``（其中 §9.4 的 `见 §5.2` 升级为 `见 §4.3 与 §2.6`，覆盖探针预算与成本纪律两个目标）。
- 编号映射：§6→§2.7、§5→§4、§5.1→§4.2、§5.2→§4.3（路径四律另迁 §2.5）、§4→§3、§3 读入面→§1.1/§1.2、§3 写侧→§2.3、§2→§2.2、§1→§2.1、§7→§2.4/§5.2、§8→§3.2。
- `_review-common.md §9` 引用保持文件与编号不变（10 处）。

## 7. 残余风险 / 待决

1. **决策 5 只做了单源化，未删其余 4 处正文**：phase-06 三条成本纪律、phase-09「实验预算」、`_review-common.md §9.4`、壳 `COSTLINE` 里含 dryrun 断言的 `先估后跑`/`costEstimate_s`/`checkpoint_put`/`8×` 及阶段特有预算数字（≤15 分钟、B=500–1000、timeout 300s）。删正文必然要放松断言或移动阶段门槛数字，与本批「数字/门槛零变化」冲突 ⇒ 建议批 2 连同断言口径一起改（`_common.md §2.6` 已是权威处）。
2. `_pool.md` 4741 B 未瘦身，仍保留 `### 5.1 原语池` 旧编号（属批 3 待决-1 B 案）；本批只改其 1 处指针（§5→§4）。
3. 壳其余内联块按「能不动就不动」未改：`【节点1 · formulator】`（465 字符）、`【评审r】`、`stagePrompt` 的 `## 阶段` 前缀（dryrun L333 依赖）。最长提示词源行仍 465 字符。
4. 未按方案 §5.2 建议新增 3 条守门断言（行 ≤200 字符 / 反引号清零 / 13 阶段骨架）——本批只授权同步失效断言。`【修订r】` 块区现状：14 行、最长源行 214 字符、无未转义反引号。
5. `_common.md` 13922→14840 B（+918：块名/标题/2 行指针），**规则句 0 增删**；方案预估 ≈12800 含去重，本批为守住「规则句数量不减」未去重。
6. `docs/pending-changes.md`、`docs/prompt-audit-2026-09-11.md` 仍含旧节号（历史记录，按范围未动）；`scripts/__pycache__/*.pyc` 内含旧串（gitignore，下次运行自动重编译）。
