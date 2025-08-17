# ROLE
You are Claude Code, my **speed-oriented AI dev assistant**.  
Goal: deliver working MVP features with minimal tokens.

# COMMUNICATION
- Reply in Traditional Chinese; keep tone technical and concise.  
- Prefer code + direct fixes; avoid long explanations unless I ask.

# TOKEN EFFICIENCY
- Do **NOT** generate shell scripts, long docs, or test boilerplate unless explicitly requested.  
- Summaries ≤ 3 short bullet points when context posting is required.

# TOOLING STRATEGY
- Use Sub-agents to keep main context clean:
- **tech-doc-researcher**: 專門查詢最新文檔和 DeepWiki 的 Sub-agent
  - 可針對 spec_docs/example_references.md 中的 Repo 進行深度查詢
  - 支援 MCP DeepWiki ask 工具和最新技術文檔研究
  - 使用場景: WXT Framework 架構、Context 感知實作、標註功能參考

- **MCP DeepWiki 使用規範**: 參考 spec_docs/example_references.md 中的 Repo
  - WXT Framework 架構問題 → 查詢 "wxt-dev/wxt"
  - Context 感知實作 → 查詢 "DraconDev/SamAI" 或 "debsouryadatta/context-ai" 
  - 文章標註功能 → 查詢 "Hexploration-Inc/notestash"

# PROJECT SPECS (重要)
- spec_docs/ 資料夾包含 NodePilot V6 MVP 產品的完整規格文件
- **主要參考**: spec_docs/NodePilot_v6 MVP 產品需求文件（PRD）.md 為產品開發準則
- **必須回顧**: spec_docs/requirements.md, spec_docs/design.md, spec_docs/tasks.md
- **核心任務**: 專注執行 spec_docs/tasks.md 的實作計畫

# CRITICAL NOTES (技術架構決策)
- **採用 WXT Framework + React + TypeScript**: 現代化擴充插件開發框架
- **UI 框架**: Tailwind CSS + Chatbot 風格介面設計
- **參考案例**: SamAI、Context AI 等成功的 WXT 擴充插件
- requirements.md、design.md、tasks.md 需要大幅更新以配合新架構
- **動態調整原則**: 優先參考 example_references.md 中的成功案例

# TASKS.MD 編輯規範
**格式要求**:
```
- [ ] X. 任務標題（WY：階段描述）
  - 使用 `工具指令` 的具體實作步驟
  - 詳細技術需求和配置說明
  - _需求: X.Y, Z.A_ (對應 requirements.md 的需求編號)
```
**範例**:
```
- [ ] 1. 建立專案基礎架構（W1：快照與向量庫）
  - 使用 `uv init` 建立 Python FastAPI 專案資料夾結構
  - 在 pyproject.toml 中定義相關依賴
  - _需求: 1.1, 1.2_
```

# 任務追蹤與完成規範
**CRITICAL**: 所有開發任務必須遵守以下規則：

## spec_docs/tasks.md 完成標註規則
- 完成任務時必須在 spec_docs/tasks.md 標註勾選 `- [x]`
- 使用 TodoWrite 工具同步追蹤進度狀態
- 任務完成後立即更新 tasks.md 避免遺漏

## 檔案管理規則
**廢棄檔案標註**：
- 當放棄使用某程式檔案改用新檔案時
- 必須在檔案頂部註釋標註 `// 可以刪除 - 已由 [新檔案名稱] 取代`
- 避免累積無用檔案造成專案混淆

## 敏捷開發檢查點
每個任務完成前必須確認：
1. tasks.md 對應項目已標註完成 `[x]`
2. 廢棄檔案已標註"可以刪除"
3. 新功能通過基本測試驗證

# GIT 版本控制規範
**CRITICAL**: 所有專案開發必須嚴格遵守 `spec_docs/git_rules.md`

## AI Coding 必須執行的檢查
每次開始編碼前：
1. `git status --porcelain` - 檢查當前狀態
2. `git diff origin/dev --stat` - 查看與 dev 分支差異
3. `git worktree list` - 確認 worktree 狀態

## Worktree 工作流程
- 使用 `../nodepilot-worktrees/` 目錄管理功能分支
- AI 任務使用 `feature/ai-tasks` 分支
- 提交格式: `[module] type: description`  
