#!/usr/bin/env python3
"""
生成论文卡片展示界面HTML文件
"""

import json

# 读取论文数据
with open('papers.json', 'r', encoding='utf-8') as f:
    papers = json.load(f)

# 生成HTML内容
html_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>arXiv Robotics 论文卡片展示</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }

        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .search-box {
            background: white;
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }

        .search-box input {
            flex: 1;
            min-width: 200px;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }

        .search-box input:focus {
            outline: none;
            border-color: #667eea;
        }

        .stats {
            color: #666;
            font-size: 14px;
        }

        .papers-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .paper-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
            display: flex;
            flex-direction: column;
        }

        .paper-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 15px rgba(0,0,0,0.2);
        }

        .paper-title {
            font-size: 1.1em;
            font-weight: 600;
            color: #333;
            margin-bottom: 12px;
            line-height: 1.4;
            flex-grow: 1;
        }

        .paper-authors {
            font-size: 0.9em;
            color: #666;
            margin-bottom: 15px;
            line-height: 1.5;
        }

        .paper-authors strong {
            color: #555;
        }

        .paper-id {
            font-size: 0.85em;
            color: #888;
            margin-bottom: 15px;
            font-family: 'Courier New', monospace;
        }

        .paper-links {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .paper-link {
            display: inline-block;
            padding: 8px 16px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-size: 0.9em;
            transition: opacity 0.3s;
            font-weight: 500;
        }

        .paper-link:hover {
            opacity: 0.9;
        }

        .paper-link.abstract-link {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }

        .no-results {
            text-align: center;
            color: white;
            font-size: 1.2em;
            padding: 40px;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
        }

        @media (max-width: 768px) {
            .papers-grid {
                grid-template-columns: 1fr;
            }

            .header h1 {
                font-size: 2em;
            }

            .search-box {
                flex-direction: column;
                align-items: stretch;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 arXiv Robotics 论文集合</h1>
            <p>共 <span id="total-count">0</span> 篇论文</p>
        </div>

        <div class="search-box">
            <input type="text" id="search-input" placeholder="搜索论文标题、作者或arXiv ID...">
            <div class="stats">
                显示 <span id="display-count">0</span> / <span id="total-display">0</span> 篇
            </div>
        </div>

        <div id="papers-container" class="papers-grid">
            <!-- 论文卡片将在这里动态生成 -->
        </div>
    </div>

    <script>
        // 论文数据
        const papersData = ''' + json.dumps(papers, ensure_ascii=False, indent=2) + ''';
        
        let filteredPapers = papersData;

        // 初始化
        document.addEventListener('DOMContentLoaded', function() {
            document.getElementById('total-count').textContent = papersData.length;
            document.getElementById('total-display').textContent = papersData.length;
            renderPapers(papersData);

            // 搜索功能
            const searchInput = document.getElementById('search-input');
            searchInput.addEventListener('input', function(e) {
                const query = e.target.value.toLowerCase().trim();
                if (query === '') {
                    filteredPapers = papersData;
                } else {
                    filteredPapers = papersData.filter(paper => {
                        const title = paper.title.toLowerCase();
                        const authors = paper.authors.join(' ').toLowerCase();
                        const arxivId = paper.arxiv_id.toLowerCase();
                        return title.includes(query) || authors.includes(query) || arxivId.includes(query);
                    });
                }
                renderPapers(filteredPapers);
            });
        });

        function renderPapers(papers) {
            const container = document.getElementById('papers-container');
            const displayCount = document.getElementById('display-count');
            
            displayCount.textContent = papers.length;

            if (papers.length === 0) {
                container.innerHTML = '<div class="no-results">未找到匹配的论文</div>';
                return;
            }

            container.innerHTML = papers.map(paper => {
                const authorsText = paper.authors.length > 0 
                    ? paper.authors.slice(0, 3).join(', ') + (paper.authors.length > 3 ? ' 等' : '')
                    : '未知作者';
                const arxivUrl = `https://arxiv.org/abs/${paper.arxiv_id}`;
                const pdfUrl = `https://arxiv.org/pdf/${paper.arxiv_id}.pdf`;

                return `
                    <div class="paper-card">
                        <div class="paper-title">${escapeHtml(paper.title)}</div>
                        <div class="paper-authors">
                            <strong>作者:</strong> ${escapeHtml(authorsText)}
                        </div>
                        <div class="paper-id">arXiv: ${paper.arxiv_id}</div>
                        <div class="paper-links">
                            <a href="${arxivUrl}" target="_blank" class="paper-link abstract-link">查看摘要</a>
                            <a href="${pdfUrl}" target="_blank" class="paper-link">下载PDF</a>
                        </div>
                    </div>
                `;
            }).join('');

            // 更新显示数量
            document.getElementById('total-display').textContent = papersData.length;
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
'''

# 保存HTML文件
with open('papers_viewer.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ 已生成 papers_viewer.html 文件，包含 {len(papers)} 篇论文")
print("📖 可以直接用浏览器打开该文件查看！")

