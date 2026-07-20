#!/usr/bin/env bash
set -e

PLUGIN_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="${HOME}/.claude/skills"
WORKFLOWS_DIR="${HOME}/.claude/workflows"

echo "==> 安装 math-model v2.2.0"

# ═══ System dependency checks ═══
echo ""
echo "── 环境检查 ──"

MISSING=()

check_cmd() {
    if command -v "$1" &>/dev/null; then
        echo "  ✓ $1"
        return 0
    else
        echo "  ✗ $1"
        return 1
    fi
}

# --- pdftotext ---
if check_cmd pdftotext; then
    :
else
    MISSING+=("pdftotext")
    echo "    ├─ 用途：从 PDF 提取题目文字"
    echo "    ├─ 缺失影响：无法用 /math-model ~/题.pdf，需手动粘贴题目"
    echo "    └─ 安装：sudo apt install poppler-utils"
fi

# --- xelatex ---
if check_cmd xelatex; then
    :
else
    MISSING+=("xelatex")
    echo "    ├─ 用途：standard/thorough 模式编译 LaTeX 论文为 PDF"
    echo "    ├─ 缺失影响：只能产出 Markdown（quick 模式不受影响）"
    echo "    └─ 安装：sudo apt install texlive-xetex texlive-lang-chinese（约 500MB）"
fi

# --- python3 ---
if check_cmd python3; then
    :
else
    MISSING+=("python3")
    echo "    ├─ 用途：Phase 5 求解阶段运行建模代码"
    echo "    ├─ 缺失影响：无法执行求解，只能产出算法方案"
    echo "    └─ 安装：sudo apt install python3 python3-pip"
fi

# --- Python libs ---
if python3 -c "import numpy, scipy, pandas, matplotlib, openpyxl" 2>/dev/null; then
    echo "  ✓ numpy/scipy/pandas/matplotlib/openpyxl"
else
    MISSING+=("python-libs")
    echo "  ✗ numpy/scipy/pandas/matplotlib/openpyxl"
    echo "    ├─ 用途：数值计算、数据处理、图表生成、附件读取"
    echo "    ├─ 缺失影响：求解代码无法运行（quick 模式可跳过求解）"
    echo "    └─ 安装：pip3 install numpy scipy pandas matplotlib openpyxl"
fi

# --- Summary ---
if [[ ${#MISSING[@]} -gt 0 ]]; then
    echo ""
    echo "── 依赖汇总 ──"
    echo "  以下 ${#MISSING[@]} 项缺失：${MISSING[*]}"
    echo ""
    echo "  是否需要安装？复制上面的安装命令逐条执行即可。"
    echo "  不装也不影响插件安装——对应功能会在运行时降级。"
else
    echo ""
    echo "  ✓ 所有依赖就绪"
fi

# ═══ Install plugin files ═══
echo ""
echo "── 安装插件文件 ──"
mkdir -p "${SKILLS_DIR}/math-model" "${WORKFLOWS_DIR}"
cp "${PLUGIN_DIR}/skills/math-model/SKILL.md" "${SKILLS_DIR}/math-model/SKILL.md"
echo "  ✓ skill → ${SKILLS_DIR}/math-model/SKILL.md"
# 安装整个 workflows/ 目录（主脚本 + lib/ 模块）
rm -f "${WORKFLOWS_DIR}/math-model.js"          # 移除旧版单文件
rm -rf "${WORKFLOWS_DIR}/lib"                     # 移除旧版 lib（如有）
cp -r "${PLUGIN_DIR}/workflows/." "${WORKFLOWS_DIR}/"
echo "  ✓ workflow → ${WORKFLOWS_DIR}/math-model.js + lib/ ($(wc -l < ${WORKFLOWS_DIR}/math-model.js) 行主脚本, $(find ${WORKFLOWS_DIR}/lib -name '*.js' | wc -l) 个模块)"
# 安装 env-check.sh
cp "${PLUGIN_DIR}/env-check.sh" "${SKILLS_DIR}/math-model/env-check.sh"
chmod +x "${SKILLS_DIR}/math-model/env-check.sh"
echo "  ✓ env-check.sh → ${SKILLS_DIR}/math-model/env-check.sh"

# ═══ Auto-run env check ═══
echo ""
echo "── 运行环境检测 ──"
bash "${SKILLS_DIR}/math-model/env-check.sh"

echo ""
echo ""
echo "安装完成！/math-model 已就绪。"
echo "卸载：rm -rf ${SKILLS_DIR}/math-model ${WORKFLOWS_DIR}/math-model.js ${WORKFLOWS_DIR}/lib"
