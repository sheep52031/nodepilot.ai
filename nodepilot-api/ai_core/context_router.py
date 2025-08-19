"""
上下文路由器 - 智慧上下文感知和動態路由
======================================

負責在 Agent 間傳遞和轉換上下文資料，實現動態上下文範圍調整。
"""

import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum

from .execution_plan import TaskNode
from .scheduler import AgentExecutionContext, AgentType


class ContextType(Enum):
    """上下文類型"""
    USER_INPUT = "user_input"           # 用戶輸入
    SELECTED_TEXT = "selected_text"     # 選取文字
    PAGE_CONTEXT = "page_context"       # 頁面上下文
    AUDIO_TRANSCRIPTION = "audio"       # 音訊轉錄
    ARTICLE_STRUCTURE = "article"       # 文章結構
    CONFUSION_ANALYSIS = "confusion"    # 困惑分析
    NOTE_RETRIEVAL = "notes"           # 筆記檢索
    TEACHING_CONTENT = "teaching"       # 教學內容


@dataclass
class ContextWindow:
    """上下文視窗"""
    context_type: ContextType
    data: Dict[str, Any]
    relevance_score: float = 0.0       # 相關性評分 0.0-1.0
    token_count: int = 0               # 預估 token 數量
    priority: int = 1                  # 優先級 1-5
    source_agent: Optional[AgentType] = None
    

class ContextRouter:
    """
    上下文路由器
    
    功能:
    - Agent 間上下文資料傳遞
    - 動態上下文範圍調整
    - 上下文相關性評估
    - 記憶體使用最佳化
    """
    
    def __init__(self, max_context_tokens: int = 8000):
        self.max_context_tokens = max_context_tokens
        self.logger = logging.getLogger(__name__)
        
        # 上下文優先級映射
        self.agent_context_needs = {
            AgentType.PLANNING: [
                ContextType.USER_INPUT, 
                ContextType.SELECTED_TEXT, 
                ContextType.PAGE_CONTEXT,
                ContextType.AUDIO_TRANSCRIPTION
            ],
            AgentType.CONTEXT_ANALYSIS: [
                ContextType.SELECTED_TEXT,
                ContextType.PAGE_CONTEXT,
                ContextType.USER_INPUT
            ],
            AgentType.AUDIO_SEMANTIC: [
                ContextType.AUDIO_TRANSCRIPTION,
                ContextType.USER_INPUT,
                ContextType.SELECTED_TEXT
            ],
            AgentType.NOTE_RETRIEVAL: [
                ContextType.USER_INPUT,
                ContextType.CONFUSION_ANALYSIS,
                ContextType.SELECTED_TEXT
            ],
            AgentType.TEACHING_GENERATION: [
                ContextType.USER_INPUT,
                ContextType.SELECTED_TEXT,
                ContextType.ARTICLE_STRUCTURE,
                ContextType.CONFUSION_ANALYSIS,
                ContextType.NOTE_RETRIEVAL,
                ContextType.AUDIO_TRANSCRIPTION
            ]
        }
    
    async def route_context(
        self,
        target_task: TaskNode,
        previous_results: Dict[str, AgentExecutionContext]
    ) -> Dict[str, Any]:
        """
        為目標任務路由合適的上下文
        
        Args:
            target_task: 目標任務節點
            previous_results: 之前執行的結果
            
        Returns:
            路由後的上下文資料
        """
        target_agent = target_task.agent_type
        
        # 收集可用的上下文視窗
        available_contexts = await self._collect_available_contexts(
            target_task, previous_results
        )
        
        # 篩選相關的上下文類型
        relevant_contexts = self._filter_relevant_contexts(
            target_agent, available_contexts
        )
        
        # 評估上下文相關性
        scored_contexts = await self._score_context_relevance(
            target_task, relevant_contexts
        )
        
        # 動態調整上下文範圍
        optimized_contexts = self._optimize_context_window(
            scored_contexts, target_task
        )
        
        # 格式化為 Agent 可用的格式
        routed_context = self._format_context_for_agent(
            target_agent, optimized_contexts
        )
        
        self.logger.info(
            f"Routed {len(optimized_contexts)} contexts to {target_agent.value} "
            f"(total tokens: {sum(ctx.token_count for ctx in optimized_contexts)})"
        )
        
        return routed_context
    
    async def _collect_available_contexts(
        self,
        target_task: TaskNode,
        previous_results: Dict[str, AgentExecutionContext]
    ) -> List[ContextWindow]:
        """收集可用的上下文視窗"""
        contexts = []
        
        # 從任務輸入中提取基礎上下文
        task_inputs = target_task.inputs
        
        if "user_confusion" in task_inputs:
            contexts.append(ContextWindow(
                context_type=ContextType.USER_INPUT,
                data={"confusion": task_inputs["user_confusion"]},
                token_count=self._estimate_tokens(task_inputs["user_confusion"]),
                priority=5
            ))
        
        if "selected_text" in task_inputs:
            contexts.append(ContextWindow(
                context_type=ContextType.SELECTED_TEXT,
                data={"text": task_inputs["selected_text"]},
                token_count=self._estimate_tokens(task_inputs["selected_text"]),
                priority=4
            ))
        
        if "page_context" in task_inputs:
            contexts.append(ContextWindow(
                context_type=ContextType.PAGE_CONTEXT,
                data=task_inputs["page_context"],
                token_count=self._estimate_tokens(str(task_inputs["page_context"])),
                priority=3
            ))
        
        if "audio_transcription" in task_inputs:
            contexts.append(ContextWindow(
                context_type=ContextType.AUDIO_TRANSCRIPTION,
                data={"transcription": task_inputs["audio_transcription"]},
                token_count=self._estimate_tokens(task_inputs["audio_transcription"]),
                priority=4
            ))
        
        # 從之前的 Agent 結果中提取上下文
        for execution_ctx in previous_results.values():
            if not execution_ctx.result:
                continue
            
            ctx_type = self._map_agent_result_to_context_type(execution_ctx.agent_type)
            if ctx_type:
                contexts.append(ContextWindow(
                    context_type=ctx_type,
                    data=execution_ctx.result,
                    token_count=self._estimate_tokens(str(execution_ctx.result)),
                    priority=2,
                    source_agent=execution_ctx.agent_type
                ))
        
        return contexts
    
    def _filter_relevant_contexts(
        self,
        target_agent: AgentType,
        contexts: List[ContextWindow]
    ) -> List[ContextWindow]:
        """篩選與目標 Agent 相關的上下文"""
        needed_types = set(self.agent_context_needs.get(target_agent, []))
        
        return [ctx for ctx in contexts if ctx.context_type in needed_types]
    
    async def _score_context_relevance(
        self,
        target_task: TaskNode,
        contexts: List[ContextWindow]
    ) -> List[ContextWindow]:
        """評估上下文相關性並評分"""
        for context in contexts:
            # 基礎評分基於優先級
            base_score = context.priority / 5.0
            
            # 根據 Agent 類型調整評分
            agent_boost = self._get_agent_context_boost(
                target_task.agent_type, context.context_type
            )
            
            # 根據資料新鮮度調整評分
            freshness_boost = 1.0 if context.source_agent else 0.8
            
            # 計算最終相關性評分
            context.relevance_score = min(1.0, base_score * agent_boost * freshness_boost)
        
        # 按相關性評分排序
        contexts.sort(key=lambda ctx: ctx.relevance_score, reverse=True)
        
        return contexts
    
    def _get_agent_context_boost(
        self, 
        agent_type: AgentType, 
        context_type: ContextType
    ) -> float:
        """取得 Agent 對特定上下文類型的偏好加成"""
        boost_map = {
            AgentType.PLANNING: {
                ContextType.USER_INPUT: 1.2,
                ContextType.AUDIO_TRANSCRIPTION: 1.1,
                ContextType.SELECTED_TEXT: 1.0,
                ContextType.PAGE_CONTEXT: 0.9
            },
            AgentType.CONTEXT_ANALYSIS: {
                ContextType.SELECTED_TEXT: 1.3,
                ContextType.PAGE_CONTEXT: 1.2,
                ContextType.USER_INPUT: 1.0
            },
            AgentType.AUDIO_SEMANTIC: {
                ContextType.AUDIO_TRANSCRIPTION: 1.5,
                ContextType.USER_INPUT: 1.1,
                ContextType.SELECTED_TEXT: 0.9
            },
            AgentType.NOTE_RETRIEVAL: {
                ContextType.USER_INPUT: 1.2,
                ContextType.CONFUSION_ANALYSIS: 1.3,
                ContextType.SELECTED_TEXT: 1.0
            },
            AgentType.TEACHING_GENERATION: {
                ContextType.USER_INPUT: 1.3,
                ContextType.SELECTED_TEXT: 1.2,
                ContextType.ARTICLE_STRUCTURE: 1.2,
                ContextType.CONFUSION_ANALYSIS: 1.1,
                ContextType.NOTE_RETRIEVAL: 1.1,
                ContextType.AUDIO_TRANSCRIPTION: 1.0
            }
        }
        
        return boost_map.get(agent_type, {}).get(context_type, 1.0)
    
    def _optimize_context_window(
        self,
        contexts: List[ContextWindow],
        target_task: TaskNode
    ) -> List[ContextWindow]:
        """動態最佳化上下文視窗大小"""
        selected_contexts = []
        total_tokens = 0
        
        # 預留一些 token 給 Agent 的回應
        available_tokens = self.max_context_tokens - 1000
        
        for context in contexts:
            if total_tokens + context.token_count <= available_tokens:
                selected_contexts.append(context)
                total_tokens += context.token_count
            else:
                # 嘗試截斷上下文資料
                remaining_tokens = available_tokens - total_tokens
                if remaining_tokens > 100 and context.relevance_score > 0.7:
                    truncated_context = self._truncate_context(
                        context, remaining_tokens
                    )
                    if truncated_context:
                        selected_contexts.append(truncated_context)
                        break
        
        self.logger.info(
            f"Optimized context window: {len(selected_contexts)} contexts, "
            f"{total_tokens} tokens"
        )
        
        return selected_contexts
    
    def _truncate_context(
        self, 
        context: ContextWindow, 
        max_tokens: int
    ) -> Optional[ContextWindow]:
        """截斷上下文資料以符合 token 限制"""
        if context.context_type == ContextType.SELECTED_TEXT:
            # 對於選取文字，保留前後部分
            text = context.data.get("text", "")
            words = text.split()
            
            # 簡單估算：假設平均每個 token 1.3 個字
            max_words = int(max_tokens * 1.3)
            
            if len(words) <= max_words:
                return context
            
            # 保留前半和後半
            half_words = max_words // 2
            truncated_text = (
                " ".join(words[:half_words]) + 
                " ... [truncated] ... " + 
                " ".join(words[-half_words:])
            )
            
            return ContextWindow(
                context_type=context.context_type,
                data={"text": truncated_text, "truncated": True},
                relevance_score=context.relevance_score * 0.9,  # 略降分數
                token_count=max_tokens,
                priority=context.priority,
                source_agent=context.source_agent
            )
        
        return None
    
    def _format_context_for_agent(
        self,
        agent_type: AgentType,
        contexts: List[ContextWindow]
    ) -> Dict[str, Any]:
        """格式化上下文資料供 Agent 使用"""
        formatted = {
            "metadata": {
                "total_contexts": len(contexts),
                "total_tokens": sum(ctx.token_count for ctx in contexts),
                "context_types": [ctx.context_type.value for ctx in contexts]
            }
        }
        
        # 按類型組織上下文資料
        for context in contexts:
            ctx_key = context.context_type.value
            
            if ctx_key not in formatted:
                formatted[ctx_key] = []
            
            formatted[ctx_key].append({
                "data": context.data,
                "relevance_score": context.relevance_score,
                "source_agent": context.source_agent.value if context.source_agent else None,
                "token_count": context.token_count
            })
        
        return formatted
    
    def _map_agent_result_to_context_type(self, agent_type: AgentType) -> Optional[ContextType]:
        """將 Agent 結果映射到上下文類型"""
        mapping = {
            AgentType.CONTEXT_ANALYSIS: ContextType.ARTICLE_STRUCTURE,
            AgentType.AUDIO_SEMANTIC: ContextType.CONFUSION_ANALYSIS,
            AgentType.NOTE_RETRIEVAL: ContextType.NOTE_RETRIEVAL,
            AgentType.TEACHING_GENERATION: ContextType.TEACHING_CONTENT
        }
        return mapping.get(agent_type)
    
    def _estimate_tokens(self, text: str) -> int:
        """簡單估算文字的 token 數量"""
        if not text:
            return 0
        
        # 簡化估算：英文約 4 字符/token，中文約 1.5 字符/token
        char_count = len(text)
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        english_chars = char_count - chinese_chars
        
        estimated_tokens = (chinese_chars / 1.5) + (english_chars / 4)
        
        return int(estimated_tokens)