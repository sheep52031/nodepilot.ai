#!/usr/bin/env bash
set -euo pipefail

# 用法: ./pickup_handoff.sh <TICKET_JSON_PATH>
# 範例: ./pickup_handoff.sh .handoff/EXT/20250819-1430_api_ext_001.json

TICKET_JSON="${1:?path to handoff ticket .json file}"

# 檢查檔案是否存在
if [ ! -f "$TICKET_JSON" ]; then
    echo "❌ Error: Ticket file not found: $TICKET_JSON"
    exit 1
fi

# 檢查是否已被認領
if [[ "$TICKET_JSON" == *.claimed.json ]]; then
    echo "⚠️  此交接單已被認領: $TICKET_JSON"
    exit 1
fi

if [[ "$TICKET_JSON" == *.done.json ]]; then
    echo "✅ 此交接單已完成: $TICKET_JSON"
    exit 1
fi

# 檢查 JSON 格式
if ! jq . "$TICKET_JSON" >/dev/null 2>&1; then
    echo "❌ Error: Invalid JSON format in $TICKET_JSON"
    exit 1
fi

echo "📥 正在認領交接單: $TICKET_JSON"

# 提取基本資訊
HANDOFF_ID="$(jq -r '.handoff_id // ""' "$TICKET_JSON")"
FROM_ROLE="$(jq -r '.from // ""' "$TICKET_JSON")"
TO_ROLE="$(jq -r '.to // ""' "$TICKET_JSON")"
INTENT="$(jq -r '.intent // ""' "$TICKET_JSON")"
PRIORITY="$(jq -r '.priority // "medium"' "$TICKET_JSON")"

echo ""
echo "📋 交接單詳情:"
echo "   ID: $HANDOFF_ID"
echo "   來源: $FROM_ROLE → 目標: $TO_ROLE" 
echo "   任務: $INTENT"
echo "   優先級: $PRIORITY"
echo ""

# 建立 .claimed.json 檔案
CLAIMED_FILE="$(echo "$TICKET_JSON" | sed 's/\.json$/.claimed.json/')"

# 更新 JSON 內容，加入認領資訊
jq '. + {
    "status": "claimed",
    "claimed_by": "Claude-Code-Agent",
    "claimed_at": now | strftime("%Y-%m-%d %H:%M:%S")
}' "$TICKET_JSON" > "$CLAIMED_FILE"

# 移除原始 pending 檔案
rm "$TICKET_JSON"

# 提交認領狀態
git add "$CLAIMED_FILE" "$TICKET_JSON" 2>/dev/null || git add "$CLAIMED_FILE"
git commit -m "[handoff] claimed: $HANDOFF_ID by Claude" || {
    echo "⚠️  Warning: Failed to commit claim status, continuing anyway..."
}

echo "✅ 交接單已成功認領: $CLAIMED_FILE"
echo ""

# 顯示任務相關檔案和資源
echo "📁 相關資源:"
jq -r '.inputs | to_entries[] | "   \(.key): \(.value)"' "$CLAIMED_FILE" 2>/dev/null || echo "   (無額外輸入資源)"

echo ""
echo "🎯 驗收標準:"
jq -r '.acceptance[]? | "   ✓ \(.)"' "$CLAIMED_FILE" 2>/dev/null || echo "   (無明確驗收標準)"

echo ""
echo "🔗 相關連結:"
jq -r '.links[]? | "   📎 \(.)"' "$CLAIMED_FILE" 2>/dev/null || echo "   (無相關連結)"

echo ""
echo "⏰ 提醒: 任務完成後請使用以下指令標記完成:"
DONE_FILE="$(echo "$CLAIMED_FILE" | sed 's/\.claimed\.json$/.done.json/')"
echo "   echo '{\"status\":\"completed\",\"completed_at\":\"$(date)\"}' | jq '. + input' $CLAIMED_FILE > $DONE_FILE"

echo ""
echo "🚀 開始執行任務: $INTENT"