# Voxtral Mini 3B Q4 推理服務

獨立的 Voxtral ONNX Q4 量化模型推理微服務，與 NodePilot 主後端分離。

## 🎯 功能特性

- **Q4 量化模型**：使用 ONNX 社群的 Q4 量化版本
- **GPU 加速**：支援 NVIDIA RTX 3080 CUDA 推理
- **多種任務**：語音轉錄、總結、描述、問答
- **REST API**：提供標準 HTTP 接口
- **Docker 部署**：完全容器化，易於部署

## 🚀 快速啟動

### 1. 構建並啟動服務

```bash
cd /home/jaren/nodepilot.ai/voxtral-inference-service
docker-compose up --build -d
```

### 2. 檢查服務狀態

```bash
curl http://localhost:8001/health
curl http://localhost:8001/model/info
```

### 3. 測試音頻推理

```bash
# 上傳音頻檔案
curl -X POST "http://localhost:8001/inference/upload" \
  -F "file=@/path/to/audio.wav" \
  -F "task=transcribe" \
  -F "language=zh"

# Base64 音頻推理
curl -X POST "http://localhost:8001/inference" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_data": "base64_encoded_audio",
    "task": "summarize",
    "language": "zh"
  }'
```

## 📡 API 端點

| 端點 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 服務資訊 |
| `/health` | GET | 健康檢查 |
| `/model/info` | GET | 模型資訊 |
| `/inference` | POST | 音頻推理 (Base64) |
| `/inference/upload` | POST | 音頻推理 (檔案上傳) |
| `/docs` | GET | API 文檔 |

## 🎭 支援任務

- **transcribe**: 語音轉錄
- **summarize**: 中文總結
- **describe**: 音頻描述
- **qa**: 問答分析

## 🌐 語言支援

- **zh**: 中文
- **en**: English
- **auto**: 自動檢測
- 其他：es, fr, pt, hi, de, nl, it

## 🔧 環境需求

- **GPU**: NVIDIA RTX 3080 (8GB VRAM)
- **CUDA**: 12.2+
- **cuDNN**: 9.x
- **Docker**: 支援 GPU
- **Python**: 3.10+

## 📊 性能指標

- **模型大小**: ~3GB (Q4 量化)
- **VRAM 使用**: ~4-6GB
- **推理速度**: 實時 (RTX 3080)
- **支援長度**: 最長 40 分鐘音頻

## 🔗 與 NodePilot 整合

NodePilot 主後端透過 HTTP 調用此服務：

```python
import httpx

async def call_voxtral_inference(audio_base64: str, task: str = "transcribe"):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/inference",
            json={
                "audio_data": audio_base64,
                "task": task,
                "language": "zh"
            }
        )
        return response.json()
```

## 🐳 Docker 指令

```bash
# 構建
docker-compose build

# 啟動
docker-compose up -d

# 查看日誌
docker-compose logs -f

# 停止
docker-compose down

# 重啟
docker-compose restart
```

## 📋 日誌監控

```bash
# 即時日誌
docker-compose logs -f voxtral-inference

# 檢查 GPU 使用
nvidia-smi

# 檢查容器狀態
docker-compose ps
```

## 🚢 部署到高通筆電

1. **轉換模型格式**：Q4 ONNX → QNN
2. **修改 Dockerfile**：使用高通 SDK
3. **調整配置**：CPU/NPU 推理
4. **性能測試**：確認推理速度

## ⚠️ 注意事項

- 首次啟動會下載模型檔案 (~3GB)
- 需要 NVIDIA Container Toolkit
- 確保 8001 端口未被佔用
- GPU 記憶體充足 (建議 8GB+)