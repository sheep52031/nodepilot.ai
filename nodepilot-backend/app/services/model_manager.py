"""
NodePilot 模型管理系統
支援可切換模型架構、Fallback 機制和成本控制
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import openai
import os
from dotenv import load_dotenv

load_dotenv()


class ModelProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic" 
    LOCAL = "local"


class ModelType(Enum):
    PLANNER = "planner"          # 任務規劃模型 (GPT-4o/Claude 3.5)
    CONTENT_GENERATOR = "content_generator"  # 教學生成模型 (Claude 4.0/GPT-5)
    AUDIO_PROCESSOR = "audio_processor"      # Whisper
    CONTEXT_ANALYZER = "context_analyzer"    # 文章分析模型
    RAG_RETRIEVER = "rag_retriever"         # 筆記檢索模型


@dataclass
class ModelConfig:
    """模型配置"""
    model_id: str
    provider: ModelProvider
    model_type: ModelType
    api_key_env: str
    max_tokens: int = 1000
    temperature: float = 0.7
    cost_per_1k_tokens: float = 0.0
    rate_limit_per_minute: int = 60
    timeout_seconds: int = 30
    is_primary: bool = True
    is_available: bool = True


@dataclass
class ModelUsage:
    """模型使用統計"""
    model_id: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_response_time: float = 0.0
    last_used: Optional[datetime] = None
    
    def update_usage(self, tokens: int, response_time: float, success: bool = True):
        """更新使用統計"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        self.total_tokens += tokens
        self.total_cost += (tokens / 1000) * self.get_cost_per_1k_tokens()
        
        # 更新平均回應時間
        if self.avg_response_time == 0:
            self.avg_response_time = response_time
        else:
            self.avg_response_time = (self.avg_response_time + response_time) / 2
        
        self.last_used = datetime.now()
    
    def get_cost_per_1k_tokens(self) -> float:
        # 這裡可以從配置中獲取
        return 0.002  # 預設值


class BaseModelClient(ABC):
    """模型客戶端基礎類"""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.usage = ModelUsage(model_id=config.model_id)
        self.logger = logging.getLogger(f"Model.{config.model_id}")
        self._last_request_time = 0
        self._request_count_minute = 0
        
    @abstractmethod
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """生成內容"""
        pass
        
    async def is_available(self) -> bool:
        """檢查模型可用性"""
        try:
            test_response = await self.generate([
                {"role": "user", "content": "test"}
            ], max_tokens=5)
            return True
        except Exception:
            return False
    
    def _check_rate_limit(self) -> bool:
        """檢查速率限制"""
        current_time = time.time()
        if current_time - self._last_request_time > 60:
            self._request_count_minute = 0
            
        return self._request_count_minute < self.config.rate_limit_per_minute
        
    def _update_rate_limit(self):
        """更新速率限制計數"""
        self._request_count_minute += 1
        self._last_request_time = time.time()


class OpenAIModelClient(BaseModelClient):
    """OpenAI 模型客戶端"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.client = openai.AsyncOpenAI(
            api_key=os.getenv(config.api_key_env)
        )
        
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        if not self._check_rate_limit():
            raise Exception("Rate limit exceeded")
            
        start_time = time.time()
        
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model_id,
                messages=messages,
                max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                temperature=kwargs.get('temperature', self.config.temperature),
                timeout=self.config.timeout_seconds
            )
            
            response_time = time.time() - start_time
            tokens_used = response.usage.total_tokens
            
            # 更新使用統計
            self.usage.update_usage(tokens_used, response_time, True)
            self._update_rate_limit()
            
            return {
                "content": response.choices[0].message.content,
                "tokens_used": tokens_used,
                "response_time": response_time,
                "model": self.config.model_id
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            self.usage.update_usage(0, response_time, False)
            self.logger.error(f"OpenAI API 調用失敗: {e}")
            raise e


class WhisperClient(BaseModelClient):
    """Whisper 音檔轉錄客戶端"""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.client = openai.AsyncOpenAI(
            api_key=os.getenv(config.api_key_env)
        )
    
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Whisper 不支援聊天格式，這個方法不會被使用"""
        raise NotImplementedError("Whisper 使用 transcribe 方法，不是 generate")
    
    async def transcribe(self, audio_file, language: str = "zh") -> Dict[str, Any]:
        start_time = time.time()
        
        try:
            response = await self.client.audio.transcriptions.create(
                model=self.config.model_id,
                file=audio_file,
                language=language,
                temperature=0.0
            )
            
            response_time = time.time() - start_time
            # Whisper 按分鐘計費，這裡簡化處理
            self.usage.update_usage(100, response_time, True)  # 估算 token
            
            return {
                "transcription": response.text,
                "response_time": response_time,
                "model": self.config.model_id
            }
            
        except Exception as e:
            response_time = time.time() - start_time
            self.usage.update_usage(0, response_time, False)
            raise e


class ModelManager:
    """模型管理器"""
    
    def __init__(self):
        self.models: Dict[str, BaseModelClient] = {}
        self.model_configs: Dict[ModelType, List[ModelConfig]] = {}
        self.logger = logging.getLogger("ModelManager")
        self._initialize_default_models()
        
    def _initialize_default_models(self):
        """初始化預設模型配置"""
        
        # GPT-4o 作為任務規劃主要模型
        gpt4_config = ModelConfig(
            model_id="gpt-4o",
            provider=ModelProvider.OPENAI,
            model_type=ModelType.PLANNER,
            api_key_env="OPENAI_API_KEY",
            max_tokens=2000,
            temperature=0.3,
            cost_per_1k_tokens=0.015,
            is_primary=True
        )
        
        # GPT-3.5 作為備援模型
        gpt35_config = ModelConfig(
            model_id="gpt-3.5-turbo",
            provider=ModelProvider.OPENAI,
            model_type=ModelType.PLANNER,
            api_key_env="OPENAI_API_KEY",
            max_tokens=1000,
            temperature=0.3,
            cost_per_1k_tokens=0.002,
            is_primary=False
        )
        
        # Whisper 音檔轉錄
        whisper_config = ModelConfig(
            model_id="whisper-1",
            provider=ModelProvider.OPENAI,
            model_type=ModelType.AUDIO_PROCESSOR,
            api_key_env="OPENAI_API_KEY",
            cost_per_1k_tokens=0.006  # Whisper 按分鐘計費，這裡簡化
        )
        
        # 註冊模型配置
        self.register_model_config(gpt4_config)
        self.register_model_config(gpt35_config)
        self.register_model_config(whisper_config)
        
    def register_model_config(self, config: ModelConfig):
        """註冊模型配置"""
        if config.model_type not in self.model_configs:
            self.model_configs[config.model_type] = []
            
        self.model_configs[config.model_type].append(config)
        
        # 建立模型客戶端
        if config.provider == ModelProvider.OPENAI:
            if config.model_type == ModelType.AUDIO_PROCESSOR:
                client = WhisperClient(config)
            else:
                client = OpenAIModelClient(config)
                
            self.models[config.model_id] = client
            
        self.logger.info(f"已註冊模型: {config.model_id} ({config.model_type.value})")
    
    def get_available_models(self, model_type: ModelType) -> List[ModelConfig]:
        """獲取指定類型的可用模型"""
        if model_type not in self.model_configs:
            return []
            
        available_models = []
        for config in self.model_configs[model_type]:
            if config.is_available and config.model_id in self.models:
                available_models.append(config)
                
        # 按優先級排序 (主要模型優先)
        return sorted(available_models, key=lambda x: not x.is_primary)
    
    async def get_best_model(self, model_type: ModelType) -> Optional[BaseModelClient]:
        """獲取最佳可用模型"""
        available_models = self.get_available_models(model_type)
        
        for config in available_models:
            client = self.models.get(config.model_id)
            if client and await client.is_available():
                return client
                
        return None
    
    async def generate_with_fallback(self, 
                                   model_type: ModelType, 
                                   messages: List[Dict[str, str]], 
                                   **kwargs) -> Dict[str, Any]:
        """帶降級機制的內容生成"""
        available_models = self.get_available_models(model_type)
        
        last_error = None
        for config in available_models:
            client = self.models.get(config.model_id)
            if not client:
                continue
                
            try:
                result = await client.generate(messages, **kwargs)
                self.logger.info(f"成功使用模型: {config.model_id}")
                return result
                
            except Exception as e:
                self.logger.warning(f"模型 {config.model_id} 調用失敗: {e}")
                last_error = e
                continue
        
        # 所有模型都失敗
        raise Exception(f"所有 {model_type.value} 模型都不可用。最後錯誤: {last_error}")
    
    async def transcribe_with_fallback(self, audio_file, language: str = "zh") -> Dict[str, Any]:
        """帶降級機制的音檔轉錄"""
        whisper_models = self.get_available_models(ModelType.AUDIO_PROCESSOR)
        
        for config in whisper_models:
            client = self.models.get(config.model_id)
            if isinstance(client, WhisperClient):
                try:
                    return await client.transcribe(audio_file, language)
                except Exception as e:
                    self.logger.warning(f"Whisper 模型 {config.model_id} 轉錄失敗: {e}")
                    continue
        
        raise Exception("所有 Whisper 模型都不可用")
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """獲取使用統計"""
        stats = {
            "models": {},
            "total_requests": 0,
            "total_cost": 0.0,
            "total_tokens": 0
        }
        
        for model_id, client in self.models.items():
            usage = client.usage
            stats["models"][model_id] = {
                "total_requests": usage.total_requests,
                "successful_requests": usage.successful_requests,
                "failed_requests": usage.failed_requests,
                "success_rate": usage.successful_requests / max(usage.total_requests, 1),
                "total_tokens": usage.total_tokens,
                "total_cost": usage.total_cost,
                "avg_response_time": usage.avg_response_time,
                "last_used": usage.last_used.isoformat() if usage.last_used else None
            }
            
            stats["total_requests"] += usage.total_requests
            stats["total_cost"] += usage.total_cost
            stats["total_tokens"] += usage.total_tokens
        
        return stats
    
    def set_model_availability(self, model_id: str, available: bool):
        """設定模型可用性"""
        for model_type_configs in self.model_configs.values():
            for config in model_type_configs:
                if config.model_id == model_id:
                    config.is_available = available
                    self.logger.info(f"模型 {model_id} 可用性設為: {available}")
                    return
        
        self.logger.warning(f"未找到模型: {model_id}")


# 全域模型管理器實例
model_manager = ModelManager()