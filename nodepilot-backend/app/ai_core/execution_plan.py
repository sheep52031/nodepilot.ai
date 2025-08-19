"""
執行計畫 - Plan-and-Execute 模式的任務規劃
=========================================

負責將用戶困惑分解為結構化的 Agent 執行計畫。
"""

from typing import Dict, List, Set, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import json

from .scheduler import AgentType


class TaskStatus(Enum):
    """任務狀態"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskPriority(Enum):
    """任務優先級"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TaskNode:
    """
    任務節點 - 代表一個 Agent 執行任務
    """
    task_id: str
    agent_type: AgentType
    inputs: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)  # 依賴的任務 ID
    priority: TaskPriority = TaskPriority.MEDIUM
    estimated_duration: Optional[int] = None  # 預估執行時間(秒)
    
    # 執行狀態
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    # 執行結果
    outputs: Dict[str, Any] = field(default_factory=dict)


class ExecutionPlan:
    """
    執行計畫 - 管理 Agent 任務的依賴關係和執行順序
    """
    
    def __init__(self, plan_id: str):
        self.plan_id = plan_id
        self.tasks: Dict[str, TaskNode] = {}
        self.created_at = datetime.utcnow()
        
    def add_task(self, task: TaskNode):
        """新增任務到計畫中"""
        self.tasks[task.task_id] = task
    
    def get_task(self, task_id: str) -> Optional[TaskNode]:
        """取得指定任務"""
        return self.tasks.get(task_id)
    
    def get_execution_batches(self) -> List[List[TaskNode]]:
        """
        取得按依賴關係排序的執行批次
        
        Returns:
            List of batches, 每個 batch 中的任務可以並行執行
        """
        batches = []
        completed_tasks = set()
        remaining_tasks = set(self.tasks.keys())
        
        while remaining_tasks:
            # 找到當前可執行的任務 (所有依賴都已完成)
            current_batch = []
            
            for task_id in list(remaining_tasks):
                task = self.tasks[task_id]
                if all(dep in completed_tasks for dep in task.dependencies):
                    current_batch.append(task)
                    remaining_tasks.remove(task_id)
            
            if not current_batch:
                # 如果沒有可執行的任務，可能存在循環依賴
                raise ValueError(f"Circular dependency detected in remaining tasks: {remaining_tasks}")
            
            # 按優先級排序
            current_batch.sort(key=lambda t: (t.priority.value, t.created_at))
            batches.append(current_batch)
            
            # 標記批次中的任務為已完成 (供下一輪依賴檢查)
            completed_tasks.update(task.task_id for task in current_batch)
        
        return batches
    
    def validate_dependencies(self) -> bool:
        """驗證依賴關係是否有效"""
        for task_id, task in self.tasks.items():
            for dep_id in task.dependencies:
                if dep_id not in self.tasks:
                    raise ValueError(f"Task {task_id} depends on non-existent task {dep_id}")
        return True
    
    def get_critical_path(self) -> List[str]:
        """取得關鍵路徑 (最長執行時間路徑)"""
        # 簡化實作: 返回依賴鏈最長的路徑
        def get_depth(task_id: str, visited: Set[str] = None) -> int:
            if visited is None:
                visited = set()
            
            if task_id in visited:
                return 0  # 避免循環
            
            visited.add(task_id)
            task = self.tasks[task_id]
            
            if not task.dependencies:
                return 1
            
            max_depth = max(get_depth(dep, visited.copy()) for dep in task.dependencies)
            return max_depth + 1
        
        # 找到最深的任務路徑
        task_depths = {task_id: get_depth(task_id) for task_id in self.tasks}
        critical_task = max(task_depths, key=task_depths.get)
        
        # 回溯建立關鍵路徑
        path = []
        current = critical_task
        
        while current:
            path.append(current)
            task = self.tasks[current]
            
            # 找到依賴中最深的任務
            if task.dependencies:
                current = max(task.dependencies, 
                            key=lambda dep: task_depths.get(dep, 0))
            else:
                current = None
        
        return list(reversed(path))
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化為字典"""
        return {
            "plan_id": self.plan_id,
            "created_at": self.created_at.isoformat(),
            "tasks": {
                task_id: {
                    "task_id": task.task_id,
                    "agent_type": task.agent_type.value,
                    "inputs": task.inputs,
                    "dependencies": task.dependencies,
                    "priority": task.priority.value,
                    "status": task.status.value,
                    "estimated_duration": task.estimated_duration
                }
                for task_id, task in self.tasks.items()
            }
        }
    
    @classmethod
    def from_plan_result(cls, plan_result: Dict[str, Any]) -> "ExecutionPlan":
        """
        從 Planning Agent 的結果建立 ExecutionPlan
        
        Args:
            plan_result: Planning Agent 輸出的規劃結果
            
        Returns:
            ExecutionPlan 實例
        """
        plan = cls(plan_result.get("plan_id", f"plan_{datetime.utcnow().timestamp()}"))
        
        # 解析任務節點
        for task_data in plan_result.get("tasks", []):
            task = TaskNode(
                task_id=task_data["task_id"],
                agent_type=AgentType(task_data["agent_type"]),
                inputs=task_data.get("inputs", {}),
                dependencies=task_data.get("dependencies", []),
                priority=TaskPriority(task_data.get("priority", "medium")),
                estimated_duration=task_data.get("estimated_duration")
            )
            plan.add_task(task)
        
        # 驗證依賴關係
        plan.validate_dependencies()
        
        return plan