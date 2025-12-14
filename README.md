# arXiv AI 论文助手 v2.0

一个智能的 arXiv 论文搜索和筛选工具，使用  AI 帮助你快速找到最相关的研究论文。

## ✨ 功能特点

- **智能关键词生成**：输入中文或英文的研究主题，AI 自动生成适合 arXiv 搜索的学术关键词
- **arXiv 论文搜索**：自动在 arXiv 上搜索论文，获取标题、摘要、作者等信息
- **AI 相关性分析**：使用 GLM-4 分析论文与研究主题的相关性，筛选最相关的论文
- **研究方向总结**：自动生成研究方向建议和阅读指南
- **现代化界面**：赛博朋克风格的响应式 Web 界面

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/WORMMMMMM/PaperFilter.git
cd PaperFilter
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置 API Key

**方法一：创建本地配置文件（推荐）**

```bash
cp config.example.py config_local.py
```

然后编辑 `config_local.py`，填入你的 GLM API Key：

```python
GLM_API_KEY = "your-api-key-here"
```

**方法二：设置环境变量**

```bash
# Windows
set GLM_API_KEY=your-api-key-here

# Linux/Mac
export GLM_API_KEY=your-api-key-here
```

> 💡 GLM API Key 可从 [智谱AI开放平台](https://open.bigmodel.cn/) 获取

### 4. 启动服务

```bash
python app.py
```

### 5. 访问界面

打开浏览器访问 http://localhost:5000

## 📖 使用方法

1. **输入研究主题**：在搜索框中输入你想研究的主题，可以是中文或英文
   - 例如：`Contact-rich Manipulation`
   - 例如：`机器人灵巧操作`
   - 例如：`强化学习在机械臂控制中的应用`

2. **调整参数**（可选）：
   - **搜索数量**：在 arXiv 上搜索的最大论文数量（默认50）
   - **筛选数量**：AI 筛选后返回的论文数量（默认10）
   - **智能关键词**：是否让 AI 自动生成搜索关键词

3. **查看结果**：
   - **AI 研究方向总结**：对筛选出的论文进行整体分析
   - **AI 推荐**：按相关性排序的论文列表，包含 AI 评分和推荐理由
   - **全部结果**：所有搜索到的论文

## 📁 项目结构

```
PaperFilter/
├── app.py                 # Flask 主应用
├── config.py              # 配置文件
├── config.example.py      # 配置文件示例
├── config_local.py        # 本地配置（不会提交到Git）
├── requirements.txt       # Python 依赖
├── utils/
│   ├── arxiv_search.py    # arXiv 搜索模块
│   ├── glm_client.py      # GLM API 客户端
│   └── __init__.py
├── templates/
│   └── index.html         # Web 界面
└── data/                  # 数据存储目录
```

## 🔧 API 接口

### POST /api/search
智能搜索并筛选论文

**参数：**
- `query` (必需): 搜索主题
- `max_results`: 最大搜索结果数（默认50）
- `top_k`: 筛选后返回的论文数（默认10）
- `auto_keywords`: 是否自动生成关键词（默认true）

### POST /api/quick_search
快速搜索（不使用 AI 筛选）

**参数：**
- `query` (必需): 搜索关键词
- `max_results`: 最大结果数（默认30）

### POST /api/generate_keywords
生成搜索关键词

**参数：**
- `input` (必需): 用户输入的研究描述

### GET /api/history
获取上次搜索结果

## ⚠️ 注意事项

- 请遵守 arXiv 的使用条款，不要过于频繁地发送请求
- GLM API 有调用限制，请注意配额使用
- 搜索结果会自动保存到 `data/last_search.json`
- `config_local.py` 包含敏感信息，已被 `.gitignore` 忽略

## 📝 License

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
