export const meta = {
  name: 'math-model',
  description: '数学建模国赛全流程: 审题→选题→文献(局限分析)→建模(Gap驱动创新+4人评审⇄修订loop)→求解(baseline对比)⇄验证→写作(叙事大纲+交叉审查)→终审(摘要数字溯源+评委自评+LaTeX)。国一导向：正确性第一、数据说话、摘要定生死。',
  whenToUse: '用户需要完成数学建模竞赛（国赛/美赛）的完整流程时。支持三种模式：quick（模拟训练）、standard（正常比赛含baseline）、thorough（冲奖全开）。',
  phases: [
    { title: '审题', detail: '并行阅读所有题目，提取结构化信息' },
    { title: '选题', detail: '综合对比，推荐最优题目' },
    { title: '文献调研', detail: '多角度搜索 + 精读 + 局限分析' },
    { title: '建模方案', detail: 'Gap分析(含方向筛选) → 3角度创新提案 → 综合 → 4人评审团 ⇄ 修订(max 6轮)' },
    { title: '求解', detail: '算法设计 → 代码实现 → baseline对比 → 迭代修复' },
    { title: '验证', detail: '灵敏度 + 边界 + 对抗 + 数据验证' },
    { title: '写作', detail: '叙事大纲 → 并行撰写 → 交叉一致性检查' },
    { title: '终审', detail: '摘要3轮打磨 + 一致性检查 + 评委自评 + LaTeX编译' },
  ],
}

// ═══ Strategy config — mode determines factors/switches ═══
const MODES = {
  quick: {
    searchAngles: 2, maxFetch: 4,
    votesPerClaim: 0, refutationsRequired: 0,
    dryThreshold: 1, maxIterations: 2,
    enableCodeReview: false,
    sectionPreset: "compact", finalReviewAgents: 1,
    latexOutput: false, latexMaxRetries: 0,
    enableBaseline: false, abstractRounds: 1, rethinkThreshold: 5,
    contextBudget: 30000,
  },
  standard: {
    searchAngles: 3, maxFetch: 6,
    votesPerClaim: 3, refutationsRequired: 2,
    dryThreshold: 2, maxIterations: 4,
    enableCodeReview: false,
    sectionPreset: "standard", finalReviewAgents: 2,
    latexOutput: true, latexMaxRetries: 2,
    enableBaseline: true, abstractRounds: 2, rethinkThreshold: 3,
    contextBudget: 60000,
  },
  thorough: {
    searchAngles: 4, maxFetch: 8,
    votesPerClaim: 5, refutationsRequired: 3,
    dryThreshold: 3, maxIterations: 6,
    enableCodeReview: true,
    sectionPreset: "full", finalReviewAgents: 3,
    latexOutput: true, latexMaxRetries: 5,
    enableBaseline: true, abstractRounds: 2, rethinkThreshold: 3,
    contextBudget: 100000,
  },
}

// ═══ CUMC 内建论文格式规范（始终生效，与题目包中 paperRules 互补） ═══
// 2025 修订稿核心要求。paperRules 中可能包含的题目特定格式要求会追加在内建规则之后。
const CUMC_PAPER_RULES = `## ⚠️ 全国大学生数学建模竞赛论文格式规范（内建，始终生效）

### 电子版结构
- **第一页必须为摘要专用页**（含标题+摘要+关键词），不得出现承诺书和编号专用页
- 正文紧接摘要之后，**不要目录**
- 正文尽量控制在 **20 页以内**
- 正文之后为**附录**：必须包含支撑材料清单 + 建模所用全部完整可运行的源程序代码

### 页面格式
- A4 纸，上下左右 ≥ 2.5cm 页边距
- 页码从摘要页开始，阿拉伯数字从 "1" 连续编号，位于页脚**中部**

### 内容红线
- 摘要页、正文、附录任何地方**不得有参赛者身份、学校、赛区信息**
- 所有引用他人或公开资料的成果必须按科技论文规范列出参考文献，并在正文引用处标注
- **附录必须包含全部完整可运行的源程序代码**（含 Excel、SPSS 等交互命令）。缺少源程序或程序不能运行 → 可能被取消评奖资格。确实没有用到程序时需在附录中明确说明`

// ═══ Domain expertise lookup ═══
const DOMAIN_EXPERTISE = [
  { keywords: ["弹道", "轨道", "拦截", "制导"], expertise: "弹道学与军事运筹学专家，关注拦截几何和物理合理性。" },
  { keywords: ["流体", "CFD", "湍流", "空气动力学"], expertise: "流体力学专家，关注方程数值稳定性和边界条件。" },
  { keywords: ["统计", "回归", "假设检验"], expertise: "统计学家，关注假设检验、置信区间和过拟合。" },
  { keywords: ["图论", "网络", "路径", "拓扑"], expertise: "图论与网络优化专家，关注算法复杂度和最优性证明。" },
  { keywords: ["机器学习", "深度学习", "神经网络", "分类", "预测"], expertise: "ML研究员，关注特征工程和模型可解释性。" },
  { keywords: ["生物力学", "运动学", "力学"], expertise: "生物力学专家，关注运动学约束和力合理性。" },
  { keywords: ["优化", "规划", "调度"], expertise: "运筹学专家，关注目标函数设计和全局最优性。" },
]
const getDomainExpertise = (domain) => {
  if (!domain) return ""
  const match = DOMAIN_EXPERTISE.find(d => d.keywords.some(k => domain.includes(k)))
  return match ? "\n\n## 领域专家视角\n" + match.expertise : ""
}

// ═══ URL/label safety helpers (from deep-research) ═══
const URL_HOST_PATTERN = /^[a-z][a-z0-9+.-]*:\/\/(?:[^/?#\\]*@)?(?:www\.)?([^/:?#@\\]+)(?::\d+)?([^?#]*)/i
const normURL = u => {
  const m = String(u).match(URL_HOST_PATTERN)
  return m ? (m[1] + m[2].replace(/\/$/, "")).toLowerCase() : String(u).toLowerCase()
}
const LABEL_CAP = 40
const LABEL_STRIP = /[\x00-\x1f\x7f-\x9f​-‏‪-‮⁦-⁩﻿"“-‟″‶❝❞〝〞＂]/g
const STRICT_HOST = /^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$/
const stripLabelChars = s => String(s).replace(LABEL_STRIP, "")
const quotedLabel = s => {
  const cps = Array.from(stripLabelChars(s))
  return '"' + cps.slice(0, LABEL_CAP).join("").trim() + (cps.length > LABEL_CAP ? "…" : "") + '"'
}

// ═══ Intermediate output persistence ═══
const saveToFile = (label) =>  "\n\n**附加任务**: 将你的输出也保存到 `" + intermediatesDir + "/" + label + "`。" +
  "先用 `mkdir -p " + intermediatesDir + "` 创建目录，然后 `Write` 或 `Bash` 写入文件。保存失败不影响主流程（best-effort）。"

// ═══ Schemas ═══
const PROBLEM_ANALYSIS_SCHEMA = {
  type: "object", required: ["problemId", "domain", "objectives", "constraints", "mathType", "difficulty"],
  properties: {
    problemId: { type: "string" }, domain: { type: "string" }, background: { type: "string" },
    objectives: { type: "array", items: { type: "string" } },
    constraints: { type: "array", items: { type: "string" } },
    dataAvailable: { type: "string" },
    mathType: { type: "array", items: { enum: ["optimization", "differential_equation", "statistics", "graph_theory", "machine_learning", "simulation", "game_theory", "numerical_methods", "other"] } },
    difficulty: { enum: ["low", "medium", "high"] },
    keyChallenges: { type: "array", items: { type: "string" } },
  },
}

const SELECTION_SCHEMA = {
  type: "object", required: ["selected", "reason", "approachHint"],
  properties: {
    selected: { type: "string" }, reason: { type: "string" },
    fallback: { type: "string" }, approachHint: { type: "string" },
    riskAssessment: { type: "string" },
  },
}

const SEARCH_SCHEMA = {
  type: "object", required: ["results"],
  properties: { results: { type: "array", maxItems: 6, items: {
    type: "object", required: ["url", "title", "relevance"],
    properties: { url: { type: "string" }, title: { type: "string" }, snippet: { type: "string" }, relevance: { enum: ["high", "medium", "low"] } },
  }}},
}

const EXTRACT_SCHEMA = {
  type: "object", required: ["sourceQuality", "claims"],
  properties: {
    sourceQuality: { enum: ["primary", "secondary", "blog", "forum", "unreliable"] },
    publishDate: { type: "string" },
    models: { type: "array", items: { type: "object", required: ["name", "description"], properties: {
      name: { type: "string" }, description: { type: "string" },
      formulas: { type: "array", items: { type: "string" } },
      assumptions: { type: "array", items: { type: "string" } },
      applicability: { type: "string" },
    }}},
    claims: { type: "array", maxItems: 5, items: {
      type: "object", required: ["claim", "quote", "importance"],
      properties: { claim: { type: "string" }, quote: { type: "string" }, importance: { enum: ["central", "supporting", "tangential"] } },
    }},
  },
}

const MODEL_PROPOSAL_SCHEMA = {
  type: "object", required: ["approach", "assumptions", "equations", "solvingStrategy"],
  properties: {
    approach: { type: "string" },
    assumptions: { type: "array", items: { type: "string" } },
    notation: { type: "array", items: { type: "object", required: ["symbol", "meaning"], properties: { symbol: { type: "string" }, meaning: { type: "string" }, unit: { type: "string" } } } },
    equations: { type: "array", items: { type: "string" } },
    solvingStrategy: { type: "string" },
    pros: { type: "array", items: { type: "string" } },
    cons: { type: "array", items: { type: "string" } },
    expectedComplexity: { enum: ["low", "medium", "high"] },
  },
}

const VERDICT_SCHEMA = {
  type: "object", required: ["refuted", "evidence", "confidence"],
  properties: {
    refuted: { type: "boolean" }, evidence: { type: "string" },
    confidence: { enum: ["high", "medium", "low"] }, suggestion: { type: "string" },
  },
}

const SOLUTION_SCHEMA = {
  type: "object", required: ["algorithm", "code", "results"],
  properties: {
    algorithm: { type: "string" }, code: { type: "string" },
    results: { type: "object", properties: {
      summary: { type: "string" },
      keyValues: { type: "array", items: { type: "object", properties: { label: { type: "string" }, value: { type: "string" } } } },
      plots: { type: "array", items: { type: "string" } },
    }},
    testPassed: { type: "boolean" }, concerns: { type: "array", items: { type: "string" } },
  },
}

const VERIFICATION_SCHEMA = {
  type: "object", required: ["dimension", "findings"],
  properties: {
    dimension: { enum: ["sensitivity", "edge_cases", "adversarial", "data_validation", "devils_advocate"] },
    findings: { type: "array", items: { type: "object", required: ["issue", "severity"], properties: {
      issue: { type: "string" }, severity: { enum: ["critical", "moderate", "minor"] },
      evidence: { type: "string" }, fixSuggestion: { type: "string" },
    }}},
    modelRobustness: { enum: ["robust", "acceptable", "fragile"] },
  },
}

const PAPER_SECTION_SCHEMA = {
  type: "object", required: ["section", "content"],
  properties: {
    section: { type: "string" }, content: { type: "string" },
    keyPoints: { type: "array", items: { type: "string" } },
    formulas: { type: "array", items: { type: "string" } },
    references: { type: "array", items: { type: "string" } },
  },
}

const BASELINE_COMPARISON_SCHEMA = {
  type: "object", required: ["metrics", "summary", "significance"],
  properties: {
    metrics: { type: "array", items: { type: "object", properties: {
      name: { type: "string" }, baseline: { type: "string" }, improved: { type: "string" }, improvement: { type: "string" },
    }}},
    summary: { type: "string" },
    significance: { enum: ["high", "medium", "low", "marginal"] },
    weaknessExposed: { type: "string" },
  },
}

// ═══ Parse args — two modes: pre-selected problem (from skill) or full auto ═══
const hasArgs = typeof args === "object"
const MODE = (hasArgs && args?.mode && MODES[args.mode]) ? args.mode : "standard"
const cfg = MODES[MODE]
const outputDir = (hasArgs && args?.outputDir) || "/home/tofu/math-model-output"
const attachments = (hasArgs && args?.attachments) || []
const intermediatesDir = outputDir + "/intermediates"
const isPreSelected = !!(hasArgs && args?.selectedProblem)
const currentYear = 2026

log("模式: " + MODE + " | 输出: " + outputDir)
log("投票=" + (cfg.votesPerClaim > 0 ? cfg.votesPerClaim + "票/" + cfg.refutationsRequired + "否" : "关闭") + " | dry=" + cfg.dryThreshold + " | 最多" + cfg.maxIterations + "轮迭代")
log("baseline对比=" + (cfg.enableBaseline ? "开" : "关") + " | 摘要溯源=开")

// ── 输出目录结构（预创建所有子目录，best-effort）──
const ALL_DIRS = [
  outputDir + "/paper", outputDir + "/code", outputDir + "/figures",
  outputDir + "/data", outputDir + "/logs",
  intermediatesDir,
  intermediatesDir + "/05-writing", intermediatesDir + "/06-final",
]
try {
  await agent("创建所有输出目录: `mkdir -p " + ALL_DIRS.join(" ") + "`", { label: "mkdir-dirs", phase: "初始化" })
} catch (_) {}

// ═══════════════════════════════════════════
// Phase 1-2: 审题 + 选题 (skip if pre-selected)
// ═══════════════════════════════════════════

let chosenAnalysis, selection, analyses

if (isPreSelected) {
  // Pre-selected by skill — use the provided analysis directly
  phase("审题+选题")
  const presel = args
  chosenAnalysis = presel.problem?.analysis || {}
  if (!chosenAnalysis.domain || !chosenAnalysis.objectives) {
    return { error: "预选题目缺少分析数据——请提供 problem.analysis (含 domain, objectives 等字段)" }
  }
  chosenAnalysis.problemId = presel.selectedProblem
  // 保存阶段一传入的逐字原文和数据画像——阶段二各 Phase 需要用到
  chosenAnalysis._rawDescription = presel.problem?.description || ""
  chosenAnalysis._dataProfile = presel.problem?.dataProfile || ""
  chosenAnalysis._paperRules = presel.problem?.paperRules || ""
  selection = {
    selected: presel.selectedProblem,
    reason: "用户在阶段一中选定",
    fallback: null,
    approachHint: (chosenAnalysis.mathType || []).join(", "),
    riskAssessment: (chosenAnalysis.keyChallenges || []).join("; "),
  }
  analyses = [chosenAnalysis]
  log("使用阶段一审题结果: " + presel.selectedProblem + " — " + (chosenAnalysis.domain || ""))
} else {
  // Full auto: run Phase 1+2 inside workflow
  const problemsInput = typeof args === "string" ? args : (args?.problems || [])
  if (!problemsInput || (Array.isArray(problemsInput) && problemsInput.length === 0)) {
    return { error: "未提供题目。传入格式: /math-model <题目文本> 或 {mode, problems:[...]} 或 {mode, selectedProblem, problem:{id,description,analysis}}" }
  }
  const problems = Array.isArray(problemsInput)
    ? problemsInput
    : [{ id: "A", raw: problemsInput }]

  // Phase 1: 审题
  phase("审题")

  const ANALYZE_PROMPT = (p, i) =>
    "## 题目" + (p.id || ("#" + (i + 1))) + "\n\n" +
    (p.raw || p.description || JSON.stringify(p)) + "\n\n" +
    "## 任务\n" +
    "你是数学建模竞赛的审题专家。仔细阅读题目，提取结构化信息：\n" +
    "1. **domain**: 问题所属领域\n" +
    "2. **background**: 1-2句话总结背景\n" +
    "3. **objectives**: 要优化/预测/求解的具体目标\n" +
    "4. **constraints**: 所有约束条件（显式+隐式）\n" +
    "5. **dataAvailable**: 提供了什么数据？数据量和维度？\n" +
    "6. **mathType**: 可能涉及的数学类型（可多选）\n" +
    "7. **difficulty**: low/medium/high\n" +
    "8. **keyChallenges**: 预判的主要难点\n\nStructured output only."

  analyses = (await parallel(
    problems.map((p, i) => () =>
      agent(ANALYZE_PROMPT(p, i), {
        label: "审题:" + (p.id || ("#" + (i + 1))),
        schema: PROBLEM_ANALYSIS_SCHEMA,
      })
    )
  )).filter(Boolean)

  if (analyses.length === 0) {
    return { error: "审题阶段失败——所有 agent 均未返回结果。" }
  }
  log("审题完成: " + analyses.length + "/" + problems.length + " 道")

  // Phase 2: 选题
  phase("选题")

  selection = problems.length === 1
    ? {
        selected: problems[0].id || "A",
        reason: "仅一道题目",
        fallback: null,
        approachHint: (analyses[0]?.mathType || []).join(", "),
        riskAssessment: (analyses[0]?.keyChallenges || []).join("; "),
      }
    : await agent(
      "## 选题决策\n\n" +
      "你是数学建模竞赛教练。根据以下题目分析，帮助选择最优题目。\n\n" +
      "## 题目分析\n" + JSON.stringify(analyses, null, 2) + "\n\n" +
      "## 选题维度\n" +
      "1. **模型匹配度**: 是否有成熟的数学框架？\n" +
      "2. **数据优势**: 附件数据是否足够？\n" +
      "3. **求解可行性**: 算法复杂度可控？代码实现难度？\n" +
      "4. **创新空间**: 能否在标准解法外做出亮点？\n" +
      "5. **风险**: 是否有数据陷阱或模型坑？\n\n" +
      "推荐题目 + 理由 + 备选 + 方向提示 + 风险评估。\n\nStructured output only." + saveToFile("02-selection.json"),
      { label: "选题", schema: SELECTION_SCHEMA }
    )

  if (!selection) {
    return { error: "选题阶段失败。", analyses }
  }
  log("选定: " + selection.selected + " — " + (selection.reason || "").slice(0, 80))
}

// From here on, Phase 3-8 uses chosenAnalysis (set above)
chosenAnalysis = analyses.find(a => a.problemId === selection.selected) || analyses[0]

// ═══════════════════════════════════════════
// Phase 3: 文献调研 — search→fetch→limitation analysis
// ═══════════════════════════════════════════
phase("文献调研")

const SEARCH_ANGLES = [
  { label: "前沿学术", query: chosenAnalysis.domain + " recent advances mathematical model arxiv " + (currentYear - 1) + " " + currentYear, rationale: "前沿学术成果（arXiv/Google Scholar）" },
  { label: "海外方法", query: chosenAnalysis.domain + " " + (chosenAnalysis.objectives || []).slice(0, 2).join(" ") + " state-of-the-art methods review", rationale: "海外最新方法论（英文优先）" },
  { label: "中文核心", query: chosenAnalysis.domain + " " + (chosenAnalysis.mathType || []).join(" ") + " 数学建模 论文", rationale: "国内竞赛相关文献" },
  { label: "开源代码", query: (chosenAnalysis.mathType || ["optimization"])[0] + " modeling solution github python " + (currentYear - 2) + " " + currentYear, rationale: "可复现的代码实现" },
  { label: "数据方法", query: chosenAnalysis.domain + " parameter estimation sensitivity analysis validation methodology", rationale: "验证与数据处理方法" },
].slice(0, cfg.searchAngles)

const SEARCH_PROMPT = (angle) =>
  "## 文献搜索: " + angle.label + "\n\n" +
  "研究题目: " + selection.selected + " — " + chosenAnalysis.domain + "\n" +
  "目标: " + (chosenAnalysis.objectives || []).join("; ") + "\n\n" +
  "搜索角度: **" + angle.label + "** — " + angle.rationale + "\n" +
  "搜索词: `" + angle.query + "`\n\n" +
  "用 WebSearch 搜索（可优化搜索词），返回 4-6 条最相关结果。优先学术论文、技术博客、GitHub。跳过 SEO 垃圾。\n\nStructured output only." + saveToFile("03-search-" + angle.label.replace(/[^a-zA-Z一-龥]/g, "_") + ".json")

const seenUrls = new Map()
const relRank = { high: 0, medium: 1, low: 2 }
let fetchSlots = cfg.maxFetch

const searchResults = await pipeline(
  SEARCH_ANGLES,
  angle => agent(SEARCH_PROMPT(angle), {
    label: "search:" + angle.label, schema: SEARCH_SCHEMA,
  }).then(r => {
    if (!r) return null
    // 兼容 agent 直接返回数组的情况（schema validation 有时不强制）
    const resultsArr = Array.isArray(r) ? r : (r.results || [])
    log(angle.label + ": " + resultsArr.length + " 条")
    return { angle: angle.label, results: resultsArr }
  }),
  searchResult => {
    if (!searchResult) return []
    const results = Array.isArray(searchResult) ? searchResult : (searchResult.results || [])
    const sorted = [...results].sort((a, b) => relRank[a.relevance] - relRank[b.relevance])
    const novel = sorted.filter(r => {
      const key = normURL(r.url)
      if (seenUrls.has(key)) return false
      if (fetchSlots <= 0 && relRank[r.relevance] >= 1) return false
      seenUrls.set(key, { angle: searchResult.angle, title: r.title })
      fetchSlots--
      return true
    })
    return parallel(novel.map(source => () => {
      const capturedHost = String(source.url).match(URL_HOST_PATTERN)?.[1] ?? ""
      const host = capturedHost.toLowerCase()
      const cleanHost = stripLabelChars(host)
      const isClean = cleanHost === host && host !== "" && Array.from(host).length <= LABEL_CAP && STRICT_HOST.test(host)
      const hostLabel = cleanHost === "" ? "" : isClean ? host : quotedLabel(host)
      const sourceLabel = hostLabel || (stripLabelChars(source.title).trim() && quotedLabel(source.title)) || "unknown"
      return agent(
        "## 文献精读\n\n研究题目: " + selection.selected + "\n搜索角度: " + searchResult.angle + "\n\n" +
        "**URL:** " + source.url + "\n**标题:** " + source.title + "\n\n" +
        "## 任务\n" +
        "1. 用 WebFetch 获取页面内容\n" +
        "2. 评估来源质量: primary/secondary/blog/forum/unreliable\n" +
        "3. 提取 2-5 条与建模相关的 claim，附原文引用\n" +
        "4. 提取可复用的数学模型（公式、参数、算法、预处理方法）\n" +
        "5. 无法访问/付费墙/不相关 → claims:[], sourceQuality:'unreliable'\n\nStructured output only." + saveToFile("03-fetch-" + (sourceLabel || "unknown") + ".json"),
        { label: "fetch:" + sourceLabel, schema: EXTRACT_SCHEMA }
      ).then(ext => ext ? { ...ext, url: source.url, title: source.title, angle: searchResult.angle } : null)
        .catch(e => { log("fetch failed: " + source.url); return { url: source.url, title: source.title, angle: searchResult.angle, sourceQuality: "unreliable", claims: [], models: [] } })
    }))
  }
)

const allSources = searchResults.flat().filter(Boolean)
const allModels = allSources.flatMap(s => (s.models || []))
const allClaims = allSources.flatMap(s => (s.claims || []).map(c => ({ ...c, sourceUrl: s.url, sourceQuality: s.sourceQuality })))
log("文献: " + allSources.length + " 篇 → " + allModels.length + " 模型, " + allClaims.length + " 条关键信息")

// ── Phase 3.5: 标准解法局限分析 —— 创新的合法来源 ──
let limitationAnalysis = null
if (allModels.length > 0 || allClaims.length > 0) {
  limitationAnalysis = await agent(
    "## 标准解法局限分析\n\n" +
    (chosenAnalysis._rawDescription ? "## 题目原文（逐字引自赛题）\n" + chosenAnalysis._rawDescription + "\n\n" : "") +
    (chosenAnalysis._dataProfile ? "## 附件数据画像\n" + chosenAnalysis._dataProfile + "\n\n" : "") +
    "## 题目结构化分析\n" + JSON.stringify(chosenAnalysis, null, 2) + "\n\n" +
    "## 文献调研结果\n" + JSON.stringify({
      sources: allSources.length,
      models: allModels.slice(0, 10),
      claims: allClaims.slice(0, 12),
    }, null, 2) + "\n\n" +
    "## 任务\n" +
    "你是一位资深审稿人，专门找现有方法的局限性。创新必须有根有据，不能凭空编造——以下分析是后续建模方案的依据。\n\n" +
    "从以下角度逐一分析标准/主流方法的局限：\n" +
    "1. **假设过强**: 标准方法做了什么不现实的假设？放宽它会发生什么？\n" +
    "2. **精度瓶颈**: 标准方法在什么条件下精度不够？为什么？\n" +
    "3. **计算代价**: 有没有效率问题？高维/大规模时如何处理？\n" +
    "4. **泛化缺陷**: 标准方法在本题目特定约束下是否失效？哪里不匹配？\n" +
    "5. **方法冲突**: 不同文献给出的方法之间有没有矛盾？为什么？\n\n" +
    "每个局限按以下结构输出：「局限描述 → 为什么是问题 → 可能的改进方向」\n" +
    "输出纯文本，不需 JSON。不要泛泛而谈，要引用文献中的具体方法来支撑。" + saveToFile("03-limitation-analysis.txt"),
    { label: "limitation-analysis", phase: "文献调研" }
  )
  if (limitationAnalysis) {
    log("标准解法局限: " + (typeof limitationAnalysis === "string" ? limitationAnalysis.slice(0, 80).replace(/\n/g, " ") : "..."))
  }
} else {
  log("文献较少，跳过局限分析")
}

// Phase 3.5: 方向筛选已合并到 Phase 4.1 Gap Analysis 中（正确性/简洁性/创新性排序规则内嵌于 gap prompt）
// directionContext 直接从文献结果构建，不再单独跑 agent
let directionContext =
  // 阶段一传来的逐字原文（建模 agent 需要回溯题目原文，不只是结构化摘要）
  (chosenAnalysis._rawDescription ? "## 题目原文（逐字引自赛题）\n" + chosenAnalysis._rawDescription + "\n\n" : "") +
  // 阶段一传来的数据画像（建模 agent 需要知道数据的真实形状）
  (chosenAnalysis._dataProfile ? "## 附件数据画像\n" + chosenAnalysis._dataProfile + "\n\n" : "") +
  "## 题目结构化分析\n" + JSON.stringify(chosenAnalysis, null, 2) +
  "\n\n## 文献模型参考\n" + JSON.stringify(allModels.slice(0, 10), null, 2) +
  "\n\n## 文献关键发现\n" + JSON.stringify(allClaims.slice(0, 15), null, 2)
if (limitationAnalysis) {
  directionContext += "\n\n## 标准解法局限\n" + (typeof limitationAnalysis === "string" ? limitationAnalysis : JSON.stringify(limitationAnalysis))
}

// ═══════════════════════════════════════════
// Phase 4: 建模方案 — gap→提案→综合→统一critique⇄修订loop
// ═══════════════════════════════════════════
phase("建模方案")

// ── Step 4.1: Gap analysis —— 总是运行，将局限转化为可操作的切入点 ──
let gapContext = directionContext
let gapAnalysis = null
{
  const gapInput = limitationAnalysis
    ? (typeof limitationAnalysis === "string" ? limitationAnalysis : JSON.stringify(limitationAnalysis))
    : "## 基于题目分析推断的潜在局限\n" + JSON.stringify(chosenAnalysis?.keyChallenges || [], null, 2) +
      "\n\n（文献调研未找到足够参考资料，以下局限分析基于题目本身的关键挑战推断。求解和验证阶段应特别关注这些方向。）"

  gapAnalysis = await agent(
    "## 创新机会分析 (Gap Analysis)\n\n" +
    (chosenAnalysis._rawDescription ? "## 题目原文（逐字引自赛题）\n" + chosenAnalysis._rawDescription + "\n\n" : "") +
    (chosenAnalysis._dataProfile ? "## 附件数据画像\n" + chosenAnalysis._dataProfile + "\n\n" : "") +
    "## 题目结构化分析\n" + JSON.stringify(chosenAnalysis, null, 2) + "\n\n" +
    "## 标准解法局限\n" + gapInput + "\n\n" +
    "## 文献模型参考\n" + JSON.stringify(allModels.slice(0, 8), null, 2) + "\n\n" +
    "## 任务\n" +
    "将上述局限转化为**具体可操作的创新切入点**。每个切入点必须包含：\n" +
    "- 在哪个环节改进？（建模/求解/后处理/数据预处理？）\n" +
    "- 用什么替代什么？（具体技术路径，如「用 P-spline 替代三次多项式解决 Runge 振荡」）\n" +
    "- 预期提升是什么？（精度/效率/稳健性的哪个指标？）\n\n" +
    "**排序规则（优先级从高到低）**：\n" +
    "1. 正确性/可行性第一：核心假设是否有文献支撑？无先例的全新框架 → 高风险\n" +
    "2. 简洁性第二：能用更简单方法达到相近效果吗？简单方案优先\n" +
    "3. 创新性第三：只有正确性和简洁性满足时才加分，不要为了创新而创新\n\n" +
    "输出 3-5 个具体创新切入点，按以上优先级排序。" +
    (limitationAnalysis ? "" : "\n\n⚠️ 文献不足，请基于题目本身的 keyChallenges 和你的领域知识推断合理的局限和改进方向。") +
    "\n\n纯文本输出。" + saveToFile("04-gap-analysis.txt"),
    { label: "gap-analysis", phase: "建模方案" }
  )
  if (gapAnalysis) {
    gapContext = directionContext + "\n\n## 创新机会分析 (Gap Analysis)\n" + (typeof gapAnalysis === "string" ? gapAnalysis : "")
    log("Gap分析: " + (typeof gapAnalysis === "string" ? gapAnalysis.slice(0, 80).replace(/\n/g, " ") : "..."))
  }
}

// ── Step 4.2: 多角度方案提案 ──
// ⚠️ 每个角度都必须贯彻"正确性第一，创新是锦上添花"原则
const INNOVATION_ANGLES = [
  { id: "method", label: "方法改进",
    prompt: "从**方法层面**改进标准流程中的某个关键步骤。具体到公式级别——写出自适应规则的具体数学形式。\n" +
      "⚠️ 正确性第一：能加一项修正解决的就不要替换整个方法。如果标准方法已经够好，你的提案就是「选择标准方法+解释为什么不需要改」——这不叫没有创新，这叫正确。" },
  { id: "model", label: "模型方案",
    prompt: "从**数学模型层面**设计方案。选择标准：哪个框架对这个具体问题最贴切？不要因为某个框架更「高级」而选它。\n" +
      "写成完整的建模方案：假设→符号→方程→求解策略。正确性>简洁性>新颖性。\n" +
      "⚠️ 每个假设必须有文献或常识支撑。超过1个无支撑假设 → 方案不可行。" },
  { id: "algorithm", label: "求解方案",
    prompt: "从**求解算法层面**设计方案。优先使用成熟算法库（scipy/numpy/sklearn）；只在标准方法不适用时才设计新算法。\n" +
      "给出算法复杂度分析，并与标准方法对比。\n" +
      "⚠️ 如果你的「改进算法」跑出来和标准算法结果差异 < 5%，改用标准算法——复杂度更低、更可靠，评委不会因此扣分。" },
]

const innovationProposals = (await parallel(
  INNOVATION_ANGLES.map(angle => () =>
    agent(
      "## 创新提案: " + angle.label + "\n\n" + gapContext + "\n\n" +
      "## 创新方向\n" + angle.prompt + "\n\n" +
      "## ⚠️ 硬性要求（正确性第一，创新是锦上添花）\n" +
      "1. **必要性测试**：如果把这个「创新」去掉，改用该领域最标准的方法，核心结果会差多少？差 < 5% → 这不是有意义的创新，降级为辅助方案。\n" +
      "2. **假设自检**：你的方案有多少个未经文献支撑的假设？超过1个 → 不可行。\n" +
      "3. **可验证性**：你的改进能在 Phase 5-6 中用数据（baseline对比）量化证明吗？不能 → 不可作为主创新。\n" +
      "4. 创新必须**解决 gap analysis 中发现的具体局限**，不能凭空创造。\n" +
      "提出一个完整的、可实现的建模方案。Structured output only." + saveToFile("04-proposal-" + angle.id + ".json"),
      { label: "innovate:" + angle.id, schema: MODEL_PROPOSAL_SCHEMA }
    )
  )
)).filter(Boolean)

log("创新提案: " + innovationProposals.length + " 个")

if (innovationProposals.length === 0) {
  return { error: "创新提案阶段失败——所有 agent 均未返回结果。", analyses, selection }
}

// ── Step 4.4: 综合 —— 从提案中整合出初始建模方案 ──
let finalModel = await agent(
  "## 建模方案综合\n\n" +
  (chosenAnalysis._rawDescription ? "## 题目原文（逐字引自赛题）\n" + chosenAnalysis._rawDescription + "\n\n" : "") +
  (chosenAnalysis._dataProfile ? "## 附件数据画像\n" + chosenAnalysis._dataProfile + "\n\n" : "") +
  "## 题目结构化分析\n" + JSON.stringify(chosenAnalysis, null, 2) + "\n\n" +
  "## 提案方案 (" + innovationProposals.length + " 个)\n" + JSON.stringify(innovationProposals, null, 2) + "\n\n" +
  (allModels.length > 0 ? "## 文献模型\n" + JSON.stringify(allModels.slice(0, 8), null, 2) + "\n\n" : "") +
  (limitationAnalysis ? "## 标准解法局限\n" + (typeof limitationAnalysis === "string" ? limitationAnalysis : "") + "\n\n" : "") +
  "## 任务\n" +
  "综合以上方案给出最终建模路线。你需要完成三件事：\n\n" +
  "1. **必要性筛选**（最重要）：对每个提案中的「创新」，做必要性测试——如果改用该领域最标准的方法，结果会差多少？\n" +
  "   差 < 5% → 这不是有意义的创新，丢弃或用标准方法替代。差 5-15% → 辅助改进，不作为主创新叙事。差 > 15% → 核心创新。\n" +
  "2. **建模方案综合**: 整合好想法，舍弃不可行的。如果多个提案有互相矛盾的假设，选择最有文献支撑的那个。\n" +
  "3. **方案叙事设计**（如有改进点，附在 approach 字段末尾，用 `\\n\\n【方案亮点】` 分隔）：解决了哪个具体问题、改进效果如何、如何在论文中展开。\n" +
  "   如果所有提案都没通过必要性测试 → 诚实地写「采用标准方法」并解释为什么标准方法对这个题目已经足够好——这不丢分，硬贴创新才丢分。\n\n" +
  "⚠️ 这个方案会立即接受 4 人评审团的严格审查——数学家(数学正确性，否决权)+工程师(可实现性，否决权)+领域专家+魔鬼代言人。确保你的方案经得起推敲。\n\n" +
  "Structured output only." + saveToFile("04-final-model.json"),
  { label: "synthesize-model", schema: MODEL_PROPOSAL_SCHEMA }
)
if (!finalModel) {
  return { error: "建模方案综合失败。", proposals: innovationProposals, analyses, selection }
}
log("初始方案: " + (finalModel.approach || "").slice(0, 60))

// ═══ 统一评审团定义（Phase 4 和 Loop B 的 FUNDAMENTAL_FLAW 路径共用）═══
let earlyJudgeReview = null
const MAX_CRITIQUE_ROUNDS = 6
// 4 人评审团：数学正确性 + 可实现性是硬门槛（否决权），领域专家 + 魔鬼代言人提供深度反馈但不参与 gate
const CRITIQUE_PERSONAS = [
  { id: "mathematician", role: "理论数学家", veto: true,
    focus: "方程正确性、量纲一致性、假设自洽性、推导严密性。对数学不严谨零容忍。" },
  { id: "engineer", role: "资深工程师", veto: true,
    focus: "方案可实现性、计算复杂度、近似简化合理性。发现理论可行但工程灾难的设计。" },
  { id: "domain-expert", role: "领域专家", veto: false,
    focus: "方案是否符合该领域实践、是否忽略标准做法、输出数值数量级是否合理。方法堆砌还是方法融合？" },
  { id: "devils-advocate", role: "魔鬼代言人", veto: false,
    focus: "如果竞争对手要推翻这篇论文，从哪攻击。找最薄弱的环节，不用客气。关注：更简单的baseline能否得到类似结果？有没有cherry-picking嫌疑？数值结果是否too good to be true？" },
]

// ═══ critiqueLoop: shared 4-person review → revise cycle ═══
// Used by: Phase 4 model review, Phase 5-6 redesign review
async function critiqueLoop(model, context, opts = {}) {
  const {
    personas = CRITIQUE_PERSONAS,
    maxRounds = MAX_CRITIQUE_ROUNDS,
    label = "critique",
    phaseName = "建模方案",
    savePrefix = "04",
    extraContext = "",
  } = opts
  let currentModel = model
  let bestModelSoFar = null, bestPassCount = -1
  let judgeReview = null
  let vetoPassed = false

  for (let round = 0; round < maxRounds; round++) {
    log(label + " 第" + (round + 1) + "/" + maxRounds + "轮...")

    const critiques = (await parallel(
      personas.map(p => () =>
        agent(
          "## 建模方案评审 — " + p.role + "\n\n" +
          "## 审查角度\n" + p.focus + "\n\n" +
          (context.chosenAnalysis?._rawDescription ? "## 题目原文（逐字引自赛题）\n" + context.chosenAnalysis._rawDescription + "\n\n" : "") +
          (context.chosenAnalysis?._dataProfile ? "## 附件数据画像\n" + context.chosenAnalysis._dataProfile + "\n\n" : "") +
          "## 题目结构化分析\n" + JSON.stringify(context.chosenAnalysis, null, 2) + "\n\n" +
          "## 建模方案\n" + JSON.stringify(currentModel, null, 2).slice(0, 8000) + "\n\n" +
          (round > 0 && judgeReview
            ? "## 上轮评审反馈（必须逐条核对是否已解决）\n" + (typeof judgeReview === "string" ? judgeReview.slice(0, 4000) : "")
            : "") + "\n\n" +
          "## 任务\n" +
          "从你的角色视角严格审查此方案。列出你发现的所有问题（致命/中等/轻微）。\n" +
          (round > 0 ? "**逐条核对上轮反馈**：每个上轮问题是否真正解决了？没解决的标出来。\n" : "") +
          "纯文本输出。\n\n" +
          "**最后一行必须是以下二者之一，单独一行，不要加任何其他字符：**\n" +
          "PASS\nREVISE\n" +
          "PASS = 从你的角度看这个方案已经可以进入求解。REVISE = 仍有你需要看到修复的问题。" +
          saveToFile(savePrefix + "-critique-" + p.id + "-r" + round + ".txt"),
          { label: label + ":" + p.id + "-r" + round, phase: phaseName }
        )
      )
    )).filter(Boolean)

    if (critiques.length === 0) { log(label + " 全部失败，跳过修订循环"); break }

    const verdicts = critiques.map(c => {
      const text = typeof c === "string" ? c : ""
      const lines = text.trim().split("\n")
      return lines[lines.length - 1].trim()
    })
    vetoPassed = personas
      .filter(p => p.veto)
      .every(p => verdicts[personas.indexOf(p)] === "PASS")
    const allPassed = vetoPassed
    const passCount = verdicts.filter(v => v === "PASS").length
    log(label + " r" + round + ": " + passCount + "/" + critiques.length + " PASS (否决" + (vetoPassed ? "✓" : "✗") + ")" + (allPassed ? " 锁定" : ""))

    judgeReview = critiques.map((c, i) =>
      "=== " + personas[i].role + " (" + (verdicts[i] || "?") + ") ===\n" + (typeof c === "string" ? c : "")
    ).join("\n\n")

    if (passCount > bestPassCount) {
      bestPassCount = passCount
      bestModelSoFar = JSON.parse(JSON.stringify(currentModel))
    }

    if (round >= maxRounds - 1 || allPassed) {
      if (!allPassed && bestModelSoFar && bestPassCount > passCount) {
        currentModel = bestModelSoFar
        log("回归检测: 修订后退化(" + bestPassCount + "→" + passCount + " PASS)，回滚到最佳版本")
      }
      if (allPassed) {
        log("全部评审通过，方案锁定")
      } else {
        // 未收敛→最终修复轮：对最后一轮反馈做关键问题修复
        log("已达最大 critique 轮数(" + maxRounds + ")，执行最终修复轮")
        const finalFeedback = critiques.map((c, i) =>
          "### " + personas[i].role + "\n" + (typeof c === "string" ? c.replace(/\nPASS$/, "").replace(/\nREVISE$/, "") : "")
        ).join("\n\n---\n\n")
        const finalRevise = await agent(
          "## 最终修复轮 — 模型修订\n\n" +
          (context.chosenAnalysis?._rawDescription ? "## 题目原文（逐字引自赛题）\n" + context.chosenAnalysis._rawDescription + "\n\n" : "") +
          (context.chosenAnalysis?._dataProfile ? "## 附件数据画像\n" + context.chosenAnalysis._dataProfile + "\n\n" : "") +
          "## 当前方案\n" + JSON.stringify(currentModel, null, 2).slice(0, 6000) + "\n\n" +
          "## 评审团最后一轮反馈（只修关键问题）\n" + finalFeedback.slice(0, 10000) + "\n\n" +
          (context.limitationAnalysis ? "## 文献局限（参考）\n" + (typeof context.limitationAnalysis === "string" ? context.limitationAnalysis.slice(0, 1000) : "") + "\n\n" : "") +
          extraContext +
          "## 修订要求\n" +
          "这是最后一轮修订，只修复**致命问题**（数学错误、可实现性硬伤、假设不自洽）。\n" +
          "不要做大改——不换模型框架、不新增假设、不重构方案。\n" +
          "其余非致命问题标记为已知局限。\n\n" +
          "输出完整 MODEL_PROPOSAL_SCHEMA。Structured output only." + saveToFile(savePrefix + "-final-fix.json"),
          { label: "final-fix-" + label, phase: phaseName, schema: MODEL_PROPOSAL_SCHEMA }
        )
        if (finalRevise) {
          currentModel = finalRevise
          log("最终修复完成")
        }
      }
      break
    }

    const allFeedback = critiques.map((c, i) =>
      "### " + personas[i].role + "\n" + (typeof c === "string" ? c.replace(/\nPASS$/, "").replace(/\nREVISE$/, "") : "")
    ).join("\n\n---\n\n")

    const revised = await agent(
      "## 模型修订（" + personas.length + "人评审团反馈驱动）\n\n" +
      (context.chosenAnalysis?._rawDescription ? "## 题目原文（逐字引自赛题）\n" + context.chosenAnalysis._rawDescription + "\n\n" : "") +
      (context.chosenAnalysis?._dataProfile ? "## 附件数据画像\n" + context.chosenAnalysis._dataProfile + "\n\n" : "") +
      "## 当前方案\n" + JSON.stringify(currentModel, null, 2).slice(0, 6000) + "\n\n" +
      "## 评审团反馈（逐条解决，不得选择性忽略）\n" + allFeedback.slice(0, 12000) + "\n\n" +
      (context.limitationAnalysis ? "## 文献局限（参考）\n" + (typeof context.limitationAnalysis === "string" ? context.limitationAnalysis.slice(0, 1500) : "") + "\n\n" : "") +
      extraContext +
      "## 修订要求\n" +
      "1. **逐条解决**：评审团的每个问题都必须回应——要么修改方案，要么解释为什么不需要改\n" +
      "2. **精简核心**：如果多人说「方法堆砌」，选出1-2个核心创新，其他降级为辅助\n" +
      "3. **深化主线**：如果有人说「不够深」，在核心创新上增加公式推导和理论分析\n" +
      "4. **数学正确性第一**：量纲、假设自洽性等硬伤必须修，这是底线\n" +
      "5. **Q1-Q4全覆盖**：确保每个问题都有对应的方法\n" +
      "6. **三天可实现**：删掉过重的工具，保持方案在三天比赛内可实现\n\n" +
      "输出完整 MODEL_PROPOSAL_SCHEMA。Structured output only." + saveToFile(savePrefix + "-revised-model-r" + round + ".json"),
      { label: "revise-" + label + "-r" + round, phase: phaseName, schema: MODEL_PROPOSAL_SCHEMA }
    )

    if (revised) {
      currentModel = revised
      log("方案已修订(r" + round + "): " + (currentModel.approach || "").slice(0, 80))
    } else {
      log("修订失败，保留当前方案")
      break
    }
  }

  return { finalModel: currentModel, judgeReview, passCount: bestPassCount, vetoPassed: vetoPassed }
}

if (cfg.votesPerClaim > 0) {
  const result = await critiqueLoop(finalModel, { chosenAnalysis, limitationAnalysis }, {
    personas: CRITIQUE_PERSONAS, maxRounds: MAX_CRITIQUE_ROUNDS,
    label: "critique", phaseName: "建模方案", savePrefix: "04",
  })
  finalModel = result.finalModel
  earlyJudgeReview = result.judgeReview
}

// Checkpoint: Phase 4 complete. 如果 workflow crash，可从 `intermediatesDir/04-*.json` 恢复 finalModel。
// 重新运行时会跳过 Phase 1-4（如果 args.selectedProblem 已提供）。

// ═══════════════════════════════════════════
// Phase 4.5: 模型适配性预检 —— 在投入大量agent求解前验证模型是否适合这道题
// quick 模式跳过（votesPerClaim=0），减少 agent 调用
// ═══════════════════════════════════════════
if (cfg.votesPerClaim > 0) {
  const fitnessCheck = await agent(
    "## 模型适配性预检\n\n" +
    "你是数学建模竞赛资深评委，在不运行代码的情况下快速判断建模方案是否适合这道题。\n\n" +
    (chosenAnalysis._rawDescription ? "## 题目原文（逐字引自赛题）\n" + chosenAnalysis._rawDescription + "\n\n" : "") +
    (chosenAnalysis._dataProfile ? "## 附件数据画像\n" + chosenAnalysis._dataProfile + "\n\n" : "") +
    "## 题目结构化分析\n" + JSON.stringify(chosenAnalysis, null, 2) + "\n\n" +
    "## 建模方案\n" + JSON.stringify(finalModel, null, 2).slice(0, 6000) + "\n\n" +
    (limitationAnalysis ? "## 标准解法局限\n" + (typeof limitationAnalysis === "string" ? limitationAnalysis.slice(0, 1500) : "") + "\n\n" : "") +
    "## 评估维度（每个 0-3 分）\n" +
    "1. **问题-方法匹配度**: 这个数学框架是处理此类问题的标准/合理选择吗？\n" +
    "2. **假设支撑度**: 每个假设有文献或常识支撑吗？有无超过 1 个无支撑假设？\n" +
    "3. **求解可行性**: 算法复杂度可控吗？能在三天内用 Python 实现吗？\n" +
    "4. **改进合理性**: 方案中的改进点是否解决真实局限？必要性能通过吗？\n\n" +
    "输出 JSON：{\"scores\":{\"methodFit\":0-3,\"assumptions\":0-3,\"feasibility\":0-3,\"innovation\":0-3},\"totalScore\":0-12,\"verdict\":\"GO\"|\"WARN\"|\"STOP\",\"riskSummary\":\"一句话总结最大风险\"}\n\n" +
    "GO = 总分≥9，方案可靠 → 进入求解\n" +
    "WARN = 总分6-8，有风险但可尝试 → 进入求解但标记 warning\n" +
    "STOP = 总分<6，方案有结构性问题 → 建议打回 Phase 4 重新设计\n\n" +
    "Structured output only.",
    { label: "fitness-check", phase: "建模方案",
      schema: { type: "object", required: ["scores", "totalScore", "verdict"], properties: {
        scores: { type: "object", properties: { methodFit: { type: "integer" }, assumptions: { type: "integer" }, feasibility: { type: "integer" }, innovation: { type: "integer" } } },
        totalScore: { type: "integer" }, verdict: { enum: ["GO", "WARN", "STOP"] }, riskSummary: { type: "string" },
      } }
    }
  )
  if (fitnessCheck) {
    log("模型适配性: " + fitnessCheck.totalScore + "/12 — " + fitnessCheck.verdict + " | " + (fitnessCheck.riskSummary || ""))
    if (fitnessCheck.verdict === "STOP") {
      log("⚠️ 模型适配性检查: STOP — 方案可能有结构性问题，建议回到 Phase 4 重新设计。如果继续求解，预期会触发多次 FUNDAMENTAL_FLAW。")
      // 不强制停止——但记录 warning，求解阶段会更快触发 redesign
    } else if (fitnessCheck.verdict === "WARN") {
      log("⚠️ 模型适配性检查: WARN — 方案有风险但可尝试求解")
    }
  }
}  // end Phase 4.5 (mode guard)

// ═══════════════════════════════════════════
// Phase 5 ⇄ 6 Loop: 求解 → 验证 → 修 → 再验
// ═══════════════════════════════════════════
let iteration = 0, dry = 0, prevNewCount = Infinity, worseningStreak = 0, currentSolution = null, baselineResult = null, needsBaseline = cfg.enableBaseline
let allIssues = [], refutedIssues = [], iterationLog = [], allAdversarialFindings = [], allRethinkResults = []
let redesignHistory = []  // 保存每次重设计的完整方案，供写作阶段引用
let redesignCount = 0
const MAX_REDESIGNS = 2  // 防止无数据环境下死循环

while (dry < cfg.dryThreshold && iteration < cfg.maxIterations) {
  iteration++
  const iterPhase = "求解-第" + iteration + "轮"
  phase(iterPhase)

  // ── Solve ──
  const prevIssues = allIssues.filter(i => i.severity === "critical" || i.severity === "moderate")
  const fixContext = prevIssues.length > 0
    ? "\n\n## ⚠️ 上轮验证问题 (必须修复)\n" + JSON.stringify(prevIssues, null, 2) : ""

  const algoAgent = await agent(
    (iteration === 1
      ? "## 算法设计\n\n" +
        (chosenAnalysis._rawDescription ? "## 题目原文（逐字引自赛题）\n" + chosenAnalysis._rawDescription + "\n\n" : "") +
        (chosenAnalysis._dataProfile ? "## 附件数据画像\n" + chosenAnalysis._dataProfile + "\n\n" : "") +
        "## 建模方案\n" + JSON.stringify(finalModel, null, 2) + "\n\n" +
        (attachments.length > 0 ? "## 附件文件\n" + attachments.map((a, ai) => (ai + 1) + ". `" + a + "`").join("\n") + "\n\n**先读取附件确认数据格式**，然后设计算法。\n\n" : "") +
        "## 任务\n" +
        "设计完整求解算法，**给出可直接翻译为 Python 代码的实现细节**。\n" +
        "1. 每个子问题的输入/输出明确定义\n" +
        "2. 关键公式写清楚计算顺序（不是伪代码概述，是「第1步: np.linalg.solve(A,b)，其中A=..., b=...」这种级别）\n" +
        "3. 数值方法的具体参数（迭代次数、步长、收敛判据等）\n" +
        "4. 附件数据处理流程（pandas读取→清洗→输入模型）\n" +
        "5. 可视化输出设计\n\n" +
        "**禁止说「可以用 xxx 方法」——直接选定一个并给出实现细节。**" +
        (earlyJudgeReview ? "\n\n## 评委反馈\n" + (typeof earlyJudgeReview === "string" ? earlyJudgeReview.slice(0, 2000) : "") + "\n\n算法设计时注意评委点出的风险点。" : "")
      : "## 算法改进 (第" + iteration + "轮)\n\n## 方案\n" + JSON.stringify(finalModel, null, 2) + "\n\n## 上次结果\n" + JSON.stringify(currentSolution?.results || {}, null, 2)
    ) + fixContext + "\n\n" +
    "## 任务\n" +
    (iteration === 1
      ? ""  // already included above
      : "针对验证发现的问题修改算法。不要重新设计——只修改出问题的部分。给出修改后的具体实现细节。") + "\n\n输出纯文本（不要 structured output）。",
    { label: "algo-r" + iteration, phase: iterPhase }
  )
  if (!algoAgent) { log("算法设计失败"); break }

  let solution = await agent(
    "## 代码实现与执行 (第" + iteration + "轮)\n\n" +
    (iteration === 1 && chosenAnalysis._rawDescription ? "## 题目原文（逐字引自赛题）\n" + chosenAnalysis._rawDescription + "\n\n" : "") +
    (iteration === 1 && chosenAnalysis._dataProfile ? "## 附件数据画像\n" + chosenAnalysis._dataProfile + "\n\n" : "") +
    "## 算法设计\n" + algoAgent + "\n\n" +
    "## 建模方案\n" + JSON.stringify(finalModel, null, 2) + "\n\n" +
    (fixContext ? "## ⚠️ 本轮必须修复的问题\n" + fixContext + "\n\n" : "") +
    (attachments.length > 0 ? "## 附件文件（必须读取处理）\n" + attachments.map((a,ai) => (ai+1) + ". `" + a + "`").join("\n") + "\n\n" : "") +
    "## ⚠️ 强制要求：你必须实际运行代码并报告真实结果，不允许只写代码不运行。\n\n" +
    "## 执行步骤\n" +
    "1. `mkdir -p " + outputDir + "` 创建输出目录\n" +
    "2. 将所有 Python 代码写入 `" + outputDir + "/code/solution_v" + iteration + ".py`\n" +
    "3. **如果有附件数据**，先用 `python3 -c \"import pandas; print(pandas.read_excel('附件路径').head())\"` 检查数据结构\n" +
    "4. 用 `run_in_background: true` 在后台运行 Python：\n" +
    "   ```bash\n" +
    "   cd " + outputDir + " && python3 code/solution_v" + iteration + ".py > logs/solution_v" + iteration + ".log 2>&1\n" +
    "   ```\n" +
    "   然后每隔 10 秒检查 `logs/solution_v" + iteration + ".log` 是否完成，最长等待 15 分钟。\n" +
    "   完成后读取日志文件获取结果。如果 15 分钟后仍未完成，报告已产生的文件和部分结果。\n" +
    "5. **如果运行报错**：读取错误信息 → 修改代码 → 重新运行，直到跑通为止\n" +
    "6. 对题目中的**每一个子问题**分别运行并记录结果\n" +
    "7. 生成关键图表并保存到 `" + outputDir + "/figures/fig_v" + iteration + "_*.png`\n\n" +
    "## 报告要求\n" +
    "- results.summary: 每个子问题的**具体数值结果**（不能写「待实现」或「见代码」）\n" +
    "- results.keyValues: 关键变量的数值列表\n" +
    "- testPassed: 所有子问题代码均已跑通 → true\n" +
    "- concerns: 运行中遇到的任何问题\n\n" +
    "**如果你只写了代码没有运行，这个任务就是失败的。**\n\n" +
    "Structured output only.",
    { label: "impl-r" + iteration, phase: iterPhase, schema: SOLUTION_SCHEMA }
  )
  if (!solution) { log("代码实现失败"); break }
  currentSolution = solution

  // Hard check: agent must have actually run the code
  if (!solution.testPassed || !solution.results || !solution.results.summary || solution.results.summary.includes("待实现")) {
    log("⚠️ agent 未实际运行代码，强制重试...")
    const forcedRetry = await agent(
      "## ⚠️ 强制重试：你必须运行代码\n\n" +
      "上次你返回的结果表明你没有实际运行 Python 代码。\n" +
      "现在重新执行以下步骤，**每一步都必须完成**：\n\n" +
      "1. 检查 `" + outputDir + "/code/solution_v" + iteration + ".py` 是否存在？如果不存在，重新写入完整代码\n" +
      "2. 用 `run_in_background: true` 在后台运行：`cd " + outputDir + " && python3 code/solution_v" + iteration + ".py > logs/solution_v" + iteration + "_retry.log 2>&1`，每 10 秒检查，最长等 15 分钟。\n" +
      "3. 如果报错：读错误 → 修代码 → 重跑，直到跑通\n" +
      "4. 复制终端中的**实际输出**到 results.summary\n" +
      "5. testPassed 只有在你亲眼看到代码跑通时才设为 true\n\n" +
      "## 上次返回（无效）\n" + JSON.stringify(solution, null, 2).slice(0, 3000) + "\n\n" +
      "Structured output only.",
      { label: "impl-retry-r" + iteration, phase: iterPhase, schema: SOLUTION_SCHEMA }
    )
    if (forcedRetry) {
      currentSolution = forcedRetry
      solution = forcedRetry  // keep loop-local var in sync for verification prompts below
      log("强制重试完成")
    }
  }

  log("第" + iteration + "轮求解" + (!currentSolution.testPassed ? "(运行错误)" : "完成"))

  // ── Baseline comparison (after first successful solve, or after redesign) ──
  if (cfg.enableBaseline && needsBaseline && currentSolution && currentSolution.testPassed !== false) {
    needsBaseline = false
    const baselineAgent = await agent(
      "## 标准基线求解\n\n" +
      (chosenAnalysis._rawDescription ? "## 题目原文（逐字引自赛题）\n" + chosenAnalysis._rawDescription + "\n\n" : "") +
      (chosenAnalysis._dataProfile ? "## 附件数据画像\n" + chosenAnalysis._dataProfile + "\n\n" : "") +
      "## 题目结构化分析\n" + JSON.stringify(chosenAnalysis, null, 2) + "\n\n" +
      "## 任务\n" +
      "实现**不使用任何创新的标准解法**作为对照基线。这是论文中「与标准方法对比」的数据来源。\n" +
      "是国一论文最有说服力的部分：不是自卖自夸「我们的方法好」，而是用数据证明「好在哪、好多少」。\n\n" +
      "1. 使用该领域最经典/最标准的方法（教科书级别）——不要用任何 Phase 4 中的创新\n" +
      "2. 在相同数据上运行，确保对比公平\n" +
      "3. 记录和运行创新方案时相同的指标\n" +
      "4. 用 `run_in_background: true` 在后台运行 Python 脚本，每 10 秒检查，最长等 15 分钟。完成后读日志取结果。\n\n" +
      "输出：标准方法的结果描述 + 核心指标数值。纯文本。" + saveToFile("05-baseline-result.txt"),
      { label: "baseline", phase: "求解-第1轮" }
    )

    if (baselineAgent) {
      const comparison = await agent(
        "## 创新 vs 标准基线 量化对比\n\n" +
        "## 创新方案结果\n" + JSON.stringify(currentSolution.results, null, 2) + "\n\n" +
        "## 标准基线结果\n" + (typeof baselineAgent === "string" ? baselineAgent.slice(0, 5000) : JSON.stringify(baselineAgent, null, 2)) + "\n\n" +
        "## 任务\n" +
        "量化对比两种方法。这是论文最有说服力的一段——用数据说话。\n\n" +
        "- metrics: 至少3个对比维度（如精度、效率、稳定性）\n" +
        "- 每个 metric 给出 baseline 值、improved 值、improvement 百分比\n" +
        "- summary: 一句话总结创新带来的提升（用于摘要）\n" +
        "- significance: 提升是否显著\n" +
        "- weaknessExposed: 对比暴露了创新方案的什么弱点？（诚实，这也应该在论文中讨论）\n\n" +
        "Structured output only." + saveToFile("05-baseline-comparison.json"),
        { label: "baseline-compare", phase: "求解-第1轮", schema: BASELINE_COMPARISON_SCHEMA }
      )
      if (comparison) {
        baselineResult = comparison
        log("创新 vs 基线: " + (comparison.summary || "").slice(0, 80))
      }
    }
  }

  // ── Verify ──
  const dctx = getDomainExpertise(chosenAnalysis?.domain) || "\n\n## 领域专家视角\n资深工程师，关注计算结果的工程合理性。"
  const actx = attachments.length > 0
    ? ("\n\n## 附件数据验证\n" + attachments.map((a,ai) => (ai+1)+". \`" + a + "\`").join("\n") + "\n用 Python/pandas 读取附件，对比求解输出与参考值。差异>10% → critical severity。") : ""
  // 问题上下文（原文 + 数据画像 + 结构化分析）—— 验证 agent 需要对照题目原文判断模型是否正确
  const problemCtx = ""
    + (chosenAnalysis._rawDescription ? "## 题目原文（逐字引自赛题）\n" + chosenAnalysis._rawDescription + "\n\n" : "")
    + (chosenAnalysis._dataProfile ? "## 附件数据画像\n" + chosenAnalysis._dataProfile + "\n\n" : "")
    + "## 题目结构化分析\n" + JSON.stringify(chosenAnalysis, null, 2)
  const verifiers = [
    {
      dimension: "sensitivity",
      prompt: "## 灵敏度分析\n\n" + problemCtx + "\n\n## 模型\n" + JSON.stringify(finalModel, null, 2) + "\n\n## 求解结果\n" + JSON.stringify(solution.results || {}, null, 2) + "\n\n" +
        "## 已有数据文件（先 `ls " + outputDir + "/data/` 和 `ls " + outputDir + "/figures/` 检查，再决定要不要补跑）\n" +
        "求解阶段可能已生成数据文件和图表。先列出目录内容，如果有数据文件则读取分析；如果没有或不足，才补跑轻量脚本。\n\n" +
        "## 任务\n" +
        "1. **先读已有数据**分析关键参数 (±10%/±20%) 扰动对结果的影响，识别最敏感参数\n" +
        "2. **仅当已有数据不足时**，写一个小型 Python 脚本（≤50 行）做针对性测试——不允许重跑完整求解 pipeline\n" +
        "3. 如果写脚本跑代码：轻量脚本用 `timeout 300 python3 <script>.py 2>&1`；如果预计超 5 分钟，用 `run_in_background: true` 后台跑+每10秒检查日志，最长等 15 分钟。超时后基于已有数据报告，不重试。\n" +
        "每个发现标注 severity。\n\nStructured output only." + dctx + actx,
    },
    {
      dimension: "edge_cases",
      prompt: "## 边界条件测试\n\n" + problemCtx + "\n\n## 模型\n" + JSON.stringify(finalModel, null, 2) + "\n\n## 结果\n" + JSON.stringify(solution.results || {}, null, 2) + "\n\n" +
        "根据题目原文中定义的约束和边界条件，测试极端/边界情况：输入极值、数据缺失、约束边界、不同初始条件。每个发现标注 severity。\n\nStructured output only." + dctx + actx,
    },
    {
      dimension: "adversarial",
      prompt: "## 对抗审查\n\n" + problemCtx + "\n\n## 模型\n" + JSON.stringify(finalModel, null, 2) + "\n\n## 结果\n" + JSON.stringify(solution.results || {}, null, 2) + "\n\n" +
        "对照题目原文，试图找到模型崩溃场景：假设是否成立？是否有更优解？输出物理上合理吗？有没有更简单的 benchmark？每个发现标注 severity。\n\nStructured output only." + dctx + actx,
    },
    // 数据验证（有附件时）
    ...(attachments.length > 0 ? [{
      dimension: "data_validation",
      prompt: "## 硬数据验证\n\n" + problemCtx + "\n\n" +
        "## 附件\n" + attachments.map((a,ai) => (ai+1)+". \\`"+a+"\\`").join("\\n") + "\n\n" +
        "**硬数据检查，不依赖主观判断。**\n" +
        "1. 用 Python pandas 读取附件 xlsx/csv\n" +
        "2. 运行求解代码，将输出与附件参考值逐项对比\n" +
        "3. 报告数值差异百分比和格式匹配情况\n" +
        "4. 差异>10% → critical severity。差异<5% → minor\n\nStructured output only." + dctx
    }] : []),
    // 魔鬼代言人（投票启用时运行：standard + thorough）
    ...(cfg.votesPerClaim > 0 ? [{
      dimension: "devils_advocate",
      prompt: "## 魔鬼代言人审查\n\n" +
        "你是这篇**建模方案和求解结果**的竞争对手，要在评委面前证明这套方法和结论不可信。\n" +
        "⚠️ 注意：论文还没写——你审查的是下面的模型设计+数值结果+baseline对比，不是一篇已完成的论文。\n\n" +
        problemCtx + "\n\n" +
        "## 建模方案\n" + JSON.stringify(finalModel, null, 2).slice(0, 5000) + "\n\n" +
        "## 求解结果\n" + JSON.stringify(solution.results || {}, null, 2).slice(0, 3000) + "\n\n" +
        (baselineResult ? "## Baseline对比\n" + JSON.stringify(baselineResult, null, 2).slice(0, 3000) + "\n\n" : "") +
        "## 审查维度\n" +
        "1. 找到模型最依赖的单个假设——如果它不成立，整个结论崩溃\n" +
        "2. 用更简单的 baseline 方法能否得到类似结果？如果能，复杂模型没带来额外价值\n" +
        "3. 是否存在 cherry-picking（只展示有利数据）？\n" +
        "4. 有更近期方法/数据可以推翻当前结论吗？\n" +
        "5. 数值结果有没有看起来太好的？（too good to be true）\n" +
        "不要客气。每个发现标注 severity。\n\nStructured output only." + saveToFile("06-devils-advocate.json") + dctx
    }] : []),
  ]

  const findings = (await parallel(
    verifiers.map(v => () =>
      agent(v.prompt, { label: "verify:" + v.dimension, phase: "验证-第" + iteration + "轮", schema: VERIFICATION_SCHEMA })
    )
  )).filter(Boolean)

  let verifiedFindings = findings.flatMap(f => (f.findings || []).map(fi => ({ ...fi, _dimension: f.dimension })))

  // 魔鬼代言人 findings 跨迭代累积——每轮的发现都保留，避免早期关键发现被覆盖
  const roundAdversarial = verifiedFindings.filter(f => f._dimension === "devils_advocate")
  // 去重合并：新发现中不在已有列表中的才加入
  for (const af of roundAdversarial) {
    if (!allAdversarialFindings.some(ex => ex.issue === af.issue)) {
      allAdversarialFindings.push(af)
    }
  }

  // Voting on findings — batch multiple findings per agent to reduce calls
  if (cfg.votesPerClaim > 0 && verifiedFindings.length > 0) {
    const BATCH_SIZE = MODE === "thorough" ? 4 : 10  // thorough保准确，standard/quick用大batch
    const batches = []
    for (let i = 0; i < verifiedFindings.length; i += BATCH_SIZE) {
      batches.push(verifiedFindings.slice(i, i + BATCH_SIZE))
    }
    const votedFindings = (await parallel(
      batches.map((batch, bi) => () =>
        agent(
          "## 批量发现验证 (" + batch.length + " 个发现)\n\n" +
          batch.map((f, fi) => "### 发现 #" + fi + " (index=" + fi + ")\n" + JSON.stringify(f, null, 2)).join("\n\n") + "\n\n" +
          "## 题目\n" + JSON.stringify(chosenAnalysis, null, 2) + "\n\n" +
          "## 任务\n" +
          "对每个发现，判断 refuted=true（误报/不重要）还是 refuted=false（有效问题）。不确定倾向于 false。\n" +
          "输出 JSON 数组，每个元素对应一个发现：{\"index\": 0, \"refuted\": false, \"evidence\": \"...\", \"confidence\": \"high/medium/low\"}\n\n" +
          "Structured output only.",
          { label: "vf-batch-" + (bi + 1), phase: "验证-第" + iteration + "轮",
            schema: { type: "object", required: ["verdicts"], properties: { verdicts: { type: "array", items: { type: "object", required: ["index", "refuted"], properties: { index: { type: "integer" }, refuted: { type: "boolean" }, evidence: { type: "string" }, confidence: { enum: ["high", "medium", "low"] } } } } } } }
        ).then(result => {
          const verdicts = (result && result.verdicts) ? result.verdicts : (Array.isArray(result) ? result : [])
          if (!Array.isArray(verdicts) || verdicts.length === 0) return batch.map(f => ({ ...f, confirmed: true, voteSummary: "default" }))
          return batch.map((finding, fi) => {
            const v = verdicts.find(v => v && v.index === fi)
            const refuted = v ? v.refuted : false
            return { ...finding, confirmed: !refuted, voteSummary: refuted ? "refuted" : "confirmed", refuteReasons: refuted && v.evidence ? [v.evidence] : [] }
          })
        })
      )
    )).filter(Boolean)
    const flatFindings = votedFindings.flat()
    // Track refuted findings with reasons
    const refutedThisRound = flatFindings.filter(f => !f.confirmed)
    for (const f of refutedThisRound) {
      refutedIssues.push({ issue: f.issue, refuteReasons: f.refuteReasons || [] })
    }
    verifiedFindings = flatFindings.filter(f => f.confirmed)
  }

  // Dedup phase 1: 精确字符串匹配（快速路径）
  let newIssues = verifiedFindings.filter(
    f => !allIssues.some(ex => ex.issue === f.issue) && !refutedIssues.some(rf => rf.issue === f.issue)
  )

  // Dedup phase 2: 每轮运行语义去重——不同agent描述同一底层问题措辞不同，精确匹配不够
  if (allIssues.length > 5) {
    const dupReport = await agent(
      "## 语义去重\n\n## 已有问题列表 (" + allIssues.length + "个)\n" +
      JSON.stringify(allIssues.map(i => ({ issue: i.issue, severity: i.severity })), null, 2).slice(0, 8000) +
      "\n\n## 本轮新增 (" + newIssues.length + "个)\n" +
      JSON.stringify(newIssues.map(i => ({ issue: i.issue, severity: i.severity })), null, 2) +
      "\n\n## 任务\n" +
      "识别语义重复：不同措辞描述同一底层问题的情况。\n" +
      "输出 JSON：{\"groups\": [[0,5,\"原因\"],[2,7,\"原因\"]]}，每个 group 是应合并为一组的问题索引列表。\n" +
      "只合并真正相同的问题。误解不算重复。",
      { label: "dedup-r" + iteration, phase: "验证-第" + iteration + "轮",
        schema: { type: "object", required: ["groups"], properties: { groups: { type: "array", items: { type: "array", items: { type: "string" } } } } } }
    )
    if (dupReport && Array.isArray(dupReport.groups)) {
      const groups = dupReport.groups
      const mergeCount = groups.length
      // 每组保留第一条，标记后续为重复
      const mergedIndices = new Set()
      for (const group of groups) {
        if (Array.isArray(group) && group.length > 1) {
          for (let gi = 1; gi < group.length; gi++) {
            mergedIndices.add(Number(group[gi]))
          }
        }
      }
      if (mergedIndices.size > 0) {
        newIssues = newIssues.filter((_, i) => !mergedIndices.has(i))
        log("语义去重: 合并 " + mergeCount + " 组 → 移除 " + mergedIndices.size + " 条重复")
      }
    }
  }

  // ── 模型反思 checkpoint（每轮验证后触发）──
  // 评估本轮critical问题是否指向建模路线根本缺陷；若是 → 打回 Phase 4 重新建模
  const criticalNew = newIssues.filter(f => f.severity === "critical")
  if (criticalNew.length >= (cfg.rethinkThreshold || 3)) {
    log("检测到" + criticalNew.length + "个critical问题(第" + iteration + "轮)，触发模型反思...")
    const rethinkResult = await agent(
      "## 模型反思——审视建模路线\n\n" +
      problemCtx + "\n\n" +
      "## 当前建模方案\n" + JSON.stringify(finalModel, null, 2).slice(0, 4000) + "\n\n" +
      "## 本轮新确认的 critical 问题 (" + criticalNew.length + "个)\n" +
      criticalNew.map(f => "- [" + f.severity + "] " + f.issue).join("\n") + "\n\n" +
      "## 所有已确认问题 (" + allIssues.length + "个)\n" +
      allIssues.slice(-20).map(f => "- [" + f.severity + "] " + f.issue).join("\n") + "\n\n" +
      "## 任务\n" +
      "判断：这些问题是否指向**建模路线的根本缺陷**（核心假设不成立、数学框架选错、数据不支持方法）？\n\n" +
      "输出 JSON：{\"verdict\": \"FUNDAMENTAL_FLAW\" | \"FIXABLE\", \"flawedAssumptions\": [\"...\"], \"reasoning\": \"...\", \"suggestedRedesign\": \"如果判定 FLAW，简述应改用哪种建模路线\"}\n\n" +
      "FUNDAMENTAL_FLAW = 核心假设/数学框架需要换，不是调参能解决的\n" +
      "FIXABLE = 问题在实现层面，修代码/改参数可以搞定\n\n" +
      "Structured output only.",
      { label: "model-rethink", phase: "求解-第" + iteration + "轮",
        schema: { type: "object", required: ["verdict", "reasoning"], properties: { verdict: { enum: ["FUNDAMENTAL_FLAW", "FIXABLE"] }, flawedAssumptions: { type: "array", items: { type: "string" } }, reasoning: { type: "string" }, suggestedRedesign: { type: "string" } } } }
    )

    if (rethinkResult && rethinkResult.verdict === "FUNDAMENTAL_FLAW") {
      redesignCount++
      if (redesignCount > MAX_REDESIGNS) {
        log("已达最大重新设计次数(" + MAX_REDESIGNS + ")，以当前方案继续求解")
        allIssues.push(...criticalNew.map(i => ({ ...i, severity: "moderate", issue: "[未解决] " + i.issue })))
        continue
      }
      log("判定: 建模路线根本缺陷 → 打回 Phase 4 重新建模 (#" + redesignCount + "/" + MAX_REDESIGNS + ")")
      log("缺陷假设: " + (rethinkResult.flawedAssumptions || []).join("; ").slice(0, 200))

      // ── Alert: 通知用户建模路线问题 ──
      log("⚠️⚠️⚠️ 建模路线根本缺陷! 自动启动重新设计流程。用户可随时通过 /workflows 查看进度。")
      await agent(
        "## 写警报文件\n\n" +
        "将以下内容写入 `" + outputDir + "/logs/MODEL_RETHINK_ALERT.txt`：\n\n" +
        "建模路线根本缺陷检测报告\n" +
        "========================\n" +
        "时间: 第" + iteration + "轮验证后\n" +
        "缺陷假设:\n" + (rethinkResult.flawedAssumptions || []).map(a => "  - " + a).join("\n") + "\n\n" +
        "分析:\n" + (rethinkResult.reasoning || "") + "\n\n" +
        "建议方向:\n" + (rethinkResult.suggestedRedesign || "") + "\n\n" +
        "---\n" +
        "Workflow 将自动进行模型重新设计并由4人评审团审查。\n" +
        "用户可在任何时候通过 /workflows 查看进度。\n\n" +
        "Use Write tool to create this file. Create dir first if needed.",
        { label: "write-alert", phase: "求解-第" + iteration + "轮" }
      )

      // ── 重新建模：利用所有验证知识设计新方案 ──
      const redesignContext = "## 原始方案\n" + JSON.stringify(finalModel, null, 2).slice(0, 3000) +
        "\n\n## 验证暴露的问题\n" + JSON.stringify(allIssues.filter(f => f.severity === "critical").slice(-15), null, 2) +
        "\n\n## 模型反思结论\n" + JSON.stringify(rethinkResult, null, 2)

      let redesignApproach = await agent(
        "## 建模路线重新设计\n\n" + problemCtx + "\n\n" + redesignContext + "\n\n" +
        "## 文献上下文\n" + JSON.stringify({ models: allModels.slice(0, 8), claims: allClaims.slice(0, 10) }, null, 2) + "\n\n" +
        "## 任务\n" +
        "根据验证暴露的根本问题，重新设计建模路线。不要改参数——换思路。\n" +
        "比如：生存分析不行→换贝叶斯分层模型？PAVA过拟合→换正则化回归？AFT随机→换决策树ensemble？\n" +
        "给出完整的重新设计方案：假设→符号→方程→求解策略。\n\n" +
        "Structured output only." + saveToFile("04-redesign-r" + iteration + ".json"),
        { label: "redesign-model", phase: "求解-第" + iteration + "轮", schema: MODEL_PROPOSAL_SCHEMA }
      )

      if (redesignApproach) {
        if (cfg.votesPerClaim > 0) {
          const extraCtx = "\n## 原方案致命缺陷\n" + JSON.stringify(rethinkResult.flawedAssumptions || [], null, 2) +
            "\n## 原方案验证暴露的问题\n" + JSON.stringify(allIssues.filter(f => f.severity === "critical").slice(-10), null, 2)
          const redesignResult = await critiqueLoop(redesignApproach, { chosenAnalysis, limitationAnalysis }, {
            personas: CRITIQUE_PERSONAS, maxRounds: 2,
            label: "redesign-critique", phaseName: "求解-第" + iteration + "轮", savePrefix: "04-redesign",
            extraContext: extraCtx,
          })
          redesignApproach = redesignResult.finalModel
          if (redesignResult.vetoPassed) {
            redesignHistory.push({ iteration, approach: JSON.parse(JSON.stringify(redesignApproach)), reason: rethinkResult?.reasoning })
            finalModel = redesignApproach
            const legacyIssues = allIssues.filter(f => f.severity === "critical").slice(-10)
            currentSolution = null; dry = 0; baselineResult = null; needsBaseline = true
            allIssues = []; refutedIssues = []
            if (legacyIssues.length > 0) {
              allIssues.push(...legacyIssues.map(i => ({ ...i, severity: "moderate", issue: "[原方案遗留] " + i.issue })))
            }
            log("重新设计通过4人审查! 新方案: " + (redesignApproach.approach || "").slice(0, 80))
          } else {
            log("重新设计审查未通过，保留原方案继续")
          }
        } else {
          redesignHistory.push({ iteration, approach: JSON.parse(JSON.stringify(redesignApproach)), reason: rethinkResult?.reasoning })
          finalModel = redesignApproach
          currentSolution = null; dry = 0; baselineResult = null; needsBaseline = true
          allIssues = []; refutedIssues = []
          log("重新设计方案: " + (redesignApproach.approach || "").slice(0, 80))
        }
      }
    } else if (rethinkResult && rethinkResult.verdict === "FIXABLE") {
      log("判定: 问题可修复 — 继续求解迭代")
    }
    // 无论 FLAW 还是 FIXABLE，反思结果都保存下来供写作阶段使用
    if (rethinkResult) {
      allRethinkResults.push({ iteration, verdict: rethinkResult.verdict, flawedAssumptions: rethinkResult.flawedAssumptions, reasoning: rethinkResult.reasoning, suggestedRedesign: rethinkResult.suggestedRedesign })
    }
  }

  // ── Dry/Convergence logic + Trend exit ──
  if (newIssues.length === 0) {
    dry++
    log("第" + iteration + "轮: 无新问题 (dry=" + dry + "/" + cfg.dryThreshold + ")")
  } else {
    dry = 0
    allIssues.push(...newIssues)
    const criticalNow = newIssues.filter(f => f.severity === "critical").length
    log("第" + iteration + "轮: +" + newIssues.length + " 问题 (critical=" + criticalNow + " total=" + allIssues.length + "), dry 重置")
  }

  // 趋势退出：连续2轮newIssues不降反升 → 求解在恶化，退出
  if (prevNewCount !== Infinity) {
    if (newIssues.length >= prevNewCount) { worseningStreak++; }
    else { worseningStreak = 0; }
    if (worseningStreak >= 2) {
      log("求解趋势恶化(连续" + worseningStreak + "轮不降)→ 退出迭代")
      break
    }
  }
  prevNewCount = newIssues.length

  // 溢出退出：累积问题过多时取TOP修复后退出
  if (allIssues.length > 50) {
    log("累积问题超50个(allIssues=" + allIssues.length + ")→ 取critical+top20修复后退出")
    break
  }

  iterationLog.push({ iteration, newIssues: newIssues.length, dry, totalIssues: allIssues.length })
}

// ── 最终修复轮：非收敛退出时，对 unresolved critical 问题做一次修复 ──
const solveConverged = dry >= cfg.dryThreshold
if (!solveConverged && currentSolution && allIssues.length > 0) {
  const unfixedCritical = allIssues.filter(i => i.severity === "critical").slice(0, 5)
  if (unfixedCritical.length > 0) {
    log("求解未收敛(dry=" + dry + "/" + cfg.dryThreshold + ")，执行最终修复 (critical=" + unfixedCritical.length + ")")
    const finalFixAlgo = await agent(
      "## 最终修复 — 算法修正\n\n" +
      (chosenAnalysis._rawDescription ? "## 题目原文（逐字引自赛题）\n" + chosenAnalysis._rawDescription + "\n\n" : "") +
      (chosenAnalysis._dataProfile ? "## 附件数据画像\n" + chosenAnalysis._dataProfile + "\n\n" : "") +
      "## 建模方案\n" + JSON.stringify(finalModel, null, 2).slice(0, 4000) + "\n\n" +
      "## 上一轮求解结果\n" + JSON.stringify(currentSolution?.results || {}, null, 2).slice(0, 2000) + "\n\n" +
      "## 待修复的 critical 问题（只修这些）\n" + unfixedCritical.map(i => "- [" + i.severity + "] " + i.issue).join("\n") + "\n\n" +
      "## 任务\n" +
      "只修复以上列出的 critical 问题。不做大改——不换算法框架、不重构代码。\n" +
      "给出修改后的具体实现细节。输出纯文本。",
      { label: "final-fix-algo", phase: "求解-最终修复" }
    )
    if (finalFixAlgo) {
      const finalFixImpl = await agent(
        "## 最终修复 — 代码实现\n\n" +
        "## 算法修正\n" + finalFixAlgo + "\n\n" +
        "## 上一轮求解结果\n" + JSON.stringify(currentSolution?.results || {}, null, 2).slice(0, 2000) + "\n\n" +
        "## 任务\n" +
        "将算法修正写入代码并运行。\n" +
        "1. 将修改后的代码写入 `" + outputDir + "/code/solution_final_fix.py`\n" +
        "2. 用 `run_in_background: true` 后台运行：`cd " + outputDir + " && python3 code/solution_final_fix.py > logs/solution_final_fix.log 2>&1`，每10秒检查，最长等15分钟\n" +
        "3. 报告实际运行结果。\n\n" +
        "Structured output only.",
        { label: "final-fix-impl", phase: "求解-最终修复", schema: SOLUTION_SCHEMA }
      )
      if (finalFixImpl) {
        currentSolution = finalFixImpl
        log("求解最终修复完成")
        // 标记这些 critical 为已处理
        for (const ci of unfixedCritical) {
          ci.severity = "moderate"
          ci.issue = "[最终修复] " + ci.issue
        }
      }
    }
  }
}

log("求解⇄验证结束: " + iteration + "轮, " + allIssues.length + "个问题, " + allIssues.filter(i => i.severity === "critical").length + "个严重")

// ═══════════════════════════════════════════
// Phase 7: 写作 — 创新追溯矩阵 → 叙事大纲 → 并行写作 → 交叉审查
// ═══════════════════════════════════════════
if (!currentSolution) {
  return { error: "求解阶段未产生有效解。", analyses, selection, finalModel, allIssues, iterationLog }
}
if (!finalModel) {
  return { error: "建模阶段未产生有效方案。", analyses, selection }
}
phase("写作")

// ── Step 7.0: 创新追溯矩阵 —— 确保创新点在论文各章节完整传递 ──
let innovationMatrix = null
if (cfg.votesPerClaim > 0) {
  innovationMatrix = await agent(
    "## 创新追溯矩阵\n\n" +
    (chosenAnalysis._rawDescription ? "## 题目原文（逐字引自赛题）\n" + chosenAnalysis._rawDescription + "\n\n" : "") +
    (chosenAnalysis._dataProfile ? "## 附件数据画像\n" + chosenAnalysis._dataProfile + "\n\n" : "") +
    "## 最终建模方案\n" + JSON.stringify(finalModel, null, 2).slice(0, 5000) + "\n\n" +
    "## Gap Analysis 局限\n" + (typeof limitationAnalysis === "string" ? limitationAnalysis.slice(0, 2000) : "") + "\n\n" +
    "## 求解结果\n" + JSON.stringify(currentSolution?.results || {}, null, 2).slice(0, 2000) + "\n\n" +
    (baselineResult ? "## Baseline 对比\n" + JSON.stringify(baselineResult, null, 2).slice(0, 1500) + "\n\n" : "") +
    "## 任务\n" +
    "生成创新追溯表格。每个创新点一行，每行包含：\n" +
    "| 创新点 | 解决的GAP/局限 | 对应方程/算法 | 验证指标 | 基线对比提升 | 摘要位点 | 模型章位点 | 分析章位点 |\n\n" +
    "确保：(1) 每个创新点都有对应的验证数据支撑 (2) 摘要中提到的东西在模型章节有详细展开 (3) 分析章节的结论与baseline对比一致\n\n" +
    "输出纯文本表格。",
    { label: "innovation-matrix", phase: "写作" }
  )
  if (innovationMatrix) log("创新追溯矩阵完成")
}

// ═══ Context builders — per-agent targeted subsets ═══
const advFindings = allAdversarialFindings || []
const otherIssues = allIssues.filter(i => !advFindings.some(a => a.issue === i.issue))
const figuresDir = outputDir + "/figures"

const allContext = {
  problem: chosenAnalysis, selection,
  // 阶段一传来的逐字原文、数据画像、论文规则
  rawDescription: chosenAnalysis._rawDescription || "",
  dataProfile: chosenAnalysis._dataProfile || "",
  paperRules: chosenAnalysis._paperRules || "",
  finalModel, solution: currentSolution,
  adversarialFindings: advFindings.map(f => ({ issue: f.issue, severity: f.severity, evidence: f.evidence })),
  rethinkHistory: allRethinkResults.map(r => ({ iteration: r.iteration, verdict: r.verdict, flawedAssumptions: r.flawedAssumptions, reasoning: (r.reasoning || "").slice(0, 500) })),
  redesignHistory: redesignHistory.map(r => ({ iteration: r.iteration, reason: (r.reason || "").slice(0, 300), approachSummary: (r.approach?.approach || "").slice(0, 500) })),
  innovationMatrix: typeof innovationMatrix === "string" ? innovationMatrix.slice(0, 3000) : null,
  innovation: {
    limitationAnalysis: typeof limitationAnalysis === "string" ? limitationAnalysis.slice(0, 3000) : null,
    gapAnalysis: typeof gapAnalysis === "string" ? gapAnalysis.slice(0, 2000) : null,
    baselineResult: baselineResult ? { summary: baselineResult.summary, significance: baselineResult.significance, metrics: baselineResult.metrics, weaknessExposed: baselineResult.weaknessExposed } : null,
    earlyJudgeReview: typeof earlyJudgeReview === "string" ? earlyJudgeReview.slice(0, 2000) : null,
  },
  literature: { sources: allSources.length, models: allModels.slice(0, 10), keyClaims: allClaims.slice(0, 15) },
  verification: { otherIssues, iterationLog },
}

// Internal helper: serialize with priority truncation
const WRITING_PRIORITY = ["paperRules", "adversarialFindings", "finalModel", "rawDescription", "dataProfile", "solution", "problem", "innovation", "rethinkHistory", "redesignHistory", "innovationMatrix", "literature", "verification"]
function buildContextStr(ctx, priorityKeys, budget) {
  const parts = []
  let remaining = budget
  for (const key of priorityKeys) {
    if (ctx[key] === null || ctx[key] === undefined) continue
    const block = "## " + key + "\n" + JSON.stringify(ctx[key], null, 2) + "\n"
    if (block.length <= remaining) { parts.push(block); remaining -= block.length }
    else { parts.push(block.slice(0, remaining)); remaining = 0; break }
  }
  const remainingKeys = Object.keys(ctx).filter(k => !priorityKeys.includes(k) && ctx[k] !== null && ctx[k] !== undefined)
  for (const key of remainingKeys) {
    const block = "## " + key + "\n" + JSON.stringify(ctx[key], null, 2) + "\n"
    if (block.length <= remaining) { parts.push(block); remaining -= block.length }
    else if (remaining > 100) { parts.push(block.slice(0, remaining)); remaining = 0; break }
    else break
  }
  return parts.join("\n")
}

// Named builders — each targets a specific agent's needs
const buildWritingContext = () => buildContextStr(allContext, WRITING_PRIORITY, cfg.contextBudget)
const buildNarrativeContext = () => buildContextStr(allContext, WRITING_PRIORITY, Math.floor(cfg.contextBudget * 0.8))

const writingContext = buildWritingContext()

// ── Step 7.1: 叙事大纲 —— 论文不是技术报告 ──
let narrativeOutline = null
if (cfg.votesPerClaim > 0) {
  narrativeOutline = await agent(
    "## 论文叙事大纲\n\n" +
    "## 建模上下文\n" + buildNarrativeContext() + "\n\n" +
    "## 任务\n" +
    "为国一论文设计叙事大纲。记住：论文不是技术报告——评委是人，读完要有「这个队有想法」的直觉。\n\n" +
    "设计要点：\n" +
    "1. **方案逻辑为主线**：核心方法如何逐层展开？如有改进点，自然融入推导，不要最后才贴上去。\n" +
    "2. **问题驱动**：每一章回答什么问题？为什么读者想看下一章？\n" +
    "3. **节奏控制**：模型推导(dense)→结果展示(light)→亮点highlight(punch)——张弛有道\n" +
    "4. **记忆点**：哪一段让评委在这100篇论文里记住你的？\n" +
    "5. **摘要先行**：摘要要怎么埋钩子让评委想继续看？\n\n" +
    "输出：各章节的叙事定位、衔接逻辑、创新展示节奏、记忆点设计。" + saveToFile("07-narrative-outline.txt"),
    { label: "narrative-outline", phase: "写作" }
  )
  if (narrativeOutline) {
    log("叙事大纲完成")
  }
}

// ── Step 7.2: 章节定义（按 preset 选择）──
const SECTION_PRESETS = {
  compact: [
    { id: "abstract", label: "摘要", prompt: "撰写摘要。问题、方法、创新、核心结果、结论。300-500字。**必须有具体数字。**\n\n最后附上**关键词**（3-5个，用分号分隔）。" },
    { id: "intro", label: "问题重述+假设", prompt: "重述问题+列出假设+符号说明。" },
    { id: "model", label: "模型+求解", prompt: "完整推导+方程+算法+结果。**创新自然融入推导，不是单独贴一段。**" },
    { id: "closing", label: "分析+结论", prompt: "结果分析+灵敏度+优劣势+总结改进。" },
  ],
  standard: [
    { id: "abstract", label: "摘要", prompt: "撰写摘要。问题、方法、创新、核心结果、结论。300-500字。**必须有具体数字和创新highlight。**\n\n最后附上**关键词**（3-5个，用分号分隔）。" },
    { id: "restatement", label: "问题重述", prompt: "重述问题。背景、分析、已知条件、目标。" },
    { id: "assumptions", label: "模型假设+符号", prompt: "列出假设+符号说明表。每个假设说明合理性。" },
    { id: "model", label: "模型建立与求解", prompt: "完整推导+方程(LaTeX)+算法+结果。**创新点自然融入推导——不是单独贴一段。**如有baseline对比用表格展示。" },
    { id: "analysis_conclusion", label: "分析+结论", prompt: "结果分析、灵敏度、优劣势、baseline对比 + 总结改进方向。**必须引用adversarialFindings和redesignHistory。**" },
  ],
  full: [
    { id: "abstract", label: "摘要", prompt: "撰写摘要。概述问题、方法、创新亮点、核心结果、结论。300-500字。**必须有：①具体数字（不要模糊说「显著提升」）②创新一句话 ③如果有baseline对比，用百分比**\n\n最后附上**关键词**（3-5个，用分号分隔）。" },
    { id: "restatement", label: "问题重述", prompt: "重述问题。背景、问题分析、已知条件、求解目标。不要复制原题——用自己的话重新组织。" },
    { id: "assumptions", label: "模型假设+符号", prompt: "列出假设条件和符号说明。每个假设说明合理性（为什么可以这样简化）。符号用表格（符号|含义|单位）。" },
    { id: "model", label: "模型建立与求解", prompt: "核心章节。写出完整模型推导、关键方程(LaTeX)、求解算法、代码逻辑、结果(含图表描述)。**创新点要自然融入推导过程——不是单独一段「我们的创新是……」而是在推导中展示「标准方法在这里有X局限，因此我们引入Y来处理」。**如有baseline对比数据，在这里用表格展示。" },
    { id: "analysis", label: "结果分析与验证", prompt: "分析结果意义、灵敏度、模型优劣势、与baseline/文献对比。如果有baseline对比数据，用图表展示创新vs标准的差异。诚实讨论局限。**必须引用adversarialFindings和redesignHistory中至少各1条发现。**" },
    { id: "conclusion", label: "结论与改进", prompt: "总结全文，重申创新贡献和关键发现。提出改进方向和未来工作。**这一章必须是论文最后一章。**实事求是，不要过度吹嘘。" },
  ],
}
const sectionDefs = SECTION_PRESETS[cfg.sectionPreset] || SECTION_PRESETS.compact

const formatGuide = cfg.latexOutput
  ? "\n\n## LaTeX 格式要求\n" +
    "输出完整 LaTeX 源码，要求：\n" +
    "- 章节标题：`\\section{...}`、`\\subsection{...}`\n" +
    "- 行内公式：`$...$`，独立公式：`\\begin{equation}...\\end{equation}`\n" +
    "- 表格：`\\begin{table}...\\end{table}` + `\\begin{tabular}...\\end{tabular}`\n" +
    "- 图片：`\\begin{figure}...\\includegraphics{...}...\\end{figure}`\n" +
    "- 引用：`\\cite{...}`（参考文献必须按科技论文规范列出，正文中标注引用位置）\n" +
    "- 列表：`\\begin{itemize}...\\end{itemize}` 或 `\\begin{enumerate}...\\end{enumerate}`\n" +
    "- 中文字符直接写，不需要转义\n" +
    "- **不要**包含 `\\documentclass`、`\\begin{document}`、`\\maketitle` 等文档级命令\n" +
    "- 仅输出你负责的这一章节的 body 内容\n" +
    "- ⚠️ 文中不要出现参赛者身份、学校、赛区信息（CUMC 禁令）"
  : "\n\n格式：中文撰写，公式用 LaTeX ($...$ 或 $$...$$)。⚠️ 文中不要出现参赛者身份、学校、赛区信息。"

const EXPECTED_SECTION_COUNT = sectionDefs.length  // 预期章节数，交叉审查时验证

// ── Step 7.2: 各章节并行撰写 ──
const paperSections = (await parallel(
  sectionDefs.map(s => () =>
    agent(
      "## 论文撰写: " + s.label + "\n\n" +
      "## ⚠️ 论文格式规则（必须严格遵守）\n" + CUMC_PAPER_RULES + "\n" +
      (chosenAnalysis._paperRules ? "\n### 题目特定补充规则\n" + chosenAnalysis._paperRules + "\n" : "") + "\n" +
      "## 叙事大纲\n" + (narrativeOutline ? (typeof narrativeOutline === "string" ? narrativeOutline.slice(0, 3000) : "") : "（无叙事大纲，请自行组织）") + "\n\n" +
      "## 全部上下文\n" + writingContext + "\n\n" +
      "## 图表\n求解阶段已生成图表在 `" + figuresDir + "` 目录下。如果 `ls " + figuresDir + "` 有文件，在合适的章节中用 `\\includegraphics{...}` 引用。\n\n" +
      "## 任务\n" + s.prompt + formatGuide + "\n\n" +
      "本章节应自包含但注意上下文连贯。\n\nStructured output only." + saveToFile("05-writing/section-" + s.id + ".json"),
      { label: "write:" + s.id, phase: "写作", schema: PAPER_SECTION_SCHEMA }
    )
  )
)).filter(Boolean)

log("完成 " + paperSections.length + " 个章节")

// ── Step 7.3: 交叉审查 ⇄ 修复 loop（并行交叉审查 + 评委视角审查）──
// quick 模式: 1轮审查不loop; standard/thorough: max 3轮 dry=2收敛
const MAX_WRITING_ROUNDS = cfg.votesPerClaim > 0 ? 3 : 1
let writingRound = 0, writingDry = 0, prevWritingP0Count = Infinity
let crossSectionReview = null

while (writingDry < 2 && writingRound < MAX_WRITING_ROUNDS) {
  writingRound++
  log("写作审查 第" + writingRound + "/" + MAX_WRITING_ROUNDS + "轮...")

  // ── 并行：交叉审查（含质量门）+ 评委视角审查 ──
  const [crossReview, judgeReview] = (await parallel([
    // 交叉审查（含质量门检查）
    () => agent(
      "## 交叉一致性审查 + 质量门 (第" + writingRound + "轮)\n\n" +
      "## 叙事大纲（预期结构）\n" + (narrativeOutline ? (typeof narrativeOutline === "string" ? narrativeOutline.slice(0, 3000) : "") : "（无）") + "\n\n" +
      "## 各章节内容\n" + paperSections.map(s => "### " + s.section + "\n" + (s.content || "").slice(0, 3000)).join("\n\n---\n\n") + "\n\n" +
      "## 创新追溯矩阵（对照检查）\n" + (typeof innovationMatrix === "string" ? innovationMatrix.slice(0, 2000) : "（无）") + "\n\n" +
      "## 任务：逐项检查以下维度\n\n" +
      "### 一致性检查\n" +
      "1. **符号统一**: 问题重述→模型→结果中的符号是否一致？\n" +
      "2. **数据一致**: 摘要中的数字→正文中的数据→结论中的引用是否匹配？**每个摘要中的数字都必须能在正文中找到出处**，找不到标记为 P0。\n" +
      "3. **逻辑连贯**: 假设→推导→结果→结论是否有逻辑断点？\n" +
      "4. **创新呼应**: 创新点是否在各章节中得到呼应？对照创新追溯矩阵检查。\n" +
      "5. **重复/矛盾**: 不同章节写相同内容？或互相矛盾？\n\n" +
      (writingRound > 1 ? "### ⚠️ 上轮 P0 修复验证\n逐条检查上轮发现的 P0 问题是否真正修复了。没修复的再次标记为 P0。\n\n" : "") +
      "### 质量门检查（硬性指标）\n" +
      "6. **章节数量**: 实际章节数=" + paperSections.length + "，预期=" + EXPECTED_SECTION_COUNT + "。缺失章节→P0。\n" +
      "7. **章节排序**: 结论/改进方向应该是最后一章，不在第1-3节。排序错误→P0。\n" +
      "8. **图表引用**: 是否有求解生成的图表未被引用？列出该引用但未引用的图表。\n" +
      "9. **章节长度**: 模型章<2000字→P0，其他核心章<500字→P1。\n" +
      "10. **redesignHistory引用**: 局限性讨论是否引用了模型重设计历史（至少1条）？\n" +
      "11. **adversarialFindings引用**: 局限性章节是否引用了魔鬼代言人发现（至少2条）？\n\n" +
      "输出格式：每个问题一行 `[severity:P0/P1/P2] [章节名] 问题描述 | 修复建议`。\n纯文本。" + saveToFile("05-writing/cross-review-r" + writingRound + ".txt"),
      { label: "cross-review-r" + writingRound, phase: "写作" }
    ),
    // 评委视角审查
    ...(writingRound < MAX_WRITING_ROUNDS ? [() => agent(
      "## 评委视角审查 (第" + writingRound + "轮)\n\n" +
      "你是数模评委，读了100篇同题论文。快速扫读以下论文后回答：\n\n" +
      "## 论文\n" + paperSections.map(s => "## " + s.section + "\n" + (s.content || "").slice(0, 2500)).join("\n\n") + "\n\n" +
      "## 评估\n" +
      "1. **结构**: 章节顺序合理吗？有没有前言不搭后语？结论放对位置了吗？\n" +
      "2. **可读性**: 读完知道创新是什么吗？还是得自己找？\n" +
      "3. **数字可信度**: 摘要/正文里的数字有推导支撑吗？还是看起来像编的？\n" +
      "4. **最大弱点**: 哪个问题最影响评分？（具体说，不要废话）\n" +
      "5. **一句话建议**: 改什么最提升竞争力？\n\n" +
      "输出纯文本，坦诚直接。每行一个问题格式：`[severity] 问题 | 建议`。" + saveToFile("05-writing/judge-review-r" + writingRound + ".txt"),
      { label: "judge-review-r" + writingRound, phase: "写作" }
    )] : []),
  ])).filter(Boolean)

  const crossText = typeof crossReview === "string" ? crossReview : ""
  const judgeText = typeof judgeReview === "string" ? judgeReview : ""

  // 提取 P0 问题计数
  const p0Matches = (crossText + "\n" + judgeText).match(/\[P0\]/g) || []
  const allIssueLines = (crossText + "\n" + judgeText).split("\n").filter(l => /\[P[0-2]\]/.test(l))
  const currentP0Count = p0Matches.length
  crossSectionReview = crossText + "\n\n=== 评委视角 ===\n" + judgeText

  if (allIssueLines.length === 0 || (currentP0Count === 0 && writingRound > 1)) {
    writingDry++
    log("审查 r" + writingRound + ": 0 个新问题 (dry=" + writingDry + "/2)")
  } else {
    if (currentP0Count >= prevWritingP0Count) {
      writingDry = 0
    }
    prevWritingP0Count = currentP0Count
    log("审查 r" + writingRound + ": " + allIssueLines.length + " 个问题 (P0=" + currentP0Count + ")")
  }

  if (writingDry >= 2 || (allIssueLines.length === 0 && writingRound >= 2)) {
    log("写作审查收敛 (dry=" + writingDry + ")，跳过修复")
    break
  }
  if (writingRound >= MAX_WRITING_ROUNDS) {
    log("已达最大写作审查轮数(" + MAX_WRITING_ROUNDS + ")，执行最终 P0 修复")
    // 最后一轮 P0 修复
    const combinedIssues = crossText + "\n" + judgeText
    const p0Lines = combinedIssues.split("\n").filter(l => /\[P0\]/.test(l))
    if (p0Lines.length > 0) {
      const p0Only = p0Lines.join("\n")
      const fixPrompts = paperSections.map(s => () =>
        agent(
          "## 最终 P0 修复: " + s.section + "\n\n" +
          "## 你的章节内容\n" + (s.content || "").slice(0, 5000) + "\n\n" +
          "## ⚠️ 只修复这些 P0 问题（其他忽略）\n" +
          p0Only.slice(0, 6000) + "\n\n" +
          "## 修复要求\n" +
          "只修复 P0 问题。这是最后一轮，不做大改——精准修复，不重写章节。\n" +
          "输出修改后的完整 content。Structured output only.",
          { label: "final-fix:" + s.id, phase: "写作", schema: PAPER_SECTION_SCHEMA }
        ).then(fixed => fixed || s)
      )
      const fixedSections = (await parallel(fixPrompts)).filter(Boolean)
      for (const fs of fixedSections) {
        const idx = paperSections.findIndex(s => s.id === fs.id || s.section === fs.section)
        if (idx >= 0) paperSections[idx] = fs
      }
      log("最终 P0 修复完成: " + fixedSections.length + " 个章节已更新")
    }
    break
  }

  // ── 修复：各章节并行修（只修审查指出的问题）──
  const combinedIssues = crossText + "\n" + judgeText
  const fixPrompts = paperSections.map(s => () =>
    agent(
      "## 章节修复: " + s.section + " (第" + writingRound + "轮)\n\n" +
      "## 你的章节内容\n" + (s.content || "").slice(0, 5000) + "\n\n" +
      "## 审查发现的问题（只修复与你章节相关的，其他忽略）\n" +
      combinedIssues.slice(0, 8000) + "\n\n" +
      "## 修复要求\n" +
      "- 只修改审查报告中指出的问题（符号、数字、逻辑衔接、创新呼应、图表引用、结构排序）\n" +
      "- 不要重写整个章节——精准手术，不是开膛\n" +
      "- 如果某个问题不涉及你的章节，忽略它\n" +
      "- **特别注意**：如果问题涉及摘要数字无出处，要么补推导，要么删数字\n" +
      "输出修改后的完整 content。Structured output only.",
      { label: "fix:" + s.id + "-r" + writingRound, phase: "写作", schema: PAPER_SECTION_SCHEMA }
    ).then(fixed => fixed || s)
  )
  const fixedSections = (await parallel(fixPrompts)).filter(Boolean)
  for (const fs of fixedSections) {
    const idx = paperSections.findIndex(s => s.id === fs.id || s.section === fs.section)
    if (idx >= 0) paperSections[idx] = fs
  }
  log("修复完成 r" + writingRound + ": " + fixedSections.length + " 个章节已更新")
}

// ═══════════════════════════════════════════
// Phase 8: 终审 — 摘要多轮打磨（统一）→ 格式分支（LaTeX/Markdown）
// ═══════════════════════════════════════════
phase("终审")

const abstractSection = paperSections.find(s => s.id === "abstract" || s.section === "摘要")
let polishedAbstract = abstractSection?.content || ""

// ── Step 8.0: 摘要数字溯源验证 ──
// Phase 7 交叉审查已覆盖摘要的符号/数据/创新呼应等维度。
// 这里只做 Phase 7 做不到的事：结构化提取每个数字 → 逐在正文搜索出处。
{
  const bodyText = paperSections.filter(s => s.id !== "abstract" && s.section !== "摘要").map(s => s.content || "").join("\n")
  const abstractVerify = await agent(
    "## 摘要数字溯源验证\n\n" +
    "## 摘要\n" + polishedAbstract + "\n\n" +
    "## 正文全文\n" + bodyText.slice(0, 15000) + "\n\n" +
    "## 任务\n" +
    "1. 从摘要中提取所有**具体数字**（百分比、数值、时间等），忽略序号和年份\n" +
    "2. 逐一在正文中搜索每个数字的出处/推导过程\n" +
    "3. 输出 JSON：{\"claims\": [{\"number\": \"11.1%\", \"context\": \"...\", \"foundInBody\": true/false, \"bodyLocation\": \"第X节 或 未找到\"}]}\n" +
    "4. 如果 foundInBody=false → 这个数字是凭空编造的，必须删除或补推导\n\n" +
    "Structured output only.",
    { label: "abstract-verify", phase: "终审",
      schema: { type: "object", required: ["claims"], properties: { claims: { type: "array", items: { type: "object", required: ["number", "foundInBody"], properties: { number: { type: "string" }, context: { type: "string" }, foundInBody: { type: "boolean" }, bodyLocation: { type: "string" } } } } } } }
  )
  if (abstractVerify) {
    const unverifiable = (abstractVerify.claims || []).filter(c => !c.foundInBody)
    if (unverifiable.length > 0) {
      log("摘要数字验证: " + unverifiable.length + " 个数字在正文中找不到出处! 修复...")
      const fixedAbstract = await agent(
        "## 摘要数字修复\n\n" +
        "## 当前摘要\n" + polishedAbstract + "\n\n" +
        "## 以下数字在正文中找不到出处，必须删除或替换为正文中已有的数据：\n" +
        unverifiable.map(c => "- **" + c.number + "**: " + (c.context || "无上下文")).join("\n") + "\n\n" +
        "## 正文中可用的数据（从正文提取的可靠数字）\n" +
        "如果某个数字在正文中不存在，请从以下正文片段中找最接近的可靠数据替换，或者直接删除那句声称。\n\n" +
        bodyText.slice(0, 8000) + "\n\n" +
        "输出修复后的完整摘要（纯文本，300-500字）。只删除/替换不可溯源的数字，不重写其他部分。" + saveToFile("06-final/abstract-fixed.txt"),
        { label: "abstract-fix", phase: "终审" }
      )
      if (fixedAbstract) { polishedAbstract = fixedAbstract; log("摘要已修复: 移除/替换了 " + unverifiable.length + " 个不可溯源数字") }
    } else {
      log("摘要数字验证: 全部 " + (abstractVerify.claims || []).length + " 个数字可溯源 ✓")
    }
  }
}

// ── Step 8.1: 替换 paperSections 中的摘要 → 构建全文 ──
if (abstractSection) {
  abstractSection.content = polishedAbstract
}
const fullPaperMdBody = paperSections.map(s => "## " + s.section + "\n\n" + (s.content || "")).join("\n\n---\n\n")

// ── Step 8.2: 评委终审（Phase 7 交叉审查已覆盖一致性检查，这里只做整体评估）──
const judgeReview = await agent(
  "## 评委视角终审\n\n" +
  "你是数学建模竞赛评委，已读了100篇同题论文。读完以下论文后回答：\n\n" +
  "## 论文\n" + fullPaperMdBody.slice(0, 15000) + "\n\n" +
  "## 问题\n" +
  "1. 这篇和另外100篇摆在一起，我为什么会对它**有印象**？（找不到就说无，建议在哪里做深/做奇创造记忆点）\n" +
  "2. 创新是否真实可信？还是看起来像硬贴的？\n" +
  "3. 最大弱点是什么？（不能是废话，要具体的）\n" +
  "4. 你给这篇打什么等级？（国一/国二/省一/省二/省三）给理由。\n" +
  "5. 修改**哪一个**东西能最大程度提升竞争力？\n\n" +
  "返回纯文本，坦诚直接。" + saveToFile("06-final/judge-review.txt"),
  { label: "judge-review", phase: "终审" }
)

// ═══ 格式分支：LaTeX 或 Markdown ═══
let finalPaperMd = ""
let texFilePath = ""
let pdfFilePath = ""

// ═══ Shared return-value builders (used by both LaTeX and Markdown paths) ═══
const buildMetadata = (format) => ({
  mode: MODE, problem: selection?.selected, approach: finalModel?.approach,
  iterations: iteration,
  totalIssues: allIssues.length,
  criticalIssues: allIssues.filter(i => i.severity === "critical").length,
  sections: paperSections.length,
  format,
  baselineComparison: baselineResult ? { significance: baselineResult.significance, summary: baselineResult.summary } : null,
  abstractRounds: cfg.abstractRounds,
})
const buildDetails = () => ({
  analyses, selection,
  sources: allSources.map(s => ({ url: s.url, quality: s.sourceQuality, modelCount: (s.models || []).length })),
  finalModel, solution: currentSolution, allIssues, iterationLog,
  limitationAnalysis: typeof limitationAnalysis === "string" ? limitationAnalysis : null,
  baselineResult,
  narrativeOutline: typeof narrativeOutline === "string" ? narrativeOutline : null,
  crossSectionReview: typeof crossSectionReview === "string" ? crossSectionReview : null,
  earlyJudgeReview: typeof earlyJudgeReview === "string" ? earlyJudgeReview : null,
  consistencyIssues: [],  // Phase 7 交叉审查已覆盖一致性检查
  formatNotes: null,
  judgeReview: typeof judgeReview === "string" ? judgeReview : null,
})
const buildStats = () => ({
  problemsAnalyzed: analyses.length, sourcesFetched: allSources.length,
  modelsReferenced: allModels.length, proposalsGenerated: innovationProposals.length, solveIterations: iteration,
  issuesFound: allIssues.length, sectionsWritten: paperSections.length,
  baselineMetrics: baselineResult?.metrics?.length || 0,
})

if (cfg.latexOutput) {
  // ── LaTeX 路径 ──
  // CUMC 2025 规范：电子版第一页 = 摘要专用页（无承诺书、无编号页）
  // 页码从摘要页起算第 1 页，页脚居中

  const TITLE = selection?.selected
    ? ("全国大学生数学建模竞赛" + selection.selected + "题")
    : "数学建模论文"

  const preamble = [
    "\\documentclass[12pt,a4paper]{ctexart}",
    "\\usepackage{amsmath,amssymb,amsthm}",
    "\\usepackage{graphicx,float}",
    "\\usepackage{booktabs,array,multirow}",
    "\\usepackage{geometry}",
    "\\geometry{top=2.5cm,bottom=2.5cm,left=2.5cm,right=2.5cm}",
    "\\usepackage{fancyhdr}",
    "\\pagestyle{fancy}",
    "\\fancyhf{}",
    "\\fancyfoot[C]{\\thepage}",
    "\\renewcommand{\\headrulewidth}{0pt}",
    "\\usepackage{hyperref}",
    "\\hypersetup{colorlinks=true,linkcolor=black,citecolor=black,urlcolor=black}",
    "\\usepackage{cite}",
    "\\usepackage{listings}",
    "\\lstset{basicstyle=\\ttfamily\\small,breaklines=true,frame=single,numbers=left}",
    "\\usepackage[titletoc]{appendix}",
    "",
    "\\title{" + TITLE + "}",
    "\\date{}",
    "",
    "\\begin{document}",
    "\\maketitle",
    "\\setcounter{page}{1}",
    "",
  ].join("\n")

  const bodySections = paperSections
    .filter(s => s.id !== "abstract" && s.section !== "摘要")
    .map(s => s.content || "")
    .join("\n\n")

  // 从摘要中提取关键词（摘要末尾的 "关键词：..." 行）
  const kwMatch = polishedAbstract.match(/关键词[：:]\s*(.+?)(?:\n|$)/s)
  const keywords = kwMatch ? kwMatch[1].trim() : ""
  const abstractBody = keywords ? polishedAbstract.replace(/关键词[：:]\s*.+$/s, "").trim() : polishedAbstract

  let texContent = (
    preamble +
    "\\begin{abstract}\n" + abstractBody + "\n\\end{abstract}\n\n" +
    (keywords ? "\\noindent\\textbf{关键词：}" + keywords.replace(/[；;]/g, "；") + "\n\n\\newpage\n\n" : "\\newpage\n\n") +
    bodySections +
    "\n\n\\newpage\n" +
    "\\begin{appendices}\n" +
    "\\section{支撑材料清单}\n" +
    "建模过程中生成的全部图表、数据文件和源程序代码。详见 `" + outputDir + "/code/` 和 `" + outputDir + "/figures/` 目录。\n\n" +
    "\\section{源程序代码}\n" +
    "以下为建模求解所用全部完整可运行的源程序代码（CUMC 规范第5条要求）。\n\n" +
    "\\end{appendices}\n" +
    "\\end{document}\n"
  )

  // ── LaTeX 编译 ──
  texFilePath = outputDir + "/paper/paper.tex"

  const compileResult = await agent(
    "## LaTeX 排版编译\n\n" +
    "## 任务\n" +
    "1. 将完整 LaTeX 源码写入文件 `" + texFilePath + "`：\n" +
    "先用 `mkdir -p " + outputDir + "` 创建目录。\n\n" +
    "```latex\n" + texContent.slice(0, 30000) + "\n```\n" +
    (texContent.length > 30000 ? "(LaTeX 源码共计 " + texContent.length + " 字符，已截断至前 30000。⚠️ 写入文件后必须在末尾补齐 `\\end{document}`，否则编译必然失败。)\n" : "") +
    "\n2. 从 `" + codeDir + "` 目录读取所有 .py/.m/.jl 源程序文件，将其内容嵌入附录 `\\section{源程序代码}` 中（每个文件用一个 `\\subsection{文件名}` + `\\begin{lstlisting}...\\end{lstlisting}`）。如果目录为空或没有代码文件，在附录中写"本论文没有用到程序"（CUMC 规范第5条要求）。\n\n" +
    "3. 编译：\n```bash\ncd " + outputDir + " && xelatex -interaction=nonstopmode -file-line-error paper.tex 2>&1 | tail -100\n```\n\n" +
    "4. 如果出现 LaTeX 错误，分析错误原因并修正 .tex 文件，然后重新编译。最多重试 " + cfg.latexMaxRetries + " 次。\n\n" +
    "5. 常见 LaTeX 错误及修复方法：\n" +
    "   - `Undefined control sequence` → 命令拼写错误或缺少 \\usepackage\n" +
    "   - `Missing $ inserted` → 数学符号（_ ^ \\alpha 等）需在数学模式中使用\n" +
    "   - `Missing \\endgroup` → 环境未正确闭合\n" +
    "   - `File not found` → \\includegraphics 引用的图片路径不正确\n" +
    "   - 中文显示为乱码 → 确保使用 ctexart 文档类，用 xelatex 编译\n" +
    "   - 附录中代码含特殊字符（_ ^ % & 等）→ 用 listings 的 `basicstyle=\\ttfamily` 可避免大部分问题\n\n" +
    "6. 每次修复后重新编译验证。\n\n" +
    "返回：最终编译状态、PDF 是否成功生成、如有残留 warning 也列出来。" + saveToFile("08-compile-result.txt"),
    { label: "compile", phase: "终审" }
  )

  pdfFilePath = outputDir + "/paper/paper.pdf"
  log("LaTeX 编译完成 → " + pdfFilePath)

  finalPaperMd = texContent

  return {
    paper: finalPaperMd,
    texPath: texFilePath,
    pdfPath: pdfFilePath,
    compileResult: typeof compileResult === "string" ? compileResult : "",
    metadata: buildMetadata("latex"),
    details: buildDetails(),
    stats: buildStats(),
  }
}

// ═══ Markdown 路径 (quick / no latex) ═══

const mdAbstractSection = paperSections.find(s => s.id === "abstract" || s.section === "摘要")
const mdAbstract = polishedAbstract || mdAbstractSection?.content || ""
const mdKwMatch = mdAbstract.match(/关键词[：:]\s*(.+?)(?:\n|$)/s)
const mdAbstractBody = mdKwMatch ? mdAbstract.replace(/关键词[：:]\s*.+$/s, "").trim() : mdAbstract
const mdKeywords = mdKwMatch ? mdKwMatch[1].trim() : ""

finalPaperMd = [
  "# " + (selection?.selected || "数学建模论文"),
  "",
  "**摘要：** " + mdAbstractBody,
  (mdKeywords ? "\n\n**关键词：** " + mdKeywords : ""),
  "",
  ...paperSections.filter(s => s.id !== "abstract" && s.section !== "摘要").map(s => "## " + s.section + "\n\n" + s.content),
  "",
  "## 附录",
  "",
  "### 支撑材料清单",
  "建模过程中生成的全部图表、数据文件和源程序代码。详见 `" + codeDir + "` 和 `" + figuresDir + "` 目录。",
  "",
  "### 源程序代码",
  "以下为建模求解所用全部完整可运行的源程序代码（CUMC 规范第5条要求）。详见 `" + codeDir + "` 目录。",
  "> 注：quick 模式不自动嵌入代码。如需嵌入，复制 `" + codeDir + "` 下的文件内容至此附录。",
].join("\n\n")

return {
  paper: finalPaperMd,
  metadata: buildMetadata("markdown"),
  details: buildDetails(),
  stats: buildStats(),
}
