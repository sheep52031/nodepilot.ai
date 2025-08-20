#!/bin/bash
# Voxtral Q4 GPU 快速部署腳本

set -e

echo "🚀 Voxtral Mini 3B Q4 GPU 快速部署"

# 停止現有容器
echo "📋 停止現有服務..."
docker stop voxtral-gpu-service 2>/dev/null || true
docker rm voxtral-gpu-service 2>/dev/null || true

# 構建映像
echo "🔨 構建 GPU 映像..."
docker build -t voxtral-inference:gpu .

# 啟動服務
echo "▶️  啟動 GPU 服務..."
docker run --gpus all -d \
  --name voxtral-gpu-service \
  -p 8001:8001 \
  voxtral-inference:gpu

# 等待啟動
echo "⏳ 等待服務啟動..."
sleep 10

# 健康檢查
echo "🔍 檢查服務狀態..."
curl -s http://localhost:8001/health | jq

echo "✅ 服務部署完成! 訪問 http://localhost:8001/docs"