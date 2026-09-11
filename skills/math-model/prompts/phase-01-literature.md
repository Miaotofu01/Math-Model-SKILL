# 阶段模板 01：文献调研（literature）

> 你是本小问的文献调研 agent，本模板定义你要做的全部工作。

> 工具纪律（减回合）：四个角度的检索词一次全部发出（不逐条等待），精读 WebFetch 批量抓取；引用登记一次写完。

> 公共纪律见 `_common.md`（壳与模板一并注入）。

## 规范引用

规范引用：先 Read `<技能根>/docs/writing-and-format.md`（技能根见 `_common.md` §2.7）。本节相关：§1-10 文献引用支撑（参考文献按 GB/T 7714，正文 `\cite` 标注）、§5 创新链条（文献局限分析是 Gap 的合法来源）。引用规范，不复制内容。

## 输入

- `intermediates/00-problem.json`：题目原文全文（problem.description，必读）
- `intermediates/00-problem.json`：结构化分析（domain、mathType、各小问 objectives、keyChallenges）
- `pool/literature-pool.md`：共享文献池（首问可能不存在）

## 执行步骤

### 1. 构造检索词

从 00-problem.json 取领域 domain 与各小问 objectives，按 4 个角度构造检索词（可自行优化措辞）：

1. 前沿学术：domain + recent advances + mathematical model + arxiv + 近两年
2. 海外方法：domain + 前 3 个 objectives + state-of-the-art methods review（英文优先）
3. 中文核心：domain + mathType + 数学建模 论文
4. 开源代码：主 mathType + modeling solution + github + python

### 2. 首问全量 / 后续补检索

- `pool/literature-pool.md` 不存在或为空 → 本问全量执行 4 个角度的搜索。
- 池已存在 → 先 Read 池：提取与本问相关的既有条目与已覆盖主题，**只对本问新增主题/角度做补充搜索**（通常 1-2 个角度），不重复劳动。

### 3. 执行搜索

每个角度用 WebSearch（可优化搜索词）返回 4-6 条最相关结果。优先学术论文、技术博客、GitHub；跳过 SEO 垃圾。每条标注相关性 high/medium/low；跨角度按 URL 去重，重复只保留相关性最高的一条。

### 4. 精读与提取

对选中的来源用 WebFetch 获取页面内容（精读预算约 8 篇，按相关性从高到低分配）：

1. 评估来源质量：primary / secondary / blog / forum / unreliable
2. 提取 2-5 条与建模相关的 claim，附原文引用（quote）与重要性（central / supporting / tangential）
3. 提取可复用的数学模型：名称、描述、公式、参数、假设、适用条件、预处理方法
4. 无法访问 / 付费墙 / 不相关 → 按 §4b 分级处理：能拿到摘要 → 标 L2 并摘录摘要明确陈述；只有元数据 → 标 L3（仅存在性提及）；确实不可验证 → claims 留空、来源质量标 unreliable（L4，禁止进参考文献）

### 4b. 证据分级与取文回退链（硬规则）

**证据分级**（每条来源登记时必须标级；级别只表示「能读到什么」，与权威性正交）：

| 级别 | 定义 | 允许用途 |
|---|---|---|
| L1 | 全文可得（OA 全文 / 预印本 / 官网全文 / 社区复现仓库或博客） | 支撑方法选择、数值锚点、结论对比 |
| L2 | 摘要级（abstract + 元数据可读） | 可引用摘要明确陈述的内容；数值须标「摘要级」 |
| L3 | 元数据级（仅标题/DOI/卷期页） | **只能作存在性提及**，不得支撑数值或方法 |
| L4 | 不可验证 | **禁止进参考文献** |

另用**来源性质**标注权威性：`同行评审` / `预印本` / `社区复现（非同行评审）` / `命题人·教学期刊`。规则是**可引用 + 标注级别**，不是禁止引用付费文献（整体删掉会让参考文献变薄、丢掉权威源）；但**数值锚点必须标注来源性质**（同行评审值 / 社区复现值）。

**取文回退链（按序尝试，命中即停，不硬闯付费墙）**：OA 优先（arXiv / OpenAlex OA（`is_oa` + `best_oa_location.pdf_url`）/ PMC / DOAJ）→ 作者版·预印本（Semantic Scholar `openAccessPdf`、机构仓储）→ 摘要级（OpenAlex `abstract_inverted_index` 重建摘要、期刊官网、SCITEPRESS）→ 元数据级（OpenAlex / Crossref 补 DOI + 卷期页）→ 社区复现（GitHub/blog，明确标非同行评审）→ 仍拿不到 → 按上表降级标注，并在登记表写明卡在哪一步。

**接口要点（已踩坑，勿重复试）**：OpenAlex 必须带 `mailto`；Unpaywall 需真实邮箱（`test@example.com` 会 422）；**中文 DOI 在 Crossref/OpenAlex 均 404** → 走 `doi.org` → chndoi + 期刊官网（官网通常免费给完整摘要/关键词/参考文献表，全文需登录 → 上限 L2）；部分站点可达性不稳（一次超时一次成功）→ 重试 1 次。

**检索式偏好**：OA 优先（`open access` / `site:arxiv.org` / `filetype:pdf` / diamond-gold OA 期刊）；综述优先（一篇可读综述可替代多篇付费原文，引用其观点并标 `[综述]`）；命题人·教学期刊优先（其方法框架往往就是本题标准解法）。

### 5. 局限分析（创新合法来源，必须有据）

以资深审稿人视角分析**标准/主流方法的局限**，逐小问给出 2-3 个关键局限，角度：假设过强（放宽会怎样）、精度瓶颈（什么条件下不够、为什么）、计算代价（高维/大规模）、泛化缺陷（本题目特定约束下失效、哪里不匹配）、方法冲突（文献间矛盾）。每个局限按「局限描述 → 为什么是问题 → 可能的改进方向」结构输出，必须引用上文文献中的具体方法支撑，不得泛泛而谈。

文献不足时：基于 00-problem.json 的 keyChallenges 与领域常识推断潜在局限，并明确注明「文献不足，局限为推断」。

### 6. 引用登记

在本问报告中登记每条精读来源：编号、**完整标题（不得截断，勿照抄检索结果的省略形态）**、作者、年份、来源类型、**DOI**、URL、获取日期、相关小问、**证据级（L1–L4）+ 来源性质**、关键 claim 摘要——供写作阶段按 GB/T 7714 整理参考文献（§1-10）。GB/T 7714 条目需要卷(期):页码，**IEEE/会议条目必须补 DOI 或卷期页**，缺失视为登记不合格。

### 7. 池核验（脚本，0 agent 回合，收尾跑一次）

```
python <技能根>/scripts/lit_verify.py --pool pool/literature-pool.md \
  --out intermediates/q{id}/01-literature/lit-verify.md \
  --json intermediates/q{id}/01-literature/lit-verify.json \
  --cache <outputDir>/.litcache --mailto <真实邮箱>
```

（`<技能根>` 见 `_common.md` §2.7）产出核验表（编号 / 完整标题 / DOI / 元数据命中 / OA 状态 / 证据级建议 / URL 状态）+ **池数据缺陷**（标题截断、缺 DOI、URL 失效）。**按核验结果回填本问产物与池**：补 DOI 与卷期页、修正截断标题、把「付费墙 → unreliable」改成实际可达级别（**逐条核验后再定级**，不要按粗判直接降级；案例依据见仓库 `docs/prompt-audit-2026-09-11.md` §16）。首问跑全量；后续小问只对本次新增条目补核验。

## 产物

- `intermediates/q{id}/01-literature/literature.md`（主产物）：检索过程 → 精读结果（来源/claims/可复用模型/证据级）→ 局限分析 → 引用登记表
- `intermediates/q{id}/01-literature/lit-verify.md` + `lit-verify.json`（池核验表：DOI/OA/证据级/URL 状态 + 池数据缺陷）
- `pool/literature-pool.md`：共享池。首问创建；后续小问**追加**本次新来源（标题+URL+角度+相关性+精读摘要+局限要点），不覆盖已有条目

## 完成标准

- 每个小问至少 2-3 条相关来源；确实搜不到（如小众机理题）→ 如实记录，以推断局限交付，不算失败
- 每条来源有证据级（L1–L4）与来源性质；无 DOI / 核验失败条目为 0（不可得者必须写明卡在哪一步）
- 全部检索词、来源、局限、引用登记可追溯
- 文献总量极少（无可用来源）→ 在 literature.md 写明，正常返回 PASS（局限基于题面推断），供后续阶段降级处理
