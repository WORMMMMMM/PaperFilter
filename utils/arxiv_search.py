#!/usr/bin/env python3
"""
arXiv 搜索模块
通过arXiv搜索页面搜索论文并获取摘要
"""

import requests
from bs4 import BeautifulSoup
import time
import re
from typing import List, Dict, Optional
from urllib.parse import quote_plus
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import REQUEST_TIMEOUT, REQUEST_DELAY


class ArxivSearcher:
    """arXiv论文搜索器"""
    
    BASE_URL = "https://arxiv.org/search/"
    
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
    
    def search(self, query: str, max_results: int = 50, search_type: str = "all") -> List[Dict]:
        """
        在arXiv上搜索论文
        
        Args:
            query: 搜索关键词
            max_results: 最大返回结果数
            search_type: 搜索类型 (all, title, abstract, author)
            
        Returns:
            论文列表，每个包含 title, arxiv_id, abstract, authors, abs_link, html_link
        """
        papers = []
        start = 0
        page_size = 50  # arXiv每页最多50条
        
        print(f"正在搜索: {query}")
        
        while len(papers) < max_results:
            # 构建搜索URL
            encoded_query = quote_plus(query)
            url = f"{self.BASE_URL}?query={encoded_query}&searchtype={search_type}&source=header&start={start}"
            
            try:
                response = self.session.get(
                    url, 
                    headers=self.headers, 
                    timeout=REQUEST_TIMEOUT
                )
                response.raise_for_status()
                response.encoding = 'utf-8'
            except requests.RequestException as e:
                print(f"搜索请求失败: {e}")
                break
            
            # 解析搜索结果
            page_papers = self._parse_search_results(response.text)
            
            if not page_papers:
                # 没有更多结果
                break
            
            papers.extend(page_papers)
            print(f"已获取 {len(papers)} 篇论文...")
            
            if len(page_papers) < page_size:
                # 最后一页
                break
            
            start += page_size
            time.sleep(REQUEST_DELAY)
        
        # 截取到max_results
        papers = papers[:max_results]
        print(f"搜索完成，共找到 {len(papers)} 篇论文")
        
        return papers
    
    def _parse_search_results(self, html: str) -> List[Dict]:
        """
        解析arXiv搜索结果页面
        
        Args:
            html: HTML内容
            
        Returns:
            论文列表
        """
        soup = BeautifulSoup(html, 'html.parser')
        papers = []
        
        # arXiv搜索结果在 <li class="arxiv-result"> 中
        results = soup.find_all('li', class_='arxiv-result')
        
        for result in results:
            paper = {}
            
            # 获取arXiv ID和链接
            paper_link = result.find('p', class_='list-title')
            if paper_link:
                a_tag = paper_link.find('a')
                if a_tag:
                    href = a_tag.get('href', '')
                    # 提取arXiv ID
                    match = re.search(r'abs/(\d+\.\d+)', href)
                    if match:
                        paper['arxiv_id'] = match.group(1)
                        paper['abs_link'] = f"https://arxiv.org/abs/{paper['arxiv_id']}"
                        paper['html_link'] = f"https://arxiv.org/html/{paper['arxiv_id']}v1"
                        paper['pdf_link'] = f"https://arxiv.org/pdf/{paper['arxiv_id']}.pdf"
            
            if 'arxiv_id' not in paper:
                continue
            
            # 获取标题
            title_p = result.find('p', class_='title')
            if title_p:
                title = title_p.get_text(strip=True)
                paper['title'] = ' '.join(title.split())
            else:
                continue
            
            # 获取作者
            authors_p = result.find('p', class_='authors')
            if authors_p:
                author_links = authors_p.find_all('a')
                if author_links:
                    paper['authors'] = [a.get_text(strip=True) for a in author_links]
                else:
                    # 尝试从文本中提取
                    authors_text = authors_p.get_text(strip=True)
                    authors_text = re.sub(r'^Authors?:\s*', '', authors_text)
                    paper['authors'] = [a.strip() for a in authors_text.split(',') if a.strip()]
            else:
                paper['authors'] = []
            
            # 获取摘要
            abstract_span = result.find('span', class_='abstract-full')
            if abstract_span:
                # 移除 "Less" 链接文本
                abstract_text = abstract_span.get_text(strip=True)
                abstract_text = re.sub(r'\s*△\s*Less\s*$', '', abstract_text)
                paper['abstract'] = abstract_text
            else:
                # 尝试获取短摘要
                abstract_short = result.find('span', class_='abstract-short')
                if abstract_short:
                    paper['abstract'] = abstract_short.get_text(strip=True)
                else:
                    paper['abstract'] = ""
            
            # 获取提交日期
            submitted_p = result.find('p', class_='is-size-7')
            if submitted_p:
                submitted_text = submitted_p.get_text(strip=True)
                date_match = re.search(r'Submitted\s+(\d+\s+\w+,?\s+\d+)', submitted_text)
                if date_match:
                    paper['submitted_date'] = date_match.group(1)
            
            papers.append(paper)
        
        return papers
    
    def search_multiple_keywords(self, keywords: List[str], max_results_per_keyword: int = 30) -> List[Dict]:
        """
        使用多个关键词搜索并合并结果（去重）
        
        Args:
            keywords: 关键词列表
            max_results_per_keyword: 每个关键词的最大结果数
            
        Returns:
            去重后的论文列表
        """
        all_papers = {}  # 使用arxiv_id作为key去重
        
        for keyword in keywords:
            papers = self.search(keyword, max_results=max_results_per_keyword)
            for paper in papers:
                arxiv_id = paper.get('arxiv_id')
                if arxiv_id and arxiv_id not in all_papers:
                    all_papers[arxiv_id] = paper
            
            time.sleep(REQUEST_DELAY)  # 关键词间延迟
        
        return list(all_papers.values())
    
    def get_full_abstract(self, arxiv_id: str) -> Optional[str]:
        """
        获取论文的完整摘要（从abs页面）
        
        Args:
            arxiv_id: arXiv ID
            
        Returns:
            摘要文本
        """
        url = f"https://arxiv.org/abs/{arxiv_id}"
        
        try:
            response = self.session.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 摘要在 <blockquote class="abstract">
            abstract_block = soup.find('blockquote', class_='abstract')
            if abstract_block:
                abstract_text = abstract_block.get_text(strip=True)
                abstract_text = re.sub(r'^Abstract:\s*', '', abstract_text)
                return abstract_text
            
            return None
            
        except requests.RequestException as e:
            print(f"获取摘要失败 ({arxiv_id}): {e}")
            return None
    
    def close(self):
        """关闭session"""
        self.session.close()


# 测试代码
if __name__ == "__main__":
    searcher = ArxivSearcher()
    
    # 测试搜索
    print("测试搜索 'Contact-rich Manipulation'...")
    papers = searcher.search("Contact-rich Manipulation", max_results=10)
    
    for i, paper in enumerate(papers):
        print(f"\n{i+1}. {paper['title']}")
        print(f"   ID: {paper['arxiv_id']}")
        print(f"   Authors: {', '.join(paper['authors'][:3])}")
        print(f"   Abstract: {paper['abstract'][:200]}...")
    
    searcher.close()

