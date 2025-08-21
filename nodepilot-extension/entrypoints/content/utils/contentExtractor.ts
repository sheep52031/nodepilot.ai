export interface ExtractedContent {
  title: string;
  content: string;
  cleanText: string;
  images: ExtractedImage[];
  metadata: {
    author?: string;
    publishDate?: string;
    wordCount: number;
    readTime: number;
  };
  originalUrl: string;
}

export interface ExtractedImage {
  src: string;
  alt?: string;
  width?: number;
  height?: number;
}

/**
 * 智慧文章內容擷取器
 */
export class ContentExtractor {
  private baseUrl: string;

  constructor(baseUrl: string = window.location.href) {
    this.baseUrl = baseUrl;
  }

  /**
   * 擷取完整文章內容
   */
  async extractArticleContent(): Promise<ExtractedContent> {
    const title = this.extractTitle();
    const mainContent = this.extractMainContent();
    const cleanText = this.extractCleanText(mainContent);
    const images = await this.extractImages(mainContent);
    const metadata = this.extractMetadata(cleanText);

    return {
      title,
      content: mainContent.outerHTML,
      cleanText,
      images,
      metadata,
      originalUrl: this.baseUrl,
    };
  }

  /**
   * 提取文章標題
   */
  private extractTitle(): string {
    // 優先從 h1 標籤獲取
    const h1 = document.querySelector('h1');
    if (h1?.textContent?.trim()) {
      return h1.textContent.trim();
    }

    // 從 title 標籤獲取
    const title = document.title;
    if (title?.trim()) {
      return title.trim();
    }

    // 從 meta property="og:title" 獲取
    const ogTitle = document.querySelector('meta[property="og:title"]');
    if (ogTitle && ogTitle.getAttribute('content')) {
      return ogTitle.getAttribute('content')!.trim();
    }

    return '未命名文章';
  }

  /**
   * 提取主要文章內容
   */
  private extractMainContent(): Element {
    // 常見的文章容器選擇器
    const selectors = [
      'article',
      '[role="article"]',
      '.article',
      '.post',
      '.content',
      '.entry-content',
      '.post-content',
      '.article-content',
      'main',
      '#content',
      '.main-content',
    ];

    for (const selector of selectors) {
      const element = document.querySelector(selector);
      if (element && this.isValidArticleContainer(element)) {
        return this.cleanElement(element.cloneNode(true) as Element);
      }
    }

    // 備案：尋找最大的文字容器
    return this.findLargestTextContainer();
  }

  /**
   * 檢查元素是否為有效的文章容器
   */
  private isValidArticleContainer(element: Element): boolean {
    const textContent = element.textContent || '';
    const textLength = textContent.trim().length;
    
    // 文字長度至少 200 字元
    if (textLength < 200) return false;

    // 檢查是否包含常見的文章元素
    const hasArticleElements = 
      element.querySelector('p') ||
      element.querySelector('h2, h3, h4') ||
      element.querySelector('ul, ol');

    return !!hasArticleElements;
  }

  /**
   * 尋找最大的文字容器
   */
  private findLargestTextContainer(): Element {
    let maxLength = 0;
    let bestElement = document.body;

    const checkElement = (element: Element) => {
      const textLength = (element.textContent || '').trim().length;
      if (textLength > maxLength && textLength > 200) {
        maxLength = textLength;
        bestElement = element;
      }
    };

    // 檢查所有可能的容器
    document.querySelectorAll('div, section, main').forEach(checkElement);

    return this.cleanElement(bestElement.cloneNode(true) as Element);
  }

  /**
   * 清理元素，移除不需要的內容
   */
  private cleanElement(element: Element): Element {
    // 移除廣告和干擾元素
    const removeSelectors = [
      'script',
      'style',
      'noscript',
      'iframe',
      '.advertisement',
      '.ad',
      '.ads',
      '.social-share',
      '.comments',
      '.comment',
      '.sidebar',
      '.navigation',
      '.nav',
      '.header',
      '.footer',
      '.breadcrumb',
      '.related-posts',
      '.tags',
      '.author-bio',
      '[class*="share"]',
      '[id*="comment"]',
      '[class*="ad-"]',
      '[id*="ad-"]',
    ];

    removeSelectors.forEach(selector => {
      element.querySelectorAll(selector).forEach(el => el.remove());
    });

    // 移除空白元素
    element.querySelectorAll('*').forEach(el => {
      if (!el.textContent?.trim() && !el.querySelector('img, video, audio')) {
        el.remove();
      }
    });

    return element;
  }

  /**
   * 提取純文字內容
   */
  private extractCleanText(element: Element): string {
    // 將 HTML 轉換為純文字，保留基本格式
    let text = element.textContent || '';
    
    // 清理多餘空白
    text = text.replace(/\s+/g, ' ').trim();
    
    return text;
  }

  /**
   * 提取圖片
   */
  private async extractImages(element: Element): Promise<ExtractedImage[]> {
    const images: ExtractedImage[] = [];
    const imgElements = element.querySelectorAll('img');

    for (const img of imgElements) {
      const src = img.getAttribute('src') || img.getAttribute('data-src');
      if (!src) continue;

      // 轉換為絕對路徑
      const absoluteSrc = this.convertToAbsoluteUrl(src);
      
      images.push({
        src: absoluteSrc,
        alt: img.getAttribute('alt') || '',
        width: img.naturalWidth || undefined,
        height: img.naturalHeight || undefined,
      });
    }

    return images;
  }

  /**
   * 轉換相對路徑為絕對路徑
   */
  private convertToAbsoluteUrl(url: string): string {
    if (url.startsWith('http')) {
      return url;
    }

    try {
      return new URL(url, this.baseUrl).href;
    } catch {
      return url;
    }
  }

  /**
   * 提取元資料
   */
  private extractMetadata(text: string): ExtractedContent['metadata'] {
    const wordCount = text.split(/\s+/).length;
    const readTime = Math.max(1, Math.ceil(wordCount / 200)); // 假設每分鐘讀 200 字

    // 嘗試提取作者
    const authorMeta = document.querySelector('meta[name="author"]');
    const author = authorMeta?.getAttribute('content') || undefined;

    // 嘗試提取發布日期
    const dateMeta = 
      document.querySelector('meta[property="article:published_time"]') ||
      document.querySelector('meta[name="date"]') ||
      document.querySelector('time[datetime]');
    
    const publishDate = dateMeta?.getAttribute('content') || 
                       dateMeta?.getAttribute('datetime') || 
                       undefined;

    return {
      author,
      publishDate,
      wordCount,
      readTime,
    };
  }
}