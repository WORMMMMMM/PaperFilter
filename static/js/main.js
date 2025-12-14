// API基础URL
const API_BASE = '';

// DOM元素
const scrapeBtn = document.getElementById('scrapeBtn');
const searchBtn = document.getElementById('searchBtn');
const searchInput = document.getElementById('searchInput');
const scrapeStatus = document.getElementById('scrapeStatus');
const searchStatus = document.getElementById('searchStatus');
const papersContainer = document.getElementById('papersContainer');
const loading = document.getElementById('loading');
const paperCount = document.getElementById('paperCount');
const searchReady = document.getElementById('searchReady');

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    checkStatus();
    loadPapers();
    
    // 绑定事件
    scrapeBtn.addEventListener('click', handleScrape);
    searchBtn.addEventListener('click', handleSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSearch();
        }
    });
});

// 检查系统状态
async function checkStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/status`);
        const data = await response.json();
        
        paperCount.textContent = `论文数量: ${data.papers_count}`;
        
        if (data.search_ready) {
            searchReady.textContent = '搜索已就绪';
            searchReady.classList.add('ready');
            searchInput.disabled = false;
            searchBtn.disabled = false;
        } else {
            searchReady.textContent = '搜索未就绪';
            searchReady.classList.remove('ready');
            searchInput.disabled = true;
            searchBtn.disabled = true;
        }
    } catch (error) {
        console.error('检查状态失败:', error);
    }
}

// 加载所有论文
async function loadPapers() {
    try {
        const response = await fetch(`${API_BASE}/api/papers`);
        const data = await response.json();
        
        if (data.papers && data.papers.length > 0) {
            displayPapers(data.papers);
        }
    } catch (error) {
        console.error('加载论文失败:', error);
    }
}

// 抓取论文
async function handleScrape() {
    scrapeBtn.disabled = true;
    scrapeBtn.querySelector('.btn-text').textContent = '抓取中...';
    scrapeStatus.textContent = '正在抓取论文，请稍候...';
    scrapeStatus.className = 'status info';
    loading.classList.remove('hidden');
    papersContainer.innerHTML = '';
    
    try {
        const response = await fetch(`${API_BASE}/api/scrape`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        });
        
        const data = await response.json();
        
        if (data.success) {
            scrapeStatus.textContent = data.message;
            scrapeStatus.className = 'status success';
            
            // 重新加载论文和更新状态
            await checkStatus();
            await loadPapers();
        } else {
            scrapeStatus.textContent = `错误: ${data.error}`;
            scrapeStatus.className = 'status error';
        }
    } catch (error) {
        scrapeStatus.textContent = `请求失败: ${error.message}`;
        scrapeStatus.className = 'status error';
    } finally {
        scrapeBtn.disabled = false;
        scrapeBtn.querySelector('.btn-text').textContent = '抓取论文';
        loading.classList.add('hidden');
    }
}

// 搜索论文
async function handleSearch() {
    const query = searchInput.value.trim();
    
    if (!query) {
        searchStatus.textContent = '请输入搜索关键词';
        searchStatus.className = 'status error';
        return;
    }
    
    searchBtn.disabled = true;
    searchStatus.textContent = `正在搜索: "${query}"...`;
    searchStatus.className = 'status info';
    loading.classList.remove('hidden');
    papersContainer.innerHTML = '';
    
    try {
        const response = await fetch(`${API_BASE}/api/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                top_k: 20
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (data.results && data.results.length > 0) {
                const papers = data.results.map(r => r.paper);
                displayPapers(papers, data.results);
                searchStatus.textContent = `找到 ${data.total} 篇相关论文`;
                searchStatus.className = 'status success';
            } else {
                papersContainer.innerHTML = '<div class="empty-state"><p>未找到相关论文，请尝试其他关键词</p></div>';
                searchStatus.textContent = '未找到相关论文';
                searchStatus.className = 'status info';
            }
        } else {
            searchStatus.textContent = `错误: ${data.error}`;
            searchStatus.className = 'status error';
            papersContainer.innerHTML = '<div class="empty-state"><p>搜索失败，请重试</p></div>';
        }
    } catch (error) {
        searchStatus.textContent = `请求失败: ${error.message}`;
        searchStatus.className = 'status error';
        papersContainer.innerHTML = '<div class="empty-state"><p>搜索失败，请检查网络连接</p></div>';
    } finally {
        searchBtn.disabled = false;
        loading.classList.add('hidden');
    }
}

// 显示论文卡片
function displayPapers(papers, searchResults = null) {
    if (!papers || papers.length === 0) {
        papersContainer.innerHTML = '<div class="empty-state"><p>暂无论文数据</p></div>';
        return;
    }
    
    papersContainer.innerHTML = '';
    
    papers.forEach((paper, index) => {
        const card = createPaperCard(paper, searchResults ? searchResults[index] : null);
        papersContainer.appendChild(card);
    });
}

// 创建论文卡片
function createPaperCard(paper, searchResult = null) {
    const card = document.createElement('div');
    card.className = 'paper-card';
    
    if (searchResult) {
        card.classList.add('highlight');
    }
    
    const title = paper.title || '（无标题）';
    const abstract = paper.abstract || '（无摘要）';
    const htmlLink = paper.html_link || '';
    const absLink = paper.abs_link || '';
    
    let similarityBadge = '';
    if (searchResult && searchResult.similarity) {
        const similarity = (searchResult.similarity * 100).toFixed(1);
        similarityBadge = `<span class="similarity-score">相似度: ${similarity}%</span>`;
    }
    
    card.innerHTML = `
        <div class="paper-title">
            <a href="${absLink}" target="_blank">${title}</a>
        </div>
        <div class="paper-abstract">${abstract}</div>
        <div class="paper-links">
            ${htmlLink ? `<a href="${htmlLink}" target="_blank" class="paper-link">📄 HTML版本</a>` : ''}
            ${absLink ? `<a href="${absLink}" target="_blank" class="paper-link">📑 摘要页面</a>` : ''}
        </div>
        <div class="paper-meta">
            <span>arXiv ID: ${paper.arxiv_id || 'N/A'}</span>
            ${similarityBadge}
        </div>
    `;
    
    return card;
}

