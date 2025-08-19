"""
NodePilot RAG 筆記檢索服務
整合 Obsidian 筆記 RAG 向量資料庫檢索系統
"""

import logging
import os
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import asyncio
from datetime import datetime

# 向量搜索相關導入 (這裡先用模擬，實際需要安裝 sentence-transformers, chromadb 等)
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None


@dataclass
class NoteDocument:
    """筆記文件資料結構"""
    title: str
    content: str
    file_path: str
    created_at: datetime
    modified_at: datetime
    tags: List[str] = None
    embedding: Optional[List[float]] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class RAGSearchResult:
    """RAG 搜索結果"""
    document: NoteDocument
    relevance_score: float
    matched_snippets: List[str]
    reasoning: str


class ObsidianNoteParser:
    """Obsidian 筆記解析器"""
    
    def __init__(self, notes_directory: str = None):
        self.notes_directory = notes_directory or os.getenv("OBSIDIAN_VAULT_PATH", "")
        self.logger = logging.getLogger("ObsidianNoteParser")
        
    def scan_notes(self) -> List[NoteDocument]:
        """掃描筆記目錄並解析所有筆記"""
        if not self.notes_directory or not os.path.exists(self.notes_directory):
            self.logger.warning(f"筆記目錄不存在: {self.notes_directory}")
            return self._get_mock_notes()
            
        notes = []
        notes_path = Path(self.notes_directory)
        
        for md_file in notes_path.glob("**/*.md"):
            try:
                note = self._parse_note_file(md_file)
                if note:
                    notes.append(note)
            except Exception as e:
                self.logger.error(f"解析筆記失敗 {md_file}: {e}")
                
        return notes
        
    def _parse_note_file(self, file_path: Path) -> Optional[NoteDocument]:
        """解析單一筆記檔案"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析 YAML front matter 和標籤
            title = file_path.stem
            tags = self._extract_tags(content)
            
            stat = file_path.stat()
            
            return NoteDocument(
                title=title,
                content=content,
                file_path=str(file_path),
                created_at=datetime.fromtimestamp(stat.st_ctime),
                modified_at=datetime.fromtimestamp(stat.st_mtime),
                tags=tags
            )
            
        except Exception as e:
            self.logger.error(f"讀取筆記檔案失敗 {file_path}: {e}")
            return None
    
    def _extract_tags(self, content: str) -> List[str]:
        """提取筆記中的標籤"""
        tags = []
        
        # 提取 #標籤 格式
        import re
        tag_matches = re.findall(r'#([a-zA-Z0-9\u4e00-\u9fff_-]+)', content)
        tags.extend(tag_matches)
        
        # 提取 YAML front matter 中的 tags
        yaml_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if yaml_match:
            try:
                import yaml
                yaml_data = yaml.safe_load(yaml_match.group(1))
                if isinstance(yaml_data, dict) and 'tags' in yaml_data:
                    yaml_tags = yaml_data['tags']
                    if isinstance(yaml_tags, list):
                        tags.extend(yaml_tags)
            except ImportError:
                pass  # yaml 套件未安裝
                
        return list(set(tags))  # 去重
    
    def _get_mock_notes(self) -> List[NoteDocument]:
        """取得模擬筆記資料用於測試"""
        return [
            NoteDocument(
                title="Python FastAPI 開發筆記",
                content="""# Python FastAPI 開發筆記
                
## 基礎概念
FastAPI 是現代高效能的 Python Web 框架，基於 Starlette 和 Pydantic。

## 關鍵特色
- 自動生成 OpenAPI 文件
- 內建資料驗證
- 異步支援
- 高效能

## 實作範例
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}
```

## 相關筆記
- [[RESTful API 設計原則]]
- [[Python 異步程式設計]]

#python #fastapi #webdev""",
                file_path="/mock/notes/python-fastapi.md",
                created_at=datetime(2025, 1, 15),
                modified_at=datetime(2025, 1, 19),
                tags=["python", "fastapi", "webdev"]
            ),
            
            NoteDocument(
                title="多 Agent 系統設計",
                content="""# 多 Agent 系統設計

## 核心概念
多 Agent 系統是由多個智能代理協作完成複雜任務的架構。

## 設計原則
1. 任務分解：將複雜問題拆解為子任務
2. Agent 專責：每個 Agent 負責特定領域
3. 協作機制：Agent 間的通信和協調
4. 容錯處理：降級和錯誤恢復機制

## 實作架構
- 調度器 (Scheduler)
- 任務佇列 (Task Queue)
- 執行引擎 (Execution Engine)
- 結果整合 (Result Integration)

## 相關概念
- Plan-and-Execute 模式
- 事件驅動架構
- 微服務設計

#ai #multiagent #architecture""",
                file_path="/mock/notes/multi-agent-design.md", 
                created_at=datetime(2025, 1, 10),
                modified_at=datetime(2025, 1, 18),
                tags=["ai", "multiagent", "architecture"]
            )
        ]


class EmbeddingService:
    """向量嵌入服務"""
    
    def __init__(self):
        self.logger = logging.getLogger("EmbeddingService")
        self.model_loaded = False
        
    async def get_embedding(self, text: str) -> List[float]:
        """取得文字的向量嵌入"""
        if not NUMPY_AVAILABLE:
            # 模擬向量嵌入
            return self._mock_embedding(text)
        
        # TODO: 實際整合 sentence-transformers 或 OpenAI embeddings
        return self._mock_embedding(text)
        
    def _mock_embedding(self, text: str) -> List[float]:
        """模擬向量嵌入 - 基於文字長度和內容生成"""
        # 簡單的模擬演算法
        import hashlib
        text_hash = hashlib.md5(text.encode()).hexdigest()
        
        # 生成 384 維度的模擬向量
        embedding = []
        for i in range(384):
            char_index = i % len(text_hash)
            value = int(text_hash[char_index], 16) / 16.0 - 0.5  # 正規化到 [-0.5, 0.5]
            embedding.append(value)
            
        return embedding
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """計算兩個向量的相似度"""
        if not NUMPY_AVAILABLE:
            return self._mock_similarity(embedding1, embedding2)
            
        # 使用餘弦相似度
        if not embedding1 or not embedding2:
            return 0.0
            
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
            
        return dot_product / (norm1 * norm2)
        
    def _mock_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """模擬相似度計算"""
        if not embedding1 or not embedding2:
            return 0.0
            
        # 簡化的相似度計算
        total_diff = sum(abs(a - b) for a, b in zip(embedding1, embedding2))
        max_diff = len(embedding1) * 1.0  # 最大可能差異
        similarity = 1.0 - (total_diff / max_diff)
        return max(0.0, similarity)


class RAGService:
    """RAG 筆記檢索服務主類"""
    
    def __init__(self):
        self.note_parser = ObsidianNoteParser()
        self.embedding_service = EmbeddingService()
        self.logger = logging.getLogger("RAGService")
        self.note_cache: List[NoteDocument] = []
        self.cache_timestamp = None
        
    async def initialize(self):
        """初始化服務，載入筆記和建立向量嵌入"""
        try:
            self.logger.info("開始載入筆記資料...")
            self.note_cache = self.note_parser.scan_notes()
            
            # 為每個筆記建立向量嵌入
            for note in self.note_cache:
                if note.embedding is None:
                    note.embedding = await self.embedding_service.get_embedding(
                        f"{note.title} {note.content[:500]}"  # 限制長度
                    )
            
            self.cache_timestamp = datetime.now()
            self.logger.info(f"✅ 載入了 {len(self.note_cache)} 篇筆記")
            
        except Exception as e:
            self.logger.error(f"RAG 服務初始化失敗: {e}")
            
    async def search_relevant_notes(self, 
                                  query: str, 
                                  selected_text: str = "",
                                  top_k: int = 5,
                                  min_relevance: float = 0.3) -> List[RAGSearchResult]:
        """搜尋相關筆記"""
        
        if not self.note_cache:
            await self.initialize()
            
        if not self.note_cache:
            return []
        
        # 建立搜尋查詢的向量嵌入
        search_text = f"{query} {selected_text}".strip()
        query_embedding = await self.embedding_service.get_embedding(search_text)
        
        # 計算相似度並排序
        results = []
        for note in self.note_cache:
            if note.embedding is None:
                continue
                
            similarity = self.embedding_service.calculate_similarity(
                query_embedding, note.embedding
            )
            
            if similarity >= min_relevance:
                # 提取匹配的片段
                matched_snippets = self._extract_relevant_snippets(
                    note.content, query, max_snippets=3
                )
                
                reasoning = self._generate_relevance_reasoning(
                    note, query, similarity
                )
                
                result = RAGSearchResult(
                    document=note,
                    relevance_score=similarity,
                    matched_snippets=matched_snippets,
                    reasoning=reasoning
                )
                results.append(result)
        
        # 按相似度排序並返回 top_k
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:top_k]
    
    def _extract_relevant_snippets(self, content: str, query: str, max_snippets: int = 3) -> List[str]:
        """提取相關的內容片段"""
        snippets = []
        
        # 按段落分割
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        # 尋找包含查詢關鍵字的段落
        query_words = query.lower().split()
        
        for paragraph in paragraphs[:10]:  # 限制檢查段落數
            paragraph_lower = paragraph.lower()
            
            # 檢查是否包含查詢詞
            matches = sum(1 for word in query_words if word in paragraph_lower)
            if matches > 0:
                # 截斷過長的段落
                if len(paragraph) > 200:
                    paragraph = paragraph[:200] + "..."
                snippets.append(paragraph)
                
                if len(snippets) >= max_snippets:
                    break
        
        return snippets
    
    def _generate_relevance_reasoning(self, note: NoteDocument, query: str, similarity: float) -> str:
        """產生相關性推理說明"""
        reasons = []
        
        # 標題相關性
        if any(word.lower() in note.title.lower() for word in query.split()):
            reasons.append("標題匹配")
            
        # 標籤相關性  
        query_words = set(query.lower().split())
        tag_words = set(tag.lower() for tag in note.tags)
        if query_words & tag_words:
            reasons.append("標籤相關")
            
        # 相似度等級
        if similarity > 0.7:
            reasons.append("高度相關")
        elif similarity > 0.5:
            reasons.append("中度相關")
        else:
            reasons.append("低度相關")
            
        return "、".join(reasons) if reasons else "內容相關"
    
    def get_service_statistics(self) -> Dict[str, Any]:
        """獲取服務統計資訊"""
        return {
            "total_notes": len(self.note_cache),
            "cache_updated": self.cache_timestamp.isoformat() if self.cache_timestamp else None,
            "notes_directory": self.note_parser.notes_directory,
            "embedding_service": "mock" if not NUMPY_AVAILABLE else "enabled"
        }


# 全域 RAG 服務實例
rag_service = RAGService()