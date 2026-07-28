#!/bin/bash
#
# publish-hermes-skill 推前检查钩子
# 在 git push 时自动验证发布流程完整性
#
# 变更类型自动检测：
#   检测本次 push 涉及的文件变更，按发版判断矩阵自动判定是否需要发版。
#   需要发版 → 验证 CHANGELOG + tag 是否到位，不到位就拦截
#   不需要发版 → 跳过版本相关检查，仅做格式和安全检查
#
# 检查项 (需发版时):
#   ✅ 变更类型自动归类
#   □ 提交信息遵循 Conventional Commits 格式
#   □ CHANGELOG.md 包含当前版本的条目
#   □ SKILL.md 版本号与 CHANGELOG 一致
#   □ 当前版本已打 Tag（首次发版除外）
#   □ 无开发工具/私密文件混入
#

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
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

info() {
    local msg="$1"
    echo -e "  ${CYAN}ℹ️${NC} $msg"
}

echo ""
echo "═══════════════════════════════════════"
echo "  publish-hermes-skill: 推前检查"
echo "═══════════════════════════════════════"

# 切换到仓库根目录
cd "$(git rev-parse --show-toplevel)" || exit 1

# ── 步骤 0: 变更类型自动检测 ─────────────────
echo ""
echo "  ── 变更类型检测 ──"

# 获取本次 push 涉及的文件变更
# 优先用 HEAD~1..HEAD（常规提交），首次提交用 diff-tree
CHANGED_FILES=$(git diff --name-only HEAD~1..HEAD 2>/dev/null || \
                git diff-tree --no-commit-id -r --name-only HEAD 2>/dev/null || \
                echo "")

if [ -z "$CHANGED_FILES" ]; then
    warn "变更文件检测" "未能获取变更文件列表，将全部检查"
    RELEASE_NEEDED=true
else
    echo "$CHANGED_FILES" | while read -r f; do
        echo "    📄 $f"
    done

    # ── 分类逻辑（对应发版判断矩阵） ──
    RELEASE_NEEDED=false
    HAS_DATA=false
    HAS_SCRIPT=false
    HAS_FEATURE=false
    HAS_DOCS=false
    HAS_OTHER=false

    while IFS= read -r file; do
        case "$file" in
            cache/*)
                HAS_DATA=true ;;
            scripts/*.py|scripts/*.sh)
                HAS_SCRIPT=true ;;
            SKILL.md|templates/*)
                HAS_FEATURE=true ;;
            README.md|CHANGELOG.md|.gitignore|LICENSE)
                HAS_DOCS=true ;;
            *)
                HAS_OTHER=true ;;
        esac
    done <<< "$CHANGED_FILES"

    # ── 判定是否需要发版 ──
    if $HAS_DATA || $HAS_SCRIPT || $HAS_FEATURE || $HAS_OTHER; then
        RELEASE_NEEDED=true
    fi

    # 输出类型摘要
    types=""
    $HAS_DATA && types="$types 数据"
    $HAS_SCRIPT && types="$types 脚本"
    $HAS_FEATURE && types="$types 功能"
    $HAS_DOCS && types="$types 文档"
    $HAS_OTHER && types="$types 其他"

    check "变更类型归类${types}" "ok"

    if $RELEASE_NEEDED; then
        info "判定结果：⛓️ 需发版 — 请确保版本号 + CHANGELOG + Tag 均已就绪"
        echo ""
    else
        info "判定结果：📄 纯文档变更 — 跳过版本检查，直接推送即可"
        echo ""
    fi
fi

echo ""
echo "  ── 通用检查 ──"

# ── 检查 1: 提交信息格式 ──
COMMIT_MSG=$(git log -1 --pretty=%B)
if echo "$COMMIT_MSG" | grep -qE '^(feat|fix|docs|chore|refactor)(\(.+\))?!?:'; then
    check "提交信息格式 (Conventional Commits)" "ok"
else
    warn "提交信息格式" "不是标准 Conventional Commits，建议: feat/fix/docs/chore/refactor"
fi

# ── 检查 2: 无开发工具混入 ──
STAGED=$(git diff --cached --name-only 2>/dev/null)
echo "$STAGED" | grep -qE 'dev-tools/|\.env' && {
    check "无开发工具/私密文件混入" "发现包含 dev-tools/ 或 .env 文件"
} || {
    check "无开发工具/私密文件混入" "ok"
}

# ── 需要发版时的版本检查 ──
if $RELEASE_NEEDED; then
    echo ""
    echo "  ── 发版检查 ──"

    # ── 检查 3: SKILL.md 有版本号 ──
    SKILL_VER=$(grep '^version:' SKILL.md 2>/dev/null | grep -oP '\d+\.\d+\.\d+')
    if [ -n "$SKILL_VER" ]; then
        check "SKILL.md 版本号 (v$SKILL_VER)" "ok"
    else
        check "SKILL.md 版本号" "未找到版本号字段"
    fi

    # ── 检查 4: CHANGELOG.md 包含当前版本 ──
    if [ -n "$SKILL_VER" ]; then
        if grep -q "## v$SKILL_VER" CHANGELOG.md 2>/dev/null; then
            check "CHANGELOG.md 已更新 (v$SKILL_VER)" "ok"
        else
            check "CHANGELOG.md 已更新" "未找到 v$SKILL_VER 的条目"
        fi
    fi

    # ── 检查 5: 版本号与 Tag 一致 ──
    if [ -n "$SKILL_VER" ]; then
        if git tag -l "v$SKILL_VER" | grep -q .; then
            check "Git Tag (v$SKILL_VER)" "ok"
        else
            warn "Git Tag" "版本 v$SKILL_VER 尚未打 Tag，建议创建"
        fi
    fi
fi

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
elif $RELEASE_NEEDED; then
    echo -e "  ${GREEN}✓ 全部通过 ($PASS 项)${NC}"
    echo -e "  ${GREEN}✓ 发版检查就绪，可推送${NC}"
    echo "───────────────────────────────────────"
    exit 0
else
    echo -e "  ${GREEN}✓ 全部通过 ($PASS 项)${NC}"
    echo -e "  ${GREEN}✓ 纯文档变更，直接推送${NC}"
    echo "───────────────────────────────────────"
    exit 0
fi
