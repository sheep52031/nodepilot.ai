# NodePilot V6 Handoff Protocol

## 概述

本協議規範三個 Terminal 之間的工作交接機制，實現 Plan-and-Execute 多 Agent 協作架構：

- **EXT Terminal** (`feature/extension`) → WXT Framework + React + TypeScript
- **API Terminal** (`feature/api`) → FastAPI + 調度器 + SQLite
- **AI-CORE Terminal** (`feature/ai-core`) → 多 Agent 系統 + 模型池 + 整合

## 交接文件結構

### 文件位置規範
```
.handoff/
├── EXT/           # 給 EXT Terminal 的交接單
├── API/           # 給 API Terminal 的交接單
└── AI-CORE/       # 給 AI-CORE Terminal 的交接單
```

### 文件命名規範
- **待處理**: `YYYYMMDD-HHMM_<task-id>.json`
- **處理中**: `YYYYMMDD-HHMM_<task-id>.claimed.json`
- **已完成**: `YYYYMMDD-HHMM_<task-id>.done.json`
- **說明文件**: `YYYYMMDD-HHMM_<task-id>.md` (可選)

## Handoff JSON 結構

### 基本結構
```json
{
  "handoff_id": "20250819-1430_api_ext_001",
  "from": "API",
  "to": "EXT", 
  "intent": "前端串接 /annotations/search 新 API 並完成 E2E 測試",
  "priority": "high|medium|low",
  "estimated_hours": 2,
  "worktrees": {
    "from": "../nodepilot-worktrees/feature-api",
    "to": "../nodepilot-worktrees/feature-extension"
  },
  "inputs": {
    "api_contract": "spec_docs/api/annotations.yml",
    "example_payload": "api/examples/annotations_search.json", 
    "test_endpoint": "http://localhost:8000/annotations/search"
  },
  "acceptance": [
    "前端可在允許的白名單頁面呼叫 API 並顯示結果",
    "通過整合測試（見 tests/integration/annotations_search.spec.ts）"
  ],
  "related_tasks": ["9.6 結果整合", "Ext integration smoke test"],
  "links": [
    "spec_docs/tasks.md#task-96",
    "PR #123"
  ],
  "status": "pending",
  "claimed_by": "",
  "claimed_at": "",
  "completed_at": ""
}
```

### 角色專用欄位

#### API → EXT
```json
{
  "inputs": {
    "api_contract": "OpenAPI 規格檔案路徑",
    "example_payload": "API 請求/回應範例",
    "test_endpoint": "測試用 API 端點",
    "mock_data": "前端開發用 mock 資料"
  }
}
```

#### API → AI-CORE  
```json
{
  "inputs": {
    "agent_interface": "Agent 呼叫介面規格",
    "context_schema": "上下文傳遞格式",
    "fallback_config": "備援機制配置"
  }
}
```

#### AI-CORE → API
```json
{
  "inputs": {
    "model_choices": "模型選擇策略",
    "context_routing": "上下文路由邏輯", 
    "integration_points": "整合點規格"
  }
}
```

#### AI-CORE → EXT
```json
{
  "inputs": {
    "ui_updates": "介面更新需求",
    "state_changes": "狀態管理變更",
    "user_feedback": "使用者體驗改善"
  }
}
```

## 工作流程

### 1. 交接單產生 (發送方)
```bash
# 1. 產生交接 JSON
echo '{...}' > .handoff/EXT/20250819-1430_api_ext_001.json

# 2. 可選：產生說明文件
echo "## 詳細說明..." > .handoff/EXT/20250819-1430_api_ext_001.md

# 3. 自動提交推送 (使用 scripts/handoff/emit_handoff.sh)
./scripts/handoff/emit_handoff.sh EXT .handoff/EXT/20250819-1430_api_ext_001.json
```

### 2. 交接單接收 (接收方)
```bash
# 1. 拉取最新交接單
git pull

# 2. Claim 交接單 (修改狀態為 in_progress)  
/pickup .handoff/EXT/20250819-1430_api_ext_001.json

# 3. 執行任務...

# 4. 完成後產生 .done.json
echo '{...}' > .handoff/EXT/20250819-1430_api_ext_001.done.json
```

### 3. 狀態管理
- **pending**: 等待接收方處理
- **claimed**: 接收方已認領，處理中
- **completed**: 任務完成
- **blocked**: 遇到阻礙，需要協調

## 整合測試交接

### E2E 測試流程
```json
{
  "handoff_id": "e2e_integration_test",
  "from": "AI-CORE",
  "to": "API", 
  "intent": "執行端到端整合測試並回報結果",
  "inputs": {
    "test_scenarios": "tests/e2e/scenarios.yml",
    "expected_flows": "使用者完整操作流程",
    "performance_targets": "效能指標要求"
  },
  "acceptance": [
    "所有核心使用者流程通過測試",
    "AI 教學生成回應時間 ≤ 15 秒", 
    "Extension 在 manus.im 正常載入運作"
  ]
}
```

## 衝突解決機制

### 文件衝突
- 使用 Git merge 策略解決檔案衝突
- 交接單衝突：以時間戳記較新者為準
- API 契約衝突：強制要求在 `spec_docs/api/` 先更新契約

### 優先權管理
- `high`: 阻塞其他任務的核心功能
- `medium`: 正常開發任務
- `low`: 優化和增強功能

### 死鎖預防
- 每個交接單必須設定 `estimated_hours`
- 超過預估時間 150% 自動標記為 `blocked`
- 每日 standup 檢查 `blocked` 狀態交接單

## 最佳實踐

### 交接單品質
- `intent` 描述要具體可測試
- `acceptance` 標準要清楚量化
- `inputs` 要包含所有必要資源
- 避免過大的交接單 (> 8 小時)

### 並行開發
- 同一模組內的任務可並行處理
- 跨模組的依賴必須透過交接單管理
- API 契約變更需要通知所有相關 Terminal

### 文檔維護
- 每個交接單完成後更新相關 `spec_docs/`
- 重要決策要記錄在 `.md` 說明文件中
- 定期清理已完成的交接單 (保留 7 天)