#!/usr/bin/env bash
set -euo pipefail

# 用法: ./emit_handoff.sh <TARGET_ROLE> <TICKET_JSON_PATH>
# 範例: ./emit_handoff.sh EXT .handoff/EXT/20250819-1430_api_ext_001.json

ROLE="${1:?target role e.g. EXT, API, AI-CORE}"
TICKET_JSON="${2:?path to .handoff/<ROLE>/<id>.json}"

# 檢查檔案是否存在
if [ ! -f "$TICKET_JSON" ]; then
    echo "❌ Error: Ticket file not found: $TICKET_JSON"
    exit 1
fi

# 檢查 JSON 格式有效性
if ! jq . "$TICKET_JSON" >/dev/null 2>&1; then
    echo "❌ Error: Invalid JSON format in $TICKET_JSON"
    exit 1
fi

# 可選：同名 .md 說明檔案也一起提交
MD_FILE="$(echo "$TICKET_JSON" | sed 's/\.json$/.md/')"

echo "📤 準備提交交接單: $TICKET_JSON"

# 加入 Git 暫存
git add "$TICKET_JSON" 2>/dev/null || {
    echo "❌ Error: Failed to add $TICKET_JSON to git"
    exit 1
}

# 如果有 .md 說明檔，也一起加入
if [ -f "$MD_FILE" ]; then
    git add "$MD_FILE"
    echo "📝 同時提交說明檔: $MD_FILE"
fi

# 從 JSON 提取 intent 作為提交訊息
INTENT="$(jq -r '.intent // ""' "$TICKET_JSON" | head -c 80)"
HANDOFF_ID="$(jq -r '.handoff_id // ""' "$TICKET_JSON")"

# 構建提交訊息
if [ -n "$INTENT" ]; then
    COMMIT_MSG="[handoff] to $ROLE: $INTENT"
else
    COMMIT_MSG="[handoff] to $ROLE: $HANDOFF_ID"
fi

# 提交並推送
git commit -m "$COMMIT_MSG" || {
    echo "❌ Error: Failed to commit handoff ticket"
    exit 1
}

git push -u origin HEAD || {
    echo "❌ Error: Failed to push handoff ticket"
    exit 1
}

echo "✅ 交接單已成功推送: $TICKET_JSON"
echo "🎯 目標角色: $ROLE"
echo "📋 任務內容: $INTENT"
echo ""
echo "🔔 通知 $ROLE Terminal: 請執行 'git pull' 並使用 '/pickup $TICKET_JSON'"