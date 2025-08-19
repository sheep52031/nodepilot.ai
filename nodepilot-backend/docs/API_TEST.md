# NodePilot API 測試指南

## 啟動後端服務

```bash
cd /home/jaren/nodepilot-worktrees/feature-api/nodepilot-api
uv run python main.py
```

服務將運行在 http://127.0.0.1:8000

## API 端點測試

### 1. 建立標註（文字）

```bash
curl -X POST "http://127.0.0.1:8000/annotations" \
  -F "url=https://example.com" \
  -F "selected_text=test code" \
  -F "confusion_note=I don't understand this" \
  -F "page_title=Test Page"
```

### 2. 建立標註（含音檔）

```bash
# 需要有實際音檔文件
curl -X POST "http://127.0.0.1:8000/annotations" \
  -F "url=https://example.com" \
  -F "selected_text=test code" \
  -F "confusion_note=I don't understand this" \
  -F "page_title=Test Page" \
  -F "audio_file=@recording.webm"
```

### 3. 獲取標註列表

```bash
curl "http://127.0.0.1:8000/annotations"
```

### 4. 更新標註狀態

```bash
curl -X PUT "http://127.0.0.1:8000/annotations/1/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "learning"}'
```

### 5. 生成教學內容

```bash
curl -X POST "http://127.0.0.1:8000/generate-teaching" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "selected_text": "test code", 
    "confusion_note": "I dont understand this"
  }'
```

## 音檔上傳要求

- **支援格式**: webm, mp4, mpeg, wav
- **檔案大小**: ≤ 20MB
- **處理流程**: 音檔 → Whisper 轉錄 → 認知記錄生成 → 存儲

## API 回應格式

```json
{
  "id": 1,
  "url": "https://example.com", 
  "selected_text": "test code",
  "confusion_note": "I don't understand this",
  "audio_transcription": "這是我的困惑描述...",
  "cognitive_note": "用戶對於程式碼執行流程感到困惑...",
  "teaching_content": null,
  "page_title": "Test Page",
  "status": "unknown",
  "created_at": "2025-08-18T07:45:47",
  "updated_at": null
}
```

## 前端整合說明

前端 `createAnnotation` 函數可直接調用 POST /annotations API：

```typescript
const response = await fetch('http://127.0.0.1:8000/annotations', {
  method: 'POST',
  body: formData, // 包含音檔的 FormData
});
```