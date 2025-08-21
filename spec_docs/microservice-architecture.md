# NodePilot V6 微服務架構設計文件

## 概述

NodePilot V6 MVP 採用**微服務架構**，將語音推理從主後端服務中分離，實現更好的**開發靈活性**和**部署可擴展性**。此架構設計特別適合**多環境開發**場景：Linux RTX 3080 作為推理伺服器，MacBook Air 進行遠端開發。

## 🏗️ 微服務架構概覽

### 服務拆分策略

```
NodePilot 生態系統
├── 主後端服務 (NodePilot Backend)     Port 8000
│   ├── 擴充插件業務邏輯
│   ├── 多 Agent 系統調度
│   ├── 資料庫管理
│   └── 前端 API 接口
│
└── 語音推理微服務 (Voxtral Service)    Port 8001
    ├── Voxtral Mini 3B Q4 ONNX 模型
    ├── ONNX Runtime GPU 推理
    ├── 音頻預處理
    └── REST API 接口
```

### 核心設計原則

1. **服務獨立性**: 每個微服務可獨立開發、測試、部署
2. **技術異構性**: 主後端使用 uv + FastAPI，推理服務使用 Docker + PyTorch
3. **故障隔離**: 推理服務故障不影響主程式運行（備援機制）
4. **水平擴展**: 推理服務可在多台 GPU 伺服器上部署

## 🚀 Voxtral 推理微服務

### 技術棧

- **容器化**: Docker + docker-compose
- **GPU 支援**: NVIDIA Container Toolkit + cuDNN 9
- **模型**: Voxtral Mini 3B Q4 ONNX 量化版本
- **推理引擎**: ONNX Runtime GPU + Transformers
- **API 框架**: FastAPI + Uvicorn

### 服務特性

- **專業化**: 專門處理音頻推理任務
- **高性能**: RTX 3080 GPU 加速，支援即時推理
- **多任務**: 語音轉錄、總結、描述、問答
- **量化優化**: Q4 壓縮，為高通 QNN 轉換做準備

### API 接口設計

```python
# 健康檢查
GET /health

# 模型資訊
GET /model/info

# Base64 音頻推理
POST /inference
{
  "audio_data": "base64_encoded_audio",
  "task": "transcribe|summarize|describe|qa",
  "language": "zh|en|auto"
}

# 檔案上傳推理
POST /inference/upload
Form-data: file, task, language
```

## 🔗 服務間通信設計

### HTTP API 通信模式

```python
# 主後端 → Voxtral 推理服務
class VoxtralInferenceClient:
    async def inference(self, audio_data: bytes, task: str) -> Dict
    async def health_check(self) -> Dict
    async def is_service_available(self) -> bool
```

### 備援機制

```python
# 服務可用性檢查 + 自動備援
if await voxtral_client.is_service_available():
    result = await voxtral_client.inference(audio_data, task)
else:
    # 備援至 OpenAI Whisper API
    result = await whisper_api_fallback(audio_data)
```

## 🌐 多環境開發架構

### 開發模式設計

```
MacBook Air (開發環境)          Linux RTX 3080 (推理伺服器)
├── NodePilot 主後端            ├── Voxtral 推理微服務
├── WXT 擴充插件開發            ├── Docker 容器運行
├── API 測試和調試              ├── GPU 模型推理
└── 透過 HTTP 遠端調用 ──────────┘ └── 高性能運算資源
```

### 優勢

1. **資源最佳化**: MacBook 專注開發，Linux 專注推理
2. **開發效率**: 無需在開發機上配置複雜的 GPU 環境
3. **成本控制**: GPU 伺服器僅在需要時運行
4. **部署一致性**: Docker 容器確保環境一致性

## 🔧 部署和運維

### 本地開發啟動

```bash
# 1. 啟動 Voxtral 推理微服務 (Linux RTX 3080)
cd /home/jaren/nodepilot.ai/voxtral-inference-service
./start-services.sh

# 2. 啟動 NodePilot 主後端 (MacBook Air 或 Linux)
cd /home/jaren/nodepilot.ai/nodepilot-backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 健康監控

```bash
# 檢查推理服務狀態
curl http://localhost:8001/health

# 檢查主後端狀態  
curl http://localhost:8000/health

# 檢查微服務整合
curl -X GET http://localhost:8000/voxtral/audio/capabilities
```

### 日誌監控

```bash
# Voxtral 推理服務日誌
docker-compose logs -f voxtral-inference

# 主後端服務日誌
uv run uvicorn app.main:app --log-level info
```

## 📈 性能和擴展

### 當前性能指標

- **模型大小**: ~3GB (Q4 量化)
- **VRAM 使用**: ~4-6GB (RTX 3080)
- **推理延遲**: <2 秒 (語音轉錄)
- **並發支援**: 單個容器實例

### 水平擴展策略

```bash
# 多實例部署
docker-compose up --scale voxtral-inference=3

# 負載均衡 (未來)
nginx upstream {
  server localhost:8001;
  server localhost:8002;  
  server localhost:8003;
}
```

## 🛣️ 未來演進路徑

### 高通筆電部署

1. **模型轉換**: Q4 ONNX → QNN 格式
2. **容器適配**: 修改 Dockerfile 使用高通 SDK
3. **性能測試**: CPU/NPU 推理性能驗證
4. **部署優化**: 針對 ARM 架構優化

### 雲端部署

1. **容器編排**: Kubernetes + Helm Charts
2. **服務發現**: Consul 或 etcd
3. **API 閘道**: Kong 或 Istio
4. **監控告警**: Prometheus + Grafana

## 📊 架構優勢總結

### 對比單體架構

| 方面 | 微服務架構 | 單體架構 |
|------|------------|----------|
| **開發靈活性** | ✅ 獨立開發和部署 | ❌ 高耦合 |
| **技術選型** | ✅ 異構技術棧 | ❌ 技術統一 |
| **故障隔離** | ✅ 服務獨立 | ❌ 全局故障 |
| **資源利用** | ✅ 按需分配 | ❌ 資源浪費 |
| **擴展性** | ✅ 水平擴展 | ❌ 垂直擴展 |

### 特別適用場景

- **多環境開發**: MacBook + Linux GPU 伺服器
- **模型評估**: Q4 量化性能測試
- **設備遷移**: 輕鬆適配高通筆電
- **成本控制**: GPU 資源按需使用

這個微服務架構為 NodePilot V6 MVP 提供了強大的技術基礎，既滿足當前開發需求，也為未來的擴展和優化奠定了堅實基礎。