# AnythingLLM + RTX 3080 部署指南
## Voxtral Mini 3B ONNX Q4 遠端推理服務

> **目標**：在 Linux RTX 3080 機器上部署 AnythingLLM，運行 Voxtral Mini 3B ONNX Q4 模型，並通過 ngrok 提供 API 服務供 Mac 筆電調用。

---

## 📋 系統需求檢查

### 硬體需求
- ✅ RTX 3080 (8GB VRAM) 
- ✅ 至少 16GB RAM
- ✅ 50GB+ 可用硬碟空間

### 軟體準備
```bash
# 檢查 CUDA 版本
nvidia-smi

# 檢查 Docker 是否安裝
docker --version

# 檢查 Python 版本
python3 --version
```

---

## 🚀 Phase 1: AnythingLLM 安裝

### 方法 A：Docker 部署 (推薦)

```bash
# 1. 拉取 AnythingLLM Docker 鏡像
docker pull mintplexlabs/anythingllm

# 2. 創建數據目錄
mkdir -p ~/anythingllm-data

# 3. 運行 AnythingLLM 容器 (開放 API 端口)
docker run -d \
  --name anythingllm \
  --gpus all \
  -p 3001:3001 \
  -p 8080:8080 \
  -v ~/anythingllm-data:/app/server/storage \
  -v ~/anythingllm-data/models:/app/server/models \
  mintplexlabs/anythingllm
```

### 方法 B：原生安裝

```bash
# 1. 克隆倉庫
git clone https://github.com/Mintplex-Labs/anything-llm.git
cd anything-llm

# 2. 安裝依賴
npm install
cd server && npm install

# 3. 配置環境變數
cp .env.example .env
# 編輯 .env 文件設定 GPU 支援
nano .env
```

### 驗證安裝
```bash
# 檢查容器運行狀態
docker ps | grep anythingllm

# 訪問 Web 界面
curl http://localhost:3001/health
```

---

## 🎯 Phase 2: Voxtral Mini 3B ONNX Q4 模型配置

### 1. 模型下載

```bash
# 創建模型目錄
mkdir -p ~/anythingllm-data/models/voxtral-mini-3b

# 使用 git-lfs 下載 ONNX 模型
cd ~/anythingllm-data/models/voxtral-mini-3b
git lfs clone https://huggingface.co/onnx-community/Voxtral-Mini-3B-2507-ONNX

# 或使用 huggingface_hub
pip install huggingface_hub
python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='onnx-community/Voxtral-Mini-3B-2507-ONNX',
    local_dir='./voxtral-model',
    allow_patterns=['*q4*', '*.json', '*.txt']
)
"
```

### 2. 模型配置檢查

```bash
# 檢查下載的模型檔案
ls -la ~/anythingllm-data/models/voxtral-mini-3b/
# 應該看到：
# - voxtral_*q4*.onnx (Q4 量化模型)
# - tokenizer.json
# - config.json
```

### 3. AnythingLLM 模型註冊

```bash
# 進入 AnythingLLM Web 界面：http://localhost:3001
# 1. 登入管理後台
# 2. 進入 Settings > Models
# 3. 添加 Local Model：
#    - Model Type: ONNX
#    - Model Path: /app/server/models/voxtral-mini-3b/voxtral_*q4*.onnx
#    - Model Name: voxtral-mini-3b-q4
```

---

## 🌐 Phase 3: API 服務配置

### 1. 啟用 AnythingLLM API

```bash
# 編輯 AnythingLLM 配置
docker exec -it anythingllm bash

# 在容器內編輯配置檔案
nano /app/server/.env

# 添加以下配置：
API_ENABLED=true
API_PORT=8080
CORS_ENABLED=true
CORS_ORIGINS=*
```

### 2. 重啟服務應用配置

```bash
# 重啟 Docker 容器
docker restart anythingllm

# 等待啟動完成
sleep 30

# 測試 API 端點
curl http://localhost:8080/api/health
```

### 3. API 端點測試

```bash
# 獲取 API Token (從 Web 界面)
# 訪問 http://localhost:3001/settings/api-keys
# 生成新的 API Key

# 測試音訊推理 API
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "測試連接",
    "model": "voxtral-mini-3b-q4"
  }'
```

---

## 🚇 Phase 4: ngrok 隧道設定

### 1. 安裝 ngrok

```bash
# 下載 ngrok
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# 或直接下載二進制文件
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar -xzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/
```

### 2. 配置 ngrok

```bash
# 註冊 ngrok 帳號並獲取 authtoken
# 訪問：https://dashboard.ngrok.com/get-started/your-authtoken

# 設定 authtoken
ngrok config add-authtoken YOUR_NGROK_TOKEN

# 創建 ngrok 配置檔案
cat > ~/.ngrok2/ngrok.yml << EOF
version: "2"
authtoken: YOUR_NGROK_TOKEN
tunnels:
  anythingllm-web:
    addr: 3001
    proto: http
    name: anythingllm-web
  anythingllm-api:
    addr: 8080
    proto: http
    name: anythingllm-api
EOF
```

### 3. 啟動 ngrok 隧道

```bash
# 啟動多個隧道
ngrok start anythingllm-web anythingllm-api

# 或分別啟動
# Terminal 1: Web 界面隧道
ngrok http 3001

# Terminal 2: API 隧道  
ngrok http 8080
```

### 4. 記錄隧道 URL

```bash
# ngrok 會顯示類似以下的 URL：
# Web UI: https://abc123.ngrok.io -> http://localhost:3001
# API: https://def456.ngrok.io -> http://localhost:8080

# 記錄這些 URL，稍後 Mac 筆電會使用
```

---

## 🖥️ Phase 5: Mac 筆電 API 調用配置

### 1. 創建 Python 客戶端

在 Mac 上創建以下測試腳本：

```python
# test_remote_voxtral.py
import requests
import json
import base64

class RemoteVoxtralClient:
    def __init__(self, api_url, api_token):
        self.api_url = api_url.rstrip('/')
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
    
    def transcribe_audio(self, audio_file_path, user_context=None):
        """發送音訊檔案到遠端 Voxtral 服務"""
        
        # 讀取音訊檔案
        with open(audio_file_path, 'rb') as f:
            audio_data = base64.b64encode(f.read()).decode('utf-8')
        
        # 構建請求
        payload = {
            "model": "voxtral-mini-3b-q4",
            "audio_data": audio_data,
            "task": "transcribe_and_analyze",
            "context": user_context or {}
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/audio/transcribe",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "success": False,
                    "error": f"API 調用失敗: {response.status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"連接失敗: {str(e)}"
            }

# 使用範例
if __name__ == "__main__":
    # 使用 ngrok 提供的 URL
    API_URL = "https://def456.ngrok.io"  # 替換為實際 ngrok URL
    API_TOKEN = "your-api-token"        # 替換為實際 API Token
    
    client = RemoteVoxtralClient(API_URL, API_TOKEN)
    
    # 測試音訊檔案
    result = client.transcribe_audio(
        "test_audio.wav",
        user_context={
            "confusion_note": "我需要理解這個概念",
            "selected_text": "相關技術內容"
        }
    )
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
```

### 2. 更新 NodePilot 後端

修改 `nodepilot-backend/app/services/voxtral_processor.py`：

```python
# 在現有的 VoxtralProcessor 中添加遠端調用選項
class RemoteVoxtralProcessor:
    def __init__(self, api_url, api_token):
        self.api_url = api_url
        self.api_token = api_token
        self.client = RemoteVoxtralClient(api_url, api_token)
    
    async def process_audio_direct(self, audio_file, filename, user_context=None):
        # 儲存臨時檔案
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            tmp.write(audio_file.read())
            tmp_path = tmp.name
        
        try:
            # 調用遠端 API
            result = self.client.transcribe_audio(tmp_path, user_context)
            return result
        finally:
            os.unlink(tmp_path)

# 在 .env 中配置
VOXTRAL_REMOTE_API_URL=https://def456.ngrok.io
VOXTRAL_REMOTE_API_TOKEN=your-api-token
```

---

## ✅ Phase 6: 驗證測試

### 1. 端到端連接測試

```bash
# 在 RTX 3080 機器上
# 確認服務運行
docker ps | grep anythingllm
curl http://localhost:8080/api/health

# 確認 ngrok 隧道
curl -I https://def456.ngrok.io/api/health
```

### 2. Mac 筆電測試

```python
# 在 Mac 上運行
python3 test_remote_voxtral.py

# 期望輸出：
# {
#   "success": True,
#   "transcription": "測試音訊轉錄結果",
#   "bullet_points": ["學習重點1", "學習重點2"],
#   "processing_time": 2.1
# }
```

### 3. 性能基準測試

```bash
# 測試音訊處理時間
time curl -X POST https://def456.ngrok.io/api/v1/audio/transcribe \
  -H "Authorization: Bearer $API_TOKEN" \
  -F "audio=@test.wav"

# 期望：RTX 3080 處理時間 < 3 秒
```

---

## 🔧 故障排除

### 常見問題

1. **GPU 不被識別**
```bash
# 檢查 NVIDIA Driver
nvidia-smi
# 檢查 Docker GPU 支援
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
```

2. **模型載入失敗**
```bash
# 檢查模型檔案權限
ls -la ~/anythingllm-data/models/
# 檢查 Docker 掛載
docker exec -it anythingllm ls -la /app/server/models/
```

3. **ngrok 連接問題**
```bash
# 檢查防火牆
sudo ufw status
# 檢查端口佔用
netstat -tlnp | grep -E ':(3001|8080)'
```

4. **API 調用失敗**
```bash
# 檢查 CORS 設定
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS https://def456.ngrok.io/api/health
```

### 日誌檢查

```bash
# AnythingLLM 日誌
docker logs -f anythingllm

# ngrok 連接日誌
ngrok status
ngrok http 8080 --log stdout

# 系統資源監控
nvidia-smi -l 1
htop
```

---

## 🎯 預期性能指標

### RTX 3080 + Q4 量化預期：
- **音訊轉錄時間**：1-3 秒/分鐘音訊
- **內存佔用**：~4GB VRAM
- **並發處理**：2-3 個音訊檔案
- **API 響應時間**：< 5 秒（包含網路延遲）

### 對比基準：
- Whisper + GPT: 8-15 秒
- Voxtral ONNX Q4: 2-5 秒
- **預期提升**：60-70% 速度提升

---

## 📝 配置檢查清單

- [ ] RTX 3080 CUDA 環境正常
- [ ] AnythingLLM Docker 容器運行
- [ ] Voxtral Mini 3B Q4 模型下載完成
- [ ] API 端點正常響應
- [ ] ngrok 隧道建立成功
- [ ] Mac 筆電可以調用遠端 API
- [ ] 端到端音訊處理測試通過
- [ ] 性能指標達到預期

---

## 🚀 下一步計劃

完成部署後：
1. 整合到 NodePilot 後端 (`test_main.py`)
2. 性能對比測試：Voxtral vs Whisper+GPT
3. 優化 API 調用和錯誤處理
4. 設定自動重啟和監控機制

---

**部署完成後記得將 ngrok URL 和 API Token 更新到 NodePilot 配置中！**