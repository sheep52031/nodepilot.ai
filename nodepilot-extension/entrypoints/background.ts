export default defineBackground(() => {
  console.log('NodePilot Background Script loaded', { id: browser.runtime.id });
  
  // 處理 Popup 與 Content Script 之間的通信
  browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
    console.log('Background received message:', message);
    
    // 轉發 Popup 消息到所有 Content Scripts
    if (message.type === 'POPUP_TO_CONTENT') {
      browser.tabs.query({}, (tabs) => {
        tabs.forEach(tab => {
          if (tab.id) {
            browser.tabs.sendMessage(tab.id, {
              type: 'FROM_POPUP',
              data: message.data
            }).catch(() => {
              // 忽略無法傳送的分頁（非目標網站）
            });
          }
        });
      });
      sendResponse({ success: true });
    }
    
    // 轉發 Content Script 消息到 Popup
    if (message.type === 'CONTENT_TO_POPUP') {
      // 通知 Popup 有新的標註資料
      browser.runtime.sendMessage({
        type: 'FROM_CONTENT',
        data: message.data
      }).catch(() => {
        // Popup 可能未開啟，忽略錯誤
      });
      sendResponse({ success: true });
    }
    
    return true; // 保持消息通道開啟
  });
  
  // 處理 Extension 安裝
  browser.runtime.onInstalled.addListener(() => {
    console.log('NodePilot Extension installed');
  });
});
