# Voxtral Mini 3B Q4 完整實作指南

## 🎯 專案概述

**目標**: 部署 Voxtral Mini 3B ONNX Q4 量化模型至高通筆記型電腦
**流程**: ONNX Q4 → QNN 量化格式轉換
**架構**: Docker 微服務 + FastAPI + 完整生成循環

## 🔧 技術架構

### **三階段 Pipeline 實現**
```
音頻輸入 → audio_encoder.onnx → 音頻嵌入
        ↓
音頻嵌入 + 提示 → embed_tokens.onnx → inputs_embeds 
        ↓  
inputs_embeds → decoder_model_merged.onnx → 完整生成循環 → 文字
```

### **核心檔案結構**
```
voxtral-inference-service/
├── app.py                    # FastAPI 主服務
├── requirements.txt          # Python 依賴
├── Dockerfile               # Docker 配置
└── /app/models/onnx/        # 模型檔案
    ├── audio_encoder.onnx
    ├── embed_tokens.onnx
    ├── decoder_model_merged.onnx
    └── tokenizer.json
```

## 💻 完整實作程式碼

### 1. **requirements.txt** (修復 GPU 依賴衝突)
```toml
# 核心服務
fastapi>=0.100.0
uvicorn[standard]==0.35.0
pydantic==2.11.7

# 音頻處理
librosa>=0.10.0
soundfile>=0.12.0
numpy>=1.24.0,<1.27.0

# ONNX Runtime GPU (注意: librosa 會帶入 CPU 版本，需要後續修復)
onnxruntime-gpu>=1.20.0

# Tokenizer 和模型下載
tokenizers>=0.19.1
huggingface_hub>=0.15.0
```

⚠️ **重要**: `librosa` 依賴會安裝 `onnxruntime` (CPU版本)，必須手動修復！

### 2. **核心服務類別**
```python
class VoxtralONNXInferenceService:
    def __init__(self, model_path: str, device: str = "cpu"):
        self.model_path = model_path
        self.device = device
        self.audio_encoder_session = None
        self.embed_tokens_session = None
        self.decoder_session = None
        self.tokenizer = None
        self.sample_rate = 16000
        
        # Voxtral 特殊 token IDs
        self.bos_id = 1     # <s>
        self.inst_id = 3    # [INST]
        self.baud_id = 25   # [BAUD]
        self.aud_id = 24    # [AUD]
        self.einst_id = 4   # [/INST]
        self.eos_token_id = 2  # </s>
```

### 3. **模型載入方法**
```python
def load_model(self) -> bool:
    """載入完整的 Voxtral ONNX Pipeline"""
    try:
        # 找到所有必需的模型
        audio_encoder_files = list(Path(self.model_path).rglob("audio_encoder*.onnx"))
        embed_tokens_files = list(Path(self.model_path).rglob("embed_tokens*.onnx"))
        decoder_files = list(Path(self.model_path).rglob("decoder_model_merged*.onnx"))
        
        # 配置執行提供者
        providers = ["CPUExecutionProvider"]
        if self.device == "cuda" and "CUDAExecutionProvider" in ort.get_available_providers():
            providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        
        # 載入三個模型
        self.audio_encoder_session = ort.InferenceSession(str(audio_encoder_files[0]), providers=providers)
        self.embed_tokens_session = ort.InferenceSession(str(embed_tokens_files[0]), providers=providers)
        self.decoder_session = ort.InferenceSession(str(decoder_files[0]), providers=providers)
        
        # 載入 tokenizer
        tokenizer_files = list(Path(self.model_path).rglob("tokenizer.json"))
        if tokenizer_files:
            self.tokenizer = Tokenizer.from_file(str(tokenizer_files[0]))
        
        return True
    except Exception as e:
        logger.error(f"Pipeline 載入失敗: {e}")
        return False
```

### 4. **音頻處理 Pipeline**
```python
def extract_mel_features_for_chunk(self, audio_chunk: np.ndarray, sampling_rate=16000, 
                                 n_fft=400, hop_length=160, n_mels=128, target_length=3000):
    """處理音頻塊為標準化 log-mel 頻譜圖"""
    # 填充或截斷到 30 秒
    target_samples = sampling_rate * 30
    audio_chunk = librosa.util.fix_length(audio_chunk, size=target_samples)

    mel_spec = librosa.feature.melspectrogram(
        y=audio_chunk, sr=sampling_rate, n_fft=n_fft, 
        hop_length=hop_length, n_mels=n_mels
    )

    log_spec = np.log10(np.maximum(mel_spec, 1e-10))
    log_spec = np.maximum(log_spec, log_spec.max() - 8.0)
    log_spec = (log_spec + 4.0) / 4.0

    if log_spec.shape[1] > target_length:
        log_spec = log_spec[:, :target_length]

    return log_spec.astype(np.float32)

def process_long_audio(self, audio_data: np.ndarray, sampling_rate=16000):
    """處理長音頻，分塊處理並拼接特徵"""
    chunk_duration = 30
    chunk_samples = chunk_duration * sampling_rate
    num_chunks = int(np.ceil(len(audio_data) / chunk_samples))
    all_audio_embeds = []

    for i in range(num_chunks):
        start_sample = i * chunk_samples
        end_sample = start_sample + chunk_samples
        chunk = audio_data[start_sample:end_sample]

        # 獲取 mel 特徵
        mel_features = self.extract_mel_features_for_chunk(chunk, sampling_rate)
        audio_values = mel_features[None, :] # 添加 batch 維度

        # 音頻編碼器推理
        chunk_embeds_raw = self.audio_encoder_session.run(
            None, {self.audio_encoder_session.get_inputs()[0].name: audio_values}
        )[0]
        all_audio_embeds.append(chunk_embeds_raw)

    # 拼接所有塊的嵌入
    concatenated_embeds = np.concatenate(all_audio_embeds, axis=0)
    return concatenated_embeds
```

### 5. **完整生成循環**
```python
def transcribe(self, audio_input: np.ndarray, max_generation_tokens: int = 200) -> str:
    """執行完整的 Voxtral 轉錄 Pipeline"""
    try:
        # 階段 1: 處理音頻並獲取嵌入
        audio_embeds_raw = self.process_long_audio(audio_input)
        batch_size = 1
        audio_output_frames = audio_embeds_raw.shape[0] // batch_size
        audio_embeds = audio_embeds_raw.reshape(batch_size, audio_output_frames, -1)

        # 階段 2: 建立初始提示
        text_instruction_ids = self.tokenizer.encode("Transcribe the audio.", add_special_tokens=False).ids
        prompt_tokens = ([self.bos_id, self.inst_id, self.baud_id] + 
                       [self.aud_id] * audio_output_frames + 
                       text_instruction_ids + [self.einst_id])
        current_input_ids = np.array([prompt_tokens], dtype=np.int64)
        initial_sequence_length = current_input_ids.shape[1]

        # 階段 3: 運行 embed_tokens 並拼接音頻嵌入
        embed_inputs = {self.embed_tokens_session.get_inputs()[0].name: current_input_ids}
        inputs_embeds = self.embed_tokens_session.run(None, embed_inputs)[0]
        
        # 拼接音頻嵌入到正確位置 (在 [BAUD] 之後)
        audio_splice_start_idx = 3
        inputs_embeds[0, audio_splice_start_idx:audio_splice_start_idx + audio_output_frames, :] = audio_embeds[0]

        # 階段 4: 生成循環
        generated_ids = []
        past_key_values_cache = None
        current_past_sequence_length = 0
        num_decoder_layers = 30

        for i in range(max_generation_tokens):
            dec_inputs = {}
            current_step_sequence_length = 1 if i > 0 else initial_sequence_length
            current_total_sequence_length = current_past_sequence_length + current_step_sequence_length

            if i == 0:  # Prefill 階段
                dec_inputs["inputs_embeds"] = inputs_embeds
                dec_inputs["attention_mask"] = np.ones((batch_size, initial_sequence_length), dtype=np.int64)
                dec_inputs["position_ids"] = np.arange(initial_sequence_length, dtype=np.int64)[None, :]
                for l in range(num_decoder_layers):
                    dec_inputs[f"past_key_values.{l}.key"] = np.zeros((batch_size, 8, 0, 128), dtype=np.float32)
                    dec_inputs[f"past_key_values.{l}.value"] = np.zeros((batch_size, 8, 0, 128), dtype=np.float32)
            else:  # Decode 階段
                next_token_input_id = np.array([[generated_ids[-1]]], dtype=np.int64)
                single_token_embeds = self.embed_tokens_session.run(
                    None, {"input_ids": next_token_input_id}
                )[0]
                dec_inputs["inputs_embeds"] = single_token_embeds
                dec_inputs["attention_mask"] = np.ones((batch_size, current_total_sequence_length), dtype=np.int64)
                dec_inputs["position_ids"] = np.array([[current_past_sequence_length]], dtype=np.int64)
                for l in range(num_decoder_layers):
                    dec_inputs[f"past_key_values.{l}.key"] = past_key_values_cache[l * 2]
                    dec_inputs[f"past_key_values.{l}.value"] = past_key_values_cache[l * 2 + 1]

            # 執行解碼器
            outputs = self.decoder_session.run(None, dec_inputs)
            logits, past_key_values_cache = outputs[0], outputs[1:]
            next_token_id = int(np.argmax(logits[0, -1, :]))
            generated_ids.append(next_token_id)
            
            current_past_sequence_length = current_total_sequence_length
            
            # 檢查結束條件
            if next_token_id == self.eos_token_id:
                break

        # 最終解碼
        final_text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        return final_text
        
    except Exception as e:
        return f"推理錯誤: {str(e)}"
```

## 🐳 Docker 部署

### **Dockerfile** (修復 GPU 依賴衝突版本)
```dockerfile
# Voxtral Mini 3B Q4 ONNX GPU 推理服務
FROM nvidia/cuda:12.2.2-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV CUDA_VISIBLE_DEVICES=0

# 系統依賴
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-dev \
    ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# 🔧 修復 ONNX Runtime GPU 依賴衝突
RUN pip3 install --no-cache-dir -r requirements.txt && \
    pip3 uninstall -y onnxruntime && \
    pip3 install --force-reinstall onnxruntime-gpu>=1.20.0

# 下載 Q4 量化模型
RUN python3 -c "from huggingface_hub import snapshot_download; \
    snapshot_download('onnx-community/Voxtral-Mini-3B-2507-ONNX', \
    local_dir='/app/models', allow_patterns=['*q4*', 'tokenizer.json'])"

COPY app.py .
EXPOSE 8001
CMD ["python3", "app.py"]
```

### **部署指令**
```bash
# 快速部署 (使用提供的腳本)
./quick-deploy.sh

# 或手動部署
docker build -t voxtral-inference:gpu .
docker run --gpus all -d --name voxtral-service -p 8001:8001 voxtral-inference:gpu

# 檢查 GPU 支援
curl -s http://localhost:8001/health | jq '.cuda_available'
# 預期: true

# 驗證 CUDA 執行提供者
docker exec voxtral-service python3 -c "import onnxruntime as ort; print(ort.get_available_providers())"
# 預期: ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']
```

## 📡 API 使用方式

### **端點說明**
- `POST /inference` - 音頻推理 (Base64 編碼)
- `POST /inference/upload` - 檔案上傳推理
- `GET /health` - 服務健康檢查
- `GET /model/info` - 模型詳細資訊

### **請求範例**
```python
import base64
import requests

# 讀取音頻檔案
with open("audio.wav", "rb") as f:
    audio_bytes = f.read()
    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

# 發送請求
response = requests.post("http://localhost:8001/inference", json={
    "audio_data": audio_base64,
    "task": "transcribe",
    "language": "zh"
})

result = response.json()
print(f"轉錄結果: {result['result']}")
```

## 🔧 故障排除

### **🚨 GPU 依賴衝突問題 (最常見)**
**症狀**: `cuda_available: true` 但實際無法使用 GPU
**原因**: `librosa` 安裝了 `onnxruntime` (CPU版本) 覆蓋了 GPU 版本
**解決方案**:
```bash
# 方法 1: Docker 構建時修復 (推薦)
RUN pip3 install --no-cache-dir -r requirements.txt && \
    pip3 uninstall -y onnxruntime && \
    pip3 install --force-reinstall onnxruntime-gpu>=1.20.0

# 方法 2: 運行時容器內修復
docker exec <container> pip3 uninstall -y onnxruntime
docker exec <container> pip3 install --force-reinstall onnxruntime-gpu==1.22.0
docker restart <container>
```

### **CUDA 相容性問題**
```bash
# 檢查 CUDA 版本
nvidia-smi

# RTX 3080 建議配置
# - CUDA 12.2 (避免 12.4+)
# - ONNX Runtime >= 1.20.0
```

### **驗證 GPU 支援**
```python
import onnxruntime as ort
print('可用提供者:', ort.get_available_providers())
# 正確: ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']
# 錯誤: ['AzureExecutionProvider', 'CPUExecutionProvider']
```

### **模型檢查工具**
```python
def inspect_onnx_model(model_path: str):
    session = ort.InferenceSession(model_path)
    
    print("=== 輸入格式 ===")
    for input_meta in session.get_inputs():
        print(f"名稱: {input_meta.name}, 形狀: {input_meta.shape}")
    
    print("=== 輸出格式 ===")
    for output_meta in session.get_outputs():
        print(f"名稱: {output_meta.name}, 形狀: {output_meta.shape}")
```

### **記憶體優化**
```python
# ONNX 會話優化
sess_options = ort.SessionOptions()
sess_options.intra_op_num_threads = 4          # CPU 核心數
sess_options.inter_op_num_threads = 2          # 並行操作數
sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
```

## 📊 技術決策說明

### **為什麼必須使用 ONNX Q4？**
1. **部署限制**: 原版模型 VRAM 需求過大 (>16GB)
2. **量化評估**: 測試 Q4 性能是否符合預期  
3. **轉換需求**: QNN 需要 ONNX 作為中間格式
4. **硬體相容**: 高通 DSP 優化需要量化模型

### **Pipeline 分離的好處**
1. **記憶體效率**: 分階段載入降低峰值用量
2. **調試便利**: 可獨立測試各階段功能  
3. **優化彈性**: 可針對不同階段選擇最佳配置
4. **維護性**: 模組化架構便於問題排查

### **生成循環架構**
1. **Prefill 階段**: 處理完整提示序列，建立初始狀態
2. **Decode 階段**: 逐個 token 生成，利用快取狀態
3. **狀態管理**: 30層解碼器的 key/value 快取
4. **停止條件**: EOS token 或最大長度限制

## 🎯 效能指標

### **預期性能**
- **GPU (RTX 3080)**: ~2-5s 音頻轉錄時間
- **CPU**: ~10-30s 音頻轉錄時間  
- **記憶體使用**: ~4-8GB VRAM
- **支援音頻長度**: 無限制 (30秒分塊處理)

### **優化建議**
1. **批次處理**: 同時處理多個音頻檔案
2. **模型量化**: 使用 Q4 而非 FP16 版本
3. **硬體加速**: 優先使用 GPU 推理
4. **快取策略**: 複用 tokenizer 和模型會話

## ⚠️ 重要注意事項

### **🔥 關鍵問題 (必須處理)**
1. **GPU 依賴衝突**: `librosa` → `onnxruntime` (CPU) 覆蓋 GPU 版本
   - 解決: 先安裝依賴 → 卸載 CPU 版本 → 強制重裝 GPU 版本
2. **不要使用 VoxtralProcessor**: 此類別不存在於 transformers 庫中
3. **CUDA 相容性**: RTX 3080 使用 CUDA 12.2 (避免 12.4+)
4. **tokenizer 必需**: 沒有 tokenizer.json 無法正確解碼文字

### **🛠️ 技術細節**
5. **音頻格式標準化**: 務必重新採樣到 16kHz
6. **記憶體管理**: ONNX 模型載入會佔用大量記憶體
7. **模型檔案完整性**: 確保下載所有 Q4 ONNX 檔案
8. **Docker GPU 支援**: 必須使用 `--gpus all` 參數

## 🚀 後續部署計畫

### **短期 (Q4 測試階段)**
- ✅ 完整 pipeline 實現
- ✅ 生成循環和 tokenizer 整合
- ✅ GPU 推理優化
- ✅ GPU 依賴衝突修復
- ⏳ 性能基準測試

### **中期 (QNN 轉換準備)**
- ⏳ 批次處理支持
- ⏳ 模型性能調優
- ⏳ 端到端測試驗證
- ⏳ 文檔和範例完善

### **長期 (高通部署)**
- ⏳ ONNX → QNN 格式轉換
- ⏳ 高通 SDK 集成測試
- ⏳ 移動端性能優化
- ⏳ 產品整合部署

---

## 📋 檔案清單

**保留的關鍵檔案** (`voxtral-inference-service/`):
- `app.py` - 完整的三階段 ONNX Pipeline 實作
- `Dockerfile` - 修復了 GPU 依賴衝突的構建檔案  
- `requirements.txt` - 精簡的依賴清單
- `gpu-fix.md` - GPU 問題修復指南
- `quick-deploy.sh` - 一鍵部署腳本
- `test_inference.py` - 推理測試腳本

---

**狀態**: GPU 推理完全啟用 + 依賴衝突已修復  
**更新**: 2025-08-20  
**適用於**: Voxtral Mini 3B ONNX Q4, FastAPI, Docker GPU 微服務架構