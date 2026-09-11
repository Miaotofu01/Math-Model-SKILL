#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""artifact_lint.py —— 数字单一真源检查（math-model skill 技能级工具）

用途
----
扫描一次 run 的产物树，检查**关键结果数字**是否被到处抄写（口径分叉风险）。
设计依据（上次 run 实测）：同一个关键数字可散落到 40+ 份文件、上百处（含实现代码、原始输出与
题面给定常量）—— 抄写不仅费 token，更制造「口径分叉」。因此判据必须**先减掉题面给定值，
再只看下游消费的产物品**，否则会产出大量噪声（首版实现曾一次报出 82 条无效告警）。

判定规则（与 `prompts/_common.md` §4 一致）
------------------------------------------
- **唯一真源**：`intermediates/q*/06-computation/results.json`（各问数值权威）
  与 `intermediates/12-writing/fact-sheet.md`（全篇唯一数字来源）。
- 关键数字 = 有效数字 ≥5 位，或 ≥4 位整数（年份除外）。
- 同一关键数字在**其它产物**中出现 ≥3 处 → P0（口径分叉，必须收敛到 results.json，改锚点引用）。
- 降级模式（找不到任何 results.json）：对所有产物做同样的散落统计，剔除题面给定常量（`00-problem.json` 内出现过的数字）。

额外检查
--------
- `paper.unsourced`（P1）：论文正文（`12-writing/paper-sections/*.md`）里的关键数字不在任何 results.json 的
  `keyValues` 中 → 可能无源，需要补登记或删改。
- `draft.ledger_section`（**P0**，零容差）：`q*/04-formulation/draft.md` 的标题里出现台账类章节
  （修订记录/处置表/证据键表/已通过项/符号登记/口径勘误/验证计划）→ 违反 phase-04「产物与篇幅预算」：
  台账归 `revision-log/verification/handoff/errata/symbols`，draft 只留 1 行指针。
  实测依据：q1 台账占 46.9%（51,434/109,599 字符）、q2 占 39.6%；方案本体两问均 ≈57–58k 字符。
- `boot.payload_limit`（P1）：调度壳启动一次并列读的 5 件（`intermediates/00-problem.json`、`state.json`、
  三份 `manifest.json`）单文件须 <50 KiB 且单行 ≤1500 字符 —— read 工具在此硬截断，超限会让整个 boot
  「全有或全无」（本项目曾因此启动失败 6 次）。

用法
----
    python3 scripts/artifact_lint.py --root <outputDir> [--json lint.json] [--quiet] [--min-places 3]

退出码：0 = 无 P0；1 = 有 P0；2 = 参数/路径错误。
仅用标准库；不改动任何输入文件。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

TEXT_SUFFIXES = {".md", ".json", ".tex", ".py", ".html", ".txt", ".csv", ".yaml", ".yml"}
PRODUCT_SUFFIXES = {".md", ".html", ".tex", ".py"}
SKIP_DIR_PARTS = {".git", "__pycache__", ".venv", ".chrome-tmp", "node_modules", ".ipynb_checkpoints"}
# 计数范围＝**下游要消费的产物**（白名单）。以下都是合法数字载体，永不计数：
#   - 实现代码与原始输出（code/**、outputs/**、*_results.json|txt）：数值算出来就落在这里
#   - 评审意见 review-r*.md：其职责就是引用并质疑数字
#   - 探针/校验脚本（_*.py、*_verify.py、*_judge_*.py）：本身在验数
#   - 真源文件本身（results.json / fact-sheet.md）
COUNTED_PRODUCT_RE = re.compile(
    r"^(?:"
    r"q\d+/(?:02-data/(?:eda\.md|data-collection\.json|figure-manifest\.md)"
    r"|03-assumptions/[^/]+\.md"
    r"|04-formulation/(?:draft\.md|symbols\.json|baseline-registry\.md|self-check\.md)"
    r"|07-sanity/[^/]+\.md"
    r"|08-visualization/(?:figure-manifest\.md|plot_[^/]+\.py)"
    r"|08-visualization/figures/[^/]+\.html"
    r"|09-robustness/[^/]+\.md"
    r"|10-completed/[^/]+\.md)"
    r"|12-writing/paper-sections/[^/]+\.md"          # 论文正文（关键数字复制到正文必须计数，否则漏报 P0）
    r"|(?:12-writing|13-final)/[^/]+\.(?:md|tex)"
    r"|figures/[^/]+\.html"
    r")$"
)
MAX_SHOWN = 8   # 报告里最多逐条展开的 P0 数量（其余见 --json）
MAX_FILE_BYTES = 8 * 1024 * 1024

NUM_RE = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?:[eE][-+]?\d+)?(?![\w.])")
SINGLE_SOURCE_BASENAMES = {"results.json", "fact-sheet.md"}
# 真源只在契约位置（否则 02-data/results.json 之类同名数据文件会被当成权威数字来源）
SINGLE_SOURCE_RE = re.compile(
    r"^(?:intermediates/)?q[^/]+/06-computation/results\.json$"
    r"|^(?:intermediates/)?12-writing/fact-sheet\.md$"
)


def is_single_source(rel: str) -> bool:
    return bool(SINGLE_SOURCE_RE.match(rel.replace("\\", "/")))


def norm_number(raw: str) -> str | None:
    """把匹配到的数字串规范化为可比较的十进制字符串；非有限/异常返回 None。"""
    s = raw.strip().replace(",", "")
    if s.startswith("-"):
        s = s[1:]
    if not s or not any(ch.isdigit() for ch in s):
        return None
    if "e" in s or "E" in s:
        try:
            val = float(s)
        except ValueError:
            return None
        if val == 0:
            return None
        # 科学计数法统一展开为普通十进制（保留 12 位有效数字以内）
        s = f"{val:.12g}"
        if "e" in s or "E" in s:
            return None
    if s.endswith("."):
        s = s[:-1]
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    s = s.lstrip("0") or "0"
    return s or None


def is_key_number(n: str) -> bool:
    """有效数字 ≥5 或 ≥4 位整数（年份另由 is_year 排除）。"""
    digits = n.replace(".", "")
    if len(digits) >= 5:
        return True
    return "." not in n and len(digits) >= 4


def is_year(n: str) -> bool:
    return "." not in n and len(n) == 4 and 1900 <= int(n) <= 2100


def iter_files(root: Path):
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in SKIP_DIR_PARTS for part in p.parts):
            continue
        try:
            if p.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        yield p


def get_paths(root: Path, inter: Path):
    """返回 (真源文件, 计数用产物文件, 全部文本文件)。"""
    sources, products, texts = [], [], []
    for p in iter_files(root):
        rel = str(p.relative_to(root))
        texts.append(p)
        if is_single_source(rel):
            sources.append(p)
            continue
        if not COUNTED_PRODUCT_RE.match(rel):
            continue
        products.append(p)
    return sources, products, texts


def read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def numbers_with_lines(text: str) -> dict[str, list[int]]:
    """返回 {规范化数字: [行号...]}。"""
    out: dict[str, list[int]] = defaultdict(list)
    for lineno, line in enumerate(text.splitlines(), 1):
        for m in NUM_RE.finditer(line):
            n = norm_number(m.group(0))
            if n and is_key_number(n) and not is_year(n):
                out[n].append(lineno)
    return dict(out)


def collect_single_source(root: Path) -> tuple[set[str], list[str]]:
    """从 results.json / fact-sheet.md 收集权威数字，并返回这些文件的相对路径列表。"""
    keys: set[str] = set()
    paths: list[str] = []
    for p in iter_files(root):
        rel = str(p.relative_to(root)).replace("\\", "/")
        if is_single_source(rel):
            paths.append(rel)
            for n in numbers_with_lines(read_text(p)):
                keys.add(n)
    return keys, paths


def collect_problem_givens(root: Path) -> set[str]:
    """题面给定常量（00-problem.json 内出现过）—— 不算分叉，重复出现属正常。"""
    givens: set[str] = set()
    for p in iter_files(root):
        if p.name == "00-problem.json":
            for n in numbers_with_lines(read_text(p)):
                givens.add(n)
    return givens


def _load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _norm_rel(root: Path, s: str) -> str:
    s = str(s).replace("\\", "/").lstrip("./")
    p = Path(s)
    if p.is_absolute():
        try:
            return str(p.relative_to(root))
        except ValueError:
            return s
    return s


def check_pool_registration(root: Path) -> tuple[list[dict], dict]:
    """池登记完整性：目录里的 .py 与 manifest 条目必须双向对得上（看不见 = 会被重写）。"""
    out: list[dict] = []
    stats = {"pool_py": 0, "probe_py": 0, "pool_entries": 0, "probe_entries": 0}

    prim = root / "pool" / "primitives.py"
    pman = _load_json(root / "pool" / "manifest.json")
    if prim.is_file():
        stats["pool_py"] += 1
        if not isinstance(pman, dict) or not (pman.get("entries") or {}):
            out.append({"level": "P1", "check": "pool.manifest_missing", "locations": ["pool/primitives.py"],
                        "detail": "pool/primitives.py 存在但 pool/manifest.json 缺失或为空 → 后问看不见池内容；"
                                  "在 outputDir 下跑 `python pool/primitives.py --manifest pool/manifest.json`"})
        else:
            stats["pool_entries"] += len(pman.get("entries") or {})

    pdir = root / "probes"
    qman = _load_json(pdir / "manifest.json")
    reg: set[str] = set()
    if isinstance(qman, dict):
        for v in (qman.get("probes") or {}).values():
            stats["probe_entries"] += 1
            s = (v or {}).get("script") or ""
            if s:
                reg.add(_norm_rel(root, s))
    files = []
    if pdir.is_dir():
        for p in sorted(pdir.rglob("*.py")):
            try:                                     # 只排除 probes/results/ 下的 *.py（按相对路径判断，
                rel_parts = p.relative_to(pdir).parts  # 否则 run 根路径含 results 段时会误报幽灵条目）
            except ValueError:
                rel_parts = p.parts
            if rel_parts and rel_parts[0] == "results":
                continue
            files.append(p)
    stats["probe_py"] = len(files)
    now = {str(p.relative_to(root)) for p in files}
    for rel in sorted(now - reg):
        out.append({"level": "P1", "check": "probes.unregistered", "locations": [rel],
                    "detail": f"探针 {rel} 未登记进 probes/manifest.json → 评审/后问看不见、会被重写；"
                              f"用 `probe_cache.py --run {rel} …` 跑一次即自动登记"})
    for rel in sorted(reg - now):
        out.append({"level": "P1", "check": "probes.ghost", "locations": [rel],
                    "detail": f"probes/manifest.json 登记了 {rel}，但文件不存在（幽灵条目）"})

    pdirp = root / "pool" / "problem"
    oman = _load_json(pdirp / "manifest.json")
    keys = list((oman or {}).get("entries") or {}) if isinstance(oman, dict) else []
    stats["pool_entries"] += len(keys)
    stems: dict[str, str] = {}
    for p in sorted(pdirp.rglob("*.py")) if pdirp.is_dir() else []:
        if p.name.startswith("__"):
            continue
        stats["pool_py"] += 1
        stems[p.stem] = str(p.relative_to(root))
        if not any(k == p.stem or k.startswith(p.stem + ".") or "." + p.stem + "." in k for k in keys):
            out.append({"level": "P1", "check": "pool.unregistered", "locations": [stems[p.stem]],
                        "detail": f"题专用核心 {stems[p.stem]} 未登记进 pool/problem/manifest.json → 后问看不见；"
                                  f"补一条 {{\"entries\":{{\"{p.stem}.<函数>\":{{\"口径\":…,\"单位\":…,\"被复用\":[…]}}}}}}"})
    for k in keys:
        mod = k.split(".")[0]
        if mod and mod not in stems:
            out.append({"level": "P1", "check": "pool.ghost", "locations": [f"pool/problem/manifest.json#{k}"],
                        "detail": f"登记条目 {k} 对应的模块文件不存在（幽灵条目）"})
    return out, stats


# ── draft 台账零容差（phase-04「产物与篇幅预算」）──
DRAFT_LEDGER_KEYS = ("修订记录", "修订处置", "处置表", "逐条处置", "证据键表", "已通过项",
                     "符号登记", "口径勘误", "验证计划", "台账")
DRAFT_LEDGER_SKIP = ("指针",)          # 「台账与机械核验指针」这类纯指针节不算台账


def check_draft_ledger(root: Path) -> list[dict]:
    """draft.md 标题里出现台账类章节 ⇒ P0（台账另存，draft 只留 1 行指针）。"""
    out: list[dict] = []
    base = root / "intermediates"
    if not base.is_dir():
        return out
    for draft in sorted(base.glob("q*/04-formulation/draft.md")):
        hits: list[str] = []
        for i, line in enumerate(read_text(draft).split("\n"), 1):
            if not line.startswith("#"):
                continue
            title = line.lstrip("#").strip()
            if any(s in title for s in DRAFT_LEDGER_SKIP):
                continue
            if any(k in title for k in DRAFT_LEDGER_KEYS):
                hits.append(f"{draft.relative_to(root)}:{i}  {title[:70]}")
        if hits:
            out.append({"level": "P0", "check": "draft.ledger_section", "locations": hits[:12],
                        "detail": (f"{draft.relative_to(root)} 含 {len(hits)} 个台账类章节标题（台账归 "
                                   "revision-log/verification/handoff/errata/symbols，draft 只留 1 行指针）")})
    return out


# ── boot 载荷上限（壳启动一次并列读的 5 件）──
BOOT_FILES = ("intermediates/00-problem.json", "intermediates/state.json", "pool/manifest.json",
              "pool/problem/manifest.json", "probes/manifest.json")
BOOT_MAX_BYTES = 50 * 1024
BOOT_MAX_LINE_CHARS = 1500


def check_boot_payload(root: Path) -> tuple[list[dict], dict]:
    """boot 读的 5 件：单文件 <50 KiB 且单行 ≤1500 字符（read 工具硬限 ⇒ 超限则续跑启动失败）。"""
    out: list[dict] = []
    stats: dict = {"checked": 0, "files": []}
    for rel in BOOT_FILES:
        fp = root / rel
        if not fp.is_file():
            continue
        size = fp.stat().st_size
        max_line = max((len(x) for x in read_text(fp).split("\n")), default=0)
        stats["checked"] += 1
        stats["files"].append({"path": rel, "bytes": size, "maxLineChars": max_line})
        bad = []
        if size >= BOOT_MAX_BYTES:
            bad.append(f"{size} B ≥ 50 KiB")
        if max_line > BOOT_MAX_LINE_CHARS:
            bad.append(f"最长行 {max_line} 字符 > {BOOT_MAX_LINE_CHARS}")
        if bad:
            out.append({"level": "P1", "check": "boot.payload_limit", "locations": [rel],
                        "detail": f"{rel} 超限（{'; '.join(bad)}）⇒ 壳启动批量读会被截断，续跑可能直接报「未找到 00-problem.json」"})
    return out, stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="math-model 数字单一真源检查")
    ap.add_argument("--root", required=True, help="outputDir（含 intermediates/）")
    ap.add_argument("--json", dest="json_out", default=None, help="结构化结果落盘路径")
    ap.add_argument("--min-places", type=int, default=3, help="判定分叉的最小出现处数（默认 3）")
    ap.add_argument("--quiet", action="store_true", help="只输出汇总")
    args = ap.parse_args(argv)

    root = Path(args.root).expanduser()
    if not root.is_dir():
        print(f"[错误] 不是目录：{root}", file=sys.stderr)
        return 2
    inter = root / "intermediates"
    scan_root = inter if inter.is_dir() else root

    single_keys, single_paths = collect_single_source(scan_root)
    givens = collect_problem_givens(scan_root)
    keys = single_keys - givens  # 题面给定常量不算「关键结果数字」；无真源时退化为全量扫描
    mode = "真源模式" if keys else "降级模式（未找到可用真源数值）"
    _src, product_files, all_texts = get_paths(scan_root, scan_root)

    # 出现统计：数字 -> [(相对路径, 行号)...]（只统计叙述/派生产物，见 SKIP_PATH_PARTS 说明）
    places: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for p in product_files:
        rel = str(p.relative_to(scan_root))
        text = read_text(p)
        if not text:
            continue
        for n, lines in numbers_with_lines(text).items():
            if keys:
                if n not in keys:
                    continue
            elif n in givens:
                continue
            places[n].append((rel, lines[0]))

    findings: list[dict] = []
    for n, locs in sorted(places.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        files = sorted({f for f, _ in locs})
        if len(locs) >= args.min_places:
            findings.append({
                "level": "P0",
                "check": "number.scattered",
                "number": n,
                "places": len(locs),
                "files": files,
                "locations": [f"{f}:{ln}" for f, ln in locs],
                "detail": f"关键数字 {n} 在 {len(files)} 份产物 / {len(locs)} 处出现（唯一真源应为 results.json，其余改锚点引用）",
            })

    # 正文数字是否有源（仅真源模式，P1）
    paper_dir = scan_root / "12-writing" / "paper-sections"
    if keys and paper_dir.is_dir():
        unsourced: dict[str, list[str]] = defaultdict(list)
        for p in sorted(paper_dir.glob("*.md")):
            for n, lines in numbers_with_lines(read_text(p)).items():
                # 题面给定常量（givens）是 §4 的显式例外：论文引用它们不算「无源」
                if n not in keys and n not in givens:
                    unsourced[n].append(f"{p.name}:{lines[0]}")
        for n, locs in sorted(unsourced.items(), key=lambda kv: -len(kv[1])):
            findings.append({
                "level": "P1",
                "check": "paper.unsourced",
                "number": n,
                "places": len(locs),
                "files": sorted({l.split(":")[0] for l in locs}),
                "locations": locs,
                "detail": f"论文正文数字 {n} 不在任何 results.json/fact-sheet 中（可能无源或漏登记）",
            })

    pool_findings, pool_stats = check_pool_registration(root)
    findings.extend(pool_findings)
    findings.extend(check_draft_ledger(root))
    boot_findings, boot_stats = check_boot_payload(root)
    findings.extend(boot_findings)

    p0 = [f for f in findings if f["level"] == "P0"]
    p1 = [f for f in findings if f["level"] == "P1"]

    if not args.quiet:
        print(f"# artifact_lint 报告 — {scan_root}")
        print(f"- 模式：{mode}；真源文件 {len(single_paths)} 个" + (f"（{', '.join(single_paths[:6])}{' …' if len(single_paths) > 6 else ''}）" if single_paths else ""))
        print(f"- 真源数字 {len(single_keys)} 种，其中题面给定常量 {len(single_keys) - len(keys)} 种已排除；待查关键数字 {len(keys)} 种")
        print(f"- 扫描文本文件 {len(all_texts)} 份，其中计数范围（叙述/派生产物）{len(product_files)} 份；命中关键数字 {len(places)} 种")
        print(f"- 池登记：pool/ 下 {pool_stats['pool_py']} 个 .py（条目 {pool_stats['pool_entries']}）、"
              f"probes/ 下 {pool_stats['probe_py']} 个 .py（条目 {pool_stats['probe_entries']}）；"
              f"未登记/幽灵 {len(pool_findings)} 项")
        print(f"- boot 载荷：检查 {boot_stats['checked']} 件（阈值 <50 KiB 且单行 ≤1500 字符）")
        if not findings:
            print("- 未发现数字散落问题")
        for f in (p0 + p1)[:MAX_SHOWN]:
            print(f"\n[{f['level']}] {f['check']}: {f['detail']}")
            for loc in f["locations"][:12]:
                print(f"    - {loc}")
            if len(f["locations"]) > 12:
                print(f"    … 其余 {len(f['locations']) - 12} 处见 --json")
        if len(p0) + len(p1) > MAX_SHOWN:
            print(f"\n（其余 {len(p0) + len(p1) - MAX_SHOWN} 项见 --json）")
        offender: dict[str, int] = defaultdict(int)
        for f in p0:
            for loc in f["locations"]:
                offender[loc.split(":")[0]] += 1
        if offender:
            print("\n## 优先整改文件（承载最多散落数字）")
            for fn, c in sorted(offender.items(), key=lambda kv: -kv[1])[:10]:
                print(f"    - {fn}：{c} 个关键数字需改锚点引用")

    print(f"\n汇总：P0={len(p0)} P1={len(p1)}（判定阈值：同一关键数字 ≥{args.min_places} 处）")

    if args.json_out:
        payload = {
            "root": str(scan_root),
            "mode": mode,
            "single_source_files": single_paths,
            "given_numbers_excluded": sorted(single_keys - keys),
            "counted_products": len(product_files),
            "min_places": args.min_places,
            "findings": findings,
            "pool": {"stats": pool_stats, "findings": pool_findings},
            "summary": {"P0": len(p0), "P1": len(p1)},
        }
        try:
            Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.json_out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            if not args.quiet:
                print(f"JSON：{args.json_out}")
        except OSError as exc:
            print(f"[错误] 无法写 --json（{args.json_out}）：{exc}（报告已在上方 stdout）", file=sys.stderr)
            return 2

    return 1 if p0 else 0


if __name__ == "__main__":
    sys.exit(main())
