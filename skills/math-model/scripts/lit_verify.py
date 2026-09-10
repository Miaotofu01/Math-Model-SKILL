#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lit_verify.py —— 文献池批量核验（math-model skill · 阶段 01 配套脚本，仅标准库）

用途：把「逐条 WebFetch 核验文献池」的几十个 agent 回合压成一次脚本运行。读取 Markdown 文献池
（条目编号 S1/S2/…），对每条走六条链路，产出 Markdown 主表 + 缺陷区 + 可选 JSON：
  1. DOI 解析  https://doi.org/<doi>（跟随重定向，记录最终 URL / Content-Type）
  2. OpenAlex  works/https://doi.org/<doi>；无 DOI 用标题检索（标题可能被截断 → 前缀/包含匹配）
  3. Crossref  works/<doi>（中文 DOI 404 属正常，记 not_found）
  4. Semantic Scholar  paper/DOI:<doi> 与 paper/search（无 key 会 429 → 记 rate_limited 继续）
  5. URL 状态  HEAD → 失败退回 GET(Range: bytes=0-2047)；IEEE 202 空响应、DTIC 非 PDF 如实记录
  6. arXiv     export.arxiv.org/api/query（URL/DOI 含 arXiv 时），解析 XML 取标题与 PDF 可得性
HTTP 响应按 URL 哈希落盘缓存（含失败结果），重跑零网络请求。社区复现条目（GitHub/博客，
无 DOI）跳过两库标题检索：它们本就不是可检索的学术条目。用法：
  /usr/bin/python3 skills/math-model/scripts/lit_verify.py --pool POOL.md [--out REPORT.md]
      [--json OUT.json] [--mailto EMAIL] [--timeout 20] [--retries 2] [--only S3,S14]
      [--workers 6] [--cache DIR]
--mailto 或环境变量 LIT_MAILTO 提供 OpenAlex 礼貌池邮箱；缺失时报告警告可能 403 并继续跑其它源。
退出码：0 = 跑完（无论条目好坏）；2 = 参数/输入不可读等致命错误（核验失败不算致命）。

证据分级：L1 有全文（OA 全文 PDF / arXiv 预印本 PDF / 池内 URL 直链 PDF / 社区复现仓库·博客全文可读）；
L2 只有摘要（OpenAlex abstract_inverted_index 重建、S2 abstract、官网落地页摘要）；L3 只有元数据
（标题/DOI/卷期页，无摘要）；L4 不可验证（无 DOI、URL 失效且无元数据命中）。来源性质：同行评审 /
预印本 / 社区复现（非同行评审）/ 命题人·教学期刊 / 待人工（启发式，判据不足不猜）。
容错：单点失败只影响该条该源，解析不到的字段留空记 unknown，不抛异常。
局限：TLS 校验不降级为不校验；arXiv 链路按 URL/DOI 文本启发式触发。
"""
from __future__ import annotations

import argparse, base64, concurrent.futures as futures, difflib, hashlib, json, os, re, sys
import tempfile, threading, time, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape

VERSION = "1.0"
UA_BASE = "math-model-lit-verify/" + VERSION
MAX_BACKOFF = 2.0
HOST_SPACING = {"api.openalex.org": 0.34, "api.crossref.org": 0.2, "doi.org": 0.3,
                "api.semanticscholar.org": 0.5, "export.arxiv.org": 0.5}
RETRY_CODES = {429, 500, 502, 503, 504}
COMMUNITY_HOSTS = ("github.com", "raw.githubusercontent.com", "gitee.com", "gitcode.com", "cnblogs.com",
                   "csdn.net", "zhihu.com", "juejin.cn", "segmentfault.com", "medium.com", "substack.com")
PREPRINT_HOSTS = ("arxiv.org", "biorxiv.org", "medrxiv.org", "ssrn.com", "preprints.org", "osf.io",
                  "techrxiv.org", "researchsquare.com")
PUBLISHER_HOSTS = ("ieeexplore.ieee.org", "dl.acm.org", "mdpi.com", "link.springer.com", "sciencedirect.com",
                   "onlinelibrary.wiley.com", "tandfonline.com", "spiedigitallibrary.org", "computer.org",
                   "scitepress.org", "tlr-journal.com", "jsuese.scu.edu.cn", "cjournal.hep.com.cn",
                   "cqvip.com", "opticsjournal.net", "chndoi.org", "springer.com", "nature.com", "sagepub.com")
TEACHING_HINTS = ("数学建模及其应用", "数学的实践与认识", "数学建模", "mathematical modeling and algorithm application")
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>()\[\]，,；;、]+")
ARXIV_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5}|[a-z\-]+/\d{7})|"
                      r"10\.48550/arxiv\.([0-9]{4}\.[0-9]{4,5})", re.I)
TRUNC_END_OK = set(".!?。！？;；,，:：'\")]}）】》")
STOP_LABEL = re.compile(r"关键词|关键字|Key\s?words|引用本文|参考文献|References|Citation|Publication Keywords|"
                        r"Download|Share|All rights|Cookie", re.I)
BAD_ABSTRACT = re.compile(r"中图分类号|学科分类号|高级检索|Access Denied|Just a moment|robots")
POOL_FLAG = re.compile(r"未精读|标题级|付费墙|抓取失败|空页|不可得|JS 渲染|仅题名|元数据级|403")
_LOCK, _STATS, _LAST_HIT = threading.Lock(), {"net": 0, "cache": 0}, {}

# ------------------------------------------------------------------ 网络层

def _ascii_url(url: str) -> str:
    """非 ASCII（中文路径）URL 百分号编码，否则 urllib 抛 UnicodeEncodeError。"""
    p = urllib.parse.urlsplit((url or "").strip())
    if p.scheme not in ("http", "https"):
        return (url or "").strip()
    return urllib.parse.urlunsplit((p.scheme, p.netloc,
                                    urllib.parse.quote(p.path, safe="/%:@!$&'()*+,;=~"),
                                    urllib.parse.quote(p.query, safe="=&%:@!$'()*+,;/?~"), p.fragment))


def _host_wait(url: str) -> None:
    """同主机最小请求间隔，降低 OpenAlex / S2 的 429 概率。"""
    host = urllib.parse.urlsplit(url).netloc
    with _LOCK:
        last, now = _LAST_HIT.get(host), time.monotonic()
        wait = 0.0 if last is None else max(0.0, HOST_SPACING.get(host, 0.05) - (now - last))
        _LAST_HIT[host] = now + wait
    if wait > 0:
        time.sleep(wait)


def _backoff(attempt: int, headers: dict | None) -> None:
    delay = min(MAX_BACKOFF, 0.5 * (2 ** attempt))
    raw = (headers or {}).get("retry-after")
    if raw:
        try:
            delay = max(delay, min(MAX_BACKOFF, float(raw)))
        except ValueError:
            try:
                delay = max(delay, min(MAX_BACKOFF,
                                       (parsedate_to_datetime(str(raw)) - datetime.now(timezone.utc)).total_seconds()))
            except Exception:
                pass
    time.sleep(max(0.0, min(MAX_BACKOFF, delay)))


def fetch(url: str, *, method: str = "GET", headers: dict | None = None, timeout: float = 20,
          retries: int = 2, cache: str | None = None, read_limit: int = 65536, mailto: str = "") -> dict:
    """所有源的唯一 HTTP 出口 → {status, headers, body(bytes), final_url, error, from_cache}。

    status=None 表示连接层失败（error 非空）。cache 目录按 (method,url,Range) 哈希持久化响应，
    连失败结果一起缓存，保证重跑走缓存、不再发请求；单点失败只返回错误串，不抛异常。
    """
    url = _ascii_url(url)
    hdrs = {"User-Agent": UA_BASE + (f" (mailto:{mailto})" if mailto else ""), "Accept": "*/*"}
    hdrs.update(headers or {})
    key = f"{method} {url} {hdrs.get('Range', '')} limit={read_limit}"   # read_limit 进键：否则 2KB 小读会截断后续 400KB 落地页抓取
    cpath = os.path.join(cache, hashlib.sha256(key.encode()).hexdigest()[:40] + ".json") if cache else None
    if cpath and os.path.exists(cpath):
        try:
            with open(cpath, encoding="utf-8") as fh:
                res = json.load(fh)
            with _LOCK:
                _STATS["cache"] += 1
            return {"status": res["status"], "headers": res.get("headers") or {},
                    "body": base64.b64decode(res.get("body") or ""), "final_url": res.get("final_url") or url,
                    "error": res.get("error"), "from_cache": True}
        except Exception:
            pass  # 缓存损坏 → 重新请求
    res = {"status": None, "headers": {}, "body": b"", "final_url": url, "error": None, "from_cache": False}
    attempt = 0
    while True:
        _host_wait(url)
        try:
            with _LOCK:
                _STATS["net"] += 1
            with urllib.request.urlopen(urllib.request.Request(url, headers=hdrs, method=method), timeout=timeout) as r:
                res.update(status=r.status, headers={k.lower(): v for k, v in r.headers.items()},
                           body=b"" if method == "HEAD" else r.read(read_limit), final_url=r.geturl(), error=None)
            break
        except urllib.error.HTTPError as e:
            try:
                body = e.read(4096)
            except Exception:
                body = b""
            hh = {k.lower(): v for k, v in (e.headers or {}).items()}
            res.update(status=e.code, headers=hh, body=body, final_url=e.geturl() or url, error=f"HTTP {e.code}")
            if e.code in RETRY_CODES and attempt < retries:
                _backoff(attempt, hh)
                attempt += 1
                continue
            break
        except Exception as e:  # URLError / timeout / SSL / Unicode …
            res.update(status=None, headers={}, body=b"", final_url=url, error=f"{type(e).__name__}: {str(e)[:110]}")
            if attempt < retries:
                _backoff(attempt, None)
                attempt += 1
                continue
            break
    if cpath:
        try:
            os.makedirs(cache, exist_ok=True)
            with open(cpath + ".tmp", "w", encoding="utf-8") as fh:
                json.dump({"url": url, "method": method, "status": res["status"], "headers": res["headers"],
                           "body": base64.b64encode(res["body"]).decode("ascii"), "final_url": res["final_url"],
                           "error": res["error"], "ts": datetime.now(timezone.utc).isoformat()}, fh)
            os.replace(cpath + ".tmp", cpath)
        except Exception:
            pass
    return res


def _status_word(code: int | None) -> str:
    return {200: "ok", 404: "not_found", 429: "rate_limited", None: "error"}.get(code, f"http_{code}")


def api(url: str, cfg: "Config") -> tuple[str, object]:
    """GET JSON → (status_word, 对象或 None)；异常一律收敛成状态字符串。

    read_limit 放大到 4MB：OpenAlex 检索响应带 abstract_inverted_index 时可能远超 64KB，
    截断的 JSON 会被误判成「无命中」。
    """
    r = fetch(url, timeout=cfg.timeout, retries=cfg.retries, cache=cfg.cache, mailto=cfg.mailto,
              read_limit=4_000_000)
    if r["status"] == 200 and r["body"]:
        try:
            return "ok", json.loads(r["body"].decode("utf-8", "replace"))
        except Exception:
            return "json_error", None
    return _status_word(r["status"]), None


# ------------------------------------------------------------------ 文本工具

def _field(block: str, names: tuple[str, ...]) -> str:
    for n in names:
        m = re.search(rf"^[>\-*\s]*\**\s*{re.escape(n)}\**\s*[:：]\s*(.+)$", block, re.M)
        if m:
            return m.group(1).strip().strip("*").strip()
    return ""


def clean_doi(raw: str) -> str:
    d = re.sub(r"^doi[:：]?\s*", "", re.sub(r"^(?:https?://)?(?:dx\.)?doi\.org/", "", (raw or "").strip(),
                                            flags=re.I), flags=re.I)
    d = d.strip().strip("<>").rstrip(".,;；、)）]】")
    return d if DOI_RE.fullmatch(d) else ""


def find_doi(*texts: str) -> str:
    """兼容 `DOI: 10.x/y`、`DOI：`、`doi.org/10.x`、`https://doi.org/10.x` 与裸 DOI。"""
    for t in texts:
        if not t:
            continue
        m = (re.search(r"DOI\s*[:：]\s*(10\.\d{4,9}/\S+)", t, re.I)
             or re.search(r"doi\.org/(10\.\d{4,9}/\S+)", t, re.I) or DOI_RE.search(t))
        if m:
            d = clean_doi(m.group(1) if m.re.groups else m.group(0))
            if d:
                return d
    return ""


def strip_venue(title: str) -> str:
    """去掉作者前缀、尾部「期刊/会议 + 年卷页」、DOI 与括号注解，留下题名主体。"""
    t = re.sub(r"DOI\s*[:：]?\s*10\.\S+|doi\.org/\S+", " ", title or "", flags=re.I)
    t = re.sub(r"\s*(\d{6,})\s*$", " ", re.sub(r"\s*(\d{6,})\)\s*$", ")", t))  # IEEE 文献号
    t = re.sub(r"\s*[（(【\[][^（()）\[\]【】]*[)）】\]]\s*$", " ", t)
    for _ in range(2):
        t = re.sub(r"[.。]\s*[A-Z][A-Za-z&.\- ]{2,60}(?:\s*,?\s*\d{4}[^.]*)?$", " ", t)
    t = re.sub(r"^\s*[A-Z][A-Za-z.\-']+(?:\s*(?:,|&|and)\s*[A-Z][A-Za-z.\-']+)*\s*[.。]\s+", "", t)
    return re.sub(r"\s+", " ", t).strip(" .;；,，-—")


def query_title(title: str) -> str:
    """检索串：中文题名取最长中文串（顺手去掉作者/刊名），英文走 strip_venue。"""
    core = strip_venue(title)
    cjk = re.findall(r"[\u4e00-\u9fff]{4,}", core)
    return max(cjk, key=len) if cjk and max(len(x) for x in cjk) >= 6 else core[:300]


def norm_title(s: str) -> str:
    """归一化题名用于匹配；顺带展开 UAV 这类别名（池内常写 UAVs、权威题名写 Unmanned Aerial Vehicles）。"""
    t = re.sub(r"\buavs\b", "unmannedaerialvehicles", s or "", flags=re.I)
    t = re.sub(r"\buav\b", "unmannedaerialvehicle", t, flags=re.I)
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", t.lower())


def title_match(query_core: str, cand: str) -> tuple[float, str]:
    """(得分, 命中方式)；前缀/包含即命中 —— 池内标题被截断时仍能匹配。"""
    q, c = norm_title(query_core), norm_title(cand)
    if len(q) < 6 or len(c) < 6:
        return 0.0, ""
    if c.startswith(q):
        return 1.0, "prefix"
    if q in c:
        return 0.98, "contains"
    r = difflib.SequenceMatcher(None, q, c).ratio()
    return (r, f"similar:{r:.2f}") if r >= 0.92 else (0.0, "")


def truncation_suspect(raw_title: str, core: str) -> str:
    """标题疑似截断：含省略号，或长度 ≥90 且未以句号/字母数字收尾。"""
    for e in ("...", "…"):
        if e in raw_title:
            return f"标题含省略号（{e}）"
    t = core.strip()
    if len(t) >= 90 and t[-1] not in TRUNC_END_OK and not re.search(r"[0-9A-Za-z\u4e00-\u9fff]$", t):
        return f"长度 {len(t)} 且未以句号/字母数字收尾（结尾 {t[-8:]!r}）"
    return ""


def abstract_from_inverted(inv: object) -> str:
    """OpenAlex abstract_inverted_index → 摘要文本（位置倒排重建）。"""
    if not isinstance(inv, dict):
        return ""
    pos = {i: str(w) for w, idxs in inv.items() if isinstance(idxs, list) for i in idxs if isinstance(i, int)}
    return " ".join(pos[k] for k in sorted(pos))


def landing_meta(html: str) -> dict:
    """落地页（HEP / SCITEPRESS 等官网）可提供的元数据与摘要证据。"""
    metas: dict[str, str] = {}
    for tag in re.findall(r"<meta\b[^>]*>", html, re.I):
        attrs = {k.lower(): (a or b) for k, a, b in
                 re.findall(r"""([\w:.-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""", tag)}
        if attrs.get("name") or attrs.get("property"):
            metas.setdefault((attrs.get("name") or attrs["property"]).lower(), unescape(attrs.get("content", "")))
    abstract = ""
    for k in ("citation_abstract", "dc.description", "dcterms.abstract"):
        v = (metas.get(k) or "").strip()
        if len(v) >= 100 and not BAD_ABSTRACT.search(v):
            abstract = v
            break
    if not abstract:
        txt = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", re.sub(
            r"<(script|style|noscript)\b.*?</\1>", " ", html, flags=re.S | re.I)))).strip()
        best = ""
        for m in re.finditer(r"(?:Abstract|ABSTRACT|摘\s?要)\s*[:：]?", txt):
            seg = txt[m.end():m.end() + 1500]
            stop = STOP_LABEL.search(seg)
            seg = (seg[:stop.start()] if stop else seg).strip()
            if len(seg) > len(best) and not BAD_ABSTRACT.search(seg):
                best = seg
        abstract = best if len(best) >= 120 else ""
    return {"title": (metas.get("citation_title") or "").strip(), "doi": clean_doi(metas.get("citation_doi") or ""),
            "venue": (metas.get("citation_journal_title") or metas.get("citation_conference_title") or "").strip(),
            "abstract": re.sub(r"\s+", " ", abstract).strip()}


# ------------------------------------------------------------------ 池解析

def parse_pool(text: str) -> list[dict]:
    """宽松解析：`### S1 [高] 角度④ …` 小节式；也兼容 `| S1 | 标题 | URL |` 表格行。"""
    entries: list[dict] = []
    seen: set[str] = set()
    for blk in re.split(r"\n(?=#{2,6}\s)", text):
        head = blk.split("\n", 1)[0].strip()
        m = re.match(r"#{2,6}\s*\**\s*(S\d+)\**\s*(?:\[([^\]]*)\])?\s*(.*)$", head)
        if m:
            sid, rel, tag = m.group(1).upper(), m.group(2) or "", m.group(3).strip()
        else:
            row = next((ln for ln in blk.split("\n") if re.match(r"^\|\s*\**S\d+\**\s*\|", ln)), "")
            if not row:
                continue
            cells = [c.strip().strip("*") for c in row.strip().strip("|").split("|")]
            sid, rel, tag = cells[0].upper(), (cells[1] if len(cells) > 1 else ""), "表格行"
            blk = blk + "\n" + " ; ".join(cells[1:])
        if not re.fullmatch(r"S\d+", sid) or sid in seen:
            continue
        seen.add(sid)
        title = _field(blk, ("标题", "title", "题名", "论文"))
        url = _field(blk, ("URL", "链接", "url", "link"))
        if not url:
            mu = re.search(r"https?://\S+", blk)
            url = mu.group(0).rstrip(".,;；、)）") if mu else ""
        entries.append({"id": sid, "rel": rel, "tag": tag, "title_pool": title, "url": _ascii_url(url),
                        "doi_pool": find_doi(title, blk), "excerpt": _field(blk, ("精读摘要", "摘录", "摘要", "excerpt")),
                        "limits": _field(blk, ("局限要点", "局限", "notes"))})
    return sorted(entries, key=lambda e: int(e["id"][1:]))


# ------------------------------------------------------------------ 核验链

def _probe_url(url: str, cfg: "Config") -> dict:
    """HEAD → 失败/无信息退回 GET(Range: bytes=0-2047)。"""
    if not url:
        return {"status": None, "content_type": "", "content_length": "", "final_url": "", "error": "池内无 URL",
                "bytes": 0, "method": "-"}
    r = fetch(url, method="HEAD", timeout=cfg.timeout, retries=cfg.retries, cache=cfg.cache, mailto=cfg.mailto)
    method = "HEAD"
    # 连接层失败不做 GET 重试（同因必然再失败，白等超时）；仅 HTTP 层面的 HEAD 不受理才退回 GET
    if r["status"] in (400, 403, 405, 406, 501) or (r["status"] == 200 and not r["headers"].get("content-length")):
        g = fetch(url, method="GET", headers={"Range": "bytes=0-2047"}, timeout=cfg.timeout,
                  retries=cfg.retries, cache=cfg.cache, mailto=cfg.mailto)
        if g["status"] is not None:
            r, method = g, "GET"
    return {"status": r["status"], "content_type": (r["headers"].get("content-type") or "").split(";")[0].strip(),
            "content_length": r["headers"].get("content-length", ""), "final_url": r["final_url"],
            "error": r["error"], "bytes": len(r["body"]), "method": method}


def _openalex_work(w: object) -> dict:
    w = w if isinstance(w, dict) else {}
    loc, oa, bib = w.get("best_oa_location") or {}, w.get("open_access") or {}, w.get("biblio") or {}
    return {"title": (w.get("title") or "").strip(), "year": w.get("publication_year"),
            "doi": clean_doi(w.get("doi") or ""), "is_oa": oa.get("is_oa"), "oa_status": oa.get("oa_status") or "",
            "pdf_url": loc.get("pdf_url") or "", "oa_url": oa.get("oa_url") or "",
            "landing_url": loc.get("landing_page_url") or "",
            "venue": (((w.get("primary_location") or {}).get("source") or {}).get("display_name") or "").strip(),
            "abstract": abstract_from_inverted(w.get("abstract_inverted_index")),
            "biblio": {k: bib.get(k) for k in ("volume", "issue", "first_page", "last_page")}}


def _blank(ent: dict) -> dict:
    return {"id": ent["id"], "title_pool": ent["title_pool"], "title_full": ent["title_pool"], "doi": ent["doi_pool"],
            "url": ent["url"], "relevance": ent["rel"], "tag": ent["tag"],
            "openalex": {"hit": False, "status": "not_attempted", "query": ""},
            "crossref": {"hit": False, "status": "not_attempted"},
            "s2": {"hit": False, "status": "not_attempted"}, "doi_resolve": {}, "arxiv": {}, "landing": {},
            "url_probe": {}, "evidence_level": "L4", "source_nature": "待人工", "notes": [], "defects": []}


def verify_entry(ent: dict, cfg: "Config") -> dict:
    """一条文献的完整核验；单点失败只写进该条字段，不向上抛异常。"""
    rec, notes = _blank(ent), []
    rec["notes"] = notes
    doi, url = ent["doi_pool"], ent["url"]
    core = query_title(ent["title_pool"]) or strip_venue(ent["title_pool"])
    oa, cr, s2 = rec["openalex"], rec["crossref"], rec["s2"]
    mq = f"&mailto={urllib.parse.quote(cfg.mailto)}" if cfg.mailto else ""
    # 社区复现仓库/博客（GitHub、博客园…）不是可检索的学术条目，无 DOI 时跳过两库标题检索：
    # 省请求也避 429，且不会因「查不到」把全文可读的条目误判。
    community = any(h in url.lower() for h in COMMUNITY_HOSTS)
    if community and not doi:
        oa["status"] = s2["status"] = "skipped_community"

    # 1) DOI 解析
    if doi:
        r = fetch(f"https://doi.org/{urllib.parse.quote(doi)}", timeout=cfg.timeout, retries=cfg.retries,
                  cache=cfg.cache, mailto=cfg.mailto, read_limit=2048)
        rec["doi_resolve"] = {"status": r["status"], "final_url": r["final_url"], "error": r["error"],
                              "content_type": (r["headers"].get("content-type") or "").split(";")[0].strip()}
        if r["status"] is None:
            notes.append(f"doi.org 解析失败：{r['error']}")
        elif r["status"] >= 400:
            notes.append(f"doi.org 返回 {r['status']}（落地站点拒绝直连，DOI 本身可能仍有效）")
    else:
        rec["doi_resolve"] = {"status": "no_doi"}

    # 2) OpenAlex：有 DOI 走 DOI（便宜）；无 DOI 先靠 Crossref 书目检索定位 DOI，再回来按 DOI 查
    def oa_by_doi(d: str) -> None:
        oa["status_doi"], obj = api(f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(d)}"
                                    f"?mailto={urllib.parse.quote(cfg.mailto)}" if cfg.mailto else
                                    f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(d)}", cfg)
        oa["status"] = oa["status_doi"]
        if isinstance(obj, dict) and obj.get("id"):
            oa.update(_openalex_work(obj), hit=True)
        elif oa["status"] == "not_found":
            notes.append("OpenAlex 无此 DOI（中文库 DOI 常见，非错误）")

    def oa_by_title(query: str) -> None:
        oa["query"] = query
        if len(norm_title(query)) < 20:
            notes.append("检索串过短（<20 字符），跳过标题检索以免误命中同系列文献")
            oa["status"] = "query_too_short"
            return
        st, obj = api("https://api.openalex.org/works?search=" + urllib.parse.quote(query) + "&per_page=3" + mq, cfg)
        oa["status"] = st
        if st == "rate_limited":
            notes.append("OpenAlex 限流（429：search 端点有额度限制，建议 --mailto 并稍后重跑）")
        best = (0.0, "", None)
        for w in (obj or {}).get("results", []) if isinstance(obj, dict) else []:
            score, how = title_match(query, w.get("title") or "")
            if score > best[0]:
                best = (score, how, w)
        if best[2] is not None:
            oa.update(_openalex_work(best[2]), hit=True, match=best[1])
            notes.append(f"标题检索命中（{best[1]}）")
        elif st == "ok":
            notes.append("标题检索无命中（池内标题可能被截断或未被收录）")

    # 3) Crossref：DOI 直查，或（无 DOI / DOI 未注册）书目检索定位 DOI
    def cr_take(msg: dict, how: str = "") -> None:
        cr.update(hit=True, title=((msg.get("title") or [""])[0] or "").strip(),
                  container_title=((msg.get("container-title") or [""])[0] or "").strip(),
                  volume=msg.get("volume", ""), issue=msg.get("issue", ""), page=msg.get("page", ""),
                  published="-".join(str(x) for x in
                                     (((msg.get("published") or {}).get("date-parts") or [[""]])[0])),
                  match=how, doi=clean_doi(msg.get("DOI") or ""))

    def cr_by_title(query: str) -> str:
        """Crossref 书目检索 → 命中则返回 DOI（Crossref 无额度限制，OpenAlex search 有）。"""
        if len(norm_title(query)) < 20:
            return ""
        st, obj = api("https://api.crossref.org/works?rows=3&query.bibliographic=" +
                      urllib.parse.quote(query) + mq, cfg)
        cr["status_search"] = st
        best = (0.0, "", None)
        for w in ((obj or {}).get("message") or {}).get("items", []) if isinstance(obj, dict) else []:
            score, how = title_match(query, (w.get("title") or [""])[0])
            if score > best[0]:
                best = (score, how, w)
        if best[2] is not None:
            cr_take(best[2], best[1])
            notes.append(f"Crossref 书目检索定位 DOI（{best[1]}）")
            return cr["doi"]
        return ""

    if doi:
        oa_by_doi(doi)
        cr["status"], obj = api(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}", cfg)
        msg = (obj or {}).get("message") if isinstance(obj, dict) else None
        if isinstance(msg, dict):
            cr_take(msg)
        elif cr["status"] == "not_found":
            notes.append("Crossref 无此 DOI（中文 DOI 正常，记 not_found）")
        if not oa["hit"] and not cr["hit"]:  # DOI 两库皆无 → 书目检索找替代 DOI
            alt = cr_by_title(core)
            if alt and alt != doi:
                rec["doi"] = oa["doi"] = alt
                oa_by_doi(alt)
            elif oa["status_doi"] == "not_found":
                oa_by_title(core)
    elif core and not community:
        cr["status"] = "no_doi"
        alt = cr_by_title(core)
        if alt:
            rec["doi"] = oa["doi"] = alt
            oa_by_doi(alt)
        if not oa["hit"]:
            oa_by_title(core)
    else:
        cr["status"] = "no_doi"

    # 4) Semantic Scholar：DOI 端点；未命中/无 DOI → 标题检索
    def s2_take(w: dict, how: str = "") -> None:
        s2.update(hit=True, title=w.get("title") or "", year=w.get("year"), venue=w.get("venue") or "",
                  abstract=w.get("abstract") or "", external_doi=clean_doi((w.get("externalIds") or {}).get("DOI") or ""),
                  pdf_url=((w.get("openAccessPdf") or {}) or {}).get("url") or "")
        if how and how not in ("prefix", "contains"):
            notes.append(f"S2 标题检索相似命中（{how}）")

    rdoi = rec["doi"] or oa.get("doi") or ""
    if rdoi:
        s2["status"], obj = api("https://api.semanticscholar.org/graph/v1/paper/DOI:"
                                + urllib.parse.quote(rdoi) +
                                "?fields=title,abstract,openAccessPdf,year,venue,externalIds", cfg)
        if isinstance(obj, dict) and obj.get("title"):
            s2_take(obj)
    else:
        s2["status"] = "skipped_community" if community else "no_doi"
    if not s2["hit"] and core and not community:
        st, obj = api("https://api.semanticscholar.org/graph/v1/paper/search?query=" + urllib.parse.quote(core) +
                      "&limit=3&fields=title,year,venue,openAccessPdf,externalIds,abstract", cfg)
        s2["status_search"] = st
        if s2["status"] == "not_attempted":
            s2["status"] = st
        if st == "rate_limited":
            notes.append("Semantic Scholar 限流（429，无 key 常态）")
        best = (0.0, "", None)
        for w in (obj or {}).get("data", []) if isinstance(obj, dict) else []:
            score, how = title_match(core, w.get("title") or "")
            if score > best[0]:
                best = (score, how, w)
        if best[2] is not None:
            s2_take(best[2], best[1])

    # 5) arXiv
    m = ARXIV_RE.search(url) or ARXIV_RE.search(doi or "")
    if m:
        aid = m.group(1) or m.group(2)
        r = fetch(f"http://export.arxiv.org/api/query?id_list={urllib.parse.quote(aid)}", timeout=cfg.timeout,
                  retries=cfg.retries, cache=cfg.cache, mailto=cfg.mailto)
        ax_title, ax_pdf = "", False
        if r["status"] == 200 and r["body"]:
            try:
                ns = {"a": "http://www.w3.org/2005/Atom"}
                e = ET.fromstring(r["body"].decode("utf-8", "replace")).find("a:entry", ns)
                if e is not None:
                    ax_title = re.sub(r"\s+", " ", (e.findtext("a:title", "", ns) or "")).strip()
                    ax_pdf = any(l.get("title") == "pdf" for l in e.findall("a:link", ns))
            except Exception as ex:
                notes.append(f"arXiv XML 解析失败：{type(ex).__name__}")
        rec["arxiv"] = {"id": aid, "status": r["status"], "title": ax_title, "pdf": ax_pdf,
                        "abs_url": f"https://arxiv.org/abs/{aid}"}

    # 6) URL 状态（HEAD → GET Range）；拿不到 OA/摘要且 URL 是 HTML 时补抓一次落地页找摘要证据
    p = rec["url_probe"] = _probe_url(url, cfg)
    host = urllib.parse.urlsplit(p.get("final_url") or url).netloc.lower()
    community = any(h in host or h in url.lower() for h in COMMUNITY_HOSTS)
    if p["status"] in (200, 206) and "html" in (p["content_type"] or "") and \
            urllib.parse.urlsplit(url).path not in ("", "/") and urllib.parse.urlsplit(p["final_url"]).path in ("", "/"):
        notes.append("URL 被重定向到站点首页（详情页不可达）")
    if not (oa.get("abstract") or s2.get("abstract") or (oa.get("is_oa") and oa.get("pdf_url")) or
            s2.get("pdf_url")) and p["status"] in (200, 206) and "html" in (p["content_type"] or "html") and not community:
        full = fetch(url, timeout=cfg.timeout, retries=cfg.retries, cache=cfg.cache, mailto=cfg.mailto,
                     read_limit=400000)
        if full["status"] == 200 and full["body"]:
            rec["landing"] = landing_meta(full["body"].decode("utf-8", "replace"))

    # ---- 证据分级
    landing = rec["landing"]
    if oa.get("is_oa") and oa.get("pdf_url"):
        # OpenAlex 的 pdf_url 也可能指向落地页 → 判 L1（「有全文」）前必须探测：可达且 Content-Type 是 PDF
        pr = fetch(oa["pdf_url"], method="HEAD", timeout=cfg.timeout, retries=1, cache=cfg.cache,
                   read_limit=2048, mailto=cfg.mailto)
        ct = (pr.get("headers") or {}).get("content-type", "")
        ok = pr["status"] in (200, 206, 301, 302, 303, 307, 308) and ("pdf" in ct or not ct)
        rec["oa_pdf_probe"] = {"url": oa["pdf_url"], "status": pr["status"], "content_type": ct, "ok": ok}
        if ok:
            rec["fulltext_reason"] = f"OpenAlex OA 全文 PDF（{oa.get('oa_status') or 'oa'}）"
        else:
            notes.append(f"OpenAlex 声明 OA 但 pdf_url 不可达/非 PDF（status={pr['status']}，"
                         f"content-type={ct or 'n/a'}）→ 不判 L1")
    elif s2.get("pdf_url"):
        rec["fulltext_reason"] = "Semantic Scholar openAccessPdf"
    elif rec["arxiv"].get("pdf"):
        rec["fulltext_reason"] = f"arXiv 预印本 PDF（{rec['arxiv']['id']}）"
    elif p["status"] in (200, 206) and "pdf" in (p["content_type"] or ""):
        rec["fulltext_reason"] = "池内 URL 直链 PDF（Content-Type application/pdf）"
    elif community and p["status"] in (200, 206):
        rec["fulltext_reason"] = "社区复现仓库/博客全文可读（非同行评审）"
    else:
        rec["fulltext_reason"] = ""
    abstract = oa.get("abstract") or s2.get("abstract") or landing.get("abstract") or ""
    meta_hit = bool(oa["hit"] or cr["hit"] or s2["hit"] or landing.get("title") or landing.get("doi"))
    rec["evidence_level"] = ("L1" if rec["fulltext_reason"] else "L2" if len(abstract) >= 100
                             else "L3" if meta_hit else "L4")
    rec["abstract_chars"] = len(abstract)

    # ---- 来源性质（启发式，判据不足写「待人工」）
    venue = oa.get("venue") or cr.get("container_title") or s2.get("venue") or landing.get("venue") or ""
    if community:
        rec["source_nature"] = "社区复现（非同行评审）"
    elif any(h in host for h in PREPRINT_HOSTS) or "arxiv" in f"{url}{doi}".lower() or "preprint" in venue.lower():
        rec["source_nature"] = "预印本"
    elif any(k in (venue + ent["title_pool"]).lower() for k in TEACHING_HINTS):
        rec["source_nature"] = "命题人/教学期刊"
    elif venue or any(h in host for h in PUBLISHER_HOSTS):
        rec["source_nature"] = "同行评审"
    else:
        rec["source_nature"] = "待人工"

    # ---- 标题完整性（启发式 + 权威题名证据）
    auth = max((oa.get("title") or "", cr.get("title") or "", s2.get("title") or "",
                rec["arxiv"].get("title") or "", landing.get("title") or ""), key=len)
    nq, nc = norm_title(core), norm_title(auth)
    rec["title_truncated"] = truncation_suspect(ent["title_pool"], strip_venue(ent["title_pool"]))
    rec["matched_title"] = auth
    if auth:
        score, _ = title_match(core, auth)
        if len(nq) >= 60 and nc.startswith(nq) and len(nc) > len(nq) + 3:
            # 池内标题是权威题名的真前缀 → 几乎肯定是截断（如断在句中）
            rec["title_truncated"] = rec["title_truncated"] or "权威题名以池内标题前缀开头且更长（疑似截断）"
        if ((nq and nq in nc) or score >= 0.92) and len(auth) > len(ent["title_pool"]):
            rec["title_full"] = auth
        elif not (nq and nq in nc) and score < 0.92:
            rec["defects"].append(("title-mismatch", f"池内题名与权威题名不一致：{auth[:90]}"))

    # ---- 缺陷
    if rec["title_truncated"]:
        rec["defects"].append(("title-truncated", rec["title_truncated"]))
    if not doi:
        found = rec["doi"] or oa.get("doi") or s2.get("external_doi") or ""
        rec["doi"] = found
        rec["defects"].append(("missing-doi", f"池内无 DOI；脚本检索到 {found}" if found else "池内无 DOI 且未检索到"))
    if p["status"] is None:
        rec["defects"].append(("url-broken", f"连接失败：{(p.get('error') or '')[:80]}"))
    elif p["status"] >= 400:
        rec["defects"].append(("url-broken", f"HTTP {p['status']}（{p['content_type'] or 'n/a'}）"))
    elif p["status"] == 202 and not p["bytes"]:
        rec["defects"].append(("url-broken", "HTTP 202 空响应（IEEE 反爬，如实记录）"))
    if len(abstract) >= 100 and POOL_FLAG.search(ent["excerpt"] + " " + ent["limits"]):
        rec["defects"].append(("abstract-underrated", f"池内标为「未精读/标题级/付费墙」，但实得摘要 {len(abstract)} 字符"))
    return rec


# ------------------------------------------------------------------ 报告

def _cell(s: object, n: int = 64) -> str:
    t = re.sub(r"\s+", " ", str(s or "")).replace("|", "\\|").strip()
    return (t[:n - 1] + "…") if len(t) > n else (t or "—")


def render_markdown(records: list[dict], cfg: "Config", stats: dict, elapsed: float) -> str:
    t = stats["levels"]
    L = [f"# 文献池核验报告（lit_verify.py v{VERSION}）", "", f"- 池文件：`{cfg.pool}`",
         f"- 生成时间：{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}（UTC，不参与判据）",
         f"- 条目数：{t['entries']} ｜ 证据级 L1={t['L1']} / L2={t['L2']} / L3={t['L3']} / L4={t['L4']} ｜ 缺陷 {t['defects']} 项",
         f"- 网络请求：{stats['net']} ｜ 缓存命中：{stats['cache']} ｜ 耗时 {elapsed:.1f}s ｜ workers={cfg.workers}",
         f"- OpenAlex mailto：{cfg.mailto or '**缺失**'}", ""]
    if not cfg.mailto:
        L += ["> ⚠ 未提供 `--mailto` / `LIT_MAILTO`：OpenAlex 礼貌池要求邮箱，可能 403 或限流；已继续跑其它源。", ""]
    L += ["## 证据分级规则", "", "| 级别 | 含义 | 判据 |", "|---|---|---|",
          "| L1 | 能拿到全文 | OA 全文 PDF（OpenAlex `best_oa_location` / S2 `openAccessPdf`）、arXiv 预印本 PDF、"
          "池内 URL 直链 PDF（Content-Type application/pdf）、社区复现仓库/博客全文可读 |",
          "| L2 | 只有摘要级 | 有摘要文本（OpenAlex `abstract_inverted_index` 重建 / S2 `abstract` / 官网落地页摘要），无全文 |",
          "| L3 | 只有元数据 | 标题/DOI/卷期页可核，无摘要 |",
          "| L4 | 不可验证 | 无 DOI、URL 失效且无元数据命中 |", "",
          "**来源性质**（venue + 来源域名启发式）：`同行评审` / `预印本` / `社区复现（非同行评审）` / "
          "`命题人/教学期刊` / `待人工`（判据不足不猜）。", "", "## 主表", "",
          "| 编号 | 相关性 | 标题（完整） | DOI | 元数据命中 | OA 状态 | 证据级 | 来源性质 | URL 状态 | 命中标题 | 备注 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in records:
        oa, cr, s2, p = r["openalex"], r["crossref"], r["s2"], r["url_probe"]
        oa_state = "—" if oa.get("is_oa") is None else \
            f"is_oa={oa.get('is_oa')} · {oa.get('oa_status') or 'n/a'} · PDF{'✓' if oa.get('pdf_url') else '✗'}"
        if p.get("status") is None:
            ustat = "ERR " + (p.get("error") or "")[:24]
        elif p["status"] == 202 and not p.get("bytes"):
            ustat = "202（空响应）"
        else:
            ustat = f"{p['status']} {p.get('content_type') or 'n/a'}"
        note = "；".join(([r["fulltext_reason"]] if r.get("fulltext_reason") else []) + r["notes"])
        L.append("| " + " | ".join([
            r["id"], _cell(r["relevance"], 4), _cell(r["title_full"], 78), _cell(r["doi"], 40),
            f"OA{'✓' if oa['hit'] else '✗'} · CR{'✓' if cr['hit'] else '✗'} · S2{'✓' if s2['hit'] else '✗'}",
            _cell(oa_state + (" · S2PDF✓" if s2.get("pdf_url") else ""), 44), f"**{r['evidence_level']}**",
            r["source_nature"], _cell(ustat, 26), _cell(r["matched_title"], 46), _cell(note, 70)]) + " |")
    L += ["", "## 缺陷区", ""]
    for key, label in (("title-truncated", "标题疑似截断"), ("missing-doi", "缺 DOI"), ("url-broken", "URL 失效"),
                       ("abstract-underrated", "摘要可得但被标为不可用"), ("title-mismatch", "题名与权威题名不一致")):
        items = [(r["id"], d) for r in records for k, d in r["defects"] if k == key]
        L += [f"### {label}（{len(items)}）"] + ([f"- **{i}**：{d}" for i, d in items] or ["- 无"]) + [""]
    L += ["## 汇总", "", f"- 证据级：L1={t['L1']}，L2={t['L2']}，L3={t['L3']}，L4={t['L4']}",
          f"- 缺陷：标题截断 {t['title-truncated']}，缺 DOI {t['missing-doi']}，URL 失效 {t['url-broken']}，"
          f"摘要可得却标为不可用 {t['abstract-underrated']}，题名不一致 {t['title-mismatch']}",
          f"- 来源性质：同行评审 {t['peer']}，预印本 {t['preprint']}，社区复现 {t['community']}，"
          f"命题人/教学期刊 {t['teaching']}，待人工 {t['unknown_nature']}", f"- 脚本新补出 DOI：{t['doi_recovered']} 条", ""]
    return "\n".join(L)


def build_json(records: list[dict], cfg: "Config", stats: dict, elapsed: float) -> dict:
    out = []
    for r in records:
        s2 = r["s2"]
        s2_status = " ".join(x for x in [(f"DOI:{s2['status']}" if s2.get("status") not in ("no_doi", None) else ""),
                                         f"search:{s2['status_search']}" if s2.get("status_search") else ""] if x)
        out.append({"id": r["id"], "title_full": r["title_full"], "title_pool": r["title_pool"], "doi": r["doi"],
                    "url": r["url"], "evidence_level": r["evidence_level"], "source_nature": r["source_nature"],
                    "metadata_hits": {"openalex": bool(r["openalex"]["hit"]), "crossref": bool(r["crossref"]["hit"]),
                                      "semantic_scholar": bool(s2["hit"])},
                    "openalex": r["openalex"], "crossref": r["crossref"], "s2": s2,
                    "semantic_scholar_url_status": s2_status, "doi_resolve": r["doi_resolve"], "arxiv": r["arxiv"],
                    "landing": r["landing"], "url_status": r["url_probe"],
                    "title_truncated": r.get("title_truncated", ""), "abstract_chars": r.get("abstract_chars", 0),
                    "defects": [{"kind": k, "detail": d} for k, d in r["defects"]], "notes": r["notes"]})
    return {"generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "pool_path": cfg.pool,
            "tool": f"lit_verify.py v{VERSION}", "mailto": cfg.mailto,
            "totals": dict(stats["levels"], network_requests=stats["net"], cache_hits=stats["cache"],
                           elapsed_sec=round(elapsed, 2)), "entries": out}


# ------------------------------------------------------------------ CLI

class Config:
    def __init__(self, a: argparse.Namespace):
        self.pool, self.out, self.json = a.pool, a.out, a.json
        self.mailto = (a.mailto or os.environ.get("LIT_MAILTO") or "").strip()
        self.timeout, self.retries, self.workers = a.timeout, a.retries, a.workers
        self._cache_arg = a.cache
        self.cache = a.cache or ""      # 真正的缓存目录在池校验通过后再定（避免致命错误也建 .litcache）
        self.only = [x.strip().upper() for x in (a.only or "").split(",") if x.strip()]

    @staticmethod
    def default_cache_dir() -> str:
        # 默认：当前工作目录下的 .litcache（确定性、随 run 走）。原先按脚本路径推 repo 根再回退系统临时目录，
        # 既算错层级（少了一层→<repo>/skills/test/...）又把缓存放到会被清理的 /tmp，导致重跑不走缓存。
        return self._cache_arg or os.path.join(os.getcwd(), ".litcache")

    def ensure_cache(self) -> str:
        """池校验通过后再确定/创建缓存目录（不可写 → 回退系统临时目录）。"""
        try:
            os.makedirs(self.cache, exist_ok=True)
        except OSError:
            self.cache = os.path.join(tempfile.gettempdir(), "litcache")
            os.makedirs(self.cache, exist_ok=True)
        return self.cache


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="文献池批量核验（DOI/OpenAlex/Crossref/S2/URL/arXiv → 证据分级 L1–L4）")
    p.add_argument("--pool", required=True, help="文献池 Markdown 路径（只读）")
    p.add_argument("--out", help="Markdown 报告输出路径")
    p.add_argument("--json", help="JSON 明细输出路径")
    p.add_argument("--mailto", help="OpenAlex 礼貌池邮箱（或环境变量 LIT_MAILTO）")
    p.add_argument("--timeout", type=float, default=20.0, help="单请求超时秒数（默认 20）")
    p.add_argument("--retries", type=int, default=2, help="失败重试次数，指数退避 ≤2s（默认 2）")
    p.add_argument("--only", help="仅核验指定编号，如 S3,S14")
    p.add_argument("--workers", type=int, default=6, help="并发线程数（默认 6）")
    p.add_argument("--cache", help="HTTP 响应缓存目录（默认 <cwd>/.litcache；不可写时回退系统临时目录）")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    cfg = Config(parse_args(argv))
    if not os.path.isfile(cfg.pool):
        print(f"[lit_verify] 致命错误：文献池不存在或不可读：{cfg.pool}", file=sys.stderr)
        return 2
    try:
        with open(cfg.pool, encoding="utf-8") as fh:
            text = fh.read()
    except Exception as e:
        print(f"[lit_verify] 致命错误：读取文献池失败：{type(e).__name__}: {e}", file=sys.stderr)
        return 2
    all_entries = parse_pool(text)
    entries = [e for e in all_entries if not cfg.only or e["id"] in cfg.only]
    if not entries:
        if all_entries and cfg.only:
            have = ", ".join(e["id"] for e in all_entries[:20])
            print(f"[lit_verify] 致命错误：--only {','.join(cfg.only)} 在池中无匹配条目"
                  f"（池内解析到 {len(all_entries)} 条：{have}）", file=sys.stderr)
        else:
            print(f"[lit_verify] 致命错误：未从池中解析出任何 S 编号条目（{cfg.pool}）"
                  f"——检查池内条目是否以 `### S<编号>` 开头", file=sys.stderr)
        return 2
    cfg.ensure_cache()
    if not cfg.mailto:
        print("[lit_verify] 警告：未提供 --mailto / LIT_MAILTO，OpenAlex 可能 403/限流，继续跑其它源。", file=sys.stderr)
    t0, records = time.monotonic(), []
    with futures.ThreadPoolExecutor(max_workers=max(1, cfg.workers)) as ex:
        futs = {ex.submit(verify_entry, e, cfg): e for e in entries}
        for f in futures.as_completed(futs):
            e = futs[f]
            try:
                records.append(f.result())
            except Exception as ex_:  # 单条异常不得拖垮整轮
                rec = _blank(e)
                rec.update(notes=[f"核验异常：{type(ex_).__name__}: {ex_}"],
                           url_probe={"status": None, "error": str(ex_)})
                records.append(rec)
    records.sort(key=lambda r: int(r["id"][1:]))
    elapsed = time.monotonic() - t0
    t = {"entries": len(records), "L1": 0, "L2": 0, "L3": 0, "L4": 0, "defects": 0, "title-truncated": 0,
         "missing-doi": 0, "url-broken": 0, "abstract-underrated": 0, "title-mismatch": 0, "peer": 0,
         "preprint": 0, "community": 0, "teaching": 0, "unknown_nature": 0, "doi_recovered": 0}
    for r in records:
        t[r["evidence_level"]] = t.get(r["evidence_level"], 0) + 1
        for k, _d in r["defects"]:
            t[k] = t.get(k, 0) + 1
        t["defects"] += len(r["defects"])
        t["doi_recovered"] += int(any(k == "missing-doi" and "脚本检索到" in d for k, d in r["defects"]))
        n = r["source_nature"]
        t["peer" if n == "同行评审" else "preprint" if n == "预印本" else "community" if n.startswith("社区")
          else "teaching" if n.startswith("命题") else "unknown_nature"] += 1
    stats = {"net": _STATS["net"], "cache": _STATS["cache"], "levels": t}
    for path, is_md in ((cfg.out, True), (cfg.json, False)):
        if not path:
            continue
        try:
            with open(path, "w", encoding="utf-8") as fh:
                if is_md:
                    fh.write(render_markdown(records, cfg, stats, elapsed))
                else:
                    json.dump(build_json(records, cfg, stats, elapsed), fh, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[lit_verify] 输出写入失败（{path}）：{type(e).__name__}: {e}", file=sys.stderr)
    print(f"[lit_verify] 条目={t['entries']} L1={t['L1']} L2={t['L2']} L3={t['L3']} L4={t['L4']} "
          f"缺陷={t['defects']} 网络={stats['net']} 缓存命中={stats['cache']} 耗时={elapsed:.1f}s"
          + ("" if cfg.out else "  （未传 --out，未写主表）"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
