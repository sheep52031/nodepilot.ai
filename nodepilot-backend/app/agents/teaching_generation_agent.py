"""
教學內容生成 Agent - Artifacts 可視化教學
========================================

整合多 Agent 結果，生成個人化教學內容和 Artifacts。
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from .base_agent import BaseAgent, AgentExecutionResult
from ai_core.scheduler import AgentExecutionContext
from ai_core.model_pool import ModelPool


class ArtifactType(Enum):
    """Artifacts 類型"""
    HTML_VISUALIZATION = "html"
    INTERACTIVE_DEMO = "demo"
    CODE_EXAMPLE = "code"
    CONCEPT_DIAGRAM = "diagram"
    STEP_BY_STEP_GUIDE = "guide"
    COMPARISON_TABLE = "table"


@dataclass
class ArtifactItem:
    """Artifacts 項目"""
    type: ArtifactType
    title: str
    content: str
    description: str
    interactive: bool = False


class TeachingGenerationAgent(BaseAgent):
    """
    教學內容生成 Agent
    
    功能:
    - 整合多 Agent 分析結果
    - 生成個人化教學內容
    - 建立 Artifacts 可視化輸出
    - 適應用戶學習風格和難度
    """
    
    def __init__(self, model_pool: ModelPool):
        super().__init__(model_pool, "teaching_generation")
        
        # 教學模板配置
        self.teaching_templates = {
            "concept_understanding": {
                "structure": ["definition", "examples", "applications", "common_mistakes"],
                "artifacts": [ArtifactType.CONCEPT_DIAGRAM, ArtifactType.HTML_VISUALIZATION]
            },
            "application_problem": {
                "structure": ["problem_analysis", "solution_steps", "implementation", "testing"],
                "artifacts": [ArtifactType.CODE_EXAMPLE, ArtifactType.STEP_BY_STEP_GUIDE]
            },
            "implementation_details": {
                "structure": ["overview", "detailed_steps", "code_examples", "troubleshooting"],
                "artifacts": [ArtifactType.CODE_EXAMPLE, ArtifactType.INTERACTIVE_DEMO]
            },
            "comparison_analysis": {
                "structure": ["similarities", "differences", "use_cases", "recommendations"],
                "artifacts": [ArtifactType.COMPARISON_TABLE, ArtifactType.HTML_VISUALIZATION]
            }
        }
        
        # 難度等級調整
        self.difficulty_adjustments = {
            "beginner": {
                "vocabulary": "simple",
                "examples": "basic",
                "detail_level": "high",
                "assumptions": "minimal"
            },
            "intermediate": {
                "vocabulary": "standard",
                "examples": "practical",
                "detail_level": "medium",
                "assumptions": "moderate"
            },
            "advanced": {
                "vocabulary": "technical",
                "examples": "complex",
                "detail_level": "focused",
                "assumptions": "extensive"
            }
        }
    
    def get_task_type(self) -> str:
        return "teaching_generation"
    
    async def execute(self, context: AgentExecutionContext) -> AgentExecutionResult:
        """執行教學內容生成"""
        self.logger.info("Starting teaching content generation")
        
        return await self._execute_with_model(context, priority="quality")
    
    async def _process_context(self, context: AgentExecutionContext) -> Dict[str, Any]:
        """處理執行上下文"""
        inputs = context.inputs
        context_data = context.context_data
        
        # 提取基礎資訊
        user_confusion = inputs.get("user_confusion", "")
        selected_text = inputs.get("selected_text", "")
        
        # 整合其他 Agent 的結果
        context_analysis = self._extract_context_analysis(context_data)
        confusion_analysis = self._extract_confusion_analysis(context_data)
        note_retrieval = self._extract_note_retrieval(context_data)
        
        # 決定教學策略
        teaching_strategy = self._determine_teaching_strategy(
            confusion_analysis, context_analysis, note_retrieval
        )
        
        # 分析學習者特徵
        learner_profile = self._analyze_learner_profile(confusion_analysis)
        
        # 選擇合適的 Artifacts
        recommended_artifacts = self._recommend_artifacts(
            confusion_analysis, teaching_strategy
        )
        
        return {
            "user_confusion": user_confusion,
            "selected_text": selected_text,
            "context_analysis": context_analysis,
            "confusion_analysis": confusion_analysis,
            "note_retrieval": note_retrieval,
            "teaching_strategy": teaching_strategy,
            "learner_profile": learner_profile,
            "recommended_artifacts": recommended_artifacts
        }
    
    def _extract_context_analysis(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取上下文分析結果"""
        if "article_structure" in context_data:
            context_list = context_data["article_structure"]
            if isinstance(context_list, list) and context_list:
                return context_list[0].get("data", {})
        return {}
    
    def _extract_confusion_analysis(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取困惑分析結果"""
        if "confusion_analysis" in context_data:
            confusion_list = context_data["confusion_analysis"]
            if isinstance(confusion_list, list) and confusion_list:
                return confusion_list[0].get("data", {})
        return {}
    
    def _extract_note_retrieval(self, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取筆記檢索結果"""
        if "note_retrieval" in context_data:
            notes_list = context_data["note_retrieval"]
            if isinstance(notes_list, list) and notes_list:
                return notes_list[0].get("data", {})
        return {}
    
    def _determine_teaching_strategy(
        self,
        confusion_analysis: Dict[str, Any],
        context_analysis: Dict[str, Any],
        note_retrieval: Dict[str, Any]
    ) -> Dict[str, Any]:
        """決定教學策略"""
        strategy = {
            "approach": "comprehensive",
            "focus_areas": [],
            "teaching_methods": [],
            "content_structure": []
        }
        
        # 根據困惑分析決定方法
        if confusion_analysis:
            confusion_type = confusion_analysis.get("confusion_analysis", {}).get("primary_confusion_type", "")
            
            if confusion_type in self.teaching_templates:
                template = self.teaching_templates[confusion_type]
                strategy["content_structure"] = template["structure"]
                strategy["approach"] = confusion_type
        
        # 根據難度等級調整
        difficulty = confusion_analysis.get("difficulty_assessment", {}).get("level", "intermediate")
        if difficulty in self.difficulty_adjustments:
            strategy["difficulty_adjustments"] = self.difficulty_adjustments[difficulty]
        
        # 根據學習意圖調整教學方法
        learning_context = confusion_analysis.get("learning_context", {})
        learning_intent = learning_context.get("learning_intent", "understand")
        
        if learning_intent == "apply":
            strategy["teaching_methods"].append("hands-on_examples")
        elif learning_intent == "compare":
            strategy["teaching_methods"].append("comparative_analysis")
        elif learning_intent == "troubleshoot":
            strategy["teaching_methods"].append("problem_solving")
        else:
            strategy["teaching_methods"].append("conceptual_explanation")
        
        # 根據上下文分析添加焦點區域
        if context_analysis:
            article_structure = context_analysis.get("article_structure", {})
            key_concepts = article_structure.get("key_concepts", [])
            strategy["focus_areas"].extend(key_concepts[:3])
        
        return strategy
    
    def _analyze_learner_profile(self, confusion_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """分析學習者特徵"""
        profile = {
            "difficulty_level": "intermediate",
            "learning_style": "visual",
            "emotional_state": "confused",
            "technical_background": "moderate",
            "preferred_pace": "normal"
        }
        
        if confusion_analysis:
            # 難度等級
            difficulty_assessment = confusion_analysis.get("difficulty_assessment", {})
            profile["difficulty_level"] = difficulty_assessment.get("level", "intermediate")
            
            # 學習風格
            learning_context = confusion_analysis.get("learning_context", {})
            profile["learning_style"] = learning_context.get("preferred_learning_style", "visual")
            
            # 情緒狀態
            emotional_analysis = confusion_analysis.get("emotional_analysis", {})
            profile["emotional_state"] = emotional_analysis.get("primary_emotion", "confused")
            
            # 技術背景
            communication_patterns = confusion_analysis.get("communication_patterns", {})
            profile["technical_background"] = communication_patterns.get("technical_vocabulary_level", "moderate")
        
        return profile
    
    def _recommend_artifacts(
        self, 
        confusion_analysis: Dict[str, Any], 
        teaching_strategy: Dict[str, Any]
    ) -> List[ArtifactType]:
        """推薦合適的 Artifacts"""
        recommended = []
        
        # 根據困惑類型推薦
        approach = teaching_strategy.get("approach", "comprehensive")
        if approach in self.teaching_templates:
            template_artifacts = self.teaching_templates[approach]["artifacts"]
            recommended.extend(template_artifacts)
        
        # 根據學習風格調整
        if confusion_analysis:
            learning_context = confusion_analysis.get("learning_context", {})
            learning_style = learning_context.get("preferred_learning_style", "visual")
            
            if learning_style == "visual":
                if ArtifactType.CONCEPT_DIAGRAM not in recommended:
                    recommended.append(ArtifactType.CONCEPT_DIAGRAM)
            elif learning_style == "kinesthetic":
                if ArtifactType.INTERACTIVE_DEMO not in recommended:
                    recommended.append(ArtifactType.INTERACTIVE_DEMO)
        
        # 去重並限制數量
        unique_artifacts = list(dict.fromkeys(recommended))
        return unique_artifacts[:3]  # 最多3個 Artifacts
    
    async def _generate_prompt(self, processed_input: Dict[str, Any]) -> str:
        """生成教學內容 prompt"""
        
        user_confusion = processed_input["user_confusion"]
        selected_text = processed_input["selected_text"]
        context_analysis = processed_input["context_analysis"]
        confusion_analysis = processed_input["confusion_analysis"]
        note_retrieval = processed_input["note_retrieval"]
        teaching_strategy = processed_input["teaching_strategy"]
        learner_profile = processed_input["learner_profile"]
        recommended_artifacts = processed_input["recommended_artifacts"]
        
        # 建構上下文摘要
        context_summary = self._build_context_summary(
            context_analysis, confusion_analysis, note_retrieval
        )
        
        artifacts_list = ", ".join([artifact.value for artifact in recommended_artifacts])
        
        prompt = f"""你是個人化教學專家，根據多維度分析結果生成最適合的學習內容。

## 用戶困惑
{user_confusion}

## 選取文字
```
{selected_text[:500]}{"..." if len(selected_text) > 500 else ""}
```

## 多 Agent 分析摘要
{context_summary}

## 學習者特徵分析
- **難度等級**: {learner_profile['difficulty_level']}
- **學習風格**: {learner_profile['learning_style']}
- **情緒狀態**: {learner_profile['emotional_state']}
- **技術背景**: {learner_profile['technical_background']}

## 教學策略
- **教學方法**: {teaching_strategy.get('approach', 'comprehensive')}
- **內容結構**: {', '.join(teaching_strategy.get('content_structure', []))}
- **焦點領域**: {', '.join(teaching_strategy.get('focus_areas', []))}

## 任務要求
請生成個人化教學內容，並創建以下 Artifacts：{artifacts_list}

輸出格式：
```json
{{
  "teaching_content": {{
    "title": "個人化學習解答標題",
    "introduction": "溫暖的開場白，確認用戶困惑並給予鼓勵",
    "main_content": "主要教學內容 (使用 Markdown 格式)",
    "key_takeaways": ["關鍵要點1", "關鍵要點2", "關鍵要點3"],
    "next_steps": ["下一步學習建議1", "建議2", "建議3"]
  }},
  "artifacts": [
    {{
      "type": "artifact_type",
      "title": "Artifact 標題",
      "description": "Artifact 說明",
      "content": "實際的 HTML/JavaScript/CSS 程式碼或結構化內容",
      "interactive": true/false
    }}
  ],
  "personalization_notes": {{
    "difficulty_adaptation": "如何根據用戶難度等級調整內容",
    "learning_style_optimization": "針對學習風格的最佳化",
    "emotional_support": "提供的情緒支持方式",
    "technical_level_matching": "技術程度匹配說明"
  }},
  "quality_metrics": {{
    "relevance_to_confusion": 0.95,
    "pedagogical_effectiveness": 0.90,
    "engagement_level": 0.85,
    "practical_applicability": 0.88
  }},
  "sources": ["teaching_generation_agent", "multi_agent_integration"]
}}
```

## 內容要求
1. **個人化程度高** - 直接回應用戶的具體困惑
2. **結構清晰** - 使用標題、列表、程式碼區塊等
3. **實用性強** - 提供可執行的範例和建議
4. **情緒支持** - 根據用戶情緒狀態給予適當鼓勵
5. **適當難度** - 匹配用戶的技術背景和理解程度

## Artifacts 建立指南
- **HTML_VISUALIZATION**: 互動式概念圖表或資訊圖
- **INTERACTIVE_DEMO**: 可執行的程式碼示範
- **CODE_EXAMPLE**: 完整的程式碼範例
- **CONCEPT_DIAGRAM**: 概念關係圖
- **STEP_BY_STEP_GUIDE**: 步驟式操作指南
- **COMPARISON_TABLE**: 比較表格

確保輸出是有效的 JSON 格式，Artifacts 內容要完整可用。"""

        return prompt
    
    def _build_context_summary(
        self,
        context_analysis: Dict[str, Any],
        confusion_analysis: Dict[str, Any],
        note_retrieval: Dict[str, Any]
    ) -> str:
        """建構上下文摘要"""
        summary_parts = []
        
        # 上下文分析摘要
        if context_analysis:
            article_structure = context_analysis.get("article_structure", {})
            main_theme = article_structure.get("main_theme", "未知主題")
            key_concepts = article_structure.get("key_concepts", [])
            
            summary_parts.append(f"**文章主題**: {main_theme}")
            if key_concepts:
                summary_parts.append(f"**關鍵概念**: {', '.join(key_concepts[:3])}")
        
        # 困惑分析摘要
        if confusion_analysis:
            confusion_analysis_data = confusion_analysis.get("confusion_analysis", {})
            primary_type = confusion_analysis_data.get("primary_confusion_type", "概念理解")
            
            semantic_structure = confusion_analysis.get("semantic_structure", {})
            key_concepts = semantic_structure.get("key_concepts", [])
            
            summary_parts.append(f"**困惑類型**: {primary_type}")
            if key_concepts:
                summary_parts.append(f"**困惑關鍵詞**: {', '.join(key_concepts[:3])}")
        
        # 筆記檢索摘要
        if note_retrieval:
            retrieval_summary = note_retrieval.get("retrieval_summary", {})
            notes_found = retrieval_summary.get("total_notes_found", 0)
            
            if notes_found > 0:
                related_notes = note_retrieval.get("related_notes", [])
                note_titles = [note.get("title", "") for note in related_notes[:2]]
                summary_parts.append(f"**相關筆記**: {', '.join(note_titles)}")
            else:
                summary_parts.append("**相關筆記**: 未找到相關筆記")
        
        return "\n".join(summary_parts) if summary_parts else "基礎分析完成"
    
    async def _parse_model_response(self, response: str) -> Dict[str, Any]:
        """解析模型回應"""
        try:
            # 解析 JSON
            if response.strip().startswith('{'):
                teaching_data = json.loads(response.strip())
            else:
                # 提取 JSON 部分
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    teaching_data = json.loads(json_match.group(1))
                else:
                    raise ValueError("No valid JSON found in response")
            
            # 驗證並完善結果
            validated_result = self._validate_teaching_result(teaching_data)
            
            return validated_result
            
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Failed to parse teaching generation response: {str(e)}")
            
            # 回退到基礎教學內容
            return self._create_fallback_teaching_content(response)
    
    def _validate_teaching_result(self, teaching_data: Dict[str, Any]) -> Dict[str, Any]:
        """驗證教學結果"""
        # 確保必要欄位存在
        if "teaching_content" not in teaching_data:
            teaching_data["teaching_content"] = {
                "title": "學習解答",
                "introduction": "讓我來幫助您理解這個問題。",
                "main_content": "正在生成教學內容...",
                "key_takeaways": ["請稍候，內容正在生成"],
                "next_steps": ["繼續學習"]
            }
        
        if "artifacts" not in teaching_data:
            teaching_data["artifacts"] = []
        
        if "personalization_notes" not in teaching_data:
            teaching_data["personalization_notes"] = {
                "difficulty_adaptation": "Standard difficulty level",
                "learning_style_optimization": "General approach",
                "emotional_support": "Encouraging tone",
                "technical_level_matching": "Appropriate level"
            }
        
        if "quality_metrics" not in teaching_data:
            teaching_data["quality_metrics"] = {
                "relevance_to_confusion": 0.8,
                "pedagogical_effectiveness": 0.75,
                "engagement_level": 0.7,
                "practical_applicability": 0.75
            }
        
        if "sources" not in teaching_data:
            teaching_data["sources"] = ["teaching_generation_agent"]
        
        # 驗證 Artifacts 結構
        validated_artifacts = []
        for artifact in teaching_data.get("artifacts", []):
            if isinstance(artifact, dict) and "type" in artifact:
                validated_artifacts.append(artifact)
        teaching_data["artifacts"] = validated_artifacts
        
        return teaching_data
    
    def _create_fallback_teaching_content(self, original_response: str) -> Dict[str, Any]:
        """建立回退教學內容"""
        # 嘗試從原始回應中提取有用資訊
        content_lines = original_response.split('\n')
        usable_content = []
        
        for line in content_lines[:20]:  # 只取前20行
            if line.strip() and not line.startswith(('```', '{')):
                usable_content.append(line.strip())
        
        main_content = '\n'.join(usable_content) if usable_content else "我正在分析您的問題，請稍候..."
        
        return {
            "teaching_content": {
                "title": "學習解答 (基礎版本)",
                "introduction": "很抱歉，完整的分析遇到了技術問題，讓我為您提供基礎的解答。",
                "main_content": main_content,
                "key_takeaways": ["基礎解答已提供", "如需更詳細說明請重新詢問"],
                "next_steps": ["嘗試重新提問", "查閱相關資料"]
            },
            "artifacts": [
                {
                    "type": "html",
                    "title": "簡單說明",
                    "description": "基礎的解答內容",
                    "content": f"<div><p>{main_content[:200]}...</p></div>",
                    "interactive": False
                }
            ],
            "personalization_notes": {
                "difficulty_adaptation": "Fallback mode - general level",
                "learning_style_optimization": "Basic text-based approach",
                "emotional_support": "Apologetic and helpful tone",
                "technical_level_matching": "General audience"
            },
            "quality_metrics": {
                "relevance_to_confusion": 0.5,
                "pedagogical_effectiveness": 0.4,
                "engagement_level": 0.3,
                "practical_applicability": 0.4
            },
            "sources": ["teaching_generation_agent_fallback"],
            "fallback_reason": "Response parsing failed",
            "original_response_preview": original_response[:300] + "..." if len(original_response) > 300 else original_response
        }