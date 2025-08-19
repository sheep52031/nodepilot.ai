from abc import ABC, abstractmethod
from typing import Optional
import openai
import os
from dotenv import load_dotenv

load_dotenv()

class AIProvider(ABC):
    """AI 服務提供者抽象介面"""
    
    @abstractmethod
    def generate_teaching_content(self, url: str, selected_text: str, confusion_note: str) -> str:
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        pass

class OpenAIProvider(AIProvider):
    """OpenAI API 提供者"""
    
    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo"):
        self.client = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model
    
    def generate_teaching_content(self, url: str, selected_text: str, confusion_note: str) -> str:
        system_prompt = """你是專業的程式設計導師，為 NodePilot 學習平台提供個人化教學內容。"""
        
        user_prompt = f"""
**文章來源**: {url}
**選取文字**: {selected_text}
**困惑**: {confusion_note}

請生成教學說明。
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"OpenAI 生成失敗: {str(e)}"
    
    def test_connection(self) -> bool:
        try:
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return True
        except:
            return False

class AIService:
    """AI 服務管理器"""
    
    def __init__(self, provider_type: str = "openai"):
        self.provider = self._create_provider(provider_type)
    
    def _create_provider(self, provider_type: str) -> AIProvider:
        """工廠方法建立 AI 提供者"""
        if provider_type == "openai":
            return OpenAIProvider()
        # 未來可擴充其他供應商
        else:
            raise ValueError(f"不支援的 AI 提供者: {provider_type}")
    
    def generate_teaching_content(self, url: str, selected_text: str, confusion_note: str) -> str:
        return self.provider.generate_teaching_content(url, selected_text, confusion_note)
    
    def test_connection(self) -> bool:
        return self.provider.test_connection()

# 全域服務實例
ai_service = AIService(provider_type=os.getenv("AI_PROVIDER", "openai"))