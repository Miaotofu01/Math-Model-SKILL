// test/dryrun-shell.mjs —— 薄壳干跑（无 LLM、无 fs 权限）：用桩 agent 验证路由/门禁/收敛/resume
// 用法：node test/dryrun-shell.mjs [--resume] [--problem <00-problem.json 路径>] [--mode quick]
// 原理：把 workflows/math-model.js 正文包进 AsyncFunction，注入桩 agent/parallel/phase/log/args。
// 目的：改壳后不必真跑一次 run 就能确认「boot → 阶段序列 → 门禁 → 降级 → 返回」不破。

import { readFileSync, existsSync } from "node:fs"
import { resolve, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const HERE = dirname(fileURLToPath(import.meta.url))
const SKILL = resolve(HERE, "../skills/math-model")
const argv = process.argv.slice(2)
const RESUME = argv.includes("--resume") || argv.includes("--resume-mismatch")
const MISMATCH = argv.includes("--resume-mismatch")   // state.json problemId 失配 → 必须拒绝覆盖
const MODE = argv.includes("--mode") ? argv[argv.indexOf("--mode") + 1] : "full"
const FIXTURE_MANIFESTS = !!process.env.FIXTURE_MANIFESTS   // 注入三份 manifest 夹具 → 验证「已登记」分支（F1）
const BOOT_STUB = process.env.BOOT_STUB || "summary"        // summary=新契约（只取字段）｜full=旧全量回吐｜broken=摘要失败→走 a2 回退
const FAIL_STAGES = (process.env.FAIL_STAGES || "").split(",").filter(Boolean)   // 例：FAIL_STAGES=run:q1.robustness → 触发降级路径断言
const REVIEW_STATUS = process.env.REVIEW_STATUS || "PASS"   // REVIEW_STATUS=NEEDS_REVISION → 走「修订→轮次用尽收束→二次尝试→blocked」路径
const FULL_STAGES = 23   // 夹具 2 小问：10×2 + 3 个 run 级（formulation 计入 formulator）

const FIXTURE = resolve(HERE, "intermediates")
const OUT = "math-model-output"
const IM = OUT + "/intermediates"
const PD = SKILL + "/prompts"

const calls = []
let agentSeen = 0
const stateRaw = existsSync(resolve(FIXTURE, "state.json")) ? readFileSync(resolve(FIXTURE, "state.json"), "utf8") : null
const files = {
  [`${IM}/00-problem.json`]: readFileSync(resolve(FIXTURE, "00-problem.json"), "utf8"),
  [`${IM}/state.json`]: MISMATCH && stateRaw ? stateRaw.replace(/"problemId":\s*"[^"]*"/, '"problemId": "ZZZ"') : stateRaw,
}
if (FIXTURE_MANIFESTS) {   // 三份清单：原语 2 项 / 题专用核心 2 项 / 探针 1 条
  // 清单只在 resume 时随 boot 读 → 夹具用 resume + 空 gates（全部阶段照跑），以便覆盖「已登记」分支
  files[`${OUT}/pool/manifest.json`] = JSON.stringify({ primitivesVersion: "1.0.0", selftest: { passed: true }, entries: { point_segment_distance: {}, bisect_boundary: {} } })
  files[`${OUT}/pool/problem/manifest.json`] = JSON.stringify({ entries: { "core.occlusion": {}, "core.greedy": {} } })
  files[`${OUT}/probes/manifest.json`] = JSON.stringify({ probes: { "adversary/perturb": {} } })
  files[`${IM}/state.json`] = JSON.stringify({ schema: "v1", problemId: "A", current: {}, iterations: {}, gates: {}, artifacts: {}, deps: {} })
}
// boot 摘要桩：模拟新契约（只取字段、不回吐正文）
const summarize = (w, txt) => {
  if (BOOT_STUB === "full") return txt                       // 旧行为（必须仍然可用）
  if (BOOT_STUB === "broken") return undefined                 // 触发壳的 a2 回退（见下方整包替换为截断 JSON）
  try {
    const o = JSON.parse(txt)
    if (/00-problem\.json$/.test(w)) {
      const a = (o.problem && o.problem.analysis) || o.analysis || {}
      const sq = Array.isArray(a.subQuestions) ? a.subQuestions : []
      const qs = Array.isArray(o.questions) && o.questions.length
        ? o.questions.map(String)
        : sq.map(x => String(x && (x.id ?? x.questionId ?? x.number)))
      return { problemId: String(o.problemId || o.selectedProblem || (o.problem && o.problem.id) || "unknown"), questions: qs }
    }
    if (/state\.json$/.test(w)) return { problemId: o.problemId, gates: o.gates || {}, iterations: o.iterations || {} }
    if (/manifest\.json$/.test(w)) {
      const ks = o.entries && typeof o.entries === "object" ? Object.keys(o.entries)
        : (o.probes && typeof o.probes === "object" ? Object.keys(o.probes) : [])
      return { keys: ks.slice(0, 12), count: ks.length, primitivesVersion: o.primitivesVersion ?? null,
               selftestPassed: o.selftest && typeof o.selftest.passed === "boolean" ? o.selftest.passed : null }
    }
  } catch (e) { /* 落到 NOT_FOUND */ }
  return "NOT_FOUND"
}
const RESUME_GATES = stateRaw ? Object.entries(JSON.parse(stateRaw).gates || {}).filter(([, v]) => ["PASS", "PASS_WITH_WARNING", "SKIPPED"].includes(v)).map(([k]) => k) : []

// 桩：按 label 返回契约要求的形状；同时校验壳注入的提示词是否含公共纪律与技能根
const AGENTS = {
  contracts: () => JSON.stringify({
    manifest: readFileSync(PD + "/stage-manifest.json", "utf8"),
    responseSchema: readFileSync(PD + "/response-schema.json", "utf8"),
  }),
  "read-many": (p) => {
    // 路径清单在「以下全部文件…:」与「输出 JSON 对象…」之间（BOOT_SPEC 里也有 "- " 开头的说明行，不能直接扫全文）
    const seg = p.split("一次并列 Read 以下全部文件（不遗漏、不逐个读）:")[1] || ""
    const want = [...(seg.split("输出 JSON 对象")[0]).matchAll(/- (.+)/g)].map(m => m[1].trim())
    if (BOOT_STUB === "broken") return '{"math-model-output/intermediates/00-problem.json": "{\"selectedProblem\": \"A\", \"prob'  // 截断（read 工具硬限的真实签名）
    const o = {}
    for (const w of want) o[w] = files[w] === undefined ? "NOT_FOUND" : summarize(w, files[w])
    return JSON.stringify(o)
  },
}
async function agent(prompt, opts = {}) {
  agentSeen++
  const label = opts.label || "mm"
  calls.push(label)
  const out = await stub(prompt, opts, label)
  // 真实运行时：给了 schema 的调用返回**已验证对象**，其余返回文本
  return opts.schema ? JSON.parse(out) : out
}
const stubPrompts = []
async function stub(prompt, opts, label) {
  stubPrompts.push(prompt)
  if (label === "mm") {                       // rf(): 形如 `Read <path>; 存在输出内容，否则 "NOT_FOUND"。`
    const m = prompt.match(/^Read (.+?);/)
    return m && files[m[1]] ? files[m[1]] : "NOT_FOUND"
  }
  if (AGENTS[label]) return AGENTS[label](prompt)
  if (label === "env") { files[`${IM}/env-report.json`] = JSON.stringify({ problemId: "A", python: "/usr/bin/python3", fallback: false, libs: {} }); return JSON.stringify({ status: "PASS", artifact_path: `${IM}/env-report.json`, summary: "stub env" }) }
  if (label === "init") { files[`${IM}/state.json`] = JSON.stringify({ schema: "v1", problemId: "A", current: {}, iterations: {}, gates: {}, artifacts: {}, deps: {} }); return JSON.stringify({ status: "PASS", artifact_path: `${IM}/state.json`, summary: "init" }) }
  if (label.startsWith("gate:")) {
    if (!prompt.includes(label.slice(5) + ": <PASS|FAIL>")) throw new Error("门禁提示词未给出固定 ledger 键: " + label)
    return JSON.stringify({ status: "PASS", artifact_path: "", summary: "gate ok" })
  }
  if (label.startsWith("review:")) {
    // 校验：评审提示词必须并列读入 _common.md 与视角模板，且带可复用资产清单（§1.3-4）
    if (!prompt.includes("_common.md")) throw new Error("评审提示词未注入 _common.md")
    if (!prompt.includes("可复用资产")) throw new Error("评审提示词未注入可复用资产清单")
    return JSON.stringify({ status: REVIEW_STATUS, artifact_path: "x/review.md", summary: "stub review" })
  }
  if (label === "formulator" || label === "selfcheck" || label === "finalize" || label === "revise") {
    if (label === "formulator") {   // 公式化入口 agent 拿的是 stagePrompt：依赖须为「假设目录」，不得硬编码 assumption-v01（v01 可能是被自检拒绝的版本）
      if (!/依赖 [^\n]*intermediates\/q\d+\/03-assumptions\//.test(prompt)) throw new Error("formulation 依赖未渲染为假设目录")
      if (prompt.includes("assumption-v01")) throw new Error("formulation 依赖仍硬编码 assumption-v01")
    }
    return JSON.stringify({ status: "PASS", artifact_path: "q/04-formulation/draft.md", summary: label })
  }
  if (label.startsWith("run:") || label.startsWith("degrade:")) {
    if (label.startsWith("run:") && !prompt.includes("_common.md")) throw new Error("阶段提示词未注入 _common.md: " + label)
    if (label.startsWith("run:") && !prompt.includes(SKILL)) throw new Error("阶段提示词未注入技能根: " + label)
    if (label.startsWith("run:") && !prompt.includes("可复用资产")) throw new Error("阶段提示词未注入可复用资产清单: " + label)
    if (label.startsWith("run:") && !prompt.includes("pool/problem/manifest.json")) throw new Error("阶段提示词未列可复用资产清单路径: " + label)
    // deps 渲染两分支：非 {id} 路径补 intermediates/ 前缀；{id} 路径替换为当前小问
    if (label === "run:q1.literature" && !prompt.includes(`依赖 ${IM}/00-problem.json`)) throw new Error("阶段提示词依赖未渲染为完整路径: " + label)
    if (label === "run:q1.literature" && !prompt.includes("q1.literature: <status>")) throw new Error("阶段提示词未给出固定 ledger 键: " + label)
    if (label === "run:q1.data" && !prompt.includes(`${IM}/q1/01-literature/literature.md`)) throw new Error("阶段提示词 {id} 依赖未替换: " + label)
    if (label.startsWith("run:") && FAIL_STAGES.includes(label)) return JSON.stringify({ status: "FAIL", artifact_path: "", summary: "stub fail" })
    return JSON.stringify({ status: "PASS", artifact_path: "stub/out.md", summary: label })
  }
  return JSON.stringify({ status: "PASS", artifact_path: "stub", summary: label })
}
const parallel = async (thunks) => Promise.all(thunks.map(t => t()))
const phaseLog = []
const phase = (t) => phaseLog.push(t)
const log = (m) => phaseLog.push("log: " + m)

const body = readFileSync(SKILL + "/workflows/math-model.js", "utf8")
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor
const run = new AsyncFunction("agent", "parallel", "phase", "log", "args", body)

const result = await run(agent, parallel, phase, log, {
  outputDir: OUT, templateDir: SKILL, mode: MODE, innovationStrictness: "strict", resume: RESUME || FIXTURE_MANIFESTS,
})

// ── 断言 ──
const fails = []
const NEG = REVIEW_STATUS !== "PASS"   // 三视角全 NEEDS_REVISION → 走修订 + 轮次用尽收束 + 二次尝试 + blocked
const stages = calls.filter(c => c.startsWith("run:") || c === "formulator")
if ("blocked" in result && !NEG) fails.push("被阻塞：" + JSON.stringify(result.blocked))
if (!RESUME && !NEG) {
  if (result.status === "error") fails.push("壳返回 error：" + JSON.stringify(result))
  if (stages.length === 0) fails.push("没有任何阶段被调度")
  for (const need of ["q1.literature", "q2.localComplete", "crossReview", "writing", "finalReview"]) {
    if (!calls.includes("run:" + need)) fails.push("缺少阶段调用：" + need)
  }
}
if (MISMATCH) {
  if (result.status !== "error") fails.push("problemId 失配时未拒绝（应返回 error，避免覆盖 state.json）")
  else console.log("✓ 失配保护生效：" + result.ledgerTail)
} else if (RESUME) {
  if (RESUME_GATES.length && stages.length >= FULL_STAGES) fails.push("resume 未跳过已完成阶段（仍调度 " + stages.length + " / " + FULL_STAGES + "）")
  const skipped = (result.artifactSummary || "").split("；").filter(x => x.includes("RESUMED")).length
  console.log("✓ resume 跳过 " + skipped + " 个已 PASS 阶段，实调 " + stages.length + " 个（state.gates 已完成 " + RESUME_GATES.length + " 项）")
} else if (!RESUME && !NEG && stages.length !== FULL_STAGES + FAIL_STAGES.length) {   // 失败阶段重试一次 → 多一个 run: 调用
  fails.push("阶段数不符：期望 " + (FULL_STAGES + FAIL_STAGES.length) + "，实得 " + stages.length)
}
if (NEG) {   // 修订 + 轮次用尽收束路径
  if (!("blocked" in result)) fails.push("三视角全 NEEDS_REVISION 时未按 blocked 收束")
  const ri = calls.indexOf("revise")
  if (ri < 0) fails.push("修订节点未被调度")
  else if (!stubPrompts[ri].includes("q1.formulation.revision-r1")) fails.push("修订提示词未给出固定 ledger 键")
  const lastF = stubPrompts[calls.lastIndexOf("finalize")]
  if (!lastF.includes("结论 = NEEDS_REVISION")) fails.push("收束提示词未带出 NEEDS_REVISION 结论")
  if (!lastF.includes(`gates["q1.formulation"]="NEEDS_REVISION"`)) fails.push("收束提示词未写明 NEEDS_REVISION 值")
}

if (process.env.DUMP_PROMPT) {           // 调试：DUMP_PROMPT=1 → 首个阶段提示词；DUMP_PROMPT=finalize|degrade:q1.robustness → 打印匹配 label 的提示词
  const sel = process.env.DUMP_PROMPT
  const idxs = sel === "1" ? [calls.findIndex(c => c.startsWith("run:"))] : calls.map((c, i) => (c.includes(sel) ? i : -1)).filter(i => i >= 0)
  for (const i of idxs) console.log(`── ${calls[i]} ──\n${stubPrompts[i]}\n────────────────`)
}
// 专职状态节点提示词断言：必须自述职责、给全路径、用 schema 真字段名与注入值（resume/mismatch 不跑这些节点）
if (!RESUME) {
const fi = calls.indexOf("finalize")
if (fi < 0) fails.push("收束节点未被调度")
else {
  const fp = stubPrompts[fi]
  if (!/收束 q1\.formulation/.test(fp) || !fp.includes("唯一职责")) fails.push("收束提示词未自述职责")
  if (!fp.includes(`iterations["q1.formulation"]`)) fails.push("收束提示词未用 schema 字段名 iterations")
  if (/\biter\[/.test(fp)) fails.push("收束提示词仍在写不存在的 iter 字段")
  if (!fp.includes(`${IM}/state.json`) || !fp.includes(`${IM}/ledger.md`) || !fp.includes("state-schema.md")) fails.push("收束提示词未给出 state/ledger/schema 路径")
  if (!fp.includes(`gates["q1.formulation"]="${NEG ? "NEEDS_REVISION" : "PASS"}"`)) fails.push("收束提示词未写明 gates 键与注入值")
  if (!fp.includes("q1.formulation.finalize")) fails.push("收束提示词未给出固定 ledger 键")
}
// 阶段/评审模板的边界口径（静态）：draft 只覆盖本小问、假设只认最新版、评审不要求跨问展开
const p04 = readFileSync(PD + "/phase-04-formulation.md", "utf8")
if (!p04.includes("只做本小问")) fails.push("phase-04 未声明「只做本小问」边界")
if (!p04.includes("禁止据旧版建模")) fails.push("phase-04 未写明假设只认最新版")
const pj = readFileSync(PD + "/formulation-reviewer-judge.md", "utf8")
if (!pj.includes("本小问全覆盖") || pj.includes("对照 00-problem.json 的小问清单，每个子问题")) fails.push("judge 评审仍要求单问 draft 覆盖全部小问")
// 读入负担治理：7（draft 篇幅预算 + 台账归属）、1（读入范围）、2（评审文件瘦身）
for (const f of ["revision-log.md", "verification.md", "handoff.md", "errata.md"]) if (!p04.includes(f)) fails.push("phase-04 产物表缺 " + f)
if (p04.includes("≤12k 字符")) fails.push("phase-04 仍在用实测不成立的 12k 硬预算")
if (!p04.includes("台账章节零容差") || !p04.includes("60k")) fails.push("phase-04 未写明台账零容差 + 60k 软阈值")
if (!p04.includes("draft.ledger_section")) fails.push("phase-04 未把机械检查项写进完成标准")
const pc = readFileSync(PD + "/_common.md", "utf8")
if (!pc.includes("必须整体读") || !pc.includes("20KB")) fails.push("_common §3 未写明读入范围（评审对象整体读 / 参考件 >20KB 局部读）")
for (const r of ["formulation-reviewer-judge.md", "formulation-reviewer-adversary.md", "formulation-reviewer-application.md"]) {
  const rt = readFileSync(PD + "/" + r, "utf8")
  if (!rt.includes("产物体量与读入范围") || !rt.includes("可机械复核三件套")) fails.push(r + " 未写明评审文件瘦身与读入范围")
  if (!rt.includes("revision-log.md")) fails.push(r + " 未指向 revision-log.md（处置表已移出 draft）")
}
const p12 = readFileSync(PD + "/phase-12-writing.md", "utf8")
for (const s of ["q{id}/07-sanity/", "q{id}/09-robustness/", "q{id}/02-data/eda.md", "q{id}/01-literature/lit-verify.md"]) {
  if (!p12.includes(s)) fails.push("phase-12 §输入 缺前缀：" + s)
}
const manStatic = JSON.parse(readFileSync(PD + "/stage-manifest.json", "utf8"))
// A 批（信息流 + 真缺陷）：deps 补齐 / 自依赖删除 / 评审与自查读入 / 模板纠错
if (!(manStatic.deps.literature || []).some(d => d.includes("literature-pool.md"))) fails.push("deps.literature 缺 pool/literature-pool.md")
for (const [s, want] of [["implementation", ["00-problem.json", "baseline-registry.md", "symbols.json", "handoff.md"]],
                         ["computation", ["baseline-registry.md", "symbols.json", "errata.md"]],
                         ["sanity", ["00-problem.json", "symbols.json", "verification.md", "errata.md"]],
                         ["visualization", ["00-problem.json", "symbols.json"]],
                         ["robustness", ["00-problem.json"]]]) {
  for (const d of want) if (!(manStatic.deps[s] || []).some(x => x.includes(d))) fails.push("deps." + s + " 缺 " + d)
}
if ((manStatic.deps.computation || []).some(x => x.includes("06-computation/results.json"))) fails.push("deps.computation 仍含自身产物 results.json")
if (!body.includes("baseline-registry.md、${d}/symbols.json")) fails.push("评审并列读未补 baseline-registry/symbols")
if (!body.includes("一次并列 Read ${PD}/_common.md 与 ${dr}（公共纪律")) fails.push("自查节点未注入 _common.md")
const p03 = readFileSync(PD + "/phase-03-assumption.md", "utf8")
if (!p03.includes('artifacts["q{id}.assumption"]')) fails.push("phase-03 未规定 artifacts 键")
const p13 = readFileSync(PD + "/phase-13-finalReview.md", "utf8")
if (p13.includes("/tmp/refs.tex") || !p13.includes("intermediates/13-final/refs.tex")) fails.push("phase-13 组装仍读 /tmp/refs.tex")
const p10 = readFileSync(PD + "/phase-10-localComplete.md", "utf8")
if (!p10.includes("revision-log.md") || !p10.includes("handoff.md")) fails.push("phase-10 门禁未核 revision-log/handoff")
const p05 = readFileSync(PD + "/phase-05-implementation.md", "utf8")
if (/阶段指令首行 `## Python 环境`/.test(p05)) fails.push("phase-05 仍写「首行」Python 环境行")
for (const f of ["phase-11-crossReview.md", "phase-12-writing.md", "phase-13-finalReview.md"]) {
  if (!readFileSync(PD + "/" + f, "utf8").includes("errata.md")) fails.push(f + " §输入 未接 errata（孤儿台账）")
}
for (const s of ["implementation", "computation", "sanity", "robustness"]) {
  if (!(manStatic.deps[s] || []).some(d => d.includes("handoff.md"))) fails.push("deps." + s + " 未含 handoff.md（台账移出 draft 后须显式依赖）")
}
for (const fs0 of FAIL_STAGES) {
  const k = fs0.replace(/^run:/, ""), di = calls.indexOf("degrade:" + k)
  if (di < 0) { fails.push("降级节点未被调度：" + k); continue }
  const dp = stubPrompts[di]
  if (!/降级 /.test(dp) || !dp.includes("唯一职责")) fails.push("降级提示词未自述职责：" + k)
  if (!dp.includes(`${IM}/state.json`) || !dp.includes("state-schema.md")) fails.push("降级提示词未给出 state/schema 路径：" + k)
  if (!dp.includes(`gates["${k}"]="SKIPPED"`)) fails.push("降级提示词未写明 gates 键与值：" + k)
  if (!dp.includes("**不写** iterations/artifacts")) fails.push("降级提示词未禁写 iterations/artifacts：" + k)
}
// 核验成本纪律（第一批）：doc §6.1 + 06/07 判据 + 壳字面注入 + 脚本机械锚点
const perfDoc = readFileSync(SKILL + "/docs/performance.md", "utf8")
for (const s of ["6.1 嵌套核验的成本纪律", "先估后跑", "8× 同场生产主体墙钟", "checkpoint_put", "缩窗 → 减档 → 降精度"]) {
  if (!perfDoc.includes(s)) fails.push("performance.md §6.1 缺：" + s)
}
const p06 = readFileSync(PD + "/phase-06-computation.md", "utf8")
for (const s of ["先估后跑", "costEstimate_s", "checkpoint_put"]) {
  if (!p06.includes(s)) fails.push("phase-06 未写明核验成本纪律：" + s)
}
const p07 = readFileSync(PD + "/phase-07-sanity.md", "utf8")
if (!p07.includes("costEstimate_s") || !p07.includes("8×")) fails.push("phase-07 未把核验成本账列入核查")
if (!pc.includes("成本纪律（所有探针")) fails.push("_common §5.2 未加探针成本纪律")
const wf = readFileSync(SKILL + "/workflows/math-model.js", "utf8")
if (!wf.includes("COSTLINE") || !wf.includes("--budget")) fails.push("壳未字面注入核验成本纪律")
const pcsrc = readFileSync(SKILL + "/scripts/probe_cache.py", "utf8")
if (!pcsrc.includes("BudgetExceeded") || !pcsrc.includes("def checkpoint_put")) fails.push("probe_cache 缺预算预检/分档落盘")
const bootPrompt = stubPrompts.find(x => x.includes("一次并列 Read 以下全部文件")) || ""
if (!bootPrompt.includes("禁止回吐文件正文")) fails.push("boot 提示词未写明「只取字段、禁止回吐正文」")
if (!bootPrompt.includes("NOT_FOUND")) fails.push("boot 提示词未给出 NOT_FOUND 语义")
if (BOOT_STUB === "broken" && !phaseLog.some(x => x.includes("回退全量读"))) fails.push("摘要失败时未走 a2 回退")
const anyStage = stubPrompts.find(x => x.includes("## 阶段 q1.")) || ""
if (!anyStage.includes("每轮必读")) fails.push("阶段提示词未声明模板每轮必读")
const ri = calls.indexOf("revise")
if (ri >= 0) {
  const rp = stubPrompts[ri]
  if (!rp.includes("精准手术")) fails.push("修订提示词未要求精准手术（禁整篇重写）")
  if (!rp.includes("revision-log.md")) fails.push("修订提示词未把处置表落到 revision-log.md")
}
if (!wf.includes("精准手术")) fails.push("壳未注入精准手术约束")
const ci = calls.indexOf("run:q1.computation")   // REVIEW_STATUS=NEEDS_REVISION 模式在 solve-start 前就 blocked，故仅调度到时断言
if (ci >= 0 && (!stubPrompts[ci].includes("核验成本纪律") || !stubPrompts[ci].includes("--budget"))) {
  fails.push("06 阶段提示词未字面注入核验成本纪律（防散文漂移）")
}
}
console.log("阶段调用序列（" + stages.length + "）：")
console.log("  " + stages.join("\n  "))
console.log("\n门禁/日志：")
console.log("  " + phaseLog.filter(x => x.startsWith("gate:") || x.startsWith("log:")).join("\n  "))
// 资产清单口径断言（F1）：缺 manifest → 「启动快照未见…登记」；FIXTURE_MANIFESTS=1 注入三份清单 → 列出条目/版本/selftest
if (!RESUME) {
  const all = stubPrompts.join("\n")
  if (FIXTURE_MANIFESTS) {
    if (!all.includes("题专用核心池 pool/problem/ 已登记 2 项")) fails.push("资产清单未列出题专用核心条目")
    if (!all.includes("原语池 pool/primitives.py 已登记 2 项") || !all.includes("selftest 通过")) fails.push("资产清单未列出原语条目/版本/selftest")
    if (!all.includes("探针池 probes/ 已登记 1 条")) fails.push("资产清单未列出探针条目")
    if (all.includes("启动快照未见原语登记")) fails.push("注入 manifest 后仍报未见原语登记")
  } else if (!all.includes("启动快照未见原语登记")) {
    fails.push("资产清单未按缺 manifest 情形给出提示")
  }
  if (!all.includes("以文件为准")) fails.push("阶段提示词未声明以清单文件为权威")
}
console.log("\n总 agent 调用：" + agentSeen)
console.log("返回：" + JSON.stringify({ ...result, artifactSummary: (result.artifactSummary || "").slice(0, 120) + "…" }))
if (fails.length) { console.log("\n✗ 断言失败：\n  - " + fails.join("\n  - ")); process.exit(1) }
console.log("\n✓ 干跑通过（路由/门禁/收敛/桩注入断言全过）")
