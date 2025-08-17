## **NodePilot.ai Git 版本控管規則（Worktree + AI Coding 優化）**

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

## 🌲 Worktree 管理結構

### 目錄配置
```
nodepilot.ai/                    # 主倉庫 (main 分支)
├── .git/
├── spec_docs/
├── CLAUDE.md
└── README.md

../nodepilot-worktrees/          # Worktree 工作區
├── dev/                         # dev 分支
├── feature-extension/           # Chrome Extension 開發
├── feature-api/                 # FastAPI 後端開發
└── feature-integration/         # 整合測試
```

### Worktree 建立指令
```bash
# 建立新功能分支 worktree
git worktree add ../nodepilot-worktrees/feature-<module> -b feature/<module>

# 範例
git worktree add ../nodepilot-worktrees/feature-extension -b feature/extension
git worktree add ../nodepilot-worktrees/feature-api -b feature/api
```

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
# 檢查所有 worktree 狀態
git worktree list --porcelain

# 快速 diff 摘要 (供 AI 分析)
git diff --stat origin/dev
git log --oneline --graph origin/dev..HEAD -10
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

## 🛠 Worktree 開發流程

### 1. 建立 Worktree 開發環境
```bash
# 建立功能分支 worktree
git worktree add ../nodepilot-worktrees/feature-extension -b feature/extension

# 切換到工作目錄
cd ../nodepilot-worktrees/feature-extension
```

### 2. AI Coding 工作流程  
```bash
# AI 開始工作前必須檢查
git status --porcelain
git diff origin/dev --stat

# 開發與提交
git add .
git commit -m "[extension] add: content script for text selection"

# 與最新 dev 同步
git fetch origin
git rebase origin/dev
```

### 3. 整合回主倉庫
```bash
# 切回主倉庫
cd ../../nodepilot.ai

# 檢查並合併 (由專案管理人執行)
git checkout dev
git merge feature/extension
git push origin dev
```

### 4. 清理 Worktree
```bash
# 移除已完成的 worktree
git worktree remove ../nodepilot-worktrees/feature-extension
git branch -d feature/extension
```
    

---

## **🙅‍♂️ 禁忌事項**

- ❌ 不要直接在 main 或 dev 上開發
    
- ❌ 不要對 main 使用 force push
    
- ❌ 不要直接動別人的分支，請先溝通
    
- ❌ 不接受亂寫 commit message（請依規範）