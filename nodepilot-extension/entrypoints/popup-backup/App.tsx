// 可以刪除 - 已由 sidepanel/App.tsx 取代
import { useState, useEffect, useRef } from 'react';
import './App.css';

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      type: 'assistant',
      content: '你好！我是你的閱讀助手。我可以幫你理解當前頁面的內容，也可以回答你關於標註文字的問題。',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 監聽來自 Background Script 的消息
  useEffect(() => {
    const messageListener = (message: any) => {
      if (message.type === 'FROM_CONTENT') {
        // 處理來自 Content Script 的標註資料
        if (message.data.action === 'annotation') {
          const annotationMessage: ChatMessage = {
            id: Date.now().toString(),
            type: 'assistant',
            content: `檢測到新的標註：「${message.data.text}」\n我正在分析這段內容...`,
            timestamp: new Date()
          };
          setMessages(prev => [...prev, annotationMessage]);
        }
      }
    };

    browser.runtime.onMessage.addListener(messageListener);
    
    return () => {
      browser.runtime.onMessage.removeListener(messageListener);
    };
  }, []);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: inputValue,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      // 發送消息到 Background Script
      browser.runtime.sendMessage({
        type: 'POPUP_TO_CONTENT',
        data: {
          action: 'chat',
          message: inputValue
        }
      });

      // 模擬 AI 回應（實際會從 Background Script 接收）
      setTimeout(() => {
        const assistantMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          type: 'assistant',
          content: `我理解你的問題「${inputValue}」。讓我來幫你分析當前頁面的內容...`,
          timestamp: new Date()
        };
        setMessages(prev => [...prev, assistantMessage]);
        setIsLoading(false);
      }, 1000);
    } catch (error) {
      console.error('發送消息失敗:', error);
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="chatbot-container">
      {/* Header */}
      <div className="chatbot-header">
        <div className="header-content">
          <div className="assistant-info">
            <div className="avatar">🤖</div>
            <div className="assistant-details">
              <h3>閱讀助手</h3>
              <span className="status">AI 輔助的智能助手</span>
            </div>
          </div>
          <div className="header-actions">
            <button className="action-btn" title="設定">
              ⚙️
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="messages-container">
        {messages.map((message) => (
          <div key={message.id} className={`message ${message.type}`}>
            <div className="message-content">
              {message.type === 'assistant' && (
                <div className="message-avatar">🤖</div>
              )}
              <div className="message-bubble">
                <div className="message-text">{message.content}</div>
                <div className="message-time">
                  {message.timestamp.toLocaleTimeString('zh-TW', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </div>
              </div>
              {message.type === 'user' && (
                <div className="message-avatar user">👤</div>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="message assistant">
            <div className="message-content">
              <div className="message-avatar">🤖</div>
              <div className="message-bubble loading">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="input-container">
        <div className="input-wrapper">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="輸入你的問題..."
            className="message-input"
            rows={1}
            disabled={isLoading}
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputValue.trim() || isLoading}
            className="send-button"
            title="發送 (Enter)"
          >
            📤
          </button>
        </div>
        <div className="input-hint">
          按 Enter 發送，Shift + Enter 換行
        </div>
      </div>
    </div>
  );
}

export default App;
