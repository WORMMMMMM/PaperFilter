#!/usr/bin/env python3
"""
从 Robotics.html 中提取论文链接和摘要
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
        # 访问摘要页面
        url = f"https://arxiv.org/abs/{arxiv_id}"
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找摘要 - 通常在 <blockquote class="abstract mathjax"> 中
        abstract_block = soup.find('blockquote', class_='abstract')
        if abstract_block:
            # 移除 "Abstract:" 标签
            abstract_text = abstract_block.get_text()
            abstract_text = re.sub(r'Abstract:\s*', '', abstract_text, flags=re.I).strip()
            return abstract_text
        
        # 备用方法：查找包含 "Abstract" 的 blockquote
        abstract_block = soup.find('blockquote', string=re.compile('Abstract', re.I))
        if abstract_block:
            abstract_text = abstract_block.get_text()
            abstract_text = re.sub(r'Abstract:\s*', '', abstract_text, flags=re.I).strip()
            return abstract_text
        
        return None
        
    except requests.RequestException as e:
        print(f"  获取摘要失败 ({arxiv_id}): {e}")
        return None


def extract_papers_from_html(html_file):
    """
    从 HTML 文件中提取论文信息
    
    Args:
        html_file: HTML 文件路径
    
    Returns:
        list: 包含论文信息的字典列表，每个字典包含:
            - arxiv_id: arXiv ID
            - title: 论文标题
            - html_link: HTML 链接（如果有）
            - abs_link: 摘要页面链接
    """
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    papers = []
    
    # 查找所有的 <dt> 标签（每个 <dt> 对应一篇论文）
    dt_tags = soup.find_all('dt')
    
    for dt in dt_tags:
        paper = {}
        
        # 查找 arXiv ID - 在 <dt> 中的链接
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
        
        # 查找 HTML 链接
        html_link_tag = dt.find('a', href=re.compile(r'https://arxiv.org/html/\d+\.\d+v\d+'))
        if html_link_tag:
            paper['html_link'] = html_link_tag.get('href', '')
        else:
            # 尝试查找相对路径的 HTML 链接
            html_link_tag = dt.find('a', href=re.compile(r'/html/\d+\.\d+'))
            if html_link_tag:
                href = html_link_tag.get('href', '')
                if href.startswith('/'):
                    paper['html_link'] = f"https://arxiv.org{href}"
                else:
                    paper['html_link'] = href
        
        # 查找对应的 <dd> - <dd> 紧跟在 <dt> 后面
        dd = dt.find_next_sibling('dd')
        if not dd:
            continue
        
        # 查找标题 - 在 <dd> 中的 <div class="list-title">
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
        papers.append(paper)
    
    return papers


def add_abstracts_to_html(html_file, output_file=None, txt_file=None):
    """
    从 HTML 文件中提取论文信息，获取摘要，并将摘要添加到 HTML 中，同时保存到 txt 文件
    
    Args:
        html_file: 输入的 HTML 文件路径
        output_file: 输出的 HTML 文件路径（如果为 None，则覆盖原文件）
        txt_file: 输出的 txt 文件路径（如果为 None，则不保存 txt）
    """
    print(f"正在从 {html_file} 提取论文信息...")
    papers = extract_papers_from_html(html_file)
    print(f"找到 {len(papers)} 篇论文")
    
    # 读取原始 HTML
    with open(html_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    session = requests.Session()
    
    # 用于保存到 txt 的数据列表
    papers_data = []
    
    # 为每篇论文添加摘要
    dt_tags = soup.find_all('dt')
    processed_count = 0
    
    for dt in dt_tags:
        # 查找 arXiv ID
        arxiv_link = dt.find('a', href=re.compile(r'/abs/\d+\.\d+'))
        if not arxiv_link:
            continue
            
        href = arxiv_link.get('href', '')
        match = re.search(r'/(\d+\.\d+)', href)
        if not match:
            continue
        
        arxiv_id = match.group(1)
        
        # 查找对应的 <dd>
        dd = dt.find_next_sibling('dd')
        if not dd:
            continue
        
        # 获取标题
        title_div = dd.find('div', class_='list-title')
        if not title_div:
            continue
        
        title_text = title_div.get_text()
        title = re.sub(r'Title:\s*', '', title_text, flags=re.I).strip()
        title = ' '.join(title.split())
        
        # 获取 HTML 链接
        html_link_tag = dt.find('a', href=re.compile(r'https://arxiv.org/html/\d+\.\d+v\d+'))
        html_link = None
        if html_link_tag:
            html_link = html_link_tag.get('href', '')
        else:
            html_link_tag = dt.find('a', href=re.compile(r'/html/\d+\.\d+'))
            if html_link_tag:
                href = html_link_tag.get('href', '')
                if href.startswith('/'):
                    html_link = f"https://arxiv.org{href}"
                else:
                    html_link = href
        
        # 检查是否已经有摘要（避免重复处理）
        existing_abstract = dd.find('div', class_='list-abstract')
        if existing_abstract:
            # 如果已有摘要，直接从 HTML 中提取
            abstract_text = existing_abstract.get_text()
            abstract = re.sub(r'Abstract:\s*', '', abstract_text, flags=re.I).strip()
        else:
            # 获取摘要
            print(f"正在获取摘要 [{processed_count + 1}/{len(papers)}]: {arxiv_id}")
            abstract = get_abstract(arxiv_id, session)
            
            if abstract:
                # 创建摘要 div
                abstract_div = soup.new_tag('div')
                abstract_div['class'] = 'list-abstract'
                descriptor_span = soup.new_tag('span')
                descriptor_span['class'] = 'descriptor'
                descriptor_span.string = 'Abstract:'
                abstract_div.append(descriptor_span)
                
                # 添加摘要文本（保留换行）
                abstract_text = soup.new_string(f" {abstract}")
                abstract_div.append(abstract_text)
                
                # 将摘要添加到 meta div 中（在 subjects 之前）
                meta_div = dd.find('div', class_='meta')
                if meta_div:
                    subjects_div = meta_div.find('div', class_='list-subjects')
                    if subjects_div:
                        meta_div.insert(meta_div.contents.index(subjects_div), abstract_div)
                    else:
                        meta_div.append(abstract_div)
                else:
                    dd.append(abstract_div)
        
        # 保存数据用于 txt 文件
        paper_data = {
            'title': title,
            'html_link': html_link or f"https://arxiv.org/html/{arxiv_id}v1",
            'abs_link': f"https://arxiv.org/abs/{arxiv_id}",
            'abstract': abstract if abstract else "（未获取到摘要）"
        }
        papers_data.append(paper_data)
        
        processed_count += 1
        if not existing_abstract:
            time.sleep(0.5)  # 礼貌延迟，避免请求过快
    
    session.close()
    
    # 保存修改后的 HTML
    if output_file is None:
        output_file = html_file
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(str(soup))
    
    print(f"\n处理完成！已更新 {output_file}")
    print(f"共处理 {processed_count} 篇论文")
    
    # 保存到 txt 文件
    if txt_file:
        save_to_txt(papers_data, txt_file)


def save_to_txt(papers_data, txt_file):
    """
    将论文数据保存到 txt 文件
    
    Args:
        papers_data: 论文数据列表，每个元素包含 title, html_link, abs_link, abstract
        txt_file: 输出的 txt 文件路径
    """
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("arXiv Robotics 论文信息汇总\n")
        f.write("=" * 80 + "\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"总计: {len(papers_data)} 篇论文\n")
        f.write("=" * 80 + "\n\n")
        
        for i, paper in enumerate(papers_data, 1):
            f.write(f"[{i}] {paper['title']}\n")
            f.write("-" * 80 + "\n")
            
            # 链接信息
            if paper['html_link']:
                f.write(f"HTML链接: {paper['html_link']}\n")
            f.write(f"摘要页面: {paper['abs_link']}\n")
            
            # 摘要内容
            f.write(f"\n摘要:\n{paper['abstract']}\n")
            f.write("\n" + "=" * 80 + "\n\n")
    
    print(f"结果已保存到: {txt_file}")


def main():
    """主函数"""
    html_file = 'Robotics.html'
    output_file = 'Robotics_with_abstracts.html'
    txt_file = 'papers_with_abstracts.txt'
    
    print("=" * 80)
    print("开始提取论文链接和摘要...")
    print("=" * 80)
    
    add_abstracts_to_html(html_file, output_file, txt_file)
    
    print("=" * 80)
    print("完成！")


if __name__ == "__main__":
    main()

