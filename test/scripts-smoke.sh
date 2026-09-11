#!/usr/bin/env bash
# scripts-smoke.sh —— 6 个技能工具的语义回归（无网络用例全跑；网络用例失败不判死）
# 用法：bash test/scripts-smoke.sh
# 每个用例对应一次真实缺陷（来源：2026-09-10 脚本审计），修完即回归。
set -u
PY=/usr/bin/python3
HERE="$(cd "$(dirname "$0")" && pwd)"
SC="$(cd "${HERE}/../skills/math-model/scripts" && pwd)"
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf "  ✓ %s\n" "$1"; }
bad()  { FAIL=$((FAIL+1)); printf "  ✗ %s\n" "$1"; }
W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT

echo "== 1. reuse_lint：扫描根路径含 outputs/results 段时不能误杀整棵树 =="
mkdir -p "$W/outputs/out/intermediates/q1/05-implementation/code" "$W/outputs/out/intermediates/q2/06-computation"
cat > "$W/outputs/out/intermediates/q1/05-implementation/code/core.py" <<'EOF'
import numpy as np
def dist(P, A, B):
    AB = B - A
    t = np.clip(((P - A) @ AB) / float(np.dot(AB, AB)), 0.0, 1.0)
    return np.linalg.norm(P - (A + t[..., None] * AB), axis=-1)
EOF
cp "$W/outputs/out/intermediates/q1/05-implementation/code/core.py" "$W/outputs/out/intermediates/q2/06-computation/scan.py"
out=$($PY "$SC/reuse_lint.py" --scan --root "$W/outputs/out" --strict 2>&1); rc=$?
if [ $rc -eq 1 ] && echo "$out" | grep -q "同形重复组 1"; then ok "路径含 outputs 仍检出重复组并 --strict 退 1"; else bad "路径含 outputs 时漏检（rc=$rc）"; fi

echo "== 2. reuse_lint：--dirs 拼错目录要报错，不能静默 0 文件 =="
$PY "$SC/reuse_lint.py" --scan --root "$W" --dirs no_such_dir >/dev/null 2>&1
[ $? -eq 2 ] && ok "--dirs 不存在 → 退出码 2" || bad "--dirs 不存在未报错"

echo "== 3. reuse_lint：--pairs 支持 ndarray vs list =="
printf 'import numpy as np\ndef f(x):\n    return np.array([x, x+1])\n' > "$W/A.py"
printf 'def f(x):\n    return [x, x+1]\n' > "$W/B.py"
out=$($PY "$SC/reuse_lint.py" --pairs "$W/A.py" "$W/B.py" --inputs '{"x":1}' 2>&1); rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -q MATCH; then ok "ndarray/list 混比判 MATCH"; else bad "ndarray/list 混比失败（rc=$rc）：$out"; fi
out=$($PY "$SC/reuse_lint.py" --pairs "$W/A.py" "$W/missing.py" 2>&1); rc=$?
if [ $rc -eq 2 ] && echo "$out" | grep -q "无法加载待对拍脚本"; then ok "缺文件 → 明确报错 + 退出码 2"; else bad "缺文件报错不清晰（rc=$rc）"; fi

echo "== 4. artifact_lint：根路径含 results 段时探针登记不能误报幽灵 =="
mkdir -p "$W/results/out/probes/adversary" "$W/results/out/intermediates"
printf '{"schema":"v1","probes":{"k1":{"purpose":"x","script":"probes/adversary/p.py"}}}' > "$W/results/out/probes/manifest.json"
printf 'print(1)\n' > "$W/results/out/probes/adversary/p.py"
out=$($PY "$SC/artifact_lint.py" --root "$W/results/out" 2>&1)
echo "$out" | grep -q "probes.ghost" && bad "根路径含 results 时误报幽灵条目" || ok "根路径含 results 不误报"

echo "== 5. artifact_lint：论文正文关键数字要计数（漏报 P0 的旧缺陷） =="
D="$W/al"; mkdir -p "$D/intermediates/q1/03-assumptions" "$D/intermediates/q1/07-sanity" "$D/intermediates/12-writing/paper-sections" "$D/intermediates/q1/06-computation"
echo '{"results":{"a":{"keyValues":{"k":4.5856}}}}' > "$D/intermediates/q1/06-computation/results.json"
for f in "$D/intermediates/q1/03-assumptions/a.md" "$D/intermediates/q1/07-sanity/s.md" "$D/intermediates/12-writing/paper-sections/section-model.md"; do echo "数值 4.5856 在此" > "$f"; done
out=$($PY "$SC/artifact_lint.py" --root "$D" 2>&1)
echo "$out" | grep -q "P0=1" && ok "论文正文数字计入 P0" || bad "论文正文数字未计数（漏报）"

echo "== 6. artifact_lint：题面给定常量出现在论文不算无源 =="
D2="$W/al2"; mkdir -p "$D2/intermediates/12-writing/paper-sections" "$D2/intermediates/q1/06-computation"
echo '{"problem":{"description":"给定 1234 万人"}}' > "$D2/intermediates/00-problem.json"
echo '{"results":{"a":{"keyValues":{"k":4.5856}}}}' > "$D2/intermediates/q1/06-computation/results.json"
echo "题面给定 1234 万人，结果 4.5856" > "$D2/intermediates/12-writing/paper-sections/s.md"
out=$($PY "$SC/artifact_lint.py" --root "$D2" 2>&1)
echo "$out" | grep -q "paper.unsourced.*1234" && bad "题面给定常量仍被误报无源" || ok "题面给定常量不误报"

echo "== 6b. artifact_lint：非契约位置的同名 results.json 不能被当真源 =="
D3="$W/al3"; mkdir -p "$D3/intermediates/q1/02-data" "$D3/intermediates/q1/06-computation" "$D3/intermediates/q1/03-assumptions"
echo '{"junk":{"k":9.87654}}' > "$D3/intermediates/q1/02-data/results.json"
echo '{"results":{"a":{"keyValues":{"k":1.23456}}}}' > "$D3/intermediates/q1/06-computation/results.json"
out=$($PY "$SC/artifact_lint.py" --root "$D3" 2>&1)
if echo "$out" | grep -q "9.87654"; then bad "非契约位置的 results.json 被当真源"; else ok "真源只在契约位置"; fi

echo "== 7. figure_lint：单引号属性不能绕过 P0 判据 =="
cat > "$W/sq.svg" <<'EOF'
<svg viewBox="0 0 800 400" xmlns="http://www.w3.org/2000/svg"><rect x='13' y='7' width='130' height='50' fill='#ff00ff'/><line x1='13' y1='7' x2='137' y2='99' stroke='#ff00ff'/><text x='13' y='21' font-size='9'>x</text></svg>
EOF
out=$($PY "$SC/figure_lint.py" --svg "$W/sq.svg" 2>&1)
echo "$out" | grep -q "svg.color" && ok "单引号 fill/stroke 被检出（svg.color）" || bad "单引号属性绕过判据"

echo "== 8. figure_lint：非 UTF-8 文件要按文件问题报，不能崩栈 =="
printf '# -*- coding: gbk -*-\nplt.title("\xd4\xf6\xb3\xa4")\n' > "$W/gbk.py"
out=$($PY "$SC/figure_lint.py" --py "$W/gbk.py" 2>&1); rc=$?
if echo "$out" | grep -q "Traceback"; then bad "非 UTF-8 仍打印 traceback"; else ok "非 UTF-8 不崩栈（rc=$rc）"; fi

echo "== 9. figure_lint：--json 路径不可写时报告不能丢 =="
out=$($PY "$SC/figure_lint.py" --py "$W/gbk.py" --json /nonexistent-dir/x.json 2>/dev/null)
[ -n "$out" ] && ok "--json 失败仍输出 stdout 报告" || bad "--json 失败导致报告丢失"

echo "== 10. probe_cache：改 pool/ 内容后缓存必须失效 =="
D3="$W/pc"; mkdir -p "$D3/pool" "$D3/probes"
cp "$SC/primitives.py" "$D3/pool/primitives.py"
cat > "$D3/probes/p.py" <<'EOF'
import primitives as P, json
print(json.dumps({"ver": P.VERSION}))
EOF
( cd "$D3" && $PY "$SC/probe_cache.py" --run probes/p.py --inputs '{}' >/dev/null 2>&1 )
r1=$( cd "$D3" && $PY "$SC/probe_cache.py" --run probes/p.py --inputs '{}' 2>&1 >/dev/null | grep -c "命中缓存" )
printf '\n# 改池\n' >> "$D3/pool/primitives.py"
r2=$( cd "$D3" && $PY "$SC/probe_cache.py" --run probes/p.py --inputs '{}' 2>&1 >/dev/null | grep -c "命中缓存" )
if [ "$r1" -eq 1 ] && [ "$r2" -eq 0 ]; then ok "命中→改池后重算（未命中）"; else bad "改池后仍命中缓存（r1=$r1 r2=$r2）"; fi

echo "== 11. probe_cache：--run 结果要打到 stdout =="
out=$( cd "$D3" && $PY "$SC/probe_cache.py" --run probes/p.py --inputs '{}' 2>/dev/null )
echo "$out" | grep -q '"ver"' && ok "--run 输出 JSON 到 stdout" || bad "--run 未输出结果到 stdout"

echo "== 12. probe_cache：--clear 不能删 probes/manifest.json =="
( cd "$D3" && PROBE_CACHE_DIR="$D3/probes" $PY "$SC/probe_cache.py" --clear >/dev/null 2>&1 )
[ -f "$D3/probes/manifest.json" ] && ok "manifest 未被当缓存删除" || bad "--clear 删掉了 manifest"

echo "== 13. primitives：改内容未递增 VERSION 要持续报警 =="
D4="$W/pr"; mkdir -p "$D4"; cp "$SC/primitives.py" "$D4/primitives.py"
( cd "$D4" && $PY primitives.py --manifest m.json >/dev/null 2>&1 )
printf '\n# 偷偷改\n' >> "$D4/primitives.py"
( cd "$D4" && $PY primitives.py --manifest m.json >/dev/null 2>&1 ); e1=$?
( cd "$D4" && $PY primitives.py --manifest m.json >/dev/null 2>&1 ); e2=$?
sed -i 's/^VERSION = "2.0.0"/VERSION = "2.0.9"/' "$D4/primitives.py"
( cd "$D4" && $PY primitives.py --manifest m.json >/dev/null 2>&1 ); e3=$?
if [ $e1 -eq 1 ] && [ $e2 -eq 1 ] && [ $e3 -eq 0 ]; then ok "持续报警（1/1/0）"; else bad "版本守卫语义错（$e1/$e2/$e3）"; fi

echo "== 14. primitives：--manifest 目标目录不存在时自动创建 =="
( cd "$D4" && $PY primitives.py --manifest sub/dir/m.json >/dev/null 2>&1 )
[ $? -eq 0 ] && ok "自动 mkdir 并写出" || bad "目标目录不存在即失败"

echo "== 15. primitives：--selftest（含空点集边界） =="
$PY "$SC/primitives.py" --selftest | grep -q "通过" && ok "selftest 全绿" || bad "selftest 失败"

echo "== 16. probe_cache：--budget 预检拒绝（rc=3 + 缩窗建议） =="
D5="$W/pc2"; mkdir -p "$D5/probes"
cat > "$D5/probes/tiered.py" <<'EOF'
import json, os, sys
sys.path.insert(0, os.environ["PROBE_SC"])
import probe_cache as pc
key = pc.checkpoint_key(sys.argv[0], {"a": 1}, {}, "")
fresh = []
for t in ("n1", "n2"):
    v = pc.checkpoint_get(key, t)
    if v is None:
        v = {"tier": t}
        pc.checkpoint_put(key, t, v)
        fresh.append(t)
print(json.dumps({"fresh": fresh}))
EOF
out=$( cd "$D5" && PROBE_SC="$SC" $PY "$SC/probe_cache.py" --run probes/tiered.py --inputs '{"a":1}' --budget 10 --estimate 100 2>&1 ); rc=$?
if [ $rc -eq 3 ] && echo "$out" | grep -q "缩到"; then ok "超预算被拒绝（rc=3 + 缩窗比例建议）"; else bad "预算预检未生效（rc=$rc）：$out"; fi

echo "== 17. probe_cache：分档落盘 + 重跑跳过已完成档 =="
( cd "$D5" && PROBE_SC="$SC" $PY "$SC/probe_cache.py" --run probes/tiered.py --inputs '{"a":1}' --budget 60 >/dev/null 2>&1 )
n=$(find "$D5/probes/partial" -name '*.json' 2>/dev/null | wc -l)
rm -f "$D5"/probes/results/*.json
out2=$( cd "$D5" && PROBE_SC="$SC" $PY "$SC/probe_cache.py" --run probes/tiered.py --inputs '{"a":1}' --budget 60 2>/dev/null )
if [ "$n" -eq 2 ] && echo "$out2" | grep -q '"fresh": \[\]'; then ok "2 档落盘，删缓存重跑全部命中 checkpoint"; else bad "分档落盘/复用失效（n=$n, out2=$out2）"; fi

echo "== 18. probe_cache：超时被 kill 后已完成档保留并被提示 =="
cat > "$D5/probes/slow.py" <<'EOF'
import json, os, sys, time
sys.path.insert(0, os.environ["PROBE_SC"])
import probe_cache as pc
pc.checkpoint_put(pc.checkpoint_key(sys.argv[0], {"b": 1}, {}, ""), "n1", {"tier": "n1"})
time.sleep(30)
print(json.dumps({}))
EOF
out=$( cd "$D5" && PROBE_SC="$SC" $PY "$SC/probe_cache.py" --run probes/slow.py --inputs '{"b":1}' --timeout 2 2>&1 ); rc=$?
k=$(find "$D5/probes/partial" -name 'n1.json' 2>/dev/null | wc -l)
if [ $rc -eq 1 ] && [ "$k" -ge 1 ] && echo "$out" | grep -q "已完成档保留"; then ok "超时保留分档并提示（rc=1）"; else bad "超时不保留分档（rc=$rc, k=$k）：$out"; fi

echo "== 19. probe_cache：manifest 条目紧凑化（长 purpose 截断 + inputs 摘要） =="
D7="$W/pc3"; mkdir -p "$D7/probes"
cat > "$D7/probes/t.py" <<'EOF'
import json, os, sys
sys.path.insert(0, os.environ["PROBE_SC"])
import probe_cache as pc
pc.main_with_cache(lambda inputs: {"ok": 1}, purpose="用途" * 60,
                   inputs={"blob": ["y" * 50] * 40}, role="impl")
EOF
( cd "$D7" && PROBE_SC="$SC" $PY "$SC/probe_cache.py" --run probes/t.py --inputs '{"blob":1}' >/dev/null 2>&1 )
out=$(/usr/bin/python3 -c "
import json,sys
m=json.load(open('$D7/probes/manifest.json'))
e=list(m['probes'].values())[0]
print('purpose_len',len(e['purpose']),'ellipsis',e['purpose'].endswith('…'),'digest',bool(e['inputs'].get('_digest')))
")
if echo "$out" | grep -q "purpose_len 56 ellipsis True digest True"; then ok "purpose 截断到 56 字符（含省略号）、inputs 存摘要"; else bad "manifest 未紧凑化：$out"; fi

echo "== 20. artifact_lint：draft 台账章节（P0）+ boot 载荷超限（P1） =="
D8="$W/lint"; mkdir -p "$D8/intermediates/q1/04-formulation" "$D8/probes"
cat > "$D8/intermediates/q1/04-formulation/draft.md" <<'EOF'
# q1 方案
## 3. 主方案
正文
## 0.1 r3 轮评审逐条处置（历史归档）
…
## 9. 台账与机械核验指针
EOF
/usr/bin/python3 -c "print('x'*2000)" > "$D8/probes/manifest.json"
out=$($PY "$SC/artifact_lint.py" --root "$D8" 2>&1); rc=$?
hit=$(echo "$out" | grep -c "draft.ledger_section")
boot=$(echo "$out" | grep -c "boot.payload_limit")
if [ "$rc" -eq 1 ] && [ "$hit" -ge 1 ] && [ "$boot" -ge 1 ]; then ok "检出台账章节 P0 + boot 超长行 P1（rc=1）"; else bad "新检查未生效（rc=$rc hit=$hit boot=$boot）"; fi
if echo "$out" | grep -q "台账与机械核验指针"; then bad "纯指针节被误判为台账章节"; else ok "「…指针」节未被误判"; fi

echo "== 21. 归档条目算已登记 + manifest 一行一条目 =="
D9="$W/arch"; mkdir -p "$D9/probes/adversary"
printf 'print(1)\n' > "$D9/probes/adversary/old.py"
/usr/bin/python3 -c "
import json
json.dump({'schema':'v1','probes':{'k1':{'purpose':'old','script':'probes/adversary/old.py'}}}, open('$D9/probes/manifest.archive.json','w'))
json.dump({'schema':'v1','probes':{}}, open('$D9/probes/manifest.json','w'))
"
out=$($PY "$SC/artifact_lint.py" --root "$D9" 2>&1)
if echo "$out" | grep -q "probes.unregistered\|probes.ghost"; then bad "归档条目被误判为未登记/幽灵"; else ok "归档条目算已登记（无未登记/幽灵告警）"; fi
shape=$(/usr/bin/python3 -c "
import sys; sys.path.insert(0, '$SC')
import probe_cache as pc
man = {'schema':'v1','probes':{'k%03d' % i: {'purpose':'用途'*30,'inputs':{'a':i},'cacheKey':'k%03d' % i} for i in range(50)}}
s = pc.dump_manifest(man)
print('maxline', max(len(x) for x in s.split(chr(10))), 'lines', len(s.split(chr(10))))
")
if echo "$shape" | grep -qE "maxline [0-9]{1,4} " && [ "$(echo "$shape" | sed 's/maxline \([0-9]*\).*/\1/')" -lt 1500 ]; then ok "manifest 一行一条目（$shape）"; else bad "manifest 行长超限：$shape"; fi

echo "== 22. reuse_lint 第二判据：跨问同名同签名（默认只报不阻塞，--strict-samesig 才升级） =="
D10="$W/samesig"; mkdir -p "$D10/intermediates/q1/05-implementation/code" "$D10/intermediates/q2/05-implementation/code"
cat > "$D10/intermediates/q1/05-implementation/code/a.py" <<'EOF'
def shared_metric(x, y):
    a = x + 1
    b = a * 2
    return b
def main(z):
    a = z + 1
    b = a * 2
    return b
EOF
cat > "$D10/intermediates/q2/05-implementation/code/b.py" <<'EOF'
def shared_metric(x, y):
    a = x + 1
    b = a * 2
    if b > 0:
        b = b - 0
    return b
def main(z):
    a = z + 1
    b = a * 2
    if b > 0:
        b = b - 0
    return b
EOF
out=$($PY "$SC/reuse_lint.py" --scan --root "$D10" 2>&1); rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -q "跨问同名同签名候选 1 组"; then ok "默认报出 1 组跨问候选且 rc=0"; else bad "默认行为不符（rc=$rc）：$(echo "$out" | head -3)"; fi
if echo "$out" | grep -qE "\[S1\].*shared_metric"; then ok "候选区列出 shared_metric"; else bad "候选区未列出 shared_metric"; fi
if echo "$out" | grep -qE "^\[S[0-9]+\].*main"; then bad "通用名 main 被误报"; else ok "通用名 main 未误报"; fi
$PY "$SC/reuse_lint.py" --scan --root "$D10" --strict >/dev/null 2>&1; rc1=$?
$PY "$SC/reuse_lint.py" --scan --root "$D10" --strict-samesig >/dev/null 2>&1; rc2=$?
if [ $rc1 -eq 0 ] && [ $rc2 -eq 1 ]; then ok "--strict 不受新判据影响（rc=0）、--strict-samesig 升级为 1"; else bad "门语义不符（strict=$rc1 samesig=$rc2）"; fi
if $PY "$SC/reuse_lint.py" --selftest >/dev/null 2>&1; then ok "内置 --selftest 反例自检全绿"; else bad "--selftest 未通过"; fi

echo
echo "结果：通过 $PASS ／ 失败 $FAIL"
[ $FAIL -eq 0 ] || exit 1
