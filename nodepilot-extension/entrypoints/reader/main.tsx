import React from 'react';
import { createRoot } from 'react-dom/client';
import { ReaderApp } from './ReaderApp';
import '../content/style.css';

console.log('NodePilot Reader page loaded');

// 等待 DOM 載入完成
document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('reader-root');
  if (container) {
    const root = createRoot(container);
    root.render(<ReaderApp />);
  }
});

// 監聽來自 background script 的內容加載消息
browser.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  console.log('Reader received message:', message);
  
  if (message.type === 'LOAD_CONTENT') {
    // 觸發內容載入事件
    window.dispatchEvent(new CustomEvent('loadReaderContent', {
      detail: message.data
    }));
    sendResponse({ success: true });
  }
  
  return true;
});