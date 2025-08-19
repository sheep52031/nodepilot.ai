"""
模型池管理 - 可切換模型架構和 Fallback 系統
==========================================

支援多模型動態切換、fallback 機制和成本控制。
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import aiohttp


class ModelType(Enum):
    """模型類型"""
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini" 
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20241022"
    CLAUDE_3_5_HAIKU = "claude-3-5-haiku-20241022"
    O1_PREVIEW = "o1-preview"
    O1_MINI = "o1-mini"
    
    # 本地模型備援
    LLAMA_70B = "llama-70b-local"
    WHISPER_LOCAL = "whisper-local"


@dataclass
class ModelConfig:
    """模型配置"""
    model_type: ModelType
    provider: str  # "openai", "anthropic", "local"
    api_endpoint: str
    api_key: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    
    # 限額管理
    requests_per_minute: int = 60
    cost_per_1k_tokens: float = 0.01
    
    # 品質和效能
    reliability_score: float = 0.95  # 0.0-1.0
    avg_response_time: float = 5.0   # seconds
    
    # 狀態追蹤
    is_available: bool = True
    last_error: Optional[str] = None
    error_count: int = 0
    last_used: Optional[datetime] = None


@dataclass 
class ModelUsageStats:
    """模型使用統計"""
    model_type: ModelType
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_response_time: float = 0.0
    last_24h_requests: int = 0
    

class ModelPool:
    """
    模型池管理器
    
    功能:
    - 模型註冊和配置管理
    - 動態模型選擇和 fallback
    - 請求限額和成本控制
    - 效能監控和品質評估
    """
    
    def __init__(self):
        self.models: Dict[ModelType, ModelConfig] = {}
        self.usage_stats: Dict[ModelType, ModelUsageStats] = {}
        self.fallback_chains: Dict[str, List[ModelType]] = {}
        self.logger = logging.getLogger(__name__)
        
        # 請求追蹤
        self._request_history: Dict[ModelType, List[datetime]] = {}
        self._circuit_breaker: Dict[ModelType, bool] = {}
        
        # 初始化預設 fallback 鏈
        self._setup_default_fallbacks()
    
    def register_model(self, config: ModelConfig):
        """註冊模型配置"""
        self.models[config.model_type] = config
        self.usage_stats[config.model_type] = ModelUsageStats(config.model_type)
        self._request_history[config.model_type] = []
        self._circuit_breaker[config.model_type] = False
        
        self.logger.info(f"Registered model: {config.model_type.value}")
    
    def _setup_default_fallbacks(self):
        """設定預設 fallback 鏈"""
        self.fallback_chains = {
            "planning": [ModelType.GPT_4O, ModelType.CLAUDE_3_5_SONNET, ModelType.O1_PREVIEW],
            "context_analysis": [ModelType.CLAUDE_3_5_SONNET, ModelType.GPT_4O, ModelType.CLAUDE_3_5_HAIKU],
            "audio_semantic": [ModelType.CLAUDE_3_5_SONNET, ModelType.GPT_4O_MINI],
            "note_retrieval": [ModelType.GPT_4O_MINI, ModelType.CLAUDE_3_5_HAIKU],
            "teaching_generation": [ModelType.CLAUDE_3_5_SONNET, ModelType.GPT_4O, ModelType.O1_PREVIEW],
            "result_integration": [ModelType.GPT_4O, ModelType.CLAUDE_3_5_SONNET]
        }
    
    async def get_best_model(
        self, 
        task_type: str, 
        context_size: int = 0,
        priority: str = "balanced"  # "speed", "quality", "cost", "balanced"
    ) -> Optional[ModelConfig]:
        """
        取得最適合的模型
        
        Args:
            task_type: 任務類型 (planning, context_analysis, etc.)
            context_size: 上下文大小 (tokens)
            priority: 優先考量 (速度/品質/成本/平衡)
            
        Returns:
            最適合的模型配置，如果都不可用則返回 None
        """
        candidates = self.fallback_chains.get(task_type, list(self.models.keys()))
        
        for model_type in candidates:
            model = self.models.get(model_type)
            if not model:
                continue
            
            # 檢查模型可用性
            if not await self._is_model_available(model_type):
                continue
            
            # 檢查 context 大小限制
            if context_size > model.max_tokens:
                continue
            
            # 檢查請求限額
            if not await self._check_rate_limit(model_type):
                continue
            
            # 根據優先級評分
            if await self._evaluate_model_fitness(model, priority):
                return model
        
        self.logger.warning(f"No available model for task_type: {task_type}")
        return None
    
    async def _is_model_available(self, model_type: ModelType) -> bool:
        """檢查模型是否可用"""
        # 檢查斷路器狀態
        if self._circuit_breaker.get(model_type, False):
            return False
        
        model = self.models.get(model_type)
        if not model or not model.is_available:
            return False
        
        # 檢查錯誤計數
        if model.error_count >= 5:  # 連續失敗5次則暫時停用
            return False
        
        return True
    
    async def _check_rate_limit(self, model_type: ModelType) -> bool:
        """檢查請求限額"""
        model = self.models.get(model_type)
        if not model:
            return False
        
        now = datetime.utcnow()
        history = self._request_history.get(model_type, [])
        
        # 清理超過1分鐘的請求記錄
        recent_requests = [req_time for req_time in history 
                          if now - req_time < timedelta(minutes=1)]
        self._request_history[model_type] = recent_requests
        
        # 檢查是否超過限額
        return len(recent_requests) < model.requests_per_minute
    
    async def _evaluate_model_fitness(self, model: ModelConfig, priority: str) -> bool:
        """評估模型適合度"""
        stats = self.usage_stats.get(model.model_type)
        if not stats:
            return True  # 新模型，給予機會
        
        if priority == "speed":
            return model.avg_response_time <= 10.0
        elif priority == "quality":
            success_rate = stats.successful_requests / max(stats.total_requests, 1)
            return success_rate >= 0.9 and model.reliability_score >= 0.9
        elif priority == "cost":
            return model.cost_per_1k_tokens <= 0.02
        else:  # balanced
            success_rate = stats.successful_requests / max(stats.total_requests, 1)
            return (success_rate >= 0.8 and 
                   model.avg_response_time <= 15.0 and 
                   model.cost_per_1k_tokens <= 0.05)
    
    async def execute_with_fallback(
        self,
        task_type: str,
        request_func: Callable,
        context_size: int = 0,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        執行請求並自動 fallback
        
        Args:
            task_type: 任務類型
            request_func: 請求函數，接收 ModelConfig 作為參數
            context_size: 上下文大小
            max_retries: 最大重試次數
            
        Returns:
            執行結果
        """
        candidates = self.fallback_chains.get(task_type, list(self.models.keys()))
        last_error = None
        
        for model_type in candidates:
            model = await self.get_best_model(task_type, context_size)
            if not model:
                continue
            
            for retry in range(max_retries):
                try:
                    # 記錄請求
                    await self._record_request_start(model.model_type)
                    
                    # 執行請求
                    start_time = datetime.utcnow()
                    result = await request_func(model)
                    end_time = datetime.utcnow()
                    
                    # 記錄成功
                    response_time = (end_time - start_time).total_seconds()
                    await self._record_request_success(model.model_type, response_time, result)
                    
                    return {
                        "success": True,
                        "result": result,
                        "model_used": model.model_type.value,
                        "response_time": response_time
                    }
                
                except Exception as e:
                    last_error = str(e)
                    await self._record_request_failure(model.model_type, last_error)
                    
                    self.logger.warning(
                        f"Model {model.model_type.value} failed (retry {retry + 1}/{max_retries}): {e}"
                    )
                    
                    if retry == max_retries - 1:
                        break  # 嘗試下一個模型
        
        # 所有模型都失敗
        return {
            "success": False,
            "error": f"All models failed. Last error: {last_error}",
            "fallback_exhausted": True
        }
    
    async def _record_request_start(self, model_type: ModelType):
        """記錄請求開始"""
        now = datetime.utcnow()
        self._request_history[model_type].append(now)
        
        model = self.models[model_type]
        model.last_used = now
    
    async def _record_request_success(
        self, 
        model_type: ModelType, 
        response_time: float, 
        result: Any
    ):
        """記錄請求成功"""
        stats = self.usage_stats[model_type]
        stats.total_requests += 1
        stats.successful_requests += 1
        
        # 更新平均回應時間
        stats.avg_response_time = (
            (stats.avg_response_time * (stats.successful_requests - 1) + response_time) / 
            stats.successful_requests
        )
        
        # 重置錯誤計數和斷路器
        model = self.models[model_type]
        model.error_count = 0
        self._circuit_breaker[model_type] = False
    
    async def _record_request_failure(self, model_type: ModelType, error: str):
        """記錄請求失敗"""
        stats = self.usage_stats[model_type]
        stats.total_requests += 1
        stats.failed_requests += 1
        
        model = self.models[model_type]
        model.error_count += 1
        model.last_error = error
        
        # 觸發斷路器
        if model.error_count >= 3:
            self._circuit_breaker[model_type] = True
            self.logger.warning(f"Circuit breaker activated for {model_type.value}")
    
    def get_usage_stats(self) -> Dict[str, Dict[str, Any]]:
        """取得使用統計"""
        return {
            model_type.value: {
                "total_requests": stats.total_requests,
                "success_rate": stats.successful_requests / max(stats.total_requests, 1),
                "avg_response_time": stats.avg_response_time,
                "total_cost": stats.total_cost,
                "is_available": self.models[model_type].is_available,
                "circuit_breaker": self._circuit_breaker.get(model_type, False)
            }
            for model_type, stats in self.usage_stats.items()
        }