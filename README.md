# PaperFilter

一个用于爬取 arXiv Robotics 分类论文标题的 Python 爬虫工具。

## 功能特性

- 🚀 自动爬取 arXiv Robotics (cs.RO) 分类的所有最新论文
- 📄 支持分页，自动抓取所有页面
- 📊 提取论文标题、arXiv ID 和作者信息
- 💾 支持 JSON 和文本两种格式输出
- ⚡ 包含请求延迟，避免对服务器造成压力

## 安装

### 依赖要求

- Python 3.6+
- requests
- beautifulsoup4
- lxml

### 安装步骤

1. 克隆仓库：
```bash
git clone https://github.com/WORMMMMMM/PaperFilter.git
cd PaperFilter
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

直接运行爬虫脚本：

```bash
python3 arxiv_scraper.py
```

脚本会自动：
- 访问 https://arxiv.org/list/cs.RO/recent
- 爬取所有页面的论文（通常有 150-200 篇）
- 保存结果到 `papers.json` 和 `papers.txt`

## 输出文件

- **papers.json**: JSON 格式，包含完整的论文信息（标题、arXiv ID、作者）
- **papers.txt**: 文本格式，便于阅读的论文列表

## 项目结构

```
PaperFilter/
├── arxiv_scraper.py    # 主爬虫脚本
├── requirements.txt    # Python 依赖包
├── README.md          # 项目说明文档
├── papers.json        # 输出：JSON 格式的论文数据
└── papers.txt         # 输出：文本格式的论文列表
```

## 示例输出

```
开始爬取 arXiv Robotics 论文...
================================================================================
正在爬取: https://arxiv.org/list/cs.RO/recent
第1页 (skip=0): 找到 50 篇论文
第2页 (skip=50): 找到 50 篇论文
第3页 (skip=100): 找到 50 篇论文
第4页 (skip=150): 找到 50 篇论文
================================================================================
爬取完成！共找到 200 篇论文
```

## 注意事项

- 脚本包含 1 秒的请求延迟，避免对 arXiv 服务器造成压力
- 如果网络不稳定，可能需要多次运行
- 论文数量会根据 arXiv 上的实际数量而变化

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！
