"""
系統初始化器 - NodePilot AI 核心系統啟動
======================================

負責初始化多 Agent 系統和模型配置。
"""

import logging
import os
from typing import Optional, Dict, Any
from pathlib import Path

from .scheduler import AgentScheduler, AgentType
from .model_pool import ModelPool, ModelConfig, ModelType
from agents.planning_agent import PlanningAgent
from agents.context_analysis_agent import ContextAnalysisAgent
from agents.audio_semantic_agent import AudioSemanticAgent
from agents.note_retrieval_agent import NoteRetrievalAgent
from agents.teaching_generation_agent import TeachingGenerationAgent


class NodePilotSystemInitializer:
    """NodePilot AI 系統初始化器"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        
        # 系統元件
        self.model_pool: Optional[ModelPool] = None
        self.scheduler: Optional[AgentScheduler] = None
        
        # 配置
        self.system_config = self._load_system_config()
    
    def _load_system_config(self) -> Dict[str, Any]:
        """載入系統配置"""
        default_config = {
            "models": {
                "openai": {
                    "api_key": os.getenv("OPENAI_API_KEY"),
                    "base_url": "https://api.openai.com/v1",
                    "enabled": True
                },
                "anthropic": {
                    "api_key": os.getenv("ANTHROPIC_API_KEY"),
                    "base_url": "https://api.anthropic.com",
                    "enabled": True
                }
            },
            "agents": {
                "max_concurrent_executions": 5,
                "default_timeout": 30,
                "max_retries": 3
            },
            "context": {
                "max_context_tokens": 8000,
                "context_window_adjustment": True
            },
            "notes": {
                "database_path": "./data/notes.db",
                "embedding_model": "text-embedding-3-large",
                "max_retrieved_notes": 5
            }
        }
        
        if self.config_path and Path(self.config_path).exists():
            # TODO: 實作配置檔案讀取
            pass
        
        return default_config
    
    async def initialize(self) -> AgentScheduler:
        """初始化整個系統"""
        self.logger.info("正在初始化 NodePilot AI 核心系統...")
        
        # 1. 初始化模型池
        await self._initialize_model_pool()
        
        # 2. 初始化調度器
        await self._initialize_scheduler()
        
        # 3. 註冊 Agents
        await self._register_agents()
        
        # 4. 驗證系統
        await self._validate_system()
        
        self.logger.info("NodePilot AI 系統初始化完成")
        return self.scheduler
    
    async def _initialize_model_pool(self):
        """初始化模型池"""
        self.logger.info("初始化模型池...")
        
        self.model_pool = ModelPool()
        
        # 註冊 OpenAI 模型
        if self.system_config["models"]["openai"]["enabled"]:
            openai_key = self.system_config["models"]["openai"]["api_key"]
            if openai_key:
                await self._register_openai_models(openai_key)
            else:
                self.logger.warning("OpenAI API Key 未設定，跳過 OpenAI 模型")
        
        # 註冊 Anthropic 模型
        if self.system_config["models"]["anthropic"]["enabled"]:
            anthropic_key = self.system_config["models"]["anthropic"]["api_key"]
            if anthropic_key:
                await self._register_anthropic_models(anthropic_key)
            else:
                self.logger.warning("Anthropic API Key 未設定，跳過 Anthropic 模型")
        
        self.logger.info(f"模型池初始化完成，共註冊 {len(self.model_pool.models)} 個模型")
    
    async def _register_openai_models(self, api_key: str):
        """註冊 OpenAI 模型"""
        base_url = self.system_config["models"]["openai"]["base_url"]
        
        # GPT-4o
        gpt4o_config = ModelConfig(
            model_type=ModelType.GPT_4O,
            provider="openai",
            api_endpoint=f"{base_url}/chat/completions",
            api_key=api_key,
            max_tokens=4096,
            temperature=0.7,
            requests_per_minute=60,
            cost_per_1k_tokens=0.03,
            reliability_score=0.95,
            avg_response_time=5.0
        )
        self.model_pool.register_model(gpt4o_config)
        
        # GPT-4o Mini
        gpt4o_mini_config = ModelConfig(
            model_type=ModelType.GPT_4O_MINI,
            provider="openai",
            api_endpoint=f"{base_url}/chat/completions",
            api_key=api_key,
            max_tokens=2048,
            temperature=0.7,
            requests_per_minute=120,
            cost_per_1k_tokens=0.005,
            reliability_score=0.92,
            avg_response_time=3.0
        )
        self.model_pool.register_model(gpt4o_mini_config)
        
        # o1-preview
        o1_preview_config = ModelConfig(
            model_type=ModelType.O1_PREVIEW,
            provider="openai",
            api_endpoint=f"{base_url}/chat/completions",
            api_key=api_key,
            max_tokens=4096,
            temperature=1.0,  # o1 模型不支援 temperature 調整
            requests_per_minute=20,  # o1 模型限額較低
            cost_per_1k_tokens=0.15,
            reliability_score=0.98,
            avg_response_time=15.0  # o1 模型較慢
        )
        self.model_pool.register_model(o1_preview_config)
    
    async def _register_anthropic_models(self, api_key: str):
        """註冊 Anthropic 模型"""
        base_url = self.system_config["models"]["anthropic"]["base_url"]
        
        # Claude 3.5 Sonnet
        claude_sonnet_config = ModelConfig(
            model_type=ModelType.CLAUDE_3_5_SONNET,
            provider="anthropic",
            api_endpoint=f"{base_url}/v1/messages",
            api_key=api_key,
            max_tokens=4096,
            temperature=0.7,
            requests_per_minute=50,
            cost_per_1k_tokens=0.025,
            reliability_score=0.97,
            avg_response_time=4.0
        )
        self.model_pool.register_model(claude_sonnet_config)
        
        # Claude 3.5 Haiku
        claude_haiku_config = ModelConfig(
            model_type=ModelType.CLAUDE_3_5_HAIKU,
            provider="anthropic",
            api_endpoint=f"{base_url}/v1/messages",
            api_key=api_key,
            max_tokens=2048,
            temperature=0.7,
            requests_per_minute=100,
            cost_per_1k_tokens=0.01,
            reliability_score=0.94,
            avg_response_time=2.5
        )
        self.model_pool.register_model(claude_haiku_config)
    
    async def _initialize_scheduler(self):
        """初始化調度器"""
        self.logger.info("初始化 Agent 調度器...")
        
        if not self.model_pool:
            raise RuntimeError("模型池未初始化")
        
        self.scheduler = AgentScheduler(self.model_pool)
        
        # 配置調度器參數
        agent_config = self.system_config["agents"]
        # TODO: 設定調度器參數
    
    async def _register_agents(self):
        """註冊所有 Agents"""
        self.logger.info("註冊 Agents...")
        
        if not self.scheduler or not self.model_pool:
            raise RuntimeError("調度器或模型池未初始化")
        
        # 註冊任務規劃 Agent
        planning_agent = PlanningAgent(self.model_pool)
        self.scheduler.register_agent(AgentType.PLANNING, planning_agent)
        
        # 註冊上下文分析 Agent
        context_agent = ContextAnalysisAgent(self.model_pool)
        self.scheduler.register_agent(AgentType.CONTEXT_ANALYSIS, context_agent)
        
        # 註冊音訊語意 Agent
        audio_agent = AudioSemanticAgent(self.model_pool)
        self.scheduler.register_agent(AgentType.AUDIO_SEMANTIC, audio_agent)
        
        # 註冊筆記檢索 Agent
        notes_config = self.system_config["notes"]
        note_agent = NoteRetrievalAgent(
            self.model_pool, 
            notes_database_path=notes_config["database_path"]
        )
        self.scheduler.register_agent(AgentType.NOTE_RETRIEVAL, note_agent)
        
        # 註冊教學生成 Agent
        teaching_agent = TeachingGenerationAgent(self.model_pool)
        self.scheduler.register_agent(AgentType.TEACHING_GENERATION, teaching_agent)
        
        self.logger.info(f"已註冊 {len(self.scheduler._agents)} 個 Agents")
    
    async def _validate_system(self):
        """驗證系統完整性"""
        self.logger.info("驗證系統完整性...")
        
        # 檢查模型池
        if not self.model_pool or not self.model_pool.models:
            raise RuntimeError("沒有可用的模型")
        
        # 檢查調度器
        if not self.scheduler:
            raise RuntimeError("調度器未初始化")
        
        # 檢查 Agents
        required_agents = [
            AgentType.PLANNING,
            AgentType.CONTEXT_ANALYSIS,
            AgentType.TEACHING_GENERATION
        ]
        
        for agent_type in required_agents:
            if agent_type not in self.scheduler._agents:
                raise RuntimeError(f"必要的 Agent 未註冊: {agent_type.value}")
        
        self.logger.info("系統驗證通過")
    
    def get_system_status(self) -> Dict[str, Any]:
        """取得系統狀態"""
        status = {
            "initialized": self.scheduler is not None,
            "models_count": len(self.model_pool.models) if self.model_pool else 0,
            "agents_count": len(self.scheduler._agents) if self.scheduler else 0,
            "system_config": self.system_config
        }
        
        if self.model_pool:
            status["model_stats"] = self.model_pool.get_usage_stats()
        
        return status


# 全域系統實例
_system_instance: Optional[NodePilotSystemInitializer] = None


async def get_system() -> AgentScheduler:
    """取得初始化後的系統實例"""
    global _system_instance
    
    if _system_instance is None:
        _system_instance = NodePilotSystemInitializer()
        await _system_instance.initialize()
    
    return _system_instance.scheduler


async def initialize_system(config_path: Optional[str] = None) -> AgentScheduler:
    """初始化系統"""
    global _system_instance
    
    _system_instance = NodePilotSystemInitializer(config_path)
    return await _system_instance.initialize()


def get_system_status() -> Dict[str, Any]:
    """取得系統狀態"""
    if _system_instance:
        return _system_instance.get_system_status()
    else:
        return {"initialized": False}