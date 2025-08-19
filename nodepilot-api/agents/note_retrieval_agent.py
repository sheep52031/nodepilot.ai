"""
筆記檢索 Agent - RAG 知識庫智慧檢索
=================================

整合 Obsidian 筆記向量檢索，提供個人化學習記錄。
"""

import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from .base_agent import BaseAgent, AgentExecutionResult
from ai_core.scheduler import AgentExecutionContext
from ai_core.model_pool import ModelPool


@dataclass
class NoteEntry:
    """筆記條目"""
    title: str
    content: str
    file_path: str
    tags: List[str]
    created_date: datetime
    modified_date: datetime
    relevance_score: float = 0.0
    excerpt: str = ""


@dataclass
class RetrievalResult:
    """檢索結果"""
    query: str
    notes: List[NoteEntry]
    total_found: int
    search_strategy: str
    embedding_model: str


class NoteRetrievalAgent(BaseAgent):
    """
    筆記檢索 Agent
    
    功能:
    - Obsidian 筆記庫向量檢索
    - 基於困惑語意的相關筆記搜尋
    - 歷史學習記錄檢索
    - 個人化知識圖譜分析
    """
    
    def __init__(self, model_pool: ModelPool, notes_database_path: Optional[str] = None):
        super().__init__(model_pool, "note_retrieval")
        
        self.notes_database_path = notes_database_path
        self.embedding_model = "text-embedding-3-large"  # OpenAI 模型
        self.max_retrieved_notes = 5
        self.relevance_threshold = 0.7
        
        # 模擬的筆記資料庫 (實際應該連接到真實的向量資料庫)
        self._mock_notes_db = []
        self._initialize_mock_notes()
    
    def _initialize_mock_notes(self):
        """初始化模擬筆記資料庫"""
        # 這裡模擬一些範例筆記，實際實作應該連接到 Obsidian vault
        mock_notes = [
            {
                "title": "React Hooks 學習筆記",
                "content": "React Hooks 是函數組件中使用狀態和其他 React 特性的方法。useState 用於狀態管理，useEffect 用於副作用處理...",
                "file_path": "/vault/react/hooks.md",
                "tags": ["react", "hooks", "frontend"],
                "created_date": datetime(2024, 1, 15),
                "modified_date": datetime(2024, 2, 1)
            },
            {
                "title": "Python 異步程式設計",
                "content": "asyncio 是 Python 的異步程式設計庫。async/await 語法讓異步程式碼更容易理解...",
                "file_path": "/vault/python/async.md", 
                "tags": ["python", "async", "programming"],
                "created_date": datetime(2024, 1, 20),
                "modified_date": datetime(2024, 1, 25)
            },
            {
                "title": "API 設計最佳實踐",
                "content": "REST API 設計應該遵循 RESTful 原則。HTTP 方法的正確使用：GET 用於讀取，POST 用於創建...",
                "file_path": "/vault/api/design.md",
                "tags": ["api", "rest", "design"],
                "created_date": datetime(2024, 2, 5),
                "modified_date": datetime(2024, 2, 10)
            }
        ]
        
        for note_data in mock_notes:
            note = NoteEntry(**note_data)
            self._mock_notes_db.append(note)
    
    def get_task_type(self) -> str:
        return "note_retrieval"
    
    async def execute(self, context: AgentExecutionContext) -> AgentExecutionResult:
        """執行筆記檢索"""
        self.logger.info("Starting note retrieval")
        
        return await self._execute_with_model(context, priority="cost")
    
    async def _process_context(self, context: AgentExecutionContext) -> Dict[str, Any]:
        """處理執行上下文"""
        inputs = context.inputs
        context_data = context.context_data
        
        # 提取搜尋資訊
        user_confusion = inputs.get("user_confusion", "")
        selected_text = inputs.get("selected_text", "")
        
        # 從其他 Agent 的結果中提取額外搜尋線索
        confusion_analysis = None
        context_analysis = None
        
        # 檢查是否有困惑分析結果
        if "confusion_analysis" in context_data:
            confusion_data = context_data["confusion_analysis"]
            if isinstance(confusion_data, list) and confusion_data:
                confusion_analysis = confusion_data[0].get("data", {})
        
        # 檢查是否有上下文分析結果
        if "article_structure" in context_data:
            context_structure_data = context_data["article_structure"]
            if isinstance(context_structure_data, list) and context_structure_data:
                context_analysis = context_structure_data[0].get("data", {})
        
        # 建構搜尋查詢
        search_queries = self._build_search_queries(
            user_confusion, selected_text, confusion_analysis, context_analysis
        )
        
        # 分析搜尋策略
        search_strategy = self._determine_search_strategy(
            confusion_analysis, len(search_queries)
        )
        
        return {
            "user_confusion": user_confusion,
            "selected_text": selected_text,
            "search_queries": search_queries,
            "search_strategy": search_strategy,
            "confusion_analysis": confusion_analysis,
            "context_analysis": context_analysis,
            "total_queries": len(search_queries)
        }
    
    def _build_search_queries(
        self,
        user_confusion: str,
        selected_text: str,
        confusion_analysis: Optional[Dict[str, Any]],
        context_analysis: Optional[Dict[str, Any]]
    ) -> List[str]:
        """建構搜尋查詢"""
        queries = []
        
        # 基礎查詢：用戶困惑
        if user_confusion:
            queries.append(user_confusion)
        
        # 從選取文字提取關鍵概念
        if selected_text:
            # 簡化的關鍵詞提取
            key_terms = self._extract_key_terms(selected_text)
            if key_terms:
                queries.append(" ".join(key_terms[:3]))  # 前3個關鍵詞
        
        # 從困惑分析提取搜尋詞
        if confusion_analysis:
            semantic_structure = confusion_analysis.get("semantic_structure", {})
            key_concepts = semantic_structure.get("key_concepts", [])
            if key_concepts:
                queries.append(" ".join(key_concepts[:2]))
            
            specific_questions = semantic_structure.get("specific_questions", [])
            if specific_questions:
                queries.extend(specific_questions[:2])
        
        # 從上下文分析提取主題
        if context_analysis:
            article_structure = context_analysis.get("article_structure", {})
            key_concepts = article_structure.get("key_concepts", [])
            if key_concepts:
                queries.append(" ".join(key_concepts[:2]))
        
        # 去重並限制查詢數量
        unique_queries = list(dict.fromkeys(queries))
        return unique_queries[:5]  # 最多5個查詢
    
    def _extract_key_terms(self, text: str) -> List[str]:
        """簡化的關鍵詞提取"""
        import re
        
        # 移除標點符號並分詞
        words = re.findall(r'\b\w+\b', text.lower())
        
        # 過濾停用詞
        stop_words = {
            "的", "是", "在", "有", "和", "了", "我", "你", "他", "她", "它",
            "this", "that", "the", "and", "or", "but", "in", "on", "at", "to"
        }
        
        # 提取有意義的詞彙
        meaningful_words = [
            word for word in words 
            if len(word) > 2 and word not in stop_words
        ]
        
        # 簡單的詞頻統計
        word_freq = {}
        for word in meaningful_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 按頻率排序並返回前幾個
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:8]]
    
    def _determine_search_strategy(
        self,
        confusion_analysis: Optional[Dict[str, Any]],
        query_count: int
    ) -> str:
        """決定搜尋策略"""
        if confusion_analysis:
            confusion_type = confusion_analysis.get("confusion_analysis", {}).get("primary_confusion_type", "")
            
            if confusion_type == "concept_understanding":
                return "concept_focused"
            elif confusion_type in ["application_problem", "implementation_details"]:
                return "practical_focused"
            elif confusion_type == "comparison_analysis":
                return "comparative_focused"
        
        if query_count >= 3:
            return "multi_angle"
        else:
            return "broad_search"
    
    async def _perform_vector_search(
        self, 
        queries: List[str], 
        strategy: str
    ) -> List[NoteEntry]:
        """執行向量搜尋"""
        # 這是模擬的向量搜尋，實際實作應該使用真實的向量資料庫
        all_results = []
        
        for query in queries:
            # 模擬向量相似度搜尋
            query_results = await self._mock_vector_search(query)
            all_results.extend(query_results)
        
        # 去重並按相關性排序
        unique_results = {}
        for note in all_results:
            if note.file_path not in unique_results:
                unique_results[note.file_path] = note
            else:
                # 保留相關性更高的版本
                if note.relevance_score > unique_results[note.file_path].relevance_score:
                    unique_results[note.file_path] = note
        
        sorted_results = sorted(
            unique_results.values(), 
            key=lambda x: x.relevance_score, 
            reverse=True
        )
        
        return sorted_results[:self.max_retrieved_notes]
    
    async def _mock_vector_search(self, query: str) -> List[NoteEntry]:
        """模擬向量搜尋"""
        # 簡化的文字相似度計算
        results = []
        query_lower = query.lower()
        
        for note in self._mock_notes_db:
            # 計算簡化的相似度分數
            title_score = self._calculate_text_similarity(query_lower, note.title.lower())
            content_score = self._calculate_text_similarity(query_lower, note.content.lower())
            tags_score = self._calculate_tags_similarity(query_lower, note.tags)
            
            # 加權計算總分數
            total_score = (title_score * 0.4 + content_score * 0.4 + tags_score * 0.2)
            
            if total_score > self.relevance_threshold:
                note_copy = NoteEntry(
                    title=note.title,
                    content=note.content,
                    file_path=note.file_path,
                    tags=note.tags,
                    created_date=note.created_date,
                    modified_date=note.modified_date,
                    relevance_score=total_score,
                    excerpt=self._create_excerpt(note.content, query_lower)
                )
                results.append(note_copy)
        
        return results
    
    def _calculate_text_similarity(self, query: str, text: str) -> float:
        """計算文字相似度"""
        query_words = set(query.split())
        text_words = set(text.split())
        
        if not query_words:
            return 0.0
        
        intersection = query_words.intersection(text_words)
        return len(intersection) / len(query_words)
    
    def _calculate_tags_similarity(self, query: str, tags: List[str]) -> float:
        """計算標籤相似度"""
        query_words = set(query.split())
        tag_words = set(" ".join(tags).lower().split())
        
        if not query_words:
            return 0.0
        
        intersection = query_words.intersection(tag_words)
        return len(intersection) / len(query_words)
    
    def _create_excerpt(self, content: str, query: str) -> str:
        """建立內容摘要"""
        words = content.split()
        
        # 找到查詢詞在內容中的位置
        for i, word in enumerate(words):
            if any(q_word in word.lower() for q_word in query.split()):
                # 提取周圍的文字作為摘要
                start = max(0, i - 15)
                end = min(len(words), i + 15)
                excerpt_words = words[start:end]
                
                excerpt = " ".join(excerpt_words)
                if start > 0:
                    excerpt = "..." + excerpt
                if end < len(words):
                    excerpt = excerpt + "..."
                
                return excerpt
        
        # 如果沒找到，返回前100個字
        return " ".join(words[:20]) + "..." if len(words) > 20 else content
    
    async def _generate_prompt(self, processed_input: Dict[str, Any]) -> str:
        """生成檢索分析 prompt"""
        
        search_queries = processed_input["search_queries"]
        search_strategy = processed_input["search_strategy"]
        user_confusion = processed_input["user_confusion"]
        
        # 執行向量搜尋
        retrieved_notes = await self._perform_vector_search(search_queries, search_strategy)
        
        # 建構筆記內容用於分析
        notes_content = ""
        for i, note in enumerate(retrieved_notes, 1):
            notes_content += f"""
### 筆記 {i}: {note.title}
**標籤**: {', '.join(note.tags)}
**相關性**: {note.relevance_score:.2f}
**摘要**: {note.excerpt}
**建立時間**: {note.created_date.strftime('%Y-%m-%d')}

"""
        
        prompt = f"""你是個人化學習助手，專門分析用戶的筆記庫並提供相關的學習記錄。

## 用戶困惑
{user_confusion}

## 搜尋策略
{search_strategy}

## 檢索到的相關筆記
{notes_content if notes_content else "未找到相關筆記"}

## 分析任務
請分析檢索結果並提供個人化的學習建議，以 JSON 格式輸出：

```json
{{
  "retrieval_summary": {{
    "total_notes_found": {len(retrieved_notes)},
    "search_effectiveness": "excellent/good/moderate/poor",
    "coverage_assessment": "檢索覆蓋度評估",
    "relevance_quality": "相關性品質評估"
  }},
  "related_notes": [
    {{
      "title": "筆記標題",
      "relevance_to_confusion": "與困惑的相關性說明",
      "key_insights": ["洞察1", "洞察2"],
      "learning_value": "high/medium/low",
      "suggested_review_order": 1
    }}
  ],
  "knowledge_connections": {{
    "related_concepts": ["相關概念1", "相關概念2"],
    "learning_progression": "建議的學習順序",
    "knowledge_gaps": ["發現的知識缺口"],
    "reinforcement_opportunities": ["可以加強的知識點"]
  }},
  "personalized_recommendations": {{
    "review_priority": ["優先複習的筆記"],
    "extension_topics": ["可以延伸學習的主題"],
    "practice_suggestions": ["實作建議"],
    "connection_building": ["建立知識連結的方法"]
  }},
  "learning_history_insights": {{
    "previous_struggles": ["之前遇到的類似困難"],
    "successful_patterns": ["成功的學習模式"],
    "improvement_areas": ["可以改進的地方"],
    "learning_style_indicators": ["學習風格指標"]
  }},
  "sources": ["note_retrieval_agent", "personal_notes_database"]
}}
```

如果沒有找到相關筆記，請提供建議建立哪些新筆記來填補知識缺口。
輸出必須是有效的 JSON 格式。"""

        return prompt
    
    async def _parse_model_response(self, response: str) -> Dict[str, Any]:
        """解析模型回應"""
        try:
            # 解析 JSON
            if response.strip().startswith('{'):
                analysis_data = json.loads(response.strip())
            else:
                # 提取 JSON 部分
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    analysis_data = json.loads(json_match.group(1))
                else:
                    raise ValueError("No valid JSON found in response")
            
            # 驗證結果結構
            validated_result = self._validate_retrieval_result(analysis_data)
            
            return validated_result
            
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Failed to parse note retrieval response: {str(e)}")
            
            # 回退到基礎分析
            return self._create_fallback_retrieval_result(response)
    
    def _validate_retrieval_result(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """驗證檢索結果"""
        # 確保必要欄位存在
        if "retrieval_summary" not in analysis_data:
            analysis_data["retrieval_summary"] = {
                "total_notes_found": 0,
                "search_effectiveness": "moderate",
                "coverage_assessment": "Basic search completed",
                "relevance_quality": "Standard quality"
            }
        
        if "related_notes" not in analysis_data:
            analysis_data["related_notes"] = []
        
        if "knowledge_connections" not in analysis_data:
            analysis_data["knowledge_connections"] = {
                "related_concepts": [],
                "learning_progression": "Sequential learning",
                "knowledge_gaps": [],
                "reinforcement_opportunities": []
            }
        
        if "personalized_recommendations" not in analysis_data:
            analysis_data["personalized_recommendations"] = {
                "review_priority": [],
                "extension_topics": [],
                "practice_suggestions": [],
                "connection_building": []
            }
        
        if "learning_history_insights" not in analysis_data:
            analysis_data["learning_history_insights"] = {
                "previous_struggles": [],
                "successful_patterns": [],
                "improvement_areas": [],
                "learning_style_indicators": []
            }
        
        if "sources" not in analysis_data:
            analysis_data["sources"] = ["note_retrieval_agent"]
        
        return analysis_data
    
    def _create_fallback_retrieval_result(self, original_response: str) -> Dict[str, Any]:
        """建立回退檢索結果"""
        return {
            "retrieval_summary": {
                "total_notes_found": 0,
                "search_effectiveness": "poor",
                "coverage_assessment": "Fallback analysis due to parsing error",
                "relevance_quality": "Unknown quality"
            },
            "related_notes": [],
            "knowledge_connections": {
                "related_concepts": [],
                "learning_progression": "Unable to determine",
                "knowledge_gaps": ["Analysis parsing failed"],
                "reinforcement_opportunities": []
            },
            "personalized_recommendations": {
                "review_priority": [],
                "extension_topics": [],
                "practice_suggestions": ["Retry note search"],
                "connection_building": []
            },
            "learning_history_insights": {
                "previous_struggles": [],
                "successful_patterns": [],
                "improvement_areas": ["Note retrieval system"],
                "learning_style_indicators": []
            },
            "sources": ["note_retrieval_agent_fallback"],
            "fallback_reason": original_response[:200] + "..." if len(original_response) > 200 else original_response
        }