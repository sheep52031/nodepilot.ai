#!/usr/bin/env python3
"""
臨時測試用的 NodePilot API 服務
簡化版本，用於測試音頻標註功能
"""

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import tempfile
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NodePilotTest")

app = FastAPI(
    title="NodePilot API - Test Version",
    version="0.1.0-test",
    debug=True
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    """根路徑"""
    return {
        "message": "NodePilot API Test Version is running",
        "version": "0.1.0-test",
        "docs": "/docs",
        "test_endpoint": "/api/v1/multi-agent/generate-teaching-integrated"
    }

@app.get("/health")
def health_check():
    """健康檢查"""
    return {"status": "healthy", "version": "test"}


@app.post("/api/v1/multi-agent/generate-teaching-integrated")
async def test_integrated_generate_teaching(
    url: str = Form(...),
    selected_text: str = Form(...),
    confusion_note: str = Form(...),
    page_title: str = Form(None),
    audio_file: UploadFile = File(None)
):
    """測試版：音頻標註處理端點"""
    
    try:
        logger.info(f"收到請求 - URL: {url}")
        logger.info(f"選取文字: {selected_text[:100]}...")
        logger.info(f"困惑筆記: {confusion_note[:100]}...")
        
        # 處理音頻檔案
        audio_processing_result = None
        if audio_file and audio_file.size > 0:
            logger.info(f"收到音頻檔案: {audio_file.filename}, 大小: {audio_file.size} bytes")
            
            # 嘗試使用 Voxtral 音頻處理服務（優先）
            try:
                # 準備用戶上下文
                user_context = {
                    "confusion_note": confusion_note,
                    "selected_text": selected_text,
                    "page_title": page_title,
                    "url": url
                }
                
                # 多層級 Voxtral 處理：遠端 RTX 3080 → 本地 Replicate → Whisper 備案
                voxtral_success = False
                
                # 第一層：嘗試遠端 RTX 3080 Voxtral
                try:
                    from app.services.remote_voxtral_processor import remote_voxtral_processor
                    
                    if remote_voxtral_processor.is_ready:
                        logger.info("🚀 嘗試使用遠端 RTX 3080 Voxtral Mini 3B")
                        remote_result = await remote_voxtral_processor.process_audio_direct(
                            audio_file.file,
                            audio_file.filename,
                            user_context=user_context
                        )
                        
                        if remote_result.get("success"):
                            logger.info("✅ 遠端 RTX 3080 Voxtral 處理成功")
                            voxtral_result = remote_result
                            voxtral_success = True
                        else:
                            logger.warning("遠端 Voxtral 處理失敗，嘗試本地備案")
                    else:
                        logger.info("遠端 Voxtral 未配置，跳過")
                        
                except Exception as remote_error:
                    logger.warning(f"遠端 Voxtral 連接失敗: {remote_error}")
                
                # 第二層：如果遠端失敗，嘗試本地 Replicate Voxtral
                if not voxtral_success:
                    try:
                        from app.services.voxtral_processor import voxtral_processor
                        
                        logger.info("🔄 嘗試使用本地 Voxtral Mini 3B (Replicate)")
                        local_result = await voxtral_processor.process_audio_direct(
                            audio_file.file,
                            audio_file.filename,
                            user_context=user_context
                        )
                        
                        if local_result.get("success"):
                            logger.info("✅ 本地 Voxtral 處理成功")
                            voxtral_result = local_result
                            voxtral_success = True
                        else:
                            logger.warning("本地 Voxtral 處理失敗")
                            
                    except Exception as local_error:
                        logger.warning(f"本地 Voxtral 處理失敗: {local_error}")
                
                # 如果任一 Voxtral 成功，格式化結果
                if voxtral_success:
                    audio_processing_result = {
                        "success": True,
                        "method": voxtral_result.get("method", "voxtral_direct"),
                        "transcription": {
                            "text": voxtral_result.get("transcription", ""),
                            "language": "zh",
                            "confidence": 0.95,
                            "model_used": voxtral_result["processing_metadata"].get("model_used", "voxtral-mini-3b")
                        },
                        "semantic_analysis": {
                            "structured_confusion": voxtral_result["semantic_analysis"]["learning_focus"],
                            "learning_intent": "直接音頻理解和重點提取",
                            "suggested_approach": "基於 bullet points 的重點學習",
                            "bullet_points": voxtral_result["bullet_points"],
                            "key_concepts": voxtral_result["semantic_analysis"]["key_concepts"],
                            "difficulty_level": voxtral_result["semantic_analysis"]["difficulty_level"]
                        },
                        "processing_metadata": voxtral_result["processing_metadata"]
                    }
                else:
                    # 第三層：降級到 Whisper + GPT
                    logger.warning("所有 Voxtral 方案失敗，降級到 Whisper 備案")
                    
                    # 降級到原有的 Whisper + GPT 處理
                    try:
                        from app.services.audio_processor import audio_processor
                        
                        audio_processing_result = await audio_processor.process_audio_file(
                            audio_file.file,
                            audio_file.filename,
                            language="zh",
                            user_context=user_context
                        )
                        
                        logger.info("✅ Whisper 備案處理服務調用成功")
                        
                    except ImportError as import_error:
                        logger.warning(f"所有音頻處理服務不可用: {import_error}")
                        # 最終降級到簡單處理
                        audio_processing_result = {
                            "success": True,
                            "method": "fallback",
                            "transcription": {
                                "text": "音頻處理服務暫時不可用，使用模擬轉錄",
                                "language": "zh",
                                "confidence": 0.0,
                                "model_used": "fallback"
                            },
                            "semantic_analysis": {
                                "structured_confusion": "無法分析音頻語意",
                                "learning_intent": "用戶提供了音頻補充說明",
                                "suggested_approach": "基於文字內容生成教學材料"
                            },
                            "processing_metadata": {
                                "filename": audio_file.filename,
                                "file_size": audio_file.size,
                                "fallback_reason": "所有服務不可用"
                            }
                        }
                
            except Exception as e:
                logger.error(f"音頻處理失敗: {str(e)}")
                return JSONResponse(
                    status_code=500,
                    content={"error": f"音頻處理失敗: {str(e)}"}
                )
                
        else:
            logger.info("未提供音頻檔案")
        
        # 生成教學內容
        audio_section = ""
        if audio_processing_result and audio_processing_result.get("success"):
            transcription = audio_processing_result.get("transcription", {})
            semantic_analysis = audio_processing_result.get("semantic_analysis", {})
            
            audio_section = f"""
## 🎵 音頻內容分析

### 音頻轉錄
{transcription.get("text", "無轉錄內容")}

### 語意分析
- **學習困惑**: {semantic_analysis.get("structured_confusion", "未檢測到明確困惑")}
- **學習意圖**: {semantic_analysis.get("learning_intent", "理解相關概念")}
- **情緒狀態**: {semantic_analysis.get("emotional_tone", "積極學習")}
- **建議教學方式**: {semantic_analysis.get("suggested_approach", "結合實例說明")}

### 關鍵概念
{chr(10).join([f"- {concept}" for concept in semantic_analysis.get("key_concepts", ["相關技術概念"])])}
"""

        mock_teaching_content = f"""# 學習筆記：{page_title or "網頁內容"}

## 📋 你的困惑
{confusion_note}

## 📖 選取內容
> {selected_text}

## 🎯 詳細解釋
針對你提到的困惑，這裡是詳細的解釋...
{audio_section}

## 💡 學習要點
- 重點1：相關概念說明
- 重點2：實際應用方式
- 重點3：延伸學習建議

## 📚 推薦資源
- 相關文章連結
- 延伸閱讀建議
"""
        
        # 構建響應
        response = {
            "success": True,
            "annotation_id": "test_12345",
            "teaching_content": mock_teaching_content,
            "system_used": "integrated_ai_core_api_test",
            "metadata": {
                "audio_processed": audio_processing_result is not None,
                "audio_processing_result": audio_processing_result,
                "processing_time": "computed_in_real_implementation",
                "models_used": (
                    ["gpt-3.5-turbo", audio_processing_result["transcription"]["model_used"]] 
                    if audio_processing_result and audio_processing_result.get("success") 
                    else ["gpt-3.5-turbo"]
                ),
                "database_stored": False,  # 測試版不實際存儲
                "timestamp": "2025-08-19T12:30:00Z"
            }
        }
        
        logger.info("處理完成，返回響應")
        return response
        
    except Exception as e:
        logger.error(f"處理失敗: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"音頻標註處理失敗: {str(e)}",
                "success": False,
                "debug": True
            }
        )


@app.get("/api/v1/multi-agent/status")
def get_system_status():
    """系統狀態檢查"""
    return {
        "system_health": "healthy",
        "version": "test",
        "features": {
            "audio_upload": True,
            "text_annotation": True,
            "ai_processing": "mock",
            "database": False
        },
        "limitations": [
            "這是測試版本",
            "不實際調用 AI API",
            "不存儲到資料庫"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 啟動 NodePilot API 測試服務...")
    uvicorn.run(
        "test_main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )