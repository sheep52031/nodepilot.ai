"""
多 Agent 系統整合測試
====================

驗證完整的 Plan-and-Execute 流程。
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from ai_core.scheduler import AgentScheduler, AgentType
from ai_core.model_pool import ModelPool, ModelConfig, ModelType
from agents.planning_agent import PlanningAgent
from agents.context_analysis_agent import ContextAnalysisAgent
from agents.audio_semantic_agent import AudioSemanticAgent
from agents.note_retrieval_agent import NoteRetrievalAgent
from agents.teaching_generation_agent import TeachingGenerationAgent


async def setup_test_system() -> AgentScheduler:
    """設定測試系統"""
    # 建立模型池
    model_pool = ModelPool()
    
    # 註冊測試模型 (模擬配置)
    gpt4o_config = ModelConfig(
        model_type=ModelType.GPT_4O,
        provider="openai",
        api_endpoint="https://api.openai.com/v1/chat/completions",
        api_key="test-key",
        max_tokens=4096,
        cost_per_1k_tokens=0.03
    )
    model_pool.register_model(gpt4o_config)
    
    claude_config = ModelConfig(
        model_type=ModelType.CLAUDE_3_5_SONNET,
        provider="anthropic",
        api_endpoint="https://api.anthropic.com/v1/messages",
        api_key="test-key",
        max_tokens=4096,
        cost_per_1k_tokens=0.025
    )
    model_pool.register_model(claude_config)
    
    # 建立調度器
    scheduler = AgentScheduler(model_pool)
    
    # 註冊 Agents
    scheduler.register_agent(AgentType.PLANNING, PlanningAgent(model_pool))
    scheduler.register_agent(AgentType.CONTEXT_ANALYSIS, ContextAnalysisAgent(model_pool))
    scheduler.register_agent(AgentType.AUDIO_SEMANTIC, AudioSemanticAgent(model_pool))
    scheduler.register_agent(AgentType.NOTE_RETRIEVAL, NoteRetrievalAgent(model_pool))
    scheduler.register_agent(AgentType.TEACHING_GENERATION, TeachingGenerationAgent(model_pool))
    
    return scheduler


async def test_basic_text_question():
    """測試基礎文字問題"""
    print("\n=== 測試案例 1: 基礎文字問題 ===")
    
    scheduler = await setup_test_system()
    
    # 模擬用戶請求
    result = await scheduler.execute_user_request(
        user_confusion="我不太理解 React Hooks 的 useEffect 是如何運作的",
        selected_text="useEffect(() => { fetchData(); }, [dependency]);",
        page_context={
            "url": "https://manus.im/blog/react-hooks-guide",
            "title": "React Hooks 完全指南",
            "content": "React Hooks 是 React 16.8 引入的新特性..."
        }
    )
    
    print(f"執行結果: {result['success']}")
    if result['success']:
        print(f"教學內容長度: {len(result.get('teaching_content', ''))}")
        print(f"使用的 Agents: {result.get('agent_contributions', {}).keys()}")
        print(f"信心分數: {result.get('quality', {}).get('confidence_score', 0)}")
    else:
        print(f"錯誤: {result.get('error', 'Unknown error')}")


async def test_audio_confusion():
    """測試音訊困惑分析"""
    print("\n=== 測試案例 2: 音訊困惑分析 ===")
    
    scheduler = await setup_test_system()
    
    # 模擬音訊轉錄
    audio_transcription = "我想要了解這個 API 的運作方式，但是我對於 async 和 await 這兩個關鍵字還是有點困惑，不知道什麼時候要用"
    
    result = await scheduler.execute_user_request(
        user_confusion="API 異步處理的問題",
        selected_text="async function fetchUserData() { const response = await fetch('/api/user'); return response.json(); }",
        page_context={
            "url": "https://manus.im/blog/javascript-async-await",
            "title": "JavaScript Async/Await 詳解",
            "content": "JavaScript 的異步程式設計..."
        },
        audio_transcription=audio_transcription
    )
    
    print(f"執行結果: {result['success']}")
    if result['success']:
        print(f"教學內容長度: {len(result.get('teaching_content', ''))}")
        print(f"使用的 Agents: {result.get('agent_contributions', {}).keys()}")
        print(f"處理時間: {result.get('quality', {}).get('processing_time', 0):.2f}s")
    else:
        print(f"錯誤: {result.get('error', 'Unknown error')}")


async def test_complex_analysis():
    """測試複雜分析場景"""
    print("\n=== 測試案例 3: 複雜分析場景 ===")
    
    scheduler = await setup_test_system()
    
    long_selected_text = """
    在現代的 web 應用程式開發中，狀態管理是一個核心議題。
    React 提供了多種狀態管理的方式，從最基本的 useState，
    到更複雜的 useReducer，以及全域狀態管理的解決方案如 Redux。
    每種方法都有其適用的場景和權衡考量。
    """
    
    result = await scheduler.execute_user_request(
        user_confusion="我需要為大型專案選擇合適的狀態管理方案，但不知道各種選項的優缺點",
        selected_text=long_selected_text,
        page_context={
            "url": "https://manus.im/blog/react-state-management-comparison",
            "title": "React 狀態管理方案比較",
            "content": f"完整文章內容包含多個段落... {long_selected_text} ..."
        }
    )
    
    print(f"執行結果: {result['success']}")
    if result['success']:
        print(f"教學內容長度: {len(result.get('teaching_content', ''))}")
        print(f"Artifacts 數量: {len(result.get('metadata', {}).get('artifacts', []))}")
        print(f"資料來源: {result.get('sources', [])}")
    else:
        print(f"錯誤: {result.get('error', 'Unknown error')}")


async def test_model_fallback():
    """測試模型 fallback 機制"""
    print("\n=== 測試案例 4: 模型 Fallback 機制 ===")
    
    scheduler = await setup_test_system()
    
    # 模擬主要模型失效
    scheduler.model_pool._circuit_breaker[ModelType.GPT_4O] = True
    
    result = await scheduler.execute_user_request(
        user_confusion="測試 fallback 機制",
        selected_text="test content",
        page_context={"url": "test", "title": "Test"}
    )
    
    print(f"執行結果: {result['success']}")
    if result['success']:
        print("Fallback 機制運作正常")
    else:
        print(f"Fallback 失敗: {result.get('error', 'Unknown error')}")


async def main():
    """主測試函數"""
    print("NodePilot 多 Agent 系統整合測試")
    print("=" * 50)
    
    # 設定日誌
    logging.basicConfig(level=logging.INFO)
    
    try:
        # 執行各種測試案例
        await test_basic_text_question()
        await test_audio_confusion()
        await test_complex_analysis()
        await test_model_fallback()
        
        print("\n" + "=" * 50)
        print("所有測試完成！")
        
    except Exception as e:
        print(f"測試執行失敗: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())