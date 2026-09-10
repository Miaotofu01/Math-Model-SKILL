#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""primitives.py —— 通用原语池 + 登记/自检框架（math-model skill 技能级工具）

**硬规则：本文件只装机制与判据，不装任何单题内容。**
技能根副本会被此后每一个 run 继承，任何一次题目的建模选择写进来都会污染后续所有题。
（上一次 run 的单题条目曾以此身份发货，已归档 `docs/cases/`，不再随技能发货——
个例的正确归宿是案例留档或 `pool/problem/<题>/`，永远不是技能根。）

- **可进本文件**：库不提供 + 口径敏感 + 领域中立（纯数学定义，不含题目建模选择），
  且已有 ≥2 个不同题的复用证据。
- **单题条目**：写 `<outputDir>/pool/problem/<题>/*.py`，并按 `_common.md` §5.1 登记
  `pool/problem/manifest.json`。

用法
----
    python3 <技能根>/scripts/primitives.py --selftest           # 自检（含暴力对拍）
    python3 <技能根>/scripts/primitives.py --manifest out.json  # 签名/单位/对拍值/耗时
    python3 <技能根>/scripts/primitives.py --list

**首要动作（各阶段 agent）**：先 `--list` 查条目；有同口径条目才
`cp <技能根>/scripts/primitives.py <outputDir>/pool/primitives.py`（run 级副本，产物自包含），
此后一律 `import` 复用，**禁止再写慢副本**。改动本文件后必须 `--selftest` 全绿并递增 VERSION
（VERSION 参与探针缓存指纹）。

**新增一条的流程**：① 过 `_common.md` §5.1 的五条进池判据；② 加 `@primitive(...)` 元数据；
③ 在 `_selftest()` 加**独立暴力实现/解析解对拍**（只做自洽检查不算）；④ 在 `_manifest()` 的
timing_cases 加一条实测；⑤ `--selftest` 全绿 + VERSION 递增。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

VERSION = "2.0.0"   # 2.0.0：清出单题条目；数值类（二分/bootstrap/DE）交回 scipy 或按判据进 pool/problem/
PRIMITIVES: dict[str, dict] = {}


def primitive(name: str, signature: str, units: str, returns: str, deps: str = "numpy"):
    """登记原语元数据（供 manifest/清单输出）。"""
    def deco(fn):
        PRIMITIVES[name] = {"name": name, "signature": signature, "units": units,
                            "returns": returns, "deps": deps, "version": VERSION}
        return fn
    return deco


# ─────────────────────────── 几何（纯定义，无建模选择） ───────────────────────────

@primitive("point_segment_distance",
           "point_segment_distance(P, A, B, eps=1e-12) -> ndarray",
           "与输入同单位（长度）；P/A/B 任意维、广播到同一批点",
           "每个点到线段 AB 的最短距离（点到直线距离在 [0,|AB|] 上截断）")
def point_segment_distance(P, A, B, eps: float = 1e-12) -> np.ndarray:
    """点到**线段**（不是直线）的最短距离。P:(n,d) 或 (d,)；A、B:(d,) 或广播。"""
    P = np.asarray(P, dtype=float)
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    AB = B - A
    denom = float(np.dot(AB, AB))
    if denom < eps:                                   # 退化线段 → 点距
        return np.linalg.norm(P - A, axis=-1)
    t = np.clip(((P - A) @ AB) / denom, 0.0, 1.0)     # 投影参数截断到 [0,1]
    proj = A + t[..., None] * AB
    return np.linalg.norm(P - proj, axis=-1)


@primitive("min_distance_to_segment_batch",
           "min_distance_to_segment_batch(points, A, B) -> float",
           "长度单位；points:(n,3) 或 (n,d)",
           "一批点到线段 AB 的最小距离（判据常用：min ≥ 阈值 ⇔ 全体在阈值外）")
def min_distance_to_segment_batch(points, A, B) -> float:
    """空点集 → `inf`（「没有任何点」= 约束恒满足，而不是抛异常）。"""
    d = point_segment_distance(np.asarray(points, dtype=float), A, B)
    return float(np.min(d)) if d.size else float("inf")


# ─────────────────────────── 区间（纯集合运算，无库对应） ───────────────────────────

@primitive("interval_union", "interval_union(intervals) -> list[tuple[float,float]]",
           "与输入同单位", "并集后的**互不相交**区间列表，按左端点升序")
def interval_union(intervals: Iterable[Sequence[float]]) -> list[tuple[float, float]]:
    iv = sorted((float(a), float(b)) for a, b in intervals if float(b) > float(a))
    out: list[list[float]] = []
    for a, b in iv:
        if out and a <= out[-1][1] + 1e-15:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


@primitive("interval_total", "interval_total(intervals) -> float",
           "与输入同单位", "区间并集的总测度（去重叠）")
def interval_total(intervals: Iterable[Sequence[float]]) -> float:
    return float(sum(b - a for a, b in interval_union(intervals)))


# ─────────────────────────── 自检（含暴力对拍） ───────────────────────────

def _selftest() -> list[str]:
    """返回失败项列表（空 = 全绿）。含独立暴力实现对拍，不只是自洽检查。"""
    bad: list[str] = []
    rng = np.random.default_rng(0)

    # 1) point_segment_distance vs 稠密采样暴力
    P = rng.normal(size=(40, 3))
    A, B = np.array([0.0, 0.0, 0.0]), np.array([2.0, 1.0, -1.0])
    got = point_segment_distance(P, A, B)
    ts = np.linspace(0, 1, 200001)
    seg = A + ts[:, None] * (B - A)
    brute = np.min(np.linalg.norm(P[:, None, :] - seg[None, :, :], axis=-1), axis=1)
    if not np.allclose(got, brute, atol=1e-4):
        bad.append(f"point_segment_distance 与暴力对拍不符 max_err={np.max(np.abs(got - brute)):.2e}")
    if abs(point_segment_distance(np.array([5.0, 0, 0]), A, B) - np.linalg.norm([5.0, 0, 0] - B)) > 1e-12:
        bad.append("point_segment_distance 未在端点截断（退化为直线距离）")
    if abs(point_segment_distance(np.array([0.0, 3.0, 0]), np.zeros(3), np.zeros(3)) - 3.0) > 1e-12:
        bad.append("point_segment_distance 退化线段未回退为点距")
    if abs(min_distance_to_segment_batch(P, A, B) - float(np.min(got))) > 1e-15:
        bad.append("min_distance_to_segment_batch 与 point_segment_distance 不一致")
    if min_distance_to_segment_batch(np.zeros((0, 3)), A, B) != float("inf"):
        bad.append("min_distance_to_segment_batch 空点集未返回 inf")

    # 2) interval_union/total vs 朴素并集测度：[(0,2),(1.5,3),(2.5,4),(5,6),(6,7.5)] → (0,4)∪(5,7.5) = 4+2.5
    iv = [(0, 2), (1.5, 3), (5, 6), (6, 7.5), (2.5, 4)]
    if abs(interval_total(iv) - 6.5) > 1e-12:
        bad.append(f"interval_total={interval_total(iv)} ≠ 6.5")
    if interval_union([(0, 1), (1, 2)]) != [(0.0, 2.0)]:
        bad.append("interval_union 未合并相接区间")
    if interval_total([]) != 0.0 or interval_union([(1, 1)]) != []:
        bad.append("interval_union 未丢弃零测/空区间")
    return bad


def _manifest() -> dict:
    """生成 manifest 条目：签名/单位/返回语义/依赖/版本/对拍值/实测耗时。"""
    src = Path(__file__).read_bytes()
    out = {"primitivesVersion": VERSION, "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "sourceSha256": hashlib.sha256(src).hexdigest()[:16],
           "selftest": {"passed": not _selftest()}, "entries": {}}
    timing_cases = {
        "point_segment_distance": lambda: point_segment_distance(np.random.default_rng(0).normal(size=(200_000, 3)),
                                                                  [0, 0, 0], [1, 1, 1]),
        "interval_total": lambda: interval_total([(0, 2), (1.5, 3), (5, 6)]),
    }
    for name, meta in PRIMITIVES.items():
        e = dict(meta)
        fn = timing_cases.get(name)
        if fn:
            t0 = time.perf_counter()
            fn()
            e["timing_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
        out["entries"][name] = e
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="math-model 通用原语池（只装通用原语；单题条目写 pool/problem/<题>/）")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--selftest", action="store_true", help="自检（含暴力对拍）")
    g.add_argument("--manifest", metavar="OUT.json", help="输出 manifest（含对拍值与耗时）")
    g.add_argument("--list", action="store_true", help="列出原语签名")
    args = ap.parse_args(argv)

    if args.list:
        for n, m in PRIMITIVES.items():
            print(f"{n}\n    {m['signature']}\n    单位：{m['units']}\n    返回：{m['returns']}")
        print(f"\n共 {len(PRIMITIVES)} 条通用原语（版本 {VERSION}）。本文件不含单题内容；"
              f"题专用条目写 <outputDir>/pool/problem/<题>/ 并登记 pool/problem/manifest.json（_common.md §5.1）。")
        return 0
    if args.selftest:
        bad = _selftest()
        if bad:
            print("✗ selftest 失败：\n  - " + "\n  - ".join(bad))
            return 1
        print(f"✓ primitives selftest 通过（{len(PRIMITIVES)} 个原语，版本 {VERSION}）")
        return 0
    man = _manifest()
    # 版本守卫基线存在**清单之外**的伴生文件里：清单自身每次都会被覆盖，写在里面只能报警一次
    base_path = args.manifest + ".baseline.json"
    baseline: dict = {}
    try:
        with open(base_path, encoding="utf-8") as fh:
            loaded = json.load(fh)
        baseline = loaded if isinstance(loaded, dict) else {}
    except (OSError, json.JSONDecodeError):
        baseline = {}
    stale_prev = None
    known = baseline.get(man["primitivesVersion"])
    if known and known != man["sourceSha256"]:
        stale_prev = {"sourceSha256": known}          # 同版本、内容变了 → 未递增版本
    try:
        Path(args.manifest).parent.mkdir(parents=True, exist_ok=True)
        Path(base_path).parent.mkdir(parents=True, exist_ok=True)
        with open(args.manifest, "w", encoding="utf-8") as fh:
            json.dump(man, fh, ensure_ascii=False, indent=2)
        if not stale_prev:                            # 版本已递增（新版本）→ 记录新基线
            baseline[man["primitivesVersion"]] = man["sourceSha256"]
            with open(base_path, "w", encoding="utf-8") as fh:
                json.dump(baseline, fh, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"✗ 写入失败：{exc}（退出码 2 = 参数/路径错误，请检查目录权限）", file=sys.stderr)
        return 2
    print(f"manifest 写入 {args.manifest}；selftest={'PASS' if man['selftest']['passed'] else 'FAIL'}；"
          f"条目 {len(man['entries'])}；scope={man['sourceSha256']}")
    if not man["selftest"]["passed"]:
        return 1
    if stale_prev:
        print(f"\n✗ 退出码 1（需动作，不是工具故障）：本文件内容已变，但 VERSION 仍是 {VERSION}"
              f"（基线指纹 {stale_prev['sourceSha256']} → 当前 {man['sourceSha256']}）。\n"
              f"  探针缓存指纹含 primitivesVersion → 不递增版本会让缓存**静默命中过期结论**。\n"
              f"  处理：把 VERSION 递增（如 {VERSION} → 下一版号）后重跑本命令。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
