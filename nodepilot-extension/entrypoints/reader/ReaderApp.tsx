import React, { useState, useEffect, useRef } from 'react';
import { ExtractedContent } from '../content/utils/contentExtractor';
import { NodePilotProvider } from '../content/context';
import { AnnotationUI } from '../content/components/AnnotationUI';

export function ReaderApp() {
  const [content, setContent] = useState<ExtractedContent | null>(null);
  const [darkMode, setDarkMode] = useState(true);
  const [fontSize, setFontSize] = useState(16);
  const [isLoading, setIsLoading] = useState(true);
  
  // 標註功能相關狀態
  const [selectedText, setSelectedText] = useState('');
  const [selectionPosition, setSelectionPosition] = useState({ x: 0, y: 0 });
  const [showAnnotationUI, setShowAnnotationUI] = useState(false);
  const contentRef = useRef<HTMLElement>(null);

  // 文字選取處理
  const handleTextSelection = () => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return;

    const selectedText = selection.toString().trim();
    if (selectedText.length < 3) {
      setShowAnnotationUI(false);
      return;
    }

    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    
    setSelectedText(selectedText);
    setSelectionPosition({
      x: rect.left + rect.width / 2,
      y: rect.top - 10,
    });
    setShowAnnotationUI(true);
  };

  const handleCloseAnnotation = () => {
    setShowAnnotationUI(false);
    setSelectedText('');
    window.getSelection()?.removeAllRanges();
  };

  useEffect(() => {
    // 監聽內容載入事件
    const handleLoadContent = (event: CustomEvent) => {
      console.log('Loading content in Reader:', event.detail);
      setContent(event.detail);
      setIsLoading(false);
    };

    window.addEventListener('loadReaderContent', handleLoadContent as EventListener);
    
    // 文字選取事件監聽
    document.addEventListener('mouseup', handleTextSelection);
    document.addEventListener('keyup', handleTextSelection);

    // 監聽快捷鍵
    const handleKeydown = (event: KeyboardEvent) => {
      // ESC 關閉 Reader
      if (event.key === 'Escape') {
        window.close();
      }
      
      // Ctrl+D 切換暗黑模式
      if ((event.ctrlKey || event.metaKey) && event.key === 'd') {
        event.preventDefault();
        setDarkMode(prev => !prev);
      }
      
      // 調整字體大小
      if ((event.ctrlKey || event.metaKey) && event.key === '=') {
        event.preventDefault();
        setFontSize(prev => Math.min(24, prev + 2));
      }
      
      if ((event.ctrlKey || event.metaKey) && event.key === '-') {
        event.preventDefault();
        setFontSize(prev => Math.max(12, prev - 2));
      }
    };

    document.addEventListener('keydown', handleKeydown);

    return () => {
      window.removeEventListener('loadReaderContent', handleLoadContent as EventListener);
      document.removeEventListener('keydown', handleKeydown);
      document.removeEventListener('mouseup', handleTextSelection);
      document.removeEventListener('keyup', handleTextSelection);
    };
  }, []);

  // 應用主題
  useEffect(() => {
    document.documentElement.className = darkMode ? 'dark' : '';
    document.body.className = darkMode 
      ? 'bg-gray-900 text-gray-100 min-h-screen' 
      : 'bg-white text-gray-900 min-h-screen';
  }, [darkMode]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <div className="text-gray-600 dark:text-gray-400">載入文章中...</div>
        </div>
      </div>
    );
  }

  if (!content) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-500 mb-2">❌</div>
          <div className="text-gray-600 dark:text-gray-400">無法載入文章內容</div>
        </div>
      </div>
    );
  }

  return (
    <NodePilotProvider>
      <div className={`min-h-screen ${darkMode ? 'dark' : ''}`}>
      <div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 transition-colors">
        {/* Header 工具列 */}
        <header className="sticky top-0 z-50 bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm border-b border-gray-200 dark:border-gray-700">
          <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => window.close()}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                title="關閉 (ESC)"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
              
              <div className="text-sm text-gray-600 dark:text-gray-400">
                {content.metadata.readTime} 分鐘閱讀 • {content.metadata.wordCount} 字
              </div>
            </div>

            <div className="flex items-center space-x-3">
              {/* 字體大小控制 */}
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => setFontSize(prev => Math.max(12, prev - 2))}
                  className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                  title="減小字體 (Ctrl+-)"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                  </svg>
                </button>
                
                <span className="text-xs text-gray-500 min-w-[2rem] text-center">{fontSize}px</span>
                
                <button
                  onClick={() => setFontSize(prev => Math.min(24, prev + 2))}
                  className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800"
                  title="增大字體 (Ctrl+=)"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </button>
              </div>

              {/* 主題切換 */}
              <button
                onClick={() => setDarkMode(prev => !prev)}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                title="切換主題 (Ctrl+D)"
              >
                {darkMode ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                  </svg>
                )}
              </button>

              {/* 返回原文 */}
              <a
                href={content.originalUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                title="返回原文"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>
          </div>
        </header>

        {/* 主要內容區 */}
        <main className="max-w-4xl mx-auto px-6 py-8">
          {/* 文章標題 */}
          <div className="mb-8">
            <h1 className="text-3xl md:text-4xl font-bold mb-4 leading-tight">
              {content.title}
            </h1>
            
            <div className="flex flex-wrap gap-4 text-sm text-gray-600 dark:text-gray-400">
              {content.metadata.author && (
                <div className="flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  {content.metadata.author}
                </div>
              )}
              
              {content.metadata.publishDate && (
                <div className="flex items-center gap-1">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  {new Date(content.metadata.publishDate).toLocaleDateString('zh-TW')}
                </div>
              )}
              
              <div className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                約 {content.metadata.readTime} 分鐘閱讀
              </div>
            </div>
          </div>

          {/* 文章內容 */}
          <article 
            ref={contentRef}
            className="prose prose-gray dark:prose-invert max-w-none select-text"
            style={{ fontSize: `${fontSize}px` }}
            dangerouslySetInnerHTML={{ __html: content.content }}
          />
        </main>

        {/* 快捷鍵提示 */}
        <div className="fixed bottom-4 left-4 bg-black/50 text-white text-xs px-3 py-2 rounded-lg">
          <div>ESC: 關閉</div>
          <div>Ctrl+D: 切換主題</div>
          <div>Ctrl+/-: 調整字體</div>
        </div>
        
        {/* 標註 UI */}
        {showAnnotationUI && (
          <AnnotationUI
            selectedText={selectedText}
            position={selectionPosition}
            onClose={handleCloseAnnotation}
          />
        )}
      </div>
      </div>
    </NodePilotProvider>
  );
}