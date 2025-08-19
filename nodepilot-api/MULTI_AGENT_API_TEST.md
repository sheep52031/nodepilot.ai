# NodePilot V6 多 Agent 系統 API 測試指南

## 📋 API Contract

### 基礎系統狀態
```bash
# 檢查多 Agent 系統狀態
curl http://localhost:8000/multi-agent/status

# 檢查系統健康
curl http://localhost:8000/multi-agent/health
```

### 多 Agent 教學生成（主要端點）
```bash
# 完整的多 Agent 教學內容生成
curl -X POST "http://localhost:8000/multi-agent/generate-teaching" \
  -F "url=https://manus.im/blog/example" \
  -F "selected_text=FastAPI async def handler" \
  -F "confusion_note=不懂這個 async 是怎麼運作的" \
  -F "page_title=FastAPI 非同步教學"

# 包含音檔的多 Agent 處理
curl -X POST "http://localhost:8000/multi-agent/generate-teaching" \
  -F "url=https://manus.im/blog/example" \
  -F "selected_text=React useEffect" \
  -F "confusion_note=useEffect 的依賴陣列規則" \
  -F "audio_file=@confusion.webm"
```

### RAG 筆記檢索系統
```bash
# 搜尋相關筆記
curl -X POST "http://localhost:8000/multi-agent/rag/search" \
  -F "query=FastAPI 開發" \
  -F "selected_text=Python Web 框架" \
  -F "top_k=5"

# 檢查 RAG 服務狀態
curl http://localhost:8000/multi-agent/rag/status

# 重新載入筆記快取
curl -X POST http://localhost:8000/multi-agent/rag/refresh

# 列出所有筆記
curl "http://localhost:8000/multi-agent/rag/notes?limit=10"
```

### 模型管理與 Fallback 系統
```bash
# 檢查模型使用統計
curl http://localhost:8000/multi-agent/models/usage

# 切換模型可用性（維護模式）
curl -X POST "http://localhost:8000/multi-agent/models/toggle?model_id=gpt-4o&available=false"

# 重新啟用模型
curl -X POST "http://localhost:8000/multi-agent/models/toggle?model_id=gpt-4o&available=true"
```

### 結果整合與格式化
```bash
# 測試內容格式化
curl -X POST "http://localhost:8000/multi-agent/formatting/test" \
  -F "content=FastAPI 是現代化的 Python Web 框架" \
  -F "confusion_note=不懂路由設計" \
  -F "selected_text=@app.get('/users')"

# 檢查品質評分演示
curl http://localhost:8000/multi-agent/formatting/quality-check
```

### 任務狀態追蹤
```bash
# 檢查特定任務狀態 (從 generate-teaching 回應中取得 session_id)
curl http://localhost:8000/multi-agent/task/{session_id}_planner

# 取消執行中的任務
curl -X POST http://localhost:8000/multi-agent/tasks/{task_id}/cancel
```

## 🔧 Endpoint Implementation 

### 核心架構設計

#### 1. Agent 調度系統
- **檔案**: `agent_scheduler.py`
- **功能**: Plan-and-Execute 模式的純 Python 多 Agent 調度
- **特色**: 無 LangChain/CrewAI 依賴，輕量化設計

#### 2. 模型管理系統
- **檔案**: `model_manager.py` 
- **功能**: 可切換模型架構和多層 Fallback 機制
- **支援模型**: OpenAI GPT-4o, GPT-3.5-turbo, Whisper-1

#### 3. RAG 筆記檢索
- **檔案**: `rag_service.py`
- **功能**: Obsidian 筆記語意搜索，模擬向量嵌入
- **特色**: 支援標籤匹配和內容片段提取

#### 4. 結果整合服務
- **檔案**: `result_formatter.py`
- **功能**: 多 Agent 結果整合、品質評估、衝突解決
- **輸出**: 高品質 Markdown 教學內容

#### 5. 專門 Agent 實作
- **檔案**: `agents.py`
- **Agents**: 
  - `PlannerAgent`: 任務規劃 (GPT-4o/Claude 3.5)
  - `ContextAnalyzerAgent`: 文章上下文分析
  - `AudioProcessorAgent`: 音訊語意結構化  
  - `RAGRetrieverAgent`: 筆記檢索整合
  - `ContentGeneratorAgent`: Artifacts 教學生成

## 🚀 Local Testing

### 測試案例 1: 基礎多 Agent 流程
```bash
# 1. 啟動服務
cd nodepilot-api
source .venv/bin/activate
python main.py

# 2. 測試基礎功能
curl http://localhost:8000/multi-agent/status
# 預期結果: {"system_health":"healthy","scheduler":{"registered_agents":5,...}

# 3. 測試 RAG 搜索
curl -X POST "http://localhost:8000/multi-agent/rag/search" \
  -F "query=FastAPI 路由" -F "top_k=2"
# 預期結果: 返回 2 篇相關筆記，包含相關度評分
```

### 測試案例 2: 完整教學生成
```bash
# 模擬完整用戶困惑案例
curl -X POST "http://localhost:8000/multi-agent/generate-teaching" \
  -F "url=https://manus.im/blog/fastapi-tutorial" \
  -F "selected_text=@app.post('/users/', response_model=User)" \
  -F "confusion_note=不理解這個 response_model 的作用"

# 預期結果結構:
{
  "success": true,
  "annotation_id": 123,
  "teaching_content": "# 關於 response_model...",
  "content_quality": {
    "quality_score": 0.85,
    "processing_notes": ["品質評分: 0.85"]
  },
  "agent_execution": {
    "agents_used": ["planner", "context_analyzer", "rag_retriever", "content_generator"],
    "integration_metadata": {...}
  }
}
```

### 測試案例 3: Fallback 機制驗證
```bash
# 1. 停用主要模型
curl -X POST "http://localhost:8000/multi-agent/models/toggle?model_id=gpt-4o&available=false"

# 2. 測試是否自動降級
curl -X POST "http://localhost:8000/multi-agent/generate-teaching" \
  -F "url=test" -F "selected_text=test code" -F "confusion_note=測試降級"

# 3. 檢查回應中的 fallback_used 標記
# 預期: metadata.fallback_used: true
```

## 🧪 Integration Test

### Agent 協作測試腳本
```python
import requests
import json

def test_multi_agent_integration():
    base_url = "http://localhost:8000/multi-agent"
    
    # 1. 系統健康檢查
    health = requests.get(f"{base_url}/health")
    assert health.json()["status"] == "healthy"
    
    # 2. RAG 系統測試
    rag_response = requests.post(f"{base_url}/rag/search", data={
        "query": "Python 開發",
        "top_k": 3
    })
    rag_data = rag_response.json()
    assert rag_data["success"] == True
    assert len(rag_data["results"]) <= 3
    
    # 3. 完整流程測試
    teaching_response = requests.post(f"{base_url}/generate-teaching", data={
        "url": "https://example.com",
        "selected_text": "async def example():",
        "confusion_note": "不懂非同步函數"
    })
    
    teaching_data = teaching_response.json()
    assert teaching_data["success"] == True
    assert "teaching_content" in teaching_data
    assert teaching_data["content_quality"]["quality_score"] > 0.0
    
    print("✅ 所有整合測試通過")

if __name__ == "__main__":
    test_multi_agent_integration()
```

### 資料庫狀態驗證
```sql
-- 檢查標註記錄是否正確儲存
SELECT id, url, selected_text, confusion_note, 
       audio_transcription IS NOT NULL as has_audio,
       cognitive_note IS NOT NULL as has_cognitive,
       teaching_content IS NOT NULL as has_teaching,
       status, created_at
FROM annotations 
ORDER BY created_at DESC 
LIMIT 5;
```

## 📤 Handoff Ticket

### 交接至前端團隊 (EXT)

```json
{
  "handoff_id": "20250119-1430_api_ext_001",
  "from": "API",
  "to": "EXT",
  "intent": "整合多 Agent 教學生成到 Chrome Extension Side Panel",
  "inputs": {
    "api_endpoints": {
      "primary": "POST /multi-agent/generate-teaching",
      "status": "GET /multi-agent/status", 
      "rag_search": "POST /multi-agent/rag/search"
    },
    "test_server": "http://localhost:8000",
    "example_requests": "見 MULTI_AGENT_API_TEST.md",
    "response_format": {
      "success": "boolean",
      "teaching_content": "markdown string",
      "content_quality": {"quality_score": "float 0-1"},
      "agent_execution": {"agents_used": "array", "session_id": "string"}
    }
  },
  "acceptance": [
    "Side Panel 能正常調用多 Agent API",
    "顯示 Agent 執行進度和狀態",
    "教學內容 Markdown 正確渲染",
    "品質評分和處理筆記顯示",
    "錯誤處理和降級機制運作"
  ],
  "integration_notes": [
    "使用 FormData 上傳音檔檔案",
    "處理 async/await API 調用",
    "實作載入狀態和進度指示",
    "支援 Agent 執行狀態追蹤",
    "整合 RAG 筆記參考顯示"
  ]
}
```

### 技術實作完成摘要

#### ✅ 已完成的核心功能
1. **純 Python 多 Agent 調度系統** - 完全避免 LangChain/CrewAI 依賴
2. **可切換模型架構** - 支援 GPT-4o/GPT-3.5 自動降級
3. **RAG 筆記檢索系統** - Obsidian 筆記語意搜索
4. **結果整合與格式化** - 品質評估、衝突解決、Markdown 輸出
5. **Agent 間協作機制** - Plan-and-Execute 模式，Context 傳遞

#### 🎯 API 端點總覽
- `POST /multi-agent/generate-teaching` - 主要教學生成
- `GET /multi-agent/status` - 系統狀態監控  
- `POST /multi-agent/rag/search` - RAG 筆記搜索
- `POST /multi-agent/models/toggle` - 模型管理
- `GET /multi-agent/health` - 健康檢查
- `POST /multi-agent/formatting/test` - 格式化測試

#### 🔄 準備就緒的交接點
1. **EXT 團隊**: Chrome Extension 整合多 Agent API
2. **AI-CORE 團隊**: Agent 邏輯優化和模型調整
3. **部署團隊**: 生產環境配置和監控

---

**NodePilot V6 多 Agent API 系統已完整實作並可投入使用** ✅