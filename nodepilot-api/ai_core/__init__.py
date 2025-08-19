"""
NodePilot AI Core - 多 Agent 調度系統
=============================================

純 Python 實作的 Plan-and-Execute 多 Agent 架構，
避免 LangChain/CrewAI 依賴，提供靈活的模型池管理和結果整合。

核心元件:
- AgentScheduler: 主要調度器
- ExecutionPlan: 任務規劃和分解
- ModelPool: 可切換模型池管理
- ContextRouter: 上下文感知路由
- ResultIntegrator: 結果整合器
"""

from .scheduler import AgentScheduler
from .execution_plan import ExecutionPlan, TaskNode
from .model_pool import ModelPool, ModelType
from .context_router import ContextRouter
from .result_integrator import ResultIntegrator

__version__ = "0.1.0"
__author__ = "NodePilot AI-CORE Team"

__all__ = [
    "AgentScheduler",
    "ExecutionPlan", 
    "TaskNode",
    "ModelPool",
    "ModelType",
    "ContextRouter",
    "ResultIntegrator"
]