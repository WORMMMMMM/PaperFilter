#!/usr/bin/env python3
"""
语义搜索模块
使用sentence-transformers和FAISS实现论文的语义搜索
"""

import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from typing import List, Dict, Tuple


class PaperSearchEngine:
    """论文语义搜索引擎"""
    
    def __init__(self, model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        """
        初始化搜索引擎
        
        Args:
            model_name: sentence-transformers模型名称
                       推荐使用多语言模型以支持中英文搜索
        """
        print(f"正在加载模型: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.index = None
        self.papers = []
        self.embeddings = None
        
    def build_index(self, papers: List[Dict]):
        """
        构建搜索索引
        
        Args:
            papers: 论文列表，每个论文包含title, abstract等字段
        """
        print(f"正在为 {len(papers)} 篇论文构建索引...")
        self.papers = papers
        
        # 为每篇论文创建搜索文本（标题+摘要）
        search_texts = []
        for paper in papers:
            title = paper.get('title', '')
            abstract = paper.get('abstract', '')
            # 组合标题和摘要作为搜索文本
            search_text = f"{title}. {abstract}"
            search_texts.append(search_text)
        
        # 生成embeddings
        print("正在生成向量表示...")
        self.embeddings = self.model.encode(search_texts, show_progress_bar=True)
        
        # 构建FAISS索引
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)  # L2距离
        
        # 归一化向量（用于余弦相似度）
        faiss.normalize_L2(self.embeddings)
        self.index.add(self.embeddings.astype('float32'))
        
        print(f"索引构建完成！维度: {dimension}, 论文数: {len(papers)}")
    
    def search(self, query: str, top_k: int = 10) -> List[Tuple[Dict, float]]:
        """
        搜索相关论文
        
        Args:
            query: 搜索查询文本
            top_k: 返回前k个结果
        
        Returns:
            List[Tuple[Dict, float]]: (论文字典, 相似度分数)的列表
        """
        if self.index is None or len(self.papers) == 0:
            return []
        
        # 将查询转换为向量
        query_embedding = self.model.encode([query])
        faiss.normalize_L2(query_embedding)
        
        # 搜索
        distances, indices = self.index.search(query_embedding.astype('float32'), top_k)
        
        # 构建结果列表（相似度 = 1 - 距离，因为使用了归一化L2）
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < len(self.papers):
                similarity = 1 - dist  # 转换为相似度分数
                results.append((self.papers[idx], float(similarity)))
        
        return results
    
    def save_index(self, index_path: str, papers_path: str):
        """
        保存索引和论文数据
        
        Args:
            index_path: FAISS索引保存路径
            papers_path: 论文数据JSON保存路径
        """
        if self.index is not None:
            faiss.write_index(self.index, index_path)
            print(f"索引已保存到: {index_path}")
        
        with open(papers_path, 'w', encoding='utf-8') as f:
            json.dump(self.papers, f, ensure_ascii=False, indent=2)
        print(f"论文数据已保存到: {papers_path}")
    
    def load_index(self, index_path: str, papers_path: str):
        """
        加载索引和论文数据
        
        Args:
            index_path: FAISS索引路径
            papers_path: 论文数据JSON路径
        """
        if os.path.exists(index_path) and os.path.exists(papers_path):
            self.index = faiss.read_index(index_path)
            print(f"索引已加载: {index_path}")
            
            with open(papers_path, 'r', encoding='utf-8') as f:
                self.papers = json.load(f)
            print(f"论文数据已加载: {papers_path}, 共 {len(self.papers)} 篇论文")
            
            # 重新生成embeddings（用于后续可能的增量更新）
            search_texts = []
            for paper in self.papers:
                title = paper.get('title', '')
                abstract = paper.get('abstract', '')
                search_text = f"{title}. {abstract}"
                search_texts.append(search_text)
            self.embeddings = self.model.encode(search_texts, show_progress_bar=False)
            faiss.normalize_L2(self.embeddings)
            
            return True
        return False

