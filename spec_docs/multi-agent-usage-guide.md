# NodePilot 多 Claude Code 協作使用指南

## 概述

本指南說明如何使用三個 Claude Code Terminal 進行高效並行開發。

## Terminal 架構

### 🎯 三個專業 Terminal
- **EXT Terminal**: `../nodepilot-worktrees/feature-extension` - 前端工程師
- **API Terminal**: `../nodepilot-worktrees/feature-api` - 後端工程師  
- **AI-CORE Terminal**: `../nodepilot-worktrees/feature-ai-core` - AI 系統工程師

## 快速開始

### 1. 啟動三個 Terminal

```bash
# Terminal 1: EXT 前端工程師
cd ../nodepilot-worktrees/feature-extension
claude-code  # 會自動載入 EXT 角色設定

# Terminal 2: API 後端工程師  
cd ../nodepilot-worktrees/feature-api
claude-code  # 會自動載入 API 角色設定

# Terminal 3: AI-CORE 系統工程師
cd ../nodepilot-worktrees/feature-ai-core  
claude-code  # 會自動載入 AI-CORE 角色設定
```

### 2. 啟動 Handoff Watcher (可選)

在每個 Terminal 開一個額外視窗運行 watcher：

```bash
# EXT Terminal 額外視窗
./scripts/handoff/watch_handoff.sh EXT

# API Terminal 額外視窗  
./scripts/handoff/watch_handoff.sh API

# AI-CORE Terminal 額外視窗
./scripts/handoff/watch_handoff.sh AI-CORE
```

## 協作工作流程範例

### 場景: 實作新的標註歷史 API

#### Step 1: API Terminal 開發 API
```
用戶: 我需要開發標註歷史查詢 API，支援分頁和篩選

API Terminal:
1. 分析需求，設計 API 端點
2. 實作 FastAPI 端點和 SQLite 查詢  
3. 建立測試資料和 API 文檔
4. 產生交接單給 EXT Terminal
```

#### Step 2: 自動交接到 EXT Terminal
```bash
# API Terminal 自動執行
./scripts/handoff/emit_handoff.sh EXT .handoff/EXT/20250819-1500_api_ext_001.json
```

#### Step 3: EXT Terminal 接收並整合
```
# EXT Terminal watcher 通知
🔔 新交接單: .handoff/EXT/20250819-1500_api_ext_001.json

用戶: /pickup .handoff/EXT/20250819-1500_api_ext_001.json

EXT Terminal:
1. 讀取 API 契約和範例資料
2. 實作前端 React 組件呼叫 API
3. 更新 Side Panel UI 顯示歷史
4. 執行整合測試
```

## 交接單範例

### API → EXT 交接單
```json
{
  "handoff_id": "20250819-1500_api_ext_001",
  "from": "API",
  "to": "EXT", 
  "intent": "前端整合標註歷史查詢 API 並實作分頁 UI",
  "inputs": {
    "api_endpoint": "GET /annotations?page=1&limit=10&status=learning",
    "api_contract": "spec_docs/api/annotations.yml",
    "example_response": "nodepilot-api/examples/annotations_list.json",
    "test_endpoint": "http://localhost:8000/annotations"
  },
  "acceptance": [
    "前端可正常調用 API 並顯示分頁結果",
    "支援狀態篩選 (all/learning/understood)",
    "通過整合測試 tests/integration/annotations_history.spec.ts"
  ],
  "worktrees": {
    "from": "../nodepilot-worktrees/feature-api",
    "to": "../nodepilot-worktrees/feature-extension"
  }
}
```

### EXT → AI-CORE 交接單  
```json
{
  "handoff_id": "20250819-1600_ext_ai_001",
  "from": "EXT",
  "to": "AI-CORE",
  "intent": "優化標註歷史的 AI 學習狀態推薦邏輯",
  "inputs": {
    "user_behavior_data": "前端收集的使用者行為資料",
    "ui_feedback": "使用者對 AI 建議的反饋 UI 設計",
    "state_transition": "學習狀態轉換的前端邏輯"
  },
  "acceptance": [
    "AI 可根據使用者行為推薦學習狀態",
    "推薦邏輯整合到現有 Agent 系統",
    "前端可顯示 AI 推薦的學習建議"
  ]
}
```

## 常用指令

### Handoff 操作
```bash
# 查看待處理交接單
ls -la .handoff/EXT/

# 認領交接單
./scripts/handoff/pickup_handoff.sh .handoff/EXT/ticket.json

# 發送交接單  
./scripts/handoff/emit_handoff.sh API .handoff/API/new_ticket.json
```

### Git 同步
```bash
# 每個 Terminal 工作前必須執行
git status --porcelain
git diff origin/dev --name-only
git pull

# 提交工作
git add .
git commit -m "[ext] feature: 實作標註歷史 UI 組件"
git push
```

## 除錯技巧

### 檢查角色設定
```bash
# 確認當前 Terminal 角色
head -5 CLAUDE.md

# 確認檔案權限設定
grep -A 10 "允許修改" CLAUDE.md
```

### 交接單狀態追蹤
```bash
# 查看所有交接單狀態
find .handoff -name "*.json" -exec basename {} \; | sort

# 清理已完成交接單 (7天前)
find .handoff -name "*.done.json" -mtime +7 -delete
```

## 最佳實踐

### 1. 保持角色專注
- 每個 Terminal 只專注自己的技術領域
- 不要越界修改其他模組的程式碼
- 有疑問時先查看對應的 Output Style 設定

### 2. 及時交接
- 遇到跨域需求立即建立交接單  
- 交接單要包含完整的上下文和驗收標準
- 使用自動化腳本確保交接單正確提交

### 3. 保持同步
- 每次工作前先 `git pull`
- 定期檢查 `.handoff/` 目錄的新交接單
- 完成任務後及時更新 `tasks.md` 狀態

### 4. 文檔維護
- 重要決策記錄在交接單的 `.md` 說明檔中
- API 契約變更要及時更新 `spec_docs/api/`
- 定期清理已完成的交接單避免混亂

## 故障排除

### Terminal 角色混亂
```bash
# 重新載入正確的 CLAUDE.md
cd 正確的-worktree-目錄
claude-code --reload
```

### 交接單衝突
```bash
# 手動解決交接單衝突
git pull
# 編輯衝突的 .json 檔案
git add .handoff/
git commit -m "resolve handoff conflicts"
```

### Watcher 沒有通知
```bash
# 手動檢查交接單
ls -la .handoff/YOUR_ROLE/

# 重啟 watcher
pkill -f watch_handoff.sh
./scripts/handoff/watch_handoff.sh YOUR_ROLE
```