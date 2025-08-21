"""
Voxtral 推理服務客戶端
透過 HTTP API 調用獨立的 Voxtral Docker 服務
"""

import httpx
import logging
from typing import Dict, Any, Optional
import base64
import asyncio
import os

logger = logging.getLogger(__name__)

class VoxtralInferenceClient:
    """Voxtral 推理服務客戶端"""
    
    def __init__(self, base_url: Optional[str] = None):
        # 支援環境變數配置
        if base_url is None:
            base_url = os.getenv("VOXTRAL_API_URL", "http://localhost:8001")
        
        self.base_url = base_url.rstrip('/')
        self.timeout = 120.0  # 2 分鐘超時
        logger.info(f"Voxtral 客戶端初始化: {self.base_url}")
    
    async def health_check(self) -> Dict[str, Any]:
        """檢查推理服務健康狀態"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/health")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"健康檢查失敗: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def get_model_info(self) -> Dict[str, Any]:
        """獲取模型資訊"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/model/info")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"獲取模型資訊失敗: {e}")
            return {"error": str(e)}
    
    async def inference(
        self,
        audio_data: bytes,
        task: str = "transcribe",
        language: str = "zh",
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        音頻推理
        
        Args:
            audio_data: 音頻二進制數據
            task: 任務類型 (transcribe, summarize, describe, qa)
            language: 語言代碼
            prompt: 自定義提示詞
        
        Returns:
            推理結果字典
        """
        try:
            # 轉換為 Base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            # 準備請求數據
            request_data = {
                "audio_data": audio_base64,
                "task": task,
                "language": language
            }
            
            if prompt:
                request_data["prompt"] = prompt
            
            # 發送推理請求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/inference",
                    json=request_data
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"推理完成: {task} - {result.get('processing_time', 0):.2f}s")
                return result
                
        except httpx.TimeoutException:
            logger.error("推理請求超時")
            return {
                "success": False,
                "error": "推理服務超時",
                "task": task
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"推理請求失敗: {e.response.status_code}")
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                "task": task
            }
        except Exception as e:
            logger.error(f"推理客戶端錯誤: {e}")
            return {
                "success": False,
                "error": str(e),
                "task": task
            }
    
    async def upload_inference(
        self,
        audio_data: bytes,
        filename: str,
        task: str = "transcribe", 
        language: str = "zh",
        prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        上傳音頻檔案進行推理
        
        Args:
            audio_data: 音頻二進制數據
            filename: 檔案名稱
            task: 任務類型
            language: 語言代碼
            prompt: 自定義提示詞
        
        Returns:
            推理結果字典
        """
        try:
            # 準備檔案和表單數據
            files = {"file": (filename, audio_data)}
            data = {
                "task": task,
                "language": language
            }
            
            if prompt:
                data["prompt"] = prompt
            
            # 發送上傳推理請求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/inference/upload",
                    files=files,
                    data=data
                )
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"上傳推理完成: {task} - {result.get('processing_time', 0):.2f}s")
                return result
                
        except Exception as e:
            logger.error(f"上傳推理失敗: {e}")
            return {
                "success": False,
                "error": str(e),
                "task": task
            }
    
    async def is_service_available(self) -> bool:
        """檢查服務是否可用"""
        health = await self.health_check()
        return health.get("status") == "healthy"

# 全域客戶端實例
voxtral_client = VoxtralInferenceClient()

async def get_voxtral_client() -> VoxtralInferenceClient:
    """獲取 Voxtral 客戶端實例"""
    return voxtral_client