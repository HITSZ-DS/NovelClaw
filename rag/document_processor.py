"""
文档处理模块：文档分块、嵌入等
"""
import os
from typing import List, Dict, Optional
import uuid
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    # 如果 langchain 不可用，使用简单的文本分割
    class RecursiveCharacterTextSplitter:
        def __init__(self, chunk_size=500, chunk_overlap=100, length_function=len):
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap
            self.length_function = length_function
        
        def split_text(self, text: str):
            chunks = []
            start = 0
            while start < len(text):
                end = start + self.chunk_size
                chunks.append(text[start:end])
                start = end - self.chunk_overlap
            return chunks
# 避免在某些环境中 transformers 自动导入 TensorFlow 引发冲突
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TRANSFORMERS_NO_FLAX", "1")
os.environ.setdefault("USE_TF", "0")

import numpy as np


class DocumentProcessor:
    """文档处理器"""
    
    def __init__(self, config):
        self.config = config
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            length_function=len,
        )
        embed_name = (config.embedding_model or "").strip().lower()
        if embed_name in {"none", "noop", "disable", "disabled"}:
            self.embedding_model = None
        else:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise ImportError(
                    "sentence-transformers is required only when EMBEDDING_MODEL is enabled."
                ) from exc
            self.embedding_model = SentenceTransformer(config.embedding_model)
    
    def split_documents(self, text: str) -> List[str]:
        """
        将文档分割成块
        
        Args:
            text: 原始文本
        
        Returns:
            文本块列表
        """
        chunks = self.text_splitter.split_text(text)
        return chunks
    
    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        获取文本的嵌入向量
        
        Args:
            texts: 文本列表
        
        Returns:
            嵌入向量数组
        """
        if self.embedding_model is None:
            # return a small dummy vector to avoid heavy model load when embedding is disabled
            return np.zeros((len(texts), 4), dtype=float)
        embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return embeddings
    
    def process_document(self, text: str, doc_id: Optional[str] = None) -> List[Dict]:
        """
        处理文档：分块并生成嵌入
        
        Args:
            text: 原始文档
            doc_id: 文档唯一ID（可选，用于去重）
        
        Returns:
            包含文本块和嵌入的字典列表
        """
        # doc_id 用于稳定去重；建议传入稳定值（如 file_path hash / jsonl 行号）
        prefix = doc_id or uuid.uuid4().hex
        chunks = self.split_documents(text)
        embeddings = self.get_embeddings(chunks)
        
        result = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            result.append({
                "id": f"{prefix}_chunk_{i}",
                "text": chunk,
                "embedding": embedding.tolist(),
                "metadata": {
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            })
        
        return result
