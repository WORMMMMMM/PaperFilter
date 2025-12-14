#!/usr/bin/env python3
"""
终端交互界面：以卡片形式浏览 arXiv Robotics 论文列表

功能特性：
- 支持搜索标题 / 作者 / arXiv ID
- 支持翻页、跳页、调整单页数量
- 以 Rich 渲染卡片，展示标题、作者、arXiv 链接
"""

import io
import json
import math
import os
import re
import sys
import time
from argparse import ArgumentParser
from collections import deque
from typing import Dict, List, Optional, Tuple

import numpy as np
import requests
import torch
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from sentence_transformers import SentenceTransformer


EMBEDDINGS_FILE = "papers_embeddings.npy"
EMBEDDINGS_META_FILE = "papers_embeddings_meta.json"
SEMANTIC_MODEL_NAME = "intfloat/e5-large-v2"
RELATIONS_CACHE_FILE = "relations_cache.json"

console = Console()

# 全局缓存：arxiv_id -> [related_arxiv_ids]
relations_cache: Dict[str, List[str]] = {}


def load_papers(path: str) -> List[dict]:
    if not os.path.exists(path):
        console.print(f"[bold red]错误：找不到数据文件 {path}[/bold red]")
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_authors(authors: List[str], limit: int = 3) -> str:
    if not authors:
        return "未知作者"
    if len(authors) <= limit:
        return ", ".join(authors)
    return ", ".join(authors[:limit]) + " 等"


def filter_papers(papers: List[dict], query: str) -> List[dict]:
    if not query:
        return papers
    query = query.lower()
    filtered = []
    for paper in papers:
        title = paper.get("title", "").lower()
        authors = " ".join(paper.get("authors", [])).lower()
        arxiv_id = paper.get("arxiv_id", "").lower()
        if query in title or query in authors or query in arxiv_id:
            filtered.append(paper)
    return filtered


def paginate(papers: List[dict], page: int, page_size: int) -> Tuple[List[dict], int]:
    if not papers:
        return [], 1
    total_pages = max(1, math.ceil(len(papers) / page_size))
    page = max(1, min(page, total_pages))
    start = (page - 1) * page_size
    end = start + page_size
    return papers[start:end], total_pages


def render_page(
    papers: List[dict],
    page: int,
    page_size: int,
    query: str,
    mode: str,
    score_lookup: Optional[Dict[str, float]] = None,
):
    os.system("clear")
    console.print(Text("📚 arXiv Robotics 论文浏览器 (终端版)", style="bold magenta"))
    
    # 模式显示 - 更醒目的样式
    if mode == "semantic":
        mode_display = "[bold green]🔍 语义搜索模式[/bold green]"
        mode_desc = "[dim]（理解语义，支持自然语言查询）[/dim]"
    else:
        mode_display = "[bold blue]🔎 关键字搜索模式[/bold blue]"
        mode_desc = "[dim]（精确匹配字符串）[/dim]"
    
    # 状态栏
    status_panel = Panel(
        f"{mode_display} {mode_desc}\n"
        f"共 [bold]{len(papers)}[/bold] 篇匹配结果 | "
        f"当前查询: [bold cyan]{query or '（无）'}[/bold cyan]",
        border_style="bright_blue" if mode == "keyword" else "bright_green",
        title="状态",
        title_align="left",
    )
    console.print(status_panel)
    page_data, total_pages = paginate(papers, page, page_size)

    console.print(
        f"\n第 [bold green]{page}[/bold green] / {total_pages} 页 "
        f"(每页 {page_size} 篇)\n"
    )

    if not page_data:
        console.print("[yellow]没有匹配的论文，请尝试其他搜索关键词。[/yellow]")
        return total_pages

    table = Table(
        show_header=True,
        header_style="bold bright_white",
        box=box.SIMPLE_HEAD,
        expand=True,
    )
    table.add_column("序号", width=4)
    table.add_column("标题", overflow="fold")
    table.add_column("作者", overflow="fold", style="cyan")
    if score_lookup:
        table.add_column("相似度", width=8, style="yellow")
    table.add_column("arXiv ID", width=12, style="magenta")
    table.add_column("链接", style="green")

    start_index = (page - 1) * page_size
    for idx, paper in enumerate(page_data, start=1):
        title = paper.get("title", "无标题")
        authors = format_authors(paper.get("authors", []))
        arxiv_id = paper.get("arxiv_id", "未知")
        abs_url = f"https://arxiv.org/abs/{arxiv_id}"
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        links = f"[链接1] 摘要: {abs_url}\n[链接2] PDF : {pdf_url}"

        panel = Panel(
            Text(title, style="bold"),
            subtitle=f"arXiv: {arxiv_id}",
            border_style="bright_blue",
        )
        row = [
            str(start_index + idx),
            panel,
            authors,
        ]
        if score_lookup:
            score = score_lookup.get(arxiv_id)
            row.append(f"{score:.3f}" if score is not None else "-")
        row.extend([arxiv_id, links])
        table.add_row(*row)

    console.print(table)
    console.print(
        "\n指令："
        "[bold green]n[/bold green]/[bold green]next[/bold green] 下一页 | "
        "[bold green]p[/bold green]/[bold green]prev[/bold green] 上一页 | "
        "[bold green]s <关键词>[/bold green] 搜索 | "
        "[bold green]c[/bold green] 清除搜索 | "
        "[bold green]g <页码>[/bold green] 跳转 | "
        "[bold green]size <数量>[/bold green] 调整每页篇数 | "
        "[bold green]mode <keyword|semantic>[/bold green] 切换搜索模式 | "
        "[bold green]graph <标题>[/bold green] 生成引用关系图 | "
        "[bold green]q[/bold green] 退出"
    )

    return total_pages


def parse_args():
    parser = ArgumentParser(description="终端论文浏览器")
    parser.add_argument(
        "-f",
        "--file",
        default="papers.json",
        help="论文 JSON 数据文件路径 (默认: papers.json)",
    )
    parser.add_argument(
        "-p",
        "--page-size",
        type=int,
        default=8,
        help="每页显示的论文数量 (默认: 8)",
    )
    return parser.parse_args()


class SemanticEngine:
    def __init__(
        self,
        embeddings_path: str,
        metadata_path: str,
        model_name: str = SEMANTIC_MODEL_NAME,
    ):
        self.embeddings_path = embeddings_path
        self.metadata_path = metadata_path
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.embeddings: Optional[np.ndarray] = None
        self.paper_ids: Optional[List[str]] = None
        self.model: Optional[SentenceTransformer] = None
        self.available = os.path.exists(embeddings_path) and os.path.exists(
            metadata_path
        )

    def _load_embeddings(self, papers_by_id: Dict[str, dict]):
        embeddings = np.load(self.embeddings_path)
        with open(self.metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        paper_ids = []
        valid_vectors = []
        for idx, meta in enumerate(metadata):
            arxiv_id = meta.get("arxiv_id")
            if not arxiv_id or arxiv_id not in papers_by_id:
                continue
            paper_ids.append(arxiv_id)
            valid_vectors.append(embeddings[idx])

        if not valid_vectors:
            raise RuntimeError("嵌入文件与论文数据不匹配，请重新生成向量。")

        self.embeddings = np.vstack(valid_vectors)
        self.paper_ids = paper_ids

    def ensure_ready(self, papers_by_id: Dict[str, dict]):
        if not self.available:
            raise RuntimeError("未找到嵌入文件，请先运行 generate_embeddings.py")
        if self.embeddings is None or self.paper_ids is None:
            self._load_embeddings(papers_by_id)
        if self.model is None:
            console.print(
                f"[cyan]加载语义模型 {self.model_name} (device={self.device}) ...[/cyan]"
            )
            self.model = SentenceTransformer(self.model_name, device=self.device)

    def search(self, query: str, papers_by_id: Dict[str, dict]):
        self.ensure_ready(papers_by_id)
        query = query.strip()
        if not query:
            return [], {}

        query_emb = self.model.encode(
            [f"query: {query}"],
            convert_to_numpy=True,
            normalize_embeddings=True,
        )[0]

        scores = np.dot(self.embeddings, query_emb)
        order = np.argsort(-scores)

        results = []
        score_lookup: Dict[str, float] = {}
        for idx in order:
            arxiv_id = self.paper_ids[idx]
            paper = papers_by_id.get(arxiv_id)
            if paper:
                score = float(scores[idx])
                results.append(paper)
                score_lookup[arxiv_id] = score

        return results, score_lookup


def load_relations_cache():
    """加载引用关系缓存"""
    global relations_cache
    if os.path.exists(RELATIONS_CACHE_FILE):
        try:
            with open(RELATIONS_CACHE_FILE, "r", encoding="utf-8") as f:
                relations_cache = json.load(f)
        except Exception:
            relations_cache = {}


def save_relations_cache():
    """保存引用关系缓存"""
    try:
        with open(RELATIONS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(relations_cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_references_from_pdf(arxiv_id: str) -> List[str]:
    """
    从PDF末尾提取References中的arXiv ID
    
    Args:
        arxiv_id: arXiv ID
    
    Returns:
        List[str]: 引用的arXiv ID列表
    """
    references = []
    try:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(pdf_url, headers=headers, timeout=15, stream=True)
        response.raise_for_status()
        
        # 读取PDF
        pdf_file = io.BytesIO(response.content)
        reader = PdfReader(pdf_file)
        
        # 提取最后几页的文本（references通常在末尾）
        # 根据PDF长度决定提取页数
        num_pages = len(reader.pages)
        pages_to_extract = min(5, max(2, num_pages // 4))  # 提取最后2-5页
        
        ref_text = ''
        for i in range(max(0, num_pages - pages_to_extract), num_pages):
            page = reader.pages[i]
            ref_text += page.extract_text() + '\n'
        
        # 查找arXiv ID的模式
        patterns = [
            r'arxiv[:\s]+(\d{4}\.\d{4,5})',  # arXiv: xxxx.xxxxx 或 arXiv xxxx.xxxxx
            r'arxiv\.org/abs/(\d{4}\.\d{4,5})',  # arxiv.org/abs/xxxx.xxxxx
            r'\[(\d{4}\.\d{4,5})\]',  # [xxxx.xxxxx] 格式
        ]
        
        found_ids = set()
        for pattern in patterns:
            matches = re.findall(pattern, ref_text, re.IGNORECASE)
            for match in matches:
                # 移除版本号
                clean_id = str(match).split('v')[0]
                found_ids.add(clean_id)
        
        references = list(found_ids)
        
    except Exception as e:
        console.print(f"[dim]从PDF提取 {arxiv_id} 的引用失败: {e}[/dim]")
    
    return references


def get_references(arxiv_id: str, session: Optional[requests.Session] = None) -> List[str]:
    """
    获取论文的References（引用列表）
    优先从PDF提取，失败则使用Semantic Scholar API
    
    Args:
        arxiv_id: arXiv ID
        session: requests session对象（未使用，保留兼容性）
    
    Returns:
        List[str]: 引用的arXiv ID列表
    """
    global relations_cache
    
    # 检查缓存
    if arxiv_id in relations_cache:
        return relations_cache[arxiv_id]
    
    references = []
    
    # 方法1: 从PDF提取（优先）
    references = get_references_from_pdf(arxiv_id)
    
    # 方法2: 如果PDF方法失败，尝试Semantic Scholar API
    if len(references) == 0:
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/arXiv:{arxiv_id}"
            params = {
                'fields': 'references.externalIds,references.paperId'
            }
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # 提取有arXiv ID的references
            refs = data.get('references', [])
            if refs:
                semantic_refs = []
                for ref in refs:
                    if not ref:
                        continue
                    external_ids = ref.get('externalIds') if ref else None
                    if external_ids:
                        ref_arxiv_id = external_ids.get('ArXiv')
                        if ref_arxiv_id:
                            ref_arxiv_id = str(ref_arxiv_id).split('v')[0]
                            if ref_arxiv_id not in semantic_refs:
                                semantic_refs.append(ref_arxiv_id)
                
                # 合并结果（去重）
                for ref_id in semantic_refs:
                    if ref_id not in references:
                        references.append(ref_id)
            
            time.sleep(0.1)  # 礼貌延迟
            
        except Exception as e:
            console.print(f"[dim]Semantic Scholar API失败: {e}[/dim]")
    
    # 缓存结果
    relations_cache[arxiv_id] = references
    
    return references


def build_citation_graph(
    start_arxiv_id: str,
    papers_by_id: Dict[str, dict],
    max_depth: int = 5,
    max_per_level: int = 20,
) -> Dict[str, Dict]:
    """
    递归构建引用关系图
    
    Args:
        start_arxiv_id: 起始论文的arXiv ID
        papers_by_id: 论文ID到论文信息的映射
        max_depth: 最大递归深度
        max_per_level: 每层最大论文数量
    
    Returns:
        Dict: {
            'nodes': {arxiv_id: paper_info},
            'edges': [(parent_id, child_id), ...],
            'levels': {arxiv_id: level}
        }
    """
    graph = {
        'nodes': {},
        'edges': [],
        'levels': {}
    }
    
    session = requests.Session()
    visited = set()
    queue = deque([(start_arxiv_id, 0)])  # (arxiv_id, level)
    visited.add(start_arxiv_id)
    
    # 添加起始节点
    if start_arxiv_id in papers_by_id:
        graph['nodes'][start_arxiv_id] = papers_by_id[start_arxiv_id]
        graph['levels'][start_arxiv_id] = 0
    
    console.print(f"[cyan]正在构建引用关系图（最大深度: {max_depth}）...[/cyan]")
    
    while queue:
        current_id, level = queue.popleft()
        
        if level >= max_depth:
            continue
        
        console.print(f"[dim]Level {level}: 处理 {current_id}...[/dim]")
        references = get_references(current_id, session)
        
        if not references:
            console.print(f"[dim]  {current_id} 没有找到references[/dim]")
            continue
        
        console.print(f"[dim]  找到 {len(references)} 个references[/dim]")
        
        # 限制每层数量
        added_count = 0
        for ref_id in references:
            if added_count >= max_per_level:
                break
            
            # 添加边
            if current_id not in graph['nodes'] or ref_id not in graph['nodes']:
                graph['edges'].append((current_id, ref_id))
            
            # 添加节点（如果在我们已知的论文列表中）
            if ref_id in papers_by_id:
                if ref_id not in graph['nodes']:
                    graph['nodes'][ref_id] = papers_by_id[ref_id]
                    graph['levels'][ref_id] = level + 1
                    queue.append((ref_id, level + 1))
                    visited.add(ref_id)
                    added_count += 1
            elif ref_id not in visited:
                # 即使不在我们的列表中，也记录为外部论文
                graph['nodes'][ref_id] = {
                    'arxiv_id': ref_id,
                    'title': f"[外部论文] {ref_id}",
                    'authors': []
                }
                graph['levels'][ref_id] = level + 1
                visited.add(ref_id)
                # 不继续递归外部论文
                added_count += 1
    
    session.close()
    save_relations_cache()
    return graph


def render_citation_tree(graph: Dict, start_arxiv_id: str, papers_by_id: Dict[str, dict]):
    """
    在终端渲染引用关系层级树
    
    Args:
        graph: 关系图数据
        start_arxiv_id: 起始论文ID
        papers_by_id: 论文ID到论文信息的映射
    """
    os.system("clear")
    console.print(Text("📊 论文引用关系图", style="bold magenta"))
    
    # 构建层级结构
    levels = graph['levels']
    edges = graph['edges']
    nodes = graph['nodes']
    
    # 按层级组织节点
    level_nodes: Dict[int, List[str]] = {}
    for node_id, level in levels.items():
        if level not in level_nodes:
            level_nodes[level] = []
        level_nodes[level].append(node_id)
    
    # 构建父子关系
    children_map: Dict[str, List[str]] = {}
    for parent, child in edges:
        if parent not in children_map:
            children_map[parent] = []
        children_map[parent].append(child)
    
    # 递归打印树（避免循环引用）
    def print_tree(node_id: str, prefix: str = "", is_last: bool = True, visited_in_path: set = None):
        if visited_in_path is None:
            visited_in_path = set()
        
        # 检查是否在当前路径中已访问（避免循环）
        if node_id in visited_in_path:
            console.print(f"{prefix}{'└── ' if is_last else '├── '}[dim][循环引用] {node_id}[/dim]")
            return
        
        visited_in_path = visited_in_path.copy()
        visited_in_path.add(node_id)
        
        node = nodes.get(node_id, {})
        title = node.get('title', f'[未知] {node_id}')
        arxiv_id = node.get('arxiv_id', node_id)
        
        # 截断过长的标题
        if len(title) > 60:
            title = title[:57] + "..."
        
        # 打印当前节点
        connector = "└── " if is_last else "├── "
        level = levels.get(node_id, 0)
        level_color = "green" if level == 0 else "yellow" if level <= 2 else "cyan"
        console.print(f"{prefix}{connector}[bold {level_color}][L{level}][/bold {level_color}] {title}")
        console.print(f"{prefix}{'    ' if is_last else '│   '}[dim]arXiv: {arxiv_id}[/dim]")
        
        # 打印子节点
        children = children_map.get(node_id, [])
        for i, child_id in enumerate(children):
            is_last_child = (i == len(children) - 1)
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(child_id, new_prefix, is_last_child, visited_in_path)
    
    # 从根节点开始打印
    console.print(f"\n[bold green]根节点:[/bold green]")
    start_node = nodes.get(start_arxiv_id, {})
    start_title = start_node.get('title', f'[未知] {start_arxiv_id}')
    console.print(f"[bold cyan]{start_title}[/bold cyan]")
    console.print(f"[dim]arXiv: {start_arxiv_id}[/dim]\n")
    
    console.print("[bold green]引用关系树:[/bold green]")
    visited = set()
    children = children_map.get(start_arxiv_id, [])
    for i, child_id in enumerate(children):
        is_last = (i == len(children) - 1)
        print_tree(child_id, "", is_last, visited)
    
    # 统计信息
    console.print(f"\n[bold]统计:[/bold]")
    console.print(f"  总节点数: {len(nodes)}")
    console.print(f"  总边数: {len(edges)}")
    console.print(f"  最大深度: {max(levels.values()) if levels else 0}")
    console.print(f"\n[dim]按任意键返回...[/dim]")


def find_paper_by_title(query: str, papers: List[dict]) -> Optional[dict]:
    """
    根据标题查找论文（支持模糊匹配）
    
    Args:
        query: 查询字符串
        papers: 论文列表
    
    Returns:
        匹配的论文，如果找到多个则返回第一个
    """
    query_lower = query.lower()
    matches = []
    
    for paper in papers:
        title = paper.get('title', '').lower()
        if query_lower in title or title in query_lower:
            matches.append(paper)
    
    if matches:
        return matches[0]
    return None


def main():
    args = parse_args()
    if args.page_size <= 0:
        console.print("[bold red]每页数量必须为正整数[/bold red]")
        sys.exit(1)

    # 加载引用关系缓存
    load_relations_cache()

    papers = load_papers(args.file)
    papers_by_id = {
        paper.get("arxiv_id"): paper for paper in papers if paper.get("arxiv_id")
    }
    semantic_engine = SemanticEngine(
        EMBEDDINGS_FILE,
        EMBEDDINGS_META_FILE,
        model_name=SEMANTIC_MODEL_NAME,
    )
    filtered = papers
    query = ""
    page = 1
    page_size = args.page_size
    search_mode = "keyword"
    score_lookup: Optional[Dict[str, float]] = None
    while True:
        total_pages = render_page(
            filtered,
            page,
            page_size,
            query,
            mode=search_mode,
            score_lookup=score_lookup,
        )
        # 命令提示符显示当前模式
        if search_mode == "semantic":
            prompt = "[bold cyan]命令[/bold cyan] [bold green][语义模式][/bold green] > "
        else:
            prompt = "[bold cyan]命令[/bold cyan] [bold blue][关键字模式][/bold blue] > "
        command = console.input(f"\n{prompt}").strip()

        if not command:
            continue
        cmd_lower = command.lower()

        if cmd_lower in {"q", "quit", "exit"}:
            console.print("\n[bold green]再见！[/bold green]")
            break
        elif cmd_lower in {"n", "next"}:
            if page < total_pages:
                page += 1
        elif cmd_lower in {"p", "prev", "previous"}:
            if page > 1:
                page -= 1
        elif cmd_lower.startswith("s "):
            query = command[2:].strip()
            if search_mode == "keyword":
                filtered = filter_papers(papers, query)
                score_lookup = None
            else:
                try:
                    filtered, score_lookup = semantic_engine.search(query, papers_by_id)
                except RuntimeError as exc:
                    console.print(f"[red]{exc}[/red]")
                    continue
            page = 1
        elif cmd_lower in {"c", "clear"}:
            query = ""
            filtered = papers
            score_lookup = None
            page = 1
        elif cmd_lower.startswith("g "):
            try:
                target = int(command.split()[1])
                if 1 <= target <= total_pages:
                    page = target
            except (IndexError, ValueError):
                pass
        elif cmd_lower.startswith("size "):
            try:
                new_size = int(command.split()[1])
                if new_size > 0:
                    page_size = new_size
                    page = 1
            except (IndexError, ValueError):
                pass
        elif cmd_lower.startswith("mode "):
            try:
                target = command.split()[1].lower()
            except IndexError:
                console.print("[yellow]用法: mode keyword 或 mode semantic[/yellow]")
                continue
            if target == "keyword":
                search_mode = "keyword"
                score_lookup = None
                console.print("[green]已切换到关键字模式[/green]")
            elif target == "semantic":
                if not semantic_engine.available:
                    console.print(
                        "[red]未找到语义嵌入文件，请先运行 generate_embeddings.py[/red]"
                    )
                else:
                    search_mode = "semantic"
                    console.print("[green]已切换到语义模式[/green]")
            else:
                console.print("[yellow]未知模式，可选 keyword 或 semantic[/yellow]")
        elif cmd_lower.startswith("graph "):
            title_query = command[6:].strip()
            if not title_query:
                console.print("[yellow]用法: graph <论文标题>[/yellow]")
                continue
            
            # 查找论文
            paper = find_paper_by_title(title_query, papers)
            if not paper:
                console.print(f"[red]未找到标题包含 '{title_query}' 的论文[/red]")
                continue
            
            arxiv_id = paper.get('arxiv_id')
            if not arxiv_id:
                console.print("[red]该论文没有arXiv ID[/red]")
                continue
            
            console.print(f"[cyan]找到论文: {paper.get('title')}[/cyan]")
            console.print(f"[cyan]arXiv ID: {arxiv_id}[/cyan]\n")
            
            try:
                # 构建引用关系图
                console.print("[cyan]正在从Semantic Scholar获取引用关系...[/cyan]")
                graph = build_citation_graph(arxiv_id, papers_by_id, max_depth=5, max_per_level=20)
                
                if not graph['nodes'] or len(graph['nodes']) == 1:
                    console.print("[yellow]未找到引用关系。可能原因：[/yellow]")
                    console.print("[yellow]  1. 论文太新，Semantic Scholar还未索引其references[/yellow]")
                    console.print("[yellow]  2. 论文的references中没有arXiv论文[/yellow]")
                    console.print("[yellow]  3. 网络连接问题[/yellow]")
                    console.input("\n[dim]按任意键返回...[/dim]")
                    continue
                
                # 渲染关系树
                render_citation_tree(graph, arxiv_id, papers_by_id)
                console.input()  # 等待用户按键
                
            except Exception as e:
                console.print(f"[red]生成关系图时出错: {e}[/red]")
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
        else:
            console.print("[yellow]未知命令，输入 n/p/s/g/size/mode/graph/q。[/yellow]")


if __name__ == "__main__":
    main()

