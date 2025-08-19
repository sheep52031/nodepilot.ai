"""
任務規劃 Agent - GPT-4o/Claude 3.5 驅動的智慧任務分解
====================================================

負責將用戶困惑轉換為結構化的 Agent 執行計畫。
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .base_agent import BaseAgent, AgentExecutionResult
from ai_core.scheduler import AgentExecutionContext, AgentType
from ai_core.model_pool import ModelPool


class PlanningAgent(BaseAgent):
    """
    任務規劃 Agent
    
    功能:
    - 分析用戶困惑和上下文
    - 決定需要調用的 Agent 類型和順序
    - 生成結構化執行計畫
    - 設定任務優先級和依賴關係
    """
    
    def __init__(self, model_pool: ModelPool):
        super().__init__(model_pool, "planning")
        
        # 規劃模板
        self.task_templates = {
            "simple_text_question": [
                AgentType.CONTEXT_ANALYSIS,
                AgentType.TEACHING_GENERATION
            ],
            "audio_confusion": [
                AgentType.AUDIO_SEMANTIC,
                AgentType.CONTEXT_ANALYSIS,
                AgentType.NOTE_RETRIEVAL,
                AgentType.TEACHING_GENERATION
            ],
            "complex_analysis": [
                AgentType.CONTEXT_ANALYSIS,
                AgentType.NOTE_RETRIEVAL,
                AgentType.TEACHING_GENERATION
            ]
        }
    
    def get_task_type(self) -> str:
        return "planning"
    
    async def execute(self, context: AgentExecutionContext) -> AgentExecutionResult:
        """執行任務規劃"""
        self.logger.info("Starting task planning")
        
        return await self._execute_with_model(context, priority="quality")
    
    async def _process_context(self, context: AgentExecutionContext) -> Dict[str, Any]:
        """處理執行上下文"""
        inputs = context.inputs
        context_data = context.context_data
        
        # 提取基礎資訊
        user_confusion = inputs.get("user_confusion", "")
        selected_text = inputs.get("selected_text", "")
        page_context = inputs.get("page_context", {})
        audio_transcription = inputs.get("audio_transcription")
        
        # 分析困惑複雜度
        complexity_level = self._analyze_confusion_complexity(
            user_confusion, selected_text, audio_transcription
        )
        
        # 判斷任務類型
        task_category = self._categorize_task(
            user_confusion, selected_text, audio_transcription
        )
        
        return {
            "user_confusion": user_confusion,
            "selected_text": selected_text,
            "page_context": page_context,
            "audio_transcription": audio_transcription,
            "complexity_level": complexity_level,
            "task_category": task_category,
            "has_audio": bool(audio_transcription),
            "context_length": len(selected_text) if selected_text else 0
        }
    
    def _analyze_confusion_complexity(
        self, 
        user_confusion: str, 
        selected_text: str, 
        audio_transcription: Optional[str]
    ) -> str:
        """分析困惑複雜度"""
        complexity_indicators = 0
        
        # 困惑描述長度
        if len(user_confusion) > 100:
            complexity_indicators += 1
        
        # 選取文字長度
        if len(selected_text) > 500:
            complexity_indicators += 1
        
        # 是否有音訊
        if audio_transcription:
            complexity_indicators += 1
        
        # 是否包含技術術語
        technical_keywords = ["API", "函數", "演算法", "資料庫", "架構", "程式碼"]
        if any(keyword in user_confusion or keyword in selected_text 
               for keyword in technical_keywords):
            complexity_indicators += 1
        
        if complexity_indicators >= 3:
            return "high"
        elif complexity_indicators >= 2:
            return "medium"
        else:
            return "low"
    
    def _categorize_task(
        self, 
        user_confusion: str, 
        selected_text: str, 
        audio_transcription: Optional[str]
    ) -> str:
        """判斷任務類型"""
        if audio_transcription:
            return "audio_confusion"
        elif len(selected_text) > 1000 or "複雜" in user_confusion:
            return "complex_analysis"
        else:
            return "simple_text_question"
    
    async def _generate_prompt(self, processed_input: Dict[str, Any]) -> str:
        """生成規劃 prompt"""
        
        prompt = f"""你是 NodePilot 的任務規劃專家，負責將用戶的學習困惑分解為結構化的 Agent 執行計畫。

## 用戶情境
**困惑描述**: {processed_input['user_confusion']}
**選取文字長度**: {processed_input['context_length']} 字元
**頁面資訊**: {processed_input['page_context'].get('url', 'N/A')}
**是否有音訊**: {processed_input['has_audio']}
**複雜度**: {processed_input['complexity_level']}
**任務類型**: {processed_input['task_category']}

## 可用的 Agent 類型
1. **context_analysis** - 文章上下文分析，提取相關段落和概念
2. **audio_semantic** - 音訊語意結構化，分析用戶困惑類型
3. **note_retrieval** - RAG 筆記檢索，找尋相關學習記錄  
4. **teaching_generation** - 教學內容生成，產出個人化解答

## 規劃原則
- 音訊困惑 → 優先 audio_semantic → context_analysis → note_retrieval → teaching_generation
- 簡單問題 → context_analysis → teaching_generation
- 複雜分析 → context_analysis → note_retrieval → teaching_generation
- 考慮 Agent 間依賴關係和並行執行可能性

請生成結構化的執行計畫：

```json
{{
  "plan_id": "plan_{{timestamp}}",
  "task_category": "{processed_input['task_category']}",
  "estimated_duration": 15,
  "tasks": [
    {{
      "task_id": "task_1",
      "agent_type": "context_analysis",
      "inputs": {{
        "selected_text": "...",
        "page_context": {{...}}
      }},
      "dependencies": [],
      "priority": "high",
      "estimated_duration": 5
    }},
    {{
      "task_id": "task_2", 
      "agent_type": "teaching_generation",
      "inputs": {{
        "user_confusion": "...",
        "context_analysis_result": "@task_1.result"
      }},
      "dependencies": ["task_1"],
      "priority": "high",
      "estimated_duration": 8
    }}
  ],
  "reasoning": "說明為什麼選擇這個執行順序和 Agent 組合"
}}
```

輸出格式必須是有效的 JSON，不要包含額外的說明文字。"""

        return prompt
    
    async def _parse_model_response(self, response: str) -> Dict[str, Any]:
        """解析模型回應"""
        try:
            # 嘗試直接解析 JSON
            if response.strip().startswith('{'):
                plan_data = json.loads(response.strip())
            else:
                # 如果包含 markdown 格式，提取 JSON 部分
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    plan_data = json.loads(json_match.group(1))
                else:
                    raise ValueError("No valid JSON found in response")
            
            # 驗證計畫結構
            validated_plan = self._validate_and_enhance_plan(plan_data)
            
            return {
                "execution_plan": validated_plan,
                "planning_reasoning": validated_plan.get("reasoning", ""),
                "estimated_duration": validated_plan.get("estimated_duration", 15),
                "task_count": len(validated_plan.get("tasks", [])),
                "sources": ["planning_agent"]
            }
            
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Failed to parse planning response: {str(e)}")
            
            # 回退到預設計畫
            fallback_plan = self._create_fallback_plan(response)
            return {
                "execution_plan": fallback_plan,
                "planning_reasoning": "使用預設規劃模板（模型回應解析失敗）",
                "estimated_duration": 10,
                "task_count": len(fallback_plan.get("tasks", [])),
                "sources": ["planning_agent_fallback"],
                "error": f"Response parsing failed: {str(e)}"
            }
    
    def _validate_and_enhance_plan(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """驗證和增強計畫資料"""
        # 確保必要欄位存在
        if "plan_id" not in plan_data:
            plan_data["plan_id"] = f"plan_{int(datetime.utcnow().timestamp())}"
        
        if "tasks" not in plan_data:
            plan_data["tasks"] = []
        
        # 驗證任務結構
        for i, task in enumerate(plan_data["tasks"]):
            if "task_id" not in task:
                task["task_id"] = f"task_{i+1}"
            
            if "agent_type" not in task:
                task["agent_type"] = "teaching_generation"  # 預設
            
            if "inputs" not in task:
                task["inputs"] = {}
            
            if "dependencies" not in task:
                task["dependencies"] = []
            
            if "priority" not in task:
                task["priority"] = "medium"
            
            if "estimated_duration" not in task:
                task["estimated_duration"] = 5
        
        return plan_data
    
    def _create_fallback_plan(self, original_response: str) -> Dict[str, Any]:
        """建立回退計畫"""
        return {
            "plan_id": f"fallback_{int(datetime.utcnow().timestamp())}",
            "task_category": "simple_text_question",
            "estimated_duration": 10,
            "tasks": [
                {
                    "task_id": "fallback_context",
                    "agent_type": "context_analysis",
                    "inputs": {},
                    "dependencies": [],
                    "priority": "medium",
                    "estimated_duration": 4
                },
                {
                    "task_id": "fallback_teaching",
                    "agent_type": "teaching_generation", 
                    "inputs": {},
                    "dependencies": ["fallback_context"],
                    "priority": "high",
                    "estimated_duration": 6
                }
            ],
            "reasoning": "使用簡化的預設計畫：上下文分析 + 教學生成",
            "fallback_reason": original_response[:200] + "..." if len(original_response) > 200 else original_response
        }
    
    async def create_plan(self, planning_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        公開介面：建立執行計畫
        
        Args:
            planning_input: 規劃輸入資料
            
        Returns:
            執行計畫
        """
        # 建立執行上下文
        context = AgentExecutionContext(
            agent_id="planning_agent",
            agent_type=AgentType.PLANNING,
            task_node=None,  # Planning agent 不需要 task_node
            inputs=planning_input
        )
        
        # 執行規劃
        result = await self.execute(context)
        
        if result.success:
            return result.result["execution_plan"]
        else:
            # 返回最基本的預設計畫
            return self._create_fallback_plan(result.error or "Unknown error")