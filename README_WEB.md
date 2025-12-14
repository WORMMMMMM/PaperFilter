# PaperFilter Web应用使用指南

## 功能特性

- 🔍 **一键抓取论文**: 点击按钮自动抓取arXiv Robotics分类的最新论文
- 📄 **卡片式展示**: 美观的卡片界面展示论文标题、链接和摘要
- 🤖 **AI语义搜索**: 使用sentence-transformers实现智能语义搜索，支持中英文查询
- 💾 **本地索引**: 使用FAISS构建高效的向量搜索索引

## 安装步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

**注意**: 
- `sentence-transformers` 首次运行时会自动下载模型（约400MB）
- `faiss-cpu` 是CPU版本的FAISS，如果需要GPU加速可以安装 `faiss-gpu`

### 2. 运行应用

```bash
python app.py
```

应用将在 `http://localhost:5000` 启动

## 使用方法

### 抓取论文

1. 打开浏览器访问 `http://localhost:5000`
2. 点击"抓取论文"按钮
3. 等待抓取完成（首次抓取可能需要几分钟）
4. 论文数据会自动保存到 `data/papers.json`
5. 搜索索引会自动构建并保存到 `data/index.faiss`

### 搜索论文

1. 在搜索框中输入关键词，例如：
   - `diffusion` - 查找与扩散模型相关的论文
   - `reinforcement learning` - 查找强化学习相关论文
   - `manipulation` - 查找机器人操作相关论文
   - `帮我找一下和diffusion相关的论文` - 中文查询也支持
2. 点击"搜索"按钮或按Enter键
3. 查看搜索结果，每张卡片显示相似度分数

## 项目结构

```
PaperFilter/
├── app.py                      # Flask主应用
├── templates/
│   └── index.html              # 前端HTML界面
├── static/
│   ├── css/
│   │   └── style.css          # 样式文件
│   └── js/
│       └── main.js            # 前端JavaScript逻辑
├── utils/
│   ├── scraper.py             # 论文爬取模块
│   └── search.py              # 语义搜索模块
├── data/                      # 数据目录（自动创建）
│   ├── papers.json            # 论文数据
│   ├── index.faiss            # FAISS搜索索引
│   └── papers_index.json      # 索引对应的论文数据
└── requirements.txt            # Python依赖
```

## API接口

### GET `/api/papers`
获取所有论文列表

**响应**:
```json
{
  "papers": [...],
  "total": 50
}
```

### POST `/api/scrape`
抓取论文

**请求体**:
```json
{
  "max_papers": 50  // 可选，限制抓取数量
}
```

**响应**:
```json
{
  "success": true,
  "total": 50,
  "message": "成功抓取 50 篇论文"
}
```

### POST `/api/search`
搜索论文

**请求体**:
```json
{
  "query": "diffusion",
  "top_k": 10  // 可选，默认10
}
```

**响应**:
```json
{
  "success": true,
  "query": "diffusion",
  "results": [
    {
      "paper": {...},
      "similarity": 0.8523
    }
  ],
  "total": 10
}
```

### GET `/api/status`
获取系统状态

**响应**:
```json
{
  "papers_count": 50,
  "has_index": true,
  "search_ready": true
}
```

## 技术说明

### 语义搜索原理

1. **文本向量化**: 使用 `sentence-transformers` 的多语言模型将论文标题和摘要转换为384维向量
2. **索引构建**: 使用FAISS构建L2距离索引，支持快速相似度搜索
3. **搜索过程**: 
   - 将用户查询转换为向量
   - 在FAISS索引中搜索最相似的论文向量
   - 返回相似度分数和论文信息

### 模型选择

默认使用 `paraphrase-multilingual-MiniLM-L12-v2` 模型：
- 支持中英文
- 模型较小，速度快
- 适合语义搜索任务

如需更换模型，修改 `utils/search.py` 中的 `model_name` 参数。

## 常见问题

### Q: 首次运行搜索很慢？
A: 首次运行需要下载模型文件，请耐心等待。模型下载后会缓存，后续运行会很快。

### Q: 如何限制抓取的论文数量？
A: 在抓取时，可以在前端代码中修改请求参数，或者直接修改 `app.py` 中的 `max_papers` 参数。

### Q: 搜索索引会占用多少空间？
A: 每篇论文的向量约1.5KB，1000篇论文的索引约1.5MB，加上模型文件约400MB。

### Q: 可以更换搜索模型吗？
A: 可以，修改 `utils/search.py` 中的模型名称即可。推荐模型：
- `paraphrase-multilingual-MiniLM-L12-v2` (默认，多语言)
- `all-MiniLM-L6-v2` (英文，更快)
- `paraphrase-multilingual-mpnet-base-v2` (多语言，更准确但更慢)

## 注意事项

- 抓取论文时请遵守arXiv的使用条款，避免请求过于频繁
- 首次构建索引可能需要几分钟时间
- 如果论文数量很大（>1000篇），建议使用GPU版本的FAISS以提高搜索速度

