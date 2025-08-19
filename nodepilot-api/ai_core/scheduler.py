"""
Agent 調度器 - 多 Agent 系統的核心調度器
==========================================

負責 Plan-and-Execute 模式的任務分解、Agent 調度和結果整合。
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from .execution_plan import ExecutionPlan, TaskNode, TaskStatus
from .model_pool import ModelPool
from .context_router import ContextRouter
from .result_integrator import ResultIntegrator


class AgentType(Enum):
    """Agent 類型定義"""
    PLANNING = "planning"           # 任務規劃 Agent
    CONTEXT_ANALYSIS = "context"   # 上下文分析 Agent
    AUDIO_SEMANTIC = "audio"       # 音訊語意 Agent
    NOTE_RETRIEVAL = "notes"       # 筆記檢索 Agent (RAG)
    TEACHING_GENERATION = "teaching"  # 教學生成 Agent


@dataclass
class AgentExecutionContext:
    """Agent 執行上下文"""
    agent_id: str
    agent_type: AgentType
    task_node: TaskNode
    inputs: Dict[str, Any]
    context_data: Dict[str, Any] = field(default_factory=dict)
    execution_start: Optional[datetime] = None
    execution_end: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AgentScheduler:
    """
    多 Agent 調度器
    
    實作 Plan-and-Execute 模式：
    1. 接收用戶困惑和上下文
    2. 規劃 Agent 執行計畫
    3. 調度 Agent 並行/序列執行
    4. 整合結果並輸出
    """
    
    def __init__(self, model_pool: ModelPool):
        self.model_pool = model_pool
        self.context_router = ContextRouter()
        self.result_integrator = ResultIntegrator()
        self.logger = logging.getLogger(__name__)
        self._active_executions: Dict[str, AgentExecutionContext] = {}
        
        # Agent 實例註冊 (延遲載入)
        self._agents: Dict[AgentType, Any] = {}
    
    def register_agent(self, agent_type: AgentType, agent_instance):
        """註冊 Agent 實例"""
        self._agents[agent_type] = agent_instance
        self.logger.info(f"Registered agent: {agent_type.value}")
    
    async def execute_user_request(
        self, 
        user_confusion: str,
        selected_text: str,
        page_context: Dict[str, Any],
        audio_transcription: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        執行用戶請求的主入口點
        
        Args:
            user_confusion: 用戶困惑描述
            selected_text: 選取的文字
            page_context: 頁面上下文 (URL, title, etc.)
            audio_transcription: 音訊轉錄 (可選)
            
        Returns:
            整合後的教學結果
        """
        execution_id = str(uuid.uuid4())
        self.logger.info(f"Starting execution {execution_id}")
        
        try:
            # Step 1: 規劃執行計畫
            execution_plan = await self._create_execution_plan(
                user_confusion, selected_text, page_context, audio_transcription
            )
            
            # Step 2: 執行 Agent 協作
            execution_results = await self._execute_plan(execution_plan)
            
            # Step 3: 整合結果
            final_result = await self.result_integrator.integrate_results(
                execution_results, execution_plan
            )
            
            self.logger.info(f"Execution {execution_id} completed successfully")
            return final_result
            
        except Exception as e:
            self.logger.error(f"Execution {execution_id} failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "execution_id": execution_id
            }
    
    async def _create_execution_plan(
        self,
        user_confusion: str,
        selected_text: str, 
        page_context: Dict[str, Any],
        audio_transcription: Optional[str]
    ) -> ExecutionPlan:
        """使用 Planning Agent 建立執行計畫"""
        
        planning_agent = self._agents.get(AgentType.PLANNING)
        if not planning_agent:
            raise ValueError("Planning Agent not registered")
        
        planning_input = {
            "user_confusion": user_confusion,
            "selected_text": selected_text,
            "page_context": page_context,
            "audio_transcription": audio_transcription
        }
        
        # 調用 Planning Agent
        plan_result = await planning_agent.create_plan(planning_input)
        
        return ExecutionPlan.from_plan_result(plan_result)
    
    async def _execute_plan(self, plan: ExecutionPlan) -> Dict[str, AgentExecutionContext]:
        """執行 Agent 計畫"""
        results = {}
        
        # 按執行順序處理任務節點
        for task_batch in plan.get_execution_batches():
            # 並行執行同一批次的任務
            batch_tasks = []
            for task_node in task_batch:
                task = self._execute_agent_task(task_node, results)
                batch_tasks.append(task)
            
            # 等待批次完成
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # 處理批次結果
            for i, result in enumerate(batch_results):
                task_node = task_batch[i]
                if isinstance(result, Exception):
                    self.logger.error(f"Task {task_node.task_id} failed: {str(result)}")
                    task_node.status = TaskStatus.FAILED
                    task_node.error = str(result)
                else:
                    results[task_node.task_id] = result
                    task_node.status = TaskStatus.COMPLETED
        
        return results
    
    async def _execute_agent_task(
        self, 
        task_node: TaskNode, 
        previous_results: Dict[str, AgentExecutionContext]
    ) -> AgentExecutionContext:
        """執行單一 Agent 任務"""
        
        agent = self._agents.get(task_node.agent_type)
        if not agent:
            raise ValueError(f"Agent {task_node.agent_type.value} not registered")
        
        # 建立執行上下文
        execution_context = AgentExecutionContext(
            agent_id=str(uuid.uuid4()),
            agent_type=task_node.agent_type,
            task_node=task_node,
            inputs=task_node.inputs,
            execution_start=datetime.utcnow()
        )
        
        # 路由上下文資料
        routed_context = await self.context_router.route_context(
            task_node, previous_results
        )
        execution_context.context_data = routed_context
        
        try:
            # 執行 Agent
            task_node.status = TaskStatus.RUNNING
            result = await agent.execute(execution_context)
            
            execution_context.result = result
            execution_context.execution_end = datetime.utcnow()
            
            self.logger.info(f"Agent {task_node.agent_type.value} completed task {task_node.task_id}")
            
        except Exception as e:
            execution_context.error = str(e)
            execution_context.execution_end = datetime.utcnow()
            self.logger.error(f"Agent {task_node.agent_type.value} failed: {str(e)}")
            raise
        
        return execution_context
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """取得執行狀態 (用於 UI 進度顯示)"""
        context = self._active_executions.get(execution_id)
        if not context:
            return None
        
        return {
            "execution_id": execution_id,
            "agent_type": context.agent_type.value,
            "status": context.task_node.status.value,
            "start_time": context.execution_start,
            "end_time": context.execution_end,
            "error": context.error
        }