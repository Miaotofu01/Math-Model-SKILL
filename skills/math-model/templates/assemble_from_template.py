#!/usr/bin/env python3
r"""CUMCM 论文组装脚本（math-model skill 内置，配合 cumcm-paper.tex 模板）。

用法:
    python3 assemble_from_template.py \
        --template <cumcm-paper.tex 路径> \
        --sections <sections 目录> \
        --output <输出 paper.tex 路径> \
        [--title "全国大学生数学建模竞赛B题"] \
        [--paper-title "论文题目"] \
        [--subtitle "基于XX的方法"] \
        [--suspect-json <名单 JSON 路径>] \
        [--suspect-title "附录B 节标题（默认：疑似名单）"] \
        [--code-dir <code 目录>] \
        [--code-entries "subsection名|文件路径" 可多次] \
        [--materials "支撑材料 item 文本" 可多次]

职责：
1. 读模板，替换 @TITLE@/@ABSTRACT@/@BODY@ 等占位符
2. 摘要：自动剥离内容开头的 \section{摘 要} 章节编号（改 \section*），
   避免与模板的摘要节标题重复
3. 名单 JSON → LaTeX 表（通用渲染：列名取自数据行键，支持任意赛题名单；
   无名单时附录 B 整节删除）
4. code 目录 → \lstinputlisting[style=pythonstyle] 条目
"""
import argparse, glob, json, os, re, sys


def load_sections(sections_dir):
    """加载 sections/*.json（{"section","content"}），按名称返回 dict。"""
    out = {}
    for f in sorted(glob.glob(os.path.join(sections_dir, 'section-*.json'))):
        try:
            d = json.load(open(f, encoding='utf-8'))
        except Exception as e:
            print(f'⚠️ 跳过 {f}: {e}', file=sys.stderr)
            continue
        if d.get('section') and d.get('content'):
            out[d['section']] = d['content']
    return out


def fix_abstract(body):
    r"""摘要内容：\section{摘 要} → \section*{摘 要}（无编号，与模板同款实现）。"""
    return re.sub(r'\\section\{摘\\quad 要\}\s*', r'\\section*{摘\\quad 要}\n', body, count=1)


def _fmt(v):
    """单元格格式化：float 保留 3 位小数，其余转字符串并转义下划线。"""
    if isinstance(v, bool):
        return '是' if v else '否'
    if isinstance(v, (int, float)):
        return f'{v:.3f}' if isinstance(v, float) else str(v)
    return str(v).replace('_', r'\_')


def suspect_to_latex(suspect_path):
    """名单 JSON → LaTeX 表（通用：列名取自首行键，含排名列；支持 dict/标量行）。"""
    if not suspect_path or not os.path.exists(suspect_path):
        return ''
    suspect = json.load(open(suspect_path, encoding='utf-8'))
    parts = []
    for i, (label, rows) in enumerate(suspect.items()):
        if not rows:
            continue
        safe_label = str(label).replace('_', r'\_')
        # 列结构：优先按首行 dict 的键；标量行退化为单列"值"
        if isinstance(rows[0], dict):
            keys = list(rows[0].keys())
            cols = ['l'] + ['c'] * len(keys)
            header = '排名 & ' + ' & '.join(k.replace('_', r'\_') for k in keys) + r' \\'
            body_lines = []
            for rank, r in enumerate(rows, 1):
                cells = [str(rank)] + [_fmt(r.get(k)) for k in keys]
                body_lines.append(' & '.join(cells) + r' \\')
        else:
            cols = ['l', 'l']
            header = '排名 & 值 \\\\'
            body_lines = [f'{rank} & {_fmt(v)} \\\\' for rank, v in enumerate(rows, 1)]
        parts.append(f"""\\begin{{table}}[H]
\\centering
\\small
\\caption{{名单（{safe_label}，按嫌疑评分降序，共{len(rows)}行）}}
\\label{{tab:suspect_{i}}}
\\begin{{tabular}}{{{''.join(cols)}}}
\\toprule
{header}
\\midrule
{chr(10).join(body_lines)}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
""")
    return '\n'.join(parts)


def code_entries(code_dir, code_files):
    r"""code 目录文件 → \subsection + \lstinputlisting 条目。"""
    if code_dir and os.path.isdir(code_dir):
        files = sorted(os.listdir(code_dir))
        files = [f for f in files if f.endswith(('.py', '.m', '.jl', '.R')) and '__pycache__' not in f]
        return '\n'.join(
            f'\\subsection{{{f.replace("_", "\\_")}}}\n'
            f'\\lstinputlisting[style=pythonstyle]{{{code_dir}/{f}}}'
            for f in files
        )
    if code_files:
        return '\n'.join(
            f'\\subsection{{{name.replace("_", "\\_")}}}\n'
            f'\\lstinputlisting[style=pythonstyle]{{{path}}}'
            for name, path in code_files
        )
    return '\\subsection{本论文没有用到程序}\n本论文没有用到程序。'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--template', required=True)
    ap.add_argument('--sections', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--title', default='全国大学生数学建模竞赛')
    ap.add_argument('--paper-title', default='')
    ap.add_argument('--subtitle', default='')
    ap.add_argument('--suspect-json', default='')
    ap.add_argument('--suspect-title', default='', help='附录B 节标题（默认：疑似名单）')
    ap.add_argument('--code-dir', default='')
    ap.add_argument('--code-entries', action='append', default=[])
    ap.add_argument('--materials', action='append', default=[])
    ap.add_argument('--references', default='', help='参考文献 thebibliography 内容（含 bibitem 行）')
    args = ap.parse_args()

    template = open(args.template, encoding='utf-8').read()

    # 章节
    sections = load_sections(args.sections)
    order = ['摘要', '问题重述', '问题重述与分析', '模型假设与符号说明', '模型假设与符号',
             '模型建立与求解', '结果分析与验证', '结论与改进']
    body_parts = []
    abstract = ''
    for name in order:
        if name in sections:
            if name == '摘要':
                abstract = fix_abstract(sections[name])
            else:
                body_parts.append(sections[name])
    body = '\n\n'.join(body_parts)
    if not abstract:
        print('⚠️ 未找到摘要章节（section-*.json 中 section 名为"摘要"）', file=sys.stderr)
    if not body:
        print('⚠️ 未找到正文章节内容', file=sys.stderr)

    # 名单/代码/支撑材料
    suspect_tex = suspect_to_latex(args.suspect_json)
    # 附录B 整节由脚本生成：有名单才输出（含前后分页），无名单整节删除
    suspect_section = ''
    if suspect_tex:
        title = args.suspect_title or '疑似名单'
        suspect_section = (
            f'\\newpage\n'
            f'\\section{{{title}}}\n'
            f'以下为按嫌疑评分降序输出的名单，字段含义见正文。\n\n'
            f'{suspect_tex}\n'
        )
    code_tex = code_entries(args.code_dir, [tuple(e.split('|', 1)) for e in args.code_entries])
    materials = args.materials or [
        '\\item 求解程序（完整可运行，位于支撑材料 code/ 目录）',
        '\\item 结果数据（results.json 等，位于 data/ 目录）',
        '\\item 图表文件（位于 figures/ 目录，均在正文引用）',
        '\\item AI工具使用详情（AI 工具使用详情.pdf，按《全国大学生数学建模竞赛人工智能工具使用规定》第4(2)条要求）',
        '\\item 赛题原始数据由竞赛提供，按规范第十一条不包含在支撑材料中；全部结果可由上述源程序直接复算',
    ]
    references = (args.references or r'''\begin{thebibliography}{99}
% ⚠️ 参考文献由写作阶段生成（\cite 键 → bibitem），组装前必须替换此占位！
\end{thebibliography}''')

    # 占位符替换
    out = template
    out = out.replace('@TITLE@', args.title)
    out = out.replace('@PAPER_TITLE@', args.paper_title)
    out = out.replace('@SUBTITLE@', args.subtitle)
    out = out.replace('@ABSTRACT@', abstract)
    out = out.replace('@BODY@', body)
    out = out.replace('@REFERENCES@', references)
    out = out.replace('@MATERIALS@', '\n'.join(materials))
    out = out.replace('@SUSPECT_SECTION@', suspect_section)
    out = out.replace('@CODE_ENTRIES@', code_tex)
    out = out.replace('@CODE_DIR@', args.code_dir)

    # 残留占位符检查（忽略 %% 注释行：注释里的 @XXX@ 是说明性示例）
    leftovers = re.findall(r'@[A-Z_]+@', '\n'.join(
        ln for ln in out.split('\n') if not ln.strip().startswith('%')))
    if leftovers:
        print(f'⚠️ 未替换占位符: {set(leftovers)}', file=sys.stderr)

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(out)
    print(f'✓ 已生成 {args.output} ({len(out)} 字符)')


if __name__ == '__main__':
    main()
