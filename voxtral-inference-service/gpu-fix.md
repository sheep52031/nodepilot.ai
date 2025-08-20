# Voxtral ONNX Runtime GPU 修復指南

## 問題根源
`librosa` 依賴會自動安裝 `onnxruntime` (CPU版本)，與 `onnxruntime-gpu` 產生套件衝突，導致 `CUDAExecutionProvider` 不可用。

## 解決方案
### 方法 1: Docker 構建時修復
```dockerfile
RUN pip3 install --no-cache-dir -r requirements.txt && \
    pip3 uninstall -y onnxruntime && \
    pip3 install --force-reinstall onnxruntime-gpu>=1.20.0
```

### 方法 2: 運行時容器內修復
```bash
docker exec <container> pip3 uninstall -y onnxruntime
docker exec <container> pip3 install --force-reinstall onnxruntime-gpu==1.22.0
docker restart <container>
```

## 驗證
```python
import onnxruntime as ort
print('可用提供者:', ort.get_available_providers())
# 預期: ['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']
```

## 部署命令
```bash
# 構建映像
docker build -t voxtral-gpu .

# 運行服務 (需要 --gpus all)
docker run --gpus all -d --name voxtral-service -p 8001:8001 voxtral-gpu
```