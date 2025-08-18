import React from 'react';
import { useNodePilot } from '../context';
import { AnnotationData } from '../types';

interface TeachingResultProps {
  annotation: AnnotationData;
  onClose: () => void;
}

export function TeachingResult({ annotation, onClose }: TeachingResultProps) {
  const { updateAnnotationStatus } = useNodePilot();

  const handleStatusUpdate = async (status: string) => {
    if (annotation.id) {
      await updateAnnotationStatus(annotation.id, status);
    }
    onClose();
  };

  return (
    <div
      className="nodepilot-interactive"
      style={{
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        background: 'white',
        border: '1px solid #e2e8f0',
        borderRadius: '12px',
        padding: '20px',
        boxShadow: '0 8px 24px rgba(0,0,0,0.2)',
        zIndex: 10001,
        maxWidth: '500px',
        maxHeight: '400px',
        overflowY: 'auto',
        fontFamily: 'system-ui, -apple-system, sans-serif',
        pointerEvents: 'auto',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '600' }}>AI 教學內容</h3>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            fontSize: '18px',
            cursor: 'pointer',
            color: '#6b7280',
          }}
        >
          ×
        </button>
      </div>
      
      <div
        style={{
          whiteSpace: 'pre-wrap',
          lineHeight: '1.6',
          fontSize: '14px',
          color: '#374151',
          marginBottom: '16px',
        }}
      >
        {annotation.teaching_content}
      </div>
      
      <div style={{ display: 'flex', gap: '8px' }}>
        <button
          onClick={() => handleStatusUpdate('understood')}
          style={{
            background: '#10b981',
            color: 'white',
            border: 'none',
            padding: '8px 16px',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '13px',
          }}
        >
          ✅ 已理解
        </button>
        
        <button
          onClick={() => handleStatusUpdate('learning')}
          style={{
            background: '#f59e0b',
            color: 'white',
            border: 'none',
            padding: '8px 16px',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '13px',
          }}
        >
          📚 學習中
        </button>
      </div>
    </div>
  );
}