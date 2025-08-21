import React, { useState } from 'react';

interface ReaderBarProps {
  onOpenReader: () => void;
  onClose: () => void;
  isExtracting?: boolean;
}

export function ReaderBar({ onOpenReader, onClose, isExtracting = false }: ReaderBarProps) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      height: '100%',
      padding: '0 16px',
      fontFamily: 'system-ui, -apple-system, sans-serif',
    }}>
      {/* 左側：Logo 和 Open in Reader 按鈕 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          color: '#fff',
          fontSize: '14px',
          fontWeight: '500'
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
          NodePilot
        </div>
        
        <button
          onClick={!isExtracting ? onOpenReader : undefined}
          disabled={isExtracting}
          style={{
            background: isExtracting ? '#4a5568' : '#3b82f6',
            color: 'white',
            border: 'none',
            padding: '6px 12px',
            borderRadius: '4px',
            cursor: isExtracting ? 'not-allowed' : 'pointer',
            fontSize: '13px',
            fontWeight: '500',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            transition: 'background-color 0.2s',
          }}
          onMouseEnter={(e) => {
            if (!isExtracting) {
              (e.target as HTMLButtonElement).style.backgroundColor = '#2563eb';
            }
          }}
          onMouseLeave={(e) => {
            if (!isExtracting) {
              (e.target as HTMLButtonElement).style.backgroundColor = '#3b82f6';
            }
          }}
        >
          {isExtracting ? (
            <>
              <div style={{
                width: '12px',
                height: '12px',
                border: '2px solid transparent',
                borderTop: '2px solid currentColor',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
              }}></div>
              擷取中...
            </>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
              </svg>
              Open in Reader
            </>
          )}
        </button>
      </div>

      {/* 右側：關閉按鈕 */}
      <button
        onClick={onClose}
        style={{
          background: 'transparent',
          color: '#9ca3af',
          border: 'none',
          padding: '6px',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '18px',
          lineHeight: '1',
          transition: 'color 0.2s',
        }}
        onMouseEnter={(e) => {
          (e.target as HTMLButtonElement).style.color = '#fff';
        }}
        onMouseLeave={(e) => {
          (e.target as HTMLButtonElement).style.color = '#9ca3af';
        }}
        title="關閉"
      >
        ×
      </button>

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}