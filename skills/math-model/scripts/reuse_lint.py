#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reuse_lint.py —— 复用率机械核验：同口径重复实现检测 + 对拍（math-model skill 技能级工具）

用途
----
回答「**该进池的代码，是不是又各写了一份**」——`artifact_lint.py` 只查「进了池却没登记」，
本工具查「**根本没进池的重复实现**」，即 `_common.md` §4.2「rule of two / 第 2 次需要禁止再写副本」的机械执行者。

判据（与 `_pool.md` §5.1 一致）
--------------------------------
- 把每个函数**规范化成骨架**（去 docstring、标识符按首次出现顺序重命名、保留属性名与常量）后聚类；
  骨架相同 = 结构同形的重复实现候选（**只是候选**：口径是否一致要靠 `_pool.md` §5.1 判据 + `--pairs` 对拍确认）。
- 建议权威：`pool/primitives.py` > `pool/problem/` > `probes/` > 更早的小问（同口径只留一份）。
- 置信度：函数名或参数名也一致 → `high`；仅骨架一致 → `medium`（medium 必须先对拍再合并）。
- **第二判据（互补）：跨小问同名同签名** —— 函数**名相同 + 参数个数相同**且出现在 ≥2 个小问
  （`intermediates/q*` 的 zone，或探针文件名 `q1_…`／`q2_…` 推定）⇒「**同职责各写一份**」候选。
  骨架判据**抓不到**这类：口径微差、变量名不同、多一行 `try/except` 就会让骨架不同（实测某 run：
  q1↔q2 交付 driver 有 **15 个同名函数**未进任何骨架组）。
  **默认只报不阻塞**（`--strict` 的退出码不受本判据影响，避免事后改变既有 run 的门）；
  `--strict-samesig` 可显式升级（仅 `high` 档、跨小问）为退出码 1。
  结构性必有的通用名（`main`/`run`/`parse_args`…）在 `GENERIC_NAMES` 白名单内，不判。

用法
----
    python3 scripts/reuse_lint.py --scan --root <outputDir> [--json out.json] [--min-stmts 3]
    python3 scripts/reuse_lint.py --scan --root <outputDir> --strict          # 跨小问重复组 → 退出码 1（供 11 阶段）
    python3 scripts/reuse_lint.py --scan --root <outputDir> --strict-samesig  # 另：跨问同名同签名(high) → 退出码 1
    python3 scripts/reuse_lint.py --selftest                                  # 第二判据的反例自检
    python3 scripts/reuse_lint.py --scan --dirs a,b,c                        # 自定义扫描目录（不按 run 布局）
    python3 scripts/reuse_lint.py --pairs A.py B.py --inputs '{"x":[1,2]}'   # 同输入对拍两份实现

退出码：`--scan` 默认恒 0（只报不阻塞）；`--strict` 有跨小问重复组 → 1；`--pairs` 全部一致 → 0，有分歧/异常 → 1。
仅用标准库（被检函数自身可用 numpy 等）；只读，不改动任何输入文件。

**硬约束**：本工具只产报告。**禁止自动回改已定稿小问的代码**——改动必须同问重跑 `06-computation`
才有资格（否则代码与 results.json 脱钩）；07 之后发现 → 只写整改清单。
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import sys
import tempfile
import warnings
from collections import defaultdict
from pathlib import Path

MIN_STMTS_DEFAULT = 3
ZONE_ORDER = {"prim": 0, "problem": 1, "probe": 2}
# 第二判据（跨问同名同签名）的白名单：每个模块/CLI 结构性必有的名字，出现同名不算「同职责重写」
GENERIC_NAMES = {"main", "run", "cli", "parse_args", "build_parser", "setup", "teardown", "wrapper"}
SKIP_PARTS = {"__pycache__", "libs", "site-packages", "node_modules", "vendor", "third_party",
              ".venv", "venv", "build", "dist", ".git", "results", "outputs", ".litcache"}


def _skip(f: Path, base: Path | None = None) -> bool:
    """按**相对扫描根**的路径段过滤（绝对路径里出现 outputs/results 等段不该误杀整棵树）。"""
    try:
        parts = (f.relative_to(base) if base else f).parts
    except ValueError:
        parts = f.parts[-2:] if len(f.parts) > 1 else f.parts
    return bool(SKIP_PARTS & set(parts))


def _skip_docstring(body: list) -> list:
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        return body[1:]
    return body


def skeleton(fn) -> str | None:
    """函数体骨架：去 docstring + 标识符按出现顺序重命名（保留属性名/常量/结构）。"""
    body = _skip_docstring(list(fn.body))
    stmts = [s for s in body if not (isinstance(s, ast.Expr) and isinstance(getattr(s, "value", None), ast.Constant))]
    if not stmts:
        return None
    if len(stmts) == 1 and isinstance(stmts[0], (ast.Pass, ast.Raise)):
        return None
    tree = ast.Module(body=body, type_ignores=[])
    ren: dict = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.arg):
            ren.setdefault(node.arg, "v%d" % len(ren))
            node.arg = ren[node.arg]
        elif isinstance(node, ast.Name):
            ren.setdefault(node.id, "v%d" % len(ren))
            node.id = ren[node.id]
    return ast.dump(tree, annotate_fields=False, include_attributes=False)


def n_stmts(fn) -> int:
    return len([s for s in _skip_docstring(list(fn.body))
                if not (isinstance(s, ast.Expr) and isinstance(getattr(s, "value", None), ast.Constant))])


def iter_files(root: Path, dirs) -> list:
    """返回 (文件, 分区标签)。默认按 run 布局；`--dirs` 时按传入目录命名分区。"""
    out: list = []
    if dirs:
        for d in dirs:
            p = Path(d)
            if not p.is_absolute():
                p = root / d
            for f in (sorted(p.rglob("*.py")) if p.is_dir() else []):
                if not _skip(f, root):
                    out.append((f, d))
        return out
    for rel, zone in (("pool/primitives.py", "prim"), ("pool/problem", "problem"), ("probes", "probe")):
        p = root / rel
        files = [p] if p.is_file() else (sorted(p.rglob("*.py")) if p.is_dir() else [])
        for f in files:
            if not _skip(f, root):
                out.append((f, zone))
    idir = root / "intermediates"
    if idir.is_dir():
        for q in sorted(idir.glob("q*")):
            for sub in ("02-data", "05-implementation/code", "06-computation"):
                for f in sorted((q / sub).rglob("*.py")):
                    if not _skip(f, root):
                        out.append((f, "%s:%s" % (q.name, sub)))
    return out


def q_index(zone: str) -> int:
    if zone in ZONE_ORDER:
        return ZONE_ORDER[zone]
    try:
        return 100 + int(zone.split(":")[0].lstrip("q"))
    except ValueError:
        return 999


_Q_IN_NAME = re.compile(r"(?:^|[/_\-])q([1-4])(?=[_\-./]|$)")


def _qtag(zone: str, rel: str):
    """推定实现所属小问：`q1:05-implementation/code` → `q1`；探针按文件名 `q1_…` 推定；推不出 → None。"""
    if ":" in zone:
        return zone.split(":")[0]
    m = _Q_IN_NAME.search(rel)
    return "q%s" % m.group(1) if m else None


def samesig(recs: list) -> list:
    """第二判据：跨小问**同名同签名**（名相同 + 参数个数相同 + ≥2 份实现）的候选组。

    与骨架聚类互补——骨架不同但职责相同的重写由本判据暴露。只报候选，是否合并仍按 `_pool.md` §5.1 五条判据
    并 `--pairs` 对拍确认（**禁止**凭名同就合并：同名不同口径是常见且合法的）。
    """
    by = defaultdict(list)
    for r in recs:
        if r["func"].strip("_").lower() in GENERIC_NAMES:
            continue
        by[(r["func"], len(r["args"]))].append(r)
    out: list = []
    for (_name, _nargs), ms in by.items():
        if len({m["file"] for m in ms}) < 2:
            continue
        qs = {q for q in (_qtag(m["zone"], m["file"]) for m in ms) if q}
        exact = len({",".join(m["args"]) for m in ms}) == 1
        ms.sort(key=lambda m: (q_index(m["zone"]), m["file"], m["line"]))
        out.append({
            "confidence": "high" if exact else "medium",
            "func": ms[0]["func"], "nargs": _nargs,
            "cross_question": len(qs) >= 2, "questions": sorted(qs),
            "canonical": "%s:%d" % (ms[0]["file"], ms[0]["line"]),
            "members": ["%s:%d %s(%s)" % (m["file"], m["line"], m["func"], ", ".join(m["args"])) for m in ms],
            "detail": "%d 份同名同参数个数实现（%s 置信）%s" % (
                len(ms), "high" if exact else "medium",
                "，**跨小问**" if len(qs) >= 2 else "（同小问内）")})
    out.sort(key=lambda g: (not g["cross_question"], g["confidence"] != "high", -len(g["members"]), g["func"]))
    return out


def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def registry(root: Path) -> dict:
    pm = load_json(root / "pool" / "manifest.json") or {}
    om = load_json(root / "pool" / "problem" / "manifest.json") or {}
    qm = load_json(root / "probes" / "manifest.json") or {}
    qa = load_json(root / "probes" / "manifest.archive.json") or {}      # 归档条目也算已登记
    probes = {str((v or {}).get("script", "")).lstrip("./")
              for src in (qm, qa) for v in (src.get("probes") or {}).values()}
    return {"prim": set((pm.get("entries") or {})), "problem": set((om.get("entries") or {})),
            "probes": {p for p in probes if p}}


def is_registered(zone: str, rel: str, fname: str, reg: dict):
    if zone == "prim":
        ok = fname in reg["prim"]
        return ok, "pool/manifest.json" if ok else "（原语未登记）"
    if zone == "problem":
        stem = Path(rel).stem
        ok = any(k == stem or k.startswith(stem + ".") or ("." + stem + ".") in k for k in reg["problem"])
        return ok, "pool/problem/manifest.json" if ok else "（题专用核心未登记）"
    if zone == "probe":
        ok = rel in reg["probes"]
        return ok, "probes/manifest.json" if ok else "（探针未登记）"
    return False, "（小问目录内实现，未入池）"


def scan(root: Path, dirs, min_stmts: int):
    files = iter_files(root, dirs)
    groups = defaultdict(list)
    recs: list = []                      # 第二判据（跨问同名同签名）用：全函数原始记录，与骨架无关
    funcs = 0
    zones = defaultdict(int)
    for f, zone in files:
        zones[zone] += 1
        try:
            with warnings.catch_warnings():          # 被检源里的 `\{` 之类非法转义会刷 SyntaxWarning，与被检结论无关
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.name.startswith("__"):
                continue
            if n_stmts(node) < min_stmts:
                continue
            sk = skeleton(node)
            if not sk:
                continue
            funcs += 1
            try:
                rel = str(f.relative_to(root))
            except ValueError:
                rel = str(f)
            rec = {"file": rel, "line": node.lineno, "func": node.name,
                   "args": [a.arg for a in node.args.args], "zone": zone}
            groups[(sk, len(node.args.args))].append(rec)
            recs.append(rec)
    reg = registry(root)
    out: list = []
    for _k, members in groups.items():
        vis = {m["file"] for m in members}
        if len(vis) < 2:
            continue
        members.sort(key=lambda m: (q_index(m["zone"]), m["file"], m["line"]))
        canon = members[0]
        names = {m["func"].strip("_").lower() for m in members}
        argsets = {",".join(m["args"]) for m in members}
        confidence = "high" if (len(names) == 1 or len(argsets) == 1) else "medium"
        qs = {m["zone"].split(":")[0] for m in members if ":" in m["zone"]}
        ok, where = is_registered(canon["zone"], canon["file"], canon["func"], reg)
        out.append({
            "confidence": confidence, "func": canon["func"],
            "canonical": "%s:%d" % (canon["file"], canon["line"]),
            "canonical_registered": ok, "registry": where,
            "cross_question": len(qs) >= 2, "questions": sorted(qs),
            "members": ["%s:%d %s(%s)" % (m["file"], m["line"], m["func"], ", ".join(m["args"])) for m in members],
            "detail": "%d 份同形实现（%s 置信）%s%s" % (len(members), confidence,
                       "，跨小问" if len(qs) >= 2 else "", "" if ok else "，且权威份未登记")})
    out.sort(key=lambda g: (-(g["confidence"] == "high"), -len(g["members"]), g["func"]))
    ss_out = samesig(recs)
    stats = {"files": len(files), "funcs": funcs, "groups": len(out),
             "cross_question": sum(1 for g in out if g["cross_question"]),
             "unregistered": sum(1 for g in out if not g["canonical_registered"]),
             "same_sig": len(ss_out),
             "same_sig_cross": sum(1 for g in ss_out if g["cross_question"]),
             "same_sig_high_cross": sum(1 for g in ss_out if g["cross_question"] and g["confidence"] == "high"),
             "zones": dict(zones)}
    return out, ss_out, stats


def _cmp(a, b, rtol: float, atol: float) -> bool:
    if hasattr(a, "tolist") or hasattr(b, "tolist"):     # 一侧 ndarray、一侧 list 时也要能比
        a = a.tolist() if hasattr(a, "tolist") else a
        b = b.tolist() if hasattr(b, "tolist") else b
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_cmp(a[k], b[k], rtol, atol) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_cmp(x, y, rtol, atol) for x, y in zip(a, b))
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= atol + rtol * max(abs(a), abs(b))
    return a == b


def pairs(a_path: str, b_path: str, inputs, rtol: float, atol: float):
    import importlib.util

    def load(p: str, alias: str):
        if not Path(p).is_file():
            raise FileNotFoundError(f"文件不存在：{p}")
        spec = importlib.util.spec_from_file_location(alias, p)
        if spec is None or spec.loader is None:
            raise ImportError(f"无法按路径加载：{p}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[alias] = mod
        spec.loader.exec_module(mod)          # 语法错误 / 顶层异常在这里抛出
        return mod

    try:
        ma, mb = load(a_path, "reuse_a"), load(b_path, "reuse_b")
    except Exception as exc:                  # noqa: BLE001 —— 明确告诉调用方是哪个文件、什么问题
        print(f"[错误] 无法加载待对拍脚本：{type(exc).__name__}: {exc}", file=sys.stderr)
        return [], 2
    rows: list = []
    mism = 0
    for name in sorted(n for n in dir(ma) if not n.startswith("_")):
        fa = getattr(ma, name)
        fb = getattr(mb, name, None)
        if not callable(fa) or not callable(fb):
            continue
        if inputs is None:
            rows.append({"func": name, "verdict": "STATIC",
                         "detail": "未给 --inputs，仅比对同名可调用存在性；判定同口径须提供输入对拍"})
            continue
        try:
            ra, rb = fa(**inputs), fb(**inputs)
        except Exception as exc:                      # noqa: BLE001 —— 被检脚本异常如实报出
            rows.append({"func": name, "verdict": "ERR", "detail": ("%s: %s" % (type(exc).__name__, exc))[:200]})
            mism += 1
            continue
        same = _cmp(ra, rb, rtol, atol)
        rows.append({"func": name, "verdict": "MATCH" if same else "DIFF",
                     "detail": "rtol=%g atol=%g%s" % (rtol, atol, "" if same else "；A=%r B=%r" % (ra, rb))})
        if not same:
            mism += 1
    return rows, (1 if mism else 0)


def selftest_samesig() -> int:
    """第二判据的反例自检：造一棵临时 run 树，逐条断言「该报的报、该放过的放过」。"""
    tmp = Path(tempfile.mkdtemp(prefix="reuse_lint_selftest_"))

    def w(rel: str, body: str):
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")

    S3 = "    a = x + 1\n    b = a * 2\n    return b\n"
    S4 = "    a = x + 1\n    b = a * 2\n    c = b - 1\n    return c\n"
    w("intermediates/q1/05-implementation/code/a.py", "def alpha(x, y):\n" + S3)   # ① 应报（high）
    w("intermediates/q2/05-implementation/code/b.py", "def alpha(x, y):\n" + S3)
    w("intermediates/q1/05-implementation/code/c.py", "def beta(x, y):\n" + S3)    # ② 应放过（参数个数不同）
    w("intermediates/q2/05-implementation/code/d.py", "def beta(x, y, z):\n" + S4)
    w("intermediates/q1/05-implementation/code/e.py", "def main(x):\n" + S3)       # ③ 应放过（通用名）
    w("intermediates/q2/05-implementation/code/f.py", "def main(x):\n" + S3)
    w("intermediates/q1/05-implementation/code/g.py", "def gamma(x):\n" + S3)      # ④ 应放过（同小问内）
    w("intermediates/q1/06-computation/h.py", "def gamma(x):\n" + S3)
    w("probes/other/q1_ramp.py", "def ramp(t, T):\n" + S3)                        # ⑤ 应报（medium，探针按名推小问）
    w("probes/other/q2_ramp.py", "def ramp(x, y):\n" + S3)
    w("intermediates/q3/05-implementation/code/i.py", "def delta(x):\n" + S3)      # ⑥ 应放过（仅一份）
    try:
        _g, ss, stats = scan(tmp, None, MIN_STMTS_DEFAULT)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    cross = {g["func"]: g for g in ss if g["cross_question"]}
    within = {g["func"]: g for g in ss if not g["cross_question"]}
    checks = [
        ("① 跨问同名同签名被报出", set(cross) == {"alpha", "ramp"}),
        ("① high 档 = 参数名亦一致", cross.get("alpha", {}).get("confidence") == "high"),
        ("⑤ medium 档 = 仅参数个数一致", cross.get("ramp", {}).get("confidence") == "medium"),
        ("② 同名但参数个数不同 → 不报", "beta" not in cross and "beta" not in within),
        ("③ 通用名 main → 不报", "main" not in cross and "main" not in within),
        ("④ 同小问内 → 不计入跨问", "gamma" in within and "gamma" not in cross),
        ("⑥ 只有一份实现 → 不报", "delta" not in cross and "delta" not in within),
        ("stats 计数与组数一致", stats["same_sig"] == len(ss) and stats["same_sig_cross"] == len(cross)),
        ("探针文件名推定小问生效", cross.get("ramp", {}).get("questions") == ["q1", "q2"]),
    ]
    print("# reuse_lint --selftest（第二判据：跨问同名同签名）")
    nok = 0
    for name, ok in checks:
        print("  [%s] %s" % ("OK" if ok else "!!", name))
        nok += 1 if ok else 0
    print("自检通过 %d/%d" % (nok, len(checks)))
    if nok != len(checks):
        print("候选组实测：%s" % json.dumps(ss, ensure_ascii=False, indent=1)[:1200])
    return 0 if nok == len(checks) else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="复用率机械核验（重复实现检测 + 对拍）")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--scan", action="store_true", help="扫描同形重复实现")
    g.add_argument("--pairs", nargs=2, metavar=("A.py", "B.py"), help="同输入对拍两份实现")
    g.add_argument("--selftest", action="store_true", help="第二判据（跨问同名同签名）的反例自检")
    ap.add_argument("--root", default=".", help="outputDir（默认当前目录）")
    ap.add_argument("--dirs", default=None, help="自定义扫描目录（逗号分隔，相对 --root）")
    ap.add_argument("--json", dest="json_out", default=None, help="结构化结果落盘")
    ap.add_argument("--min-stmts", type=int, default=MIN_STMTS_DEFAULT,
                    help="忽略语句数少于此的函数（默认 %d）" % MIN_STMTS_DEFAULT)
    ap.add_argument("--strict", action="store_true", help="有跨小问重复组 → 退出码 1")
    ap.add_argument("--strict-samesig", action="store_true",
                    help="有跨小问同名同签名（high 档）→ 退出码 1（默认只报不阻塞）")
    ap.add_argument("--inputs", default=None, help="--pairs 的 JSON 关键字参数")
    ap.add_argument("--rtol", type=float, default=1e-9)
    ap.add_argument("--atol", type=float, default=1e-12)
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest_samesig()

    if args.pairs:
        try:
            inputs = json.loads(args.inputs) if args.inputs else None
        except json.JSONDecodeError as exc:
            print("[错误] --inputs 不是合法 JSON：%s" % exc, file=sys.stderr)
            return 2
        rows, rc = pairs(args.pairs[0], args.pairs[1], inputs, args.rtol, args.atol)
        if rc == 2 and not rows:
            return 2
        if not rows:
            print("两份实现没有同名可调用对象 → 不是同口径实现，无需对拍")
            return 0
        print("# reuse_lint 对拍 — %s vs %s" % (args.pairs[0], args.pairs[1]))
        for r in rows:
            print("[%s] %s: %s" % (r["verdict"], r["func"], r["detail"]))
        if rc:
            print("\n✗ 存在分歧/异常：**不得合并**，按口径分叉处理（写差异理由或各自 scope 登记）", file=sys.stderr)
        return rc

    root = Path(args.root).expanduser()
    if not root.is_dir():
        print("[错误] 不是目录：%s" % root, file=sys.stderr)
        return 2
    dirs = [d.strip() for d in args.dirs.split(",")] if args.dirs else None
    if dirs:
        missing = [d for d in dirs if not (Path(d) if Path(d).is_absolute() else root / d).is_dir()]
        if missing:
            print("[错误] --dirs 目录不存在：%s（相对 %s 解析）" % (", ".join(missing), root), file=sys.stderr)
            return 2
    groups, ss_groups, stats = scan(root, dirs, args.min_stmts)
    ss_cross = [g for g in ss_groups if g["cross_question"]]
    ss_within = [g for g in ss_groups if not g["cross_question"]]
    print("# reuse_lint 报告 — %s" % root)
    print("- 扫描 .py %d 份 / 函数 %d 个（分区：%s）" % (
        stats["files"], stats["funcs"], "、".join("%s %d" % kv for kv in sorted(stats["zones"].items()))))
    print("- 同形重复组 %d 个，其中跨小问 %d 个、权威份未登记 %d 个" % (
        stats["groups"], stats["cross_question"], stats["unregistered"]))
    print("- 跨问同名同签名候选 %d 组（跨小问 %d / 同小问内 %d；high 档跨问 %d）—— 默认只报不阻塞" % (
        stats["same_sig"], len(ss_cross), len(ss_within), stats["same_sig_high_cross"]))
    if stats["files"] == 0:
        print("[警告] 扫描到 0 个 .py —— 检查 --root/--dirs 是否指对（中文路径、拼写、目录层级）", file=sys.stderr)
        if args.strict:
            return 2
    if not groups:
        print("- 未发现同形重复实现")
    for i, gp in enumerate(groups[:12], 1):
        print("\n[G%d] %s 置信｜%s：%s" % (i, gp["confidence"], gp["func"], gp["detail"]))
        print("    建议权威：%s（%s）" % (gp["canonical"], gp["registry"]))
        for m in gp["members"]:
            print("    - %s" % m)
        print("    处置：后写份改 import 建议权威（同问内改动须重跑 06）；口径不一致 → 写差异理由并各自登记 scope")
    if len(groups) > 12:
        print("\n（其余 %d 组见 --json）" % (len(groups) - 12))
    if ss_cross:
        print("\n—— 第二判据：跨小问**同名同签名**（同职责各写一份的候选；需人工确认口径后按 `_pool.md` §5.1 处置）——")
        for i, gp in enumerate(ss_cross[:12], 1):
            print("\n[S%d] %s 置信｜%s（%d 参数）：%s" % (i, gp["confidence"], gp["func"], gp["nargs"], gp["detail"]))
            for m in gp["members"][:6]:
                print("    - %s" % m)
            if len(gp["members"]) > 6:
                print("    - …（共 %d 份，见 --json）" % len(gp["members"]))
        if len(ss_cross) > 12:
            print("\n（其余 %d 组见 --json）" % (len(ss_cross) - 12))
        print("处置：**先判口径**——同口径 ⇒ 合并进池/改 import 权威份（改动须重跑该问 06）；"
              "口径确有分叉 ⇒ 写差异理由并各自登记 scope。禁止仅凭同名就合并。")
        print("读法：`high` = 参数名亦一致（优先看）；`medium` = 仅参数个数一致——其中**成员数很大**的组"
              "（如各探针里的局部 `compute`）通常是命名惯例而非同职责，需看 members 的实参语境再定。")
    elif ss_within:
        print("\n- 无跨小问同名同签名；同小问内有 %d 组（见 --json）" % len(ss_within))
    else:
        print("\n- 未发现同名同签名候选")
    print("\n汇总：同形重复组 %d；同名同签名候选 %d 组（跨问 %d）；判定阈值：函数语句数 ≥%d、骨架同形 / 同名同参数个数" % (
        stats["groups"], stats["same_sig"], len(ss_cross), args.min_stmts))
    if args.json_out:
        try:
            Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.json_out).write_text(
                json.dumps({"root": str(root), "stats": stats, "groups": groups,
                            "same_sig_groups": ss_groups}, ensure_ascii=False, indent=2), encoding="utf-8")
            print("JSON：%s" % args.json_out)
        except OSError as exc:
            print("[错误] 无法写 --json（%s）：%s（报告已在上方 stdout，可自行保存）" % (args.json_out, exc), file=sys.stderr)
            return 2
    rc = 0
    if args.strict and stats["cross_question"]:
        rc = 1
    if args.strict_samesig and stats["same_sig_high_cross"]:
        print("\n✗ --strict-samesig：跨问同名同签名（high 档）%d 组" % stats["same_sig_high_cross"], file=sys.stderr)
        rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
