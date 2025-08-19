"""
NodePilot 遠端 Voxtral Mini 3B 音頻處理服務
通過 ngrok 隧道連接到 RTX 3080 的 AnythingLLM API
"""

import os
import tempfile
import logging
import asyncio
import aiohttp
import base64
import json
from typing import Optional, Dict, Any, BinaryIO

logger = logging.getLogger("RemoteVoxtralProcessor")


class RemoteVoxtralProcessor:
    """遠端 Voxtral Mini 3B 音頻處理服務"""
    
    def __init__(self, api_url: Optional[str] = None, api_token: Optional[str] = None):
        """初始化遠端 Voxtral 處理器"""
        
        self.api_url = (api_url or os.getenv("VOXTRAL_REMOTE_API_URL", "")).rstrip('/')
        self.api_token = api_token or os.getenv("VOXTRAL_REMOTE_API_TOKEN", "")
        self.model_name = "voxtral-mini-3b-q4"
        self.max_file_size = 20 * 1024 * 1024  # 20MB
        self.timeout = 60  # 60 秒超時
        
        if not self.api_url or not self.api_token:
            logger.warning("⚠️  未配置遠端 Voxtral API，將使用模擬結果")
            self.is_ready = False
        else:
            logger.info(f"✅ 遠端 Voxtral 處理器初始化完成: {self.api_url}")
            self.is_ready = True
    
    async def process_audio_direct(
        self,
        audio_file: BinaryIO,
        filename: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        直接處理音頻檔案產生學習重點（遠端 API）
        """
        
        try:
            # 1. 檔案大小檢查
            audio_file.seek(0, 2)
            file_size = audio_file.tell()
            audio_file.seek(0)
            
            if file_size > self.max_file_size:
                raise ValueError(f"音頻檔案過大，限制 {self.max_file_size // (1024*1024)}MB")
            
            logger.info(f"🌐 開始遠端 Voxtral 處理: {filename} ({file_size} bytes)")
            
            if not self.is_ready:
                return self._generate_mock_result(filename, user_context)
            
            # 2. 編碼音頻檔案
            audio_data = base64.b64encode(audio_file.read()).decode('utf-8')
            
            # 3. 構建分析提示和請求
            analysis_prompt = self._build_analysis_prompt(user_context)
            
            payload = {
                "model": self.model_name,
                "audio_data": audio_data,
                "filename": filename,
                "task": "transcribe_and_analyze",
                "prompt": analysis_prompt,
                "context": user_context or {},
                "parameters": {
                    "max_tokens": 1000,
                    "temperature": 0.1,
                    "response_format": "structured_learning_points"
                }
            }
            
            # 4. 發送 API 請求
            start_time = asyncio.get_event_loop().time()
            
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "User-Agent": "NodePilot/1.0"
            }
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        f"{self.api_url}/api/v1/audio/transcribe",
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        
                        processing_time = asyncio.get_event_loop().time() - start_time
                        
                        if response.status == 200:
                            api_result = await response.json()
                            
                            # 5. 解析和標準化 API 結果
                            structured_result = self._parse_api_response(api_result, user_context)
                            
                            result = {
                                "success": True,
                                "method": "remote_voxtral_rtx3080",
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
                                    "model_used": self.model_name,
                                    "api_provider": "anythingllm_rtx3080",
                                    "remote_api": True,
                                    "response_status": response.status
                                }
                            }
                            
                            logger.info(f"✅ 遠端處理完成 ({processing_time:.2f}s)")
                            return result
                            
                        else:
                            error_text = await response.text()
                            raise Exception(f"API 請求失敗 ({response.status}): {error_text}")
                            
                except aiohttp.ClientError as e:
                    raise Exception(f"網路連接失敗: {str(e)}")
                except asyncio.TimeoutError:
                    raise Exception(f"API 請求超時 ({self.timeout}s)")
            
        except Exception as e:
            logger.error(f"❌ 遠端 Voxtral 處理失敗: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "fallback_result": self._generate_mock_result(filename, user_context)
            }
    
    def _build_analysis_prompt(self, user_context: Optional[Dict[str, Any]] = None) -> str:
        """構建音頻分析提示詞"""
        
        base_prompt = """請分析這段音頻並生成結構化的學習重點。

請按照以下格式回應：
{
  "transcription": "音頻的準確轉錄",
  "bullet_points": [
    "學習重點1：核心概念說明",
    "學習重點2：重要技術點",
    "學習重點3：實際應用方法"
  ],
  "learning_focus": "主要學習困惑和目標",
  "difficulty_level": "初級/中級/高級",
  "suggested_actions": [
    "具體學習建議1",
    "具體學習建議2"
  ],
  "key_concepts": ["概念1", "概念2", "概念3"]
}"""

        if user_context:
            context_info = []
            if user_context.get("confusion_note"):
                context_info.append(f"用戶困惑：{user_context['confusion_note']}")
            if user_context.get("selected_text"):
                context_info.append(f"相關文字：{user_context['selected_text'][:200]}")
            if user_context.get("page_title"):
                context_info.append(f"頁面標題：{user_context['page_title']}")
            
            if context_info:
                context_section = "請結合以下上下文進行分析：\n" + "\n".join(context_info) + "\n\n"
                return context_section + base_prompt
        
        return base_prompt
    
    def _parse_api_response(self, api_result: Dict[str, Any], user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """解析 API 回應結果"""
        
        try:
            # 嘗試解析結構化 JSON 回應
            if "response" in api_result:
                response_text = api_result["response"]
                
                # 如果回應是 JSON 字串，嘗試解析
                if response_text.strip().startswith("{"):
                    try:
                        structured_data = json.loads(response_text)
                        return self._validate_structured_response(structured_data)
                    except json.JSONDecodeError:
                        pass
                
                # 如果不是 JSON，嘗試解析文字格式
                return self._parse_text_response(response_text, user_context)
            
            # 直接使用 API 回應中的結構化數據
            elif "bullet_points" in api_result:
                return self._validate_structured_response(api_result)
            
            # 備案：使用整個回應作為轉錄內容
            else:
                return self._create_fallback_result(str(api_result), user_context)
                
        except Exception as e:
            logger.warning(f"API 回應解析失敗: {e}")
            return self._create_fallback_result("API 回應解析錯誤", user_context)
    
    def _validate_structured_response(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """驗證和標準化結構化回應"""
        
        return {
            "bullet_points": data.get("bullet_points", ["遠端音頻分析完成"]),
            "transcription": data.get("transcription", ""),
            "learning_focus": data.get("learning_focus", "技術概念理解"),
            "difficulty_level": data.get("difficulty_level", "中級"),
            "suggested_actions": data.get("suggested_actions", ["深入學習相關概念"]),
            "key_concepts": data.get("key_concepts", ["音頻分析", "遠端推理"])
        }
    
    def _parse_text_response(self, text: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """解析文字格式的回應"""
        
        lines = text.split('\n')
        result = {
            "bullet_points": [],
            "transcription": "",
            "learning_focus": "理解相關概念",
            "difficulty_level": "中級",
            "suggested_actions": [],
            "key_concepts": []
        }
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if any(keyword in line.lower() for keyword in ["轉錄", "transcription"]):
                current_section = "transcription"
                continue
            elif any(keyword in line.lower() for keyword in ["重點", "bullet", "要點"]):
                current_section = "bullet_points"
                continue
            elif any(keyword in line.lower() for keyword in ["焦點", "focus"]):
                current_section = "learning_focus"
                continue
            elif any(keyword in line.lower() for keyword in ["難度", "difficulty"]):
                current_section = "difficulty"
                continue
            elif any(keyword in line.lower() for keyword in ["建議", "action", "建議行動"]):
                current_section = "actions"
                continue
            
            # 處理內容
            if current_section == "bullet_points" and (line.startswith(("•", "-", "1.", "2.", "3.")) or line):
                if line.startswith(("•", "-")):
                    result["bullet_points"].append(line.lstrip("•- ").strip())
                elif line and not line.startswith("#"):
                    result["bullet_points"].append(line)
            elif current_section == "transcription" and line:
                result["transcription"] += line + " "
            elif current_section == "learning_focus" and line:
                result["learning_focus"] = line
            elif current_section == "difficulty" and line:
                result["difficulty_level"] = line
            elif current_section == "actions" and line:
                if line.startswith(("•", "-")):
                    result["suggested_actions"].append(line.lstrip("•- ").strip())
                elif line:
                    result["suggested_actions"].append(line)
        
        # 清理結果
        result["transcription"] = result["transcription"].strip()
        
        # 如果沒有找到要點，從所有行中提取
        if not result["bullet_points"]:
            bullet_candidates = [line.strip() for line in lines 
                               if line.strip() and not line.strip().startswith("#") and len(line.strip()) > 10]
            result["bullet_points"] = bullet_candidates[:5] if bullet_candidates else ["遠端音頻分析完成"]
        
        return result
    
    def _create_fallback_result(self, content: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """創建備案結果"""
        
        return {
            "bullet_points": [
                "遠端音頻處理完成", 
                f"內容摘要：{content[:50]}...",
                "請查看完整轉錄內容"
            ],
            "transcription": content[:500] + "..." if len(content) > 500 else content,
            "learning_focus": "技術概念理解",
            "difficulty_level": "中級",
            "suggested_actions": ["查看詳細分析結果"],
            "key_concepts": ["音頻分析", "遠端處理"]
        }
    
    def _generate_mock_result(self, filename: str, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成模擬的遠端結果"""
        
        mock_bullet_points = [
            "遠端 RTX 3080 音頻處理（模擬）",
            f"檔案 {filename} 分析完成",
            "AnythingLLM + Q4 量化模型測試"
        ]
        
        if user_context and user_context.get("confusion_note"):
            confusion = user_context["confusion_note"][:50]
            mock_bullet_points.insert(0, f"針對「{confusion}」的遠端分析")
        
        return {
            "success": True,
            "method": "remote_voxtral_mock",
            "bullet_points": mock_bullet_points,
            "transcription": "模擬遠端音頻轉錄：這是 RTX 3080 處理的測試結果。",
            "semantic_analysis": {
                "learning_focus": "遠端音頻理解測試",
                "difficulty_level": "中級",
                "suggested_actions": [
                    "配置 RTX 3080 遠端 API",
                    "測試 ngrok 隧道連接"
                ],
                "key_concepts": ["遠端推理", "RTX 3080", "AnythingLLM"]
            },
            "processing_metadata": {
                "filename": filename,
                "processing_time": 2.8,
                "model_used": "voxtral_remote_mock",
                "api_provider": "mock_rtx3080",
                "mock_mode": True
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """檢查遠端 API 健康狀態"""
        
        if not self.is_ready:
            return {"status": "unavailable", "reason": "API 未配置"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/api/health",
                    headers={"Authorization": f"Bearer {self.api_token}"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    if response.status == 200:
                        return {"status": "healthy", "api_url": self.api_url}
                    else:
                        return {"status": "error", "code": response.status}
                        
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}


# 創建全局遠端 Voxtral 處理器實例
remote_voxtral_processor = RemoteVoxtralProcessor()