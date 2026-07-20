#!/bin/bash
# math-model 环境检测脚本
# 用法: bash env-check.sh

ERRORS=0
WARNINGS=0

check_cmd() {
    if command -v "$1" &>/dev/null; then
        echo "  ✅ $1: $(command -v $1)"
    else
        echo "  ❌ $1: 未安装"
        ((ERRORS++))
    fi
}

check_python_pkg() {
    if python3 -c "import $1" 2>/dev/null; then
        echo "  ✅ python3 $1: $(python3 -c "import $1; print($1.__version__)" 2>/dev/null || echo '已安装')"
    else
        echo "  ⚠️  python3 $1: 未安装 (pip install $1)"
        ((WARNINGS++))
    fi
}

echo "=== math-model 环境检测 ==="
echo ""

echo "--- 必需工具 ---"
check_cmd pdftotext   # 或用 fallback
check_cmd python3
check_cmd xelatex

echo ""
echo "--- Python 包 ---"
check_python_pkg pandas
check_python_pkg numpy
check_python_pkg sklearn
check_python_pkg scipy
check_python_pkg matplotlib
check_python_pkg statsmodels

echo ""
echo "--- 中文字体（国赛必须）---"
if fc-list :lang=zh 2>/dev/null | grep -q .; then
    echo "  ✅ 中文字体已安装"
else
    echo "  ⚠️  未检测到中文字体 — 国赛请安装: sudo apt install fonts-noto-cjk"
    ((WARNINGS++))
fi

echo ""
echo "--- 可选工具 ---"
check_cmd pandoc

echo ""
echo "=== 结果: $ERRORS 个错误, $WARNINGS 个警告 ==="
if [ $ERRORS -gt 0 ]; then
    echo "请先安装缺失的必需工具再运行 math-model。"
fi
