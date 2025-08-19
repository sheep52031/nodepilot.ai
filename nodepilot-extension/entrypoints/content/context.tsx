import React, { createContext, useContext, useReducer, useCallback } from 'react';
import { NodePilotState, NodePilotAction, AnnotationData, TeachingRequest, CreateAnnotationRequest, AnnotationResponse } from './types';

const initialState: NodePilotState = {
  currentAnnotation: null,
  isLoading: false,
  error: null,
  showUI: false,
};

function nodePilotReducer(state: NodePilotState, action: NodePilotAction): NodePilotState {
  switch (action.type) {
    case 'SET_ANNOTATION':
      return { ...state, currentAnnotation: action.payload };
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'SHOW_UI':
      return { ...state, showUI: action.payload };
    case 'CLEAR_STATE':
      return initialState;
    default:
      return state;
  }
}

interface NodePilotContextType {
  state: NodePilotState;
  generateTeaching: (request: TeachingRequest) => Promise<void>;
  createAnnotation: (request: CreateAnnotationRequest) => Promise<void>;
  updateAnnotationStatus: (annotationId: string, status: string) => Promise<void>;
  showAnnotationUI: () => void;
  hideAnnotationUI: () => void;
  clearError: () => void;
}

const NodePilotContext = createContext<NodePilotContextType | undefined>(undefined);

export function NodePilotProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(nodePilotReducer, initialState);

  const generateTeaching = useCallback(async (request: TeachingRequest) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    dispatch({ type: 'SET_ERROR', payload: null });

    try {
      let response;
      
      if (request.audio_file) {
        // 使用 FormData 上傳音檔
        const formData = new FormData();
        formData.append('url', request.url);
        formData.append('selected_text', request.selected_text);
        formData.append('confusion_note', request.confusion_note);
        formData.append('audio_file', request.audio_file, 'recording.webm');
        
        response = await fetch('http://127.0.0.1:8000/generate-teaching', {
          method: 'POST',
          body: formData,
        });
      } else {
        // 普通 JSON 請求
        response = await fetch('http://127.0.0.1:8000/generate-teaching', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            url: request.url,
            selected_text: request.selected_text,
            confusion_note: request.confusion_note,
          }),
        });
      }

      if (!response.ok) {
        throw new Error('生成教學失敗');
      }

      const result = await response.json();
      
      const annotation: AnnotationData = {
        id: result.id,
        url: result.url,
        selected_text: result.selected_text,
        confusion_note: result.confusion_note,
        teaching_content: result.teaching_content,
        status: result.status,
        created_at: result.created_at,
      };

      dispatch({ type: 'SET_ANNOTATION', payload: annotation });
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : '未知錯誤' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, []);

  const createAnnotation = useCallback(async (request: CreateAnnotationRequest) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    dispatch({ type: 'SET_ERROR', payload: null });

    try {
      // 總是使用 FormData 調用整合音頻標註端點
      const formData = new FormData();
      formData.append('url', request.url);
      formData.append('selected_text', request.selected_text);
      formData.append('confusion_note', request.confusion_note);
      if (request.page_title) {
        formData.append('page_title', request.page_title);
      }
      if (request.audio_file) {
        formData.append('audio_file', request.audio_file, 'recording.webm');
      }
      
      const response = await fetch('http://127.0.0.1:8000/api/v1/multi-agent/generate-teaching-integrated', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('標註困惑失敗');
      }

      const result = await response.json();
      
      // 處理後端整合音頻標註API的回應格式
      const annotation: AnnotationData = {
        id: result.annotation_id || 'temp_' + Date.now(),
        url: request.url,
        selected_text: request.selected_text,
        confusion_note: request.confusion_note,
        audio_transcription: result.metadata?.audio_processing_result?.transcription?.text || null,
        cognitive_note: result.metadata?.audio_processing_result?.semantic_analysis?.structured_confusion || null,
        teaching_content: result.teaching_content,
        status: 'unknown', // 預設狀態
        created_at: result.metadata?.timestamp || new Date().toISOString(),
      };

      dispatch({ type: 'SET_ANNOTATION', payload: annotation });
      
      // 標註成功後的處理：
      // 1. 添加螢光筆標記
      addHighlightToSelectedText(request.selected_text, annotation.id);
      
      // 2. 通知側邊欄更新
      notifySidePanelAnnotation(annotation);
      
      // 3. 顯示成功提示
      showAnnotationSuccessMessage(annotation);
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : '未知錯誤' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  }, []);

  const updateAnnotationStatus = useCallback(async (annotationId: string, status: string) => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/annotations/${annotationId}/status`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status }),
      });

      if (!response.ok) {
        throw new Error('更新狀態失敗');
      }

      const result = await response.json();
      
      if (state.currentAnnotation?.id === annotationId) {
        dispatch({ 
          type: 'SET_ANNOTATION', 
          payload: { ...state.currentAnnotation, status: result.status }
        });
      }
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: error instanceof Error ? error.message : '更新失敗' });
    }
  }, [state.currentAnnotation]);

  const showAnnotationUI = useCallback(() => {
    dispatch({ type: 'SHOW_UI', payload: true });
  }, []);

  const hideAnnotationUI = useCallback(() => {
    dispatch({ type: 'SHOW_UI', payload: false });
    dispatch({ type: 'CLEAR_STATE' });
  }, []);

  const clearError = useCallback(() => {
    dispatch({ type: 'SET_ERROR', payload: null });
  }, []);

  return (
    <NodePilotContext.Provider
      value={{
        state,
        generateTeaching,
        createAnnotation,
        updateAnnotationStatus,
        showAnnotationUI,
        hideAnnotationUI,
        clearError,
      }}
    >
      {children}
    </NodePilotContext.Provider>
  );
}

export function useNodePilot() {
  const context = useContext(NodePilotContext);
  if (context === undefined) {
    throw new Error('useNodePilot must be used within a NodePilotProvider');
  }
  return context;
}

// 輔助函數：添加螢光筆標記到選取文字
function addHighlightToSelectedText(selectedText: string, annotationId: string) {
  try {
    // 找到頁面中匹配的文字並添加螢光筆標記
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_TEXT,
      null,
      false
    );

    let textNode;
    while (textNode = walker.nextNode()) {
      if (textNode.textContent?.includes(selectedText)) {
        const parent = textNode.parentNode as HTMLElement;
        if (parent && !parent.classList.contains('nodepilot-highlight')) {
          // 創建螢光筆標記
          const highlightSpan = document.createElement('span');
          highlightSpan.classList.add('nodepilot-highlight');
          highlightSpan.setAttribute('data-annotation-id', annotationId);
          highlightSpan.style.cssText = `
            background-color: #fef3c7;
            border-radius: 2px;
            padding: 1px 2px;
            cursor: pointer;
            transition: background-color 0.2s;
          `;
          
          // 滑鼠懸停效果
          highlightSpan.addEventListener('mouseenter', () => {
            highlightSpan.style.backgroundColor = '#fbbf24';
          });
          highlightSpan.addEventListener('mouseleave', () => {
            highlightSpan.style.backgroundColor = '#fef3c7';
          });
          
          // 點擊顯示教學內容
          highlightSpan.addEventListener('click', () => {
            console.log('Highlight clicked:', annotationId);
            // 這裡可以觸發顯示該標註的教學內容
          });

          // 將文字節點包裝在螢光筆中
          const textContent = textNode.textContent || '';
          const highlightedText = textContent.replace(
            selectedText,
            `<span class="nodepilot-highlight-inner">${selectedText}</span>`
          );
          highlightSpan.innerHTML = highlightedText;
          
          parent.replaceChild(highlightSpan, textNode);
          break;
        }
      }
    }
  } catch (error) {
    console.warn('Failed to add highlight:', error);
  }
}

// 輔助函數：通知側邊欄標註更新
function notifySidePanelAnnotation(annotation: AnnotationData) {
  try {
    // 使用 Chrome Messaging API 通知側邊欄
    if (typeof chrome !== 'undefined' && chrome.runtime) {
      chrome.runtime.sendMessage({
        type: 'ANNOTATION_CREATED',
        payload: annotation
      });
    }
  } catch (error) {
    console.warn('Failed to notify side panel:', error);
  }
}

// 輔助函數：顯示標註成功提示
function showAnnotationSuccessMessage(annotation: AnnotationData) {
  // 創建成功提示
  const successMessage = document.createElement('div');
  successMessage.className = 'nodepilot-success-toast';
  successMessage.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: #10b981;
    color: white;
    padding: 12px 16px;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 99999;
    font-family: system-ui, -apple-system, sans-serif;
    font-size: 14px;
    max-width: 300px;
    opacity: 0;
    transform: translateX(100px);
    transition: all 0.3s ease;
  `;

  const hasAudio = annotation.audio_transcription ? '🎵 ' : '';
  successMessage.innerHTML = `
    <div style="display: flex; align-items: center; gap: 8px;">
      <span>✅</span>
      <div>
        <strong>${hasAudio}標註已記錄</strong>
        <div style="font-size: 12px; opacity: 0.9; margin-top: 2px;">
          AI已處理您的困惑，可在側邊欄查看
        </div>
      </div>
    </div>
  `;

  document.body.appendChild(successMessage);

  // 動畫顯示
  requestAnimationFrame(() => {
    successMessage.style.opacity = '1';
    successMessage.style.transform = 'translateX(0)';
  });

  // 3秒後自動隱藏
  setTimeout(() => {
    successMessage.style.opacity = '0';
    successMessage.style.transform = 'translateX(100px)';
    setTimeout(() => {
      if (successMessage.parentNode) {
        successMessage.parentNode.removeChild(successMessage);
      }
    }, 300);
  }, 3000);
}