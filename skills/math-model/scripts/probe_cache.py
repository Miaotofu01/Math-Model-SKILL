#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe_cache.py —— 探针池与结果缓存（math-model skill 技能级工具）

设计依据（上次 run 实测）：一次 run 产生 **53 个一次性探针脚本 / 231 次写入**（同类脚本换个名字反复重写），
全部丢在 `/tmp`，无登记、无复用；同一个重计算每次重写重跑约 25 s，评审三角色跨轮反复付这份钱。

约定（与 `prompts/_common.md` §5 一致）
------------------------------------
- 探针**固定位置**：`<outputDir>/probes/<角色>/<目的>.py`（角色如 `judge` / `adversary` / `application` / `sanity` / `robustness`）
- 探针**只输出 JSON** 到 stdout（便于缓存与对拍）
- 结果缓存：`<outputDir>/probes/results/<指纹>.json`；**指纹 = 原语版本 + 脚本内容 hash + 输入 + 配置**
  → 探针代码没改、输入没变 ⇒ 直接命中，秒回；改了任何一项 ⇒ 自动失效重算（不会拿到过期结论）
- `probes/manifest.json`：{用途, 输入, 输出契约, 单次耗时, 依赖原语}（`--register` 追加/更新一条）

用法
----
库方式（推荐，写在探针脚本里）：

    import sys; sys.path.insert(0, "<技能根>/scripts")
    import probe_cache as pc, primitives as P

    def compute(inputs):            # 纯函数：inputs -> 可 JSON 序列化的 dict
        ...

    if __name__ == "__main__":
        pc.main_with_cache(compute, purpose="边界敏感性扫描", role="adversary",
                           inputs={"R": 10.0, "n_theta": 128}, primitives_version=P.VERSION)

命令行方式（把已有脚本当黑盒跑，命中即跳过执行）：

    python3 probe_cache.py --run probes/adversary/cyl.py --inputs '{"R":10}' [--timeout 600]
    python3 probe_cache.py --list [--show <指纹前缀>] [--clear]

环境变量：`PROBE_CACHE_DIR`（默认 `<cwd>/probes/results`）、`PROBE_MANIFEST`（默认 `<cwd>/probes/manifest.json`）

import 路径口径
--------------
探针/实现脚本默认**只能 import 同目录的模块**——Python 把**脚本所在目录**放进 `sys.path`，不是 cwd。
因此本工具执行脚本时自动注入 `PYTHONPATH=<cwd>:<cwd>/pool`，探针里可直接 `import primitives`（或 `import pool.primitives`）。
自己直接跑脚本（不走 `--run`）时：先 `import probe_cache as pc; pc.bootstrap_sys_path()` **再** import 池中模块，
或命令行加 `PYTHONPATH=<outputDir>/pool:<outputDir> python probes/<角色>/<目的>.py`。
**撞到 ModuleNotFoundError 一律先修路径，禁止把池中实现内联抄一份**（那正是"反复造轮子"的起点）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

CACHE_DIR_ENV = "PROBE_CACHE_DIR"
MANIFEST_ENV = "PROBE_MANIFEST"


def cache_dir() -> Path:
    return Path(os.environ.get(CACHE_DIR_ENV) or (Path.cwd() / "probes" / "results"))


def manifest_path() -> Path:
    return Path(os.environ.get(MANIFEST_ENV) or (Path.cwd() / "probes" / "manifest.json"))


def pool_signature() -> str:
    """pool/ 下全部 .py 的内容指纹 + primitives.py 的 VERSION（改池 ⇒ 探针缓存必须失效）。"""
    cwd = Path.cwd()
    items: list[str] = []
    base = cwd / "pool"
    if base.is_dir():
        for f in sorted(base.rglob("*.py")):
            try:
                items.append(f"{f.relative_to(cwd)}:{hashlib.sha256(f.read_bytes()).hexdigest()}")
            except OSError:
                continue
    ver = ""
    pv = base / "primitives.py"
    if pv.is_file():
        m = re.search(r"^VERSION\s*=\s*[\"\']([^\"\']+)", pv.read_text(encoding="utf-8", errors="replace"), re.M)
        ver = m.group(1) if m else ""
    return ver + "|" + hashlib.sha256("\n".join(items).encode()).hexdigest()[:16]


def fingerprint(script: str | Path | None = None, inputs: Any = None, config: Any = None,
                primitives_version: str = "") -> str:
    """指纹 = 原语版本（未给则自动探测 `pool/`）+ `pool/` 内容 + 脚本路径与内容 + 输入 + 配置。

    任一变化 ⇒ 失效重算；**改 `pool/` 下任何 .py 都会让旧缓存失效**（避免拿到过期结论）。
    """
    h = hashlib.sha256()
    h.update(("pv:" + (str(primitives_version) or pool_signature()) + "\n").encode())
    if script:
        p = Path(script)
        h.update(("script:" + str(p) + "\n").encode())
        if p.is_file():
            h.update(hashlib.sha256(p.read_bytes()).hexdigest().encode())
    h.update(("inputs:" + json.dumps(inputs, sort_keys=True, ensure_ascii=False, default=str) + "\n").encode())
    h.update(("config:" + json.dumps(config, sort_keys=True, ensure_ascii=False, default=str) + "\n").encode())
    return h.hexdigest()[:16]


def load(key: str) -> dict | None:
    f = cache_dir() / f"{key}.json"
    if not f.is_file():
        return None
    try:
        rec = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    rec["_cache"] = {"hit": True, "file": str(f), "createdAt": rec.get("createdAt")}
    return rec


def save(key: str, result: Any, meta: dict | None = None, elapsed_s: float | None = None) -> Path:
    d = cache_dir()
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{key}.json"
    f.write_text(json.dumps({"key": key, "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                             "elapsed_s": elapsed_s, "meta": meta or {}, "result": result},
                            ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return f


def register(purpose: str, role: str = "other", inputs: Any = None, contract: str = "",
             key: str | None = None, elapsed_s: float | None = None, deps: str = "",
             script: str = "") -> None:
    """向 probes/manifest.json 追加/更新一条登记（按 key 去重）。"""
    mf = manifest_path()
    mf.parent.mkdir(parents=True, exist_ok=True)
    try:
        man = json.loads(mf.read_text(encoding="utf-8")) if mf.is_file() else {"schema": "v1", "probes": {}}
    except json.JSONDecodeError:
        man = {"schema": "v1", "probes": {}}
    man.setdefault("probes", {})
    k = key or f"{role}/{purpose}"
    man["probes"][k] = {"purpose": purpose, "role": role, "inputs": inputs, "outputContract": contract,
                        "elapsed_s": elapsed_s, "deps": deps, "cacheKey": key, "script": script,
                        "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    mf.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")


def bootstrap_sys_path(pool_root: str | None = None) -> list[str]:
    """把 outputDir 根与其 pool/ 加进 sys.path，使 `import primitives` / `import pool.primitives` 可用。

    默认按「探针在 <outputDir> 下执行」的约定取 cwd；返回实际插入的路径（便于日志核对）。
    """
    cwd = Path(pool_root) if pool_root else Path.cwd()
    added: list[str] = []
    for c in (cwd / "pool", cwd):
        s = str(c)
        if c.exists() and s not in sys.path:
            sys.path.insert(0, s)
            added.append(s)
    return added


def main_with_cache(compute: Callable[[Any], Any], purpose: str, inputs: Any = None, role: str = "other",
                    config: Any = None, primitives_version: str = "", contract: str = "JSON→stdout",
                    deps: str = "", force: bool = False) -> dict:
    """探针脚本的标准入口：命中即返回缓存，否则 compute(inputs) → 落盘 → 登记。"""
    bootstrap_sys_path()          # 让 compute 里的池 import 可用（直接执行脚本时也成立）
    script = sys.argv[0]
    key = fingerprint(script, inputs, config, primitives_version)
    if not force:
        hit = load(key)
        if hit is not None:
            print(json.dumps(hit["result"], ensure_ascii=False, indent=2, default=str))
            print(f"[probe_cache] 命中缓存 {key}（{hit['_cache'].get('createdAt')}）", file=sys.stderr)
            return hit["result"]
    t0 = time.perf_counter()
    result = compute(inputs)
    el = round(time.perf_counter() - t0, 3)
    try:
        save(key, result, meta={"purpose": purpose, "role": role, "inputs": inputs,
                                "primitivesVersion": primitives_version}, elapsed_s=el)
        register(purpose, role, inputs, contract, key=key, elapsed_s=el, deps=deps, script=script)
    except OSError as exc:
        print(f"[probe_cache] 警告：结果无法落盘或登记（{exc}）；结果仍输出，但不会命中缓存", file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    print(f"[probe_cache] 计算完成 {el}s → {cache_dir()}/{key}.json", file=sys.stderr)
    return result


def run_script(script: str, inputs: Any = None, config: Any = None, primitives_version: str = "",
               timeout: float = 600.0, force: bool = False, purpose: str = "", role: str = "other") -> Any:
    """把已有探针脚本当黑盒跑（脚本须把 JSON 打到 stdout）；命中缓存则不执行。"""
    key = fingerprint(script, inputs, config, primitives_version)
    if not force:
        hit = load(key)
        if hit is not None:
            print(f"[probe_cache] 命中缓存 {key}（跳过执行）", file=sys.stderr)
            print(json.dumps(hit["result"], ensure_ascii=False, indent=2, default=str))   # 命中也要给 stdout
            return hit["result"]
    env = dict(os.environ)
    paths = [str(Path.cwd() / "pool"), str(Path.cwd())]          # 池 import 路径（脚本目录不是 cwd）
    if env.get("PYTHONPATH"):
        paths.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(paths)
    env["PROBE_INPUTS"] = json.dumps(inputs or {}, ensure_ascii=False)
    env[CACHE_DIR_ENV] = str(cache_dir())
    env[MANIFEST_ENV] = str(manifest_path())
    t0 = time.perf_counter()
    proc = subprocess.run([sys.executable, script], capture_output=True, text=True, timeout=timeout, env=env)
    el = round(time.perf_counter() - t0, 3)
    if proc.returncode != 0:
        raise RuntimeError(f"探针脚本失败 rc={proc.returncode}：{proc.stderr.strip()[-500:]}")
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"探针 stdout 不是 JSON（{exc}）：{proc.stdout[:300]!r}") from exc
    try:
        save(key, result, meta={"script": script, "inputs": inputs, "purpose": purpose}, elapsed_s=el)
        register(purpose or Path(script).stem, role, inputs, "JSON→stdout", key=key, elapsed_s=el, script=script)
    except OSError as exc:      # 缓存目录只读/磁盘满 → 结果照常返回，只是不缓存
        print(f"[probe_cache] 警告：结果无法落盘或登记（{exc}）；结果仍返回，但不会命中缓存", file=sys.stderr)
    print(f"[probe_cache] 计算完成 {el}s → {cache_dir()}/{key}.json", file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))   # 结果同时打到 stdout（--run 调用方靠它取数）
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="math-model 探针池缓存")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--run", metavar="SCRIPT", help="跑探针脚本（命中缓存则跳过）")
    g.add_argument("--list", action="store_true", help="列出缓存条目")
    g.add_argument("--show", metavar="KEY", help="打印某条缓存")
    g.add_argument("--clear", action="store_true", help="清空缓存")
    ap.add_argument("--inputs", default="{}", help="JSON 输入（参与指纹）")
    ap.add_argument("--config", default="{}", help="JSON 配置（参与指纹）")
    ap.add_argument("--primitives-version", default="", help="原语池版本（参与指纹）")
    ap.add_argument("--purpose", default="")
    ap.add_argument("--role", default="other")
    ap.add_argument("--timeout", type=float, default=600.0)
    ap.add_argument("--force", action="store_true", help="忽略缓存强制重算")
    a = ap.parse_args(argv)

    if a.clear:
        n = skipped = 0
        mf = manifest_path().resolve()
        for f in sorted(cache_dir().glob("*.json")):
            if f.resolve() == mf:                      # manifest 是登记的唯一权威，绝不能被当缓存删掉
                skipped += 1
                continue
            try:
                rec = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                skipped += 1
                continue
            if not (isinstance(rec, dict) and "result" in rec and ("key" in rec or "meta" in rec)):
                skipped += 1                            # 不是本工具写的文件 → 不碰
                continue
            f.unlink()
            n += 1
        print(f"已清空 {n} 条缓存（{cache_dir()}）" + (f"；跳过 {skipped} 个非缓存文件/清单" if skipped else ""))
        return 0
    if a.list:
        files = sorted(cache_dir().glob("*.json"))
        if not files:
            print(f"（无缓存；目录 {cache_dir()}）")
        for f in files:
            try:
                rec = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(rec, dict):
                print(f"{f.stem}  （跳过：不是本工具的缓存记录）")
                continue
            meta = rec.get("meta", {}) or {}
            print(f"{f.stem}  {rec.get('elapsed_s')}s  {meta.get('role','')}/{meta.get('purpose','')}  {meta.get('inputs')}")
        return 0
    if a.show:
        hit = load(a.show)
        if hit is None:
            print(f"未找到缓存 {a.show}", file=sys.stderr)
            return 2
        print(json.dumps(hit, ensure_ascii=False, indent=2))
        return 0
    try:
        run_script(a.run, json.loads(a.inputs), json.loads(a.config), a.primitives_version,
                   a.timeout, a.force, a.purpose, a.role)
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
