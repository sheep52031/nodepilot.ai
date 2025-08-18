import React, { createContext, useContext, useReducer, useCallback } from 'react';
import { NodePilotState, NodePilotAction, AnnotationData, TeachingRequest } from './types';

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
  updateAnnotationStatus: (annotationId: number, status: string) => Promise<void>;
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

  const updateAnnotationStatus = useCallback(async (annotationId: number, status: string) => {
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