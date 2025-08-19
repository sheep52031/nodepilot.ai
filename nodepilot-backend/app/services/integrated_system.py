"""
NodePilot 整合系統
協調 AI-CORE 的企業級架構與 API Terminal 的 FastAPI 整合
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("IntegratedSystem")

# AI-CORE 系統導入 (暫時禁用循環導入問題)
try:
    from ai_core.system_initializer import SystemInitializer
    from ai_core.scheduler import AgentScheduler as AICoreSched
    from ai_core.model_pool import ModelPool
    AI_CORE_AVAILABLE = True
    logger.info("✅ AI-CORE 系統導入成功")
except ImportError as e:
    logger.warning(f"⚠️ AI-CORE 系統導入失敗，將使用 API Terminal 系統: {e}")
    SystemInitializer = None
    AICoreSched = None
    ModelPool = None
    AI_CORE_AVAILABLE = False

# API Terminal 既有系統
from rag_service import rag_service
from result_formatter import result_integration_service
from model_manager import model_manager as api_model_manager

logger = logging.getLogger("IntegratedSystem")


class IntegratedNodePilotSystem:
    """整合的 NodePilot 系統 - 合併 AI-CORE 與 API 實作的優點"""
    
    def __init__(self):
        self.ai_core_scheduler: Optional[AICoreSched] = None
        self.system_initializer = SystemInitializer() if AI_CORE_AVAILABLE else None
        self.api_model_manager = api_model_manager
        self.rag_service = rag_service
        self.result_service = result_integration_service
        self.initialized = False
        self.ai_core_available = AI_CORE_AVAILABLE
        self.logger = logging.getLogger("IntegratedSystem")
        
    async def initialize(self):
        """初始化整合系統"""
        try:
            self.logger.info("🚀 開始初始化 NodePilot 整合系統...")
            
            # 1. 嘗試初始化 AI-CORE 調度系統
            if self.ai_core_available and self.system_initializer:
                try:
                    self.ai_core_scheduler = await self.system_initializer.initialize_system()
                    self.logger.info("✅ AI-CORE 調度系統初始化完成")
                except Exception as e:
                    self.logger.warning(f"⚠️ AI-CORE 初始化失敗，將使用 API Terminal 系統: {e}")
                    self.ai_core_available = False
            else:
                self.logger.info("🔄 使用 API Terminal 系統 (AI-CORE 不可用)")
            
            # 2. 初始化 RAG 服務
            await self.rag_service.initialize()
            self.logger.info("✅ RAG 筆記檢索服務初始化完成")
            
            # 3. 建立模型管理協調
            self._coordinate_model_managers()
            self.logger.info("✅ 模型管理系統協調完成")
            
            self.initialized = True
            system_type = "AI-CORE + API Terminal" if self.ai_core_available else "API Terminal"
            self.logger.info(f"🎉 NodePilot 整合系統初始化成功 ({system_type})")
            
        except Exception as e:
            self.logger.error(f"❌ 系統初始化失敗: {e}")
            raise
    
    def _coordinate_model_managers(self):
        """協調兩套模型管理系統"""
        # 這裡可以實作模型管理的協調邏輯
        # 暫時保持兩套系統並行運作
        self.logger.info("模型管理協調：保持 AI-CORE ModelPool 和 API ModelManager 並行")
    
    async def execute_user_request(self, 
                                 user_confusion: str,
                                 selected_text: str = "",
                                 page_context: Dict[str, Any] = None,
                                 audio_transcription: str = None) -> Dict[str, Any]:
        """
        執行用戶請求 - 使用 AI-CORE 的企業級調度器
        但保留 API Terminal 的結果格式化和 RAG 整合
        """
        
        if not self.initialized:
            raise RuntimeError("系統尚未初始化，請先調用 initialize()")
        
        try:
            # 如果 AI-CORE 可用，使用企業級調度器
            if self.ai_core_available and self.ai_core_scheduler:
                try:
                    ai_core_result = await self.ai_core_scheduler.execute_user_request(
                        user_confusion=user_confusion,
                        selected_text=selected_text,
                        page_context=page_context or {},
                        audio_transcription=audio_transcription
                    )
                    
                    # 使用 API Terminal 的結果整合服務進行後處理
                    formatted_result = self._format_ai_core_result(ai_core_result)
                    
                    # 補充 RAG 筆記檢索
                    rag_supplement = await self._supplement_with_rag(user_confusion, selected_text)
                    
                    # 整合最終結果
                    final_result = self._integrate_final_result(
                        ai_core_result=formatted_result,
                        rag_supplement=rag_supplement
                    )
                    
                    return final_result
                    
                except Exception as e:
                    self.logger.warning(f"AI-CORE 執行失敗，降級到 API Terminal: {e}")
                    # 繼續執行降級邏輯
            
            # 降級：使用 API Terminal 系統
            return await self._fallback_to_api_system(
                user_confusion, selected_text, page_context, audio_transcription
            )
            
        except Exception as e:
            self.logger.error(f"執行用戶請求失敗: {e}")
            # 降級到 API Terminal 的原有系統
            return await self._fallback_to_api_system(
                user_confusion, selected_text, page_context, audio_transcription
            )
    
    def _format_ai_core_result(self, ai_core_result: Dict[str, Any]) -> Dict[str, Any]:
        """將 AI-CORE 結果格式化為 API Terminal 的標準格式"""
        return {
            "success": True,
            "teaching_content": ai_core_result.get("teaching_content", ""),
            "metadata": ai_core_result.get("metadata", {}),
            "agent_execution": {
                "session_id": ai_core_result.get("execution_id"),
                "agents_used": ai_core_result.get("agents_used", []),
                "ai_core_integration": True,
                "processing_time": ai_core_result.get("processing_time", 0)
            },
            "content_quality": {
                "quality_score": ai_core_result.get("quality", {}).get("score", 0.8),
                "processing_notes": ["使用 AI-CORE 企業級調度器"],
                "format_type": "markdown"
            }
        }
    
    async def _supplement_with_rag(self, user_confusion: str, selected_text: str) -> Dict[str, Any]:
        """使用 API Terminal 的 RAG 服務補充筆記檢索"""
        try:
            rag_results = await self.rag_service.search_relevant_notes(
                query=user_confusion,
                selected_text=selected_text,
                top_k=3
            )
            
            return {
                "rag_notes": [
                    {
                        "title": result.document.title,
                        "content_preview": result.document.content[:200],
                        "relevance_score": result.relevance_score,
                        "reasoning": result.reasoning
                    }
                    for result in rag_results
                ],
                "rag_service_used": "api_terminal_rag"
            }
            
        except Exception as e:
            self.logger.warning(f"RAG 補充檢索失敗: {e}")
            return {"rag_notes": [], "rag_service_used": "none"}
    
    def _integrate_final_result(self, 
                              ai_core_result: Dict[str, Any], 
                              rag_supplement: Dict[str, Any]) -> Dict[str, Any]:
        """整合 AI-CORE 結果和 RAG 補充資料"""
        
        final_result = ai_core_result.copy()
        
        # 添加 RAG 筆記到 metadata
        if rag_supplement.get("rag_notes"):
            final_result["metadata"]["supplementary_notes"] = rag_supplement["rag_notes"]
            
            # 如果教學內容中沒有筆記參考，添加它們
            teaching_content = final_result.get("teaching_content", "")
            if "相關筆記" not in teaching_content and rag_supplement["rag_notes"]:
                notes_section = "\n\n## 📖 補充筆記參考\n\n"
                for note in rag_supplement["rag_notes"][:2]:  # 限制 2 篇
                    notes_section += f"- **{note['title']}** ({note['reasoning']})\n"
                
                final_result["teaching_content"] += notes_section
        
        # 更新處理筆記
        final_result["content_quality"]["processing_notes"].append("整合 RAG 筆記檢索")
        final_result["integration_metadata"] = {
            "ai_core_used": True,
            "rag_supplement_used": len(rag_supplement.get("rag_notes", [])) > 0,
            "integration_timestamp": datetime.now().isoformat(),
            "system_version": "integrated_v1.0"
        }
        
        return final_result
    
    async def _fallback_to_api_system(self, 
                                    user_confusion: str,
                                    selected_text: str,
                                    page_context: Dict[str, Any],
                                    audio_transcription: str) -> Dict[str, Any]:
        """降級到 API Terminal 的原有系統"""
        self.logger.warning("降級使用 API Terminal 原有系統")
        
        try:
            # 使用原有的簡化 agent_scheduler 邏輯
            from agent_scheduler import agent_scheduler
            
            user_request = {
                "confusion_note": user_confusion,
                "selected_text": selected_text,
                "page_context": page_context or {},
                "audio_transcription": audio_transcription
            }
            
            tasks = await agent_scheduler.create_plan(user_request)
            execution_context = await agent_scheduler.execute_plan(tasks)
            
            return {
                "success": True,
                "teaching_content": execution_context.final_result.get("final_content", "降級處理：請稍後再試"),
                "agent_execution": {
                    "session_id": execution_context.session_id,
                    "agents_used": list(execution_context.intermediate_results.keys()),
                    "fallback_used": True,
                    "ai_core_integration": False
                },
                "metadata": {
                    "fallback_reason": "AI-CORE 系統執行失敗",
                    "system_version": "api_terminal_fallback"
                }
            }
            
        except Exception as e:
            self.logger.error(f"降級系統也失敗: {e}")
            return {
                "success": False,
                "error": "系統暫時不可用",
                "teaching_content": "抱歉，系統正在維護中，請稍後再試。",
                "metadata": {"error_details": str(e)}
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """取得整合系統狀態"""
        status = {
            "system_initialized": self.initialized,
            "components": {
                "ai_core_scheduler": self.ai_core_scheduler is not None,
                "rag_service": bool(self.rag_service.note_cache),
                "result_formatter": True,
                "model_managers": True
            },
            "integration_version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }
        
        if self.initialized and self.ai_core_scheduler:
            try:
                ai_core_status = await self.ai_core_scheduler.get_system_status()
                status["ai_core_details"] = ai_core_status
            except Exception as e:
                status["ai_core_details"] = {"error": str(e)}
                
        return status
    
    def get_model_usage_stats(self) -> Dict[str, Any]:
        """取得模型使用統計"""
        stats = {
            "api_terminal_stats": self.api_model_manager.get_usage_statistics(),
            "integration_mode": "dual_system"
        }
        
        # 如果 AI-CORE 有模型統計，也包含進來
        if self.initialized and hasattr(self.ai_core_scheduler, 'model_pool'):
            try:
                stats["ai_core_stats"] = self.ai_core_scheduler.model_pool.get_usage_stats()
            except Exception as e:
                stats["ai_core_stats"] = {"error": str(e)}
        
        return stats


# 全域整合系統實例
integrated_system = IntegratedNodePilotSystem()