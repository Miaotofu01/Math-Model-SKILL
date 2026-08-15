#!/usr/bin/env bash
# math-model 一键安装
# 用法:
#   bash install.sh            # 默认: DSH 符号链接安装
#   bash install.sh --dsh      # DSH 符号链接安装（推荐，享受热更新）
#   bash install.sh --claude   # Claude Code 安装（拷贝）
#   bash install.sh --both     # 两平台都装
set -e

PLUGIN_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_SRC="${PLUGIN_DIR}/skills/math-model"

echo "==> math-model v2.4.0 安装脚本"

# ═══ 参数解析 ═══
INSTALL_DSH=0
INSTALL_CLAUDE=0
for arg in "$@"; do
  case "$arg" in
    --dsh) INSTALL_DSH=1 ;;
    --claude) INSTALL_CLAUDE=1 ;;
    --both) INSTALL_DSH=1; INSTALL_CLAUDE=1 ;;
    *) echo "未知参数: $arg（支持 --dsh / --claude / --both）"; exit 1 ;;
  esac
done
if [[ $INSTALL_DSH -eq 0 && $INSTALL_CLAUDE -eq 0 ]]; then
  INSTALL_DSH=1
fi

# ═══ 环境检查（可跳过功能，不影响安装）═══
echo ""
echo "── 环境检查 ──"
if [[ -f "${PLUGIN_DIR}/env-check.sh" ]]; then
  bash "${PLUGIN_DIR}/env-check.sh" || true
else
  echo "  （未找到 env-check.sh，跳过）"
fi

# ═══ DSH 安装：符号链接（单一事实源，改仓库即热更新）═══
if [[ $INSTALL_DSH -eq 1 ]]; then
  echo ""
  echo "── 安装到 DeepSeek Harness（~/.dsh/skills）──"
  mkdir -p "${HOME}/.dsh/skills"
  if [[ -e "${HOME}/.dsh/skills/math-model" && ! -L "${HOME}/.dsh/skills/math-model" ]]; then
    echo "  ⚠️ 检测到旧实体目录，移动到备份: ~/.dsh/skills/math-model.bak.$(date +%s)"
    mv "${HOME}/.dsh/skills/math-model" "${HOME}/.dsh/skills/math-model.bak.$(date +%s)"
  fi
  ln -sfn "${SKILL_SRC}" "${HOME}/.dsh/skills/math-model"
  echo "  ✓ ~/.dsh/skills/math-model -> ${SKILL_SRC}（热更新生效）"
fi

# ═══ Claude Code 安装：技能用拷贝（SKILL.md 需用 Claude 版），workflow 用符号链接 ═══
if [[ $INSTALL_CLAUDE -eq 1 ]]; then
  echo ""
  echo "── 安装到 Claude Code（~/.claude）──"
  # skill 目录：prompts/templates 链接，SKILL.md 用 Claude 版拷贝
  mkdir -p "${HOME}/.claude/skills/math-model"
  for d in prompts templates workflows; do
    ln -sfn "${SKILL_SRC}/${d}" "${HOME}/.claude/skills/math-model/${d}"
  done
  if [[ -f "${SKILL_SRC}/SKILL.claude.md" ]]; then
    cp "${SKILL_SRC}/SKILL.claude.md" "${HOME}/.claude/skills/math-model/SKILL.md"
    echo "  ✓ ~/.claude/skills/math-model/SKILL.md（Claude 版）"
  fi
  # workflow 脚本（带 export const meta，Claude 版 Workflow scriptPath 直接可用）
  mkdir -p "${HOME}/.claude/workflows"
  ln -sfn "${SKILL_SRC}/workflows/math-model.js" "${HOME}/.claude/workflows/math-model.js"
  echo "  ✓ ~/.claude/workflows/math-model.js -> 仓库（Claude 版）"
fi

echo ""
echo "安装完成！DSH 里输入 /math-model 即可使用。"
echo "卸载：rm ~/.dsh/skills/math-model 或 rm -rf ~/.claude/skills/math-model ~/.claude/workflows/math-model.js"
