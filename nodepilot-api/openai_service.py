import openai
import os
from dotenv import load_dotenv
from functools import wraps
import logging
import time
import tempfile
from typing import Optional
from fastapi import UploadFile

load_dotenv()

class NodePilotAIService:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.default_model = "gpt-3.5-turbo"
        self.logger = logging.getLogger(__name__)
        
    def retry_decorator(self, max_retries=3, base_delay=1):
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                retries = 0
                while retries < max_retries:
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        retries += 1
                        if retries == max_retries:
                            self.logger.error(f"OpenAI API 調用失敗: {e}")
                            raise
                        wait_time = base_delay * (2 ** retries)
                        time.sleep(wait_time)
            return wrapper
        return decorator

    @retry_decorator
    def generate_teaching_content(self, url: str, selected_text: str, confusion_note: str) -> str:
        """生成個人化教學內容"""
        
        system_prompt = """你是一位專業的程式設計導師，專門為 NodePilot 學習平台提供個人化教學內容。
        
        你的任務是：
        1. 針對學習者的具體困惑提供直接、準確的解答
        2. 用簡潔易懂的方式解釋相關技術概念
        3. 提供實用的程式碼範例（如適用）
        4. 給出進一步學習的建議
        
        請用繁體中文回答，保持專業但友善的語調。"""

        user_prompt = f"""
**文章來源**: {url}
**選取的程式碼/文字**: 
```
{selected_text}
```

**學習者的困惑**: {confusion_note}

請針對這個困惑生成個人化的教學說明。
"""

        try:
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except openai.RateLimitError:
            return "目前 AI 服務使用量較高，請稍後再試。"
        except openai.APIConnectionError:
            return "網路連線問題，請檢查網路連線後重試。"
        except Exception as e:
            self.logger.error(f"生成教學內容失敗: {e}")
            return "抱歉，目前無法生成教學內容，請稍後再試。"
    
    @retry_decorator
    def transcribe_audio(self, audio_file) -> Optional[str]:
        """使用 Whisper API 轉錄音檔"""
        try:
            # 創建臨時檔案
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
                # 如果是 UploadFile，讀取內容
                if hasattr(audio_file, 'read'):
                    content = audio_file.read()
                    if hasattr(audio_file, 'seek'):
                        audio_file.seek(0)  # 重置指標
                else:
                    content = audio_file
                
                temp_file.write(content)
                temp_file.flush()
                
                # 調用 Whisper API
                with open(temp_file.name, 'rb') as f:
                    response = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=f,
                        language="zh",
                        temperature=0.0
                    )
                
                # 清理臨時檔案
                os.unlink(temp_file.name)
                
                return response.text
                
        except Exception as e:
            self.logger.error(f"音檔轉錄失敗: {e}")
            return None

    @retry_decorator
    def generate_cognitive_note(self, transcription: str, selected_text: str, confusion_note: str) -> Optional[str]:
        """將音檔轉錄轉換為結構化的認知記錄"""
        
        system_prompt = """你是一位專業的學習分析師，專門將學習者的語音困惑轉換為清晰的認知記錄。
        
        你的任務是：
        1. 分析語音轉錄內容，提取核心困惑點
        2. 結合文字困惑描述，總結學習者的真實需求
        3. 用結構化的方式記錄認知狀態
        4. 識別可能的知識盲點和學習方向
        
        請用繁體中文，以簡潔清晰的方式整理認知記錄。"""

        user_prompt = f"""
**選取文字**: {selected_text}

**文字困惑描述**: {confusion_note}

**語音轉錄內容**: 
{transcription}

請將以上資訊整理成結構化的認知記錄，包含：
- 核心困惑點
- 具體需要理解的概念
- 學習者的當前認知狀態
"""

        try:
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            self.logger.error(f"生成認知記錄失敗: {e}")
            return None
    
    def test_connection(self) -> bool:
        """測試 OpenAI API 連接"""
        try:
            response = self.client.chat.completions.create(
                model=self.default_model,
                messages=[{"role": "user", "content": "測試"}],
                max_tokens=5
            )
            return True
        except Exception:
            return False

# 全域服務實例
ai_service = NodePilotAIService()