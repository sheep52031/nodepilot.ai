"""
NodePilot 音頻處理服務
負責音頻轉錄、語意分析和學習內容生成
"""

import os
import tempfile
import logging
from typing import Optional, Dict, Any, BinaryIO
from openai import OpenAI
import json

logger = logging.getLogger("AudioProcessor")


class AudioProcessor:
    """音頻處理服務，整合轉錄和語意分析功能"""
    
    def __init__(self, api_key: Optional[str] = None):
        """初始化音頻處理器"""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.max_file_size = 20 * 1024 * 1024  # 20MB
        
        if not self.client:
            logger.warning("⚠️  未配置 OpenAI API Key，將使用模擬轉錄")
    
    async def process_audio_file(
        self,
        audio_file: BinaryIO,
        filename: str,
        language: str = "zh",
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        處理音頻檔案的完整流程
        
        Args:
            audio_file: 音頻檔案二進制流
            filename: 檔案名稱
            language: 語言代碼 (zh, en)
            user_context: 用戶上下文（困惑、選取文字等）
            
        Returns:
            處理結果字典，包含轉錄文本和語意分析
        """
        
        try:
            # 1. 檔案大小檢查
            audio_file.seek(0, 2)  # 移到檔案結尾
            file_size = audio_file.tell()
            audio_file.seek(0)  # 回到檔案開頭
            
            if file_size > self.max_file_size:
                raise ValueError(f"音頻檔案過大，限制 {self.max_file_size // (1024*1024)}MB")
            
            logger.info(f"🎵 開始處理音頻: {filename} ({file_size} bytes)")
            
            # 2. 音頻轉錄
            transcription_result = await self._transcribe_audio(
                audio_file, filename, language
            )
            
            # 3. 語意分析和結構化
            semantic_analysis = await self._analyze_audio_semantics(
                transcription_result["text"], user_context
            )
            
            # 4. 整合結果
            result = {
                "success": True,
                "transcription": {
                    "text": transcription_result["text"],
                    "language": transcription_result.get("language", language),
                    "confidence": transcription_result.get("confidence", 0.95),
                    "duration": transcription_result.get("duration"),
                    "model_used": transcription_result.get("model", "whisper-1")
                },
                "semantic_analysis": semantic_analysis,
                "processing_metadata": {
                    "file_size": file_size,
                    "filename": filename,
                    "processing_time": "computed_in_actual_implementation"
                }
            }
            
            logger.info("✅ 音頻處理完成")
            return result
            
        except Exception as e:
            logger.error(f"❌ 音頻處理失敗: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "fallback_result": self._generate_fallback_result(filename, user_context)
            }
    
    async def _transcribe_audio(
        self, 
        audio_file: BinaryIO, 
        filename: str, 
        language: str
    ) -> Dict[str, Any]:
        """音頻轉錄"""
        
        if not self.client:
            # 模擬轉錄結果
            logger.info("使用模擬轉錄")
            return {
                "text": "這是模擬的音頻轉錄內容。實際版本會調用 OpenAI Whisper API。",
                "language": language,
                "confidence": 0.85,
                "model": "mock_whisper"
            }
        
        try:
            # 保存臨時檔案
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                audio_file.seek(0)
                temp_file.write(audio_file.read())
                temp_path = temp_file.name
            
            # 調用 OpenAI Whisper API
            with open(temp_path, "rb") as audio_data:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_data,
                    language=language if language != "zh" else None,  # Whisper 自動檢測中文
                    response_format="json"
                )
            
            # 清理臨時檔案
            os.unlink(temp_path)
            
            return {
                "text": transcript.text,
                "language": language,
                "confidence": 0.95,  # Whisper 通常有很高的準確性
                "model": "whisper-1"
            }
            
        except Exception as e:
            logger.error(f"Whisper 轉錄失敗: {str(e)}")
            # 降級到模擬結果
            return {
                "text": f"轉錄服務暫時不可用。錯誤: {str(e)}",
                "language": language,
                "confidence": 0.0,
                "model": "fallback",
                "error": str(e)
            }
    
    async def _analyze_audio_semantics(
        self, 
        transcription: str, 
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """音頻語意分析和結構化"""
        
        if not self.client or not transcription.strip():
            return self._generate_mock_semantic_analysis(transcription, user_context)
        
        try:
            # 構建語意分析提示
            context_info = ""
            if user_context:
                context_info = f"""
用戶上下文資訊：
- 困惑筆記：{user_context.get('confusion_note', '')}
- 選取文字：{user_context.get('selected_text', '')}
- 頁面標題：{user_context.get('page_title', '')}
"""
            
            prompt = f"""請分析以下音頻轉錄內容，並結合用戶的學習需求進行語意結構化。

{context_info}

音頻轉錄內容：
{transcription}

請提供 JSON 格式的分析結果，包含：
1. structured_confusion: 用戶在音頻中表達的困惑點
2. learning_intent: 用戶的學習意圖和目標
3. key_concepts: 音頻中提到的關鍵概念
4. emotional_tone: 用戶的情緒狀態（困惑程度、學習動機等）
5. suggested_approach: 針對音頻內容的建議教學方式
"""
            
            completion = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一個專業的教育內容分析專家，專門分析學習者的音頻內容並提供個人化的教學建議。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            # 解析回應
            response_text = completion.choices[0].message.content
            try:
                analysis = json.loads(response_text)
            except json.JSONDecodeError:
                # 如果無法解析為 JSON，創建結構化結果
                analysis = {
                    "structured_confusion": "音頻分析結果",
                    "learning_intent": "理解相關概念",
                    "key_concepts": ["從音頻中提取的概念"],
                    "emotional_tone": "學習導向",
                    "suggested_approach": response_text,
                    "raw_analysis": response_text
                }
            
            analysis["model_used"] = "gpt-3.5-turbo"
            analysis["confidence"] = 0.85
            
            return analysis
            
        except Exception as e:
            logger.error(f"語意分析失敗: {str(e)}")
            return self._generate_mock_semantic_analysis(transcription, user_context, error=str(e))
    
    def _generate_mock_semantic_analysis(
        self, 
        transcription: str, 
        user_context: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成模擬的語意分析結果"""
        
        return {
            "structured_confusion": "從音頻中檢測到的學習困惑（模擬分析）",
            "learning_intent": "用戶希望深入理解相關技術概念",
            "key_concepts": ["音頻提及的概念1", "音頻提及的概念2"],
            "emotional_tone": "積極學習，有明確的問題導向",
            "suggested_approach": "結合實際範例和步驟說明的教學方式",
            "model_used": "mock_semantic_analyzer",
            "confidence": 0.60,
            "transcription_preview": transcription[:100] + "..." if len(transcription) > 100 else transcription,
            "mock_mode": True,
            "error": error
        }
    
    def _generate_fallback_result(
        self, 
        filename: str, 
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """生成降級結果"""
        
        return {
            "transcription": {
                "text": "音頻處理服務暫時不可用，請稍後重試。",
                "language": "unknown",
                "confidence": 0.0,
                "model_used": "fallback"
            },
            "semantic_analysis": {
                "structured_confusion": "無法分析音頻內容",
                "learning_intent": "用戶通過音頻提供了額外的學習需求",
                "suggested_approach": "基於文字標註進行教學內容生成",
                "fallback_mode": True
            },
            "processing_metadata": {
                "filename": filename,
                "fallback_reason": "音頻處理服務不可用"
            }
        }


# 創建全局音頻處理器實例
audio_processor = AudioProcessor()