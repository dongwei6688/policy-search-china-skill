#!/bin/bash
#
# publish-hermes-skill 推前检查钩子
# 在 git push 时自动验证发布流程完整性
#
# 检查项:
#   □ 提交信息遵循 Conventional Commits 格式
#   □ CHANGELOG.md 包含当前版本的条目
#   □ SKILL.md 版本号与 CHANGELOG 一致
#   □ 当前版本已打 Tag（首次发版除外）

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'
PASS=0
FAIL=0
ERRORS=()

check() {
    local desc="$1"
    local result="$2"
    if [ "$result" = "ok" ]; then
        echo -e "  ${GREEN}✅${NC} $desc"
        PASS=$((PASS+1))
    else
        echo -e "  ${RED}❌${NC} $desc"
        FAIL=$((FAIL+1))
        ERRORS+=("$desc: $result")
    fi
}

warn() {
    local desc="$1"
    local msg="$2"
    echo -e "  ${YELLOW}⚠️${NC} $desc — $msg"
}

echo ""
echo "═══════════════════════════════════════"
echo "  publish-hermes-skill: 推前检查"
echo "═══════════════════════════════════════"

# 切换到仓库根目录
cd "$(git rev-parse --show-toplevel)" || exit 1

# ── 检查 1: 提交信息格式 ──
COMMIT_MSG=$(git log -1 --pretty=%B)
if echo "$COMMIT_MSG" | grep -qE '^(feat|fix|docs|chore|refactor)(\(.+\))?!?:'; then
    check "提交信息格式 (Conventional Commits)" "ok"
else
    warn "提交信息格式" "不是标准的 Conventional Commits 格式，建议: feat/fix/docs/chore/refactor"
    # 不强制拦截，仅警告
fi

# ── 检查 2: SKILL.md 有版本号 ──
SKILL_VER=$(grep '^version:' SKILL.md 2>/dev/null | grep -oP '\d+\.\d+\.\d+')
if [ -n "$SKILL_VER" ]; then
    check "SKILL.md 版本号 (v$SKILL_VER)" "ok"
else
    check "SKILL.md 版本号" "未找到版本号字段"
fi

# ── 检查 3: CHANGELOG.md 包含当前版本 ──
if [ -n "$SKILL_VER" ]; then
    if grep -q "## v$SKILL_VER" CHANGELOG.md 2>/dev/null; then
        check "CHANGELOG.md 已更新 (v$SKILL_VER)" "ok"
    else
        check "CHANGELOG.md 已更新" "未找到 v$SKILL_VER 的条目"
    fi
fi

# ── 检查 4: 版本号与 Tag 一致 ──
if [ -n "$SKILL_VER" ]; then
    if git tag -l "v$SKILL_VER" | grep -q .; then
        check "Git Tag (v$SKILL_VER)" "ok"
    else
        warn "Git Tag" "版本 v$SKILL_VER 尚未打 Tag，建议创建"
    fi
fi

# ── 检查 5: 无开发工具混入 ──
STAGED=$(git diff --cached --name-only 2>/dev/null)
echo "$STAGED" | grep -qE 'dev-tools/|\.env' && {
    check "无开发工具/私密文件混入" "发现包含 dev-tools/ 或 .env 文件"
} || {
    check "无开发工具/私密文件混入" "ok"
}

echo ""
echo "───────────────────────────────────────"
if [ $FAIL -gt 0 ]; then
    echo -e "  ${RED}✗ 检查未通过: $FAIL 项失败, $PASS 项通过${NC}"
    for e in "${ERRORS[@]}"; do
        echo "    - $e"
    done
    echo ""
    echo "  请按 publish-hermes-skill 流程补充后重试:"
    echo "  版本号 → Changelog → tag → push"
    echo "───────────────────────────────────────"
    exit 1
else
    echo -e "  ${GREEN}✓ 全部通过 ($PASS 项)${NC}"
    echo "───────────────────────────────────────"
    exit 0
fi
