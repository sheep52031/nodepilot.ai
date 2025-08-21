"""
Voxtral 音頻 API 端點
支援語音轉錄、總結和 Q&A（含中文支援）
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, Dict, Any
import base64
import logging

from app.services.voxtral_client import get_voxtral_client

router = APIRouter(prefix="/voxtral/audio")
logger = logging.getLogger(__name__)

class AudioRequest(BaseModel):
    """音頻請求模型"""
    audio_data: str  # Base64 編碼的音頻
    mode: str = "transcribe"  # transcribe, summarize, qa
    language: Optional[str] = "auto"  # auto, zh, en, etc.
    output_language: Optional[str] = "zh"  # 輸出語言

@router.post("/process")
async def process_audio(request: AudioRequest):
    """
    處理音頻輸入 - 調用 Voxtral 推理微服務
    支援語音轉錄、總結和問答
    """
    try:
        # 解碼 Base64 音頻數據
        audio_bytes = base64.b64decode(request.audio_data)
        
        # 獲取 Voxtral 客戶端
        client = await get_voxtral_client()
        
        # 檢查服務可用性
        if not await client.is_service_available():
            raise HTTPException(
                status_code=503, 
                detail="Voxtral 推理服務暫時不可用，請稍後重試"
            )
        
        # 調用推理服務
        result = await client.inference(
            audio_data=audio_bytes,
            task=request.mode,
            language=request.output_language or "zh"
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=500,
                detail=f"推理失敗: {result.get('error', '未知錯誤')}"
            )
        
        return {
            "success": True,
            "result": {
                "text": result.get("result", ""),
                "task": result.get("task", request.mode),
                "language": result.get("language", request.language),
                "processing_time": result.get("processing_time", 0),
                "model_info": result.get("model_info", {})
            },
            "model": "Voxtral Mini 3B Q4 (微服務)",
            "device": "RTX 3080 GPU"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"音頻處理錯誤: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_audio(
    file: UploadFile = File(...),
    mode: str = Form("transcribe"),
    language: str = Form("auto"),
    output_language: str = Form("zh")
):
    """
    上傳音頻檔案進行處理 - 調用 Voxtral 推理微服務
    """
    try:
        # 讀取音頻檔案
        audio_data = await file.read()
        
        # 獲取 Voxtral 客戶端
        client = await get_voxtral_client()
        
        # 檢查服務可用性
        if not await client.is_service_available():
            raise HTTPException(
                status_code=503,
                detail="Voxtral 推理服務暫時不可用，請稍後重試"
            )
        
        # 調用推理服務
        result = await client.upload_inference(
            audio_data=audio_data,
            filename=file.filename or "audio.wav",
            task=mode,
            language=output_language or "zh"
        )
        
        if not result.get("success", False):
            raise HTTPException(
                status_code=500,
                detail=f"推理失敗: {result.get('error', '未知錯誤')}"
            )
        
        return {
            "success": True,
            "result": {
                "text": result.get("result", ""),
                "task": result.get("task", mode),
                "filename": file.filename,
                "content_type": file.content_type,
                "processing_time": result.get("processing_time", 0),
                "model_info": result.get("model_info", {})
            },
            "model": "Voxtral Mini 3B Q4 (微服務)",
            "device": "RTX 3080 GPU"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"音頻上傳處理錯誤: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/languages")
async def get_supported_languages():
    """
    獲取支援的語言列表
    """
    return {
        "languages": [
            {"code": "zh", "name": "中文", "supported": True},
            {"code": "en", "name": "English", "supported": True},
            {"code": "es", "name": "Español", "supported": True},
            {"code": "fr", "name": "Français", "supported": True},
            {"code": "pt", "name": "Português", "supported": True},
            {"code": "hi", "name": "हिन्दी", "supported": True},
            {"code": "de", "name": "Deutsch", "supported": True},
            {"code": "nl", "name": "Nederlands", "supported": True},
            {"code": "it", "name": "Italiano", "supported": True}
        ],
        "auto_detect": True,
        "default": "zh"
    }

@router.get("/capabilities")
async def get_capabilities():
    """
    獲取模型能力資訊
    """
    return {
        "capabilities": {
            "transcription": {
                "enabled": True,
                "languages": ["zh", "en", "es", "fr", "pt", "hi", "de", "nl", "it"],
                "auto_detect": True,
                "max_duration": "40 minutes"
            },
            "summarization": {
                "enabled": True,
                "output_languages": ["zh", "en"],
                "context_length": "32k tokens"
            },
            "qa": {
                "enabled": True,
                "context_aware": True,
                "function_calling": True
            }
        },
        "model": "Voxtral Mini 3B Q4",
        "hardware": "RTX 3080 (8GB VRAM)",
        "inference": "ONNX Runtime with CUDA"
    }