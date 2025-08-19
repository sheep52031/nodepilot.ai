#!/bin/bash

# 多 Terminal 狀態查看腳本
set -e

echo "=== 多 Claude Code Terminal 協作狀態 ==="
echo "時間: $(date)"
echo ""

# 檢查協調目錄是否存在
if [ ! -d ".coordination" ]; then
    echo "⚠️  協調目錄不存在，正在初始化..."
    mkdir -p .coordination
    echo '{"lastUpdated": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'", "tasks": []}' > .coordination/active_tasks.json
fi

# 顯示活躍任務
echo "📋 當前活躍任務:"
if [ -f ".coordination/active_tasks.json" ]; then
    jq -r '.tasks[] | select(.status == "in_progress") | "  \(.assignedTo): 正在執行 \(.taskId) - \(.title)"' .coordination/active_tasks.json
    
    PENDING_COUNT=$(jq '[.tasks[] | select(.status == "pending")] | length' .coordination/active_tasks.json 2>/dev/null || echo 0)
    if [ "$PENDING_COUNT" -gt 0 ]; then
        echo ""
        echo "⏳ 待處理任務 ($PENDING_COUNT 個):"
        jq -r '.tasks[] | select(.status == "pending") | "  \(.taskId): \(.title) (等待: \(.dependencies // [] | join(", ")))"' .coordination/active_tasks.json
    fi
else
    echo "  (無活躍任務)"
fi

echo ""

# 檢查各 Terminal 最近活動
echo "🔄 Terminal 最近活動:"

# 檢查各 worktree 的狀態
WORKTREES=("feature-extension:EXT" "feature-api:API" "feature-ai-core:AI-CORE")

for worktree_info in "${WORKTREES[@]}"; do
    IFS=':' read -r worktree_name terminal_role <<< "$worktree_info"
    worktree_path="../nodepilot-worktrees/$worktree_name"
    
    if [ -d "$worktree_path" ]; then
        if [ -f "$worktree_path/.coordination/last_activity.json" ]; then
            LAST_ACTIVITY=$(cat "$worktree_path/.coordination/last_activity.json" 2>/dev/null || echo '{}')
            TIMESTAMP=$(echo "$LAST_ACTIVITY" | jq -r '.timestamp // "未知"')
            COMMIT=$(echo "$LAST_ACTIVITY" | jq -r '.lastCommit[:8] // "未知"')
            echo "  $terminal_role: 最近活動 $TIMESTAMP (commit: $COMMIT)"
        else
            echo "  $terminal_role: 無活動記錄"
        fi
    else
        echo "  $terminal_role: worktree 不存在 ($worktree_path)"
    fi
done

echo ""

# Git 同步狀態
echo "🔗 Git 同步狀態:"
git fetch origin --quiet 2>/dev/null || true

CURRENT_BRANCH=$(git branch --show-current)
BEHIND_COUNT=$(git rev-list --count HEAD..origin/$CURRENT_BRANCH 2>/dev/null || echo "?")
AHEAD_COUNT=$(git rev-list --count origin/$CURRENT_BRANCH..HEAD 2>/dev/null || echo "?")

echo "  當前分支: $CURRENT_BRANCH"
echo "  落後 origin: $BEHIND_COUNT commits"  
echo "  領先 origin: $AHEAD_COUNT commits"

# 檢查是否有未提交的變更
UNTRACKED=$(git status --porcelain | wc -l | xargs)
if [ "$UNTRACKED" -gt 0 ]; then
    echo "  ⚠️  有 $UNTRACKED 個未提交的變更"
fi

echo ""
echo "✅ 狀態檢查完成"