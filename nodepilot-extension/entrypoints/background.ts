export default defineBackground(() => {
  console.log('NodePilot Background Script loaded', { id: browser.runtime.id });
  
  // 處理擴充套件圖示點擊 (Action)
  browser.action.onClicked.addListener(async (tab) => {
    console.log('Extension icon clicked on tab:', tab.id);
    
    if (tab.id && tab.url) {
      // 檢查是否為支援的網站
      const supportedSites = ['manus.im'];
      const isSupported = supportedSites.some(site => tab.url!.includes(site));
      
      if (isSupported) {
        try {
          // 傳送訊息給 Content Script 顯示 Reader 橫槓
          await browser.tabs.sendMessage(tab.id, {
            type: 'SHOW_READER_BAR'
          });
        } catch (error) {
          console.error('Failed to send message to content script:', error);
        }
      } else {
        console.log('Unsupported website:', tab.url);
      }
    }
  });
  
  // 處理 Popup 與 Content Script 之間的通信
  browser.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    console.log('Background received message:', message);
    
    // 處理 Open Reader 請求
    if (message.type === 'OPEN_READER') {
      console.log('Opening Reader tab with content:', message.data);
      
      // 創建新的 Reader Tab
      browser.tabs.create({
        url: browser.runtime.getURL('/reader.html'),
        active: true,
      }).then((tab) => {
        // 等待 tab 載入完成後傳送內容
        const onTabUpdated = (tabId: number, changeInfo: any) => {
          if (tabId === tab.id && changeInfo.status === 'complete') {
            browser.tabs.onUpdated.removeListener(onTabUpdated);
            
            // 傳送擷取的內容到 Reader Tab
            browser.tabs.sendMessage(tab.id!, {
              type: 'LOAD_CONTENT',
              data: message.data,
            }).catch(console.error);
          }
        };
        
        browser.tabs.onUpdated.addListener(onTabUpdated);
        sendResponse({ success: true, tabId: tab.id });
      }).catch((error) => {
        console.error('Failed to create Reader tab:', error);
        sendResponse({ success: false, error: error.message });
      });
      
      return true; // 保持消息通道開啟
    }
    
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
