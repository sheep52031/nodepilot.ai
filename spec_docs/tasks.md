# NodePilot V6 MVP 實作計畫

## MVP 核心目標 (更新)

基於**微服務 + 多 Agent** 架構，實現智慧音訊困惑分析和個人化教學生成。核心特色為 **Voxtral Mini 3B Q4 本地語音推理** + 雲端 LLM 教學生成，驗證「本地量化模型 + 微服務架構」比傳統雲端方案提供更好的**隱私保護**和**響應速度**。

## 技術架構：微服務 + WXT Extension + 多 Agent 後端 (更新)

- 前端: WXT Framework + React 18 + TypeScript
- 主後端: FastAPI + uv 套件管理 + 多 Agent 系統
- **語音微服務**: Voxtral Mini 3B Q4 + Docker + RTX 3080 GPU
- **開發模式**: Linux RTX 3080 推理伺服器 + MacBook Air 遠端開發
- AI 架構: 本地語音 + 雲端 LLM 混合推理
- 白名單: 僅限 https://manus.im/blog/*

## 多 Terminal 協作任務分派

**分派標記系統：**
- **【AI-CORE】**: AI-CORE Terminal 獨立完成
- **【API】**: API Terminal 獨立完成  
- **【EXT】**: EXT Terminal 獨立完成
- **【A → B】**: A Terminal 完成後交接給 B Terminal
- **【A → B → C】**: 多階段協作流程

**協作規則：**
- 每個任務都有明確的 _依賴_ 和 _輸出_ 描述
- 遇到跨 Terminal 需求必須建立 Handoff Ticket
- 依照 `spec_docs/handoff-protocol.md` 執行交接

## 當前優先任務清單

**注意：** 基礎架構任務（1.x, 2.x, 3.x, 4.x, 5.x）已完成並移至 `tasks_done.md`

### 📊 任務9進度概覽 (多Agent系統實作)

**✅ 已完成核心功能 (2025-08-20):**
- 9.0 多Agent系統基礎架構 (FastAPI + 分層架構)
- 9.1 音頻處理端點和Agent (Whisper API + 檔案上傳)
- 9.2 多模態內容整合 (文字+音頻→學習筆記生成)
- **9.9 Voxtral Mini 3B Q4 微服務架構** (Docker + RTX 3080 + ONNX Runtime)
- **9.10 微服務語音推理整合** (HTTP API 客戶端 + 備援機制)
- **9.11 本地 Q4 量化模型測試環境** (為高通筆電 QNN 轉換做準備)

**🔄 部分完成:**
- 9.5 基礎音頻語意分析 (GPT-3.5-turbo 結構化分析)

**⏳ 待實作:**
- **10.0 高通筆電 QNN 轉換測試** (Q4 ONNX → QNN 格式轉換)
- **9.11 NodePilot 主系統整合 Voxtral 微服務** (後端 API 客戶端實作)
- 9.3-9.8 進階Agent功能 (任務規劃、上下文分析、RAG檢索等)
- **11.0 WXT 擴充插件前端整合** (與微服務後端 API 整合)

**✨ 已驗證測試案例 (更新):**
```bash
# Voxtral Q4 微服務健康檢查
curl http://localhost:8001/health

# 微服務語音推理測試
curl -X POST http://localhost:8001/inference/upload \
  -F "file=@test.wav" \
  -F "task=transcribe" \
  -F "language=zh"

# NodePilot 主後端整合測試
curl -X POST "http://127.0.0.1:8000/voxtral/audio/process" \
  -H "Content-Type: application/json" \
  -d '{"audio_data": "base64_audio", "mode": "transcribe", "output_language": "zh"}'

# 成功測試多層級 Voxtral 音頻處理 API (舊版)
curl -X POST "http://127.0.0.1:8000/api/v1/multi-agent/generate-teaching-integrated" \
  -F "audio_file=@test_audio.wav" \
  -F "confusion_note=我需要理解Python的類別概念"
# 處理流程: 嘗試遠端 RTX 3080 → 本地 Replicate → Whisper 備案
# 回應: 完整學習筆記 (含 bullet points + 語意分析)
```

**🔄 待測試 (切換 RTX 3080 電腦後):**
```bash
# 測試遠端 RTX 3080 Voxtral Q4 推理
export VOXTRAL_REMOTE_API_URL="https://xxx.ngrok.io"
export VOXTRAL_REMOTE_API_TOKEN="your_token"
# 預期: 2-3 秒處理時間，直接產生 bullet points
```

### W2 多 Agent LLM 架構實現

- [x] 9. 建立多 Agent 系統基礎架構（W2：核心架構）
  - 使用 `FastAPI + 純 Python` 避免 LangChain/CrewAI 依賴
  - 建立分層架構：API 層、服務層、Agent 層、AI 核心層
  - 實作基礎 fallback 機制和錯誤處理
  - _需求: 多 Agent 系統基礎架構_
  - _依賴: 無_
  - _輸出: 可運行的 FastAPI 後端服務_

- [x] 9.1 實作音頻處理端點和 Agent（W2：音頻標註核心）
  - 使用 `curl` 和 `multipart/form-data` 實作音頻上傳 API
  - 整合 OpenAI Whisper API 進行中文音頻轉錄
  - 實作音頻語意分析 Agent (GPT-3.5-turbo)
  - 建立檔案大小限制和格式驗證 (20MB, WAV/MP3/M4A)
  - 實作完整音頻標註流程：上傳 → 轉錄 → 語意分析 → 內容整合
  - _需求: 音頻困惑標註功能_
  - _依賴: 9 (基礎架構)_
  - _輸出: `/api/v1/multi-agent/generate-teaching-integrated` 端點可用_

- [x] 9.2 實作多模態內容整合（W2：教學內容生成）
  - 整合文字標註 + 音頻轉錄 + 語意分析結果
  - 生成結構化學習筆記（Markdown 格式）
  - 實作用戶上下文感知（困惑筆記、選取文字、頁面標題）
  - 建立音頻語意分析輸出格式：困惑點、學習意圖、情緒狀態、建議教學方式
  - _需求: 個人化教學內容生成_
  - _依賴: 9.1 (音頻處理)_
  - _輸出: 完整的教學筆記生成功能_

- [ ] 9.3 實作任務規劃 Agent（GPT-4o/Claude 3.5）（W2：即時智慧規劃）
  - 整合 GPT-4o / Claude 3.5 Sonnet 作為任務規劃大腦（開發階段用 API）
  - 設計 prompt template 將用戶困惑轉為結構化 Todo List
  - 實作即時觸發機制：用戶標註時立即啟動規劃流程
  - 建立 o1-preview 思維模型作為 fallback 備援機制
  - 實作並行任務調度和優先級動態調整
  - _需求: 即時任務分解和智慧規劃_
  - _依賴: 9 (調度系統)_
  - _輸出: Agent 實作完成_

- [ ] 9.4 實作文章上下文分析 Agent（W2：無 RAG 上下文理解）
  - 實作智能段落提取算法，無需向量搜索
  - 建立文章結構樹狀分析：標題、段落、程式碼塊層級關係
  - 設計動態上下文範圍調整機制（選取文字前後 3-10 段落）
  - 建立與音訊困惑內容的語意相關性分析
  - 實作文章主題和概念關係圖譜生成
  - _需求: 高效上下文提取和分析（無向量化需求）_
  - _依賴: 9 (調度系統)_
  - _輸出: Agent 實作完成_

- [ ] 9.5 實作進階音頻語意結構化 Agent（W2：音訊理解增強）
  - ✅ **已完成**: GPT-3.5-turbo 基礎音頻語意分析實作
  - ✅ **已完成**: 困惑點結構化分析 (structured_confusion, learning_intent)
  - ✅ **已完成**: 情緒狀態分析和教學建議生成
  - 進階功能：困惑類型自動分類和品質評估機制
  - 進階功能：用戶表達習慣學習和個人化分析
  - _需求: 深度音訊語意理解_
  - _依賴: 9.1 (音頻處理基礎)_
  - _輸出: 進階語意分析 Agent 完成_

- [x] 9.9 Voxtral Mini 3B Q4 ONNX 微服務架構（W2：本地 GPU 語音推理）
  - ✅ 部署 Voxtral Mini 3B Q4 ONNX 模型至 RTX 3080 Docker 容器
  - ✅ 建立完整三階段 ONNX Pipeline：audio_encoder → embed_tokens → decoder
  - ✅ 實作 GPU 加速推理（CUDA 12.2 + CUDAExecutionProvider）
  - ✅ 修復 librosa → onnxruntime 依賴衝突導致的 GPU 問題  
  - ✅ 實作完整生成循環：prefill + decode 階段，支援 30層解碼器
  - ✅ 整合 tokenizer.json 正確解碼 Token IDs → 文字輸出
  - ✅ 建立 FastAPI 微服務端點：`/inference` 和 `/inference/upload`
  - ✅ **成功驗證**：中文語音轉錄準確，推論速度快（~2-5秒）
  - ✅ 建立前端測試頁面：`voxtral-voice.html`，支援即時錄音和檔案上傳
  - _需求: 本地 GPU 語音推理，為 QNN 轉換做準備_  
  - _依賴: 9.1 (音頻處理基礎)_
  - _輸出: **完整 Voxtral Q4 微服務就緒** → 中文轉錄驗證成功_

- [x] 9.10 Voxtral Q4 微服務整合與前端測試（W2：端到端語音服務）
  - ✅ 修復前端 API 端點配置錯誤（501 Unsupported method）
  - ✅ 整合 Docker 服務與測試頁面：`localhost:8001` ↔ `localhost:3000`
  - ✅ 解決 tokenizer.json 缺失導致的解碼問題
  - ✅ 實作音頻格式適配：webm/mp3/wav → 16kHz 重採樣
  - ✅ 建立音頻預覽和錄音回放功能
  - ✅ **測試驗證**：前端語音錄音 → Docker GPU 推理 → 中文轉錄成功
  - ✅ 效能表現：推論速度快，音質清晰，轉錄準確率高
  - ✅ 更新 Dockerfile 確保 tokenizer 正確下載  
  - _需求: 端到端語音服務驗證_
  - _依賴: 9.9 (Voxtral 微服務)_
  - _輸出: **語音轉錄服務完全就緒** → 可整合至 NodePilot 主系統_

- [ ] 9.11 NodePilot 主系統整合 Voxtral 微服務（W2：系統整合）
  - 實作 NodePilot 後端的 Voxtral 客戶端：調用 `localhost:8001` 微服務
  - 更新現有音頻處理端點：優先使用本地 Voxtral，Whisper 作備案
  - 實作微服務健康檢查和自動降級機制
  - 整合前端 WXT 擴充插件與 Voxtral 微服務 API  
  - 驗證端到端流程：瀏覽器錄音 → NodePilot 後端 → Voxtral 微服務 → 轉錄結果
  - 效能優化：快取機制、並發請求處理、錯誤重試
  - _需求: Voxtral 微服務整合至完整系統_
  - _依賴: 9.10 (Voxtral 微服務就緒)_
  - _輸出: **完整語音轉錄系統** → 可投入生產使用_

- [ ] 9.6 實作筆記檢索 Agent（W2：RAG 知識庫整合）
  - 建立 Obsidian 筆記 RAG 向量資料庫檢索系統
  - 整合高品質 Embedding 模型：OpenAI text-embedding-3-large / Voyage AI
  - 實作基於困惑語意的相關筆記智慧搜尋
  - 建立筆記內容與當前學習脈絡的關聯性分析
  - 實作歷史學習記錄和困惑解決模式檢索
  - _需求: 個人知識庫 RAG 智慧整合_
  - _依賴: 9 (調度系統)_
  - _輸出: RAG Agent 實作 → API 串接端點_

- [ ] 9.7 實作教學內容生成 Agent（W2：Artifacts 可視化教學）
  - 整合 Claude 4.0 Sonnet / GPT-5 作為主要教學生成模型
  - 設計多維度上下文整合 prompt：文章+音訊+筆記+困惑分類
  - 實作 Artifacts 輸出畫布：HTML 可視化教學、互動式範例、圖表生成
  - 建立教學內容多層次驗證：準確性+相關性+實用性+可視化效果
  - 實作教學難度和呈現方式自動調整（基於音訊表達的理解程度）
  - _需求: Artifacts 可視化個人化教學生成_
  - _依賴: 9.1-9.4 (所有 Agent 結果)_
  - _輸出: 教學內容生成 Agent 完成_

- [ ] 9.8 實作進階結果整合與格式化模組（W2：輸出優化）
  - 設計 Python 邏輯整合所有 Agent 執行結果
  - 實作 LLM 輔助的內容格式化和結構化
  - 建立教學內容的 Markdown 渲染和程式碼高亮
  - 實作多 Agent 結果的一致性檢查和衝突解決
  - 建立使用者友善的錯誤處理和部分失敗降級策略
  - _需求: 統一輸出格式和品質保證_
  - _依賴: 9.1-9.5 (所有 Agent 結果)_
  - _輸出: 整合模組完成 → API 接口 → 前端 UI 顯示_

### W2 Reader 功能實作

- [x] 8. 實作 Content Script 內容擷取功能（W2：Reader 基礎）**【EXT】**
  - 建立智慧文章內容擷取算法，自動識別主文章區域
  - 實作圖片 URL 處理，將相對路徑轉換為絕對路徑
  - 建立廣告和干擾元素過濾機制（導航、側邊欄、footer）
  - 實作 Readwise 風格頂部橫槓設計，點擊擴充套件圖示顯示
  - 建立內容擷取結果的預覽和確認機制
  - _需求: 5.1 (內容擷取功能)_
  - _依賴: 2.2 (WXT Content Script 架構)_
  - _輸出: Content Script 擷取功能完成_

- [ ] 8.1 建立後端 Reader 內容處理 API（W2：Reader 後端）**【API】**
  - 實作 `POST /extract-content` 端點進行伺服器端內容清理
  - 建立內容清理服務：HTML sanitization 和格式優化
  - 實作閱讀時間預估算法（基於字數和複雜度）
  - 建立 Reader 內容的 SQLite 存儲和檢索功能
  - 實作內容重複檢查機制，避免重複擷取同一文章
  - _需求: 5.1, 5.2 (Reader API 和資料存儲)_
  - _依賴: 3 (FastAPI 後端服務)_
  - _輸出: Reader API 端點完成_

- [x] 8.2 建立 WXT Reader Tab 頁面（W2：Reader UI）**【EXT】**
  - 使用 `browser.tabs.create()` 建立獨立的 Reader Tab 頁面
  - 實作暗黑模式和淺色模式的切換功能
  - 建立適合閱讀的字體排版和響應式設計
  - 實作閱讀進度指示器和滾動位置記憶
  - 建立快捷鍵支援（ESC 返回、Ctrl+D 模式切換）
  - _需求: 5.2, 5.4 (Reader 頁面和使用體驗)_
  - _依賴: 8.1 (Reader API)_
  - _輸出: Reader Tab 頁面完成_

- [x] 8.3 整合標註功能到 Reader（W2：Reader 標註）**【EXT】**
  - 在 Reader 頁面中注入文字選取和標註功能
  - 實作螢光筆標記的視覺效果和持久化存儲
  - 整合現有的 AI 教學生成功能到 Reader
  - 建立 Reader 和原網頁標註資料的統一管理
  - 實作標註在 Reader 中的快速檢視和編輯功能
  - _需求: 5.3 (標註功能整合)_
  - _依賴: 8.2 (Reader Tab)，9.2 (AI 教學生成)_
  - _輸出: Reader 標註功能完成_

- [x] 8.0 Reader 功能完整實作（W2：Readwise 風格 Reader）**【EXT】**
  - ✅ 實作 Readwise 風格擴充套件圖示點擊觸發機制
  - ✅ 建立黑色頂部橫槓設計，包含 NodePilot Logo 和 "Open in Reader" 按鈕
  - ✅ 整合智慧內容擷取算法，自動過濾廣告和干擾元素
  - ✅ 建立暗黑模式 Reader 頁面，支援字體調整和快捷鍵
  - ✅ 整合完整標註功能，支援文字選取和 AI 教學生成
  - ✅ 實作頁面適配機制，避免內容被橫槓遮擋
  - _需求: 5.1, 5.2, 5.3, 5.4 (完整 Reader 功能)_
  - _依賴: WXT Framework + React + TypeScript 架構_
  - _輸出: 完整 Readwise 風格 Reader 功能，可投入測試使用_

- [ ] 8.4 Reader 體驗優化和測試（W2：Reader 完善）**【EXT → API】**
  - 優化內容載入速度和渲染效能
  - 實作內容擷取準確率測試和品質評估
  - 建立不同網站的擷取策略適配機制
  - 實作錯誤處理和降級方案（擷取失敗時的處理）
  - 進行跨瀏覽器相容性測試和優化
  - _需求: 5.4 (使用體驗)_
  - _依賴: 8.3 (Reader 標註功能)_
  - _輸出: Reader 功能測試完成 → 可用於生產環境_

### W2 系統整合與優化

- [ ] 10. 建立可切換模型架構和 Fallback 系統（W2：系統穩健性）**【AI-CORE → API】**
  - 實作模型配置管理：主要模型 + 多層備援機制
  - 建立模型效能監控和自動切換邏輯
  - 實作 API 限額管理和成本控制機制
  - 設計本地模型備援選項（本地 Whisper、Llama 70B）
  - 建立模型回應品質評估和模型選擇優化
  - _需求: 系統可靠性和成本效益_
  - _依賴: 9.1-9.6 (所有 Agent 完成)_
  - _輸出: 模型管理系統 → API 配置介面_

- [ ] 10.1 實作 Side Panel 多 Agent 協作介面（W2：前端整合）**【EXT】**
  - 建立 Side Panel 顯示多 Agent 執行進度和狀態
  - 實作困惑列表與 Agent 分析結果的關聯顯示
  - 設計 Agent 協作過程的視覺化呈現
  - 實作用戶對 Agent 結果的反饋和調整機制
  - 建立多 Agent 教學結果的比較和選擇介面
  - _需求: 透明化 AI 協作過程_
  - _依賴: 9.6 (結果整合模組)_
  - _輸出: Side Panel UI 完成_

- [ ] 10.2 實作螢光筆標註交互優化（W2：用戶體驗改善）**【EXT】**
  - ✅ **已完成**: 基礎螢光筆標記功能（選取文字自動高亮）
  - ✅ **已完成**: 標註成功提示和側邊欄記錄顯示
  - 實作螢光筆點擊彈窗顯示 bullet points 學習重點
  - 設計簡潔的學習重點顯示介面（3-5個要點）
  - 實作重點標記的學習狀態更新機制
  - 建立標註歷史的快速檢視功能
  - 優化標註 UI 的視覺回饋和動畫效果
  - _需求: Readwise 風格的標註體驗_
  - _依賴: 9.9 (Voxtral bullet points 生成)_
  - _輸出: 優化的標註交互體驗完成_

- [x] 2.1 建立 React 狀態管理和通信機制（W1：Extension 核心）
  - 實作 React Context 全域狀態管理 (useNodePilotContext)
  - 建立 Content Script 與 Background Script 的 Chrome Messaging
  - 實作標註資料的 TypeScript 型別定義和驗證
  - 設定 React Error Boundary 和錯誤處理
  - _需求: 2.2, 2.7_

- [x] 2.2 修正 WXT React Content Script 架構（W1：架構優化）
  - 使用 `createShadowRootUi` 取代直接 ReactDOM 注入
  - 實作 WXT 推薦的 Shadow DOM 樣式隔離
  - 配置 `cssInjectionMode: 'ui'` 正確載入樣式
  - 建立 Background Script 作為 Popup-Content 通信中介
  - _需求: 2.1, 2.6_

- [x] 3. 建立 FastAPI 後端服務（W1：API 開發）
  - 實作 `POST /generate-teaching` API 端點，接收標註資料
  - 建立 CORS 配置，允許 Chrome Extension 跨域請求
  - 實作請求驗證和錯誤處理機制
  - 建立 `GET /annotations` 和 `PUT /annotations/{id}/status` API
  - _需求: 1.4, 1.5_

- [x] 3.1 實作標註立即存儲 API（W1：階段一實現）
  - 建立 `POST /annotations` 端點支援立即標註存儲
  - 更新 SQLite schema 添加 audio_transcription, cognitive_note 欄位
  - 實作音檔上傳整合到標註端點（multipart/form-data）
  - 實作標註狀態管理 (unknown/learning/understood)
  - **立即處理流程**：接收音檔 → Whisper 轉錄 → 認知記錄生成 → 存儲
  - _需求: 2.5, 2.6_

- [x] 3.2 實作音檔暫存與處理機制（W1：音檔基礎設施）
  - 建立音檔暫存機制使用 tempfile 模組，設定 24 小時自動清理
  - 實作音檔格式驗證（webm, mp4, mpeg）和大小限制（≤20MB）
  - 實作音檔配額管理，限制暫存總大小 ≤500MB
  - 建立音檔清理排程和錯誤恢復機制
  - _需求: 2.6_

- [x] 3.3 整合 Whisper API 立即轉錄（W1：即時 AI 轉錄）
  - 整合 OpenAI Whisper API，設定中文語言參數和即時處理
  - 實作「標註困惑」觸發的立即轉錄功能
  - 實作重試機制和錯誤處理（網路超時、API 限制）
  - 建立轉錄結果暫存，避免重複調用 API
  - **關鍵**：用戶點擊「標註困惑」立即觸發 Whisper API
  - _需求: 2.6_

- [x] 3.4 實作認知記錄立即生成（W1：即時認知分析）
  - 建立認知記錄生成功能整合到標註流程
  - 設計 prompt template 將音檔轉錄轉為用戶認知描述（包含 Function Calling 語意）
  - 實作 Voxtral mini 3B 備案：本地音檔轉行為語意文字
  - **整合流程**：Whisper 轉錄 → 認知記錄生成 → 立即存儲到標註
  - 實作認知記錄品質驗證和錯誤處理
  - _需求: 2.6, 4.1_

- [x] 4. 整合 OpenAI API 服務（W2：AI 教學生成）
  - 安裝和配置 OpenAI Python SDK
  - 建立 OpenAI 服務模塊，處理 API 呼叫和錯誤處理
  - 設計教學生成的 prompt template，結合選取文字、困惑描述和頁面上下文
  - 實作 API 呼叫的重試機制和速率限制
  - _需求: 3.1, 3.2_

- [x] 4.1 實作 AI 教學內容生成（含認知轉換）（W2：AI 教學生成）
  - 在 `POST /generate-teaching` 中整合 OpenAI API 調用
  - 實作 prompt 工程：結合 URL、選取文字、困惑描述、認知記錄生成個人化教學
  - 整合 Whisper API 於 `POST /transcribe-audio` 端點
  - 實作 AI 認知轉換：將音檔轉錄內容轉為用戶認知描述
  - 建立 AI 回應的格式化和 Markdown 輸出處理
  - 實作教學內容與標註的關聯存儲邏輯
  - _需求: 3.3, 3.4, 3.6_

- [x] 5. 建立 React Popup Chatbot 介面（W2：UI 完善）
  - 實作 `entrypoints/popup/index.tsx` React Chatbot 主應用
  - 建立 Tailwind CSS + 現代化聊天介面設計
  - 整合 react-markdown 支援 Markdown 和程式碼高亮渲染
  - 實作對話紀錄、使用者訊息和 AI 回應的 React 元件
  - 建立學習狀態更新的 UI 控制（emoji 按鈕：😕/📚/✅）
  - _需求: 3.7_

- [ ] 5.1 實作標註歷史管理（W2：UI 完善）**【EXT】**
  - 在 Popup 中建立標註歷史列表顯示
  - 實作標註狀態的視覺化和互動更新
  - 建立標註與原網頁的關聯顯示（URL、標題）
  - 實作簡單的搜尋和篩選功能
  - _需求: 2.7, 4.4, 4.5_
  - _依賴: 3 (API 端點)_
  - _輸出: 標註歷史 UI 完成_

- [ ] 6. 實作學習狀態管理系統（W2：狀態追蹤）
  - 建立學習狀態轉移邏輯 (unknown → learning → understood)
  - 實作狀態更新的 API 端點和前端 UI
  - 建立學習進度統計和顯示功能
  - 實作狀態變更的持久化存儲
  - _需求: 4.1, 4.2, 4.3, 4.4, 4.5_

- [ ] 7. 端到端測試與優化（W2：系統整合）
  - 建立完整使用者流程測試：manus.im 文字選取 → 困惑描述 → AI 教學生成
  - 驗證核心價值假設：個人化困惑描述的教學效果
  - 測試 Chrome Extension 的安裝、權限和功能完整性
  - 收集內部測試回饋並進行 UI/UX 優化
  - _需求: 所有需求的整合驗證_

- [ ] 7.1 效能優化與錯誤處理（W2：系統整合）
  - 優化 OpenAI API 呼叫的效率和錯誤處理
  - 實作 Extension 的離線狀態處理和重連機制
  - 建立全面的錯誤處理和使用者友善的錯誤訊息
  - 實作基礎的快取機制（Extension Storage API）
  - _需求: 所有需求的效能和穩定性_

- [ ] 7.2 建立部署配置與文件（W2：系統整合）
  - 建立 Chrome Extension 的打包和發佈配置
  - 撰寫使用者安裝和使用指南
  - 建立開發者 API 文件和技術說明
  - 設定後端 API 的部署環境和健康檢查
  - _需求: 所有需求的部署和維護_

## 關鍵驗收指標

### 技術指標
- Chrome Extension 在 manus.im 正常載入和運作
- 文字選取和標註功能準確性 ≥ 95%
- AI 教學生成回應時間 ≤ 15 秒
- Extension 安裝和使用無阻塞錯誤

### 價值驗證指標（核心）
- **AI 生成教學內容的有用性 ≥ 85%**
- **內部測試者認為比 Google 搜尋更有幫助**
- 新使用者能在 3 分鐘內完成首次標註和 AI 教學獲取
- ≥ 70% 的困惑描述能成功生成有用的教學內容

### 使用者體驗指標
- 標註操作流程 ≤ 3 次點擊
- Extension Popup 載入時間 ≤ 2 秒
- 學習狀態更新即時性和準確性

## 技術風險與應對

### 高風險項目
1. **OpenAI API 限制/成本** → 設定使用限制、監控用量、實作 API Key 輪換
2. **Chrome Extension 權限和安全** → 最小權限原則、內容安全政策
3. **文字選取在複雜網頁中的準確性** → 多重選取策略、容錯處理

### 中風險項目
1. **AI 教學品質不穩定** → 持續 prompt 調整、建立品質評估機制
2. **Extension 與網站衝突** → 命名空間隔離、CSS 樣式優先級管理
3. **跨瀏覽器相容性** → 優先支援 Chrome，後續擴展

## Chrome Extension 開發重點

### Manifest V3 配置
```json
{
  "manifest_version": 3,
  "name": "NodePilot Learning Assistant",
  "version": "1.0",
  "permissions": ["storage", "activeTab"],
  "content_scripts": [{
    "matches": ["https://manus.im/blog/*"],
    "js": ["content-script.js"],
    "css": ["styles.css"]
  }],
  "background": {
    "service_worker": "background.js"
  },
  "action": {
    "default_popup": "popup.html"
  }
}
```

### 安全和隱私考量
- 僅在白名單網站運作
- 本地存儲敏感標註資料
- HTTPS 強制使用
- 最小化資料收集

## 後續迭代計畫

### Phase 2 (Week 3-4) - 功能增強
- 音檔標註功能完整實作（Whisper API + 認知轉換）
- 純文本閱讀器開發（參考 Readwise OpenReader）
- 批次標註和教學生成功能
- 學習進度分析和統計

### Phase 3 (Month 2) - 技術升級
- Voxtral mini 3B 本地音檔理解（備案方案）
- 本地 AI 模型整合選項
- 向量搜尋改善教學品質
- 多瀏覽器支援（Firefox, Edge）

### Phase 4 (Month 3+) - 高級功能
- 社群分享學習筆記
- 個人化學習路徑推薦
- 與筆記應用整合（Obsidian, Notion）
- 進階音檔功能和認知分析