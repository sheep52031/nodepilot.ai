"""
NodePilot 純 Python 多 Agent 調度系統
避免 LangChain/CrewAI 依賴，實作 Plan-and-Execute 模式
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime
import json
import uuid


# 任務狀態定義
class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Agent 類型定義
class AgentType(Enum):
    PLANNER = "planner"              # 任務規劃 Agent
    CONTEXT_ANALYZER = "context_analyzer"  # 文章上下文分析 Agent
    AUDIO_PROCESSOR = "audio_processor"    # 音訊語意結構化 Agent
    RAG_RETRIEVER = "rag_retriever"       # 筆記檢索 Agent
    CONTENT_GENERATOR = "content_generator" # 教學內容生成 Agent


@dataclass
class AgentTask:
    """Agent 任務資料結構"""
    task_id: str
    agent_type: AgentType
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if isinstance(self.task_id, type(None)):
            self.task_id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        data = asdict(self)
        data['agent_type'] = self.agent_type.value
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return data


@dataclass 
class AgentContext:
    """Agent 間通信的上下文資料"""
    session_id: str
    user_input: Dict[str, Any]
    intermediate_results: Dict[str, Any]
    final_result: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if not hasattr(self, 'intermediate_results') or self.intermediate_results is None:
            self.intermediate_results = {}


class BaseAgent(ABC):
    """Agent 基礎類別"""
    
    def __init__(self, agent_type: AgentType):
        self.agent_type = agent_type
        self.logger = logging.getLogger(f"Agent.{agent_type.value}")
        self.is_healthy = True
        
    @abstractmethod
    async def execute(self, task: AgentTask, context: AgentContext) -> Dict[str, Any]:
        """執行 Agent 任務"""
        pass
        
    async def health_check(self) -> bool:
        """健康檢查"""
        return self.is_healthy
        
    def get_dependencies(self) -> List[AgentType]:
        """獲取依賴的其他 Agent"""
        return []


class AgentScheduler:
    """多 Agent 調度器"""
    
    def __init__(self):
        self.agents: Dict[AgentType, BaseAgent] = {}
        self.task_queue: List[AgentTask] = []
        self.running_tasks: Dict[str, AgentTask] = {}
        self.completed_tasks: Dict[str, AgentTask] = {}
        self.logger = logging.getLogger("AgentScheduler")
        self.max_concurrent_tasks = 5
        self.fallback_handlers: Dict[AgentType, Callable] = {}
        
    def register_agent(self, agent: BaseAgent):
        """註冊 Agent"""
        self.agents[agent.agent_type] = agent
        self.logger.info(f"已註冊 Agent: {agent.agent_type.value}")
        
    def register_fallback_handler(self, agent_type: AgentType, handler: Callable):
        """註冊降級處理器"""
        self.fallback_handlers[agent_type] = handler
        
    async def create_plan(self, user_request: Dict[str, Any]) -> List[AgentTask]:
        """
        Plan-and-Execute 模式：創建任務執行計劃
        根據用戶困惑自動生成 Agent 任務序列
        """
        session_id = str(uuid.uuid4())
        tasks = []
        
        # 1. 任務規劃 Agent - 分析用戶需求
        planner_task = AgentTask(
            task_id=f"{session_id}_planner",
            agent_type=AgentType.PLANNER,
            input_data={
                "user_request": user_request,
                "session_id": session_id
            }
        )
        tasks.append(planner_task)
        
        # 2. 上下文分析 Agent - 分析文章內容
        if "selected_text" in user_request:
            context_task = AgentTask(
                task_id=f"{session_id}_context",
                agent_type=AgentType.CONTEXT_ANALYZER,
                input_data={
                    "url": user_request.get("url", ""),
                    "selected_text": user_request["selected_text"],
                    "session_id": session_id
                }
            )
            tasks.append(context_task)
        
        # 3. 音訊處理 Agent - 處理音檔轉錄
        if "audio_transcription" in user_request and user_request["audio_transcription"]:
            audio_task = AgentTask(
                task_id=f"{session_id}_audio",
                agent_type=AgentType.AUDIO_PROCESSOR,
                input_data={
                    "transcription": user_request["audio_transcription"],
                    "confusion_note": user_request.get("confusion_note", ""),
                    "session_id": session_id
                }
            )
            tasks.append(audio_task)
        
        # 4. RAG 檢索 Agent - 檢索相關筆記
        rag_task = AgentTask(
            task_id=f"{session_id}_rag",
            agent_type=AgentType.RAG_RETRIEVER,
            input_data={
                "confusion_note": user_request.get("confusion_note", ""),
                "selected_text": user_request.get("selected_text", ""),
                "session_id": session_id
            }
        )
        tasks.append(rag_task)
        
        # 5. 內容生成 Agent - 生成最終教學內容
        generator_task = AgentTask(
            task_id=f"{session_id}_generator",
            agent_type=AgentType.CONTENT_GENERATOR,
            input_data={
                "session_id": session_id,
                "user_request": user_request
            }
        )
        tasks.append(generator_task)
        
        return tasks
        
    async def execute_plan(self, tasks: List[AgentTask]) -> AgentContext:
        """執行任務計劃"""
        if not tasks:
            raise ValueError("任務清單不能為空")
            
        session_id = tasks[0].input_data.get("session_id")
        context = AgentContext(
            session_id=session_id,
            user_input=tasks[0].input_data.get("user_request", {}),
            intermediate_results={}
        )
        
        # 依序執行任務
        for task in tasks:
            try:
                await self._execute_single_task(task, context)
                
                # 將結果加入上下文
                if task.status == TaskStatus.COMPLETED and task.output_data:
                    context.intermediate_results[task.agent_type.value] = task.output_data
                    
            except Exception as e:
                self.logger.error(f"任務執行失敗 {task.task_id}: {e}")
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
                
                # 嘗試降級處理
                if task.agent_type in self.fallback_handlers:
                    try:
                        fallback_result = await self.fallback_handlers[task.agent_type](task, context)
                        task.output_data = fallback_result
                        task.status = TaskStatus.COMPLETED
                        context.intermediate_results[task.agent_type.value] = fallback_result
                    except Exception as fallback_error:
                        self.logger.error(f"降級處理也失敗 {task.task_id}: {fallback_error}")
        
        # 整合最終結果
        context.final_result = self._integrate_results(context)
        
        return context
        
    async def _execute_single_task(self, task: AgentTask, context: AgentContext):
        """執行單一任務"""
        if task.agent_type not in self.agents:
            raise ValueError(f"未找到 Agent: {task.agent_type.value}")
            
        agent = self.agents[task.agent_type]
        
        # 健康檢查
        if not await agent.health_check():
            raise RuntimeError(f"Agent {task.agent_type.value} 健康檢查失敗")
            
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        self.running_tasks[task.task_id] = task
        
        try:
            # 執行任務
            result = await agent.execute(task, context)
            
            task.output_data = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            
            # 移到已完成清單
            self.completed_tasks[task.task_id] = task
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]
                
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_at = datetime.now()
            
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]
            
            raise e
    
    def _integrate_results(self, context: AgentContext) -> Dict[str, Any]:
        """整合所有 Agent 的執行結果"""
        integrated_result = {
            "session_id": context.session_id,
            "status": "completed",
            "agent_results": context.intermediate_results,
            "processing_time": self._calculate_processing_time(context),
            "final_content": None
        }
        
        # 從內容生成 Agent 提取最終教學內容
        if AgentType.CONTENT_GENERATOR.value in context.intermediate_results:
            generator_result = context.intermediate_results[AgentType.CONTENT_GENERATOR.value]
            integrated_result["final_content"] = generator_result.get("teaching_content")
            
        return integrated_result
    
    def _calculate_processing_time(self, context: AgentContext) -> float:
        """計算處理時間"""
        # 這裡可以實作更精確的時間計算邏輯
        return 0.0
    
    async def get_task_status(self, task_id: str) -> Optional[AgentTask]:
        """獲取任務狀態"""
        if task_id in self.running_tasks:
            return self.running_tasks[task_id]
        elif task_id in self.completed_tasks:
            return self.completed_tasks[task_id]
        else:
            # 檢查待處理佇列
            for task in self.task_queue:
                if task.task_id == task_id:
                    return task
            return None
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任務"""
        task = await self.get_task_status(task_id)
        if task and task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            task.status = TaskStatus.CANCELLED
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            return True
        return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """獲取系統狀態"""
        return {
            "registered_agents": list(self.agents.keys()),
            "running_tasks_count": len(self.running_tasks),
            "completed_tasks_count": len(self.completed_tasks),
            "queue_size": len(self.task_queue),
            "max_concurrent_tasks": self.max_concurrent_tasks
        }


# 全域調度器實例
agent_scheduler = AgentScheduler()