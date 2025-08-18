import ReactDOM from 'react-dom/client';
import { NodePilotProvider } from './context';
import { AnnotationUI } from './components/AnnotationUI';
import './style.css';

// ContentApp 組件已移除，邏輯直接在 main 函數中處理

export default defineContentScript({
  matches: ['https://manus.im/blog/*', 'https://manus.im/*/blog/*'],
  cssInjectionMode: 'ui',
  
  async main(ctx) {
    console.log('NodePilot React Content Script loaded');
    
    // 全局變量
    let currentRoot: ReactDOM.Root | null = null;
    let currentUI: any = null;

    // 文字選取處理邏輯
    const handleMouseUp = (event: Event) => {
      const mouseEvent = event as MouseEvent;
      console.log('MouseUp event detected');
      
      // 避免在自己的 UI 上觸發
      const target = mouseEvent.target as Element;
      if (target?.closest?.('.nodepilot-interactive')) {
        console.log('Ignored: click on nodepilot UI');
        return;
      }

      setTimeout(() => {
        const selection = window.getSelection();
        const selectedText = selection?.toString().trim();
        console.log('Selected text:', selectedText);

        if (selectedText && selectedText.length >= 3) {
          const range = selection?.getRangeAt(0);
          const rect = range?.getBoundingClientRect();
          console.log('Selection rect:', rect);

          if (rect && rect.width > 0 && rect.height > 0) {
            console.log('Calling showAnnotationUI');
            showAnnotationUI(selectedText, rect);
          }
        } else {
          hideAnnotationUI();
        }
      }, 100);
    };

    // 快捷鍵處理邏輯
    const handleKeyDown = (event: Event) => {
      const keyEvent = event as KeyboardEvent;
      
      // Ctrl+Shift+A 或 Cmd+Shift+A 強制觸發
      if ((keyEvent.ctrlKey || keyEvent.metaKey) && keyEvent.shiftKey && keyEvent.key === 'A') {
        keyEvent.preventDefault();
        keyEvent.stopPropagation();
        console.log('Shortcut triggered!');
        
        const selection = window.getSelection();
        let selectedText = selection?.toString().trim();
        
        // 如果沒有選取文字，提供預設文字
        if (!selectedText) {
          selectedText = '測試文字';
        }
        
        // 計算位置 - 使用螢幕中央
        const rect = {
          left: window.innerWidth / 2,
          bottom: window.innerHeight / 2,
          width: 1,
          height: 1
        };
        
        showAnnotationUI(selectedText, rect);
        return;
      }
      
      // Escape 關閉 UI
      if (keyEvent.key === 'Escape') {
        hideAnnotationUI();
      }
    };

    // 顯示標註 UI - 使用直接 DOM 創建方式
    const showAnnotationUI = async (text: string, rect: DOMRect | any) => {
      console.log('showAnnotationUI called with:', { text, rect });
      hideAnnotationUI(); // 先清理舊的 UI

      // 計算位置，確保在視窗範圍內
      const viewportHeight = window.innerHeight;
      const viewportWidth = window.innerWidth;
      
      let left = rect.left;
      let top = rect.bottom + 5;
      
      // 如果超出右邊界，往左調整
      if (left + 300 > viewportWidth) {
        left = viewportWidth - 320;
      }
      
      // 如果超出下邊界，顯示在選取文字上方
      if (top + 200 > viewportHeight) {
        top = rect.top - 200;
      }
      
      // 確保不會超出左上角
      left = Math.max(10, left);
      top = Math.max(10, top);

      // 創建容器元素
      const hostElement = document.createElement('div');
      hostElement.id = 'nodepilot-annotation-host';
      console.log('Created host element at position:', { left, top });
      hostElement.style.cssText = `
        position: fixed;
        left: ${left}px;
        top: ${top}px;
        z-index: 99999;
        pointer-events: auto;
        background: white;
        border: 2px solid red;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
      `;
      
      document.body.appendChild(hostElement);
      
      // 創建 React 應用容器
      const app = document.createElement('div');
      app.id = 'nodepilot-annotation-app';
      hostElement.appendChild(app);
      
      currentRoot = ReactDOM.createRoot(app);
      currentRoot.render(
        <NodePilotProvider>
          <AnnotationUI
            selectedText={text}
            position={{
              x: left,
              y: top + 10
            }}
            onClose={hideAnnotationUI}
          />
        </NodePilotProvider>
      );
      
      // 記錄 hostElement 用於清理
      currentUI = { 
        hostElement,
        remove: () => {
          if (hostElement.parentNode) {
            hostElement.parentNode.removeChild(hostElement);
          }
        }
      };
    };

    // 隱藏標註 UI
    const hideAnnotationUI = () => {
      if (currentUI) {
        currentUI.remove();
        currentUI = null;
      }
      if (currentRoot) {
        currentRoot.unmount();
        currentRoot = null;
      }
    };

    // 使用 ctx.addEventListener 進行事件綁定
    ctx.addEventListener(document, 'mouseup', handleMouseUp, { capture: true });
    ctx.addEventListener(document, 'keydown', handleKeyDown, { capture: true });

    // 創建開發提示 UI - 直接 DOM 方式
    const hintElement = document.createElement('div');
    hintElement.id = 'nodepilot-dev-hint';
    hintElement.style.cssText = `
      position: fixed;
      top: 10px;
      right: 10px;
      background: rgba(0,0,0,0.8);
      color: white;
      padding: 8px;
      border-radius: 4px;
      font-size: 11px;
      font-family: monospace;
      z-index: 10001;
      pointer-events: none;
    `;
    hintElement.innerHTML = `
      NodePilot 快捷鍵：<br/>
      Ctrl+Shift+A：強制標註<br/>
      Esc：關閉
    `;
    
    document.body.appendChild(hintElement);

    // 返回清理函數
    return () => {
      hideAnnotationUI();
      if (hintElement.parentNode) {
        hintElement.parentNode.removeChild(hintElement);
      }
    };
  },
});