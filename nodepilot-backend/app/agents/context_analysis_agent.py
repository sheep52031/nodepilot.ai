"""
文章上下文分析 Agent - 智慧文章結構分析和段落提取
===============================================

無需 RAG 向量搜索，直接分析文章結構和相關段落。
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from .base_agent import BaseAgent, AgentExecutionResult
from ai_core.scheduler import AgentExecutionContext
from ai_core.model_pool import ModelPool


@dataclass
class ArticleSection:
    """文章段落"""
    title: str
    content: str
    level: int  # 標題層級 1-6
    start_pos: int
    end_pos: int
    relevance_score: float = 0.0


@dataclass
class ArticleStructure:
    """文章結構"""
    title: str
    sections: List[ArticleSection]
    total_length: int
    main_topics: List[str]


class ContextAnalysisAgent(BaseAgent):
    """
    文章上下文分析 Agent
    
    功能:
    - 解析文章結構 (標題、段落、程式碼塊)
    - 提取選取文字周圍的相關段落
    - 分析文章主題和概念關係
    - 動態調整上下文範圍
    """
    
    def __init__(self, model_pool: ModelPool):
        super().__init__(model_pool, "context_analysis")
        
        # 段落提取配置
        self.default_context_paragraphs = 5  # 預設前後各5段
        self.max_context_length = 3000       # 最大上下文長度
        self.min_context_length = 500        # 最小上下文長度
    
    def get_task_type(self) -> str:
        return "context_analysis"
    
    async def execute(self, context: AgentExecutionContext) -> AgentExecutionResult:
        """執行文章上下文分析"""
        self.logger.info("Starting context analysis")
        
        return await self._execute_with_model(context, priority="balanced")
    
    async def _process_context(self, context: AgentExecutionContext) -> Dict[str, Any]:
        """處理執行上下文"""
        inputs = context.inputs
        
        # 提取基礎資料
        selected_text = inputs.get("selected_text", "")
        page_context = inputs.get("page_context", {})
        user_confusion = inputs.get("user_confusion", "")
        
        # 從頁面上下文提取文章內容
        full_article = self._extract_full_article_content(page_context)
        
        # 解析文章結構
        article_structure = self._parse_article_structure(full_article)
        
        # 定位選取文字在文章中的位置
        selected_position = self._locate_selected_text(selected_text, full_article)
        
        # 提取相關段落
        relevant_sections = self._extract_relevant_sections(
            article_structure, selected_position, user_confusion
        )
        
        # 動態調整上下文範圍
        context_window = self._adjust_context_window(
            relevant_sections, selected_text, user_confusion
        )
        
        return {
            "selected_text": selected_text,
            "full_article": full_article,
            "article_structure": article_structure,
            "selected_position": selected_position,
            "relevant_sections": relevant_sections,
            "context_window": context_window,
            "user_confusion": user_confusion,
            "page_url": page_context.get("url", ""),
            "page_title": page_context.get("title", "")
        }
    
    def _extract_full_article_content(self, page_context: Dict[str, Any]) -> str:
        """從頁面上下文提取完整文章內容"""
        # 優先順序：article_content > page_content > 其他
        content = ""
        
        if "article_content" in page_context:
            content = page_context["article_content"]
        elif "page_content" in page_context:
            content = page_context["page_content"]
        elif "content" in page_context:
            content = page_context["content"]
        else:
            # 如果沒有完整內容，嘗試從其他欄位組合
            title = page_context.get("title", "")
            description = page_context.get("description", "")
            content = f"{title}\n\n{description}"
        
        return content
    
    def _parse_article_structure(self, article_content: str) -> ArticleStructure:
        """解析文章結構"""
        sections = []
        
        # 使用正則表達式提取標題和段落
        # 支援 Markdown 格式和 HTML 格式
        
        # Markdown 標題 (# ## ### 等)
        md_header_pattern = r'^(#{1,6})\s+(.+)$'
        
        # HTML 標題 (<h1> <h2> 等)
        html_header_pattern = r'<h([1-6])[^>]*>([^<]+)</h[1-6]>'
        
        lines = article_content.split('\n')
        current_section = None
        current_content = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # 檢查 Markdown 標題
            md_match = re.match(md_header_pattern, line, re.MULTILINE)
            if md_match:
                # 儲存前一個段落
                if current_section:
                    current_section.content = '\n'.join(current_content).strip()
                    current_section.end_pos = i
                    sections.append(current_section)
                
                # 開始新段落
                level = len(md_match.group(1))
                title = md_match.group(2).strip()
                current_section = ArticleSection(
                    title=title,
                    content="",
                    level=level,
                    start_pos=i,
                    end_pos=i
                )
                current_content = []
                continue
            
            # 檢查 HTML 標題
            html_match = re.search(html_header_pattern, line)
            if html_match:
                # 儲存前一個段落
                if current_section:
                    current_section.content = '\n'.join(current_content).strip()
                    current_section.end_pos = i
                    sections.append(current_section)
                
                # 開始新段落
                level = int(html_match.group(1))
                title = html_match.group(2).strip()
                current_section = ArticleSection(
                    title=title,
                    content="",
                    level=level,
                    start_pos=i,
                    end_pos=i
                )
                current_content = []
                continue
            
            # 一般內容行
            if current_section is None:
                # 如果還沒有段落，建立一個預設段落
                current_section = ArticleSection(
                    title="Introduction",
                    content="",
                    level=1,
                    start_pos=0,
                    end_pos=0
                )
            
            if line:  # 非空行
                current_content.append(line)
        
        # 處理最後一個段落
        if current_section:
            current_section.content = '\n'.join(current_content).strip()
            current_section.end_pos = len(lines)
            sections.append(current_section)
        
        # 如果沒有找到任何結構，將整篇文章當作一個段落
        if not sections:
            sections.append(ArticleSection(
                title="Article Content",
                content=article_content,
                level=1,
                start_pos=0,
                end_pos=len(lines)
            ))
        
        # 提取主題
        main_topics = self._extract_main_topics(sections)
        
        return ArticleStructure(
            title=sections[0].title if sections else "Untitled",
            sections=sections,
            total_length=len(article_content),
            main_topics=main_topics
        )
    
    def _extract_main_topics(self, sections: List[ArticleSection]) -> List[str]:
        """提取文章主要主題"""
        topics = []
        
        # 從段落標題提取主題
        for section in sections:
            if section.level <= 2:  # 只考慮主要標題
                # 清理標題並提取關鍵詞
                clean_title = re.sub(r'[^a-zA-Z\u4e00-\u9fff\s]', ' ', section.title)
                words = clean_title.split()
                
                # 過濾短詞和常見詞
                meaningful_words = [
                    word for word in words 
                    if len(word) > 2 and word.lower() not in ['the', 'and', 'or', 'but', '的', '和', '或']
                ]
                
                topics.extend(meaningful_words)
        
        # 去重並返回前10個主題
        unique_topics = list(dict.fromkeys(topics))
        return unique_topics[:10]
    
    def _locate_selected_text(self, selected_text: str, full_article: str) -> Dict[str, Any]:
        """定位選取文字在文章中的位置"""
        if not selected_text or not full_article:
            return {"found": False, "position": -1, "section_index": -1}
        
        # 清理選取文字（移除多餘空白）
        clean_selected = re.sub(r'\s+', ' ', selected_text.strip())
        
        # 在完整文章中尋找
        position = full_article.find(clean_selected)
        
        if position == -1:
            # 如果完全匹配失敗，嘗試模糊匹配
            position = self._fuzzy_locate_text(clean_selected, full_article)
        
        return {
            "found": position != -1,
            "position": position,
            "text_length": len(selected_text),
            "context_start": max(0, position - 200),
            "context_end": min(len(full_article), position + len(selected_text) + 200)
        }
    
    def _fuzzy_locate_text(self, selected_text: str, full_article: str) -> int:
        """模糊定位文字"""
        # 嘗試找到最長的共同子字串
        words = selected_text.split()
        
        for length in range(len(words), 0, -1):
            for start in range(len(words) - length + 1):
                phrase = ' '.join(words[start:start + length])
                position = full_article.find(phrase)
                if position != -1:
                    return position
        
        return -1
    
    def _extract_relevant_sections(
        self,
        article_structure: ArticleStructure,
        selected_position: Dict[str, Any],
        user_confusion: str
    ) -> List[ArticleSection]:
        """提取相關段落"""
        if not selected_position["found"]:
            # 如果沒找到選取文字，返回前幾個段落
            return article_structure.sections[:3]
        
        position = selected_position["position"]
        relevant_sections = []
        
        # 找到包含選取文字的段落
        target_section_index = -1
        for i, section in enumerate(article_structure.sections):
            section_start = self._estimate_section_position(section, article_structure)
            section_end = section_start + len(section.content)
            
            if section_start <= position <= section_end:
                target_section_index = i
                break
        
        if target_section_index == -1:
            target_section_index = 0
        
        # 提取目標段落和相鄰段落
        start_index = max(0, target_section_index - 2)
        end_index = min(len(article_structure.sections), target_section_index + 3)
        
        for i in range(start_index, end_index):
            section = article_structure.sections[i]
            
            # 計算相關性分數
            relevance_score = self._calculate_section_relevance(
                section, user_confusion, i == target_section_index
            )
            section.relevance_score = relevance_score
            
            relevant_sections.append(section)
        
        # 按相關性排序
        relevant_sections.sort(key=lambda s: s.relevance_score, reverse=True)
        
        return relevant_sections
    
    def _estimate_section_position(
        self, 
        section: ArticleSection, 
        article_structure: ArticleStructure
    ) -> int:
        """估算段落在完整文章中的位置"""
        # 簡化估算：基於段落在列表中的位置
        total_sections = len(article_structure.sections)
        section_index = next(
            (i for i, s in enumerate(article_structure.sections) if s == section), 
            0
        )
        
        estimated_position = int(
            (section_index / total_sections) * article_structure.total_length
        )
        
        return estimated_position
    
    def _calculate_section_relevance(
        self, 
        section: ArticleSection, 
        user_confusion: str, 
        is_target_section: bool
    ) -> float:
        """計算段落相關性分數"""
        score = 0.0
        
        # 目標段落基礎分數
        if is_target_section:
            score += 0.5
        
        # 標題層級權重 (越高層級越重要)
        level_weight = max(0.1, 1.0 - (section.level - 1) * 0.15)
        score += level_weight * 0.2
        
        # 內容長度權重 (適中長度更好)
        content_length = len(section.content)
        if 100 <= content_length <= 1000:
            score += 0.2
        elif content_length > 50:
            score += 0.1
        
        # 關鍵字匹配
        confusion_keywords = set(re.findall(r'\w+', user_confusion.lower()))
        section_text = (section.title + " " + section.content).lower()
        section_keywords = set(re.findall(r'\w+', section_text))
        
        # 計算關鍵字重疊度
        if confusion_keywords and section_keywords:
            overlap = len(confusion_keywords.intersection(section_keywords))
            keyword_score = overlap / len(confusion_keywords)
            score += keyword_score * 0.3
        
        return min(1.0, score)
    
    def _adjust_context_window(
        self,
        relevant_sections: List[ArticleSection],
        selected_text: str,
        user_confusion: str
    ) -> Dict[str, Any]:
        """動態調整上下文範圍"""
        context_parts = []
        total_length = 0
        
        # 確保包含選取文字
        if selected_text:
            context_parts.append({
                "type": "selected_text",
                "content": selected_text,
                "importance": "high"
            })
            total_length += len(selected_text)
        
        # 按重要性加入相關段落
        for section in relevant_sections:
            section_content = f"## {section.title}\n{section.content}"
            
            if total_length + len(section_content) <= self.max_context_length:
                context_parts.append({
                    "type": "article_section",
                    "title": section.title,
                    "content": section.content,
                    "relevance_score": section.relevance_score,
                    "importance": "high" if section.relevance_score > 0.7 else "medium"
                })
                total_length += len(section_content)
            else:
                # 如果超出限制，嘗試截斷
                remaining_space = self.max_context_length - total_length
                if remaining_space > 100:
                    truncated_content = section.content[:remaining_space - 50] + "..."
                    context_parts.append({
                        "type": "article_section",
                        "title": section.title,
                        "content": truncated_content,
                        "relevance_score": section.relevance_score,
                        "importance": "medium",
                        "truncated": True
                    })
                break
        
        # 確保最小上下文長度
        if total_length < self.min_context_length and relevant_sections:
            # 嘗試添加更多內容
            for section in article_structure.sections:
                if section not in relevant_sections:
                    section_content = f"## {section.title}\n{section.content}"
                    if total_length + len(section_content) <= self.max_context_length:
                        context_parts.append({
                            "type": "additional_section",
                            "title": section.title,
                            "content": section.content[:300] + "...",
                            "importance": "low"
                        })
                        total_length += len(section_content)
                        
                        if total_length >= self.min_context_length:
                            break
        
        return {
            "parts": context_parts,
            "total_length": total_length,
            "sections_count": len([p for p in context_parts if p["type"] in ["article_section", "additional_section"]]),
            "has_selected_text": bool(selected_text)
        }
    
    async def _generate_prompt(self, processed_input: Dict[str, Any]) -> str:
        """生成分析 prompt"""
        
        context_window = processed_input["context_window"]
        article_structure = processed_input["article_structure"]
        user_confusion = processed_input["user_confusion"]
        
        # 建構上下文內容
        context_content = ""
        for part in context_window["parts"]:
            if part["type"] == "selected_text":
                context_content += f"**用戶選取的文字**:\n{part['content']}\n\n"
            elif part["type"] in ["article_section", "additional_section"]:
                context_content += f"## {part['title']}\n{part['content']}\n\n"
        
        prompt = f"""你是文章上下文分析專家，需要分析文章結構並提取與用戶困惑相關的關鍵資訊。

## 用戶困惑
{user_confusion}

## 文章內容
{context_content}

## 文章結構概覽
- 文章標題: {article_structure.title}
- 總段落數: {len(article_structure.sections)}
- 主要主題: {', '.join(article_structure.main_topics)}

## 分析任務
請進行以下分析並以 JSON 格式輸出：

1. **文章結構分析** - 識別文章的層次結構和主要概念
2. **相關段落識別** - 找出與用戶困惑最相關的段落
3. **概念關係圖譜** - 建立文章中概念之間的關係
4. **上下文摘要** - 為後續 Agent 提供精簡的上下文摘要

```json
{{
  "article_structure": {{
    "main_theme": "文章主要主題",
    "key_concepts": ["概念1", "概念2", "概念3"],
    "structure_type": "tutorial/explanation/reference/discussion",
    "difficulty_level": "beginner/intermediate/advanced"
  }},
  "relevant_sections": [
    {{
      "title": "段落標題",
      "summary": "段落摘要",
      "relevance_score": 0.95,
      "key_points": ["要點1", "要點2"],
      "relates_to_confusion": "為什麼這個段落與用戶困惑相關"
    }}
  ],
  "concept_relationships": {{
    "central_concept": "核心概念",
    "related_concepts": [
      {{"concept": "相關概念", "relationship": "is-part-of/enables/requires"}}
    ],
    "prerequisites": ["前置概念1", "前置概念2"],
    "applications": ["應用場景1", "應用場景2"]
  }},
  "context_summary": {{
    "background": "背景知識摘要",
    "focus_area": "重點關注區域",
    "complexity_factors": ["複雜度因素"],
    "suggested_approach": "建議的學習方法"
  }},
  "sources": ["article_content"]
}}
```

輸出必須是有效的 JSON 格式，不要包含額外說明。"""

        return prompt
    
    async def _parse_model_response(self, response: str) -> Dict[str, Any]:
        """解析模型回應"""
        try:
            # 嘗試解析 JSON
            import json
            
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
            validated_result = self._validate_analysis_result(analysis_data)
            
            return validated_result
            
        except (json.JSONDecodeError, ValueError) as e:
            self.logger.error(f"Failed to parse context analysis response: {str(e)}")
            
            # 回退到基礎分析
            return self._create_fallback_analysis(response)
    
    def _validate_analysis_result(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """驗證分析結果"""
        # 確保必要欄位存在
        if "article_structure" not in analysis_data:
            analysis_data["article_structure"] = {
                "main_theme": "Unknown",
                "key_concepts": [],
                "structure_type": "explanation",
                "difficulty_level": "intermediate"
            }
        
        if "relevant_sections" not in analysis_data:
            analysis_data["relevant_sections"] = []
        
        if "concept_relationships" not in analysis_data:
            analysis_data["concept_relationships"] = {
                "central_concept": "Unknown",
                "related_concepts": [],
                "prerequisites": [],
                "applications": []
            }
        
        if "context_summary" not in analysis_data:
            analysis_data["context_summary"] = {
                "background": "Context analysis completed",
                "focus_area": "Selected text area",
                "complexity_factors": [],
                "suggested_approach": "Step-by-step learning"
            }
        
        if "sources" not in analysis_data:
            analysis_data["sources"] = ["context_analysis_agent"]
        
        return analysis_data
    
    def _create_fallback_analysis(self, original_response: str) -> Dict[str, Any]:
        """建立回退分析結果"""
        return {
            "article_structure": {
                "main_theme": "Article analysis",
                "key_concepts": ["content", "analysis"],
                "structure_type": "explanation",
                "difficulty_level": "intermediate"
            },
            "relevant_sections": [
                {
                    "title": "Content Analysis",
                    "summary": "Basic content analysis performed",
                    "relevance_score": 0.7,
                    "key_points": ["Content structure", "Key information"],
                    "relates_to_confusion": "General content relevance"
                }
            ],
            "concept_relationships": {
                "central_concept": "Content understanding",
                "related_concepts": [],
                "prerequisites": [],
                "applications": []
            },
            "context_summary": {
                "background": "Fallback analysis due to parsing error",
                "focus_area": "General content area",
                "complexity_factors": ["Unknown complexity"],
                "suggested_approach": "General learning approach"
            },
            "sources": ["context_analysis_agent_fallback"],
            "fallback_reason": original_response[:300] + "..." if len(original_response) > 300 else original_response
        }