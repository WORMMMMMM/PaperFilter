#!/usr/bin/env python3
"""
arXiv AI 论文助手
智能搜索、分析和筛选arXiv论文
"""

from flask import Flask, render_template, jsonify, request, Response
from flask_cors import CORS
import json
import os
from datetime import datetime
from utils.arxiv_search import ArxivSearcher
from utils.glm_client import GLMClient
from config import DEFAULT_MAX_RESULTS, DEFAULT_TOP_RELEVANT

app = Flask(__name__)
CORS(app)

# 数据目录
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

# 全局实例
arxiv_searcher = ArxivSearcher()
glm_client = GLMClient()


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/search', methods=['POST'])
def search_papers():
    """
    搜索并筛选论文的主接口
    
    请求参数:
        query: 搜索主题/关键词（必需）
        max_results: 最大搜索结果数（可选，默认50）
        top_k: 筛选后返回的论文数（可选，默认10）
        auto_keywords: 是否自动生成关键词（可选，默认True）
    
    返回:
        搜索结果、筛选后的论文、研究总结
    """
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': '请提供搜索主题'}), 400
        
        query = data['query'].strip()
        if not query:
            return jsonify({'error': '搜索主题不能为空'}), 400
        
        max_results = data.get('max_results', DEFAULT_MAX_RESULTS)
        top_k = data.get('top_k', DEFAULT_TOP_RELEVANT)
        auto_keywords = data.get('auto_keywords', True)
        
        result = {
            'query': query,
            'keywords': [query],
            'total_found': 0,
            'papers': [],
            'filtered_papers': [],
            'summary': ''
        }
        
        # 第一步：生成搜索关键词
        if auto_keywords:
            keywords = glm_client.generate_search_keywords(query)
            result['keywords'] = keywords
        else:
            keywords = [query]
        
        # 第二步：搜索论文
        if len(keywords) > 1:
            papers = arxiv_searcher.search_multiple_keywords(
                keywords, 
                max_results_per_keyword=max_results // len(keywords)
            )
        else:
            papers = arxiv_searcher.search(keywords[0], max_results=max_results)
        
        result['total_found'] = len(papers)
        result['papers'] = papers
        
        if not papers:
            return jsonify({
                'success': True,
                **result,
                'message': '未找到相关论文，请尝试其他关键词'
            })
        
        # 第三步：AI筛选相关论文
        filtered = glm_client.analyze_relevance(query, papers, top_k=top_k)
        result['filtered_papers'] = filtered
        
        # 第四步：生成研究总结
        if filtered:
            summary = glm_client.summarize_research_direction(query, filtered)
            result['summary'] = summary
        
        # 保存搜索结果
        save_path = os.path.join(DATA_DIR, 'last_search.json')
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            **result,
            'message': f'找到 {len(papers)} 篇论文，筛选出 {len(filtered)} 篇最相关的'
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/quick_search', methods=['POST'])
def quick_search():
    """
    快速搜索（不使用AI筛选）
    
    适用于想要直接浏览所有结果的情况
    """
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': '请提供搜索关键词'}), 400
        
        query = data['query'].strip()
        max_results = data.get('max_results', 30)
        
        papers = arxiv_searcher.search(query, max_results=max_results)
        
        return jsonify({
            'success': True,
            'query': query,
            'papers': papers,
            'total': len(papers)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/analyze', methods=['POST'])
def analyze_papers():
    """
    对已有论文列表进行AI分析
    
    用于对之前搜索的结果重新筛选
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '请提供数据'}), 400
        
        query = data.get('query', '')
        papers = data.get('papers', [])
        top_k = data.get('top_k', DEFAULT_TOP_RELEVANT)
        
        if not papers:
            return jsonify({'error': '没有论文数据'}), 400
        
        # AI筛选
        filtered = glm_client.analyze_relevance(query, papers, top_k=top_k)
        
        # 生成总结
        summary = ''
        if filtered:
            summary = glm_client.summarize_research_direction(query, filtered)
        
        return jsonify({
            'success': True,
            'filtered_papers': filtered,
            'summary': summary
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/generate_keywords', methods=['POST'])
def generate_keywords():
    """
    生成搜索关键词
    
    根据用户描述的研究兴趣生成适合arXiv搜索的关键词
    """
    try:
        data = request.get_json()
        if not data or 'input' not in data:
            return jsonify({'error': '请提供输入'}), 400
        
        user_input = data['input'].strip()
        if not user_input:
            return jsonify({'error': '输入不能为空'}), 400
        
        keywords = glm_client.generate_search_keywords(user_input)
        
        return jsonify({
            'success': True,
            'keywords': keywords
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/history', methods=['GET'])
def get_history():
    """获取上次搜索结果"""
    try:
        history_path = os.path.join(DATA_DIR, 'last_search.json')
        if os.path.exists(history_path):
            with open(history_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify({
                'success': True,
                'data': data
            })
        else:
            return jsonify({
                'success': True,
                'data': None,
                'message': '没有历史记录'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/status', methods=['GET'])
def get_status():
    """获取系统状态"""
    return jsonify({
        'status': 'running',
        'version': '2.0',
        'features': ['智能搜索', 'AI关键词生成', 'AI论文筛选', '研究方向总结']
    })


if __name__ == '__main__':
    print("=" * 80)
    print("🔬 arXiv AI 论文助手 v2.0")
    print("=" * 80)
    print("功能：")
    print("  1. 智能搜索 - 输入研究主题，自动生成关键词搜索")
    print("  2. AI筛选 - 使用GLM-4分析论文相关性")
    print("  3. 研究总结 - 自动生成研究方向建议")
    print("=" * 80)
    print(f"访问 http://localhost:5000 开始使用")
    print("=" * 80)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
