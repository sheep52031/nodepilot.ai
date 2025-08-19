"""
NodePilot 結果整合與格式化模組
統一輸出格式和品質保證，實作多 Agent 結果的一致性檢查
"""

import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import json


@dataclass
class FormattingResult:
    """格式化結果資料結構"""
    formatted_content: str
    format_type: str  # markdown, html, json
    quality_score: float
    processing_notes: List[str]
    metadata: Dict[str, Any]


class MarkdownFormatter:
    """Markdown 格式化器"""
    
    def __init__(self):
        self.logger = logging.getLogger("MarkdownFormatter")
    
    def format_teaching_content(self, content: str) -> str:
        """格式化教學內容為標準 Markdown"""
        if not content:
            return ""
        
        # 清理和標準化內容
        content = self._clean_content(content)
        content = self._standardize_headers(content)
        content = self._format_code_blocks(content)
        content = self._format_lists(content)
        content = self._add_learning_sections(content)
        
        return content.strip()
    
    def _clean_content(self, content: str) -> str:
        """清理內容格式"""
        # 移除多餘的空行
        content = re.sub(r'\n\n\n+', '\n\n', content)
        
        # 清理行尾空白
        lines = [line.rstrip() for line in content.split('\n')]
        
        return '\n'.join(lines)
    
    def _standardize_headers(self, content: str) -> str:
        """標準化標題格式"""
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            
            # 確保標題前後有適當的空行
            if line.startswith('#'):
                if formatted_lines and formatted_lines[-1].strip():
                    formatted_lines.append('')
                formatted_lines.append(line)
                formatted_lines.append('')
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def _format_code_blocks(self, content: str) -> str:
        """格式化程式碼區塊"""
        # 確保程式碼區塊有正確的語言標註
        content = re.sub(
            r'```\s*\n((?:(?!```).)*)\n```',
            r'```\n\1\n```',
            content,
            flags=re.DOTALL
        )
        
        # 為未標註的程式碼區塊添加語言
        content = re.sub(
            r'```\n((?:(?!```).)*(?:def |class |import |from )(?:(?!```).)*)\n```',
            r'```python\n\1\n```',
            content,
            flags=re.DOTALL
        )
        
        return content
    
    def _format_lists(self, content: str) -> str:
        """格式化清單項目"""
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            # 標準化清單符號
            line = re.sub(r'^[\s]*[*-]\s+', '- ', line)
            line = re.sub(r'^[\s]*(\d+)\.\s+', r'\1. ', line)
            formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def _add_learning_sections(self, content: str) -> str:
        """添加學習結構化區塊"""
        if '## 重點摘要' not in content and '## 延伸學習' not in content:
            # 如果內容沒有結構化，添加基本結構
            content += '\n\n## 💡 重點摘要\n\n以上是針對您困惑的詳細說明。\n\n## 📚 延伸學習\n\n建議進一步了解相關概念和實作方式。'
        
        return content


class QualityChecker:
    """內容品質檢查器"""
    
    def __init__(self):
        self.logger = logging.getLogger("QualityChecker")
        
    def assess_content_quality(self, content: str, context: Dict[str, Any]) -> float:
        """評估內容品質 (0.0 - 1.0)"""
        if not content:
            return 0.0
        
        score = 0.0
        total_checks = 0
        
        # 1. 長度檢查 (0.2)
        length_score = self._check_content_length(content)
        score += length_score * 0.2
        total_checks += 0.2
        
        # 2. 結構檢查 (0.3)
        structure_score = self._check_structure(content)
        score += structure_score * 0.3
        total_checks += 0.3
        
        # 3. 相關性檢查 (0.3)
        relevance_score = self._check_relevance(content, context)
        score += relevance_score * 0.3
        total_checks += 0.3
        
        # 4. 完整性檢查 (0.2)
        completeness_score = self._check_completeness(content)
        score += completeness_score * 0.2
        total_checks += 0.2
        
        return min(1.0, score / total_checks)
    
    def _check_content_length(self, content: str) -> float:
        """檢查內容長度適當性"""
        length = len(content)
        
        if length < 100:
            return 0.2  # 太短
        elif length < 300:
            return 0.6  # 稍短但可接受
        elif length < 1500:
            return 1.0  # 理想長度
        elif length < 3000:
            return 0.8  # 稍長但詳細
        else:
            return 0.5  # 可能過長
    
    def _check_structure(self, content: str) -> float:
        """檢查內容結構"""
        score = 0.0
        
        # 是否有標題
        if re.search(r'^#+\s+', content, re.MULTILINE):
            score += 0.3
        
        # 是否有清單
        if re.search(r'^[-*+]\s+', content, re.MULTILINE):
            score += 0.2
        
        # 是否有程式碼區塊
        if '```' in content:
            score += 0.3
        
        # 是否有適當的段落
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) >= 2:
            score += 0.2
        
        return min(1.0, score)
    
    def _check_relevance(self, content: str, context: Dict[str, Any]) -> float:
        """檢查內容相關性"""
        confusion_note = context.get("confusion_note", "")
        selected_text = context.get("selected_text", "")
        
        if not confusion_note and not selected_text:
            return 0.8  # 無法判斷，給予中等分數
        
        score = 0.0
        
        # 檢查是否提及用戶的困惑
        if confusion_note:
            confusion_words = confusion_note.lower().split()
            content_lower = content.lower()
            
            matches = sum(1 for word in confusion_words if word in content_lower)
            if matches > 0:
                score += 0.5 * (matches / len(confusion_words))
        
        # 檢查是否引用了選取的文字
        if selected_text and selected_text.lower() in content.lower():
            score += 0.5
        
        return min(1.0, score)
    
    def _check_completeness(self, content: str) -> float:
        """檢查內容完整性"""
        score = 0.0
        
        # 是否有解釋/說明
        if re.search(r'(是|的|這|該|可以|能夠)', content):
            score += 0.3
        
        # 是否有範例
        if re.search(r'(例如|範例|舉例|比如)', content) or '```' in content:
            score += 0.4
        
        # 是否有建議或總結
        if re.search(r'(建議|總結|記住|注意|重點)', content):
            score += 0.3
        
        return min(1.0, score)


class ConflictResolver:
    """衝突解決器 - 處理多 Agent 結果的衝突"""
    
    def __init__(self):
        self.logger = logging.getLogger("ConflictResolver")
    
    def resolve_conflicts(self, agent_results: Dict[str, Any]) -> Dict[str, Any]:
        """解決 Agent 結果中的衝突"""
        resolved_results = {}
        conflicts_found = []
        
        # 檢查規劃建議與實際執行的一致性
        planner_result = agent_results.get("planner", {})
        content_result = agent_results.get("content_generator", {})
        
        if planner_result and content_result:
            conflict_check = self._check_planning_consistency(planner_result, content_result)
            if conflict_check["has_conflict"]:
                conflicts_found.append(conflict_check)
        
        # 檢查 RAG 檢索結果與內容生成的相關性
        rag_result = agent_results.get("rag_retriever", {})
        if rag_result and content_result:
            relevance_check = self._check_rag_relevance(rag_result, content_result)
            if relevance_check["has_conflict"]:
                conflicts_found.append(relevance_check)
        
        resolved_results = {
            "original_results": agent_results,
            "conflicts_detected": conflicts_found,
            "resolution_applied": len(conflicts_found) > 0,
            "final_recommendation": self._generate_final_recommendation(agent_results, conflicts_found)
        }
        
        return resolved_results
    
    def _check_planning_consistency(self, planner: Dict, content: Dict) -> Dict[str, Any]:
        """檢查規劃與內容生成的一致性"""
        plan_strategy = planner.get("plan", {}).get("teaching_strategy", "")
        generated_content = content.get("teaching_content", "")
        
        # 簡化的一致性檢查
        if plan_strategy and generated_content:
            if len(generated_content) < 200 and "詳細" in plan_strategy:
                return {
                    "has_conflict": True,
                    "type": "length_mismatch",
                    "description": "規劃建議詳細說明，但生成內容過短",
                    "recommendation": "建議擴展內容或調整規劃策略"
                }
        
        return {"has_conflict": False}
    
    def _check_rag_relevance(self, rag: Dict, content: Dict) -> Dict[str, Any]:
        """檢查 RAG 結果與內容的相關性"""
        relevant_notes = rag.get("relevant_notes", [])
        teaching_content = content.get("teaching_content", "")
        
        if relevant_notes and teaching_content:
            # 檢查是否有引用筆記內容
            note_titles = [note.get("title", "") for note in relevant_notes]
            content_lower = teaching_content.lower()
            
            referenced = any(title.lower() in content_lower for title in note_titles if title)
            
            if len(relevant_notes) > 0 and not referenced:
                return {
                    "has_conflict": True,
                    "type": "unused_rag_results",
                    "description": f"找到 {len(relevant_notes)} 篇相關筆記但未被引用",
                    "recommendation": "建議在教學內容中整合相關筆記"
                }
        
        return {"has_conflict": False}
    
    def _generate_final_recommendation(self, results: Dict[str, Any], conflicts: List[Dict]) -> str:
        """生成最終建議"""
        if not conflicts:
            return "所有 Agent 結果一致，品質良好"
        
        recommendations = []
        for conflict in conflicts:
            recommendations.append(conflict.get("recommendation", ""))
        
        return "發現衝突，建議：" + "；".join(filter(None, recommendations))


class ResultIntegrationService:
    """結果整合服務主類"""
    
    def __init__(self):
        self.markdown_formatter = MarkdownFormatter()
        self.quality_checker = QualityChecker()
        self.conflict_resolver = ConflictResolver()
        self.logger = logging.getLogger("ResultIntegrationService")
    
    def integrate_and_format(self, 
                           agent_results: Dict[str, Any],
                           user_context: Dict[str, Any],
                           format_type: str = "markdown") -> FormattingResult:
        """整合並格式化多 Agent 結果"""
        
        processing_notes = []
        
        try:
            # 1. 解決衝突
            conflict_resolution = self.conflict_resolver.resolve_conflicts(agent_results)
            if conflict_resolution["conflicts_detected"]:
                processing_notes.append(f"發現並解決 {len(conflict_resolution['conflicts_detected'])} 個衝突")
            
            # 2. 提取主要教學內容
            primary_content = self._extract_primary_content(agent_results)
            
            # 3. 格式化內容
            if format_type == "markdown":
                formatted_content = self.markdown_formatter.format_teaching_content(primary_content)
            else:
                formatted_content = primary_content
            
            # 4. 品質評估
            quality_score = self.quality_checker.assess_content_quality(
                formatted_content, user_context
            )
            
            # 5. 整合額外資訊
            formatted_content = self._enhance_with_agent_insights(
                formatted_content, agent_results
            )
            
            processing_notes.append(f"品質評分: {quality_score:.2f}")
            
            return FormattingResult(
                formatted_content=formatted_content,
                format_type=format_type,
                quality_score=quality_score,
                processing_notes=processing_notes,
                metadata={
                    "agents_used": list(agent_results.keys()),
                    "conflict_resolution": conflict_resolution,
                    "enhancement_applied": True,
                    "processed_at": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            self.logger.error(f"結果整合失敗: {e}")
            
            # 降級處理
            fallback_content = self._generate_fallback_content(agent_results, user_context)
            
            return FormattingResult(
                formatted_content=fallback_content,
                format_type=format_type,
                quality_score=0.5,
                processing_notes=["使用降級處理", f"錯誤: {str(e)}"],
                metadata={
                    "fallback_used": True,
                    "error": str(e),
                    "processed_at": datetime.now().isoformat()
                }
            )
    
    def _extract_primary_content(self, agent_results: Dict[str, Any]) -> str:
        """提取主要教學內容"""
        # 優先使用內容生成 Agent 的結果
        content_agent = agent_results.get("content_generator", {})
        if content_agent and content_agent.get("teaching_content"):
            return content_agent["teaching_content"]
        
        # 降級：嘗試從其他 Agent 組合內容
        combined_content = "# 學習指引\n\n"
        
        # 加入規劃建議
        planner = agent_results.get("planner", {})
        if planner:
            plan_text = planner.get("plan", {}).get("teaching_strategy", "")
            if plan_text:
                combined_content += f"## 學習策略\n{plan_text}\n\n"
        
        # 加入上下文分析
        context_agent = agent_results.get("context_analyzer", {})
        if context_agent:
            context_summary = context_agent.get("context_analysis", {}).get("context_summary", "")
            if context_summary:
                combined_content += f"## 內容分析\n{context_summary}\n\n"
        
        return combined_content
    
    def _enhance_with_agent_insights(self, content: str, agent_results: Dict[str, Any]) -> str:
        """用 Agent 洞察增強內容"""
        
        # 加入 RAG 筆記參考
        rag_result = agent_results.get("rag_retriever", {})
        if rag_result and rag_result.get("relevant_notes"):
            notes_section = "\n\n## 📖 相關筆記參考\n\n"
            for note in rag_result["relevant_notes"][:3]:  # 限制 3 篇
                title = note.get("title", "未命名筆記")
                relevance = note.get("relevance_score", 0)
                notes_section += f"- **{title}** (相關度: {relevance:.2f})\n"
            
            content += notes_section
        
        # 加入音訊分析洞察
        audio_result = agent_results.get("audio_processor", {})
        if audio_result and audio_result.get("audio_analysis"):
            audio_analysis = audio_result["audio_analysis"]
            if audio_analysis.get("structured_confusion"):
                content += f"\n\n## 🎙️ 您的表達分析\n\n{audio_analysis['structured_confusion']}"
        
        return content
    
    def _generate_fallback_content(self, agent_results: Dict[str, Any], user_context: Dict[str, Any]) -> str:
        """生成降級內容"""
        confusion_note = user_context.get("confusion_note", "")
        selected_text = user_context.get("selected_text", "")
        
        return f"""# 學習協助

## 關於您的困惑
{confusion_note}

## 選取的內容
```
{selected_text[:200] + '...' if len(selected_text) > 200 else selected_text}
```

## 建議
由於 AI 系統處理異常，建議：
1. 重新整理相關文件
2. 尋找官方範例參考
3. 嘗試實際操作驗證

系統將持續改進以提供更好的學習體驗。"""


# 全域結果整合服務實例
result_integration_service = ResultIntegrationService()