"""
Agent 基礎類別 - 所有 Agent 的共同介面和實作
=========================================

定義標準的 Agent 執行介面和共用功能。
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from ai_core.model_pool import ModelPool, ModelType
from ai_core.scheduler import AgentExecutionContext


@dataclass
class AgentExecutionResult:
    """Agent 執行結果"""
    success: bool
    result: Dict[str, Any]
    error: Optional[str] = None
    model_used: Optional[ModelType] = None
    execution_time: float = 0.0
    sources: List[str] = None
    confidence_score: float = 0.0
    
    def __post_init__(self):
        if self.sources is None:
            self.sources = []


class BaseAgent(ABC):
    """
    Agent 基礎類別
    
    提供所有 Agent 的共同介面和實作。
    """
    
    def __init__(self, model_pool: ModelPool, agent_name: str):
        self.model_pool = model_pool
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"agents.{agent_name}")
        
        # Agent 配置
        self.max_retries = 3
        self.timeout_seconds = 30
        
    @abstractmethod
    async def execute(self, context: AgentExecutionContext) -> AgentExecutionResult:
        """
        執行 Agent 任務
        
        Args:
            context: Agent 執行上下文
            
        Returns:
            Agent 執行結果
        """
        pass
    
    @abstractmethod
    def get_task_type(self) -> str:
        """取得 Agent 的任務類型 (用於模型選擇)"""
        pass
    
    @abstractmethod
    async def _process_context(self, context: AgentExecutionContext) -> Dict[str, Any]:
        """
        處理執行上下文，準備 Agent 所需的輸入資料
        
        Args:
            context: 執行上下文
            
        Returns:
            處理後的輸入資料
        """
        pass
    
    @abstractmethod
    async def _generate_prompt(self, processed_input: Dict[str, Any]) -> str:
        """
        生成模型 prompt
        
        Args:
            processed_input: 處理後的輸入資料
            
        Returns:
            模型 prompt
        """
        pass
    
    @abstractmethod
    async def _parse_model_response(self, response: str) -> Dict[str, Any]:
        """
        解析模型回應
        
        Args:
            response: 模型原始回應
            
        Returns:
            解析後的結構化結果
        """
        pass
    
    async def _execute_with_model(
        self, 
        context: AgentExecutionContext,
        priority: str = "balanced"
    ) -> AgentExecutionResult:
        """
        使用模型執行任務的通用流程
        
        Args:
            context: 執行上下文
            priority: 模型選擇優先級
            
        Returns:
            執行結果
        """
        start_time = datetime.utcnow()
        
        try:
            # 處理輸入上下文
            processed_input = await self._process_context(context)
            
            # 生成 prompt
            prompt = await self._generate_prompt(processed_input)
            
            # 估算 context 大小
            context_size = self._estimate_context_size(prompt)
            
            # 執行模型請求
            model_result = await self.model_pool.execute_with_fallback(
                task_type=self.get_task_type(),
                request_func=lambda model: self._call_model_api(model, prompt),
                context_size=context_size,
                max_retries=self.max_retries
            )
            
            if not model_result["success"]:
                return AgentExecutionResult(
                    success=False,
                    result={},
                    error=model_result.get("error", "Model execution failed")
                )
            
            # 解析模型回應
            parsed_result = await self._parse_model_response(
                model_result["result"]
            )
            
            # 計算執行時間
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # 評估結果品質
            confidence_score = await self._evaluate_result_quality(parsed_result)
            
            return AgentExecutionResult(
                success=True,
                result=parsed_result,
                model_used=ModelType(model_result.get("model_used", "")),
                execution_time=execution_time,
                sources=self._extract_sources(parsed_result),
                confidence_score=confidence_score
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.logger.error(f"{self.agent_name} execution failed: {str(e)}")
            
            return AgentExecutionResult(
                success=False,
                result={},
                error=str(e),
                execution_time=execution_time
            )
    
    async def _call_model_api(self, model_config, prompt: str) -> str:
        """
        調用模型 API
        
        Args:
            model_config: 模型配置
            prompt: 輸入 prompt
            
        Returns:
            模型回應
        """
        # 這裡是簡化的實作，實際應該根據不同 provider 調用對應的 API
        # 在 MVP 階段，可以先整合 OpenAI 和 Anthropic 的 API
        
        if model_config.provider == "openai":
            return await self._call_openai_api(model_config, prompt)
        elif model_config.provider == "anthropic":
            return await self._call_anthropic_api(model_config, prompt)
        else:
            raise ValueError(f"Unsupported provider: {model_config.provider}")
    
    async def _call_openai_api(self, model_config, prompt: str) -> str:
        """調用 OpenAI API"""
        # TODO: 實作 OpenAI API 調用
        # 暫時返回模擬回應
        return f"OpenAI response for {self.agent_name}: {prompt[:100]}..."
    
    async def _call_anthropic_api(self, model_config, prompt: str) -> str:
        """調用 Anthropic API"""
        # TODO: 實作 Anthropic API 調用
        # 暫時返回模擬回應
        return f"Anthropic response for {self.agent_name}: {prompt[:100]}..."
    
    def _estimate_context_size(self, prompt: str) -> int:
        """估算 prompt 的 token 大小"""
        # 簡化估算：英文約 4 字符/token，中文約 1.5 字符/token
        char_count = len(prompt)
        chinese_chars = sum(1 for c in prompt if '\u4e00' <= c <= '\u9fff')
        english_chars = char_count - chinese_chars
        
        estimated_tokens = (chinese_chars / 1.5) + (english_chars / 4)
        return int(estimated_tokens)
    
    async def _evaluate_result_quality(self, result: Dict[str, Any]) -> float:
        """評估結果品質"""
        # 基礎品質評估
        if not result:
            return 0.0
        
        quality_score = 0.5  # 基礎分數
        
        # 檢查結果完整性
        if len(str(result)) > 100:
            quality_score += 0.2
        
        # 檢查是否有錯誤標記
        if result.get("error"):
            quality_score -= 0.3
        
        # 檢查是否有主要內容
        main_content_keys = ["content", "analysis", "teaching_content", "plan"]
        if any(key in result for key in main_content_keys):
            quality_score += 0.3
        
        return min(1.0, max(0.0, quality_score))
    
    def _extract_sources(self, result: Dict[str, Any]) -> List[str]:
        """從結果中提取資料來源"""
        sources = []
        
        # 檢查常見的 source 欄位
        if "sources" in result:
            if isinstance(result["sources"], list):
                sources.extend(result["sources"])
            elif isinstance(result["sources"], str):
                sources.append(result["sources"])
        
        # 檢查 metadata 中的 sources
        metadata = result.get("metadata", {})
        if "sources" in metadata:
            if isinstance(metadata["sources"], list):
                sources.extend(metadata["sources"])
        
        return sources
    
    def _create_error_result(self, error_message: str) -> AgentExecutionResult:
        """建立錯誤結果"""
        return AgentExecutionResult(
            success=False,
            result={},
            error=error_message,
            confidence_score=0.0
        )