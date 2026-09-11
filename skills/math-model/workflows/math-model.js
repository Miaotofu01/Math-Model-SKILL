// ═══ math-model 薄壳 V3：无 fs，磁盘全经 agent() 子代理 ═══
// 契约(manifest/schema/state-schema.md)启动经子代理读取；业务全在 prompts/phase-*.md；壳只做路由/门禁/收敛

const A = typeof args === "object" && args ? args : {}
const outDir = (A.outputDir || "math-model-output").replace(/^\.\/|\/+$/g, "")
const IM = outDir + "/intermediates"
const SD = A.templateDir ? A.templateDir.replace(/\/templates\/?$/, "") : "skills/math-model"   // 技能根：规范 docs/ 与工具 scripts/ 所在处
const PD = SD + "/prompts"
const STRICT = A.innovationStrictness || "strict"
let TRY = 2, RND = A.mode === "quick" ? 2 : 3   // 真值见 stage-manifest.json#retryPolicy（载入契约后覆盖）
const T = { literature: "文献调研", data: "数据探索", assumption: "假设定义", formulation: "公式化", implementation: "实现", computation: "计算", sanity: "Sanity", visualization: "可视化", robustness: "鲁棒性", localComplete: "小问完成", crossReview: "跨问复核", writing: "写作", finalReview: "终审" }
const PERS = ["judge", "adversary", "application"]
const BRIEF = "返回{status,artifact_path,summary}；status∈PASS/DRAFT/NEEDS_REVISION/FAIL/SKIPPED/PASS_WITH_WARNING；≤200字"
let dg = false
let envPy = "python3"   // 默认系统 python；ensureEnv 后按 env-report.json 更新
const PYLINE = () => `\n## Python 环境（以 ${IM}/env-report.json 为准）：${envPy}；所有 python 执行一律用该路径；依赖缺失→优先 venv 安装、失败降级纯 numpy/scipy，绝不因缺库 FAIL`
const sm = []
const parseAny = x => {
  if (!x) return null
  if (typeof x !== "string") return x
  let t = x.trim()
  t = t.replace(/^```[^\n]*\n?/, "").replace(/\n?```\s*$/, "").trim()  // 剥围栏行（含语言标识，如 ```json）
  t = t.replace(/```/g, "")                                            // 兜底：残留围栏
  try { return JSON.parse(t) } catch (e) { return null }
}
async function ca(p, s, l) { try { return await agent(p, s ? { schema: s, label: l || "mm" } : { label: l || "mm" }) } catch (e) { log("⚠ agent 异常[" + (l || "mm") + "]: " + (e && e.message ? e.message : e)); return null } }
async function rf(path) { const r = await ca(`Read ${path}; 存在输出内容，否则 "NOT_FOUND"。`, null); if (!r) return null; const t = typeof r === "string" ? r.trim() : JSON.stringify(r); return t === "NOT_FOUND" ? null : t }
// boot 批量读的**摘要契约**：只取字段、不回吐文件正文。
// 原因（实测）：read 工具单文件 50 KiB、单行 1500 字符硬截断，全量回吐 ⇒ 非 JSON ⇒ 整个 boot「全有或全无」；
// 该文件集随探针累积单调增长（probes/manifest.json 曾达 148 KB / 116 KB），本项目因此启动失败 6 次（见 docs/pending-changes §4.4）。
const BOOT_SPEC = `输出 JSON 对象（**只取字段，禁止回吐文件正文**；任何字段都不得内联文件原文，超 8 KB 的内容一律摘要）：
{"<完整路径>": <摘要>}
- 00-problem.json → {"problemId":"<id>","questions":["1","2"]}（questions 取 analysis.subQuestions[].id，缺则取顶层 questions[]；字符串数组，保持原顺序）
- state.json → {"problemId":"<id>","gates":{…},"iterations":{…}}（gates/iterations 原样透传，它们是短标量映射）
- *manifest.json → {"keys":["<键名，最多 12 个>"],"count":<条目总数>,"primitivesVersion":"<有则填>","selftestPassed":<true|false|null>}
- 文件不存在 → "NOT_FOUND"
不确定的字段直接省略；仅 JSON，不要代码围栏。`
async function rfMany(paths, label) {
  const r = await ca(`一次并列 Read 以下全部文件（不遗漏、不逐个读）:\n${paths.map(p => "- " + p).join("\n")}\n${BOOT_SPEC}`, null, label || "read-many")
  const o = parseAny(r)
  // 形状校验：至少一件非 manifest 文件给出「可用的摘要对象」或「旧的全文 JSON 字符串」；否则视为失败走 a2 回退
  const usable = o && typeof o === "object" && Object.entries(o).some(([k, v]) => {
    if (/manifest\.json$/.test(k) || v === "NOT_FOUND") return false
    if (typeof v === "string") return !!parseAny(v)
    return !!(v && typeof v === "object" && (v.problemId || v.gates))
  })
  // 摘要里 00-problem 的 questions 为空 = 强信号（读残/漏字段）→ 走回退拿完整列表（全新 run 没有 gates 可补）
  const pe = Object.entries(o || {}).find(([k]) => /00-problem\.json$/.test(k))
  const probEmpty = !!(pe && pe[1] && typeof pe[1] === "object" && !(Array.isArray(pe[1].questions) && pe[1].questions.length))
  if (usable && !probEmpty) return o
  // a2 回退：摘要失败时只对「关键两件」走全量读；manifest 缺席由 buildAssets 的降级文案兜底（避免再赌一次大文件）
  const fb = {}
  for (const q of paths.filter(x => !/manifest\.json$/.test(x))) { const s = await rf(q); if (s) fb[q] = s }
  if (Object.keys(fb).length) log("⚠ boot 摘要读取失败 → 已回退全量读 " + Object.keys(fb).length + " 件关键文件")
  return Object.keys(fb).length ? fb : null
}

// 可复用资产清单（§1.3-4/5）：启动时随 boot 批量读入 manifest → 注入每个阶段/评审/修订提示词
// 目的：让"复用"成为阻力最小的路径（看得见 + selftest 一条命令 + 探针缓存命中秒回），而不是靠门禁强制
const MANIFESTS = ["pool/manifest.json", "pool/problem/manifest.json", "probes/manifest.json"]
const POOL_STAGES = ["data", "formulation", "implementation", "computation", "sanity", "visualization", "robustness"]   // 会写代码的阶段才注入 _pool.md
let ASSETS = ""
function assetsLine(live) {
  return ASSETS + (live
    ? `；本阶段已并列读入 ${MANIFESTS.join("、")}（**以文件为准**，上面的启动快照可能已过期；已存在的实现禁止再 cp 覆盖）`
    : `；清单 ${MANIFESTS.join("、")} 需要时自行 Read（上面的启动快照可能已过期）`)
}
function buildAssets(boot) {
  const rd = k => { const t = boot && boot[k]; return t && String(t).trim() !== "NOT_FOUND" ? parseAny(t) : null }
  const pm = rd(outDir + "/pool/manifest.json")
  const om = rd(outDir + "/pool/problem/manifest.json")
  const qm = rd(outDir + "/probes/manifest.json")
  // boot 摘要形态（只取字段：{keys:[…],count,primitivesVersion,selftestPassed}）与全量形态（{entries:{…}} / {probes:{…}}）都认
  const keys = o => !o || typeof o !== "object" ? []
    : (o.entries && typeof o.entries === "object" ? Object.keys(o.entries)
      : (Array.isArray(o.keys) ? o.keys.map(String) : []))
  const pkeys = o => !o || typeof o !== "object" ? []
    : (o.probes && typeof o.probes === "object" ? Object.keys(o.probes)
      : (Array.isArray(o.keys) ? o.keys.map(String) : []))
  const cnt = (o, ks) => (o && typeof o.count === "number" ? o.count : ks.length)
  const names = keys(pm), cores = keys(om), probes = pkeys(qm)
  const pv = (pm && pm.primitivesVersion) || "?"
  const selOk = !!(pm && (typeof pm.selftestPassed === "boolean" ? pm.selftestPassed : (pm.selftest && pm.selftest.passed)))
  const a = cnt(pm, names)
    ? `原语池 pool/primitives.py 已登记 ${cnt(pm, names)} 项（${names.slice(0, 6).join("、")}${cnt(pm, names) > 6 ? "…" : ""}，v${pv}${selOk ? "，selftest 通过" : ""}）`
    : "启动快照未见原语登记（pool/primitives.py 若已存在就直接 import，禁止再 cp 覆盖；确未建立才 cp 技能根副本并 --manifest）"
  const c = cnt(om, cores)
    ? `题专用核心池 pool/problem/ 已登记 ${cnt(om, cores)} 项（${cores.slice(0, 6).join("、")}${cnt(om, cores) > 6 ? "…" : ""}）`
    : "启动快照未见题专用核心登记（会被多问复用的判据/求解/目标函数写 pool/problem/<题>/*.py，并登记 pool/problem/manifest.json）"
  const b = cnt(qm, probes)
    ? `探针池 probes/ 已登记 ${cnt(qm, probes)} 条（结果缓存 probes/results/，命中秒回）`
    : "启动快照未见探针登记（探针写 probes/<角色>/<目的>.py，用 probe_cache 缓存结果）"
  return `可复用资产（先查再用；已有同口径实现禁止重写）：${a}；${c}；${b}；清单/用法见 _common.md §5–6`
}

// 06/09：核验成本纪律（字面注入，防散文漂移；规则全文见 docs/performance.md §6.1）
const COSTLINE = s => ["computation", "robustness"].includes(s)
  ? `核验成本纪律（**必须执行，非建议**）：嵌套核验（阶梯/扫参/对拍/bootstrap）**先估后跑**——用 ≤30 s 标定跑量测出单步价 → 算预估总成本 → 与预算 min(≤15 分钟, 8× 本问生产主体墙钟) 比较；调用带 「--budget <秒> --estimate <预估秒>」（超预算会被拒绝并给缩窗建议）；超预算按 **缩窗（前缀窗优先）→ 减档 → 降精度** 固定顺序缩，窗长/档数变更回写 draft/baseline-registry.md 的预注册条目；**逐档落盘** pc.checkpoint_put(key,"<档名>",payload)、重跑先 pc.checkpoint_get 跳过已完成档（kill 不作废）；档间无依赖时并行；perf 写 costEstimate_s/budget_s/tiers/shrink。规则全文 ${SD}/docs/performance.md §6.1`
  : ""

// 阶段 glue：模板/状态/依赖 → 执行 → 写产物 → 更新 state+ledger → 返回
function stagePrompt(q, s, m) {
  const k = q ? q + "." + s : s
  const lay = (m.outputLayout[s] || "").replace(/\{id\}/g, q || "")
  const deps = (m.deps[s] || []).map(d => {
    if (/[\u4e00-\u9fff]/.test(d)) return d                                  // 说明型依赖（如「全部产物」）原样注入
    if (/^(pool|probes)\//.test(d)) return outDir + "/" + d                  // 池/探针池在 outputDir 根，不在 intermediates/ 下
    const p = q ? d.replace(/\{id\}/g, q) : d.replace(/\{id\}\//g, "")
    return IM + "/" + p                                                       // 路径型依赖补 intermediates/ 前缀
  }).join("，")
  return [
    `## 阶段 ${k}：一次并列 Read ${PD}/_common.md 与 ${PD}/${m.prompts[s]}${POOL_STAGES.includes(s) ? "、" + PD + "/_pool.md（代码池手册）" : ""}（公共纪律 + 本阶段模板；**每轮必读，不得凭记忆或沿用上轮的印象**）、状态 ${IM}/state.json、依赖 ${deps||"无"}、可复用资产清单 ${MANIFESTS.join("、")}`,
    `执行：按两份模板执行（冲突时以阶段模板 ${m.prompts[s]} 为准）；技能根 ${SD}（规范 ${SD}/docs/、工具 ${SD}/scripts/，用法见 _common.md §6）；产物写 ${IM}/${lay}（mkdir -p）`,
    assetsLine(true),
    ...(COSTLINE(s) ? [COSTLINE(s)] : []),
    `完成后按 ${PD}/state-schema.md 更新 state.json（artifacts 一律用相对 intermediates/ 路径；就地合并，其余键保留），并追加 ledger 一行 \`${k}: <status> <产物相对路径> <≤50字>\``,
    `${BRIEF}；ctx q=${q||"全题"} mode=${A.mode||"full"} strict=${STRICT} date=${new Date().toISOString().slice(0,10)}`,
    PYLINE(),
  ].join("\n")
}
function gatePrompt(g, gk, q) {
  return [
    `## 门禁 ${gk}→${g.before}：验证 ${q ? g.check.replace(/该问/g, q) : g.check}；根目录 ${IM}`,
    `工具纪律：一次并列 Read 所需文件再核对，不逐文件往返。`,
    `按事实置 state.json gates["${gk}"]="PASS"|"FAIL"（就地合并，其余键保留）；追加 ledger 一行 \`${gk}: <PASS|FAIL> - <≤50字：核对了什么、结论依据>\`；返回{status:"PASS"|"FAIL",artifact_path:"",summary:"≤200字"}`,
    PYLINE(),
  ].join("\n")
}
const degradePrompt = k => [
  `## 降级 ${k}（专职状态节点）：该阶段已连续 ${TRY} 次失败，壳判定不再重试。`,
  `你的唯一职责是**记录降级事实**：不补做该阶段任务、不产出该阶段产物、不重试。`,
  `一次并列 Read ${PD}/state-schema.md（§键约定 + §更新职责·失败降级节点）、${IM}/state.json、${IM}/ledger.md 尾部；然后**就地合并** state.json（schema/problemId/其它 question.stage 记录等既有键一律保留，禁止整体覆盖）。`,
  `写 state.json：gates["${k}"]="SKIPPED"；**不写** iterations/artifacts（该阶段没有可用产物，见 schema）。`,
  `追加 ledger 一行（append，不删改既有行）：\`${k}: SKIPPED - <≤50字：失败原因与对下游的影响>\``,
  `返回 {status:"SKIPPED", artifact_path:"", summary:"≤200字：降级原因 + 下游影响"}`,
  PYLINE(),
].join("\n")
const finalizePrompt = (k, v, r, dr) => [
  `## 公式化收束 ${k}（专职状态节点）：第 ${r} 轮三视角评审结束，子流程结论 = ${v}。`,
  `你的唯一职责是**把该结论写进状态文件与账本**：不改 draft.md / review-r*.md / self-check.md（只读）、不重跑评审、不补写分析。**唯一例外＝「未结转项」结转（A2）**：把本轮评审的**登记级条目 + 未闭环必须改**逐条追加到 ${dr.replace("draft.md", "handoff.md")} 的 \`## 未结转项（收束结转·只增不改）\` 小节（每条：轮次 · 条目 ID · 一句话 · 去向）；无则写一行「无」。`,
  `一次并列 Read ${PD}/state-schema.md（§键约定 + §更新职责·公式化子流程）、${IM}/state.json、${IM}/ledger.md 尾部；然后**就地合并** state.json（schema/problemId/其它 question.stage 记录等既有键一律保留，禁止整体覆盖）。`,
  `写 state.json：iterations["${k}"] = 读到的旧值 + 1 + ${r}（旧值缺失时取 1 + ${r}；含义 = 本次 formulator 1 次 + 本轮评审 ${r} 轮，多次尝试累加，只增不减）；gates["${k}"]="${v}"（**必须原样写入该值**——本键由评审收敛判定，PASS 已含「仅建议级意见」之意，不得改写为 PASS_WITH_WARNING/DRAFT）；artifacts["${k}"]="${dr}"；current={"question":null,"stage":null}。`,
  `追加 ledger 一行（append，不删改既有行；本阶段已有 formulator/修订行，继续追加即可）：\`${k}.finalize: ${v} ${dr} <≤50字：第${r}轮三视角结论 + 结转条数（登记级 n / 未闭环必须改 m）>\``,
  `返回 {status:"${v}", artifact_path:"${dr}", summary:"≤200字：轮数 / 三视角结论 / 遗留项去向"}`,
  PYLINE(),
].join("\n")

// 公式化子流程：formulator→自查→评审团(3 视角并行)⇄修订（full 最多 3 轮 / quick 最多 2 轮；三评审全 PASS 即收束）
async function runFormulation(q, m, sc, a) {
  const k = q + ".formulation"
  const d = IM + "/" + q + "/04-formulation"
  const dr = d + "/draft.md"
  const drRel = q + "/04-formulation/draft.md"  // 记录用相对路径（artifacts 契约），写入仍用 dr 绝对路径
  const sf = d + "/self-check.md"
  const ok1 = await ca(stagePrompt(q, "formulation", m) + (a > 1 ? `\n【第2次】**动手前先重读 ${PD}/${m.prompts["formulation"]}**（模板可能已更新；实测上一跑的第 2 次尝试没读模板就重写）；改策略：重写主线或调假设，解决上轮必须改` : "") + `\n【节点1 · formulator】按阶段模板产本小问方案：${dr}（主产物）+ ${d}/baseline-registry.md（预注册，**先于 draft 完成**）+ ${d}/symbols.json；写完追加 ledger 一行 \`${k}: DRAFT ${drRel} <≤50字>\`，并在 state.json 里**就地合并** gates["${k}"]="NEEDS_REVISION"、artifacts["${k}"]="${drRel}"、current（其余既有键保留，禁止整体覆盖）`, sc, "formulator")
  if (!ok1) return null
  const ok2 = await ca(`【节点2 · 三维自查】一次并列 Read ${PD}/_common.md 与 ${dr}（公共纪律：数字单一真源/工具纪律/读入范围），按数学正确 / 可实现 / 创新真实三方面自查（关键处独立重算，不采信草案自述）；结论与需改进项写入 ${sf}；**不改 ${dr}、不改 state.json/ledger.md**（改进由后续修订节点落到 draft）；${BRIEF}`, sc, "selfcheck")
  if (!ok2) return null
  let r = 0
  for (;;) {
    r++
    const raw = await parallel(PERS.map(p => () => ca(
      `【评审r${r}-${p}】一次并列 Read ${PD}/_common.md、${PD}/_review-common.md（评审通用规则）、${PD}/formulation-reviewer-${p}.md、${dr}、${sf}、${d}/baseline-registry.md、${d}/symbols.json、${IM}/${q}/01-literature/literature.md${r > 1 ? "、" + d + "/review-r" + (r - 1) + "-" + p + ".md" : ""}；写 ${d}/review-r${r}-${p}.md；不更新 state/ledger（收束节点统一写）；${assetsLine()}；返回{status:"PASS"|"NEEDS_REVISION",artifact_path,summary}（PASS=无必须改）` + PYLINE(),
      sc, "review:" + p)))
    const vs = raw.map(x => x && x.status)
    if (vs.length && vs.every(v => v === "PASS")) {
      await ca(finalizePrompt(k, "PASS", r, drRel), sc, "finalize")
      return { accepted: true, status: "PASS", artifact_path: drRel }
    }
    if (vs.every(v => !v) && r < RND) {
      log("⚠ 评审 r" + r + " 全部异常（无有效意见）→ 跳过本轮修订，直接重跑评审")
      continue
    }
    if (r >= RND) {
      const v = vs.every(v => !v) ? "FAIL" : "NEEDS_REVISION"
      await ca(finalizePrompt(k, v, r, drRel), sc, "finalize")
      return { accepted: false, status: v, why: raw.filter(Boolean).map(x => x.summary).join(" | ").slice(0, 300) }
    }
    const okR = await ca(`【修订r${r}】**精准手术**（禁止整篇重写 draft）：先**整读 ${dr}**（至少被点名节 ±1 节；D：没有全局视野就会改出新矛盾）→ 再一次并列 Read ${PD}/_common.md、${PD}/_review-common.md（评审通用规则）、${d}/review-r${r}-*.md；**只改被点到的段落/公式/表格行**（用 Edit 定点替换；未被点到的章节一字不动，draft 只放方案本体）；**逐条处置表写 ${d}/revision-log.md**（本轮只写一个 \`## rN 处置\` 小节：一张表 \`条目ID|级别|一句话|处置|落点|状态\`，加仅在非空时出现的 \`### 未处置/留给下游\`、\`### 机械核验\`；条目 ID 沿用评审原编号、**只增不改**，必须改/登记级行数须与评审计数一致；格式契约见 ${PD}/phase-04-formulation.md；draft 内**不得新增或保留**处置表/历史归档章节，只在 ${dr} 留 1 行指针）；若修订影响基准协议/符号定义，同步更新 ${d}/baseline-registry.md、${d}/symbols.json（版本号递增）并核对一致；数字以 ${IM}/${q}/06-computation/results.json 为唯一真源，产物内只写锚点引用不复抄数值；探针一律走 probes/<角色>/<目的>.py + 结果缓存（禁止再写 /tmp 一次性脚本）；追加 ledger 一行 \`${k}.revision-r${r}: <status> ${drRel} <≤50字>\`（**不改 state.json**）；**例外（B1）**：若**同一节被连续两轮点名**，或本轮改动**跨 ≥3 节 / ≥3 个符号定义**，则允许**整节或整篇重写**——重写必须在本轮 \`revision-log.md\` 小节给出「重写范围 + 与上版逐节差异摘要」，且既有结论数字与口径不得变；**A（影响面清单，必做）**：凡改动**公式/系数/边界项/符号定义**，必须在本轮 \`revision-log.md\` 表格后追加一节 \`### 同步清单\`，逐行给「改动的量/符号 → 全文出现处(行号) → 已同步?」，并在收尾前用一次 \`grep -n\` 核对该量在 draft / baseline-registry / symbols 的**全部**出现处；漏同步＝本轮修订未完成。**例外**：纯措辞/引用键类改动可只写「无派生量」一行；${BRIEF}` + PYLINE(), sc, "revise")
    if (!okR) return null
  }
}

// 阶段执行：门禁(manifest.gates)→执行（失败收敛：2次→换策略/降级）
async function runStage(q, s, m, sc, gs, done) {
  const k = q ? q + "." + s : s
  if (done.has(k)) return { ok: true, status: "RESUMED", artifact: "" }
  phase(T[s])
  for (const g of m.gates || []) {
    if (g.before !== s) continue
    const gk = q ? q + "." + g.boundary : g.boundary
    if (gs[gk] === "PASS") continue
    let pass = false
    for (let a = 1; a <= TRY && !pass; a++) {
      const r = await ca(gatePrompt(g, gk, q), sc, "gate:" + gk)
      pass = !!(r && r.status === "PASS")
      if (!pass) log("⚠ 门禁未过 " + gk + " 第" + a + "次")
    }
    if (!pass) return { blocked: { gate: g.boundary, key: k, detail: g.check } }
    gs[gk] = "PASS"
  }
  let res = null
  for (let a = 1; a <= TRY; a++) {
    res = s === "formulation" ? await runFormulation(q, m, sc, a) : await runSimple(q, s, m, sc, a)
    if (res && res.accepted) { if (res.status === "SKIPPED") dg = true; log("✓ " + k + " → " + res.status); return { ok: true, status: res.status, artifact: res.artifact_path || "" } }
    if (s === "formulation" && a === TRY) return { blocked: { gate: "solve-start", key: k, detail: (res && res.why) || "formulation 未收敛" } }
    log("⚠ " + k + " 第" + a + "次失败")
  }
  if (s === "finalReview") {   // 终审是最后一道质量门禁，没有下游可拦 → 不降级，直接 blocked
    log("⚠ finalReview 连续 " + TRY + " 次失败 → 不降级（无下游门禁兜底），按 blocked 返回")
    return { blocked: { gate: "final-review", key: k, detail: "终审连续失败，未产出定稿（摘要数字溯源/组装未完成）" } }
  }
  await ca(degradePrompt(k), sc, "degrade:" + k)
  dg = true
  log("⚠ " + k + " 降级 SKIPPED")
  return { ok: true, status: "SKIPPED", artifact: "" }
}
async function runSimple(q, s, m, sc, a) {
  const k = q ? q + "." + s : s
  const r = await ca(stagePrompt(q, s, m) + (a > 1 ? `\n【重试】**动手前先重读 ${PD}/${m.prompts[s]}**（模板可能已更新）；改策略：缩小范围、先产最小版、写明障碍` : ""), sc, "run:" + k)
  if (!r || r.status === "FAIL" || r.status === "NEEDS_REVISION") return null
  return { accepted: true, status: r.status, artifact_path: r.artifact_path || "" }
}

// 启动：契约+Stage1产物+state 读写（checkpoint 模式）
async function loadContracts() {
  for (let a = 1; a <= TRY; a++) {
    const r = await ca(`读 ${PD}/stage-manifest.json 与 ${PD}/response-schema.json；输出 {"manifest":<文件1>,"responseSchema":<文件2>}；仅 JSON，不要 Markdown 代码围栏，不要解释文字`, null, "contracts")
    const o = parseAny(r)
    const man = o && parseAny(o.manifest)
    const sch = o && parseAny(o.responseSchema)
    if (man && sch && Array.isArray(man.perQuestionStages)) return { manifest: man, responseSchema: sch }
  }
  return null
}
function parseProblemsText(t) {
  if (!t || String(t).trim() === "NOT_FOUND") return null
  const o = parseAny(t)
  if (!o) return null
  // 兼容 00-problem.json 两种形态：① 顶层 {problemId, questions}（旧契约）② {selectedProblem, problem:{id, analysis:{subQuestions:[{id}]}}}（Stage 1 实际落盘形态）
  const a = (o.problem && o.problem.analysis) || o.analysis || {}
  const sq = Array.isArray(a.subQuestions) ? a.subQuestions : []
  const ids = sq.map(x => x && (x.id ?? x.questionId ?? x.number)).filter(x => x !== undefined && x !== null).map(String)
  const pid = o.problemId || o.selectedProblem || (o.problem && o.problem.id) || a.problemId || "unknown"
  const qs = Array.isArray(o.questions) && o.questions.length ? o.questions.map(String) : ids
  return { problemId: String(pid), questions: qs }
}
function parseStateText(t, pid) {
  const o = parseAny(t)
  if (o && o.problemId === pid) return o
  return null
}
async function initState(pid, sc) {
  const r = await ca(`mkdir -p ${IM} 后用 Write 建(覆盖)：1)state.json：{"schema":"v1","problemId":"${pid}","current":{"question":null,"stage":null},"iterations":{},"gates":{},"artifacts":{},"deps":{}} 2)ledger.md 首行：# math-model ledger — ${pid}；返回{status:"PASS",artifact_path:"${IM}/state.json",summary:"init"}`, sc, "init")
  return !!(r && r.status === "PASS")
}
async function ledgerTail() {
  const r = await rf(IM + "/ledger.md")
  return r ? r.split("\n").slice(-10).join("\n") : "N/A"
}

// 环境初始化：项目 venv（幂等，env-report.json 为权威；无网/只读/失败 → fallback 系统 python，不阻塞）
async function ensureEnv(pid) {
  const venv = outDir + "/.venv"
  return await ca(`## 环境初始化（幂等，problemId=${pid}）：
1) 若 ${IM}/env-report.json 存在且 problemId 相同 → 读它并返回{status:"PASS",artifact_path:"${IM}/env-report.json",summary:"env reused"}，不再重建/重装
2) 否则 python3 -m venv ${venv}（已存在则跳过）；venv python = ${venv}/bin/python
3) ${venv}/bin/python -m pip install --quiet numpy scipy pandas statsmodels matplotlib openpyxl joblib numba（已满足的包自动跳过；整体限时 5 分钟，超时/失败→记录后继续，不阻塞）
4) 探测版本并写 ${IM}/env-report.json：{"problemId":"${pid}","python":"${venv}/bin/python","fallback":false,"libs":{"numpy":"x","scipy":"x","pandas":"x","statsmodels":"x","matplotlib":"x","openpyxl":"x","joblib":"x","numba":"x"},"autoInstalled":[...],"failed":[...]}；pip 不可用/无网/venv 创建失败 → python 改 "python3"、fallback=true、failed 写原因
5) 返回{status:"PASS",artifact_path:"${IM}/env-report.json",summary:"env py=<python> libs=<n> fallback=<true|false>"}`, null, "env")
}

// 主循环：逐问串行 10 阶段 → 运行级 3 阶段
phase("初始化")
const err = t => ({ status: "error", statePath: IM + "/state.json", artifactSummary: "", ledgerTail: t })
const bail = async b => { phase("收束"); return { status: "blocked", statePath: IM + "/state.json", artifactSummary: sm.join("；"), ledgerTail: await ledgerTail(), blocked: b } }
const C = await loadContracts()
if (!C) return err("契约读取失败（prompts/stage-manifest/response-schema.json）")
const m = C.manifest, sc = C.responseSchema
const RP = m.retryPolicy || {}, MKEY = A.mode === "quick" ? "quick" : "full"
TRY = RP.stageAttempts || TRY
RND = (RP.formulationRounds || {})[MKEY] || RND
// 批量读启动文件（一个 agent 会话，替代微型会话；解析健壮：围栏/语言行由 parseAny 处理）
// 三份 manifest 只在 resume 时随 boot 读：全新 run 里它们必然不存在（pool/problem/manifest.json 更是 run 中途才产生），
// 读到的只会是 NOT_FOUND。资产发现不依赖这里——每个阶段的提示词都要求并列 Read 这三份清单（以文件为权威）。
const bootPaths = [IM + "/00-problem.json", IM + "/state.json"]
if (A.resume) bootPaths.push(outDir + "/pool/manifest.json", outDir + "/pool/problem/manifest.json", outDir + "/probes/manifest.json")
const boot = await rfMany(bootPaths)
ASSETS = buildAssets(boot)   // §1.3-4：可复用资产清单注入每个阶段/评审/修订提示词
const P = parseProblemsText(boot ? boot[IM + "/00-problem.json"] : null)
if (!P) return err("未找到 " + IM + "/00-problem.json（Stage 1 需先落盘）")
const questions = (P.questions.length ? P.questions : ["1"]).map(id => "q" + String(id).replace(/^[Qq]/, ""))
if (!P.questions.length) log("⚠ 00-problem.json 未解析出小问列表（analysis.subQuestions[].id 缺失）→ 按单问 q1 处理；若题目有多个小问请补全 00-problem.json")
if (P.problemId === "unknown") log("⚠ 00-problem.json 未解析出 problemId（selectedProblem/problem.id 均缺失）→ state.json 将记为 unknown，resume 会因此失配")
let state = null
if (A.resume) {
  state = parseStateText(boot ? boot[IM + "/state.json"] : null, P.problemId)
  if (!state) return err("resume 状态读取失败（拒绝覆盖 state.json，请人工检查后重试）")
} else {
  const prev = parseStateText(boot ? boot[IM + "/state.json"] : null, P.problemId)
  const n = prev ? Object.keys(prev.gates || {}).length : 0
  if (n) log("⚠ 已存在同一题（" + P.problemId + "）的 state.json（" + n + " 条 gate 记录），但本次未传 resume=true → 将从头重跑并覆盖既有产物；需要续跑请改传 resume:true")
}
const gs = (state && state.gates) || {}
if (!state && !(await initState(P.problemId, sc))) return err("initState 写入失败")
// 防御（boot 摘要可能漏/错小问）：把 state.gates 里出现过的小问补进列表——只增不减，避免静默跳过整问
{
  const seen = new Set(questions)
  for (const k of Object.keys(gs)) {
    const m = /^(q\d+)\./.exec(k)
    if (m && !seen.has(m[1])) { seen.add(m[1]); questions.push(m[1]); log("⚠ " + m[1] + " 不在 00-problem.json 的小问列表里，但 state.gates 有它的记录 → 已补入") }
  }
  if (questions.length > 1) questions.sort((a, b) => (parseInt(a.slice(1), 10) || 0) - (parseInt(b.slice(1), 10) || 0))
}
const done = A.resume ? new Set(Object.keys(gs).filter(k => gs[k] && "PASS,PASS_WITH_WARNING,SKIPPED".includes(gs[k]))) : new Set()
// 环境初始化：项目 venv（幂等；env-report.json 为权威，无网/失败回退系统 python）
await ensureEnv(P.problemId)
const envRep = parseAny(await rf(IM + "/env-report.json"))   // ensureEnv 之后现读，取到新写入的 venv 路径
if (envRep && typeof envRep.python === "string" && envRep.python) envPy = envRep.python
for (const [q, s] of questions.flatMap(q => m.perQuestionStages.map(s => [q, s])).concat(m.runLevelStages.map(s => [null, s]))) {
  const r = await runStage(q, s, m, sc, gs, done)
  const k = q ? q + "." + s : s
  if (r.blocked) return await bail(r.blocked)
  sm.push(k + "[" + r.status + "] " + r.artifact)
}
return { status: dg ? "degraded" : "ok", statePath: IM + "/state.json", artifactSummary: sm.join("；"), ledgerTail: await ledgerTail() }
