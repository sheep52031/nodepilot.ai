"""
Voxtral LocalAI 相容端點
為 AnythingLLM 提供 OpenAI 格式的 Voxtral API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import time
from datetime import datetime

router = APIRouter(prefix="/localai", tags=["voxtral-localai"])

# OpenAI 相容的數據模型
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    stream: Optional[bool] = False

@router.get("/")
async def localai_root():
    """LocalAI 根端點"""
    return {
        "message": "NodePilot Voxtral LocalAI Bridge",
        "models": ["voxtral-mini-3b-q4"],
        "status": "ready"
    }

@router.get("/v1/models")
async def list_models():
    """列出可用模型 (OpenAI 格式)"""
    return {
        "object": "list",
        "data": [
            {
                "id": "voxtral-mini-3b-q4",
                "object": "model", 
                "created": int(time.time()),
                "owned_by": "nodepilot"
            }
        ]
    }

@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """聊天完成端點 (OpenAI 格式)"""
    
    try:
        # 提取最後一個用戶訊息
        user_message = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_message = msg.content
                break
        
        if not user_message:
            raise HTTPException(status_code=400, detail="No user message found")
        
        # 使用真正的 Voxtral ONNX 推理
        from app.services.voxtral_inference import get_voxtral_inference
        
        inference_engine = get_voxtral_inference()
        response_text = inference_engine.generate_text(
            prompt=user_message,
            max_length=request.max_tokens or 1000,
            temperature=request.temperature or 0.7
        )
        
        # 建構 OpenAI 格式回應
        completion_id = f"chatcmpl-{int(time.time())}"
        
        response = {
            "id": completion_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response_text
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(response_text.split()),
                "total_tokens": len(user_message.split()) + len(response_text.split())
            }
        }
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")