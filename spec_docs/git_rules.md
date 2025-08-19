## **NodePilot.ai Git 版本控管規則（單一 Terminal + Sub-Agent 開發）**

**專案倉庫**: https://github.com/sheep52031/nodepilot.ai  
**專案管理人**: sheep52031

---

## 🔐 main 分支
- `main` 是穩定可部署的版本
- ❌ 禁止直接在 `main` 上開發或推送（包含 `force push`）
- ✅ 僅由專案管理人從 `dev` 合併穩定版本

---

## 🧪 dev 分支  
- `dev` 是整合分支，用來協作與測試
- ❌ 不要在 `dev` 上直接開發
- ✅ 從 `dev` 建立功能分支進行開發
- ✅ 整合前請先 `git pull` 最新的 `dev`
- ✅ 由專案管理人負責合併回 `dev`

---

## 🤖 主要開發分支架構

### 分支配置
```
nodepilot.ai/                    # 主倉庫目錄
├── main                         # 穩定版本分支
├── dev                          # 開發整合分支
├── feature/main-ai-agent        # 主要 AI 開發分支（目前使用）
├── feature/extension            # Chrome Extension 功能分支
├── feature/api                  # FastAPI 後端功能分支
└── feature/ai-core              # AI 核心系統功能分支
```

### AI Agent 開發模式
- **單一 Terminal 開發**: 在 `feature/main-ai-agent` 分支進行統一開發
- **Sub-Agent 分工**: 使用專業化 Sub-Agent 處理不同領域的任務
  - `tech-doc-researcher`: 技術文檔查詢和框架研究
  - `browser-debug-specialist`: 瀏覽器擴充插件調試
  - `dev-env-installer`: 開發環境設置和依賴安裝

---

## 🔧 功能分支命名規則

命名方式：
```
feature/<功能模組>
```

📦 範例：
- `feature/extension` - Chrome Extension 開發
- `feature/api` - FastAPI 後端開發  
- `feature/integration` - 系統整合測試

### AI Coding 專用分支
- `feature/main-ai-agent` - 主要 AI 開發分支（當前使用）
- `feature/ai-tasks` - AI 實作 tasks.md 指定任務  
- `feature/ai-fixes` - AI 修復和優化

---

## 🤖 AI Coding Diff 檢查規範

### 必須執行的 Diff 檢查順序
1. **當前狀態**: `git status --porcelain`
2. **vs dev 分支**: `git diff origin/dev --name-only`  
3. **vs main 分支**: `git diff origin/main --name-only`
4. **詳細變更**: `git diff origin/dev -- <specific_file>`

### AI 專用狀態查詢指令
```bash
# 快速 diff 摘要 (供 AI 分析)
git diff --stat origin/dev
git log --oneline --graph origin/dev..HEAD -10

# Sub-Agent 任務分派前的狀態檢查
git status --porcelain
git branch --show-current
```

---

## ✅ Commit Message 規範（建議使用）

統一格式：
```

[type] scope: 描述內容

```
📌 常用 type：
- `add`：新增功能
- `fix`：錯誤修正
- `update`：更新或重構
- `docs`：文件變動
- `refactor`：重構無行為改變
- `remove`：刪除程式碼或模組

📌 範例：
- `[mcp] fix: handle missing input`
- `[speech] add: streaming playback`
- `[docs] update: README for setup guide`

---

## 🛠 AI Agent 單一 Terminal 開發流程

### 1. 主要開發環境
```bash
# 當前主要開發分支
git checkout feature/main-ai-agent

# 確認工作目錄
pwd  # /Users/jason/Developer/nodepilot.ai
```

### 2. AI Coding 工作流程  
```bash
# AI 開始工作前必須檢查
git status --porcelain
git diff origin/dev --stat

# Sub-Agent 任務分工開發
# - tech-doc-researcher: 查詢 WXT 框架文檔
# - browser-debug-specialist: 調試擴充插件問題  
# - dev-env-installer: 設置開發環境

# 開發與提交
git add .
git commit -m "[main-ai-agent] add: integrated multi-agent system"

# 與最新 dev 同步
git fetch origin
git rebase origin/dev
```

### 3. 整合回主倉庫
```bash
# 檢查並合併到 dev (由專案管理人執行)
git checkout dev
git merge feature/main-ai-agent
git push origin dev
```

### 4. Sub-Agent 協作模式
- **並行處理**: 使用 Task 工具分派給多個 Sub-Agent 同時執行
- **專業分工**: 每個 Sub-Agent 專注於特定技術領域
- **結果整合**: 主 Agent 負責整合各 Sub-Agent 的成果
    

---

## **🙅‍♂️ 禁忌事項**

- ❌ 不要直接在 main 或 dev 上開發
    
- ❌ 不要對 main 使用 force push
    
- ❌ 不要直接動別人的分支，請先溝通
    
- ❌ 不接受亂寫 commit message（請依規範）
    
- ❌ 不要建立新的 worktree（已改用單一 Terminal + Sub-Agent 模式）