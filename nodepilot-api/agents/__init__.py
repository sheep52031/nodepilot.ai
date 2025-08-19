"""
NodePilot Agents - 多 Agent 系統實作
===================================

各種專門化的 Agent 實作，支援 Plan-and-Execute 協作模式。

Agent 類型:
- PlanningAgent: 任務規劃和分解
- ContextAnalysisAgent: 文章上下文分析
- AudioSemanticAgent: 音訊語意結構化
- NoteRetrievalAgent: RAG 筆記檢索
- TeachingGenerationAgent: 教學內容生成
"""

from .base_agent import BaseAgent, AgentExecutionResult
from .planning_agent import PlanningAgent
from .context_analysis_agent import ContextAnalysisAgent
from .audio_semantic_agent import AudioSemanticAgent
from .note_retrieval_agent import NoteRetrievalAgent
from .teaching_generation_agent import TeachingGenerationAgent

__all__ = [
    "BaseAgent",
    "AgentExecutionResult",
    "PlanningAgent",
    "ContextAnalysisAgent", 
    "AudioSemanticAgent",
    "NoteRetrievalAgent",
    "TeachingGenerationAgent"
]