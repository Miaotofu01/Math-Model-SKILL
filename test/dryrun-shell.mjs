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
const RESUME_GATES = stateRaw ? Object.entries(JSON.parse(stateRaw).gates || {}).filter(([, v]) => ["PASS", "PASS_WITH_WARNING", "SKIPPED"].includes(v)).map(([k]) => k) : []

// 桩：按 label 返回契约要求的形状；同时校验壳注入的提示词是否含公共纪律与技能根
const AGENTS = {
  contracts: () => JSON.stringify({
    manifest: readFileSync(PD + "/stage-manifest.json", "utf8"),
    responseSchema: readFileSync(PD + "/response-schema.json", "utf8"),
  }),
  "read-many": (p) => {
    const want = [...p.matchAll(/- (.+)/g)].map(m => m[1].trim())
    const o = {}
    for (const w of want) o[w] = files[w] ?? "NOT_FOUND"
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
  if (label.startsWith("gate:")) return JSON.stringify({ status: "PASS", artifact_path: "", summary: "gate ok" })
  if (label.startsWith("review:")) {
    // 校验：评审提示词必须并列读入 _common.md 与视角模板，且带可复用资产清单（§1.3-4）
    if (!prompt.includes("_common.md")) throw new Error("评审提示词未注入 _common.md")
    if (!prompt.includes("可复用资产")) throw new Error("评审提示词未注入可复用资产清单")
    return JSON.stringify({ status: "PASS", artifact_path: "x/review.md", summary: "no must-fix" })
  }
  if (label === "formulator" || label === "selfcheck" || label === "finalize" || label === "revise") {
    return JSON.stringify({ status: "PASS", artifact_path: "q/04-formulation/draft.md", summary: label })
  }
  if (label.startsWith("run:") || label.startsWith("degrade:")) {
    if (label.startsWith("run:") && !prompt.includes("_common.md")) throw new Error("阶段提示词未注入 _common.md: " + label)
    if (label.startsWith("run:") && !prompt.includes(SKILL)) throw new Error("阶段提示词未注入技能根: " + label)
    if (label.startsWith("run:") && !prompt.includes("可复用资产")) throw new Error("阶段提示词未注入可复用资产清单: " + label)
    if (label.startsWith("run:") && !prompt.includes("pool/problem/manifest.json")) throw new Error("阶段提示词未列可复用资产清单路径: " + label)
    // deps 渲染两分支：非 {id} 路径补 intermediates/ 前缀；{id} 路径替换为当前小问
    if (label === "run:q1.literature" && !prompt.includes(`依赖 ${IM}/00-problem.json`)) throw new Error("阶段提示词依赖未渲染为完整路径: " + label)
    if (label === "run:q1.data" && !prompt.includes(`${IM}/q1/01-literature/literature.md`)) throw new Error("阶段提示词 {id} 依赖未替换: " + label)
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
const stages = calls.filter(c => c.startsWith("run:") || c === "formulator")
if ("blocked" in result) fails.push("被阻塞：" + JSON.stringify(result.blocked))
if (!RESUME) {
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
} else if (stages.length !== FULL_STAGES) {
  fails.push("阶段数不符：期望 " + FULL_STAGES + "，实得 " + stages.length)
}

if (process.env.DUMP_PROMPT) {           // 调试：DUMP_PROMPT=1 node test/dryrun-shell.mjs → 打印首个阶段提示词
  const i = calls.findIndex(c => c.startsWith("run:"))
  console.log("── 首个阶段提示词 ──\n" + stubPrompts[i] + "\n────────────────")
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
