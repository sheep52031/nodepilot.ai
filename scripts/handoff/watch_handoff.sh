#!/usr/bin/env bash
set -euo pipefail

# 用法: ./watch_handoff.sh [ROLE]
# 範例: ./watch_handoff.sh EXT

ROLE="${1:-EXT}"
DIR=".handoff/$ROLE"

# 確保目錄存在
mkdir -p "$DIR"

echo "🔍 開始監控 $ROLE 角色的交接單..."
echo "📂 監控目錄: $DIR"
echo "⏰ 每 20 秒檢查一次新的交接單"
echo "💡 提示: 新交接單出現時會顯示 /pickup 指令"
echo ""

LAST_TICKET=""

while true; do
    # 靜默拉取最新變更
    git fetch origin >/dev/null 2>&1 || true
    git pull --ff-only >/dev/null 2>&1 || true
    
    # 尋找最新的 .json 交接單 (排除 .claimed.json 和 .done.json)
    NEW_TICKET="$(find "$DIR" -name "*.json" -not -name "*.claimed.json" -not -name "*.done.json" -type f -exec ls -1t {} \; 2>/dev/null | head -n1 || true)"
    
    # 檢查是否有新的交接單
    if [ -n "$NEW_TICKET" ] && [ "$NEW_TICKET" != "$LAST_TICKET" ]; then
        echo ""
        echo "🔔 發現新交接單: $NEW_TICKET"
        echo ""
        
        # 顯示交接單基本資訊
        if command -v jq >/dev/null 2>&1; then
            echo "📋 交接詳情:"
            echo "   來源: $(jq -r '.from // "unknown"' "$NEW_TICKET")"
            echo "   任務: $(jq -r '.intent // "no description"' "$NEW_TICKET")"
            echo "   優先級: $(jq -r '.priority // "medium"' "$NEW_TICKET")"
            echo "   預估時間: $(jq -r '.estimated_hours // "unknown"' "$NEW_TICKET") 小時"
            echo ""
        fi
        
        echo "👉 在 Claude Code 中執行以接收任務:"
        echo "   /pickup $NEW_TICKET"
        echo ""
        echo "📝 或查看詳細說明 (如果存在):"
        MD_FILE="$(echo "$NEW_TICKET" | sed 's/\.json$/.md/')"
        if [ -f "$MD_FILE" ]; then
            echo "   cat $MD_FILE"
        else
            echo "   (無額外說明檔)"
        fi
        echo ""
        echo "────────────────────────────────────────"
        
        LAST_TICKET="$NEW_TICKET"
    fi
    
    # 顯示目前等待中的交接單數量 (每分鐘顯示一次狀態)
    CURRENT_MIN=$(date +%M)
    if [ $((CURRENT_MIN % 3)) -eq 0 ]; then
        PENDING_COUNT="$(find "$DIR" -name "*.json" -not -name "*.claimed.json" -not -name "*.done.json" -type f | wc -l | tr -d ' ')"
        CLAIMED_COUNT="$(find "$DIR" -name "*.claimed.json" -type f | wc -l | tr -d ' ')"
        
        if [ "$PENDING_COUNT" -gt 0 ] || [ "$CLAIMED_COUNT" -gt 0 ]; then
            echo "📊 狀態更新 [$(date +%H:%M)]: 等待中 $PENDING_COUNT 個，處理中 $CLAIMED_COUNT 個"
        fi
    fi
    
    sleep 20
done