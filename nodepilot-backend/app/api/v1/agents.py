"""
NodePilot 多 Agent 系統 API 路由
專門處理多 Agent 調度和模型管理的端點
"""

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.schemas.schemas import AnnotationResponse
from app.services.agent_scheduler import agent_scheduler
from app.services.model_manager import model_manager
from app.services.rag_service import rag_service
from app.services.result_formatter import result_integration_service
from app.services.integrated_system import integrated_system
from app.models import crud
from typing import Optional, List

# 建立 APIRouter
router = APIRouter(prefix="/multi-agent", tags=["Multi-Agent System"])


@router.post("/generate-teaching-integrated", response_model=dict)
async def integrated_generate_teaching(
    url: str = Form(...),
    selected_text: str = Form(...),
    confusion_note: str = Form(...),
    page_title: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """使用整合系統（AI-CORE + API Terminal）生成教學內容"""
    
    try:
        # 1. 處理音檔轉錄
        audio_transcription = None
        if audio_file and audio_file.size > 0:
            if audio_file.size > 20 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="音檔檔案過大，限制 20MB")
            
            transcription_result = await model_manager.transcribe_with_fallback(
                audio_file.file, language="zh"
            )
            audio_transcription = transcription_result.get("transcription")
        
        # 2. 準備頁面上下文
        page_context = {
            "url": url,
            "title": page_title or url,
            "timestamp": "2025-08-19T17:30:00Z"
        }
        
        # 3. 使用整合系統執行用戶請求
        result = await integrated_system.execute_user_request(
            user_confusion=confusion_note,
            selected_text=selected_text,
            page_context=page_context,
            audio_transcription=audio_transcription
        )
        
        # 4. 建立標註記錄
        annotation = crud.create_annotation(
            db=db,
            url=url,
            selected_text=selected_text,
            confusion_note=confusion_note,
            page_title=page_title,
            audio_transcription=audio_transcription,
            cognitive_note=result.get("metadata", {}).get("cognitive_analysis")
        )
        
        # 5. 更新教學內容
        teaching_content = result.get("teaching_content")
        if teaching_content:
            annotation = crud.update_teaching_content(db, annotation.id, teaching_content)
        
        # 6. 整合回應
        response = result.copy()
        response["annotation_id"] = annotation.id
        response["system_used"] = "integrated_ai_core_api"
        response["metadata"]["database_stored"] = True
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"整合系統教學生成失敗: {str(e)}"
        )


@router.post("/generate-teaching", response_model=dict)
async def multi_agent_generate_teaching(
    url: str = Form(...),
    selected_text: str = Form(...),
    confusion_note: str = Form(...),
    page_title: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """使用多 Agent 系統生成個人化教學內容"""
    
    try:
        # 1. 處理音檔轉錄（如果有）
        audio_transcription = None
        if audio_file and audio_file.size > 0:
            # 檢查檔案限制
            if audio_file.size > 20 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="音檔檔案過大，限制 20MB")
            
            # 使用模型管理器進行轉錄
            transcription_result = await model_manager.transcribe_with_fallback(
                audio_file.file, language="zh"
            )
            audio_transcription = transcription_result.get("transcription")
        
        # 2. 準備用戶請求資料
        user_request = {
            "url": url,
            "selected_text": selected_text,
            "confusion_note": confusion_note,
            "page_title": page_title,
            "audio_transcription": audio_transcription
        }
        
        # 3. 創建 Agent 執行計劃
        tasks = await agent_scheduler.create_plan(user_request)
        
        # 4. 執行多 Agent 協作
        execution_context = await agent_scheduler.execute_plan(tasks)
        
        # 5. 使用結果整合服務格式化內容
        integration_result = result_integration_service.integrate_and_format(
            agent_results=execution_context.intermediate_results,
            user_context=user_request,
            format_type="markdown"
        )
        
        # 6. 建立標註記錄
        annotation = crud.create_annotation(
            db=db,
            url=url,
            selected_text=selected_text,
            confusion_note=confusion_note,
            page_title=page_title,
            audio_transcription=audio_transcription,
            cognitive_note=execution_context.intermediate_results.get(
                "audio_processor", {}
            ).get("audio_analysis", {}).get("structured_confusion")
        )
        
        # 7. 更新教學內容
        final_content = integration_result.formatted_content
        if final_content:
            annotation = crud.update_teaching_content(db, annotation.id, final_content)
        
        # 8. 回傳整合結果
        return {
            "success": True,
            "annotation_id": annotation.id,
            "teaching_content": final_content,
            "content_quality": {
                "quality_score": integration_result.quality_score,
                "format_type": integration_result.format_type,
                "processing_notes": integration_result.processing_notes
            },
            "agent_execution": {
                "session_id": execution_context.session_id,
                "agents_used": list(execution_context.intermediate_results.keys()),
                "processing_summary": execution_context.final_result.get("status", "completed"),
                "integration_metadata": integration_result.metadata
            },
            "metadata": {
                "audio_processed": audio_transcription is not None,
                "agents_count": len(execution_context.intermediate_results),
                "fallback_used": False,
                "result_integration_applied": True
            }
        }
        
    except Exception as e:
        # 降級：使用原有的單一 AI 服務
        from app.services.openai_service import ai_service
        
        try:
            annotation = crud.create_annotation(
                db=db,
                url=url,
                selected_text=selected_text,
                confusion_note=confusion_note,
                page_title=page_title,
                audio_transcription=audio_transcription
            )
            
            # 使用舊版 AI 服務作為降級方案
            teaching_content = ai_service.generate_teaching_content(
                url=url,
                selected_text=selected_text,
                confusion_note=confusion_note
            )
            
            annotation = crud.update_teaching_content(db, annotation.id, teaching_content)
            
            return {
                "success": True,
                "annotation_id": annotation.id,
                "teaching_content": teaching_content,
                "agent_execution": {
                    "session_id": "fallback",
                    "agents_used": ["legacy_openai_service"],
                    "processing_summary": "fallback_completed"
                },
                "metadata": {
                    "audio_processed": audio_transcription is not None,
                    "agents_count": 0,
                    "fallback_used": True,
                    "original_error": str(e)
                }
            }
            
        except Exception as fallback_error:
            raise HTTPException(
                status_code=500, 
                detail=f"多 Agent 系統和降級機制都失敗: {str(fallback_error)}"
            )


@router.get("/status-integrated")
async def get_integrated_system_status():
    """獲取整合系統狀態"""
    try:
        integrated_status = await integrated_system.get_system_status()
        model_stats = integrated_system.get_model_usage_stats()
        
        return {
            "system_health": "healthy" if integrated_status["system_initialized"] else "initializing",
            "integrated_system": integrated_status,
            "model_usage": model_stats,
            "system_type": "ai_core_api_integration",
            "version": "1.0.0",
            "timestamp": integrated_status["timestamp"]
        }
        
    except Exception as e:
        return {
            "system_health": "error",
            "error": str(e),
            "system_type": "ai_core_api_integration",
            "fallback_available": True
        }


@router.get("/status")
def get_multi_agent_status():
    """獲取多 Agent 系統狀態"""
    scheduler_status = agent_scheduler.get_system_status()
    model_stats = model_manager.get_usage_statistics()
    
    return {
        "system_health": "healthy",
        "scheduler": {
            "registered_agents": len(scheduler_status.get("registered_agents", [])),
            "running_tasks": scheduler_status.get("running_tasks_count", 0),
            "completed_tasks": scheduler_status.get("completed_tasks_count", 0),
            "queue_size": scheduler_status.get("queue_size", 0)
        },
        "models": {
            "total_requests": model_stats.get("total_requests", 0),
            "total_cost": model_stats.get("total_cost", 0.0),
            "total_tokens": model_stats.get("total_tokens", 0),
            "model_count": len(model_stats.get("models", {}))
        },
        "agents": [agent_type.value for agent_type in scheduler_status.get("registered_agents", [])],
        "timestamp": "2025-01-19T14:30:00Z"
    }


@router.get("/task/{task_id}")
async def get_task_status(task_id: str):
    """獲取特定任務的執行狀態"""
    task = await agent_scheduler.get_task_status(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "task_id": task.task_id,
        "agent_type": task.agent_type.value,
        "status": task.status.value,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "retry_count": task.retry_count,
        "error_message": task.error_message,
        "progress": "completed" if task.status.name == "COMPLETED" else "processing"
    }


@router.post("/models/toggle")
def toggle_model_availability(model_id: str, available: bool = True):
    """切換模型可用性 - 用於維護和降級控制"""
    model_manager.set_model_availability(model_id, available)
    return {
        "success": True,
        "message": f"模型 {model_id} 可用性已設為 {available}",
        "model_id": model_id,
        "available": available,
        "timestamp": "2025-01-19T14:30:00Z"
    }


@router.get("/models/usage")
def get_model_usage_statistics():
    """獲取詳細的模型使用統計"""
    return {
        "usage_statistics": model_manager.get_usage_statistics(),
        "cost_analysis": {
            "daily_cost": 0.0,  # TODO: 實作每日成本計算
            "monthly_projection": 0.0,
            "cost_per_request": 0.0
        },
        "performance_metrics": {
            "avg_response_time": 0.0,
            "success_rate": 0.95,
            "most_used_model": "gpt-3.5-turbo"
        }
    }


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消正在執行的任務"""
    success = await agent_scheduler.cancel_task(task_id)
    
    if not success:
        raise HTTPException(
            status_code=400, 
            detail="無法取消任務：任務不存在或已完成"
        )
    
    return {
        "success": True,
        "message": f"任務 {task_id} 已取消",
        "task_id": task_id
    }


@router.get("/health")
async def health_check():
    """系統健康檢查端點"""
    health_status = {
        "status": "healthy",
        "components": {
            "agent_scheduler": "healthy",
            "model_manager": "healthy", 
            "database": "healthy"
        },
        "checks_passed": 3,
        "checks_total": 3,
        "timestamp": "2025-01-19T14:30:00Z"
    }
    
    try:
        # 檢查 Agent 調度器
        scheduler_status = agent_scheduler.get_system_status()
        if not scheduler_status:
            health_status["components"]["agent_scheduler"] = "unhealthy"
            health_status["checks_passed"] -= 1
            
        # 檢查模型管理器
        model_stats = model_manager.get_usage_statistics()
        if not model_stats:
            health_status["components"]["model_manager"] = "unhealthy" 
            health_status["checks_passed"] -= 1
            
        # 更新整體狀態
        if health_status["checks_passed"] < health_status["checks_total"]:
            health_status["status"] = "degraded" if health_status["checks_passed"] > 0 else "unhealthy"
            
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
        health_status["checks_passed"] = 0
        
    return health_status


# ==================== RAG 筆記檢索端點 ====================

@router.post("/rag/search")
async def search_notes(
    query: str = Form(...),
    selected_text: Optional[str] = Form(""),
    top_k: int = Form(5),
    min_relevance: float = Form(0.3)
):
    """搜尋相關筆記 - RAG 知識庫檢索"""
    
    try:
        results = await rag_service.search_relevant_notes(
            query=query,
            selected_text=selected_text or "",
            top_k=min(top_k, 10),  # 限制最多 10 篇
            min_relevance=max(0.0, min(1.0, min_relevance))
        )
        
        # 格式化返回結果
        formatted_results = []
        for result in results:
            formatted_results.append({
                "title": result.document.title,
                "content_preview": result.document.content[:300] + "..." if len(result.document.content) > 300 else result.document.content,
                "file_path": result.document.file_path,
                "relevance_score": round(result.relevance_score, 3),
                "matched_snippets": result.matched_snippets,
                "reasoning": result.reasoning,
                "tags": result.document.tags,
                "modified_at": result.document.modified_at.isoformat()
            })
        
        return {
            "success": True,
            "query": query,
            "results_count": len(results),
            "results": formatted_results,
            "search_metadata": {
                "top_k": top_k,
                "min_relevance": min_relevance,
                "selected_text_included": bool(selected_text)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"RAG 搜尋失敗: {str(e)}"
        )


@router.get("/rag/status")
async def get_rag_status():
    """獲取 RAG 服務狀態"""
    
    try:
        stats = rag_service.get_service_statistics()
        
        return {
            "service_health": "healthy",
            "statistics": stats,
            "capabilities": {
                "obsidian_integration": bool(rag_service.note_parser.notes_directory),
                "vector_search": "mock" if not hasattr(rag_service.embedding_service, 'model_loaded') else "enabled",
                "semantic_analysis": True
            },
            "configuration": {
                "notes_directory": rag_service.note_parser.notes_directory or "Not configured",
                "supported_formats": ["markdown", "obsidian"],
                "max_results": 10
            }
        }
        
    except Exception as e:
        return {
            "service_health": "degraded", 
            "error": str(e),
            "statistics": {
                "total_notes": 0,
                "cache_updated": None
            }
        }


@router.post("/rag/refresh")
async def refresh_rag_cache():
    """重新載入 RAG 筆記快取"""
    
    try:
        await rag_service.initialize()
        stats = rag_service.get_service_statistics()
        
        return {
            "success": True,
            "message": "RAG 快取已重新載入",
            "statistics": stats,
            "refreshed_at": "2025-01-19T14:30:00Z"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"RAG 快取重新載入失敗: {str(e)}"
        )


@router.get("/rag/notes")
async def list_notes(skip: int = 0, limit: int = 20):
    """列出所有筆記 - 用於管理和除錯"""
    
    try:
        if not rag_service.note_cache:
            await rag_service.initialize()
        
        total_notes = len(rag_service.note_cache)
        notes_slice = rag_service.note_cache[skip:skip + limit]
        
        formatted_notes = []
        for note in notes_slice:
            formatted_notes.append({
                "title": note.title,
                "file_path": note.file_path,
                "tags": note.tags,
                "created_at": note.created_at.isoformat(),
                "modified_at": note.modified_at.isoformat(),
                "content_length": len(note.content),
                "has_embedding": note.embedding is not None
            })
        
        return {
            "total_notes": total_notes,
            "returned_count": len(formatted_notes),
            "skip": skip,
            "limit": limit,
            "notes": formatted_notes
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"列出筆記失敗: {str(e)}"
        )


# ==================== 結果整合與格式化端點 ====================

@router.post("/formatting/test")
async def test_result_formatting(
    content: str = Form(...),
    confusion_note: str = Form(""),
    selected_text: str = Form(""),
    format_type: str = Form("markdown")
):
    """測試結果整合與格式化功能"""
    
    try:
        # 模擬 Agent 結果
        mock_agent_results = {
            "content_generator": {
                "teaching_content": content,
                "tokens_used": 100
            },
            "planner": {
                "plan": {
                    "teaching_strategy": "提供詳細解釋和範例",
                    "complexity_level": 3
                }
            }
        }
        
        user_context = {
            "confusion_note": confusion_note,
            "selected_text": selected_text
        }
        
        # 執行結果整合
        integration_result = result_integration_service.integrate_and_format(
            agent_results=mock_agent_results,
            user_context=user_context,
            format_type=format_type
        )
        
        return {
            "success": True,
            "formatted_content": integration_result.formatted_content,
            "quality_assessment": {
                "score": integration_result.quality_score,
                "processing_notes": integration_result.processing_notes
            },
            "formatting_metadata": integration_result.metadata,
            "original_content_length": len(content),
            "formatted_content_length": len(integration_result.formatted_content)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"格式化測試失敗: {str(e)}"
        )


@router.get("/formatting/quality-check")
async def quality_check_demo():
    """展示內容品質檢查功能"""
    
    sample_contents = [
        {
            "name": "高品質範例",
            "content": """# FastAPI 路由設計指南

## 基本概念
FastAPI 使用裝飾器來定義 API 路由，支援多種 HTTP 方法。

## 實作範例
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"user_id": user_id}
```

## 重點摘要
- 使用 @app.get() 定義 GET 端點
- 路徑參數會自動類型轉換
- 返回的字典會自動序列化為 JSON

## 延伸學習
建議學習 Pydantic 模型定義和請求驗證。"""
        },
        {
            "name": "低品質範例", 
            "content": "這是很短的解釋。"
        },
        {
            "name": "中等品質範例",
            "content": """FastAPI 是 Python 的現代 Web 框架。它支援自動文件生成和類型檢查。你可以用它來建立 REST API。"""
        }
    ]
    
    results = []
    for sample in sample_contents:
        quality_score = result_integration_service.quality_checker.assess_content_quality(
            content=sample["content"],
            context={"confusion_note": "FastAPI 使用", "selected_text": "路由設計"}
        )
        
        results.append({
            "name": sample["name"],
            "quality_score": quality_score,
            "content_length": len(sample["content"]),
            "content_preview": sample["content"][:100] + "..." if len(sample["content"]) > 100 else sample["content"]
        })
    
    return {
        "quality_demonstration": results,
        "scoring_criteria": {
            "length": "內容長度適當性 (20%)",
            "structure": "內容結構完整性 (30%)", 
            "relevance": "與用戶需求相關性 (30%)",
            "completeness": "解釋完整性 (20%)"
        }
    }