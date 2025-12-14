#!/usr/bin/env python3
"""
配置文件
包含API密钥和其他配置项

注意：请在 config.local.py 中配置你的 API Key，或设置环境变量 GLM_API_KEY
"""

import os

# GLM API配置
# 优先从环境变量读取，如果没有则尝试从 config.local.py 读取
GLM_API_KEY = os.environ.get("GLM_API_KEY", "")

# 如果环境变量没有设置，尝试从本地配置文件读取
if not GLM_API_KEY:
    try:
        from config_local import GLM_API_KEY as LOCAL_KEY
        GLM_API_KEY = LOCAL_KEY
    except ImportError:
        pass

# 如果还是没有，提示用户
if not GLM_API_KEY:
    print("⚠️  警告: 未配置 GLM_API_KEY")
    print("   请设置环境变量 GLM_API_KEY 或创建 config_local.py 文件")

GLM_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
GLM_MODEL = "glm-4-flash"  # 使用GLM-4-Flash模型

# 搜索配置
DEFAULT_MAX_RESULTS = 50  # 默认最大搜索结果数
DEFAULT_TOP_RELEVANT = 10  # 默认筛选后返回的论文数量

# 请求配置
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 0.5  # 请求间隔（秒）
