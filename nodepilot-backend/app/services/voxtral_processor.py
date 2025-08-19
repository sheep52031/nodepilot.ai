"""
NodePilot Voxtral Mini 3B 音頻處理服務
使用 Replicate API 直接從音頻產生學習重點 bullet points
"""

import os
import tempfile
import logging
import asyncio
from typing import Optional, Dict, Any, BinaryIO, List
import replicate

logger = logging.getLogger("VoxtralProcessor")


class VoxtralProcessor:
    """Voxtral Mini 3B 音頻處理服務，直接生成 bullet points"""
    
    def __init__(self, api_token: Optional[str] = None):
        """初始化 Voxtral 處理器"""
        self.api_token = api_token or os.getenv("REPLICATE_API_TOKEN")
        self.model_version = "mistralai/voxtral-mini-3b:f5a2a8bcd86d1eb11fc27e73e52be3446ba6902bfe4a5a74e92b079639949930"
        self.max_file_size = 20 * 1024 * 1024  # 20MB
        
        if not self.api_token:
            logger.warning("⚠️  未配置 REPLICATE_API_TOKEN，將使用模擬結果")
        else:
            logger.info("✅ Voxtral Mini 3B 處理器初始化完成")
    
    async def process_audio_direct(
        self,
        audio_file: BinaryIO,
        filename: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        直接處理音頻檔案產生學習重點
        
        Args:
            audio_file: 音頻檔案二進制流
            filename: 檔案名稱
            user_context: 用戶上下文（困惑、選取文字等）
            
        Returns:
            處理結果字典，包含 bullet points 和分析結果
        """
        
        try:
            # 1. 檔案大小檢查
            audio_file.seek(0, 2)
            file_size = audio_file.tell()
            audio_file.seek(0)
            
            if file_size > self.max_file_size:
                raise ValueError(f"音頻檔案過大，限制 {self.max_file_size // (1024*1024)}MB")
            
            logger.info(f"🎵 開始 Voxtral 處理音頻: {filename} ({file_size} bytes)")
            
            if not self.api_token:
                return self._generate_mock_result(filename, user_context)
            
            # 2. 構建 Voxtral 提示詞
            prompt = self._build_analysis_prompt(user_context)
            
            # 3. 調用 Replicate API
            input_data = {
                "audio": audio_file,
                "prompt": prompt
            }
            
            start_time = asyncio.get_event_loop().time()
            
            # 使用 async API 調用
            output = await replicate.async_run(
                self.model_version,
                input=input_data
            )
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            # 4. 解析和結構化結果
            structured_result = self._parse_voxtral_output(output, user_context)
            
            result = {
                "success": True,
                "method": "voxtral_direct",
                "bullet_points": structured_result["bullet_points"],
                "transcription": structured_result.get("transcription", ""),
                "semantic_analysis": {
                    "learning_focus": structured_result["learning_focus"],
                    "difficulty_level": structured_result["difficulty_level"],
                    "suggested_actions": structured_result["suggested_actions"],
                    "key_concepts": structured_result["key_concepts"]
                },
                "processing_metadata": {
                    "file_size": file_size,
                    "filename": filename,
                    "processing_time": round(processing_time, 2),
                    "model_used": "voxtral-mini-3b",
                    "api_provider": "replicate"
                }
            }
            
            logger.info(f"✅ Voxtral 處理完成 ({processing_time:.2f}s)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Voxtral 處理失敗: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "fallback_result": self._generate_mock_result(filename, user_context)
            }
    
    def _build_analysis_prompt(self, user_context: Optional[Dict[str, Any]] = None) -> str:
        """構建 Voxtral 分析提示詞"""
        
        base_prompt = """請分析這段音頻並生成學習重點。輸出格式：

## 音頻轉錄
[音頻內容的文字轉錄]

## 學習重點 (3-5個bullet points)
• [重點1：具體學習要點]
• [重點2：重要概念或技術點]  
• [重點3：實際應用或範例]

## 學習焦點
[用戶的主要困惑和學習意圖]

## 難度評估
[初級/中級/高級]

## 建議行動
• [具體的學習建議1]
• [具體的學習建議2]"""

        if user_context:
            context_info = []
            if user_context.get("confusion_note"):
                context_info.append(f"用戶困惑：{user_context['confusion_note']}")
            if user_context.get("selected_text"):
                context_info.append(f"選取文字：{user_context['selected_text'][:200]}")
            if user_context.get("page_title"):
                context_info.append(f"頁面標題：{user_context['page_title']}")
            
            if context_info:
                context_section = "請結合以下上下文進行分析：\n" + "\n".join(context_info) + "\n\n"
                return context_section + base_prompt
        
        return base_prompt
    
    def _parse_voxtral_output(self, output: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """解析 Voxtral 輸出結果"""
        
        try:
            # 基本解析邏輯（可根據實際輸出格式調整）
            lines = output.split('\n')
            
            result = {
                "bullet_points": [],
                "transcription": "",
                "learning_focus": "理解相關技術概念",
                "difficulty_level": "中級",
                "suggested_actions": [],
                "key_concepts": []
            }
            
            current_section = None
            
            for line in lines:
                line = line.strip()
                
                if "## 音頻轉錄" in line or "transcription" in line.lower():
                    current_section = "transcription"
                    continue
                elif "## 學習重點" in line or "bullet" in line.lower():
                    current_section = "bullet_points"
                    continue
                elif "## 學習焦點" in line or "focus" in line.lower():
                    current_section = "learning_focus"
                    continue
                elif "## 難度評估" in line or "difficulty" in line.lower():
                    current_section = "difficulty"
                    continue
                elif "## 建議行動" in line or "actions" in line.lower():
                    current_section = "actions"
                    continue
                
                # 處理內容
                if current_section == "bullet_points" and (line.startswith("•") or line.startswith("-")):
                    result["bullet_points"].append(line.lstrip("•- ").strip())
                elif current_section == "transcription" and line:
                    result["transcription"] += line + " "
                elif current_section == "learning_focus" and line:
                    result["learning_focus"] = line
                elif current_section == "difficulty" and line:
                    result["difficulty_level"] = line
                elif current_section == "actions" and (line.startswith("•") or line.startswith("-")):
                    result["suggested_actions"].append(line.lstrip("•- ").strip())
            
            # 如果解析失敗，使用簡單的備案
            if not result["bullet_points"]:
                # 嘗試從原始輸出中提取要點
                bullet_candidates = [line.strip() for line in lines if line.strip().startswith(("•", "-", "1.", "2.", "3."))]
                result["bullet_points"] = bullet_candidates[:5] if bullet_candidates else ["音頻分析完成，請查看詳細內容"]
            
            # 清理轉錄結果
            result["transcription"] = result["transcription"].strip()
            
            return result
            
        except Exception as e:
            logger.warning(f"解析 Voxtral 輸出失敗: {e}")
            return {
                "bullet_points": ["解析音頻內容", "提取學習重點", "生成個人化建議"],
                "transcription": output[:200] + "..." if len(output) > 200 else output,
                "learning_focus": "技術概念理解",
                "difficulty_level": "中級",
                "suggested_actions": ["深入學習相關概念"],
                "key_concepts": []
            }
    
    def _generate_mock_result(self, filename: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成模擬的 Voxtral 結果"""
        
        mock_bullet_points = [
            "音頻中提到的核心技術概念需要進一步理解",
            "實際應用場景和使用方式值得深入探討",
            "與現有知識的連結和差異分析"
        ]
        
        if user_context and user_context.get("confusion_note"):
            confusion = user_context["confusion_note"][:50]
            mock_bullet_points.insert(0, f"針對「{confusion}」的具體解答和說明")
        
        return {
            "success": True,
            "method": "voxtral_mock",
            "bullet_points": mock_bullet_points,
            "transcription": "模擬音頻轉錄：這是一段關於技術概念的說明，用戶表達了學習困惑並希望得到解答。",
            "semantic_analysis": {
                "learning_focus": "理解技術概念和實際應用",
                "difficulty_level": "中級",
                "suggested_actions": [
                    "閱讀相關技術文檔",
                    "尋找實際範例和應用"
                ],
                "key_concepts": ["技術概念", "實際應用", "學習方法"]
            },
            "processing_metadata": {
                "filename": filename,
                "processing_time": 2.5,
                "model_used": "voxtral_mock",
                "api_provider": "mock",
                "mock_mode": True
            }
        }


# 創建全局 Voxtral 處理器實例
voxtral_processor = VoxtralProcessor()