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
import glob
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

# 2.1.0：把探针里被手写 14+19 份的两支样板（技能根定位 / 起步窗加密 t_out 阶梯）收进池
VERSION = "2.1.0"
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


# ─────────────────────── 环境/时间轴样板（纯机制，不含题目内容） ───────────────────────

_SKILL_SCRIPTS_ENV = "MATH_MODEL_SKILL_SCRIPTS"
_SKILL_SCRIPTS_MARKERS = ("probe_cache.py",)      # 判据：该目录确实是技能根 scripts/
_SKILL_SCRIPTS_GLOBS = ("~/.dsh/skills/*/scripts", "~/.claude/skills/*/scripts")
_MODULE_DIR = Path(__file__).resolve().parent     # 导入期定死 → 此后与 cwd 无关
_GRID_TOL = 1e-9


@primitive("find_skill_scripts",
           'find_skill_scripts(env_var="MATH_MODEL_SKILL_SCRIPTS", markers=("probe_cache.py",), '
           'install_globs=("~/.dsh/skills/*/scripts", "~/.claude/skills/*/scripts")) -> Path',
           "路径（pathlib.Path，绝对）；无单位",
           "技能根 scripts/ 目录：在「环境变量 → 本文件所在目录 → install_globs 展开（排序）」候选中，"
           "取第一个**确实含 markers 全部文件**者；都不符则 ModuleNotFoundError")
def find_skill_scripts(env_var: str = _SKILL_SCRIPTS_ENV,
                       markers: Sequence[str] = _SKILL_SCRIPTS_MARKERS,
                       install_globs: Sequence[str] = _SKILL_SCRIPTS_GLOBS) -> Path:
    """定位技能根 `scripts/`（内含 `probe_cache.py`/`primitives.py`）——**不要再手写候选列表**。

    机制与判据：候选目录**必须含 markers 全部文件**才算命中（只按路径猜会把 run 级 `pool/`
    副本误认成技能根）；优先级 = ① `env_var` 环境变量 → ② 本文件所在目录（技能根副本自身命中；
    `pool/` 副本不含探针缓存，自动下探）→ ③ 已知安装位 glob（排序保证同机确定）。
    纯函数：不改 `sys.path`、不改环境变量；调用方自行 `sys.path.insert(0, str(find_skill_scripts()))`。

    注意引导顺序：本函数自身也要先 import 到——走 `probe_cache.py --run` 时已注入
    `<outputDir>/pool`，纯 `python probes/x.py` 直跑请设 `PYTHONPATH=<outputDir>/pool`，
    或由调度壳设好 `env_var`（唯一无「鸡生蛋」的引导方式）。
    """
    cands: list[Path] = []
    from_env = os.environ.get(env_var, "").strip()
    if from_env:
        cands.append(Path(from_env).expanduser())
    cands.append(_MODULE_DIR)
    for pattern in install_globs:
        cands.extend(sorted(Path(p) for p in glob.glob(os.path.expanduser(str(pattern)))))
    seen: set[Path] = set()
    for cand in cands:
        try:
            resolved = cand.resolve()
        except OSError:                            # 坏链接/无权限候选 → 当作不成立，继续下探
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if all((resolved / m).is_file() for m in markers):
            return resolved
    raise ModuleNotFoundError(
        f"找不到技能根 scripts/（判据：目录内含 {'、'.join(markers)}）。"
        f"请设 {env_var}=<技能根>/scripts 后重跑；**禁止把池中实现内联抄一份**")


def _timed_find_skill_scripts() -> bool:
    """`--manifest` 计时用包装：技能根不可达时返回 False 而不抛（清单恒能产出）。"""
    try:
        find_skill_scripts()
        return True
    except ModuleNotFoundError:
        return False


@primitive("ramp_t_out",
           "ramp_t_out(t_end, t_fine_end, dt_fine, dt_coarse, dt_out=60.0) -> ndarray",
           "秒（s）：t_end/t_fine_end 为时间上界，dt_* 为步长；返回一维 t_out",
           "起步窗 [0,t_fine_end] 按 dt_fine 逐点加密、窗后只保留 dt_out 整数倍（交付行）的"
           "严格递增时间轴，含 t=0")
def ramp_t_out(t_end: float, t_fine_end: float, dt_fine: float,
               dt_coarse: float, dt_out: float = 60.0) -> np.ndarray:
    """起步窗加密的 `t_out` 阶梯（阶梯本身，不含任何题目的窗口数值）。

    机制（两道口径，缺一不可）：
      ① **内部步**：起步窗 `(0, t_fine_end]` 用 `dt_fine` 逐点加密；窗后改用 `dt_coarse`
         生成内部步格点（`dt_coarse` 的整数倍，**绝对格点**——避免从窗末点续推导致与交付格错位）。
      ② **交付子集**：起步窗内的点**全部保留**（加密不被抹掉）；窗后只保留 `dt_out` 整数倍的
         交付行。故 `dt_coarse < dt_out` 时返回的是「密内部步被抽稀成 60 s 行」的阶梯，
         `dt_coarse == dt_out` 时即「细窗逐行 + 窗后一行 60 s」。

    边界（判据外置、行为确定）：`t_fine_end` 钳到 `[0, t_end]`；`t_fine_end` 不是 `dt_fine`
    整数倍时窗内取 `floor(t_fine_end/dt_fine)` 个步（不越过窗端）；`t_fine_end=0` ⇒ 无起步窗；
    `t_end < t_fine_end` ⇒ 只留 `0..t_end` 的加密段。步长非正 ⇒ `ValueError`。
    """
    t_end = float(t_end)
    dt_fine, dt_coarse, dt_out = float(dt_fine), float(dt_coarse), float(dt_out)
    for name, val in (("t_end", t_end), ("dt_fine", dt_fine),
                      ("dt_coarse", dt_coarse), ("dt_out", dt_out)):
        if not val > 0.0:
            raise ValueError(f"ramp_t_out：{name}={val} 必须为正（时间上界/步长口径）")
    t_fine = min(max(float(t_fine_end), 0.0), t_end)

    n_fine = int(np.floor(t_fine / dt_fine + _GRID_TOL))
    fine = np.arange(1, n_fine + 1, dtype=float) * dt_fine          # 窗内：dt_fine 逐点（不含 0）
    n_coarse = int(np.floor(t_end / dt_coarse + _GRID_TOL))
    coarse = np.arange(1, n_coarse + 1, dtype=float) * dt_coarse    # 窗后内部步：dt_coarse 绝对格点
    coarse = coarse[coarse > t_fine + _GRID_TOL]                    # 窗内已由 dt_fine 覆盖
    k = np.round(coarse / dt_out)
    coarse = coarse[np.abs(coarse - k * dt_out) <= _GRID_TOL]       # 只留交付行（dt_out 整数倍）

    t = np.round(np.concatenate(([0.0], fine, coarse)), 10)
    if t.size and np.any(np.diff(t) <= 0.0):
        raise ValueError("ramp_t_out：t_out 非严格递增（t_fine_end/dt_fine/dt_coarse 组合有误）")
    return t


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

    # 3) find_skill_scripts vs 独立判据：返回目录**文件真在** + 与 cwd 无关（不是自洽检查）
    try:
        found: Path | None = find_skill_scripts()
    except ModuleNotFoundError as exc:
        found = None
        if (_MODULE_DIR / "probe_cache.py").is_file():     # 技能根副本上必须找得到
            bad.append(f"find_skill_scripts 在技能根副本上仍失败：{exc}")
    if found is not None:
        for marker in ("probe_cache.py", "primitives.py"):
            if not (found / marker).is_file():
                bad.append(f"find_skill_scripts 返回 {found}，但其下不存在 {marker}")
        cwd0 = Path.cwd()
        try:
            for probe_cwd in (Path(tempfile.gettempdir()).resolve(), Path("/")):
                os.chdir(probe_cwd)
                try:
                    again: Path | None = find_skill_scripts()
                except ModuleNotFoundError:
                    again = None
                if again != found:
                    bad.append(f"find_skill_scripts 依赖 cwd：{probe_cwd} 下得 {again} ≠ {found}")
        finally:
            os.chdir(cwd0)
        with tempfile.TemporaryDirectory() as empty:       # 判据负例：空目录不得被当成技能根
            prev = os.environ.get(_SKILL_SCRIPTS_ENV)
            os.environ[_SKILL_SCRIPTS_ENV] = empty
            try:
                neg = find_skill_scripts()
            except ModuleNotFoundError:
                neg = None
            finally:
                if prev is None:
                    os.environ.pop(_SKILL_SCRIPTS_ENV, None)
                else:
                    os.environ[_SKILL_SCRIPTS_ENV] = prev
            if neg is not None and neg == Path(empty).resolve():
                bad.append("find_skill_scripts 未校验 markers：空目录（无 probe_cache.py）被当成技能根")

    # 4) ramp_t_out vs 独立逐点暴力实现（含非整除/无窗/窗越界边界）
    def _brute_ramp(t_end, t_fine_end, dt_fine, dt_coarse, dt_out):
        """独立暴力实现：从 0 起逐点推进（不做格点向量化），再按判据筛 60 s 子集。"""
        tf = min(max(float(t_fine_end), 0.0), float(t_end))
        pts = [0.0]
        t = 0.0
        while t + dt_fine <= tf + 1e-9:                    # 起步窗：逐点 +dt_fine
            t += dt_fine
            pts.append(t)
        u = 0.0
        while u + dt_coarse <= float(t_end) + 1e-9:        # 窗后：逐点 +dt_coarse
            u += dt_coarse
            if u > tf + 1e-9 and abs(u - round(u / dt_out) * dt_out) <= 1e-9:
                pts.append(u)                              # 只留 dt_out 整数倍＝交付行
        return np.array(pts, dtype=float)

    ramp_cases = [
        (86400.0, 600.0, 0.5, 60.0, 60.0),    # 基准：窗端同为 dt_fine/dt_coarse 整数倍
        (3600.0, 100.3, 0.7, 10.0, 60.0),     # 边界：t_fine_end 非 dt_fine 整数倍；dt_coarse≠dt_out
        (600.0, 0.0, 0.5, 60.0, 60.0),        # 边界：t_fine_end=0（无起步窗）
        (90.0, 600.0, 0.5, 60.0, 60.0),       # 边界：t_end < t_fine_end（窗端钳到 t_end）
    ]
    for te, tf, df, dc, do in ramp_cases:
        tag = f"ramp_t_out({te},{tf},{df},{dc},{do})"
        try:
            got = ramp_t_out(te, tf, df, dc, do)
        except Exception as exc:                           # noqa: BLE001 —— 自检要报错不崩栈
            bad.append(f"{tag} 抛异常 {exc!r}")
            continue
        brute = _brute_ramp(te, tf, df, dc, do)
        if got.size != brute.size or not np.allclose(got, brute, rtol=0.0, atol=1e-9):
            bad.append(f"{tag} 与逐点暴力实现不符：n={got.size} vs {brute.size}")
        if got[0] != 0.0:
            bad.append(f"{tag} 首行不是 t=0")
        if np.any(np.diff(got) <= 0.0):
            bad.append(f"{tag} 时间轴非严格递增")
        tf_clamped = min(max(float(tf), 0.0), float(te))
        tail = got[got > tf_clamped + 1e-9]
        if tail.size and np.any(np.abs(tail - np.round(tail / do) * do) > 1e-9):
            bad.append(f"{tag} 窗后混入非 dt_out 交付行")
    if ramp_t_out(86400.0, 600.0, 0.5, 60.0).size != 1200 + 1430 + 1:
        bad.append("ramp_t_out 基准行数 ≠ 1200 细窗行 + 1430 交付行 + 1（解析公式）")
    if not np.array_equal(ramp_t_out(600.0, 0.0, 0.5, 60.0), np.arange(0.0, 601.0, 60.0)):
        bad.append("ramp_t_out 在 t_fine_end=0 时 ≠ 纯 60 s 交付格")
    if ramp_t_out(90.0, 600.0, 0.5, 60.0).size != 181:
        bad.append("ramp_t_out 在 t_end < t_fine_end 时未钳到 [0,t_end] 的加密段")
    try:
        ramp_t_out(600.0, 120.0, 0.0, 60.0)
        bad.append("ramp_t_out 未拒绝 dt_fine=0")
    except ValueError:
        pass
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
        # 定位失败（技能根未安装且未设 MATH_MODEL_SKILL_SCRIPTS）不拖垮 --manifest：计时里吞掉
        "find_skill_scripts": _timed_find_skill_scripts,
        "ramp_t_out": lambda: ramp_t_out(86400.0, 600.0, 0.5, 60.0, 60.0),
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
