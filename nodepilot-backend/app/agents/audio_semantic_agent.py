"""
音訊語意結構化 Agent - 深度音訊理解和困惑分析
===========================================

將 Whisper 轉錄結果結構化為語意資訊，分析用戶困惑類型。
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass

from .base_agent import BaseAgent, AgentExecutionResult
from ai_core.scheduler import AgentExecutionContext
from ai_core.model_pool import ModelPool


class ConfusionType(Enum):
    """困惑類型"""
    CONCEPT_UNDERSTANDING = "concept_understanding"    # 概念理解
    APPLICATION_PROBLEM = "application_problem"        # 應用問題
    BACKGROUND_KNOWLEDGE = "background_knowledge"      # 背景知識
    IMPLEMENTATION_DETAILS = "implementation_details"   # 實作細節
    TERMINOLOGY_CONFUSION = "terminology_confusion"     # 術語困惑
    PROCESS_FLOW = "process_flow"                       # 流程理解
    COMPARISON_ANALYSIS = "comparison_analysis"         # 比較分析


class DifficultyLevel(Enum):
    """困難度等級"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate" 
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class AudioSemanticAnalysis:
    """音訊語意分析結果"""
    confusion_type: ConfusionType
    difficulty_level: DifficultyLevel
    key_concepts: List[str]
    emotional_state: str  # confused, frustrated, curious, excited
    confidence_level: float  # 用戶對內容的信心程度
    specific_questions: List[str]
    learning_intent: str  # understand, apply, compare, troubleshoot


class AudioSemanticAgent(BaseAgent):
    """
    音訊語意結構化 Agent
    
    功能:
    - 分析 Whisper 轉錄的語意結構
    - 識別困惑類型和難度等級
    - 分析用戶情緒狀態和學習意圖
    - 提取關鍵概念和具體問題
    """
    
    def __init__(self, model_pool: ModelPool):
        super().__init__(model_pool, "audio_semantic")
        
        # 語意分析模式
        self.analysis_keywords = {
            ConfusionType.CONCEPT_UNDERSTANDING: [
                "什麼是", "是什麼", "定義", "概念", "理論", "原理", "what is", "define"
            ],
            ConfusionType.APPLICATION_PROBLEM: [
                "怎麼用", "如何應用", "實際操作", "使用方法", "how to", "apply", "use"
            ],
            ConfusionType.BACKGROUND_KNOWLEDGE: [
                "背景", "歷史", "為什麼", "原因", "起源", "why", "background", "reason"
            ],
            ConfusionType.IMPLEMENTATION_DETAILS: [
                "程式碼", "實作", "細節", "步驟", "implementation", "code", "detail", "step"
            ],
            ConfusionType.TERMINOLOGY_CONFUSION: [
                "術語", "名詞", "詞彙", "意思", "terminology", "term", "meaning"
            ],
            ConfusionType.PROCESS_FLOW: [
                "流程", "步驟", "順序", "過程", "process", "flow", "sequence", "procedure"
            ],
            ConfusionType.COMPARISON_ANALYSIS: [
                "比較", "差異", "區別", "對比", "compare", "difference", "vs", "versus"
            ]
        }
        
        self.emotion_indicators = {
            "confused": ["不懂", "搞不清楚", "困惑", "混亂", "confused", "don't understand"],
            "frustrated": ["煩躁", "氣餒", "沮喪", "frustrated", "annoying", "difficult"],
            "curious": ["好奇", "想知道", "有趣", "curious", "interesting", "wonder"],
            "excited": ["興奮", "期待", "太棒了", "excited", "amazing", "great"]
        }
    
    def get_task_type(self) -> str:
        return "audio_semantic"
    
    async def execute(self, context: AgentExecutionContext) -> AgentExecutionResult:
        """執行音訊語意分析"""
        self.logger.info("Starting audio semantic analysis")
        
        return await self._execute_with_model(context, priority="balanced")
    
    async def _process_context(self, context: AgentExecutionContext) -> Dict[str, Any]:
        """處理執行上下文"""
        inputs = context.inputs
        context_data = context.context_data
        
        # 提取音訊轉錄
        audio_transcription = inputs.get("audio_transcription", "")
        user_confusion = inputs.get("user_confusion", "")
        selected_text = inputs.get("selected_text", "")
        
        # 預處理轉錄文字
        cleaned_transcription = self._clean_transcription(audio_transcription)
        
        # 初步分析困惑類型
        preliminary_confusion_type = self._analyze_confusion_type_preliminary(
            cleaned_transcription, user_confusion
        )
        
        # 分析情緒狀態
        emotional_indicators = self._analyze_emotional_state(cleaned_transcription)
        
        # 提取關鍵詞和短語
        key_phrases = self._extract_key_phrases(cleaned_transcription)
        
        # 分析語言複雜度
        language_complexity = self._analyze_language_complexity(cleaned_transcription)
        
        return {
            "audio_transcription": audio_transcription,
            "cleaned_transcription": cleaned_transcription,
            "user_confusion": user_confusion,
            "selected_text": selected_text,
            "preliminary_confusion_type": preliminary_confusion_type,
            "emotional_indicators": emotional_indicators,
            "key_phrases": key_phrases,
            "language_complexity": language_complexity,
            "transcription_length": len(cleaned_transcription),
            "word_count": len(cleaned_transcription.split()) if cleaned_transcription else 0
        }
    
    def _clean_transcription(self, transcription: str) -> str:
        """清理轉錄文字"""
        if not transcription:
            return ""
        
        # 移除 Whisper 常見的轉錄錯誤
        cleaned = transcription
        
        # 移除重複的詞語
        words = cleaned.split()
        deduplicated_words = []
        prev_word = ""
        
        for word in words:
            if word.lower() != prev_word.lower():
                deduplicated_words.append(word)
            prev_word = word
        
        cleaned = " ".join(deduplicated_words)
        
        # 移除多餘的標點符號
        cleaned = re.sub(r'[.]{2,}', '.', cleaned)
        cleaned = re.sub(r'[,]{2,}', ',', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.strip()
    
    def _analyze_confusion_type_preliminary(
        self, 
        transcription: str, 
        user_confusion: str
    ) -> ConfusionType:
        """初步分析困惑類型"""
        combined_text = f"{transcription} {user_confusion}".lower()
        
        type_scores = {}
        
        for confusion_type, keywords in self.analysis_keywords.items():
            score = 0
            for keyword in keywords:
                score += combined_text.count(keyword.lower())
            type_scores[confusion_type] = score
        
        # 返回得分最高的類型
        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            if type_scores[best_type] > 0:
                return best_type
        
        # 預設為概念理解
        return ConfusionType.CONCEPT_UNDERSTANDING
    
    def _analyze_emotional_state(self, transcription: str) -> Dict[str, float]:
        """分析情緒狀態"""
        text_lower = transcription.lower()
        emotion_scores = {}
        
        for emotion, indicators in self.emotion_indicators.items():
            score = 0
            for indicator in indicators:
                score += text_lower.count(indicator.lower())
            emotion_scores[emotion] = score
        
        # 正規化分數
        total_score = sum(emotion_scores.values())
        if total_score > 0:
            emotion_scores = {
                emotion: score / total_score 
                for emotion, score in emotion_scores.items()
            }
        
        return emotion_scores
    
    def _extract_key_phrases(self, transcription: str) -> List[str]:
        """提取關鍵短語"""
        if not transcription:
            return []
        
        # 簡化的關鍵短語提取
        phrases = []
        
        # 提取問句
        questions = re.findall(r'[^.!?]*\?[^.!?]*', transcription)
        phrases.extend([q.strip() for q in questions if len(q.strip()) > 10])
        
        # 提取技術術語 (包含英文的短語)
        tech_terms = re.findall(r'\b[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*\b', transcription)
        phrases.extend(tech_terms)
        
        # 提取連續的名詞短語 (簡化版)
        words = transcription.split()
        for i in range(len(words) - 1):
            if len(words[i]) > 3 and len(words[i+1]) > 3:
                phrase = f"{words[i]} {words[i+1]}"
                if not any(char.isdigit() for char in phrase):
                    phrases.append(phrase)
        
        # 去重並限制數量
        unique_phrases = list(dict.fromkeys(phrases))
        return unique_phrases[:10]
    
    def _analyze_language_complexity(self, transcription: str) -> Dict[str, Any]:
        """分析語言複雜度"""
        if not transcription:
            return {"level": "simple", "indicators": []}
        
        complexity_indicators = []
        complexity_score = 0
        
        words = transcription.split()
        sentences = re.split(r'[.!?]+', transcription)
        
        # 平均詞長
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
        if avg_word_length > 6:
            complexity_score += 1
            complexity_indicators.append("long_words")
        
        # 平均句長
        avg_sentence_length = len(words) / len(sentences) if sentences else 0
        if avg_sentence_length > 15:
            complexity_score += 1
            complexity_indicators.append("long_sentences")
        
        # 技術術語數量
        tech_terms = len(re.findall(r'\b[A-Z][a-zA-Z]*\b', transcription))
        if tech_terms > 3:
            complexity_score += 1
            complexity_indicators.append("technical_terms")
        
        # 英文夾雜比例
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', transcription))
        if english_words / len(words) > 0.2 if words else False:
            complexity_score += 1
            complexity_indicators.append("mixed_language")
        
        # 判斷複雜度等級
        if complexity_score >= 3:
            level = "complex"
        elif complexity_score >= 2:
            level = "moderate"
        else:
            level = "simple"
        
        return {
            "level": level,
            "score": complexity_score,
            "indicators": complexity_indicators,
            "avg_word_length": avg_word_length,
            "avg_sentence_length": avg_sentence_length,
            "tech_terms_count": tech_terms
        }
    
    async def _generate_prompt(self, processed_input: Dict[str, Any]) -> str:
        """生成分析 prompt"""
        
        transcription = processed_input["cleaned_transcription"]
        user_confusion = processed_input["user_confusion"]
        preliminary_type = processed_input["preliminary_confusion_type"]
        emotional_indicators = processed_input["emotional_indicators"]
        key_phrases = processed_input["key_phrases"]
        complexity = processed_input["language_complexity"]
        
        prompt = f"""你是音訊語意分析專家，專門分析用戶的音訊困惑並提供深度語意理解。

## 音訊轉錄內容
```
{transcription}
```

## 用戶文字困惑描述
{user_confusion}

## 初步分析結果
- 初步困惑類型: {preliminary_type.value}
- 情緒指標: {emotional_indicators}
- 關鍵短語: {key_phrases}
- 語言複雜度: {complexity['level']} (評分: {complexity['score']})

## 分析任務
請進行深度語意分析，並以 JSON 格式輸出：

### 困惑類型分類
- **concept_understanding**: 概念理解困惑
- **application_problem**: 應用實作困惑
- **background_knowledge**: 背景知識困惑
- **implementation_details**: 實作細節困惑
- **terminology_confusion**: 術語定義困惑
- **process_flow**: 流程步驟困惑
- **comparison_analysis**: 比較分析困惑

### 難度等級評估
- **beginner**: 初學者等級
- **intermediate**: 中級等級
- **advanced**: 高級等級
- **expert**: 專家等級

### 情緒狀態識別
- **confused**: 困惑不解
- **frustrated**: 挫折沮喪
- **curious**: 好奇探索
- **excited**: 興奮期待

### 學習意圖分析
- **understand**: 理解概念
- **apply**: 實際應用
- **compare**: 比較分析
- **troubleshoot**: 問題排解

```json
{{
  "confusion_analysis": {{
    "primary_confusion_type": "confusion_type",
    "secondary_confusion_types": ["type1", "type2"],
    "confidence_score": 0.85,
    "reasoning": "為什麼判斷為這個困惑類型"
  }},
  "difficulty_assessment": {{
    "level": "difficulty_level",
    "indicators": ["指標1", "指標2"],
    "user_background_estimate": "估計用戶背景知識水平"
  }},
  "emotional_analysis": {{
    "primary_emotion": "emotion",
    "intensity": 0.7,
    "emotional_progression": "情緒變化描述",
    "support_needed": "需要的情緒支持類型"
  }},
  "semantic_structure": {{
    "key_concepts": ["概念1", "概念2", "概念3"],
    "specific_questions": ["具體問題1", "具體問題2"],
    "implicit_assumptions": ["隱含假設1", "隱含假設2"],
    "knowledge_gaps": ["知識缺口1", "知識缺口2"]
  }},
  "learning_context": {{
    "learning_intent": "intent_type",
    "preferred_learning_style": "visual/auditory/kinesthetic/reading",
    "attention_focus_areas": ["重點關注區域"],
    "suggested_teaching_approach": "建議的教學方法"
  }},
  "communication_patterns": {{
    "language_style": "formal/casual/technical",
    "expression_clarity": 0.8,
    "technical_vocabulary_level": "basic/intermediate/advanced",
    "cultural_context_clues": ["文化背景線索"]
  }},
  "sources": ["audio_transcription", "user_confusion"]
}}
```

請確保輸出是有效的 JSON 格式，包含所有必要欄位。"""

        return prompt
    
    async def _parse_model_response(self, response: str) -> Dict[str, Any]:
        """解析模型回應"""
        try:
            # 解析 JSON
            if response.strip().startswith('{'):
                analysis_data = json.loads(response.strip())
            else:
                # 提取 JSON 部分
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    analysis_data = json.loads(json_match.group(1))
                else:
                    raise ValueError("No valid JSON found in response")
            
            # 驗證並標準化結果
            validated_result = self._validate_semantic_analysis(analysis_data)
            
            return validated_result
            
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Failed to parse audio semantic response: {str(e)}")
            
            # 回退到基礎分析
            return self._create_fallback_semantic_analysis(response)
    
    def _validate_semantic_analysis(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """驗證語意分析結果"""
        # 確保必要欄位存在
        if "confusion_analysis" not in analysis_data:
            analysis_data["confusion_analysis"] = {
                "primary_confusion_type": "concept_understanding",
                "secondary_confusion_types": [],
                "confidence_score": 0.7,
                "reasoning": "Default analysis"
            }
        
        if "difficulty_assessment" not in analysis_data:
            analysis_data["difficulty_assessment"] = {
                "level": "intermediate",
                "indicators": [],
                "user_background_estimate": "General knowledge"
            }
        
        if "emotional_analysis" not in analysis_data:
            analysis_data["emotional_analysis"] = {
                "primary_emotion": "confused",
                "intensity": 0.6,
                "emotional_progression": "Standard confusion pattern",
                "support_needed": "Clear explanation"
            }
        
        if "semantic_structure" not in analysis_data:
            analysis_data["semantic_structure"] = {
                "key_concepts": [],
                "specific_questions": [],
                "implicit_assumptions": [],
                "knowledge_gaps": []
            }
        
        if "learning_context" not in analysis_data:
            analysis_data["learning_context"] = {
                "learning_intent": "understand",
                "preferred_learning_style": "visual",
                "attention_focus_areas": [],
                "suggested_teaching_approach": "step-by-step explanation"
            }
        
        if "communication_patterns" not in analysis_data:
            analysis_data["communication_patterns"] = {
                "language_style": "casual",
                "expression_clarity": 0.7,
                "technical_vocabulary_level": "intermediate",
                "cultural_context_clues": []
            }
        
        if "sources" not in analysis_data:
            analysis_data["sources"] = ["audio_semantic_agent"]
        
        return analysis_data
    
    def _create_fallback_semantic_analysis(self, original_response: str) -> Dict[str, Any]:
        """建立回退語意分析結果"""
        return {
            "confusion_analysis": {
                "primary_confusion_type": "concept_understanding",
                "secondary_confusion_types": [],
                "confidence_score": 0.6,
                "reasoning": "Fallback analysis due to parsing error"
            },
            "difficulty_assessment": {
                "level": "intermediate",
                "indicators": ["parsing_error"],
                "user_background_estimate": "Unknown background"
            },
            "emotional_analysis": {
                "primary_emotion": "confused",
                "intensity": 0.5,
                "emotional_progression": "Unknown progression",
                "support_needed": "Clear explanation"
            },
            "semantic_structure": {
                "key_concepts": ["audio_content"],
                "specific_questions": ["general_inquiry"],
                "implicit_assumptions": [],
                "knowledge_gaps": ["unknown"]
            },
            "learning_context": {
                "learning_intent": "understand",
                "preferred_learning_style": "visual",
                "attention_focus_areas": ["general_content"],
                "suggested_teaching_approach": "comprehensive_explanation"
            },
            "communication_patterns": {
                "language_style": "unknown",
                "expression_clarity": 0.5,
                "technical_vocabulary_level": "intermediate",
                "cultural_context_clues": []
            },
            "sources": ["audio_semantic_agent_fallback"],
            "fallback_reason": original_response[:200] + "..." if len(original_response) > 200 else original_response
        }