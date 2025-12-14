#!/usr/bin/env python3
"""
Flask Web应用主文件
提供论文抓取和搜索的API接口
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime
from utils.scraper import scrape_all_papers_with_abstracts
from utils.search import PaperSearchEngine

app = Flask(__name__)
CORS(app)

# 配置文件路径
DATA_DIR = 'data'
PAPERS_FILE = os.path.join(DATA_DIR, 'papers.json')
INDEX_FILE = os.path.join(DATA_DIR, 'index.faiss')
PAPERS_INDEX_FILE = os.path.join(DATA_DIR, 'papers_index.json')

# 确保数据目录存在
os.makedirs(DATA_DIR, exist_ok=True)

# 全局搜索引擎实例
search_engine = None


def init_search_engine():
    """初始化搜索引擎"""
    global search_engine
    if search_engine is None:
        search_engine = PaperSearchEngine()
        # 尝试加载已有索引
        if os.path.exists(INDEX_FILE) and os.path.exists(PAPERS_INDEX_FILE):
            search_engine.load_index(INDEX_FILE, PAPERS_INDEX_FILE)
        # 如果没有索引，尝试从papers.json构建
        elif os.path.exists(PAPERS_FILE):
            with open(PAPERS_FILE, 'r', encoding='utf-8') as f:
                papers = json.load(f)
            if papers:
                search_engine.build_index(papers)
                search_engine.save_index(INDEX_FILE, PAPERS_INDEX_FILE)


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/papers', methods=['GET'])
def get_papers():
    """获取所有论文列表"""
    if not os.path.exists(PAPERS_FILE):
        return jsonify({'papers': [], 'total': 0})
    
    try:
        with open(PAPERS_FILE, 'r', encoding='utf-8') as f:
            papers = json.load(f)
        return jsonify({
            'papers': papers,
            'total': len(papers)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/scrape', methods=['POST'])
def scrape_papers():
    """抓取论文"""
    try:
        data = request.get_json() or {}
        max_papers = data.get('max_papers', None)  # 可以限制抓取数量
        
        base_url = "https://arxiv.org/list/cs.RO/recent"
        
        # 开始抓取
        papers = scrape_all_papers_with_abstracts(base_url, max_papers=max_papers)
        
        # 保存论文数据
        with open(PAPERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(papers, f, ensure_ascii=False, indent=2)
        
        # 构建搜索索引
        global search_engine
        if search_engine is None:
            search_engine = PaperSearchEngine()
        search_engine.build_index(papers)
        search_engine.save_index(INDEX_FILE, PAPERS_INDEX_FILE)
        
        return jsonify({
            'success': True,
            'total': len(papers),
            'message': f'成功抓取 {len(papers)} 篇论文'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/search', methods=['POST'])
def search_papers():
    """AI搜索论文"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': '缺少查询参数'}), 400
        
        query = data['query'].strip()
        if not query:
            return jsonify({'error': '查询不能为空'}), 400
        
        top_k = data.get('top_k', 10)
        
        # 初始化搜索引擎
        init_search_engine()
        
        if search_engine is None or len(search_engine.papers) == 0:
            return jsonify({
                'error': '还没有论文数据，请先抓取论文',
                'results': []
            }), 400
        
        # 执行搜索
        results = search_engine.search(query, top_k=top_k)
        
        # 格式化结果
        formatted_results = []
        for paper, similarity in results:
            formatted_results.append({
                'paper': paper,
                'similarity': round(similarity, 4)
            })
        
        return jsonify({
            'success': True,
            'query': query,
            'results': formatted_results,
            'total': len(formatted_results)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """获取系统状态"""
    papers_count = 0
    if os.path.exists(PAPERS_FILE):
        try:
            with open(PAPERS_FILE, 'r', encoding='utf-8') as f:
                papers = json.load(f)
                papers_count = len(papers)
        except:
            pass
    
    has_index = os.path.exists(INDEX_FILE) and os.path.exists(PAPERS_INDEX_FILE)
    
    return jsonify({
        'papers_count': papers_count,
        'has_index': has_index,
        'search_ready': has_index and papers_count > 0
    })


if __name__ == '__main__':
    # 初始化搜索引擎
    init_search_engine()
    
    print("=" * 80)
    print("PaperFilter Web应用启动中...")
    print("=" * 80)
    print(f"访问 http://localhost:5000 查看界面")
    print("=" * 80)
    
    app.run(debug=True, host='0.0.0.0', port=5000)

