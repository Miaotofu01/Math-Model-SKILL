// ═══ math-model 薄壳 V3：无 fs，磁盘全经 agent() 子代理 ═══
// 契约(manifest/schema/state-schema.md)启动经子代理读取；业务全在 prompts/phase-*.md；壳只做路由/门禁/收敛

const A = typeof args === "object" && args ? args : {}
const outDir = (A.outputDir || "math-model-output").replace(/^\.\/|\/+$/g, "")
const IM = outDir + "/intermediates"
const PD = A.templateDir ? A.templateDir.replace(/\/templates\/?$/, "") + "/prompts" : "skills/math-model/prompts"
const STRICT = A.innovationStrictness || "strict"
const TRY = 2, RND = A.mode === "quick" ? 1 : 3
const T = { literature: "文献调研", data: "数据探索", assumption: "假设定义", formulation: "公式化", implementation: "实现", computation: "计算", sanity: "Sanity", visualization: "可视化", robustness: "鲁棒性", localComplete: "小问完成", crossReview: "跨问复核", writing: "写作", finalReview: "终审" }
const PERS = ["judge", "adversary", "application"]
const BRIEF = "返回{status,artifact_path,summary}；status∈PASS/DRAFT/NEEDS_REVISION/FAIL/SKIPPED/PASS_WITH_WARNING；≤200字"
const LG = "追加 ledger：<key>: <status> <产物> <50字>"
let dg = false
const sm = []
const parseAny = x => { if (!x) return null; if (typeof x !== "string") return x; try { return JSON.parse(x.replace(/```/g, "").trim()) } catch (e) { return null } }
async function ca(p, s, l) { try { return await agent(p, s ? { schema: s, label: l || "mm" } : { label: l || "mm" }) } catch (e) { return null } }
async function rf(path) { const r = await ca(`Read ${path}; 存在输出内容，否则 "NOT_FOUND"。`, null); if (!r) return null; const t = typeof r === "string" ? r.trim() : JSON.stringify(r); return t === "NOT_FOUND" ? null : t }

// 阶段 glue：模板/状态/依赖 → 执行 → 写产物 → 更新 state+ledger → 返回
function stagePrompt(q, s, m) {
  const k = q ? q + "." + s : s
  const lay = (m.outputLayout[s] || "").replace(/\{id\}/g, q || "")
  const deps = (m.deps[s] || []).map(d => d.includes("{id}") && q ? IM + "/" + d.replace(/\{id\}/g, q) : d).join("，")
  return [
    `## 阶段 ${k}：读模板 ${PD}/${m.prompts[s]}、状态 ${IM}/state.json、依赖 ${deps||"无"}`,
    `按模板执行，产物写 ${IM}/${lay}（mkdir -p）`,
    `完成后按 ${PD}/state-schema.md 更新 state.json，${LG}`,
    `${BRIEF}；ctx q=${q||"全题"} mode=${A.mode||"full"} strict=${STRICT}`,
  ].join("\n")
}
function gatePrompt(g, gk, q) {
  return [
    `## 门禁 ${gk}→${g.before}：验证 ${q ? g.check.replace(/该问/g, q) : g.check}；根目录 ${IM}`,
    `按事实置 state.json gates["${gk}"]="PASS"|"FAIL"；${LG}；返回{status:"PASS"|"FAIL",artifact_path:"",summary}`,
  ].join("\n")
}
const degradePrompt = k => `## 降级 ${k}：连续 ${TRY} 次失败。state.json：gates["${k}"]="SKIPPED"；${LG}；返回{status:"SKIPPED",artifact_path:"",summary}`
const finalizePrompt = (k, v, r, dr) => `【收束 ${k}】state.json：iter["${k}"]=${r + 1}；gates["${k}"]="${v}"；artifacts["${k}"]="${dr}"；${LG}；返回{status:"${v}",artifact_path:"${dr}",summary}`

// 公式化子流程：formulator→自查→评审团 parallel⇄修订（max3/quick1，全建议级收束）
async function runFormulation(q, m, sc, a) {
  const k = q + ".formulation"
  const d = IM + "/" + q + "/04-formulation"
  const dr = d + "/draft.md"
  const sf = d + "/self-check.md"
  const ok1 = await ca(stagePrompt(q, "formulation", m) + (a > 1 ? "\n【第2次】改策略：重写主线或调假设，解决上轮必须改" : "") + `\n【节点1】产方案+baseline预注册，写 ${dr}、${d}/baseline-registry.md；gates["${k}"]="NEEDS_REVISION"`, sc, "formulator")
  if (!ok1) return null
  const ok2 = await ca(`【节点2 自查】读 ${dr}，按数学正确/可实现/创新真实自查，改进写 ${sf}；${BRIEF}（不更新state）`, sc, "selfcheck")
  if (!ok2) return null
  let r = 0
  for (;;) {
    r++
    const raw = await parallel(PERS.map(p => () => ca(
      `【评审r${r}-${p}】读 ${PD}/formulation-reviewer-${p}.md、${dr}、${sf}${r > 1 ? "、" + d + "/review-r" + (r - 1) + "-" + p + ".md" : ""}；写 ${d}/review-r${r}-${p}.md；不更新 state/ledger（收束节点统一写）；返回{status:"PASS"|"NEEDS_REVISION",artifact_path,summary}（PASS=无必须改）`,
      sc, "review:" + p)))
    const vs = raw.map(x => x && x.status)
    if (vs.length && vs.every(v => v === "PASS")) {
      await ca(finalizePrompt(k, "PASS", r, dr), sc, "finalize")
      return { accepted: true, status: "PASS", artifact_path: dr }
    }
    if (r >= RND) {
      const v = vs.every(v => !v) ? "FAIL" : "NEEDS_REVISION"
      await ca(finalizePrompt(k, v, r, dr), sc, "finalize")
      return { accepted: false, status: v, why: raw.filter(Boolean).map(x => x.summary).join(" | ").slice(0, 300) }
    }
    const okR = await ca(`【修订r${r}】读 ${dr} 与 ${d}/review-r${r}-*.md；逐条回应（改或说明），覆盖写回 ${dr}；${LG}；${BRIEF}（不更新state）`, sc, "revise")
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
    const r = await ca(`读 ${PD}/stage-manifest.json 与 ${PD}/response-schema.json；输出 {"manifest":<文件1>,"responseSchema":<文件2>}（无代码块）`, null, "contracts")
    const o = parseAny(r)
    const man = o && parseAny(o.manifest)
    const sch = o && parseAny(o.responseSchema)
    if (man && sch && Array.isArray(man.perQuestionStages)) return { manifest: man, responseSchema: sch }
  }
  return null
}
async function loadProblems() {
  const r = await ca(`读 ${IM}/00-problem.json；存在输出 {"problemId":selectedProblem||problem.id||analysis.problemId||"unknown","questions":analysis.subQuestions 的id数组或[]}；否则 "NOT_FOUND"。仅JSON`, null, "stage1")
  if (!r || String(r).trim() === "NOT_FOUND") return null
  const o = parseAny(r)
  return o ? { problemId: String(o.problemId || "unknown"), questions: Array.isArray(o.questions) ? o.questions : [] } : null
}
async function loadState(pid) {
  const o = parseAny(await rf(IM + "/state.json"))
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

// 主循环：逐问串行 10 阶段 → 运行级 3 阶段
phase("初始化")
const err = t => ({ status: "error", statePath: IM + "/state.json", artifactSummary: "", ledgerTail: t })
const bail = async b => { phase("收束"); return { status: "blocked", statePath: IM + "/state.json", artifactSummary: sm.join("；"), ledgerTail: await ledgerTail(), blocked: b } }
const C = await loadContracts()
if (!C) return err("契约读取失败（prompts/stage-manifest/response-schema.json）")
const m = C.manifest, sc = C.responseSchema
const P = await loadProblems()
if (!P) return err("未找到 " + IM + "/00-problem.json（Stage 1 需先落盘）")
const questions = (P.questions.length ? P.questions : ["1"]).map(id => "q" + String(id).replace(/^[Qq]/, ""))
const state = A.resume ? await loadState(P.problemId) : null
const gs = (state && state.gates) || {}
if (!state && !(await initState(P.problemId, sc))) return err("initState 写入失败")
const done = A.resume ? new Set(Object.keys(gs).filter(k => gs[k] && "PASS,PASS_WITH_WARNING,SKIPPED".includes(gs[k]))) : new Set()
for (const [q, s] of questions.flatMap(q => m.perQuestionStages.map(s => [q, s])).concat(m.runLevelStages.map(s => [null, s]))) {
  const r = await runStage(q, s, m, sc, gs, done)
  const k = q ? q + "." + s : s
  if (r.blocked) return await bail(r.blocked)
  sm.push(k + "[" + r.status + "] " + r.artifact)
}
return { status: dg ? "degraded" : "ok", statePath: IM + "/state.json", artifactSummary: sm.join("；"), ledgerTail: await ledgerTail() }
