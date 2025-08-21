import React, { useState } from 'react';

interface ReaderButtonProps {
  onOpenReader: () => void;
  position: { x: number; y: number };
  isExtracting?: boolean;
}

export function ReaderButton({ onOpenReader, position, isExtracting = false }: ReaderButtonProps) {
  return (
    <div
      className="nodepilot-interactive"
      style={{
        position: 'fixed',
        top: position.y,
        left: position.x,
        background: '#1f2937',
        color: 'white',
        border: 'none',
        borderRadius: '8px',
        padding: '8px 12px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.25)',
        zIndex: 10000,
        fontFamily: 'system-ui, -apple-system, sans-serif',
        fontSize: '12px',
        cursor: isExtracting ? 'not-allowed' : 'pointer',
        opacity: isExtracting ? 0.7 : 1,
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        pointerEvents: 'auto',
      }}
      onClick={!isExtracting ? onOpenReader : undefined}
    >
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
        <polyline points="14,2 14,8 20,8"></polyline>
        <line x1="16" y1="13" x2="8" y2="13"></line>
        <line x1="16" y1="17" x2="8" y2="17"></line>
        <polyline points="10,9 9,9 8,9"></polyline>
      </svg>
      {isExtracting ? '擷取中...' : 'Open in Reader'}
    </div>
  );
}