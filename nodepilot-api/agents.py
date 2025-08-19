"""
NodePilot 具體 Agent 實作
實作各種專門的 AI Agent 執行邏輯
"""

import logging
import re
from typing import Dict, List, Optional, Any
from agent_scheduler import BaseAgent, AgentTask, AgentContext, AgentType
from model_manager import model_manager, ModelType


class PlannerAgent(BaseAgent):
    """任務規劃 Agent - 使用 GPT-4o/Claude 3.5 進行智慧規劃"""
    
    def __init__(self):
        super().__init__(AgentType.PLANNER)
        
    async def execute(self, task: AgentTask, context: AgentContext) -> Dict[str, Any]:
        user_request = task.input_data.get("user_request", {})
        
        system_prompt = """你是 NodePilot 的任務規劃專家。分析用戶的學習困惑，制定最佳的教學策略。

你的職責：
1. 分析用戶困惑的類型和複雜度
2. 判斷需要什麼樣的上下文資訊
3. 評估是否需要檢索筆記庫
4. 規劃個人化教學內容的結構

回應格式應為 JSON：
{
    "confusion_type": "概念理解/應用問題/背景知識/實作細節",
    "complexity_level": 1-5,
    "required_context": ["文章段落", "程式碼範例", "相關概念"],
    "teaching_strategy": "講解策略描述",
    "estimated_time": "預估處理時間(分鐘)"
}
"""
        
        user_prompt = f"""
**選取文字**: {user_request.get('selected_text', '')}
**困惑描述**: {user_request.get('confusion_note', '')}
**音檔轉錄**: {user_request.get('audio_transcription', '無')}
**文章來源**: {user_request.get('url', '')}

請分析此困惑並制定教學策略。
"""

        try:
            response = await model_manager.generate_with_fallback(
                model_type=ModelType.PLANNER,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            # 嘗試解析 JSON 回應
            import json
            try:
                plan_data = json.loads(response["content"])
            except json.JSONDecodeError:
                # 如果不是 JSON，則包裝為結構化資料
                plan_data = {
                    "confusion_type": "概念理解",
                    "complexity_level": 3,
                    "teaching_strategy": response["content"],
                    "estimated_time": 5
                }
            
            return {
                "plan": plan_data,
                "raw_response": response["content"],
                "tokens_used": response.get("tokens_used", 0),
                "processing_time": response.get("response_time", 0)
            }
            
        except Exception as e:
            self.logger.error(f"任務規劃失敗: {e}")
            # 降級：提供基本規劃
            return {
                "plan": {
                    "confusion_type": "概念理解", 
                    "complexity_level": 2,
                    "teaching_strategy": "提供基礎解釋和範例",
                    "estimated_time": 3
                },
                "raw_response": "使用預設教學策略",
                "tokens_used": 0,
                "processing_time": 0.1
            }


class ContextAnalyzerAgent(BaseAgent):
    """文章上下文分析 Agent - 無 RAG 智能段落提取"""
    
    def __init__(self):
        super().__init__(AgentType.CONTEXT_ANALYZER)
        
    async def execute(self, task: AgentTask, context: AgentContext) -> Dict[str, Any]:
        url = task.input_data.get("url", "")
        selected_text = task.input_data.get("selected_text", "")
        
        # 這裡實際上需要爬取文章內容，暫時使用模擬邏輯
        article_content = await self._fetch_article_content(url)
        
        system_prompt = """你是文章上下文分析專家。分析選取文字在整篇文章中的上下文關係。

任務：
1. 識別選取文字前後的關鍵段落
2. 分析文章結構和層級關係
3. 找出與困惑相關的程式碼塊或概念
4. 提供必要的背景知識連結

回應 JSON 格式：
{
    "relevant_sections": ["相關段落1", "相關段落2"],
    "article_structure": "文章結構摘要",
    "key_concepts": ["概念1", "概念2"],
    "code_examples": ["程式碼範例"],
    "context_summary": "上下文摘要"
}
"""
        
        user_prompt = f"""
**文章 URL**: {url}
**選取文字**: {selected_text}
**文章內容摘要**: {article_content[:1000]}

請分析選取文字的上下文關係。
"""

        try:
            response = await model_manager.generate_with_fallback(
                model_type=ModelType.CONTEXT_ANALYZER,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=1000,
                temperature=0.2
            )
            
            import json
            try:
                context_data = json.loads(response["content"])
            except json.JSONDecodeError:
                context_data = {
                    "context_summary": response["content"],
                    "relevant_sections": [selected_text],
                    "key_concepts": []
                }
            
            return {
                "context_analysis": context_data,
                "tokens_used": response.get("tokens_used", 0),
                "processing_time": response.get("response_time", 0)
            }
            
        except Exception as e:
            self.logger.error(f"上下文分析失敗: {e}")
            return {
                "context_analysis": {
                    "context_summary": f"分析文章「{url}」中的選取文字",
                    "relevant_sections": [selected_text],
                    "key_concepts": []
                },
                "tokens_used": 0,
                "processing_time": 0.1
            }
    
    async def _fetch_article_content(self, url: str) -> str:
        """取得文章內容 - 這裡需要實作爬蟲邏輯"""
        # TODO: 實際實作網頁爬取邏輯
        return f"模擬文章內容來自 {url}"


class AudioProcessorAgent(BaseAgent):
    """音訊語意結構化 Agent - 深度音訊理解"""
    
    def __init__(self):
        super().__init__(AgentType.AUDIO_PROCESSOR)
        
    async def execute(self, task: AgentTask, context: AgentContext) -> Dict[str, Any]:
        transcription = task.input_data.get("transcription", "")
        confusion_note = task.input_data.get("confusion_note", "")
        
        system_prompt = """你是音訊語意分析專家。將語音轉錄結構化為學習困惑的深度理解。

分析重點：
1. 困惑類型分類：概念理解/應用問題/背景知識/實作細節
2. 情緒狀態：困惑程度、急迫性、學習動機
3. 表達特徵：用詞習慣、技術水平判斷
4. 具體需求：期望得到什麼樣的幫助

回應 JSON 格式：
{
    "confusion_classification": "困惑類型",
    "emotional_state": "情緒分析",
    "technical_level": 1-5,
    "specific_needs": ["具體需求1", "需求2"],
    "key_phrases": ["關鍵詞語"],
    "urgency_level": 1-5,
    "structured_confusion": "結構化困惑描述"
}
"""
        
        user_prompt = f"""
**語音轉錄內容**:
{transcription}

**文字困惑描述**:
{confusion_note}

請深度分析用戶的語音表達，提供結構化的困惑理解。
"""

        try:
            response = await model_manager.generate_with_fallback(
                model_type=ModelType.CONTEXT_ANALYZER,  # 複用文章分析模型
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            import json
            try:
                audio_analysis = json.loads(response["content"])
            except json.JSONDecodeError:
                audio_analysis = {
                    "structured_confusion": response["content"],
                    "confusion_classification": "概念理解",
                    "technical_level": 3
                }
            
            return {
                "audio_analysis": audio_analysis,
                "original_transcription": transcription,
                "tokens_used": response.get("tokens_used", 0),
                "processing_time": response.get("response_time", 0)
            }
            
        except Exception as e:
            self.logger.error(f"音訊分析失敗: {e}")
            return {
                "audio_analysis": {
                    "structured_confusion": transcription or confusion_note,
                    "confusion_classification": "概念理解",
                    "technical_level": 3
                },
                "original_transcription": transcription,
                "tokens_used": 0,
                "processing_time": 0.1
            }


class RAGRetrieverAgent(BaseAgent):
    """筆記檢索 Agent - RAG 知識庫整合"""
    
    def __init__(self):
        super().__init__(AgentType.RAG_RETRIEVER)
        
    async def execute(self, task: AgentTask, context: AgentContext) -> Dict[str, Any]:
        confusion_note = task.input_data.get("confusion_note", "")
        selected_text = task.input_data.get("selected_text", "")
        
        try:
            # 使用 RAG 服務進行筆記檢索
            from rag_service import rag_service
            
            search_results = await rag_service.search_relevant_notes(
                query=confusion_note,
                selected_text=selected_text,
                top_k=5,
                min_relevance=0.3
            )
            
            # 格式化結果給其他 Agent 使用
            relevant_notes = []
            for result in search_results:
                relevant_notes.append({
                    "title": result.document.title,
                    "content_preview": result.document.content[:500],
                    "full_content": result.document.content,
                    "relevance_score": result.relevance_score,
                    "file_path": result.document.file_path,
                    "matched_snippets": result.matched_snippets,
                    "reasoning": result.reasoning,
                    "tags": result.document.tags
                })
            
            return {
                "relevant_notes": relevant_notes,
                "search_query": confusion_note,
                "notes_count": len(relevant_notes),
                "processing_time": 0.5,
                "rag_search_successful": True,
                "search_metadata": {
                    "selected_text_included": bool(selected_text),
                    "min_relevance_threshold": 0.3
                }
            }
            
        except Exception as e:
            self.logger.error(f"RAG 檢索失敗: {e}")
            
            # 降級：返回基本筆記結構
            return {
                "relevant_notes": [{
                    "title": "系統降級模式",
                    "content_preview": f"由於 RAG 服務不可用，無法檢索與「{confusion_note}」相關的筆記。請稍後再試。",
                    "relevance_score": 0.1,
                    "file_path": "system/fallback",
                    "reasoning": "降級處理"
                }],
                "search_query": confusion_note,
                "notes_count": 1,
                "processing_time": 0.1,
                "rag_search_successful": False,
                "error": str(e)
            }


class ContentGeneratorAgent(BaseAgent):
    """教學內容生成 Agent - Artifacts 可視化教學"""
    
    def __init__(self):
        super().__init__(AgentType.CONTENT_GENERATOR)
        
    async def execute(self, task: AgentTask, context: AgentContext) -> Dict[str, Any]:
        user_request = task.input_data.get("user_request", {})
        session_id = task.input_data.get("session_id")
        
        # 整合所有 Agent 的分析結果
        planner_result = context.intermediate_results.get("planner", {})
        context_result = context.intermediate_results.get("context_analyzer", {})
        audio_result = context.intermediate_results.get("audio_processor", {})
        rag_result = context.intermediate_results.get("rag_retriever", {})
        
        system_prompt = """你是 NodePilot 的專業教學內容生成專家。根據多 Agent 分析結果，生成個人化的教學內容。

你需要整合：
1. 任務規劃建議
2. 文章上下文分析
3. 音訊語意理解  
4. 相關筆記資料

生成要求：
- 針對具體困惑提供直接解答
- 使用 Markdown 格式
- 包含程式碼範例（如適用）
- 提供後續學習建議
- 保持專業但友善的語調

請用繁體中文回答。
"""
        
        user_prompt = f"""
**用戶困惑**:
- 選取文字: {user_request.get('selected_text', '')}
- 困惑描述: {user_request.get('confusion_note', '')}
- 文章來源: {user_request.get('url', '')}

**Agent 分析結果**:
- 規劃建議: {planner_result.get('plan', {})}
- 上下文分析: {context_result.get('context_analysis', {})}
- 音訊分析: {audio_result.get('audio_analysis', {})}
- 相關筆記: {rag_result.get('relevant_notes', [])}

請基於以上分析，生成個人化的教學內容。
"""

        try:
            response = await model_manager.generate_with_fallback(
                model_type=ModelType.CONTENT_GENERATOR,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            teaching_content = response["content"]
            
            # 後處理：確保內容格式正確
            teaching_content = self._post_process_content(teaching_content)
            
            return {
                "teaching_content": teaching_content,
                "content_type": "markdown",
                "generation_strategy": planner_result.get('plan', {}).get('teaching_strategy', '預設策略'),
                "tokens_used": response.get("tokens_used", 0),
                "processing_time": response.get("response_time", 0),
                "session_id": session_id
            }
            
        except Exception as e:
            self.logger.error(f"教學內容生成失敗: {e}")
            # 降級：提供基本教學內容
            fallback_content = self._generate_fallback_content(user_request)
            return {
                "teaching_content": fallback_content,
                "content_type": "markdown", 
                "generation_strategy": "降級策略",
                "tokens_used": 0,
                "processing_time": 0.1,
                "session_id": session_id
            }
    
    def _post_process_content(self, content: str) -> str:
        """後處理教學內容"""
        # 確保 Markdown 格式正確
        lines = content.split('\n')
        processed_lines = []
        
        for line in lines:
            # 處理程式碼區塊
            if line.strip().startswith('```') and not line.strip().endswith('```'):
                processed_lines.append(line)
            # 處理標題格式
            elif line.strip() and not line.startswith('#') and not line.startswith('-') and not line.startswith('*'):
                if len(line.strip()) < 50 and line.isupper():
                    processed_lines.append(f"## {line.strip()}")
                else:
                    processed_lines.append(line)
            else:
                processed_lines.append(line)
        
        return '\n'.join(processed_lines)
    
    def _generate_fallback_content(self, user_request: Dict[str, Any]) -> str:
        """生成降級教學內容"""
        selected_text = user_request.get('selected_text', '')
        confusion_note = user_request.get('confusion_note', '')
        
        return f"""# 學習指引

## 關於您選取的內容
```
{selected_text[:200]}...
```

## 針對您的困惑
{confusion_note}

## 建議
1. 重新閱讀相關段落，注意關鍵概念
2. 查找官方文件了解更多細節
3. 嘗試實際動手練習

由於 AI 服務暫時不可用，這是基礎的學習建議。請稍後再試以獲得更詳細的個人化教學內容。
"""


# 註冊所有 Agent 到全域調度器
def register_all_agents():
    """註冊所有 Agent"""
    from agent_scheduler import agent_scheduler
    
    agent_scheduler.register_agent(PlannerAgent())
    agent_scheduler.register_agent(ContextAnalyzerAgent()) 
    agent_scheduler.register_agent(AudioProcessorAgent())
    agent_scheduler.register_agent(RAGRetrieverAgent())
    agent_scheduler.register_agent(ContentGeneratorAgent())
    
    return agent_scheduler