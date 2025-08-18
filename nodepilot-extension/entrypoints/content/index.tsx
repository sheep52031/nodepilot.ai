import React, { useState, useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import { NodePilotProvider, useNodePilot } from './context';
import { AnnotationUI } from './components/AnnotationUI';
import { TeachingResult } from './components/TeachingResult';
import './style.css';

function ContentApp() {
  const [selectedText, setSelectedText] = useState('');
  const [selectionPosition, setSelectionPosition] = useState<{ x: number; y: number } | null>(null);
  const [showAnnotationUI, setShowAnnotationUI] = useState(false);
  const [showTeachingResult, setShowTeachingResult] = useState(false);
  
  const { state } = useNodePilot();

  useEffect(() => {
    function handleTextSelection() {
      const selection = window.getSelection();
      if (!selection || selection.toString().trim().length === 0) {
        setShowAnnotationUI(false);
        return;
      }
      
      const text = selection.toString().trim();
      if (text.length > 10) {
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        
        setSelectedText(text);
        setSelectionPosition({
          x: rect.left + window.scrollX,
          y: rect.bottom + window.scrollY,
        });
        setShowAnnotationUI(true);
      }
    }

    document.addEventListener('mouseup', handleTextSelection);
    document.addEventListener('keyup', handleTextSelection);

    return () => {
      document.removeEventListener('mouseup', handleTextSelection);
      document.removeEventListener('keyup', handleTextSelection);
    };
  }, []);

  useEffect(() => {
    if (state.currentAnnotation && state.currentAnnotation.teaching_content) {
      setShowTeachingResult(true);
      setShowAnnotationUI(false);
    }
  }, [state.currentAnnotation]);

  const handleCloseAnnotationUI = () => {
    setShowAnnotationUI(false);
    setSelectedText('');
    setSelectionPosition(null);
  };

  const handleCloseTeachingResult = () => {
    setShowTeachingResult(false);
  };

  return (
    <div style={{ 
      position: 'fixed', 
      top: 0, 
      left: 0, 
      width: '100%', 
      height: '100%', 
      pointerEvents: 'none', 
      zIndex: 9999 
    }}>
      {showAnnotationUI && selectionPosition && (
        <AnnotationUI
          selectedText={selectedText}
          position={selectionPosition}
          onClose={handleCloseAnnotationUI}
        />
      )}
      
      {showTeachingResult && state.currentAnnotation && (
        <TeachingResult
          annotation={state.currentAnnotation}
          onClose={handleCloseTeachingResult}
        />
      )}
    </div>
  );
}

export default defineContentScript({
  matches: ['https://manus.im/blog/*'],
  cssInjectionMode: 'ui',
  
  async main(ctx) {
    console.log('NodePilot React Content Script loaded');
    
    const ui = await createShadowRootUi(ctx, {
      name: 'nodepilot-ui',
      position: 'inline',
      anchor: 'body',
      onMount: (container) => {
        const app = document.createElement('div');
        app.id = 'nodepilot-app';
        container.append(app);

        const root = ReactDOM.createRoot(app);
        root.render(
          <NodePilotProvider>
            <ContentApp />
          </NodePilotProvider>
        );
        return root;
      },
      onRemove: (root) => {
        root?.unmount();
      },
    });

    ui.mount();
  },
});