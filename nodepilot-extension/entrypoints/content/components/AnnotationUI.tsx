import React, { useState } from 'react';
import { useNodePilot } from '../context';

interface AnnotationUIProps {
  selectedText: string;
  position: { x: number; y: number };
  onClose: () => void;
}

export function AnnotationUI({ selectedText, position, onClose }: AnnotationUIProps) {
  const [confusionNote, setConfusionNote] = useState('');
  const { state, generateTeaching } = useNodePilot();

  const handleSubmit = async () => {
    if (!confusionNote.trim()) {
      alert('請描述你的困惑');
      return;
    }

    await generateTeaching({
      url: window.location.href,
      selected_text: selectedText,
      confusion_note: confusionNote,
    });

    onClose();
  };

  return (
    <div
      className="nodepilot-interactive"
      style={{
        position: 'fixed',
        top: position.y + 10,
        left: position.x,
        background: 'white',
        border: '1px solid #e2e8f0',
        borderRadius: '8px',
        padding: '12px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
        zIndex: 10000,
        maxWidth: '300px',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        pointerEvents: 'auto',
      }}
    >
      <div style={{ marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}>
        選取文字: "{selectedText.substring(0, 50)}{selectedText.length > 50 ? '...' : ''}"
      </div>
      
      <textarea
        value={confusionNote}
        onChange={(e) => setConfusionNote(e.target.value)}
        placeholder="描述你的困惑..."
        style={{
          width: '100%',
          height: '60px',
          border: '1px solid #e2e8f0',
          borderRadius: '4px',
          padding: '8px',
          resize: 'none',
          fontSize: '13px',
        }}
      />
      
      <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
        <button
          onClick={handleSubmit}
          disabled={state.isLoading}
          style={{
            background: state.isLoading ? '#9ca3af' : '#3b82f6',
            color: 'white',
            border: 'none',
            padding: '6px 12px',
            borderRadius: '4px',
            cursor: state.isLoading ? 'not-allowed' : 'pointer',
            fontSize: '12px',
          }}
        >
          {state.isLoading ? '生成中...' : '生成教學'}
        </button>
        
        <button
          onClick={onClose}
          style={{
            background: '#f3f4f6',
            color: '#374151',
            border: 'none',
            padding: '6px 12px',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '12px',
          }}
        >
          取消
        </button>
      </div>
      
      {state.error && (
        <div style={{ marginTop: '8px', color: '#ef4444', fontSize: '12px' }}>
          {state.error}
        </div>
      )}
    </div>
  );
}