# 案例：2025 国赛 A 题「烟幕遮蔽」原语（**已移出技能根，不作为池发货**）

> 归档 2026-09-10 ｜ 来源：上一次全量 run
>
> **归档原因**：这 4 项是**单题个例**（含该题的建模选择），却以「题无关原语」身份随技能发货 → 对后续任何题都是**上下文污染**：题面完全不同，agent 第一回合却先看到一套几何采样/二分/bootstrap 条目，会被锚到上一次的建模方式上。其中 3 项还违反「不进池：一行的库函数包装」——`scipy.optimize.brentq`、`scipy.stats.bootstrap`、`scipy.optimize.differential_evolution` 已提供同功能。
>
> **保留价值**：① 证明 `primitives.py` 的「登记 + 暴力对拍 + manifest 耗时」框架可用；② 留下可复用的对拍手法（稠密采样暴力对拍、解析根对拍、已知最优对拍）；③ 若再遇同类题（几何遮蔽/区间测度），可直接搬进 `<outputDir>/pool/problem/<题>/` 复用，而不是重新发明。

## §1 判据对照（为什么只留在案例里）

| 条目 | 库是否提供 | 口径敏感 | 领域中立 | 结论 |
|---|---|---|---|---|
| `point_segment_distance` / `min_distance_to_segment_batch` | 否（numpy/scipy 无线段距离） | 是（投影截断到 [0,1]、退化线段） | 是（纯数学定义，无建模选择） | **保留在发货池** |
| `interval_union` / `interval_total` | 否（无区间代数） | 是（闭开端点、相接合并、零测集） | 是 | **保留在发货池** |
| `cylinder_sample_points` | 否 | 是 | **否**（"只采侧面、θ×z 网格、含端面圆环"是该题建模选择） | 移出 → 案例 |
| `bisect_boundary` | **是**（`scipy.optimize.brentq`） | 中 | 是 | 移出 → 案例 |
| `bootstrap_ci` | **是**（`scipy.stats.bootstrap`） | 中 | 是 | 移出 → 案例 |
| `de_minimize` | **是**（`scipy.optimize.differential_evolution`） | 否 | 是 | 移出 → 案例 |

**留下的两条判据**：库不提供 且 口径敏感 且 领域中立；要进技能根还需**≥2 个不同题的复用证据**（单题证据只能进 `pool/problem/<题>/`）。

## §2 可复用的对拍手法（比条目本身更值钱）

| 手法 | 用法 |
|---|---|
| 稠密采样暴力对拍 | 解析/向量化实现 vs 在定义域上撒 20 万点取 min/max（本次用于点到线段距离） |
| 解析根对拍 | 二分/迭代求根 vs 可解析的根（本次用 √2），并额外验证"端点单调假设不满足时抛错" |
| 已知最优对拍 | 优化器 vs 有闭式最优的目标（本次用 `(x-3)^2+(y+1)^2` 的 0） |
| 结构不变量 | 采样点数 = n_theta×n_z、到轴距离恒 = radius、轴向范围 = [c-h/2, c+h/2] |

## §3 归档实现

<details><summary>被裁剪的 4 项原始实现（点击展开）</summary>

```python
@primitive("cylinder_sample_points",
           "cylinder_sample_points(center, axis, radius, height, n_theta=64, n_z=48) -> ndarray",
           "center/axis 与 radius/height 同长度单位；返回 (n_theta*n_z, 3) 三维点",
           "圆柱**侧面**（含上下底面圆环，不含内部）上的均匀采样点；axis 需为非零向量")
def cylinder_sample_points(center, axis, radius: float, height: float,
                           n_theta: int = 64, n_z: int = 48) -> np.ndarray:
    """圆柱侧面采样：θ 均匀 n_theta 份、轴向 z ∈ [-h/2, h/2] 均匀 n_z 份（含端面）。"""
    center = np.asarray(center, dtype=float).reshape(3)
    axis = np.asarray(axis, dtype=float).reshape(3)
    nrm = np.linalg.norm(axis)
    if nrm == 0:
        raise ValueError("axis 不能为零向量")
    w = axis / nrm
    # 构造与 w 正交的基（任取不平行向量）
    tmp = np.array([1.0, 0.0, 0.0]) if abs(w[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = np.cross(w, tmp)
    u /= np.linalg.norm(u)
    v = np.cross(w, u)
    th = np.linspace(0.0, 2 * math.pi, int(n_theta), endpoint=False)
    zz = np.linspace(-height / 2.0, height / 2.0, int(n_z))
    ring = radius * (np.cos(th)[:, None] * u + np.sin(th)[:, None] * v)   # (n_theta,3)
    pts = center + ring[None, :, :] + zz[:, None, None] * w               # (n_z,n_theta,3)
    return pts.reshape(-1, 3)


# ─────────────────────────── 数值 ───────────────────────────

@primitive("bisect_boundary",
           "bisect_boundary(pred, lo, hi, tol=1e-9, increasing=True, max_iter=200) -> float",
           "lo/hi/tol 与自变量同单位", "单调谓词 pred 的符号变化点（二分精化到 tol）",
           deps="numpy")
def bisect_boundary(pred: Callable[[float], bool], lo: float, hi: float, tol: float = 1e-9,
                    increasing: bool = True, max_iter: int = 200) -> float:
    """二分求「谓词由 False 变 True（increasing=True）」或「由 True 变 False」的边界点。

    约定：increasing=True 时 pred(lo)=False、pred(hi)=True；返回边界 x ∈ [lo,hi]，|区间宽| ≤ tol。
    """
    f = (lambda x: pred(x)) if increasing else (lambda x: not pred(x))
    if f(lo) or not f(hi):
        raise ValueError("谓词在端点不满足单调假设（lo 应为 False、hi 应为 True）")
    for _ in range(int(max_iter)):
        mid = 0.5 * (lo + hi)
        if hi - lo <= tol:
            return mid
        if f(mid):
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


@primitive("bootstrap_ci",
           "bootstrap_ci(data, stat=np.mean, n_boot=10000, alpha=0.05, seed=42) -> (lo, hi, stat_value)",
           "与 stat 输出同单位", "bootstrap 百分位置信区间（固定 seed，结果可复现）")
def bootstrap_ci(data, stat=np.mean, n_boot: int = 10000, alpha: float = 0.05,
                 seed: int = 42) -> tuple[float, float, float]:
    x = np.asarray(data, dtype=float).ravel()
    rng = np.random.default_rng(int(seed))
    idx = rng.integers(0, x.size, size=(int(n_boot), x.size))
    stats = np.apply_along_axis(stat, 1, x[idx])
    lo, hi = np.percentile(stats, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi), float(stat(x))


@primitive("de_minimize",
           "de_minimize(fun, bounds, seed=42, **kw) -> dict",
           "bounds 与 fun 同口径", "{x, fun, nit, success}；固定 seed，记录迭代次数",
           deps="scipy")
def de_minimize(fun, bounds, seed: int = 42, **kw) -> dict:
    """差分进化包装（统一 seed/记录 field）。scipy 缺失 → 抛 ImportError 由调用方降级。"""
    from scipy.optimize import differential_evolution
    res = differential_evolution(fun, bounds, seed=int(seed), polish=True, **kw)
    return {"x": res.x.tolist(), "fun": float(res.fun), "nit": int(getattr(res, "nit", -1)),
            "success": bool(res.success)}
```

</details>

## §4 若再遇同类题的用法

```bash
mkdir -p pool/problem/2025A && cp <案例代码> pool/problem/2025A/occlusion.py
# 登记：pool/problem/manifest.json 的 entries.<模块.函数> 写 口径/单位/被复用/对拍值
```
