# 多 Claude Code Terminal 協作協調機制

## 問題分析

### 🚨 潛在風險
1. **Git 衝突風險**：三個 Terminal 同時修改相同檔案
2. **重複工作風險**：任務邊界模糊導致重複實作
3. **依賴阻塞風險**：前置任務未完成但後續任務已開始
4. **狀態不同步風險**：各 Terminal 不知道其他人的進度

## 解決方案：Hooks + 狀態追蹤系統

### 1. Claude Code Hooks 設定

每個 Terminal 的專屬 `~/.claude/settings.json` 需要添加：

```json
{
  "hooks": {
    "beforeToolCall": {
      "command": "bash",
      "args": ["/path/to/scripts/hooks/coordination_check.sh", "{{toolName}}", "{{workingDirectory}}"]
    },
    "afterCommit": {
      "command": "bash", 
      "args": ["/path/to/scripts/hooks/status_update.sh", "{{commitHash}}", "{{branch}}"]
    }
  }
}
```

### 2. 協調檢查腳本

#### `scripts/hooks/coordination_check.sh`
```bash
#!/bin/bash
TOOL_NAME=$1
WORKING_DIR=$2
TERMINAL_ROLE=$(head -1 CLAUDE.md | grep -o 'AI-CORE\|API\|EXT' || echo "UNKNOWN")

# 檢查是否有其他 Terminal 正在工作同一任務
if [ -f ".coordination/active_tasks.json" ]; then
  CONFLICT=$(jq -r ".tasks[] | select(.status == \"in_progress\" and .assignedTo != \"$TERMINAL_ROLE\")" .coordination/active_tasks.json)
  
  if [ ! -z "$CONFLICT" ]; then
    echo "⚠️  警告：檢測到其他 Terminal 正在執行相關任務"
    echo "請檢查 .coordination/active_tasks.json 避免衝突"
    exit 1
  fi
fi

# Git 衝突預檢查
git fetch origin
CONFLICTS=$(git merge-tree $(git merge-base HEAD origin/dev) HEAD origin/dev | grep -c "<<<<<<< ")
if [ "$CONFLICTS" -gt 0 ]; then
  echo "🚨 Git 衝突警告：請先解決與 origin/dev 的衝突"
  exit 1
fi

echo "✅ 協調檢查通過"
```

#### `scripts/hooks/status_update.sh`
```bash
#!/bin/bash
COMMIT_HASH=$1
BRANCH=$2
TERMINAL_ROLE=$(head -1 CLAUDE.md | grep -o 'AI-CORE\|API\|EXT' || echo "UNKNOWN")
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# 更新狀態檔案
mkdir -p .coordination
cat > .coordination/last_activity.json << EOF
{
  "terminal": "$TERMINAL_ROLE",
  "lastCommit": "$COMMIT_HASH", 
  "branch": "$BRANCH",
  "timestamp": "$TIMESTAMP",
  "workingDirectory": "$(pwd)"
}
EOF

# 推送狀態更新
git add .coordination/last_activity.json
git commit --amend --no-edit
git push origin $BRANCH

echo "📊 狀態更新完成：$TERMINAL_ROLE @ $TIMESTAMP"
```

### 3. 任務狀態追蹤檔案

#### `.coordination/active_tasks.json`
```json
{
  "lastUpdated": "2025-08-19T08:30:00Z",
  "tasks": [
    {
      "taskId": "9.1",
      "title": "實作任務規劃 Agent",
      "assignedTo": "AI-CORE",
      "status": "in_progress",
      "startedAt": "2025-08-19T08:00:00Z",
      "estimatedHours": 4,
      "dependencies": ["9"],
      "outputs": ["Agent 實作完成"]
    },
    {
      "taskId": "10.1", 
      "title": "實作 Side Panel 多 Agent 協作介面",
      "assignedTo": "EXT",
      "status": "pending",
      "dependencies": ["9.6"],
      "blockedBy": ["9.6"]
    }
  ]
}
```

### 4. Terminal 啟動檢查清單

每個 Terminal 開始工作前必須執行：

```bash
# 1. Git 狀態檢查
git status --porcelain
git diff origin/dev --stat

# 2. 協調狀態檢查  
cat .coordination/active_tasks.json | jq '.tasks[] | select(.status == "in_progress")'

# 3. 任務衝突檢查
./scripts/hooks/check_task_conflicts.sh

# 4. 更新自己的任務狀態
./scripts/hooks/claim_task.sh <task_id>
```

### 5. 實時協調指令

#### 查看其他 Terminal 狀態
```bash
./scripts/coordination/status.sh
# 輸出：
# AI-CORE Terminal: 正在執行 9.1 (已進行 2h/4h)
# API Terminal: 空閒 
# EXT Terminal: 正在執行 5.1 (已進行 1h/3h)
```

#### 任務交接確認
```bash
./scripts/coordination/handoff.sh AI-CORE API 9.4
# 輸出：
# ✅ 任務 9.4 已從 AI-CORE 交接給 API
# 🔄 API Terminal 請執行: ./scripts/coordination/accept_handoff.sh 9.4
```

### 6. 衝突解決流程

#### 檢測到衝突時：
1. **暫停工作**：立即停止可能衝突的操作
2. **狀態同步**：`git fetch && ./scripts/coordination/sync_status.sh`
3. **協調溝通**：檢查 `.coordination/conflicts.log`
4. **解決策略**：先到先得 vs 優先級排序

#### 自動衝突解決：
```bash
# 檔案層級衝突：按檔案權限邊界自動分配
# - AI-CORE 修改 ai_core/**
# - API 修改 nodepilot-api/**  
# - EXT 修改 wxt-extension/**

# 任務層級衝突：按依賴關係自動排序
# - 前置任務優先
# - 阻塞任務後置
```

## 最佳實踐

### 🟢 建議做法
- 每次開始工作前執行協調檢查
- 使用 `.coordination/` 目錄追蹤狀態
- 遵守檔案權限邊界（見 Output Styles）
- 及時更新任務進度

### 🔴 避免做法  
- 不要跳過 hooks 檢查
- 不要修改其他角色的檔案
- 不要同時執行有依賴關係的任務
- 不要忽略衝突警告

## 技術實現

### Hooks 觸發時機
- **beforeToolCall**: 每次使用工具前檢查
- **afterCommit**: 每次 commit 後更新狀態
- **beforePush**: push 前最終衝突檢查

### 狀態持久化
- 使用 Git 作為狀態同步媒介
- `.coordination/` 目錄版本控制
- JSON 格式易於程式解析

### 效能考量
- hooks 執行時間 < 5 秒
- 狀態檢查使用本地快取
- 僅在必要時執行網路同步