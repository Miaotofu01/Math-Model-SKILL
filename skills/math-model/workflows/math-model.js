// ═══ math-model 薄壳 V3：无 fs，磁盘全经 agent() 子代理 ═══
// 契约(manifest/schema/state-schema.md)启动经子代理读取；业务全在 prompts/phase-*.md；壳只做路由/门禁/收敛

const A = typeof args === "object" && args ? args : {}
const outDir = (A.outputDir || "math-model-output").replace(/^\.\/|\/+$/g, "")
const IM = outDir + "/intermediates"
const SD = A.templateDir ? A.templateDir.replace(/\/templates\/?$/, "") : "skills/math-model"   // 技能根：规范 docs/ 与工具 scripts/ 所在处
const PD = SD + "/prompts"
const STRICT = A.innovationStrictness || "strict"
const TRY = 2, RND = A.mode === "quick" ? 2 : 3
const T = { literature: "文献调研", data: "数据探索", assumption: "假设定义", formulation: "公式化", implementation: "实现", computation: "计算", sanity: "Sanity", visualization: "可视化", robustness: "鲁棒性", localComplete: "小问完成", crossReview: "跨问复核", writing: "写作", finalReview: "终审" }
const PERS = ["judge", "adversary", "application"]
const BRIEF = "返回{status,artifact_path,summary}；status∈PASS/DRAFT/NEEDS_REVISION/FAIL/SKIPPED/PASS_WITH_WARNING；≤200字"
const LG = "追加 ledger：<key>: <status> <产物> <50字>"
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
async function rfMany(paths) {
  const r = await ca(`一次并列 Read 以下全部文件（不遗漏、不逐个读）:\n${paths.map(p => "- " + p).join("\n")}\n输出 JSON 对象：{"<完整路径>": "<文件内容原文 或 NOT_FOUND>"}；仅 JSON，不要代码围栏。`, null, "read-many")
  const o = parseAny(r)
  return o && typeof o === "object" ? o : null
}

// 可复用资产清单（§1.3-4/5）：启动时随 boot 批量读入 manifest → 注入每个阶段/评审/修订提示词
// 目的：让"复用"成为阻力最小的路径（看得见 + selftest 一条命令 + 探针缓存命中秒回），而不是靠门禁强制
const MANIFESTS = ["pool/manifest.json", "pool/problem/manifest.json", "probes/manifest.json"]
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
  const keys = o => (o && o.entries && typeof o.entries === "object" ? Object.keys(o.entries) : [])
  const names = keys(pm), cores = keys(om)
  const probes = qm && qm.probes && typeof qm.probes === "object" ? Object.keys(qm.probes) : []
  const a = names.length
    ? `原语池 pool/primitives.py 已登记 ${names.length} 项（${names.slice(0, 6).join("、")}${names.length > 6 ? "…" : ""}，v${(pm && pm.primitivesVersion) || "?"}${pm && pm.selftest && pm.selftest.passed ? "，selftest 通过" : ""}）`
    : "启动快照未见原语登记（pool/primitives.py 若已存在就直接 import，禁止再 cp 覆盖；确未建立才 cp 技能根副本并 --manifest）"
  const c = cores.length
    ? `题专用核心池 pool/problem/ 已登记 ${cores.length} 项（${cores.slice(0, 6).join("、")}${cores.length > 6 ? "…" : ""}）`
    : "启动快照未见题专用核心登记（会被多问复用的判据/求解/目标函数写 pool/problem/<题>/*.py，并登记 pool/problem/manifest.json）"
  const b = probes.length
    ? `探针池 probes/ 已登记 ${probes.length} 条（结果缓存 probes/results/，命中秒回）`
    : "启动快照未见探针登记（探针写 probes/<角色>/<目的>.py，用 probe_cache 缓存结果）"
  return `可复用资产（先查再用；已有同口径实现禁止重写）：${a}；${c}；${b}；清单/用法见 _common.md §5–6`
}

// 阶段 glue：模板/状态/依赖 → 执行 → 写产物 → 更新 state+ledger → 返回
function stagePrompt(q, s, m) {
  const k = q ? q + "." + s : s
  const lay = (m.outputLayout[s] || "").replace(/\{id\}/g, q || "")
  const deps = (m.deps[s] || []).map(d => {
    if (/[\u4e00-\u9fff]/.test(d)) return d                                  // 说明型依赖（如「全部产物」）原样注入
    const p = q ? d.replace(/\{id\}/g, q) : d.replace(/\{id\}\//g, "")
    return IM + "/" + p                                                       // 路径型依赖补 intermediates/ 前缀
  }).join("，")
  return [
    `## 阶段 ${k}：一次并列 Read ${PD}/_common.md 与 ${PD}/${m.prompts[s]}（公共纪律 + 本阶段模板）、状态 ${IM}/state.json、依赖 ${deps||"无"}、可复用资产清单 ${MANIFESTS.join("、")}`,
    `执行：按两份模板执行（冲突时以阶段模板 ${m.prompts[s]} 为准）；技能根 ${SD}（规范 ${SD}/docs/、工具 ${SD}/scripts/，用法见 _common.md §6）；产物写 ${IM}/${lay}（mkdir -p）`,
    assetsLine(true),
    `完成后按 ${PD}/state-schema.md 更新 state.json（artifacts 一律用相对 intermediates/ 路径），${LG}`,
    `${BRIEF}；ctx q=${q||"全题"} mode=${A.mode||"full"} strict=${STRICT} date=${new Date().toISOString().slice(0,10)}`,
    PYLINE(),
  ].join("\n")
}
function gatePrompt(g, gk, q) {
  return [
    `## 门禁 ${gk}→${g.before}：验证 ${q ? g.check.replace(/该问/g, q) : g.check}；根目录 ${IM}`,
    `工具纪律：一次并列 Read 所需文件再核对，不逐文件往返。`,
    `按事实置 state.json gates["${gk}"]="PASS"|"FAIL"；${LG}；返回{status:"PASS"|"FAIL",artifact_path:"",summary}`,
    PYLINE(),
  ].join("\n")
}
const degradePrompt = k => `## 降级 ${k}：连续 ${TRY} 次失败。state.json：gates["${k}"]="SKIPPED"；${LG}；返回{status:"SKIPPED",artifact_path:"",summary}`
const finalizePrompt = (k, v, r, dr) => `【收束 ${k}】state.json：iter["${k}"]=${r + 1}；gates["${k}"]="${v}"；artifacts["${k}"]="${dr}"；current={"question":null,"stage":null}；${LG}；返回{status:"${v}",artifact_path:"${dr}",summary}` + PYLINE()

// 公式化子流程：formulator→自查→评审团(3 视角并行)⇄修订（full 最多 3 轮 / quick 最多 2 轮；三评审全 PASS 即收束）
async function runFormulation(q, m, sc, a) {
  const k = q + ".formulation"
  const d = IM + "/" + q + "/04-formulation"
  const dr = d + "/draft.md"
  const drRel = q + "/04-formulation/draft.md"  // 记录用相对路径（artifacts 契约），写入仍用 dr 绝对路径
  const sf = d + "/self-check.md"
  const ok1 = await ca(stagePrompt(q, "formulation", m) + (a > 1 ? "\n【第2次】改策略：重写主线或调假设，解决上轮必须改" : "") + `\n【节点1】产方案+baseline预注册，写 ${dr}、${d}/baseline-registry.md；gates["${k}"]="NEEDS_REVISION"`, sc, "formulator")
  if (!ok1) return null
  const ok2 = await ca(`【节点2 自查】读 ${dr}，按数学正确/可实现/创新真实自查，改进写 ${sf}；${BRIEF}（不更新state）`, sc, "selfcheck")
  if (!ok2) return null
  let r = 0
  for (;;) {
    r++
    const raw = await parallel(PERS.map(p => () => ca(
      `【评审r${r}-${p}】一次并列 Read ${PD}/_common.md、${PD}/formulation-reviewer-${p}.md、${dr}、${sf}${r > 1 ? "、" + d + "/review-r" + (r - 1) + "-" + p + ".md" : ""}；写 ${d}/review-r${r}-${p}.md；不更新 state/ledger（收束节点统一写）；${assetsLine()}；返回{status:"PASS"|"NEEDS_REVISION",artifact_path,summary}（PASS=无必须改）` + PYLINE(),
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
    const okR = await ca(`【修订r${r}】一次并列 Read ${PD}/_common.md、${dr} 与 ${d}/review-r${r}-*.md；逐条回应（改或说明），覆盖写回 ${dr}；若修订影响基准协议/符号定义，同步更新 ${d}/baseline-registry.md、${d}/symbols.json（版本号递增）并核对一致；数字以 ${IM}/${q}/06-computation/results.json 为唯一真源，产物内只写锚点引用不复抄数值；探针一律走 probes/<角色>/<目的>.py + 结果缓存（禁止再写 /tmp 一次性脚本）；${LG}；${BRIEF}（不更新state）` + PYLINE(), sc, "revise")
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
  const r = await ca(stagePrompt(q, s, m) + (a > 1 ? "\n【重试】改策略：缩小范围、先产最小版、写明障碍" : ""), sc, "run:" + k)
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
// 批量读启动文件（一个 agent 会话，替代微型会话；解析健壮：围栏/语言行由 parseAny 处理）
const boot = await rfMany([IM + "/00-problem.json", IM + "/state.json", outDir + "/pool/manifest.json", outDir + "/pool/problem/manifest.json", outDir + "/probes/manifest.json"])
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
