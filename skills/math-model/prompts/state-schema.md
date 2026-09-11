# state.json 状态契约（schema v1）

位置：`<outputDir>/intermediates/state.json`。用于**中断恢复**（重启按 `problemId` 匹配后从 `(question, stage)` 续跑）与**审计**（终审溯源）。文件由**阶段 agent 自己**更新；壳只做路由与门禁判定，仅在三个专职节点写 state：`init`（建文件）、`degrade`（失败降级 → `gates[k]="SKIPPED"`）、`finalize`（公式化收束 → `iterations`/`gates`/`artifacts`/`current`）。

## 结构

```json
{
  "schema": "v1",
  "problemId": "<题号>",
  "current": { "question": "q1|q2|...|null", "stage": "<slug>|null" },
  "iterations": { "<question>.<stage>": <int> },
  "gates": { "<question>.<stage>": "PASS|NEEDS_REVISION|FAIL|SKIPPED|PASS_WITH_WARNING" },
  "artifacts": { "<question>.<stage>": "<相对路径>" },
  "deps": { "<question>.<stage>": "<sha-256 截断>" }
}
```

## 字段

- `schema`：契约版本，固定 `"v1"`。
- `problemId`：题号（与 `intermediates/00-problem.json` 的 `selectedProblem`/`problem.id` 一致）；恢复时以此匹配，不匹配则全新开始。
- `current`（**可选**）：进度游标 `{question, stage}`；阶段 agent 顺手更新即可，仅用于人工观察——**恢复只依赖 `gates`/`artifacts`，不依赖本字段**，不要为它额外派回合。
- `iterations`：键为 `"<question>.<stage>"`，值为该阶段**累计**执行次数（公式化 = 1 次 formulator + 评审轮数，由收束节点写；同一阶段多次尝试则累加：每次尝试 = 1 次 formulator + 该次评审轮数；只能增，不得回退为单轮值）。
- `gates`：门禁/阶段结果，值域 `PASS | NEEDS_REVISION | FAIL | SKIPPED | PASS_WITH_WARNING`。
- `artifacts`：阶段产物相对路径（`<outputDir>/intermediates/` 下）。
- `deps`（**可选**）：阶段依赖哈希（`"sha-"` + 首依赖文件 `sha256sum` 截断 12 位）；审计用，**不写不算违约**、不要为它额外派回合。

## 键约定（壳 + 各阶段 agent 必须一致）

| 键 | 谁写 | 值 |
|---|---|---|
| `q1.literature` … `q1.localComplete`（每问 10 个阶段） | 该阶段 agent | 自己的返回 status |
| `q1.formulation` | 公式化**收束节点** | `PASS`（三视角均无必须改——登记级/建议级不阻塞）\| `NEEDS_REVISION`（轮次用尽仍有必须改）\| `FAIL`（评审全部失败） |
| `q1.solve-start` / `write-start` / `final-start` | 门禁**专职检查 agent** | `PASS` \| `FAIL` |
| `crossReview` / `writing` / `finalReview`（运行级 3 阶段） | 该阶段 agent | 自己的返回 status |

## 更新职责

**阶段 agent 自己在完成产物后更新 state.json 对应字段并追加 `intermediates/ledger.md`**（追加式，一行一条）：

```
<question>.<stage>: <status> <artifact相对路径> <summary截断50字>
```

壳不单独派 state 更新代理。各路径：

- **常规阶段**（含运行级 3 阶段）：agent 更新 `iterations`/`gates`/`artifacts` 并追加 ledger 一行（`current`/`deps` 可选）。
- **公式化子流程**（ledger 键固定，便于审计区分：formulator 用 `q.formulation`、修订用 `q.formulation.revision-r<轮次>`、收束用 `q.formulation.finalize`）：
  - formulator 节点：写 `draft.md` + `baseline-registry.md`，更新 `current`/`artifacts`、`gates[q.formulation]="NEEDS_REVISION"`、追加 ledger（`iterations` 由收束节点写）；
  - 三维自查节点：只写 `self-check.md`，不更新 state；
  - 评审节点（三视角**并行**）：只写 `review-r<轮次>-<视角>.md`，**不追加 ledger、不改 state**（并行写竞态；判定由收束节点统一记入 ledger）；
  - 修订节点：覆盖写 `draft.md`，追加 ledger 一行，不更新 state；
  - **收束节点**：统一写 `gates[q.formulation]`（PASS/NEEDS_REVISION/FAIL，**原样写入调度壳注入的结论值**，本键不得出现 `PASS_WITH_WARNING`/`DRAFT`）、`iterations`、`artifacts`、`current=null`，追加 ledger 一行。
  - **失败降级节点**（壳派发，任意阶段连续 2 次失败）：只写 `gates[<question>.<stage>]="SKIPPED"` 并追加 ledger；不写 `iterations`/`artifacts`（该阶段本就没有可用产物）。**例外：`finalReview` 失败不降级**——壳直接返回 blocked（终审是最后一道质量门禁，无下游可拦）。

## 恢复规则

壳启动时读 state.json；`problemId` 匹配则恢复。跳过条件：`gates[键] ∈ {PASS, PASS_WITH_WARNING, SKIPPED}`（壳直接按 gates 判定，不再派核验代理；产物缺失由下游门禁/阶段失败收敛兜底）。`NEEDS_REVISION`/`FAIL`/`DRAFT` 一律重跑。门禁键（`*-start`）若已为 `PASS` 则跳过复查。
