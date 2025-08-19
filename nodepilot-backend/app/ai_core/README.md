# NodePilot AI-CORE 系統

純 Python 多 Agent 智慧協作系統，實現 Plan-and-Execute 架構。

## 🏗️ 核心架構

```
ai_core/
├── scheduler.py          # Agent 調度器 - 主要協調中心
├── execution_plan.py     # 執行計畫 - 任務分解和依賴管理
├── model_pool.py         # 模型池 - 可切換模型和 fallback
├── context_router.py     # 上下文路由 - 智慧資料傳遞
├── result_integrator.py  # 結果整合 - 品質保證和格式化
└── system_initializer.py # 系統初始化 - 啟動和配置管理

agents/
├── planning_agent.py           # 任務規劃 (GPT-4o/Claude 3.5)
├── context_analysis_agent.py   # 文章上下文分析
├── audio_semantic_agent.py     # 音訊語意結構化
├── note_retrieval_agent.py     # RAG 筆記檢索
└── teaching_generation_agent.py # 教學內容生成 + Artifacts
```

## 🚀 快速開始

```python
from ai_core.system_initializer import initialize_system

# 初始化系統
scheduler = await initialize_system()

# 執行用戶請求
result = await scheduler.execute_user_request(
    user_confusion="我不理解 React useEffect",
    selected_text="useEffect(() => { ... }, [])",
    page_context={"url": "...", "title": "..."},
    audio_transcription="用戶音訊轉錄內容"
)

print(result["teaching_content"])  # 個人化教學內容
print(result["metadata"]["artifacts"])  # Artifacts 可視化
```

## 🧠 Agent 類型

### 1. Planning Agent
- **模型**: GPT-4o / Claude 3.5 Sonnet
- **功能**: 分析用戶困惑 → 生成結構化執行計畫
- **輸出**: 任務依賴圖、執行順序、優先級

### 2. Context Analysis Agent  
- **模型**: Claude 3.5 Sonnet / GPT-4o
- **功能**: 文章結構分析，無需向量搜尋
- **輸出**: 相關段落、概念關係圖、上下文摘要

### 3. Audio Semantic Agent
- **模型**: Claude 3.5 Sonnet / GPT-4o Mini
- **功能**: 音訊語意理解、困惑類型分析
- **輸出**: 困惑分類、情緒狀態、學習意圖

### 4. Note Retrieval Agent
- **模型**: GPT-4o Mini / Claude 3.5 Haiku  
- **功能**: RAG 筆記檢索、個人化知識連結
- **輸出**: 相關筆記、學習歷史洞察、知識缺口

### 5. Teaching Generation Agent
- **模型**: Claude 4.0 / GPT-5 (首選) 
- **功能**: 多維度整合、Artifacts 可視化教學
- **輸出**: 個人化教學內容、互動式範例、視覺化圖表

## 🔄 執行流程

1. **Planning Phase**: 用戶困惑 → 任務分解 → 執行計畫
2. **Execution Phase**: 並行/序列執行 Agent 任務
3. **Integration Phase**: 結果整合 → 品質檢查 → 格式化
4. **Output Phase**: Markdown 教學內容 + Artifacts

## 🎯 模型選擇策略

| 任務類型 | 主要模型 | 備援模型 | 考量因素 |
|---------|---------|---------|----------|
| 任務規劃 | GPT-4o | Claude 3.5 → o1-preview | 邏輯推理能力 |
| 上下文分析 | Claude 3.5 | GPT-4o → Claude Haiku | 長文檢理解 |
| 音訊語意 | Claude 3.5 | GPT-4o Mini | 語言理解精度 |
| 筆記檢索 | GPT-4o Mini | Claude Haiku | 成本效益 |
| 教學生成 | Claude 3.5 | GPT-4o → o1-preview | 創意和教學品質 |

## 🛡️ Fallback 機制

- **Circuit Breaker**: 連續失敗自動切換模型
- **Rate Limiting**: 防止 API 限額超標
- **Quality Assessment**: 低品質回應觸發重試
- **Graceful Degradation**: 部分失敗不影響整體結果

## 📊 監控指標

```python
# 取得系統狀態
status = scheduler.get_system_status()
print(status["model_stats"])  # 模型使用統計
print(status["agent_performance"])  # Agent 效能指標

# 取得模型池統計
model_stats = model_pool.get_usage_stats()
print(model_stats["gpt-4o"]["success_rate"])
print(model_stats["claude-3-5-sonnet"]["avg_response_time"])
```

## ⚙️ 環境配置

```bash
# 必要環境變數
export OPENAI_API_KEY="your_openai_key"
export ANTHROPIC_API_KEY="your_anthropic_key"

# 可選配置
export AI_MODEL_PRIORITY="quality"  # quality|speed|cost|balanced
export AI_MAX_CONCURRENT=5
export AI_TIMEOUT_SECONDS=30
```

## 🧪 測試

```bash
# 執行完整系統測試
python tests/agents/test_multi_agent_system.py

# 測試覆蓋情境
# - 基礎文字問題
# - 音訊困惑分析  
# - 複雜文章分析
# - 模型 fallback 機制
```

## 📈 效能最佳化

- **並行執行**: 無依賴的 Agent 可並行處理
- **上下文最佳化**: 動態調整上下文視窗大小
- **模型選擇**: 根據任務特性選擇最適合的模型
- **結果快取**: 避免重複 API 調用

## 🔗 整合點

準備交接給 **API Terminal**：
- FastAPI 端點整合
- 異步處理機制
- 錯誤處理和日誌
- API 回應格式標準化

查看 `.handoff/20250819-1630_ai-core_to_api_001.json` 取得詳細交接資訊。