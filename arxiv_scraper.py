#!/usr/bin/env python3
"""
arXiv Robotics Papers Scraper
爬取 https://arxiv.org/list/cs.RO/recent 上的所有论文标题
"""

import requests
from bs4 import BeautifulSoup
import time
import json
from datetime import datetime
import re


def get_papers_from_page(url, session=None):
    """
    从单个页面获取论文标题
    
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
    
    # arXiv的页面结构：有多个 <dl id="articles">，每个代表一个日期分组
    # 在每个 <dl> 中，有多个 <dt> 和 <dd> 对，每对代表一篇论文
    # 结构: <dl><dt>arXiv ID</dt><dd><div class="meta">...</div></dd>...</dl>
    
    # 查找所有的 <dt> 标签（每个 <dt> 对应一篇论文）
    dt_tags = soup.find_all('dt')
    
    for dt in dt_tags:
        paper = {}
        
        # 查找arXiv ID - 在 <dt> 中的链接
        arxiv_link = dt.find('a', href=re.compile(r'/abs/\d+\.\d+'))
        if not arxiv_link:
            continue
            
        href = arxiv_link.get('href', '')
        match = re.search(r'/(\d+\.\d+)', href)
        if match:
            paper['arxiv_id'] = match.group(1)
        
        # 查找对应的 <dd> - <dd> 紧跟在 <dt> 后面
        dd = dt.find_next_sibling('dd')
        if not dd:
            continue
        
        # 查找标题 - 在 <dd> 中的 <div class="list-title">
        title_div = dd.find('div', class_='list-title')
        if title_div:
            # 标题在 "Title:" 描述符后面的文本节点中
            # 方法：获取整个div的文本，然后移除 "Title:" 前缀
            title_text = title_div.get_text()
            # 移除 "Title:" 前缀和多余空白
            title = re.sub(r'Title:\s*', '', title_text, flags=re.I).strip()
            # 清理多余的空白字符
            title = ' '.join(title.split())
        else:
            # 备用方法：查找包含 "Title:" 的span
            title_span = dd.find('span', class_='descriptor', string=re.compile('Title:', re.I))
            if title_span:
                parent = title_span.parent
                title = parent.get_text()
                title = re.sub(r'Title:\s*', '', title, flags=re.I).strip()
                title = ' '.join(title.split())
            else:
                continue
        
        if not title or len(title) < 5:
            continue
        
        paper['title'] = title
        
        # 查找作者 - 在 <div class="list-authors"> 中
        authors = []
        authors_div = dd.find('div', class_='list-authors')
        if authors_div:
            # 作者链接
            author_links = authors_div.find_all('a', href=re.compile(r'/search/'))
            if author_links:
                authors = [link.get_text(strip=True) for link in author_links]
            else:
                # 如果没有链接，尝试从文本中提取
                authors_text = authors_div.get_text()
                authors_text = re.sub(r'Authors?:\s*', '', authors_text, flags=re.I).strip()
                if authors_text:
                    # 分割作者（逗号分隔）
                    authors = [a.strip() for a in re.split(r',', authors_text) if a.strip()]
        
        paper['authors'] = authors
        papers.append(paper)
    
    return papers


def scrape_all_papers(base_url):
    """
    爬取所有页面的论文
    
    Args:
        base_url: 基础URL
    
    Returns:
        list: 所有论文的列表
    """
    all_papers = []
    session = requests.Session()
    
    # arXiv使用查询参数 ?skip= 和 ?show= 来分页，每页50条
    page = 1
    skip = 0  # 从0开始
    show = 50  # 每页显示50条
    
    print(f"正在爬取: {base_url}")
    
    while True:
        # 构建URL
        if skip == 0:
            url = base_url
        else:
            url = f"{base_url}?skip={skip}&show={show}"
        
        # 获取当前页面的论文
        papers = get_papers_from_page(url, session)
        
        if not papers:
            # 如果没有找到论文，说明已经到最后一页
            break
        
        all_papers.extend(papers)
        print(f"第{page}页 (skip={skip}): 找到 {len(papers)} 篇论文")
        
        # 如果这一页的论文少于50篇，说明是最后一页
        if len(papers) < 50:
            break
        
        # 准备下一页
        skip += 50
        page += 1
        time.sleep(1)  # 礼貌延迟，避免请求过快
    
    session.close()
    return all_papers


def save_papers(papers, output_file='papers.json', txt_file='papers.txt'):
    """
    保存论文到文件
    
    Args:
        papers: 论文列表
        output_file: JSON输出文件名
        txt_file: 文本输出文件名
    """
    # 保存为JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)
    
    # 保存为文本文件（只保存标题）
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(f"arXiv Robotics 论文标题列表\n")
        f.write(f"爬取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"总计: {len(papers)} 篇论文\n")
        f.write("=" * 80 + "\n\n")
        
        for i, paper in enumerate(papers, 1):
            f.write(f"{i}. {paper['title']}\n")
            if paper.get('arxiv_id'):
                f.write(f"   arXiv ID: {paper['arxiv_id']}\n")
            if paper.get('authors'):
                f.write(f"   作者: {', '.join(paper['authors'][:3])}")  # 只显示前3个作者
                if len(paper['authors']) > 3:
                    f.write(f" 等")
                f.write("\n")
            f.write("\n")
    
    print(f"\n结果已保存:")
    print(f"  - JSON格式: {output_file}")
    print(f"  - 文本格式: {txt_file}")


def main():
    """主函数"""
    base_url = "https://arxiv.org/list/cs.RO/recent"
    
    print("开始爬取 arXiv Robotics 论文...")
    print("=" * 80)
    
    papers = scrape_all_papers(base_url)
    
    print("=" * 80)
    print(f"爬取完成！共找到 {len(papers)} 篇论文")
    
    if papers:
        save_papers(papers)
    else:
        print("警告: 没有找到任何论文")


if __name__ == "__main__":
    main()

