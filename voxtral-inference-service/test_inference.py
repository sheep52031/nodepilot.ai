#!/usr/bin/env python3
"""
Voxtral 推理服務測試腳本
用於驗證修正後的程式碼是否正常運作
"""

import requests
import base64
import json
import time

# 測試配置
API_URL = "http://localhost:8001"
TIMEOUT = 30

def test_health_check():
    """測試健康檢查端點"""
    print("🔍 測試健康檢查...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print("✅ 健康檢查通過")
            print(f"   - 模型載入: {data.get('model_loaded')}")
            print(f"   - ONNX 會話: {data.get('onnx_session_loaded')}")
            print(f"   - 設備: {data.get('device')}")
            print(f"   - CUDA 可用: {data.get('cuda_available')}")
            return True
        else:
            print(f"❌ 健康檢查失敗: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 健康檢查錯誤: {e}")
        return False

def test_model_info():
    """測試模型資訊端點"""
    print("\n🔍 測試模型資訊...")
    try:
        response = requests.get(f"{API_URL}/model/info", timeout=TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            print("✅ 模型資訊獲取成功")
            print(f"   - 模型: {data.get('model')}")
            print(f"   - 量化: {data.get('quantization')}")
            print(f"   - 載入狀態: {data.get('loaded')}")
            print(f"   - 採樣率: {data.get('sample_rate')}")
            print(f"   - ONNX 提供者: {data.get('onnx_providers', [])}")
            
            # 檢查模型輸入輸出資訊
            if 'model_inputs' in data:
                print("   - 模型輸入:")
                for input_info in data['model_inputs']:
                    print(f"     * {input_info['name']}: {input_info['shape']} ({input_info['type']})")
                    
            if 'model_outputs' in data:
                print("   - 模型輸出:")
                for output_info in data['model_outputs']:
                    print(f"     * {output_info['name']}: {output_info['shape']} ({output_info['type']})")
            
            return True
        else:
            print(f"❌ 模型資訊獲取失敗: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 模型資訊錯誤: {e}")
        return False

def create_test_audio():
    """創建測試音頻數據 (模擬)"""
    # 創建簡單的正弦波音頻數據
    import numpy as np
    
    duration = 2.0  # 2 秒
    sample_rate = 16000
    frequency = 440  # A4 音符
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio = np.sin(2 * np.pi * frequency * t) * 0.5
    
    # 轉換為 WAV 格式的二進制數據
    import io
    import wave
    
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # 單聲道
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        # 轉換為 16-bit PCM
        audio_data = (audio * 32767).astype(np.int16)
        wav_file.writeframes(audio_data.tobytes())
    
    return buffer.getvalue()

def test_inference():
    """測試音頻推理端點"""
    print("\n🔍 測試音頻推理...")
    try:
        # 創建測試音頻
        audio_bytes = create_test_audio()
        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
        
        # 構建推理請求
        request_data = {
            "audio_data": audio_base64,
            "task": "transcribe",
            "language": "auto"
        }
        
        print("   - 發送推理請求...")
        start_time = time.time()
        
        response = requests.post(
            f"{API_URL}/inference", 
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
        )
        
        processing_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print("✅ 推理成功")
            print(f"   - 結果: {data.get('result', '')[:100]}...")
            print(f"   - 任務: {data.get('task')}")
            print(f"   - 處理時間: {data.get('processing_time', processing_time):.2f}s")
            print(f"   - 模型狀態: {data.get('model_info', {}).get('status')}")
            return True
        else:
            print(f"❌ 推理失敗: {response.status_code}")
            print(f"   - 錯誤: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 推理錯誤: {e}")
        return False

def main():
    """主測試函數"""
    print("=" * 50)
    print("🎯 Voxtral 推理服務測試")
    print("=" * 50)
    
    # 等待服務啟動
    print("⏳ 等待服務啟動...")
    time.sleep(5)
    
    success_count = 0
    total_tests = 3
    
    # 執行測試
    if test_health_check():
        success_count += 1
        
    if test_model_info():
        success_count += 1
        
    if test_inference():
        success_count += 1
    
    # 顯示結果
    print("\n" + "=" * 50)
    print(f"📊 測試結果: {success_count}/{total_tests} 通過")
    
    if success_count == total_tests:
        print("🎉 所有測試通過！服務運行正常")
        return True
    else:
        print("⚠️  部分測試失敗，請檢查服務狀態")
        return False

if __name__ == "__main__":
    main()