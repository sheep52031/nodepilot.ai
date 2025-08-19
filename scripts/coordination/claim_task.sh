#!/bin/bash

# 認領任務腳本
set -e

if [ $# -ne 1 ]; then
    echo "用法: $0 <task_id>"
    echo "範例: $0 9.1"
    exit 1
fi

TASK_ID=$1
TERMINAL_ROLE=$(head -1 CLAUDE.md 2>/dev/null | grep -o 'AI-CORE\|API\|EXT' || echo "UNKNOWN")
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

if [ "$TERMINAL_ROLE" = "UNKNOWN" ]; then
    echo "❌ 無法識別 Terminal 角色，請確認 CLAUDE.md 檔案"
    exit 1
fi

# 確保協調目錄存在
mkdir -p .coordination
if [ ! -f ".coordination/active_tasks.json" ]; then
    echo '{"lastUpdated": "'$TIMESTAMP'", "tasks": []}' > .coordination/active_tasks.json
fi

# 檢查任務是否已被其他人認領
CURRENT_ASSIGNEE=$(jq -r ".tasks[] | select(.taskId == \"$TASK_ID\") | .assignedTo" .coordination/active_tasks.json 2>/dev/null)

if [ "$CURRENT_ASSIGNEE" != "null" ] && [ "$CURRENT_ASSIGNEE" != "" ] && [ "$CURRENT_ASSIGNEE" != "$TERMINAL_ROLE" ]; then
    echo "❌ 任務 $TASK_ID 已被 $CURRENT_ASSIGNEE 認領"
    echo "請選擇其他任務或等待該任務完成"
    exit 1
fi

# 從 tasks.md 中獲取任務資訊
if [ ! -f "spec_docs/tasks.md" ]; then
    echo "❌ 找不到 spec_docs/tasks.md 檔案"
    exit 1
fi

TASK_INFO=$(grep -A 10 "^- \[ \] $TASK_ID\." spec_docs/tasks.md | head -1)
TASK_TITLE=$(echo "$TASK_INFO" | sed "s/^- \[ \] $TASK_ID\. //" | sed 's/（.*）.*//' | sed 's/**.*$//')

if [ -z "$TASK_TITLE" ]; then
    echo "❌ 在 tasks.md 中找不到任務 $TASK_ID"
    exit 1
fi

# 檢查任務角色是否匹配
TASK_ROLE=$(echo "$TASK_INFO" | grep -o '【[^】]*】' | sed 's/【\|】//g' | head -1)
if [ ! -z "$TASK_ROLE" ] && [[ "$TASK_ROLE" != *"$TERMINAL_ROLE"* ]]; then
    echo "⚠️  警告：任務 $TASK_ID 指定給 $TASK_ROLE，但你是 $TERMINAL_ROLE"
    read -p "確定要認領嗎？ (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "任務認領已取消"
        exit 0
    fi
fi

# 更新任務狀態
TEMP_FILE=$(mktemp)
jq --arg task_id "$TASK_ID" \
   --arg title "$TASK_TITLE" \
   --arg role "$TERMINAL_ROLE" \
   --arg timestamp "$TIMESTAMP" \
   '
   .lastUpdated = $timestamp |
   .tasks = (.tasks | map(
     if .taskId == $task_id then
       . + {
         "title": $title,
         "assignedTo": $role,
         "status": "in_progress", 
         "startedAt": $timestamp
       }
     else . end
   )) |
   if (.tasks | map(.taskId) | index($task_id)) == null then
     .tasks += [{
       "taskId": $task_id,
       "title": $title,
       "assignedTo": $role,
       "status": "in_progress",
       "startedAt": $timestamp
     }]
   else . end
   ' .coordination/active_tasks.json > "$TEMP_FILE"

mv "$TEMP_FILE" .coordination/active_tasks.json

echo "✅ 成功認領任務 $TASK_ID: $TASK_TITLE"
echo "👤 認領者: $TERMINAL_ROLE"
echo "⏰ 開始時間: $TIMESTAMP"

# 提交狀態變更
if git diff --quiet .coordination/active_tasks.json; then
    echo "📝 任務狀態無變更"
else
    git add .coordination/active_tasks.json
    git commit -m "[coordination] $TERMINAL_ROLE 認領任務 $TASK_ID

任務: $TASK_TITLE
認領者: $TERMINAL_ROLE  
開始時間: $TIMESTAMP"
    
    echo "🔄 正在同步到遠端..."
    git push origin $(git branch --show-current) || echo "⚠️  推送失敗，請手動同步"
fi

echo ""
echo "📋 執行 './scripts/coordination/status.sh' 查看整體狀態"