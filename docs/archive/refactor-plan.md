# math-model 改造方案（V3 定稿）

> 状态：已讨论定稿，待实施
> 日期：2026-09-08
> 配套：SKILL.md（DSH 版）、SKILL.claude.md（Claude 版）、workflows/math-model.js、prompts/、docs/writing-and-format.md

---

## 1. 背景与问题

### 1.1 当前痛点

| 问题 | 表现 | 根因 |
|---|---|---|
| **workflow 调用截断** | `Workflow 调用因脚本过大被截断（script 参数丢失）` | `math-model.js` 已 244KB/3794 行；DSH `workflow` 工具只接受内联 `script` 字符串，主 agent 无法把 18 万字符重新输出一次 |
| **主 agent 可能忘记落盘** | 依赖主 agent 自觉性 | Stage 1 编排结果靠约定传递，缺机器强制 |
| **阶段过粗、审计线不完整** | 假设/公式/实现/计算/门禁/可视化全部揉在一起 | 阶段粒度是 AutoMM 的 1/3 |

### 1.2 DSH 版与 Claude 版为何不同

- **Claude Code** 的 `Workflow` 工具接受 `scriptPath`（文件路径引用），主 agent 只需输出一行路径 → 脚本多大都不截断。
- **DSH** 的 `workflow` 工具 schema 只有 `script` 字符串（已核实 `dsh-tool-workflow/lib/index.js`），无 `scriptPath`、无文件加载机制 → 脚本必须整体内联 → 超过模型输出上限即截断。
- 结论：**把 244KB 编排塞进 DSH 的 `script` 参数是不匹配的用法**。DSH 的 workflow 假定脚本是模型现场写的小编排（几 KB），承载不了"巨型编排程序"。

### 1.3 AutoMM 对照结论

AutoMM（`/home/tofu/repos/AutoMM`）是 Python 状态机 + daemon 形态的同类项目。对照结论：

- **不整体搬它的形态**：我们是 SKILL（GUI 里一句话启动），不是独立 harness；且它的 DSH 往返从未真跑通。
- **搬它的纪律**：状态契约、门禁、逐问串行、全拆阶段、版本化、失败收敛。
- **不搬它的设施**：daemon/锁/邮箱/事务日志、SSH/Kaggle 远端、全量不可覆盖版本、异步 task worker。

---

## 2. 目标架构（一句话）

> **逐问串行 + 全拆 + 薄壳**：小问循环在外、阶段循环在内；每个阶段是独立子代理，按统一节拍工作；workflow 脚本从 244KB 缩成几百行通用调度壳，全部业务逻辑（prompt、依赖图、状态契约）落到磁盘。

一次重构同时解决三件事：

1. **截断**：脚本几 KB，prompt 模板全在磁盘，子代理自己 Read。
2. **可恢复**：`state.json` 记录 (question, stage) 位置，中断后续跑。
3. **防忘性**：阶段推进由"读状态 → 查门禁"驱动，不依赖模型记得做某事。

---

## 3. 完整工作流（定案：13 阶段）

### Stage 1（主 agent，保持现状）

审题 + 选题 → 落盘 `intermediates/00-problem.json`。

### Stage 2（workflow 薄壳）

**小问循环在外**：对每个小问 Q1→Q2→Q3… 依次跑完以下 10 个阶段，全部小问完成后跑运行级 3 阶段。

```
对每个小问（Q1→Q2→Q3…）依次跑:
  1. 文献调研          [AutoMM]   逐问，首问全量、后续复用文献池只补检索词
  2. 数据探索与需求     [我们]     EDA + 数据需求评估 + 外部数据收集（合规）
  3. 假设定义          [AutoMM]   独立阶段，版本不可覆盖，max 5；连续 3 次拒绝→刷新文献
  4. 公式化/建模方案    [融合]     Gap 驱动创新 + 三维自查 + 评审团瘦身⇄修订 + baseline 预注册
  5. 实现              [AutoMM]   独立阶段，产出可运行代码
  6. 计算              [融合]     AutoMM 计算 + baseline 同场对比；结果落盘
  7. sanity 数值门禁    [AutoMM]   NaN/Inf/约束违反→失败，脏结果不前进
  8. 可视化            [融合]     AutoMM ≥N 图 + 我们的自绘示意图/反向校验
  9. robustness/ablation [AutoMM] 显式可选，跳过必须写理由
  10. 小问完成门禁      [AutoMM]   locally_completed，产物清单核验
全部小问完成后:
  11. 跨问复核         [AutoMM]   独立阶段（写作之前，保证写作基于一致的事实）
  12. 写作             [我们]     事实源表 + 叙事大纲 + 顺序撰写 + 交叉审查
  13. 终审             [我们]     摘要数字溯源 + 一致性 + 评委自评 + LaTeX 编译
```

**归属**：1/3/5/7/9/10/11 来自 AutoMM；2/12/13 是我们的；4/6/8 是融合。我们独有的竞争力（选题、评审团、baseline、外部数据合规、写作、终审）一个不丢。

---

## 4. 信息流设计（核心）

### 4.1 原则

> **所有传递都走磁盘产物，节点之间没有"对话"。** 连同一阶段内的多个节点也是文件接力。壳只做路由，不搬运内容。

原因：DSH workflow 每次 `agent()` 都是全新上下文、不共享聊天记录，**文件是唯一可靠的交流通道**。副作用是好的：每样东西都必须显式落盘、可审查。

### 4.2 三类通道

| 通道 | 是什么 | 管什么 |
|---|---|---|
| **产物文件**（持久） | `intermediates/` 下各阶段写的 md/json/代码/图 | 信息的全部内容——下游读文件拿内容 |
| **返回摘要**（短暂） | 每个 agent 返回 `{status, artifact_path, summary≤200字}` | 给壳做门禁判断 + 追加 ledger；跨问复核/终审靠摘要做廉价总览 |
| **状态+依赖路由**（机器） | `state.json` + `stage-manifest.json` 依赖图 | 决定下一步读哪个文件、门禁过没过 |

另有**规范层**（只读不变）：`prompts/phase-*.md` 模板 + `docs/writing-and-format.md`，每个 agent 开工先读自己的模板。

### 4.3 阶段间：显式依赖图（最小上下文）

`stage-manifest.json` 为每个阶段声明依赖清单（借 AutoMM 依赖图概念）：

```json
{
  "literature":     { "deps": ["00-problem"] },
  "data":           { "deps": ["00-problem", "q{id}/01-literature"] },
  "assumption":     { "deps": ["00-problem", "q{id}/02-data", "q{id}/01-literature"] },
  "formulation":    { "deps": ["00-problem", "q{id}/02-data", "q{id}/03-assumptions"] },
  "implementation": { "deps": ["q{id}/04-formulation", "q{id}/02-data"] },
  "computation":    { "deps": ["q{id}/05-implementation", "q{id}/04-formulation"] },
  "sanity":         { "deps": ["q{id}/06-computation", "q{id}/04-formulation"] },
  "visualization":  { "deps": ["q{id}/06-computation", "q{id}/07-sanity"] },
  "robustness":     { "deps": ["q{id}/06-computation", "q{id}/04-formulation", "q{id}/07-sanity"] },
  "localComplete":  { "deps": ["q{id}/01..09 全部"] },
  "crossReview":    { "deps": ["所有小问的 10-completed"] },
  "writing":        { "deps": ["所有产物"] },
  "finalReview":    { "deps": ["writing", "所有产物"] }
}
```

每个阶段 agent **只读自己的依赖**，不重读前面的东西。

### 4.4 两个跨阶段共享资产

- **全局符号表** `symbols.json`：公式化阶段累积写入（变量名/符号定义），实现、计算、可视化、写作都读它——从根上解决"公式与代码符号不一致"和写作符号统一（借 AutoMM 全局符号表）。
- **共享池** `pool/`：文献池（逐问累积）、外部数据（下载一次各问复用）、引用池。

### 4.5 阶段内节点：文件接力

以最复杂的公式化阶段为例：

```
节点1 formulator ──写──> q1/04-formulation/draft.md + baseline-registry.md
   │ {status: DRAFT, artifact_path: ...}
节点2 三维自查  ──读 draft──写──> self-check.md
节点3 评审团(2~3人, parallel() 并行) ──各自读 draft+self-check──写──> review-1.md, review-2.md
节点4 修订      ──读 draft + 全部 review-*.md──写──> v2.md
   ↓ 有"必须改"意见 → 回到节点3（评审读 v2 + 上一轮意见）──> review-v2.md
   ↓ 意见全是"建议级" → 自适应终止
```

要点：评审意见是写成 `review-*.md` 给修订者读，不是"说"给他听；壳只根据返回的状态字段决定"再修一轮还是收束"；迭代计数与终止判断在壳内存 + 记入 `state.json`。

### 4.6 小问之间

逐问串行下 Q2 开工时 Q1 已完全定稿：

- Q2 每个阶段读**共享池** + **Q1 的 question-summary.md**（`10-completed/q1/`）。
- Q2 公式化可直接引用 Q1 结果文件（后问依赖前问输出，天然成立）。

**红利**：逐问串行天然消灭大部分 stale 问题——前问定稿后问才开工。需要 hash 追踪的只剩运行级（跨问复核→写作→终审之间）。

### 4.7 目录布局（信息流实物形态）

```
intermediates/
├── state.json            # 位置{question,stage} + 门禁 + 迭代数 + deps哈希
├── ledger.md             # 追加式：每节点一行 {Q1·公式化: 评审1轮, 2条必须改, v2 PASS}
├── symbols.json          # 全局符号表
├── pool/                 # 文献池 / 外部数据 / 引用池
├── 00-problem.json       # Stage 1 落盘
├── q1/01-literature/ 02-data/ 03-assumptions/ 04-formulation/
│    05-implementation/ 06-computation/ 07-sanity/
│    08-visualization/ 09-robustness/ 10-completed/
├── q2/ ... q3/ ...       # 每问独立目录，串行天然隔离
└── 11-cross-review/ 12-writing/ 13-final/
```

### 4.8 位置跟踪（不额外花钱）

- **运行中**：壳在内存跟踪 (question, stage) 位置，零成本。
- **`state.json` 落盘**：由阶段 agent 顺手做（模板写死"完成后更新 state.json 对应字段 + 追加 ledger"），不单独派 agent。
- `state.json` 只在两件事上有用：**中断恢复**（重启时按 `problemId` 匹配，找到就从 (q2, stage4) 续跑）和**审计**（终审溯源）。

---

## 5. 状态契约与门禁

### 5.1 state.json schema（示意）

```json
{
  "schema": "v1",
  "problemId": "2025-A",
  "current": { "question": "q2", "stage": "formulation" },
  "iterations": { "q1.formulation": 1, "q2.literature": 1 },
  "gates": {
    "q1.sanity": "PASS",
    "q2.formulation": "NEEDS_REVISION"
  },
  "artifacts": {
    "q2.literature": "intermediates/q2/01-literature/literature.md"
  },
  "deps": {
    "q2.formulation": "sha-<hash-of-q2-assumption>"
  }
}
```

### 5.2 统一返回契约（③）

每个子代理必须：

1. 写产物文件（读不到文件 = 自然失败）；
2. 返回 `{status, artifact_path, summary}`；
3. 状态值域：`PASS | DRAFT | NEEDS_REVISION | FAIL | SKIPPED`（含理由）。

壳用 workflow 工具自带的 `agent(prompt, {schema})` 校验，不另造 JSON 校验器。

### 5.3 门禁检查（②）——只在关键边界跑

不为每个阶段派门禁检查员（那是几十次模型调用），只在三个边界：

- **求解前**（实现/计算开工前）：公式化产物存在 + 评审团 PASS；
- **写作前**：所有小问 locally_completed + 跨问复核 PASS；
- **终审前**：写作产物完整。

每次门禁 = 1 次专职检查子代理（验证文件存在 + 关键字段），结果记入 `state.json.gates`。

### 5.4 数值硬门禁（④）

sanity 阶段（阶段 7）规则：NaN/Inf、硬约束违反、单位/维度错误、公式与实现不一致、原始数据被修改、追踪缺失 → **必须失败**，不允许带病前进。非关键技术债（mip_gap 缺失、达到时限等）→ `PASS_WITH_WARNING`，保留求解器状态、约束残差、随机种子。

### 5.5 失败收敛判据（⑤）

- 同一根因连续 2 次 → 换策略/降级处理，不空转到 max 轮数；
- 版本类失败：`NEEDS_REVISION` 当前版本内修订；`VERSION_REJECTED` 关当前版本开下一版；
- 假设连续 3 次被拒 → 刷新文献池；假设版本达 max 5 仍失败 → 该小问 unresolved，停止整题推进。

---

## 6. 评审团瘦身与 baseline 预注册

### 6.1 评审团：保留但瘦身

**为什么保留**：评审团是全线唯一的"概念 + 数学质量"检查点——sanity 是数值的、跨问复核是一致性的、交叉审查是文风的，只有评审团检查"方案站不站得住、创新点真不真、假设合不合理"。方案错了，后面实现/计算/写作全白做。

**怎么瘦身**：

| 维度 | 旧 | 新 |
|---|---|---|
| 人数 | 4 人 | 2~3 视角（评委视角 + 对抗视角，可加"应用落地"视角） |
| 轮数 | max 6 轮 | max 3 轮 |
| 终止 | 固定轮数 | **自适应**：意见全是"建议级"即收束，不等满轮数 |
| 前置 | 无 | 保留三维自查（便宜，第一道线） |

成本从约 32~48 次调用/题降到约 4~9 次/题，价值不变（价值在第一轮意见，不在轮数）。

### 6.2 baseline：保留但制度化（预注册）

**为什么保留**：

1. **论文价值**：获奖论文的"模型对比/评价"章节是标配，baseline 是 Gap 驱动创新的证据链闭环——创新点声称的 Gap 要靠 baseline 证明是真的；
2. **sanity 锚点**：花大功夫的模型打不过朴素方法 = 最强红旗信号（过度复杂化、创新是假的）。

**怎么制度化**（借 AutoMM"预注册比较标准"）：

- **公式化阶段**：formulator 必须预先写明"本题 baseline 是什么、用什么指标比"（写入 `baseline-registry.md`）；
- **计算阶段**：baseline 与主模型**同场计算**，不单独开实现流程（baseline 用最朴素的公开方法）；
- **无自然 baseline**：formulator 写理由跳过（与 robustness/ablation 同纪律）。

---

## 7. 文件级改动清单

| 文件 | 改动 |
|---|---|
| `workflows/math-model.js` | **244KB → 几百行通用调度壳**（嵌套循环驱动：读状态 → 取模板 → 派 agent → 校验 → 写状态），无业务内容 |
| `prompts/phase-01-literature.md` … `phase-13-final.md` | **新增**：13 个阶段 prompt 模板，从现 3794 行里抽取（体积大头，机械搬运） |
| `prompts/stage-manifest.json` | **新增**：阶段清单 + 顺序 + 归属 + 依赖图 + 门禁边界声明 |
| `prompts/response-schema.json` | **新增**：统一返回契约 schema |
| `intermediates/state.json` | **新增**：状态契约（运行时由阶段 agent 更新） |
| `intermediates/ledger.md` | **新增**：追加式决策日志 |
| `skills/math-model/SKILL.md` | 阶段二改为"薄壳 + 逐问串行"说明；输出目录树更新 |
| `skills/math-model/SKILL.claude.md` | 同上（Claude 版保留 `scriptPath` 机制，指向同一薄壳） |
| `workflows/meta.json` | phases 换成 13 阶段清单 |
| `README.md` | 版本号 + 架构说明更新 |
| `docs/writing-and-format.md` | 补充"统一节拍"与产物契约（若需） |

### 7.1 薄壳伪码

```js
// 加载状态（首次 or 恢复）
const state = stateExists() ? await loadState() : await initState();
for (const q of manifest.questions) {
  for (const s of manifest.perQuestionStages) {
    const gate = manifest.gates[s];                    // 关键边界门禁
    if (gate && !(await checkGate(gate, state))) return { blocked: gate };
    const result = await agent(                          // 1 次调用/阶段
      `读 ${manifest.prompts[s]} 与 state.json；按模板执行；写产物；更新 state+ledger；返回摘要`,
      { schema: responseSchema }
    );
    if (!result) { /* 失败收敛判据：重试/换策略/降级 */ }
  }
}
await runStage('crossReview'); await runStage('writing'); await runStage('finalReview');
```

---

## 8. 实施顺序

1. **抽取 13 个 phase prompt** 到 `prompts/`（最重、机械；从现 3794 行中按阶段切分，保证不丢逻辑，含 AI 味治理、图表自绘、外部数据合规等既有规则）；
2. **写薄壳** + `stage-manifest.json` + `response-schema.json` + state/ledger 契约；
3. **更新** SKILL.md / SKILL.claude.md / meta.json / README / 输出目录说明；
4. **验证**：`node --check math-model.js` + `python3 -m json.tool` 校验 manifest/schema + 用 2025 国赛题真跑一次（先跑单小问冒烟，再全流程）。

### 8.1 验收标准

- 脚本体积 < 10KB；
- `node --check` 通过；
- 真跑：中断后重启用 state.json 恢复，能从 (q, stage) 续跑；
- 三处门禁边界各触发一次并通过；
- 终审摘要溯源能从 ledger + 产物追溯每个数字。

---

## 9. 风险与成本

| 风险 | 说明 | 缓解 |
|---|---|---|
| 模型调用量上升 | 4 问 × 10 阶段 + 3 运行级 ≈ 43 次阶段运行 + 评审团/修订/门禁 | 逐问串行 + 全拆的必然代价，72h 内可接受；评审团已瘦身；文献复用池 |
| prompt 抽取丢逻辑 | 从 244KB 切分可能遗漏既有规则 | 抽取后逐阶段对照原脚本核对；写对照清单 |
| 门禁误判 | 专职检查子代理判断错误 | 门禁只查"文件存在 + 关键字段"，不查内容质量；结果进 ledger 可回溯 |
| 中断恢复未验证 | state.json 恢复逻辑 | 验收标准第 3 条强制验证 |
| 阶段 agent 质量波动 | 每次全新上下文 | 统一节拍模板 + 依赖最小化 + 门禁兜底 |

---

## 10. 不搬清单（明确排除）

- daemon / 锁 / 邮箱 / 事务日志（无并发唤醒，单会话不需要）
- SSH / Kaggle 远端计算（有需要再说）
- 全量不可覆盖版本（git + 文件名版本号足够）
- 逐问异步 task + supervised worker（绑 daemon 设施）
- 逐问完成邮件通知
