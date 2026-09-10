#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""figure_lint —— 数模竞赛产物图机械自检（单文件；仅 stdlib + 可选 PIL/numpy）

用途：检查 math-model skill 的两类产物图是否符合内部规范——
  示意图/流程图（diagram-design 的 同名 .html（内联 svg）+ 2x PNG）→ docs/flowchart-drawing.md：
  §2 皮肤 token / §3 4px 网格·正交连线·标签遮罩间隙 6-10px / §4 图注 12px #6b7280 居中 /
  §5 字体 / §7 Chrome 2x 截图；matplotlib 结果图（plot_q*.py 的 PNG）→ docs/writing-and-format.md §二。

用法：
  /usr/bin/python3 skills/math-model/scripts/figure_lint.py \\
      --py out/.../plot_q2_figures.py --png out/figures/*.png --svg out/.../fig_q1_示意图_*.html \\
      [--json lint.json] [--quiet] [--render] [--timeout 600] [--margin-px 8]
  退出码：有 P0 → 1；只有 P1 或无问题 → 0；脚本自身异常 → 2（打印 traceback 摘要，不静默）。
  本文档写违规示例时用 \\_ 转义（T\\_eff、2e\\-3），以免自检自伤。

check id（P0 = 阻断 / P1 = 提示）：
  py.title      P1；标题串含内部术语（问题N / innov / 域外必查 / Q1 / 对抗性审查…）升 P0——结果图禁止
                标题（图意由图注承担），ax.set_title / plt.title / fig.suptitle 即报
  py.underscore P0 字符串字面量出现「字面下划线」X\\_y（中文标签里一律 P0；纯英文多词 wind\\_speed 报 P1）；
                豁免 $...$ math 段、文件名/路径、全大写常量 T\\_EFF、matplotlib API 名与 dict/JSON 键
  py.scientific P0 字符串含代码式科学计数法 2e\\-3（$2\\times10^{-3}$ 合格）
  py.thousands  P1 格式化字符串含千分位（格式说明符内含逗号，如 :, 或 :,.0f，或 format 的第二参数为逗号）
  py.legend_missing P1 画了 ≥2 处数据图元却无 legend()；或 axhline/axvline/axvspan/fill_between 缺 label=
  py.hardcode   P1 同目录/上层有 results.json 时，脚本硬编码了与其一致的关键数值（≥5 位有效数字，或
                ≥4 位整数）→ 应经 results.json 读取；找不到 results.json 则跳过
  py.font       P1 缺 CJK 字体设置（Noto Sans CJK / SimHei / font.sans-serif）或 axes.unicode_minus=False
                （仅对真正 import matplotlib 的脚本生效）
  py.unreadable P0 读不到文件或语法错误（该文件一条 P0，继续处理其它文件）
  png.margin    P0 非白/非透明墨迹到任一边 < --margin-px（默认 8px，按图像实际像素算）
  png.size      P1 宽度 <1200px；同目录有同名 .html（示意图）时要求 ≥1600px
  png.blank     P0 墨迹占比 <0.2%（疑似空图；alpha≈0 视为背景）
  png.unreadable P0 PNG 解码失败（无 PIL 时降级 stdlib zlib+struct 解码）
  svg.grid      P0 节点/文本基线/图例色块 x,y 不整除 4（rx/ry 圆角不在 4px 网格要求内）
  svg.orthogonal P0 连线（line/polyline/path 的 M/L/H/V 段）出现斜线（dx 与 dy 同时非 0）
  svg.mask      P0 文字遮罩（带 fill 的矮 rect）与连线相交且覆盖 >遮罩厚度 50%（例外：重叠 ≤50%，
                或遮罩侧向偏移 ≥6px）；P1 = 未相交但间隙 0<gap<6px（规范 6-10px）
  svg.color     P0 fill/stroke/color 出现 §2 token 白名单外的颜色（rule 只允许 ink@0.12）
  svg.font      P1 font-size 不在 {8,12,16,20,24}；缺 CJK 字体回退；CJK 文字 <12px
  svg.count     P1 节点 >9 或箭头（marker-end）>12
  svg.caption   P1 图注非 12px(±1) / 非 #6b7280 / 非居中
  svg.canvas    P1 viewBox 不整除 4；同名 PNG ≠ 2x(SVG 宽, SVG 高+24)（§4 页面高 = SVG 高+8+16）
  render.ticksep P0 刻度标签含千分位逗号 2,500 / 裸大数 20000（≥5 位无分隔整数、无单位无 ×10）/ 2e\\-3 式
  render.legend_cover P0 图例 bbox 与数据图元（Line2D/Patch/Collection）window extent 重叠 >该图元面积 5%
  render.legend_clip  P0 图例 bbox 或图例文字超出 figure 边界（被裁断）
  render.title  P1 figure suptitle / 轴标题非空（可见标题）
  render.invisible_claim P1（尽力而为）轴标题/图注提到的颜色词（绿/红/蓝/green…）找不到对应可见图元
  render.failed P1 --render 异常/超时/未捕获 Figure；只报 P1，绝不让整体退出码变 2

已知局限（明确不假装通过）：svg.grid 不查 path/polygon 坐标与曲线控制点；svg.mask 是纯几何判定（不渲染
  像素），非相交但 >10px 的过宽间隙不报；render.legend_* 按规范用未裁剪 window extent（bar 超出轴范围时
  重叠率被稀释，可能低估）；render.invisible_claim 只做「颜色词→色相」粗匹配，不做 OCR/像素级校验；
  png.* 只做像素墨迹统计，不识别「文字被裁」这类语义问题（那依赖 --render）。
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import os
import re
import struct
import subprocess
import sys
import tempfile
import traceback
import zlib
from dataclasses import dataclass, field
from typing import Any, Iterable, NamedTuple, Sequence

P0, P1 = "P0", "P1"


@dataclass
class Issue:
    """单条检查结果：level ∈ {P0,P1}，check = 稳定 check id，value = 结构化实测值。"""

    level: str
    check: str
    detail: str
    value: Any = None


@dataclass
class FileReport:
    """单个被检查文件的报告（kind ∈ {py,png,svg}）。"""

    path: str
    kind: str
    issues: list[Issue] = field(default_factory=list)

    def add(self, level: str, check: str, detail: str, value: Any = None) -> None:
        self.issues.append(Issue(level, check, detail, value))


def _clip(text: Any, limit: int = 70) -> str:
    """单行化 + 截断，保证报告每行可读。"""
    flat = " ".join(str(text).split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def _span(lines: Sequence[int], limit: int = 5) -> str:
    """行号列表 → 'L12,L15…'。"""
    return ",".join(f"L{n}" for n in lines[:limit]) + ("…" if len(lines) > limit else "")

# --------------------------------------------------------------------------- A. --py

_TITLE_CALLS = frozenset({"set_title", "title", "suptitle", "set_suptitle"})
_THRESHOLD_CALLS = frozenset({"axhline", "axvline", "axvspan", "fill_between"})
_DATA_CALLS = frozenset({
    "plot", "scatter", "bar", "barh", "fill_between", "axhline", "axvline", "axvspan", "contour", "contourf",
    "step", "errorbar", "hlines", "vlines", "pcolormesh", "imshow", "pie", "hist", "stackplot", "quiver"})
_INTERNAL_TERM_RE = re.compile(
    r"问题\s*[0-9０-９一二三四五六七八九十]|[Qq][1-9](?![0-9A-Za-z])|innov|域外(必查|复核)"
    r"|对抗性审查|模型重设计|adversarial|内部流程|重设计历史", re.I)
# 非标签上下文：matplotlib/pyplot/argparse API 名与参数名 + 本脚本 check id（都不是画在图上的文字标签）
_NON_LABEL_TOKENS = frozenset({
    "unicode_minus", "font_sans", "font_sans-serif", "get_window_extent", "fill_between", "axhline",
    "axvline", "axvspan", "set_title", "set_suptitle", "set_xticklabels", "set_yticklabels",
    "set_xlabel", "set_ylabel", "tight_layout", "bbox_inches", "store_true", "json_out", "lower_left",
    "upper_right", "lower_right", "upper_left", "facecolor", "edgecolor", "line_width", "marker_size",
    "font_size", "font_weight", "legend_cover", "legend_clip", "legend_missing", "invisible_claim",
    "figure_lint", "tick_sep"})
_MATH_SEG_RE = re.compile(r"\$[^$]*\$")
_HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_PATH_TOKEN_RE = re.compile(r"\S*[/\\]\S*")
_FILE_TOKEN_RE = re.compile(r"\S*\.(?:png|jpe?g|pdf|svg|html?|json|py|csv|xlsx?|tex|npy|md|txt|log)\b\S*", re.I)
_UNDERSCORE_RE = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z\u0394][A-Za-z0-9]*_[A-Za-z0-9]+(?![A-Za-z0-9_])")
_SCI_RE = re.compile(r"\d(?:\.\d+)?[eE][-+]?\d+")
_CJK_RE = re.compile(r"[\u3400-\u9fff\u3040-\u30ff]")
_BRACE_RE = re.compile(r"\{[^{}]*\}")
_FORMAT_COMMA_RE = re.compile(r"format\([^)]*,\s*['\"]\s*,\s*['\"]")
_SPEC_CHARS_RE = re.compile(r"^[,<>=^+\-0-9.#_fdgGeExXo%bc\s]*$")
_NUM_IN_TEXT_RE = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
_CODE_BLOB_RE = re.compile(r"^\s*(?:def |class |import |from )", re.M)
_CJK_FONT_RE = re.compile(r"Noto Sans CJK|Noto Serif CJK|Source Han|SimHei|SimSun|Heiti|PingFang|WenQuanYi"
                          r"|Microsoft YaHei|Songti|KaiTi")
_FONT_RE = re.compile(r"font\.sans-serif|font\.family|font_family")
_UNICODE_MINUS_RE = re.compile(r"unicode_minus[^\n]*False")


def _call_name(func: ast.expr) -> str:
    """取调用名（属性名或函数名）。"""
    if isinstance(func, ast.Attribute):
        return func.attr
    return func.id if isinstance(func, ast.Name) else ""


def _static_text(node: ast.expr | None) -> str:
    """str 常量 / f-string 静态片段 / 'fmt' % (...) 左侧 → 文本。"""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(_static_text(v) for v in node.values if isinstance(v, ast.Constant))
    return _static_text(node.left) if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod) else ""


def _scan_ast(tree: ast.AST) -> dict[str, Any]:
    """一次遍历收集：字符串（含是否 dict 键）、标题调用、图元调用、legend 调用、是否 import mpl。"""
    key_ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript):
            key_ids.add(id(node.slice))
        elif isinstance(node, ast.Dict):
            key_ids.update(id(k) for k in node.keys if k is not None)
    strings, titles, data_calls = [], [], []
    legend_calls, has_mpl = 0, False
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            strings.append((node.lineno, node.value, id(node) in key_ids))
        elif isinstance(node, ast.Call):
            name = _call_name(node.func)
            if name in _TITLE_CALLS:
                titles.append((node.lineno, name, _static_text(node.args[0] if node.args else None)))
            elif name == "legend":
                legend_calls += 1
            elif name in _DATA_CALLS:
                data_calls.append((node.lineno, name, any(k.arg == "label" for k in node.keywords)))
        elif isinstance(node, ast.Import):
            has_mpl = has_mpl or any(n.name.startswith("matplotlib") for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            has_mpl = has_mpl or (node.module or "").startswith("matplotlib")
    return {"strings": strings, "titles": titles, "data_calls": data_calls, "legend_calls": legend_calls,
            "has_mpl": has_mpl}


def _strip_non_label(value: str) -> str:
    """去掉 math 段、十六进制颜色、文件名/路径 token，只留可能是标签的文字。"""
    value = _HEX_COLOR_RE.sub(" ", value.replace("\\$", ""))
    value = _MATH_SEG_RE.sub(" ", value)
    return _FILE_TOKEN_RE.sub(" ", _PATH_TOKEN_RE.sub(" ", value))


def _looks_like_code(value: str) -> bool:
    """多行且含 def/class/import 行 → 内嵌代码块（不按图上标签扫描）。"""
    return "\n" in value and bool(_CODE_BLOB_RE.search(value))


def _classify_underscore(tok: str, has_cjk: bool) -> str | None:
    """P0 / P1 / None（豁免）。"""
    if tok in _NON_LABEL_TOKENS or (tok.upper() == tok and any(c.isalpha() for c in tok)):
        return None  # 非标签上下文 / 全大写常量（T_EFF、MPLCONFIGDIR）
    if has_cjk:
        return P0  # 中文标签里的字面下划线一律 P0
    base = tok.partition("_")[0]
    if len(base) <= 2 or any(c.isupper() for c in tok) or not tok.isascii():
        return P0  # 符号式：T_eff / v_c / 希腊字母
    return P1  # 纯英文多词（wind_speed）— 需人工判断


def _is_thousands_spec(brace: str) -> bool:
    """格式说明符（冒号后）含逗号才算千分位；dict 字面量的键值对不算。"""
    if ":" not in brace:
        return False
    spec = brace.split(":", 1)[1].rstrip("}")
    return "," in spec and len(spec) <= 12 and bool(_SPEC_CHARS_RE.match(spec))


def _check_strings(strings: Sequence[tuple[int, str, bool]], report: FileReport) -> None:
    """一个遍历做完 py.underscore / py.scientific / py.thousands。"""
    under: dict[tuple[str, str], list[int]] = {}
    sci: dict[str, list[int]] = {}
    thousands: list[str] = []
    for lineno, value, is_key in strings:
        if is_key or _looks_like_code(value):
            continue
        if "_" in value:
            stripped = _strip_non_label(value)
            has_cjk = bool(_CJK_RE.search(stripped))
            for tok in _UNDERSCORE_RE.findall(stripped):
                if level := _classify_underscore(tok, has_cjk):
                    under.setdefault((level, tok), []).append(lineno)
        for tok in _SCI_RE.findall(_strip_non_label(value)):
            sci.setdefault(tok, []).append(lineno)
        specs = [m.group(0) for m in _BRACE_RE.finditer(value) if _is_thousands_spec(m.group(0))]
        if _FORMAT_COMMA_RE.search(value):
            specs.append("format(..., 逗号)")
        thousands += [f"{spec}（L{lineno}）" for spec in specs]
    for (level, tok), lines in sorted(under.items()):
        hint = "中文标签里的下划线须写 LaTeX math" if level == P0 else "疑似英文标签误用下划线，待人工确认"
        report.add(level, "py.underscore", f"字符串含字面下划线 {tok!r}（{len(lines)} 处：{_span(lines)}）；{hint}", tok)
    for tok, lines in sorted(sci.items()):
        report.add(P0, "py.scientific", f"字符串含代码式科学计数法 {tok!r}（{_span(lines)}）：应写 LaTeX math 乘幂形式", tok)
    if thousands:
        report.add(P1, "py.thousands", f"格式化字符串含千分位：{', '.join(thousands[:4])}；图内数字不得带千分位逗号",
                   thousands[:8])


def _check_titles(titles: Sequence[tuple[int, str, str]], report: FileReport) -> None:
    """结果图禁止标题；标题串含内部流程术语升 P0。"""
    for lineno, name, text in titles:
        if not text.strip():
            continue
        level = P0 if _INTERNAL_TERM_RE.search(text) else P1
        why = "标题含内部流程术语" if level == P0 else "结果图禁止标题（图意由图注承担）"
        report.add(level, "py.title", f"第{lineno}行 {name}()：{why}；实测 {text!r}", text)


def _check_legend(data_calls: Sequence[tuple[int, str, bool]], legend_calls: int, report: FileReport) -> None:
    """py.legend_missing：缺 legend() 或阈值线/区间缺 label=。"""
    if len(data_calls) >= 2 and legend_calls == 0:
        report.add(P1, "py.legend_missing", f"画了 {len(data_calls)} 处数据图元（"
                   f"{'/'.join(sorted({n for _, n, _ in data_calls})[:4])} …）但无 legend() 调用", len(data_calls))
    missing = [ln for ln, name, has_label in data_calls if name in _THRESHOLD_CALLS and not has_label]
    if missing:
        report.add(P1, "py.legend_missing", f"{len(missing)} 处阈值线/区间缺 label=（{_span(missing, 6)}），不会进图例",
                   missing)


def _is_key_number(value: float) -> bool:
    """关键数值判定：≥5 位有效数字的浮点，或 |v|≥1000 的整数（1,231,200 这类千分位也算）。"""
    if not math.isfinite(value):
        return False
    digits = len(re.sub(r"[^0-9]", "", re.split("[eE]", repr(value))[0]).lstrip("0").rstrip("0"))
    return digits >= 5 or (value.is_integer() and abs(value) >= 1000)


def _key_numbers(obj: Any, out: set[float]) -> None:
    """递归收集 results.json 关键数值：数值字段 + 文本字段里抽出的数字（keyValues 常写成 '4.5856 s'）。"""
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        if _is_key_number(float(obj)):
            out.add(float(obj))
    elif isinstance(obj, str):
        for tok in _NUM_IN_TEXT_RE.findall(obj):
            try:
                val = float(tok.replace(",", ""))
            except ValueError:
                continue
            if _is_key_number(val):
                out.add(val)
    elif isinstance(obj, (dict, list)):
        for val in (obj.values() if isinstance(obj, dict) else obj):
            _key_numbers(val, out)


def _find_results_json(script: str, max_up: int = 6) -> str | None:
    """同目录 → 逐级上层目录（含上层目录的一级子目录，如 q2/06-computation/results.json）。"""
    cur = os.path.dirname(os.path.abspath(script))
    for _ in range(max_up):
        if os.path.isfile(os.path.join(cur, "results.json")):
            return os.path.join(cur, "results.json")
        try:
            subs = sorted(os.listdir(cur))
        except OSError:
            subs = []
        for sub in subs:
            if os.path.isfile(os.path.join(cur, sub, "results.json")):
                return os.path.join(cur, sub, "results.json")
        cur = os.path.dirname(cur)
    return None


def _check_hardcode(tree: ast.AST, script: str, report: FileReport) -> None:
    """py.hardcode：有 results.json 才查，找不到就静默跳过。"""
    path = _find_results_json(script)
    if path is None:
        return
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return
    keys: set[float] = set()
    _key_numbers(data, keys)
    hits = [(node.lineno, float(node.value)) for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float))
            and not isinstance(node.value, bool) and float(node.value) in keys]
    if hits:
        report.add(P1, "py.hardcode", f"{os.path.basename(os.path.dirname(path))}/results.json 存在，脚本硬编码了 "
                   f"{len(hits)} 个与其一致的关键数值（{', '.join(f'L{n}={v:g}' for n, v in hits[:6])}"
                   f"{'…' if len(hits) > 6 else ''}）：应经 results.json 读取", [v for _, v in hits])


def _check_font(src: str, has_mpl: bool, report: FileReport) -> None:
    """py.font：CJK 字体设置 + axes.unicode_minus=False（只对 matplotlib 脚本）。"""
    if not has_mpl:
        return
    missing = []
    if not (_CJK_FONT_RE.search(src) or _FONT_RE.search(src)):
        missing.append("CJK 字体设置（font.sans-serif = ['Noto Sans CJK SC', …]）")
    if not _UNICODE_MINUS_RE.search(src):
        missing.append("axes.unicode_minus = False")
    if missing:
        report.add(P1, "py.font", f"缺少 {'；'.join(missing)}（中文/负号会渲染异常或缺失）", missing)


def lint_py(path: str, report: FileReport) -> None:
    """AST 扫描绘图脚本（不执行）。语法错误/读不到/非 UTF-8 → 单条 P0 py.unreadable。"""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError as exc:
        report.add(P0, "py.unreadable", f"读不到文件：{exc}")
        return
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        report.add(P0, "py.unreadable", f"语法错误：第{exc.lineno}行 {exc.msg}")
        return
    scan = _scan_ast(tree)
    _check_titles(scan["titles"], report)
    _check_strings(scan["strings"], report)
    _check_legend(scan["data_calls"], scan["legend_calls"], report)
    _check_hardcode(tree, path, report)
    _check_font(src, scan["has_mpl"], report)

# --------------------------------------------------------------------------- B. --png


class InkStats(NamedTuple):
    """墨迹统计：行/列墨迹计数 + 总量（够算四边距与占比，不必存整图）。"""

    width: int
    height: int
    rows: list[int]
    cols: list[int]
    total: int

    def margins(self) -> tuple[int, int, int, int] | None:
        """(left, right, top, bottom)，单位 = 图像实际像素；无墨迹 → None。"""
        if self.total == 0:
            return None
        top = next(i for i, n in enumerate(self.rows) if n)
        bottom = next(i for i, n in enumerate(reversed(self.rows)) if n)
        left = next(i for i, n in enumerate(self.cols) if n)
        right = next(i for i, n in enumerate(reversed(self.cols)) if n)
        return left, right, top, bottom

    def ink_ratio(self) -> float:
        return self.total / float(max(1, self.width * self.height))


def _unfilter(kind: int, line: bytearray, prev: bytearray, bpp: int, stride: int) -> None:
    """PNG 反滤波（就地修改 line）。"""
    if kind == 0:
        return
    for i in range(stride):
        a = line[i - bpp] if i >= bpp else 0
        b, c = prev[i], prev[i - bpp] if i >= bpp else 0
        if kind == 1:
            line[i] = (line[i] + a) & 0xFF
        elif kind == 2:
            line[i] = (line[i] + b) & 0xFF
        elif kind == 3:
            line[i] = (line[i] + ((a + b) >> 1)) & 0xFF
        elif kind == 4:
            p = a + b - c
            pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
            line[i] = (line[i] + (a if (pa <= pb and pa <= pc) else (b if pb <= pc else c))) & 0xFF
        else:
            raise ValueError(f"未知滤波类型 {kind}")


def _png_header(path: str) -> tuple[int, int, int, int]:
    """读 IHDR：宽、高、位深、颜色类型（纯 stdlib）。"""
    with open(path, "rb") as fh:
        head = fh.read(29)
    if head[:8] != b"\x89PNG\r\n\x1a\n" or len(head) < 29:
        raise ValueError("不是 PNG 文件")
    width, height, depth, ctype, _c, _f, interlace = struct.unpack(">IIBBBBB", head[16:29])
    if interlace:
        raise ValueError("不支持隔行扫描 PNG")
    return width, height, depth, ctype


def _png_size(path: str) -> tuple[int, int] | None:
    """PNG 宽高（无需 PIL）。"""
    try:
        with open(path, "rb") as fh:
            head = fh.read(24)
        return struct.unpack(">II", head[16:24]) if head[:8] == b"\x89PNG\r\n\x1a\n" else None
    except OSError:
        return None


def _stats_stdlib(path: str) -> InkStats:
    """无 PIL 时的降级解码：zlib + 逐行反滤波（灰度/RGB/调色板/含 alpha，8 或 16 位）。"""
    width, height, depth, ctype = _png_header(path)
    if depth not in (8, 16) or ctype not in (0, 2, 3, 4, 6):
        raise ValueError(f"降级解码不支持 位深={depth} 颜色类型={ctype}")
    with open(path, "rb") as fh:
        data = fh.read()
    pos, idat, plte = 8, bytearray(), None
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctag, body = data[pos + 4:pos + 8], data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if ctag == b"IDAT":
            idat += body
        elif ctag == b"PLTE":
            plte = bytes(body)
        elif ctag == b"IEND":
            break
    bpp = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype] * (depth // 8)
    stride = width * bpp
    raw = zlib.decompress(bytes(idat))
    rows, cols, total, prev, off = [0] * height, [0] * width, 0, bytearray(stride), 0
    for y in range(height):
        kind = raw[off]
        line = bytearray(raw[off + 1:off + 1 + stride])
        off += 1 + stride
        _unfilter(kind, line, prev, bpp, stride)
        prev = line
        for x in range(width):
            i = x * bpp
            if ctype == 2:
                r, g, b, a = line[i], line[i + 1], line[i + 2], 255
            elif ctype == 6:
                r, g, b, a = line[i], line[i + 1], line[i + 2], line[i + 3]
            elif ctype == 4:
                r = g = b = line[i]
                a = line[i + 1]
            elif ctype == 3:
                idx = line[i] * 3
                r, g, b = (plte[idx], plte[idx + 1], plte[idx + 2]) if plte else (0, 0, 0)
                a = 255
            else:
                r = g = b = line[i]
                a = 255
            if a > 16 and max(255 - r, 255 - g, 255 - b) > 12:  # 非白且不透明 → 墨迹
                rows[y] += 1
                cols[x] += 1
                total += 1
    return InkStats(width, height, rows, cols, total)


def _stats_pil(path: str) -> InkStats:
    """PIL 快路径（不依赖 numpy：用 tobytes 逐行统计，保持「仅 stdlib + PIL」的依赖面）。"""
    from PIL import Image

    with Image.open(path) as im:
        im.load()
        keep_alpha = im.mode in ("RGBA", "LA", "PA", "P") or "transparency" in im.info
        rgb_im = im.convert("RGBA" if keep_alpha else "RGB")
        raw = rgb_im.tobytes()
        width, height = rgb_im.size
        bpp = 4 if keep_alpha else 3
        rows = [0] * height
        cols = [0] * width
        total = 0
        for y in range(height):
            base = y * width * bpp
            for x in range(width):
                o = base + x * bpp
                if raw[o] < 250 or raw[o + 1] < 250 or raw[o + 2] < 250:
                    rows[y] += 1
                    cols[x] += 1
                    total += 1
        return InkStats(width, height, rows, cols, total)
    rgb = arr[..., :3]
    alpha = arr[..., 3] if arr.shape[2] > 3 else np.full(rgb.shape[:2], 255, dtype=np.int16)
    ink = ((255 - rgb).max(axis=2) > 12) & (alpha > 16)
    return InkStats(int(rgb.shape[1]), int(rgb.shape[0]), [int(v) for v in ink.sum(axis=1)],
                    [int(v) for v in ink.sum(axis=0)], int(ink.sum()))


def lint_png(path: str, margin_px: int, report: FileReport) -> None:
    """像素级：边距（P0）/宽度（P1）/空图（P0）；PIL 不可用时降级 stdlib 解码。"""
    try:
        try:
            stats = _stats_pil(path)
        except ImportError:
            stats = _stats_stdlib(path)
    except Exception as exc:
        report.add(P0, "png.unreadable", f"PNG 解码失败：{exc}")
        return
    ratio = stats.ink_ratio()
    if stats.total == 0 or ratio < 0.002:
        report.add(P0, "png.blank", f"墨迹占比 {ratio * 100:.3f}% < 0.2%（疑似空图）；尺寸 "
                   f"{stats.width}x{stats.height}", round(ratio * 100, 3))
        return
    left, right, top, bottom = stats.margins() or (0, 0, 0, 0)
    bad = [(n, v) for n, v in (("左", left), ("右", right), ("上", top), ("下", bottom)) if v < margin_px]
    if bad:
        report.add(P0, "png.margin", f"{'、'.join(f'{n}边 {v}px' for n, v in bad)} < {margin_px}px"
                   f"（墨迹贴边，标签/图注可能被裁）；图像 {stats.width}x{stats.height}", [v for _, v in bad])
    is_diagram = os.path.isfile(os.path.splitext(path)[0] + ".html")
    need = 1600 if is_diagram else 1200
    if stats.width < need:
        report.add(P1, "png.size", f"宽度 {stats.width}px < {need}px（"
                   f"{'同目录存在同名 .html（示意图标准）' if is_diagram else '2x 画布要求'}）", stats.width)

# --------------------------------------------------------------------------- C. --svg

_TAG_RE = re.compile(r"<(rect|circle|ellipse|line|path|polyline|polygon|text)\b([^>]*?)/?>", re.S)
_ATTR_RE = re.compile(r"([A-Za-z_:][-\w:.]*)\s*=\s*\"([^\"]*)\"")   # 解析前由 _norm_quotes 把单引号属性统一成双引号
_SQ_ATTR_RE = re.compile(r"([A-Za-z_:][-\w:.]*)\s*=\s*'([^']*)'")


def _norm_quotes(text: str) -> str:
    """把单引号属性规范成双引号（合法 HTML/SVG 写法不能绕过 §2–§5 判据）。"""
    return _SQ_ATTR_RE.sub(lambda m: '%s="%s"' % (m.group(1), m.group(2).replace('"', "&quot;")), text)
_TEXT_RE = re.compile(r"<text\b([^>]*)>(.*?)</text>", re.S)
_STYLE_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.S)
_CSS_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)
_TAG_STRIP_RE = re.compile(r"<[^>]+>")
_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
_CSS_COLOR_RE = re.compile(r"(?:fill|stroke|color|stop-color|background|background-color)\s*:\s*([^;]+)", re.I)
_DEFS_RE = re.compile(r"<(defs|marker|clipPath|pattern)\b.*?</\1>", re.S | re.I)
_COMMAND_RE = re.compile(r"([MmLlHhVvZz])|(-?\d*\.?\d+)")
_ALLOWED_COLORS = frozenset({
    "#ffffff", "#1a1a1a", "#4f5d75", "#2e5aa8", "#6b7280", "rgba(46,90,168,0.08)", "rgba(26,26,26,0.12)",
    "none", "transparent", "currentcolor", "inherit"})
_ALLOWED_FONT_SIZES = (8, 12, 16, 20, 24)
_GRID_ATTRS = ("x", "y", "width", "height", "cx", "cy", "x1", "y1", "x2", "y2")
_MASK_MAX_H, _MASK_MAX_W = 24.0, 200.0


@dataclass
class _Element:
    """svg 元素（已排除 defs/marker/clipPath/pattern 内的 shape）。"""

    tag: str
    attrs: dict[str, str]


def _num(attrs: dict[str, str], key: str) -> float | None:
    """取数值属性（缺失/非数值 → None）。"""
    match = _NUM_RE.search(attrs.get(key, ""))
    return float(match.group(0)) if match else None


def _rect_of(el: _Element) -> tuple[float, float, float, float] | None:
    """rect 的 (x, y, w, h)。"""
    vals = [_num(el.attrs, k) for k in ("x", "y", "width", "height")]
    return None if None in vals else (vals[0], vals[1], vals[2], vals[3])  # type: ignore[return-value]


def _parse_svg(text: str) -> tuple[list[_Element], list[tuple[dict[str, str], str]], dict[str, str]]:
    """返回 (元素, [(text 属性, 文本)], CSS 规则表)；defs/marker 内一律排除。"""
    spans = [(m.start(), m.end()) for m in _DEFS_RE.finditer(text)]
    inside = lambda pos: any(lo <= pos < hi for lo, hi in spans)  # noqa: E731
    elements = [_Element(m.group(1), dict(_ATTR_RE.findall(m.group(2)))) for m in _TAG_RE.finditer(text)
                if not inside(m.start())]
    texts = [(dict(_ATTR_RE.findall(m.group(1))), _TAG_STRIP_RE.sub("", m.group(2)).strip())
             for m in _TEXT_RE.finditer(text) if not inside(m.start())]
    css: dict[str, str] = {}
    for block in _STYLE_RE.findall(text):
        for sel, decls in _CSS_RULE_RE.findall(block):
            css.setdefault(sel.strip(), decls.strip())
    return elements, texts, css


def _segments(el: _Element) -> list[tuple[float, float, float, float]]:
    """取判定用直线段；含曲线命令（C/S/Q/T/A）的 path 整条跳过。"""
    if el.tag == "line":
        v = [_num(el.attrs, k) for k in ("x1", "y1", "x2", "y2")]
        return [] if None in v else [(v[0], v[1], v[2], v[3])]  # type: ignore[list-item]
    if el.tag == "polyline":
        n = [float(x) for x in _NUM_RE.findall(el.attrs.get("points", ""))]
        return [(n[i], n[i + 1], n[i + 2], n[i + 3]) for i in range(0, len(n) - 3, 2)]
    d = el.attrs.get("d", "") if el.tag == "path" else ""
    if not d or re.search(r"[CcSsQqTtAa]", d):
        return []
    segs: list[tuple[float, float, float, float]] = []
    cur = start = (0.0, 0.0)
    cmd, buf = "M", []

    def flush() -> None:
        """把 buf 里的坐标按 cmd 转成线段（支持 M/L/H/V/Z 与相对指令）。"""
        nonlocal cur, start
        step = 1 if cmd in "HhVv" else 2
        for i in range(0, len(buf) - step + 1, step):
            a, b = (buf[i], 0.0) if step == 1 else (buf[i], buf[i + 1])
            if cmd in "Mm":
                cur = (a, b) if cmd == "M" else (cur[0] + a, cur[1] + b)
                start = cur
                continue
            if cmd in "Hh":
                nxt = (a, cur[1]) if cmd == "H" else (cur[0] + a, cur[1])
            elif cmd in "Vv":
                nxt = (cur[0], a) if cmd == "V" else (cur[0], cur[1] + a)
            else:
                nxt = (a, b) if cmd == "L" else (cur[0] + a, cur[1] + b)
            segs.append((cur[0], cur[1], nxt[0], nxt[1]))
            cur = nxt

    for letter, number in _COMMAND_RE.findall(d):
        if not letter:
            buf.append(float(number))
            continue
        flush()
        buf, cmd = [], letter
        if letter in "Zz":
            segs.append((cur[0], cur[1], start[0], start[1]))
            cur = start
    flush()
    return [s for s in segs if (s[0], s[1]) != (s[2], s[3])]


def _clip_len(x1: float, y1: float, x2: float, y2: float, rect: tuple[float, float, float, float]) -> float:
    """Liang-Barsky：线段落在矩形内的长度。"""
    rx, ry, rw, rh = rect
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - rx), (dx, rx + rw - x1), (-dy, y1 - ry), (dy, ry + rh - y1)):
        if abs(p) < 1e-12:
            if q < 0:
                return 0.0
            continue
        r = q / p
        t0, t1 = (max(t0, r), t1) if p < 0 else (t0, min(t1, r))
    return 0.0 if t0 >= t1 else math.hypot(dx, dy) * (t1 - t0)


def _seg_rect_gap(x1: float, y1: float, x2: float, y2: float,
                  rect: tuple[float, float, float, float]) -> float:
    """线段到矩形最短距离（相交 → 0）：端点→矩形 + 矩形角→线段，取最小。"""
    if _clip_len(x1, y1, x2, y2, rect) > 0:
        return 0.0
    rx, ry, rw, rh = rect
    vx, vy = x2 - x1, y2 - y1
    length2 = vx * vx + vy * vy
    gaps = [math.hypot(px - min(max(px, rx), rx + rw), py - min(max(py, ry), ry + rh))
            for px, py in ((x1, y1), (x2, y2))]
    for cx, cy in ((rx, ry), (rx + rw, ry), (rx, ry + rh), (rx + rw, ry + rh)):
        t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((cx - x1) * vx + (cy - y1) * vy) / length2))
        gaps.append(math.hypot(cx - (x1 + t * vx), cy - (y1 + t * vy)))
    return min(gaps)


def _check_geometry(elements: Sequence[_Element], text: str, report: FileReport) -> None:
    """§3：4px 网格（svg.grid）、正交连线（svg.orthogonal）、节点/箭头上限（svg.count）。"""
    offgrid = [f"<{el.tag} {key}={val:g}>" for el in elements for key in _GRID_ATTRS
               if (val := _num(el.attrs, key)) is not None and val % 4 != 0]
    if offgrid:
        report.add(P0, "svg.grid", f"{len(offgrid)} 个坐标不整除 4：{', '.join(offgrid[:8])}"
                   f"{'…' if len(offgrid) > 8 else ''}；§3 要求坐标/尺寸走 4px 网格", len(offgrid))
    diag = [f"<{el.tag}> {x1:g},{y1:g}→{x2:g},{y2:g}" for el in elements for x1, y1, x2, y2 in _segments(el)
            if abs(x1 - x2) > 1e-9 and abs(y1 - y2) > 1e-9]
    if diag:
        report.add(P0, "svg.orthogonal", f"{len(diag)} 段斜线连线（§3 要求正交直角）：{'; '.join(diag[:4])}",
                   len(diag))
    nodes = 0
    for el in elements:
        box = _rect_of(el) if el.tag == "rect" else None
        if el.tag in ("rect", "circle", "ellipse", "polygon") and not (
                box and box[3] <= _MASK_MAX_H and box[2] <= 80):
            nodes += 1
    arrows = len(re.findall(r"marker-end\s*=", text))
    if nodes > 9:
        report.add(P1, "svg.count", f"节点 {nodes} 个 > 9（§3 上限）", nodes)
    if arrows > 12:
        report.add(P1, "svg.count", f"箭头 {arrows} 个 > 12（§3 上限）", arrows)


def _check_mask(elements: Sequence[_Element], report: FileReport) -> None:
    """§3：标签遮罩不得压线（例外：重叠 ≤遮罩厚度 50% 或侧向偏移 ≥6px）；间隙应 6-10px。"""
    masks = [box for el in elements if el.tag == "rect"
             and (el.attrs.get("fill") or "").strip().lower() not in ("", "none", "transparent")
             and (box := _rect_of(el)) is not None and box[3] <= _MASK_MAX_H and box[2] <= _MASK_MAX_W]
    segs = [s for el in elements if el.tag in ("line", "path", "polyline") for s in _segments(el)]
    hard: list[str] = []
    soft: list[str] = []
    for box in masks:
        for x1, y1, x2, y2 in segs:
            inside = _clip_len(x1, y1, x2, y2, box)
            thickness = (abs(x2 - x1) * box[2] + abs(y2 - y1) * box[3]) / (math.hypot(x2 - x1, y2 - y1) or 1.0)
            label = f"遮罩({box[0]:g},{box[1]:g},{box[2]:g}x{box[3]:g}) ↔ 线({x1:g},{y1:g})→({x2:g},{y2:g})"
            if inside > 0.5 * thickness:
                hard.append(f"{label} 相交覆盖 {inside:.1f}px / 厚度 {thickness:.1f}px")
            else:
                gap = _seg_rect_gap(x1, y1, x2, y2, box)
                if inside == 0 and 0 < gap < 6:
                    soft.append(f"{label} 间隙 {gap:.1f}px")
    if hard:
        report.add(P0, "svg.mask", f"{len(hard)} 处文字遮罩压住连线（>遮罩厚度 50%）：{'; '.join(hard[:3])}",
                   len(hard))
    if soft:
        report.add(P1, "svg.mask", f"{len(soft)} 处遮罩-线间隙 <6px（规范 6-10px）：{'; '.join(soft[:3])}",
                   len(soft))


def _collect_colors(text: str, elements: Sequence[_Element]) -> dict[str, str]:
    """收集 svg 属性 / 内联 style / <style> 里的 fill|stroke|color|background 颜色（归一化小写）。"""
    found: dict[str, str] = {}

    def norm(raw: str) -> str:
        val = re.sub(r"\s+", "", raw.strip().lower())
        return "#" + "".join(c * 2 for c in val[1:]) if re.fullmatch(r"#[0-9a-f]{3}", val) else val

    for el in elements:
        pairs = [(f"{el.tag}@{k}", el.attrs[k]) for k in ("fill", "stroke", "color", "stop-color")
                 if el.attrs.get(k)]
        pairs += [(f"{el.tag}@style", v) for v in _CSS_COLOR_RE.findall(el.attrs.get("style", ""))]
        for where, raw in pairs:
            found.setdefault(norm(raw), where)
    for block in _STYLE_RE.findall(text):
        for raw in _CSS_COLOR_RE.findall(block):
            found.setdefault(norm(raw), "css")
    return found


def _check_font_svg(text: str, elements: Sequence[_Element], texts: Sequence[tuple[dict[str, str], str]],
                    css: dict[str, str], report: FileReport) -> None:
    """§3/§5：字号 ∈ {8,12,16,20,24}、CJK 文字 ≥12px、字体栈带本机 CJK 回退。"""
    sizes: dict[float, str] = {}
    for el in elements:
        if (val := _num(el.attrs, "font-size")) is not None:
            sizes.setdefault(val, f"<{el.tag}>")
    for sel, decls in css.items():
        match = re.search(r"font-size\s*:\s*([\d.]+)px", decls)
        if match and any(k in sel for k in ("caption", "text", "svg", "body", "html")):
            sizes.setdefault(float(match.group(1)), f"css {sel}")
    bad = [v for v in sorted(sizes) if v not in _ALLOWED_FONT_SIZES]
    if bad:
        report.add(P1, "svg.font", f"非规范字号：{', '.join(f'{v:g}px（{sizes[v]}）' for v in bad[:6])}；"
                   f"§3 仅允许 {list(_ALLOWED_FONT_SIZES)}", bad)
    if not _CJK_FONT_RE.search(text):
        report.add(P1, "svg.font", "字体栈缺 CJK 回退（§5：'Noto Sans CJK SC'/'PingFang SC'/'Microsoft YaHei'）")
    small = [f"{_clip(content, 24)}={size:g}px" for attrs, content in texts
             if (size := _num(attrs, "font-size")) is not None and size < 12 and _CJK_RE.search(content)]
    if small:
        report.add(P1, "svg.font", f"{len(small)} 处 CJK 文字 <12px：{'; '.join(small[:4])}", len(small))


def _check_caption_canvas(path: str, text: str, css: dict[str, str], report: FileReport) -> None:
    """§4：图注 12px/#6b7280/居中（svg.caption）；viewBox 与 2x 画布（svg.canvas）。"""
    rule = next((decls for sel, decls in css.items() if "caption" in sel), None)
    if rule is None:
        has_el = bool(re.search(r'class\s*=\s*"[^"]*caption', text))
        report.add(P1, "svg.caption", "有 .caption 元素但缺 CSS 规则，无法确认 12px/#6b7280/居中" if has_el
                   else "未找到图注样式（§4 要求图下方 12px #6b7280 居中）")
    else:
        match = re.search(r"font-size\s*:\s*([\d.]+)px", rule)
        size = float(match.group(1)) if match else None
        bad = []
        if size is None or abs(size - 12) > 1:
            bad.append(f"font-size {f'{size:g}px' if size else '缺失'}（应 12px±1）")
        if "#6b7280" not in rule.lower():
            bad.append("color 非 #6b7280")
        if not re.search(r"text-align\s*:\s*center", rule):
            bad.append("未居中（缺 text-align: center）")
        if bad:
            report.add(P1, "svg.caption", "图注样式不合 §4：" + "；".join(bad), bad)
    match = re.search(r'viewBox\s*=\s*"([^"]+)"', text)
    parts = [float(v) for v in _NUM_RE.findall(match.group(1))] if match else []
    if len(parts) != 4:
        report.add(P1, "svg.canvas", "未找到 viewBox，无法核对 2x 画布")
        return
    width, height = parts[2], parts[3]
    if width % 4 or height % 4:
        report.add(P1, "svg.canvas", f"viewBox {width:g}x{height:g} 不整除 4", [width, height])
    png = os.path.splitext(path)[0] + ".png"
    size2 = _png_size(png) if os.path.isfile(png) else None
    expect = (int(width * 2), int((height + 24) * 2))
    if size2 is not None and size2 != expect:
        report.add(P1, "svg.canvas", f"同名 PNG {size2[0]}x{size2[1]} ≠ 2×画布 {expect[0]}x{expect[1]}"
                   f"（画布 {width:g}x{height + 24:g}）", list(size2))


def lint_svg(path: str, report: FileReport) -> None:
    """解析 .svg / 含内联 <svg> 的 .html：§2 token、§3 网格·正交·遮罩、§4 图注、§5 字体。"""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = _norm_quotes(fh.read())
    except OSError as exc:
        report.add(P0, "svg.unreadable", f"读不到文件：{exc}")
        return
    if "<svg" not in text.lower():
        report.add(P0, "svg.unreadable", "文件中未找到内联 <svg>")
        return
    elements, texts, css = _parse_svg(text)
    _check_geometry(elements, text, report)
    _check_mask(elements, report)
    colors = _collect_colors(text, elements)
    bad = sorted(c for c in colors if c not in _ALLOWED_COLORS and not c.startswith("url("))
    if bad:
        report.add(P0, "svg.color", f"{len(bad)} 个颜色不在 §2 token 白名单："
                   f"{', '.join(f'{c}（{colors[c]}）' for c in bad[:6])}", bad)
    _check_font_svg(text, elements, texts, css, report)
    _check_caption_canvas(path, text, css, report)

# --------------------------------------------------------------------------- D. --render

_RENDER_DRIVER = r'''# -*- coding: utf-8 -*-
"""figure_lint --render 驱动：Agg 执行绘图脚本，monkeypatch savefig 收集 Figure 后内省。"""
import json, os, runpy, sys, traceback
script, outJson, tmpDir = sys.argv[1], sys.argv[2], sys.argv[3]
result = {"error": None, "figures": [], "savefigErrors": []}
import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.colors import to_rgba

def rgbsOf(art):
    out = []
    for getter in ("get_color", "get_facecolor", "get_edgecolor"):
        fn = getattr(art, getter, None)
        if fn is None:
            continue
        try:
            val = fn()
            if isinstance(val, str):
                out.append([round(v, 4) for v in to_rgba(val)])
                continue
            seq = list(val)
            if seq and hasattr(seq[0], "__len__") and not isinstance(seq[0], str):
                for row in seq[:4]:
                    out.append([round(float(v), 4) for v in list(row)[:4]])
            elif len(seq) >= 3:
                out.append([round(float(v), 4) for v in seq[:4]])
        except Exception:
            continue
    return out

def hasGeom(art):
    try:
        if hasattr(art, "get_paths"):
            return bool(any(len(getattr(p, "vertices", [])) > 2 for p in art.get_paths()))
        if hasattr(art, "get_xdata"):
            return bool(len(art.get_xdata()) >= 2)
        if hasattr(art, "get_width"):
            return bool(abs(art.get_width()) > 0 and abs(art.get_height()) > 0)
    except Exception:
        return True
    return True

def boxOf(obj, renderer):
    bb = obj.get_window_extent(renderer)
    return [round(float(bb.x0), 2), round(float(bb.y0), 2), round(float(bb.x1), 2), round(float(bb.y1), 2)]

def introspect(fig, index):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    info = {"index": index, "canvas": boxOf(fig, renderer), "axes": [],
            "suptitle": fig._suptitle.get_text() if fig._suptitle is not None else ""}
    for ax in fig.axes:
        axInfo = {"title": ax.get_title(), "ticks": {}, "legends": [], "artists": []}
        for name in ("x", "y", "z"):
            axis = getattr(ax, name + "axis", None)
            if axis is None:
                continue
            labels = [t.get_text() for t in axis.get_ticklabels() if t.get_visible() and t.get_text().strip()]
            if labels:
                axInfo["ticks"][name] = labels
        for art in list(ax.get_lines()) + list(ax.patches) + list(ax.collections):
            try:
                if hasattr(art, "get_xdata") and str(art.get_label()).startswith("_"):
                    continue  # 仅为占位的辅助线（不进图例）
                axInfo["artists"].append({"type": type(art).__name__, "box": boxOf(art, renderer),
                                          "colors": rgbsOf(art), "geom": hasGeom(art),
                                          "visible": bool(art.get_visible())})
            except Exception:
                continue
        legend = ax.get_legend()
        if legend is not None and legend.get_visible():
            try:
                axInfo["legends"].append({"box": boxOf(legend, renderer),
                                          "texts": [t.get_text() for t in legend.get_texts()],
                                          "textBoxes": [boxOf(t, renderer) for t in legend.get_texts()]})
            except Exception:
                pass
        info["axes"].append(axInfo)
    return info

captured = []
originalSavefig = Figure.savefig

def patchedSavefig(self, fname, *args, **kwargs):
    dst = os.path.join(tmpDir, "captured_%d.png" % len(captured))
    try:
        originalSavefig(self, dst, *args, **kwargs)
    except Exception as exc:
        result["savefigErrors"].append(repr(exc))
    index = len(captured)
    captured.append(self)
    try:
        result["figures"].append(introspect(self, index))
    except Exception:
        result.setdefault("introspectErrors", []).append(traceback.format_exc(limit=4))
    return None

Figure.savefig = patchedSavefig
os.chdir(os.path.dirname(os.path.abspath(script)))
sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
sys.argv = [script]
try:
    runpy.run_path(script, run_name="__main__")
except BaseException as exc:
    result["error"] = "".join(traceback.format_exception_only(type(exc), exc)).strip()
    result["traceback"] = traceback.format_exc(limit=6)
with open(outJson, "w", encoding="utf-8") as fh:
    json.dump(result, fh, ensure_ascii=False, default=str)
'''


def _run_render_driver(script: str, timeout: float) -> tuple[dict[str, Any] | None, str | None]:
    """子进程 Agg 执行脚本并收集内省 JSON；返回 (数据, 失败原因)。"""
    with tempfile.TemporaryDirectory(prefix="figure_lint_") as tmp:
        driver, out_json = os.path.join(tmp, "driver.py"), os.path.join(tmp, "out.json")
        with open(driver, "w", encoding="utf-8") as fh:
            fh.write(_RENDER_DRIVER)
        env = dict(os.environ)
        env.update({"MPLCONFIGDIR": tmp, "MPLBACKEND": "Agg", "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONIOENCODING": "utf-8"})
        try:
            proc = subprocess.run([sys.executable, driver, os.path.abspath(script), out_json, tmp],
                                  capture_output=True, text=True, timeout=timeout, env=env, check=False)
        except subprocess.TimeoutExpired:
            return None, f"执行超时 >{timeout:g}s"
        except OSError as exc:
            return None, f"子进程启动失败：{exc}"
        if not os.path.isfile(out_json):
            tail = _clip(proc.stderr.strip().splitlines()[-1], 120) if proc.stderr.strip() else ""
            return None, f"驱动未产出结果（退出码 {proc.returncode}）{tail}"
        with open(out_json, encoding="utf-8") as fh:
            data = json.load(fh)
    return (data, f"脚本执行中断：{data['error']}") if data.get("error") else (data, None)


def _ticksep_labels(labels: Iterable[str]) -> list[str]:
    """千分位逗号 / 裸大数（≥5 位无分隔整数）/ 代码式科学计数法的刻度标签。"""
    return [raw for raw in labels if re.search(r"\d,\d{3}", raw.replace("\u2212", "-"))
            or _SCI_RE.search(raw) or re.fullmatch(r"-?\d{5,}", raw.strip())]


_ASCII_COLOR_WORDS = {"green": "green", "red": "red", "blue": "blue", "yellow": "yellow",
                      "orange": "orange", "purple": "purple", "gray": "gray", "grey": "gray",
                      "black": "black", "cyan": "cyan", "white": "white", "gold": "gold"}
_CJK_COLOR_WORDS = {"绿": "green", "红": "red", "蓝": "blue", "黄": "yellow", "橙": "orange",
                    "紫": "purple", "灰": "gray", "黑": "black", "青": "cyan", "白": "white", "金": "gold"}
_ASCII_COLOR_RE = re.compile(r"\b(" + "|".join(_ASCII_COLOR_WORDS) + r")\b", re.I)
_CJK_COLOR_RE = re.compile("|".join(_CJK_COLOR_WORDS))
# 色相粗判（render.invisible_claim 用；不做像素级校验）
_COLOR_TESTS: dict[str, Any] = {
    "green": lambda r, g, b: g > 0.35 and g - max(r, b) > 0.15,
    "red": lambda r, g, b: r > 0.35 and r - max(g, b) > 0.15,
    "blue": lambda r, g, b: b > 0.35 and b - max(r, g) > 0.12,
    "yellow": lambda r, g, b: r > 0.5 and g > 0.5 and b < 0.45,
    "orange": lambda r, g, b: r > 0.6 and 0.25 < g < 0.75 and b < 0.4,
    "purple": lambda r, g, b: r > 0.3 and b > 0.3 and g < min(r, b) - 0.05,
    "cyan": lambda r, g, b: g > 0.5 and b > 0.5 and r < 0.5,
    "gray": lambda r, g, b: max(r, g, b) - min(r, g, b) < 0.12 and 0.25 < max(r, g, b) < 0.85,
    "black": lambda r, g, b: max(r, g, b) < 0.3,
    "white": lambda r, g, b: min(r, g, b) > 0.85,
    "gold": lambda r, g, b: r > 0.6 and g > 0.45 and b < 0.45}


def _claimed_colors(text: str) -> list[str]:
    """标题/图注里提到的颜色词（尽力而为的粗匹配）。"""
    if not text:
        return []
    names = {_ASCII_COLOR_WORDS[w.lower()] for w in _ASCII_COLOR_RE.findall(text)}
    return sorted(names | {_CJK_COLOR_WORDS[w] for w in _CJK_COLOR_RE.findall(text)})


def _color_match(rgba: Sequence[float], name: str) -> bool:
    """该图元颜色是否算得上 name 这种颜色（半透明≈不可见则不算）。"""
    r, g, b, a = (list(rgba) + [1.0, 1.0, 1.0, 1.0])[:4]
    test = _COLOR_TESTS.get(name)
    return bool(test and a >= 0.05 and test(r, g, b))


def _check_rendered(data: dict[str, Any], report: FileReport) -> None:
    """内省数据 → 4 类问题：刻度分隔 / 图例遮挡·越界 / 标题 / 图文不符。"""
    tick_bad: dict[str, str] = {}
    cover: list[tuple[float, str, int]] = []
    clip: list[str] = []
    titles: list[str] = []
    missing: set[str] = set()
    for fig in data.get("figures", []):
        canvas = fig["canvas"]
        outside = lambda box: (box[0] < canvas[0] - 0.5 or box[2] > canvas[2] + 0.5  # noqa: E731
                               or box[1] < canvas[1] - 0.5 or box[3] > canvas[3] + 0.5)
        if fig.get("suptitle", "").strip():
            titles.append(f"suptitle {_clip(fig['suptitle'], 32)!r}")
        for index, ax in enumerate(fig.get("axes", [])):
            if ax.get("title", "").strip():
                titles.append(f"ax{index} {_clip(ax['title'], 32)!r}")
            for axis_name, labels in ax.get("ticks", {}).items():
                for label in _ticksep_labels(labels):
                    tick_bad.setdefault(label, f"fig{fig['index']} {axis_name}轴")
            for legend in ax.get("legends", []):
                if outside(legend["box"]):
                    clip.append(f"fig{fig['index']} 图例框 {[round(v, 1) for v in legend['box']]} 越界")
                for name, box in zip(legend["texts"], legend["textBoxes"]):
                    if outside(box):
                        clip.append(f"fig{fig['index']} 图例文字 {_clip(name, 24)!r} 越界")
                for art in ax.get("artists", []):
                    area = (art["box"][2] - art["box"][0]) * (art["box"][3] - art["box"][1])
                    ratio = inter / area if area > 0 and (inter := _inter(legend["box"], art["box"])) else 0.0
                    if ratio > 0.05:
                        cover.append((ratio, art["type"], fig["index"]))
            visible = [a for a in ax.get("artists", []) if a["geom"] and a["visible"] and a["colors"]]
            for name in set(_claimed_colors(f"{ax.get('title', '')} {fig.get('suptitle', '')}")):
                if not any(_color_match(c, name) for a in visible for c in a["colors"]):
                    missing.add(name)
    if tick_bad:
        report.add(P0, "render.ticksep", f"{len(tick_bad)} 个刻度标签含千分位逗号/裸大数/代码式科学计数法："
                   f"{', '.join(f'{lb!r}（{w}）' for lb, w in list(tick_bad.items())[:5])}", list(tick_bad)[:8])
    if cover:
        ratio, kind, fig_index = max(cover)
        report.add(P0, "render.legend_cover", f"图例压住数据图元：fig{fig_index} {kind} 被覆盖 "
                   f"{ratio * 100:.1f}%（阈值 5%），共 {len(cover)} 个图元超阈值", round(ratio * 100, 1))
    if clip:
        report.add(P0, "render.legend_clip", f"{len(clip)} 处图例越界被裁：{'; '.join(clip[:3])}", len(clip))
    if titles:
        report.add(P1, "render.title", f"{len(titles)} 个可见标题：{'; '.join(titles[:3])}", len(titles))
    if missing:
        report.add(P1, "render.invisible_claim", f"标题/图注提到但图中找不到可见图元：{', '.join(sorted(missing))}"
                   f"（尽力而为：颜色词→色相粗匹配，不做像素级校验）", sorted(missing))


def _inter(a: Sequence[float], b: Sequence[float]) -> float:
    """两个 bbox 的重叠面积。"""
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def lint_render(script: str, timeout: float, report: FileReport) -> None:
    """渲染后内省：任何异常/超时只报 P1 render.failed，绝不让整体退出码变 2。"""
    try:
        data, failure = _run_render_driver(script, timeout)
    except Exception as exc:
        report.add(P1, "render.failed", f"--render 驱动异常：{exc!r}")
        return
    if data is None:
        report.add(P1, "render.failed", f"--render 未完成：{failure}")
        return
    if data.get("figures"):
        _check_rendered(data, report)
    else:
        report.add(P1, "render.failed", f"--render 未捕获到任何 Figure（{failure or '脚本未调用 savefig'}）")
    if failure:
        report.add(P1, "render.failed",
                   f"脚本执行中断，但已分析 {len(data.get('figures', []))} 张已保存的图：{failure}")

# --------------------------------------------------------------------------- 主流程


def _lint_one(path: str, kind: str, args: argparse.Namespace, report: FileReport) -> None:
    """按类型分发；--render 只作用于 --py。"""
    if kind == "py":
        lint_py(path, report)
        if args.render:
            lint_render(path, args.timeout, report)
    elif kind == "png":
        lint_png(path, args.margin_px, report)
    else:
        lint_svg(path, report)


def run_all(args: argparse.Namespace) -> list[FileReport]:
    """按 --py / --png / --svg 顺序检查；单文件异常降级为一条 P0 并继续。"""
    targets = ([(p, "py") for p in args.py] + [(p, "png") for p in args.png]
               + [(p, "svg") for p in args.svg])
    reports: list[FileReport] = []
    for path, kind in targets:
        report = FileReport(path, kind)
        try:
            _lint_one(path, kind, args, report)
        except Exception as exc:
            traceback.print_exc(limit=6)
            report.add(P0, f"{kind}.unreadable", f"检查过程异常（figure_lint bug，非文件问题）：{exc!r}")
        report.issues.sort(key=lambda i: (i.level, i.check))
        reports.append(report)
    return reports


def _payload(reports: Sequence[FileReport]) -> dict[str, Any]:
    """结构化结果：{files:[{path,kind,issues:[{level,check,detail,value}]}], summary:{P0,P1}}。"""
    p0 = p1 = 0
    files = []
    for report in reports:
        issues = []
        for issue in report.issues:
            p0 += issue.level == P0
            p1 += issue.level == P1
            issues.append({"level": issue.level, "check": issue.check, "detail": issue.detail,
                           "value": issue.value})
        files.append({"path": report.path, "kind": report.kind, "issues": issues})
    return {"files": files, "summary": {"P0": p0, "P1": p1}}


def format_report(payload: dict[str, Any], quiet: bool = False) -> str:
    """文本报告：[级别] 文件: check: 说明（含实测值），末尾汇总 P0=n P1=n。"""
    lines = [] if quiet else [f"[{issue['level']}] {entry['path']}: {issue['check']}: {issue['detail']}"
                              for entry in payload["files"] for issue in entry["issues"]]
    summary = payload["summary"]
    lines.append(f"汇总: 文件={len(payload['files'])} P0={summary['P0']} P1={summary['P1']}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """CLI：--py/--png/--svg 可组合，--render 默认关闭。"""
    parser = argparse.ArgumentParser(
        prog="figure_lint.py", description="数模竞赛产物图机械自检（示意图 svg/html + matplotlib PNG/脚本）")
    parser.add_argument("--py", action="extend", nargs="+", default=[], metavar="SCRIPT.py",
                        help="绘图脚本（AST 扫描；可给多个，也可重复该选项）")
    parser.add_argument("--png", action="extend", nargs="+", default=[], metavar="FILE.png",
                        help="结果图 PNG（像素检查）")
    parser.add_argument("--svg", action="extend", nargs="+", default=[], metavar="FILE.svg|FILE.html",
                        help="示意图源文件（.svg 或含内联 svg 的 .html）")
    parser.add_argument("--json", dest="json_out", metavar="OUT.json", help="额外落盘结构化结果")
    parser.add_argument("--quiet", action="store_true", help="只输出末尾汇总行")
    parser.add_argument("--render", action="store_true", help="对 --py 脚本做渲染后内省（默认关闭）")
    parser.add_argument("--timeout", type=float, default=600.0, help="--render 单脚本超时秒数（默认 600）")
    parser.add_argument("--margin-px", type=int, default=8, help="png.margin 阈值像素（默认 8）")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """入口：0 = 无 P0，1 = 有 P0，2 = 自身异常。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    if not (args.py or args.png or args.svg):
        parser.print_help(sys.stderr)
        sys.stderr.write("figure_lint: 至少要给一个 --py / --png / --svg\n")
        return 2
    try:
        payload = _payload(run_all(args))
    except Exception:
        sys.stderr.write("figure_lint 自身异常（这是脚本 bug，不是被检查文件的问题）：\n")
        traceback.print_exc(limit=8)
        return 2
    print(format_report(payload, args.quiet))          # 报告先进 stdout：--json 失败也不能丢结论
    if args.json_out:
        try:
            Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
            with open(args.json_out, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=1)
        except OSError as exc:
            sys.stderr.write(f"figure_lint: 无法写 --json（{args.json_out}）：{exc}（报告已在上方 stdout）\n")
            return 2
    return 1 if payload["summary"]["P0"] else 0


if __name__ == "__main__":
    sys.exit(main())
