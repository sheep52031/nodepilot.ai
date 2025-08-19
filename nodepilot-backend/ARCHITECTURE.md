# NodePilot Backend 架構說明

## 🏗️ 分層架構設計

```
nodepilot-backend/
├── app/                           # 主應用目錄
│   ├── __init__.py
│   ├── main.py                    # 應用入口點
│   │
│   ├── core/                      # 核心配置層
│   │   ├── __init__.py
│   │   └── config.py              # 應用設定和環境變數
│   │
│   ├── api/                       # API 路由層
│   │   ├── __init__.py
│   │   └── v1/                    # API 版本 1
│   │       ├── __init__.py
│   │       └── agents.py          # 多 Agent 系統路由
│   │
│   ├── services/                  # 業務邏輯服務層
│   │   ├── __init__.py
│   │   ├── agent_scheduler.py     # Agent 調度服務
│   │   ├── integrated_system.py   # 整合系統服務
│   │   ├── model_manager.py       # AI 模型管理
│   │   ├── openai_service.py      # OpenAI 服務
│   │   ├── rag_service.py         # RAG 檢索服務
│   │   └── result_formatter.py    # 結果格式化服務
│   │
│   ├── agents/                    # AI Agent 層
│   │   ├── __init__.py
│   │   ├── base_agent.py          # Agent 基礎類別
│   │   ├── planning_agent.py      # 任務規劃 Agent
│   │   ├── context_analysis_agent.py  # 內容分析 Agent
│   │   ├── audio_semantic_agent.py    # 音訊語意 Agent
│   │   ├── note_retrieval_agent.py    # 筆記檢索 Agent
│   │   └── teaching_generation_agent.py # 教學生成 Agent
│   │
│   ├── ai_core/                   # AI 核心基礎設施
│   │   ├── __init__.py
│   │   ├── scheduler.py           # 核心調度器
│   │   ├── model_pool.py          # 模型池管理
│   │   ├── context_router.py      # 上下文路由
│   │   ├── execution_plan.py      # 執行計畫
│   │   ├── result_integrator.py   # 結果整合器
│   │   └── system_initializer.py  # 系統初始化
│   │
│   ├── models/                    # 資料模型層
│   │   ├── __init__.py            # 統一匯出介面
│   │   ├── database.py            # SQLAlchemy 模型和連接
│   │   └── crud.py                # 資料庫 CRUD 操作
│   │
│   ├── schemas/                   # API 介面模型
│   │   ├── __init__.py
│   │   └── schemas.py             # Pydantic 請求/回應模型
│   │
│   └── utils/                     # 工具函數層
│       └── __init__.py
│
├── tests/                         # 測試檔案
│   ├── agents/
│   │   └── test_multi_agent_system.py
│   └── test_integration.py        # 整合測試
│
├── docs/                          # 文件資料夾
│   ├── API_TEST.md                # API 測試指南
│   └── MULTI_AGENT_API_TEST.md    # 多 Agent API 測試指南
│
├── init_db.py                     # 資料庫初始化腳本
├── pyproject.toml                 # 專案配置和依賴
├── uv.lock                        # 依賴鎖定檔
├── nodepilot.db                   # SQLite 資料庫
└── ARCHITECTURE.md                # 本文件
```

## 🎯 架構層級職責

### 1. API 層 (`app/api/`)
- **職責**: HTTP 請求處理、路由分發、請求驗證
- **主要檔案**: `v1/agents.py` - 多 Agent 系統 API 端點
- **特色**: RESTful API 設計，支援 FormData 和 JSON

### 2. 服務層 (`app/services/`)
- **職責**: 業務邏輯實作、系統整合、外部 API 調用
- **核心服務**:
  - `agent_scheduler.py` - Agent 任務調度和協作
  - `integrated_system.py` - AI-CORE 與 API 的整合層
  - `model_manager.py` - AI 模型管理和 fallback
  - `rag_service.py` - RAG 筆記檢索系統

### 3. Agent 層 (`app/agents/`)
- **職責**: 具體的業務邏輯智能代理實作
- **代理類型**:
  - `planning_agent.py` - 任務規劃代理 (GPT-4o/Claude 3.5)
  - `context_analysis_agent.py` - 文章上下文分析
  - `audio_semantic_agent.py` - 音訊語意結構化
  - `note_retrieval_agent.py` - 筆記檢索整合
  - `teaching_generation_agent.py` - 教學內容生成

### 4. AI 核心基礎設施 (`app/ai_core/`)
- **職責**: 支撐代理運作的底層架構和調度系統
- **核心組件**:
  - `scheduler.py` - Plan-and-Execute 任務調度
  - `model_pool.py` - 多模型管理和切換
  - `result_integrator.py` - 多 Agent 結果整合
  - `system_initializer.py` - 系統啟動和初始化

### 5. 模型層 (`app/models/`)
- **職責**: 資料庫模型定義、CRUD 操作、資料存取
- **清晰分離**:
  - `database.py` - SQLAlchemy 資料庫模型和連接
  - `crud.py` - 資料庫操作函數
  - `__init__.py` - 統一匯出介面

### 6. API 介面模型 (`app/schemas/`)
- **職責**: API 輸入輸出資料結構定義
- **Pydantic 模型**: 請求驗證、回應序列化、型別檢查

## 🔄 設計原則

### 單一職責原則
- **agents/**: 專注業務邏輯智能代理
- **ai_core/**: 專注基礎設施和核心系統
- **services/**: 專注服務編排和外部整合
- **models/**: 專注資料存取和操作

### 依賴倒置
- 高層模組不依賴低層模組
- Agent 層使用 ai_core 提供的抽象介面
- 服務層整合各個 Agent 而不直接操作核心系統

### 開放封閉原則
- 新增 Agent 不需修改現有程式碼
- 新增模型供應商通過介面擴展
- API 版本控制支援向後相容

## 🚀 啟動方式

### 開發模式
```bash
cd nodepilot-backend
python app/main.py
```

### 生產模式
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 資料庫初始化
```bash
python init_db.py
```

## 📚 開發指南

### 新增 AI Agent
1. 在 `app/agents/` 建立新的 Agent 類別
2. 繼承 `base_agent.BaseAgent`
3. 在 `agent_scheduler.py` 註冊新 Agent
4. 在相關的 API 端點中整合使用

### 新增 API 端點
1. 在 `app/api/v1/agents.py` 新增路由
2. 使用 `app/schemas/` 定義請求回應模型
3. 在 `app/services/` 實作業務邏輯
4. 更新 `docs/API_TEST.md` 添加測試範例

### 新增資料模型
1. SQLAlchemy 模型 → `app/models/database.py`
2. CRUD 操作 → `app/models/crud.py`
3. API 模型 → `app/schemas/schemas.py`
4. 更新 `app/models/__init__.py` 匯出介面

### 測試開發
1. 單元測試 → `tests/`
2. 整合測試 → `tests/test_integration.py`
3. API 測試 → `docs/API_TEST.md` 中的 curl 範例

## 📂 檔案管理規範

### 廢棄檔案標註
已廢棄的檔案在檔案頂部標註：
```python
# 可以刪除 - 已由 [新檔案名稱] 取代
```

### 文件組織
- **測試檔案** → `tests/`
- **API 文件** → `docs/`
- **配置檔案** → 專案根目錄
- **應用程式碼** → `app/`

## 🔧 技術特色

### 多 Agent 協作
- Plan-and-Execute 模式
- Agent 間 Context 傳遞
- 結果智慧整合和衝突解決

### 模型管理
- 多供應商支援 (OpenAI, 未來擴展)
- 自動 fallback 機制
- 使用統計和成本控制

### RAG 整合
- Obsidian 筆記解析
- 語意搜索 (模擬向量嵌入)
- 上下文相關性分析

這個架構設計確保了 NodePilot Backend 的可維護性、擴展性和清晰性，支援複雜的多 Agent AI 系統運作。