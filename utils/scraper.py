#!/usr/bin/env python3
"""
论文爬取工具模块
整合了arxiv_scraper.py和extract_links_and_abstracts.py的功能
"""

import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime


def get_abstract(arxiv_id, session=None):
    """
    获取论文摘要
    
    Args:
        arxiv_id: arXiv ID (例如: "2511.08583")
        session: requests session对象（可选）
    
    Returns:
        str: 摘要文本，如果获取失败则返回 None
    """
    if session is None:
        session = requests.Session()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        url = f"https://arxiv.org/abs/{arxiv_id}"
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        abstract_block = soup.find('blockquote', class_='abstract')
        if abstract_block:
            abstract_text = abstract_block.get_text()
            abstract_text = re.sub(r'Abstract:\s*', '', abstract_text, flags=re.I).strip()
            return abstract_text
        
        return None
        
    except requests.RequestException as e:
        print(f"  获取摘要失败 ({arxiv_id}): {e}")
        return None


def get_papers_from_page(url, session=None):
    """
    从单个页面获取论文信息
    
    Args:
        url: 要爬取的URL
        session: requests session对象（可选）
    
    Returns:
        list: 包含论文信息的字典列表
    """
    if session is None:
        session = requests.Session()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
    except requests.RequestException as e:
        print(f"请求失败: {e}")
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    papers = []
    
    dt_tags = soup.find_all('dt')
    
    for dt in dt_tags:
        paper = {}
        
        # 查找arXiv ID
        arxiv_link = dt.find('a', href=re.compile(r'/abs/\d+\.\d+'))
        if not arxiv_link:
            continue
            
        href = arxiv_link.get('href', '')
        match = re.search(r'/(\d+\.\d+)', href)
        if match:
            paper['arxiv_id'] = match.group(1)
            paper['abs_link'] = f"https://arxiv.org/abs/{paper['arxiv_id']}"
        else:
            continue
        
        # 查找HTML链接
        html_link_tag = dt.find('a', href=re.compile(r'https://arxiv.org/html/\d+\.\d+v\d+'))
        if html_link_tag:
            paper['html_link'] = html_link_tag.get('href', '')
        else:
            html_link_tag = dt.find('a', href=re.compile(r'/html/\d+\.\d+'))
            if html_link_tag:
                href = html_link_tag.get('href', '')
                if href.startswith('/'):
                    paper['html_link'] = f"https://arxiv.org{href}"
                else:
                    paper['html_link'] = href
            else:
                paper['html_link'] = f"https://arxiv.org/html/{paper['arxiv_id']}v1"
        
        # 查找对应的<dd>
        dd = dt.find_next_sibling('dd')
        if not dd:
            continue
        
        # 查找标题
        title_div = dd.find('div', class_='list-title')
        if title_div:
            title_text = title_div.get_text()
            title = re.sub(r'Title:\s*', '', title_text, flags=re.I).strip()
            title = ' '.join(title.split())
        else:
            continue
        
        if not title or len(title) < 5:
            continue
        
        paper['title'] = title
        
        # 查找作者
        authors = []
        authors_div = dd.find('div', class_='list-authors')
        if authors_div:
            author_links = authors_div.find_all('a', href=re.compile(r'/search/'))
            if author_links:
                authors = [link.get_text(strip=True) for link in author_links]
            else:
                authors_text = authors_div.get_text()
                authors_text = re.sub(r'Authors?:\s*', '', authors_text, flags=re.I).strip()
                if authors_text:
                    authors = [a.strip() for a in re.split(r',', authors_text) if a.strip()]
        
        paper['authors'] = authors
        papers.append(paper)
    
    return papers


def scrape_all_papers_with_abstracts(base_url, max_papers=None):
    """
    爬取所有页面的论文并获取摘要
    
    Args:
        base_url: 基础URL
        max_papers: 最大爬取论文数量（None表示全部）
    
    Returns:
        list: 所有论文的列表，每个包含title, arxiv_id, html_link, abs_link, abstract, authors
    """
    all_papers = []
    session = requests.Session()
    
    page = 1
    skip = 0
    show = 50
    
    print(f"正在爬取: {base_url}")
    
    while True:
        if skip == 0:
            url = base_url
        else:
            url = f"{base_url}?skip={skip}&show={show}"
        
        papers = get_papers_from_page(url, session)
        
        if not papers:
            break
        
        # 为每篇论文获取摘要
        for i, paper in enumerate(papers):
            if max_papers and len(all_papers) >= max_papers:
                break
            
            print(f"正在获取摘要 [{len(all_papers) + 1}]: {paper['arxiv_id']} - {paper['title'][:50]}...")
            abstract = get_abstract(paper['arxiv_id'], session)
            paper['abstract'] = abstract if abstract else "（未获取到摘要）"
            all_papers.append(paper)
            time.sleep(0.5)  # 礼貌延迟
        
        if max_papers and len(all_papers) >= max_papers:
            break
        
        if len(papers) < 50:
            break
        
        skip += 50
        page += 1
        time.sleep(1)
    
    session.close()
    return all_papers

