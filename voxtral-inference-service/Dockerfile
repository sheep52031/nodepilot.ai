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

# 修復 ONNX Runtime GPU 依賴衝突
RUN pip3 install --no-cache-dir -r requirements.txt && \
    pip3 uninstall -y onnxruntime && \
    pip3 install --force-reinstall onnxruntime-gpu>=1.20.0

# 下載 Q4 量化模型和 tokenizer
RUN python3 -c "from huggingface_hub import snapshot_download, hf_hub_download; \
    snapshot_download('onnx-community/Voxtral-Mini-3B-2507-ONNX', \
    local_dir='/app/models', allow_patterns=['*q4*']); \
    hf_hub_download('onnx-community/Voxtral-Mini-3B-2507-ONNX', \
    filename='tokenizer.json', local_dir='/app/models')"

COPY app.py .
EXPOSE 8001
CMD ["python3", "app.py"]