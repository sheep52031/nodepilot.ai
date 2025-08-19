"""
結果整合器 - 多 Agent 結果整合和格式化
=====================================

負責整合多個 Agent 的執行結果，確保一致性和品質。
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import re

from .execution_plan import ExecutionPlan, TaskNode
from .scheduler import AgentExecutionContext, AgentType


@dataclass
class IntegrationResult:
    """整合結果"""
    success: bool
    teaching_content: str
    metadata: Dict[str, Any]
    sources: List[str]
    confidence_score: float
    processing_time: float
    agent_contributions: Dict[str, Any]
    quality_metrics: Dict[str, float]


class ResultIntegrator:
    """
    結果整合器
    
    功能:
    - 多 Agent 結果整合
    - 品質一致性檢查
    - Markdown 格式化
    - Artifacts 輸出處理
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 品質檢查權重
        self.quality_weights = {
            "relevance": 0.3,      # 相關性
            "accuracy": 0.25,      # 準確性
            "completeness": 0.2,   # 完整性
            "clarity": 0.15,       # 清晰度
            "usefulness": 0.1      # 實用性
        }
    
    async def integrate_results(
        self,
        execution_results: Dict[str, AgentExecutionContext],
        execution_plan: ExecutionPlan
    ) -> Dict[str, Any]:
        """
        整合 Agent 執行結果
        
        Args:
            execution_results: Agent 執行結果
            execution_plan: 執行計畫
            
        Returns:
            整合後的最終結果
        """
        start_time = datetime.utcnow()
        
        try:
            # 提取各 Agent 的核心結果
            agent_outputs = await self._extract_agent_outputs(execution_results)
            
            # 檢查結果完整性
            completeness_check = await self._check_completeness(
                agent_outputs, execution_plan
            )
            
            # 執行品質評估
            quality_metrics = await self._evaluate_quality(agent_outputs)
            
            # 整合教學內容
            integrated_content = await self._integrate_teaching_content(agent_outputs)
            
            # 格式化 Markdown 輸出
            formatted_content = await self._format_markdown_output(integrated_content)
            
            # 處理 Artifacts 輸出
            artifacts = await self._generate_artifacts(agent_outputs)
            
            # 建立最終結果
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            result = IntegrationResult(
                success=True,
                teaching_content=formatted_content,
                metadata={
                    "execution_plan_id": execution_plan.plan_id,
                    "agents_used": list(agent_outputs.keys()),
                    "artifacts": artifacts,
                    "timestamp": datetime.utcnow().isoformat()
                },
                sources=self._extract_sources(agent_outputs),
                confidence_score=self._calculate_confidence_score(quality_metrics),
                processing_time=processing_time,
                agent_contributions=self._summarize_agent_contributions(agent_outputs),
                quality_metrics=quality_metrics
            )
            
            self.logger.info(
                f"Integration completed successfully in {processing_time:.2f}s "
                f"(confidence: {result.confidence_score:.2f})"
            )
            
            return self._format_final_output(result)
            
        except Exception as e:
            self.logger.error(f"Result integration failed: {str(e)}")
            return self._create_error_response(str(e), execution_results)
    
    async def _extract_agent_outputs(
        self, 
        execution_results: Dict[str, AgentExecutionContext]
    ) -> Dict[AgentType, Dict[str, Any]]:
        """提取各 Agent 的核心輸出"""
        agent_outputs = {}
        
        for task_id, context in execution_results.items():
            if context.result and context.agent_type:
                agent_outputs[context.agent_type] = context.result
        
        return agent_outputs
    
    async def _check_completeness(
        self,
        agent_outputs: Dict[AgentType, Dict[str, Any]],
        execution_plan: ExecutionPlan
    ) -> Dict[str, Any]:
        """檢查結果完整性"""
        required_agents = set()
        for task in execution_plan.tasks.values():
            required_agents.add(task.agent_type)
        
        available_agents = set(agent_outputs.keys())
        missing_agents = required_agents - available_agents
        
        completeness_score = len(available_agents) / len(required_agents)
        
        return {
            "score": completeness_score,
            "required_agents": [agent.value for agent in required_agents],
            "available_agents": [agent.value for agent in available_agents],
            "missing_agents": [agent.value for agent in missing_agents]
        }
    
    async def _evaluate_quality(
        self, 
        agent_outputs: Dict[AgentType, Dict[str, Any]]
    ) -> Dict[str, float]:
        """評估整體品質"""
        quality_scores = {}
        
        # 相關性評估
        quality_scores["relevance"] = await self._evaluate_relevance(agent_outputs)
        
        # 準確性評估
        quality_scores["accuracy"] = await self._evaluate_accuracy(agent_outputs)
        
        # 完整性評估
        quality_scores["completeness"] = await self._evaluate_completeness_quality(agent_outputs)
        
        # 清晰度評估
        quality_scores["clarity"] = await self._evaluate_clarity(agent_outputs)
        
        # 實用性評估
        quality_scores["usefulness"] = await self._evaluate_usefulness(agent_outputs)
        
        return quality_scores
    
    async def _evaluate_relevance(self, agent_outputs: Dict[AgentType, Dict[str, Any]]) -> float:
        """評估相關性"""
        # 簡化實作：檢查是否有教學內容與用戶困惑對應
        if AgentType.TEACHING_GENERATION in agent_outputs:
            teaching_result = agent_outputs[AgentType.TEACHING_GENERATION]
            if teaching_result.get("teaching_content"):
                return 0.85  # 有教學內容就算及格
        
        return 0.5  # 預設中等分數
    
    async def _evaluate_accuracy(self, agent_outputs: Dict[AgentType, Dict[str, Any]]) -> float:
        """評估準確性"""
        # 簡化實作：檢查是否有明顯的錯誤指標
        accuracy_score = 0.8  # 預設良好分數
        
        for agent_type, output in agent_outputs.items():
            # 檢查是否有錯誤標記
            if output.get("error") or output.get("warnings"):
                accuracy_score -= 0.1
        
        return max(0.0, accuracy_score)
    
    async def _evaluate_completeness_quality(self, agent_outputs: Dict[AgentType, Dict[str, Any]]) -> float:
        """評估完整性品質"""
        # 檢查各 Agent 是否提供了完整的輸出
        completeness_scores = []
        
        for agent_type, output in agent_outputs.items():
            if agent_type == AgentType.TEACHING_GENERATION:
                # 教學生成應該有主要內容
                if output.get("teaching_content"):
                    completeness_scores.append(1.0)
                else:
                    completeness_scores.append(0.3)
            
            elif agent_type == AgentType.CONTEXT_ANALYSIS:
                # 上下文分析應該有文章結構
                if output.get("article_structure"):
                    completeness_scores.append(0.9)
                else:
                    completeness_scores.append(0.4)
            
            elif agent_type == AgentType.AUDIO_SEMANTIC:
                # 音訊語意應該有困惑分析
                if output.get("confusion_analysis"):
                    completeness_scores.append(0.8)
                else:
                    completeness_scores.append(0.3)
            
            else:
                # 其他 Agent 的基本檢查
                if output and len(str(output)) > 50:
                    completeness_scores.append(0.7)
                else:
                    completeness_scores.append(0.2)
        
        return sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0.5
    
    async def _evaluate_clarity(self, agent_outputs: Dict[AgentType, Dict[str, Any]]) -> float:
        """評估清晰度"""
        # 簡化實作：檢查教學內容的結構化程度
        if AgentType.TEACHING_GENERATION in agent_outputs:
            teaching_content = agent_outputs[AgentType.TEACHING_GENERATION].get("teaching_content", "")
            
            # 檢查是否有標題、段落等結構
            has_headers = bool(re.search(r'^#+\s', teaching_content, re.MULTILINE))
            has_lists = bool(re.search(r'^[-*+]\s', teaching_content, re.MULTILINE))
            has_code_blocks = '```' in teaching_content
            
            clarity_score = 0.5  # 基礎分數
            if has_headers:
                clarity_score += 0.2
            if has_lists:
                clarity_score += 0.15
            if has_code_blocks:
                clarity_score += 0.15
            
            return min(1.0, clarity_score)
        
        return 0.6  # 預設分數
    
    async def _evaluate_usefulness(self, agent_outputs: Dict[AgentType, Dict[str, Any]]) -> float:
        """評估實用性"""
        # 簡化實作：檢查是否提供了可操作的建議
        usefulness_score = 0.6  # 基礎分數
        
        if AgentType.TEACHING_GENERATION in agent_outputs:
            teaching_content = agent_outputs[AgentType.TEACHING_GENERATION].get("teaching_content", "")
            
            # 檢查是否有實際的程式碼範例
            if '```' in teaching_content:
                usefulness_score += 0.2
            
            # 檢查是否有步驟說明
            if re.search(r'\d+\.\s', teaching_content):
                usefulness_score += 0.15
        
        return min(1.0, usefulness_score)
    
    async def _integrate_teaching_content(
        self, 
        agent_outputs: Dict[AgentType, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """整合教學內容"""
        integrated = {
            "main_content": "",
            "context_info": {},
            "confusion_analysis": {},
            "related_notes": [],
            "artifacts": []
        }
        
        # 主要教學內容
        if AgentType.TEACHING_GENERATION in agent_outputs:
            teaching_result = agent_outputs[AgentType.TEACHING_GENERATION]
            integrated["main_content"] = teaching_result.get("teaching_content", "")
            integrated["artifacts"] = teaching_result.get("artifacts", [])
        
        # 上下文資訊
        if AgentType.CONTEXT_ANALYSIS in agent_outputs:
            context_result = agent_outputs[AgentType.CONTEXT_ANALYSIS]
            integrated["context_info"] = {
                "article_structure": context_result.get("article_structure", {}),
                "relevant_sections": context_result.get("relevant_sections", [])
            }
        
        # 困惑分析
        if AgentType.AUDIO_SEMANTIC in agent_outputs:
            audio_result = agent_outputs[AgentType.AUDIO_SEMANTIC]
            integrated["confusion_analysis"] = {
                "confusion_type": audio_result.get("confusion_type", "unknown"),
                "key_concepts": audio_result.get("key_concepts", []),
                "difficulty_level": audio_result.get("difficulty_level", "medium")
            }
        
        # 相關筆記
        if AgentType.NOTE_RETRIEVAL in agent_outputs:
            notes_result = agent_outputs[AgentType.NOTE_RETRIEVAL]
            integrated["related_notes"] = notes_result.get("related_notes", [])
        
        return integrated
    
    async def _format_markdown_output(self, integrated_content: Dict[str, Any]) -> str:
        """格式化 Markdown 輸出"""
        markdown_parts = []
        
        # 主標題
        markdown_parts.append("# 📚 個人化學習解答\n")
        
        # 困惑分析區塊
        confusion_analysis = integrated_content.get("confusion_analysis", {})
        if confusion_analysis:
            markdown_parts.append("## 🤔 困惑分析\n")
            
            confusion_type = confusion_analysis.get("confusion_type", "未知")
            markdown_parts.append(f"**困惑類型**: {confusion_type}\n")
            
            key_concepts = confusion_analysis.get("key_concepts", [])
            if key_concepts:
                markdown_parts.append("**關鍵概念**: " + ", ".join(key_concepts) + "\n")
            
            markdown_parts.append("")
        
        # 主要教學內容
        main_content = integrated_content.get("main_content", "")
        if main_content:
            markdown_parts.append("## 💡 學習解答\n")
            markdown_parts.append(main_content)
            markdown_parts.append("")
        
        # 相關筆記
        related_notes = integrated_content.get("related_notes", [])
        if related_notes:
            markdown_parts.append("## 📝 相關筆記\n")
            for i, note in enumerate(related_notes[:3], 1):  # 限制顯示3筆
                markdown_parts.append(f"{i}. **{note.get('title', '無標題')}**")
                markdown_parts.append(f"   {note.get('summary', '無摘要')}\n")
            markdown_parts.append("")
        
        # 上下文參考
        context_info = integrated_content.get("context_info", {})
        relevant_sections = context_info.get("relevant_sections", [])
        if relevant_sections:
            markdown_parts.append("## 🔗 相關段落\n")
            for section in relevant_sections[:2]:  # 限制顯示2個段落
                markdown_parts.append(f"- {section.get('title', '無標題')}")
                markdown_parts.append(f"  _{section.get('summary', '無摘要')}_\n")
        
        return "\n".join(markdown_parts)
    
    async def _generate_artifacts(self, agent_outputs: Dict[AgentType, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成 Artifacts 輸出"""
        artifacts = []
        
        # 從教學生成 Agent 提取 Artifacts
        if AgentType.TEACHING_GENERATION in agent_outputs:
            teaching_result = agent_outputs[AgentType.TEACHING_GENERATION]
            teaching_artifacts = teaching_result.get("artifacts", [])
            artifacts.extend(teaching_artifacts)
        
        return artifacts
    
    def _extract_sources(self, agent_outputs: Dict[AgentType, Dict[str, Any]]) -> List[str]:
        """提取資料來源"""
        sources = []
        
        for agent_type, output in agent_outputs.items():
            agent_sources = output.get("sources", [])
            if isinstance(agent_sources, list):
                sources.extend(agent_sources)
            elif isinstance(agent_sources, str):
                sources.append(agent_sources)
        
        # 去除重複並排序
        return sorted(list(set(sources)))
    
    def _calculate_confidence_score(self, quality_metrics: Dict[str, float]) -> float:
        """計算整體信心分數"""
        weighted_score = sum(
            score * self.quality_weights.get(metric, 0.1)
            for metric, score in quality_metrics.items()
        )
        
        return min(1.0, max(0.0, weighted_score))
    
    def _summarize_agent_contributions(
        self, 
        agent_outputs: Dict[AgentType, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """總結各 Agent 的貢獻"""
        contributions = {}
        
        for agent_type, output in agent_outputs.items():
            contributions[agent_type.value] = {
                "status": "completed",
                "output_size": len(str(output)),
                "key_outputs": list(output.keys()) if isinstance(output, dict) else ["result"]
            }
        
        return contributions
    
    def _format_final_output(self, result: IntegrationResult) -> Dict[str, Any]:
        """格式化最終輸出"""
        return {
            "success": result.success,
            "teaching_content": result.teaching_content,
            "metadata": result.metadata,
            "quality": {
                "confidence_score": result.confidence_score,
                "quality_metrics": result.quality_metrics,
                "processing_time": result.processing_time
            },
            "sources": result.sources,
            "agent_contributions": result.agent_contributions,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _create_error_response(
        self, 
        error_message: str, 
        execution_results: Dict[str, AgentExecutionContext]
    ) -> Dict[str, Any]:
        """建立錯誤回應"""
        return {
            "success": False,
            "error": error_message,
            "partial_results": {
                task_id: {
                    "agent_type": ctx.agent_type.value,
                    "status": ctx.task_node.status.value,
                    "error": ctx.error
                }
                for task_id, ctx in execution_results.items()
            },
            "timestamp": datetime.utcnow().isoformat()
        }