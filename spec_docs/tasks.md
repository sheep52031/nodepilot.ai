# NodePilot V6 MVP 實作計畫

## MVP 核心目標

驗證「個人化困惑描述 + 文章上下文」比「直接 Google 搜尋」產生更好學習效果的核心價值假設。

## 技術架構：Chrome Extension + FastAPI

- 前端: Chrome Extension (Content Script + Background + Popup)
- 後端: FastAPI + SQLite 
- AI: OpenAI API
- 白名單: 僅限 https://manus.im/blog/*

## 實作任務清單

- [x] 1. 建立 WXT + React 專案基礎架構（W1：基礎環境）
  - 使用 `npm create wxt@latest nodepilot-extension -- --template react` 建立 WXT React 專案
  - 配置 `wxt.config.ts` 支援 TypeScript + Tailwind CSS + React 18
  - 設定專案結構：entrypoints/, components/, hooks/, utils/
  - 配置 Manifest V3 和 manus.im 白名單權限
  - 設定開發環境和 HMR 熱重載
  - _需求: 1.1, 1.2_

- [ ] 1.1 建立後端 API 專案（W1：基礎環境）
  - 使用 `uv init nodepilot-api` 建立 Python FastAPI 專案資料夾結構
  - 在 pyproject.toml 中定義 FastAPI、SQLite、OpenAI、CORS 等依賴
  - 使用 `uv venv` 建立虛擬環境，並用 `uv sync` 同步依賴套件
  - 設定 `.env` 環境變數管理 (OPENAI_API_KEY 等)
  - _需求: 1.1, 1.2_

- [ ] 1.2 設定 SQLite 資料庫結構（W1：基礎環境）
  - 建立 `database.py` 和 SQLAlchemy 模型定義
  - 實作 annotations 資料表 schema (url, selected_text, confusion_note, teaching_content, status)
  - 建立資料庫初始化和遷移腳本
  - 設定資料庫連接和基礎 CRUD 操作
  - _需求: 1.3_

- [ ] 2. 實作 React Content Script 標註功能（W1：Extension 核心）
  - 建立 `entrypoints/content/index.tsx` React 元件注入功能
  - 使用 WXT Shadow DOM API 實作文字選取事件監聽
  - 建立 React 標註 UI 元件和困惑輸入表單
  - 實作選取文字高亮和位置記錄的 React Hook
  - _需求: 2.1, 2.6_

- [ ] 2.1 建立 React 狀態管理和通信機制（W1：Extension 核心）
  - 實作 React Context 全域狀態管理 (useNodePilotContext)
  - 建立 Content Script 與 Background Script 的 Chrome Messaging
  - 實作標註資料的 TypeScript 型別定義和驗證
  - 設定 React Error Boundary 和錯誤處理
  - _需求: 2.2, 2.7_

- [ ] 3. 建立 FastAPI 後端服務（W1：API 開發）
  - 實作 `POST /generate-teaching` API 端點，接收標註資料
  - 建立 CORS 配置，允許 Chrome Extension 跨域請求
  - 實作請求驗證和錯誤處理機制
  - 建立 `GET /annotations` 和 `PUT /annotations/{id}/status` API
  - _需求: 1.4, 1.5_

- [ ] 3.1 實作標註存儲與管理（W1：API 開發）
  - 建立標註資料的存儲邏輯到 SQLite
  - 實作標註狀態管理 (unknown/learning/understood)
  - 建立標註歷史查詢和篩選功能
  - 實作資料驗證和安全檢查
  - _需求: 2.4, 2.5, 4.1_

- [ ] 4. 整合 OpenAI API 服務（W2：AI 教學生成）
  - 安裝和配置 OpenAI Python SDK
  - 建立 OpenAI 服務模塊，處理 API 呼叫和錯誤處理
  - 設計教學生成的 prompt template，結合選取文字、困惑描述和頁面上下文
  - 實作 API 呼叫的重試機制和速率限制
  - _需求: 3.1, 3.2_

- [ ] 4.1 實作 AI 教學內容生成（W2：AI 教學生成）
  - 在 `POST /generate-teaching` 中整合 OpenAI API 調用
  - 實作 prompt 工程：結合 URL、選取文字、困惑描述生成個人化教學
  - 建立 AI 回應的格式化和 Markdown 輸出處理
  - 實作教學內容與標註的關聯存儲邏輯
  - _需求: 3.3, 3.4, 3.6_

- [ ] 5. 建立 React Popup Chatbot 介面（W2：UI 完善）
  - 實作 `entrypoints/popup/index.tsx` React Chatbot 主應用
  - 建立 Tailwind CSS + 現代化聊天介面設計
  - 整合 react-markdown 支援 Markdown 和程式碼高亮渲染
  - 實作對話紀錄、使用者訊息和 AI 回應的 React 元件
  - 建立學習狀態更新的 UI 控制（emoji 按鈕：😕/📚/✅）
  - _需求: 3.7_

- [ ] 5.1 實作標註歷史管理（W2：UI 完善）
  - 在 Popup 中建立標註歷史列表顯示
  - 實作標註狀態的視覺化和互動更新
  - 建立標註與原網頁的關聯顯示（URL、標題）
  - 實作簡單的搜尋和篩選功能
  - _需求: 2.7, 4.4, 4.5_

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
- 擴展支援更多技術網站（白名單）
- 批次標註和教學生成功能
- 學習進度分析和統計

### Phase 3 (Month 2) - 技術升級
- 本地 AI 模型整合選項
- 向量搜尋改善教學品質
- 多瀏覽器支援（Firefox, Edge）

### Phase 4 (Month 3+) - 高級功能
- 社群分享學習筆記
- 個人化學習路徑推薦
- 與筆記應用整合（Obsidian, Notion）